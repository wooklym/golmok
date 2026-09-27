// WP-18 / V-11: exercise the real WP-12 subsystem when that lane is present.
// A main-only build reports NOT EXECUTED explicitly until WP-12 is integrated.
#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#if __has_include("Photo/GolmokPhotoModeSubsystem.h")
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Characters/GolmokCharacterSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Editor.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "Photo/GolmokPhotoCameraPawn.h"
#include "Photo/GolmokPhotoModeSubsystem.h"
#include "Player/GolmokCharacter.h"
#include "Tests/AutomationEditorCommon.h"

namespace GolmokCharacterRosterPhotoTest
{
	const TCHAR* Map = TEXT("/Game/Golmok/Maps/L_Dev");
	const TCHAR* Ids[] = {TEXT("proxy135"), TEXT("proxy110"), TEXT("quinn")};
	const float Fovs[] = {75.f, 72.2222222f, 80.f};

	class FScenario : public IAutomationLatentCommand
	{
	public:
		explicit FScenario(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

		virtual bool Update() override
		{
			const double Now = FPlatformTime::Seconds();
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			UGolmokPhotoModeSubsystem* Photo = World ? World->GetSubsystem<UGolmokPhotoModeSubsystem>() : nullptr;
			if (Now - CreatedAt > 60.0)
			{
				if (Photo) Photo->Exit(TEXT("roster integration timeout"));
				Test->AddError(TEXT("roster/photo integration timed out"));
				return true;
			}
			APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
			AGolmokCharacter* Character = PC ? Cast<AGolmokCharacter>(PC->GetPawn()) : nullptr;
			UGolmokCharacterSubsystem* Roster = World ? World->GetSubsystem<UGolmokCharacterSubsystem>() : nullptr;
			if (!Photo || !Character || !Roster || !PC->PlayerCameraManager || World->GetTimeSeconds() < 0.6f)
			{
				return false;
			}
			const int32 Index = Case % 3;
			const bool bTimeDilation = Case >= 3;
			FString Message;
			if (Phase == 0)
			{
				Character->GetCharacterMovement()->DisableMovement();
				Character->SetActorLocation(FVector(500, 0, 1000), false, nullptr, ETeleportType::TeleportPhysics);
				if (!Test->TestTrue(TEXT("select before photo"), Roster->SelectCharacter(Ids[Index], Message)))
				{
					Test->AddError(Message);
					return true;
				}
				Photo->PauseMode = bTimeDilation ? EGolmokPhotoPauseMode::TimeDilation : EGolmokPhotoPauseMode::GamePause;
				// Non-default values make restoration observable in the fallback path.
				UGameplayStatics::SetGlobalTimeDilation(World, bTimeDilation ? 0.8f : 1.f);
				Character->CustomTimeDilation = bTimeDilation ? 0.65f : 1.f;
				Phase = 1;
				PhaseAt = Now;
				return false;
			}
			if (Phase == 1)
			{
				if (Now - PhaseAt < 0.4) return false; // Refresh the actual PlayerCameraManager after switching.
				Test->TestTrue(TEXT("player camera uses roster FOV"), FMath::IsNearlyEqual(PC->PlayerCameraManager->GetFOVAngle(), Fovs[Index], 0.01f));
				OriginalCharacter = Character;
				CharacterLocation = Character->GetActorLocation();
				MeshTransform = Character->GetMesh()->GetRelativeTransform();
				Mesh = Character->GetMesh()->GetSkeletalMeshAsset();
				Radius = Character->GetCapsuleComponent()->GetUnscaledCapsuleRadius();
				HalfHeight = Character->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight();
				WalkSpeed = Character->GetWalkSpeed();
				ControlRotation = PC->GetControlRotation();
				if (!Test->TestTrue(TEXT("enter real photo mode"), Photo->Enter(Message)))
				{
					Test->AddError(Message);
					return true;
				}
				Test->TestTrue(TEXT("photo inherits selected character FOV"), FMath::IsNearlyEqual(Photo->GetParam(EGolmokPhotoParam::Fov), double(Fovs[Index]), 0.01));
				Test->TestTrue(TEXT("photo anchor is the resized capsule center"), Photo->GetAnchor().Equals(CharacterLocation, 0.01));
				Test->TestTrue(TEXT("photo keeps original possession"), PC->GetPawn() == Character);
				Test->TestEqual(TEXT("requested pause path"), UGameplayStatics::IsGamePaused(World), !bTimeDilation);
				Photo->SetCharacterHidden(true);
				PhotoPawn = Photo->GetPhotoPawn();
				if (!Test->TestNotNull(TEXT("real photo camera exists"), PhotoPawn.Get()))
				{
					Photo->Exit(TEXT("missing photo camera"));
					return true;
				}
				PhotoLocation = PhotoPawn->GetActorLocation();
				GlobalDilation = UGameplayStatics::GetGlobalTimeDilation(World);
				PawnDilation = Character->CustomTimeDilation;
				PhotoTicks = Photo->GetPawnTickCount();
				Test->TestFalse(TEXT("manual switch refused during actual photo"), Roster->SelectCharacter(TEXT("manny"), Message));
				Test->TestFalse(TEXT("switch refusal explains why"), Message.IsEmpty());
				IConsoleManager::Get().ProcessUserConsoleInput(TEXT("golmok.character manny"), *GLog, World);
				Phase = 2;
				PhaseAt = Now;
				return false;
			}
			if (Phase == 2)
			{
				if (Now - PhaseAt < 0.35) return false; // Exercise the paused/time-dilated world across real frames.
				Test->TestTrue(TEXT("photo camera ticks while frozen"), Photo->GetPawnTickCount() > PhotoTicks);
				Test->TestEqual(TEXT("refusal keeps selected id"), Roster->GetCurrentId(), FString(Ids[Index]));
				Test->TestTrue(TEXT("refusal keeps character instance"), Character == OriginalCharacter.Get());
				Test->TestTrue(TEXT("refusal keeps photo view target"), PC->GetViewTarget() == PhotoPawn.Get());
				Test->TestTrue(TEXT("refusal keeps hidden character"), Character->IsHidden() && Photo->IsCharacterHidden());
				Test->TestTrue(TEXT("refusal keeps character position"), Character->GetActorLocation().Equals(CharacterLocation, 0.01));
				Test->TestTrue(TEXT("refusal keeps mesh and transform"), Character->GetMesh()->GetSkeletalMeshAsset() == Mesh.Get() && Character->GetMesh()->GetRelativeTransform().Equals(MeshTransform));
				Test->TestEqual(TEXT("refusal keeps capsule radius"), Character->GetCapsuleComponent()->GetUnscaledCapsuleRadius(), Radius);
				Test->TestEqual(TEXT("refusal keeps capsule half height"), Character->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight(), HalfHeight);
				Test->TestEqual(TEXT("refusal keeps movement speed"), Character->GetWalkSpeed(), WalkSpeed);
				Test->TestEqual(TEXT("refusal keeps player FOV"), Character->GetFollowCamera()->FieldOfView, Fovs[Index]);
				Test->TestEqual(TEXT("refusal keeps world dilation"), UGameplayStatics::GetGlobalTimeDilation(World), GlobalDilation);
				Test->TestEqual(TEXT("refusal keeps pawn dilation"), Character->CustomTimeDilation, PawnDilation);
				Test->TestTrue(TEXT("refusal keeps photo pose"), PhotoPawn.IsValid() && PhotoPawn->GetActorLocation().Equals(PhotoLocation, 0.01));
				Test->TestTrue(TEXT("photo exit"), Photo->Exit(TEXT("roster integration")));
				Test->TestFalse(TEXT("photo inactive after exit"), Photo->IsActive());
				Test->TestFalse(TEXT("exit restores unpaused world"), UGameplayStatics::IsGamePaused(World));
				Test->TestFalse(TEXT("exit restores shown character"), Character->IsHidden());
				Test->TestTrue(TEXT("exit restores original view target"), PC->GetViewTarget() == Character);
				Test->TestTrue(TEXT("exit restores control rotation"), PC->GetControlRotation().Equals(ControlRotation, 0.01));
				Test->TestEqual(TEXT("exit restores original world dilation"), UGameplayStatics::GetGlobalTimeDilation(World), bTimeDilation ? 0.8f : 1.f);
				Test->TestEqual(TEXT("exit restores original pawn dilation"), Character->CustomTimeDilation, bTimeDilation ? 0.65f : 1.f);
				Test->TestTrue(TEXT("switch succeeds after photo exit"), Roster->SelectCharacter(TEXT("manny"), Message));
				Test->TestEqual(TEXT("post-photo selection applied"), Roster->GetCurrentId(), FString(TEXT("manny")));
				Test->TestTrue(TEXT("post-photo resize keeps feet"), FMath::IsNearlyEqual(Character->GetActorLocation().Z - 92.0, CharacterLocation.Z - HalfHeight, 0.01));
				Test->AddInfo(FString::Printf(TEXT("EXECUTED %s / %s: entry FOV, capsule anchor, refusal, restore, post-exit switch"), Ids[Index], bTimeDilation ? TEXT("TimeDilation") : TEXT("GamePause")));
				UGameplayStatics::SetGlobalTimeDilation(World, 1.f);
				Character->CustomTimeDilation = 1.f;
				++Case;
				Phase = 0;
				return Case == 6;
			}
			return true;
		}

	private:
		FAutomationTestBase* Test;
		double CreatedAt;
		double PhaseAt = 0.0;
		int32 Phase = 0;
		int32 Case = 0;
		int32 PhotoTicks = 0;
		TWeakObjectPtr<AGolmokCharacter> OriginalCharacter;
		TWeakObjectPtr<AGolmokPhotoCameraPawn> PhotoPawn;
		TWeakObjectPtr<USkeletalMesh> Mesh;
		FVector CharacterLocation = FVector::ZeroVector;
		FVector PhotoLocation = FVector::ZeroVector;
		FTransform MeshTransform;
		FRotator ControlRotation = FRotator::ZeroRotator;
		float Radius = 0.f;
		float HalfHeight = 0.f;
		float WalkSpeed = 0.f;
		float GlobalDilation = 1.f;
		float PawnDilation = 1.f;
	};
}
#endif

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokCharacterRosterPhotoTest, "Golmok.Character.PhotoIntegration",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokCharacterRosterPhotoTest::RunTest(const FString& Parameters)
{
#if __has_include("Photo/GolmokPhotoModeSubsystem.h")
	using namespace GolmokCharacterRosterPhotoTest;
	if (!FPackageName::DoesPackageExist(Map))
	{
		AddError(TEXT("L_Dev missing; run test.ps1 -SetupDevLevel"));
		return false;
	}
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(Map));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
#else
	AddWarning(TEXT("NOT EXECUTED: WP-12 Photo subsystem is absent. This result is not a photo integration pass."));
#endif
	return true;
}
#endif
