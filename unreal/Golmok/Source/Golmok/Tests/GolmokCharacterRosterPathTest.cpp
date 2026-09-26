#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "Camera/CameraComponent.h"
#include "Characters/GolmokCharacterSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Debug/GolmokPathPawn.h"
#include "Editor.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Misc/PackageName.h"
#include "Player/GolmokCharacter.h"
#include "Tests/AutomationEditorCommon.h"

namespace GolmokCharacterRosterPathTest
{
	const TCHAR* Map = TEXT("/Game/Golmok/Maps/L_Dev");

	class FScenario : public IAutomationLatentCommand
	{
	public:
		explicit FScenario(FAutomationTestBase* InTest) : Test(InTest), Started(FPlatformTime::Seconds()) {}
		virtual ~FScenario() override
		{
			if (!File.IsEmpty()) IFileManager::Get().Delete(*File, false, false, true);
		}

		virtual bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
			UGolmokCharacterSubsystem* Roster = World ? World->GetSubsystem<UGolmokCharacterSubsystem>() : nullptr;
			UGolmokDebugSubsystem* Debug = World ? World->GetSubsystem<UGolmokDebugSubsystem>() : nullptr;
			if (FPlatformTime::Seconds() - Started > 30.0)
			{
				if (Debug && Debug->IsPlaying()) Debug->StopPlayback(TEXT("roster test timeout"));
				Test->AddError(TEXT("roster path round trip timed out"));
				return true;
			}
			if (!World || !PC || !Roster || !Debug || World->GetTimeSeconds() < 0.6f) return false;
			FString Message;
			if (Phase == 0)
			{
				AGolmokCharacter* Pawn = Cast<AGolmokCharacter>(PC->GetPawn());
				if (!Pawn) return false;
				Character = Pawn;
				Pawn->GetCharacterMovement()->DisableMovement();
				Pawn->SetActorLocation(FVector(-500, 0, 1000), false, nullptr, ETeleportType::TeleportPhysics);
				if (!Test->TestTrue(TEXT("select proxy before playback"), Roster->SelectCharacter(TEXT("proxy135"), Message))) return true;
				Position = Pawn->GetActorLocation();
				MeshTransform = Pawn->GetMesh()->GetRelativeTransform();
				const FString Name = TEXT("_automation_roster_") + FGuid::NewGuid().ToString(EGuidFormats::Digits);
				File = Debug->PathFilePath(Name);
				GolmokStatsMath::CameraPath Path;
				Path.Name = TCHAR_TO_UTF8(*Name);
				Path.Level = TCHAR_TO_UTF8(Map);
				Path.Created = "2026-09-27T00:00:00Z"; // Synthetic fixture metadata, not the execution timestamp.
				for (int32 Index = 0; Index <= 20; ++Index)
				{
					GolmokStatsMath::PoseSample Sample;
					Sample.T = Index * 0.1;
					Sample.P[0] = -600.0 + Index * 5.0;
					Sample.P[1] = 0.0;
					Sample.P[2] = 1000.0;
					Path.Samples.push_back(Sample);
				}
				if (!Test->TestTrue(TEXT("write private temporary path"), UGolmokDebugSubsystem::SavePathFile(File, Path, Message))) return true;
				if (!Test->TestTrue(TEXT("start real path playback"), Debug->StartPlayback(Name, false, Message))) return true;
				Test->TestNotNull(TEXT("path system possesses its actual pawn"), Cast<AGolmokPathPawn>(PC->GetPawn()));
				Test->TestTrue(TEXT("path hides original character"), Pawn->IsHidden());
				Test->TestFalse(TEXT("roster refuses selection during path playback"), Roster->SelectCharacter(TEXT("manny"), Message));
				Test->TestEqual(TEXT("path refusal preserves selection"), Roster->GetCurrentId(), FString(TEXT("proxy135")));
				Phase = 1;
				return false;
			}
			if (Debug->IsPlaying())
			{
				Test->TestTrue(TEXT("path stays on separate pawn across ticks"), PC->GetPawn() != Character.Get());
				return false;
			}
			Test->TestTrue(TEXT("natural playback end restores original pawn"), PC->GetPawn() == Character.Get());
			Test->TestTrue(TEXT("natural playback end restores view target"), PC->GetViewTarget() == Character.Get());
			if (Test->TestNotNull(TEXT("original character survives"), Character.Get()))
			{
				Test->TestFalse(TEXT("original character visible after playback"), Character->IsHidden());
				Test->TestEqual(TEXT("selection survives actual re-possession"), Roster->GetCurrentId(), FString(TEXT("proxy135")));
				Test->TestTrue(TEXT("position survives actual re-possession"), Character->GetActorLocation().Equals(Position, 0.01));
				Test->TestTrue(TEXT("mesh transform survives actual re-possession"), Character->GetMesh()->GetRelativeTransform().Equals(MeshTransform));
				Test->TestEqual(TEXT("capsule survives actual re-possession"), Character->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight(), 69.f);
				Test->TestEqual(TEXT("camera survives actual re-possession"), Character->GetFollowCamera()->FieldOfView, 75.f);
				Test->TestEqual(TEXT("speed survives actual re-possession"), Character->GetWalkSpeed(), 145.f);
				Test->TestTrue(TEXT("switch works after playback"), Roster->SelectCharacter(TEXT("quinn"), Message));
			}
			Test->AddInfo(TEXT("EXECUTED real path start -> separate pawn -> natural finish -> original proxy135 restored"));
			return true;
		}

	private:
		FAutomationTestBase* Test;
		double Started;
		int32 Phase = 0;
		FString File;
		TWeakObjectPtr<AGolmokCharacter> Character;
		FVector Position = FVector::ZeroVector;
		FTransform MeshTransform;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokCharacterRosterPathTest, "Golmok.Character.PathRoundTrip",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokCharacterRosterPathTest::RunTest(const FString& Parameters)
{
	using namespace GolmokCharacterRosterPathTest;
	if (!FPackageName::DoesPackageExist(Map))
	{
		AddError(TEXT("L_Dev missing; run test.ps1 -SetupDevLevel"));
		return false;
	}
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(Map));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}
#endif
