#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Animation/AnimInstance.h"
#include "Camera/CameraComponent.h"
#include "Characters/GolmokCharacterSubsystem.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Editor.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Player/GolmokCharacter.h"
#include "Tests/AutomationEditorCommon.h"

namespace GolmokCharacterRosterTest
{
	const TCHAR* DevMap = TEXT("/Game/Golmok/Maps/L_Dev");
	const TCHAR* MannyPath = TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple");
	const TCHAR* QuinnPath = TEXT("/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple.SKM_Quinn_Simple");
	const TCHAR* AnimPath = TEXT("/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed_C");

	void CheckDefault(FAutomationTestBase* Test, AGolmokCharacter* Character)
	{
		// Literals, deliberately independent of the JSON and math helper.
		Test->TestEqual(TEXT("default radius"), Character->GetCapsuleComponent()->GetUnscaledCapsuleRadius(), 42.f);
		Test->TestEqual(TEXT("default half height"), Character->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight(), 92.f);
		Test->TestTrue(TEXT("default mesh offset"), Character->GetMesh()->GetRelativeLocation().Equals(FVector(0, 0, -92)));
		Test->TestTrue(TEXT("default mesh rotation"), Character->GetMesh()->GetRelativeRotation().Equals(FRotator(0, -90, 0)));
		Test->TestTrue(TEXT("default mesh scale"), Character->GetMesh()->GetRelativeScale3D().Equals(FVector::OneVector));
		Test->TestEqual(TEXT("default boom"), Character->GetCameraBoom()->TargetArmLength, 320.f);
		Test->TestTrue(TEXT("default socket"), Character->GetCameraBoom()->SocketOffset.Equals(FVector(0, 45, 55)));
		Test->TestEqual(TEXT("default FOV"), Character->GetFollowCamera()->FieldOfView, 80.f);
		Test->TestEqual(TEXT("default walk"), Character->GetWalkSpeed(), 180.f);
		Test->TestEqual(TEXT("default run"), Character->GetRunSpeed(), 500.f);
		Test->TestEqual(TEXT("default active speed"), Character->GetCharacterMovement()->MaxWalkSpeed, 180.f);
		USkeletalMesh* Mesh = Character->GetMesh()->GetSkeletalMeshAsset();
		UAnimInstance* Anim = Character->GetMesh()->GetAnimInstance();
		Test->TestEqual(TEXT("default mesh asset"), Mesh ? Mesh->GetPathName() : FString(), FString(MannyPath));
		Test->TestEqual(TEXT("default animation class"), Anim ? Anim->GetClass()->GetPathName() : FString(), FString(AnimPath));
	}

	class FRosterScenario : public IAutomationLatentCommand
	{
	public:
		explicit FRosterScenario(FAutomationTestBase* InTest) : Test(InTest), Started(FPlatformTime::Seconds()) {}
		virtual bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
			AGolmokCharacter* Character = PC ? Cast<AGolmokCharacter>(PC->GetPawn()) : nullptr;
			UGolmokCharacterSubsystem* System = World ? World->GetSubsystem<UGolmokCharacterSubsystem>() : nullptr;
			if (!Character || !System || World->GetTimeSeconds() < 0.6f)
			{
				if (FPlatformTime::Seconds() - Started < 60.0) return false;
				Test->AddError(TEXT("timed out waiting for initialized character/subsystem"));
				return true;
			}
			Test->TestEqual(TEXT("automatic initial application"), System->GetCurrentId(), FString(TEXT("manny")));
			CheckDefault(Test, Character);
			FString Message;
			Test->TestFalse(TEXT("unknown id rejected"), System->SelectCharacter(TEXT("missing_id"), Message));
			Test->TestEqual(TEXT("bad id leaves current selection"), System->GetCurrentId(), FString(TEXT("manny")));
			CheckDefault(Test, Character);

			// Stay away from map props; no physics tick occurs inside this transaction scenario.
			Character->SetActorLocation(FVector(500, 0, 1000), false, nullptr, ETeleportType::TeleportPhysics);
			const double Feet = Character->GetActorLocation().Z - 92.0;
			Test->TestTrue(TEXT("switch proxy135"), System->SelectCharacter(TEXT("proxy135"), Message));
			Test->TestEqual(TEXT("proxy radius"), Character->GetCapsuleComponent()->GetUnscaledCapsuleRadius(), 33.6f);
			Test->TestEqual(TEXT("proxy half height"), Character->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight(), 69.f);
			Test->TestTrue(TEXT("feet preserved"), FMath::IsNearlyEqual(Character->GetActorLocation().Z - 69.0, Feet));
			Test->TestTrue(TEXT("proxy mesh scale"), Character->GetMesh()->GetRelativeScale3D().Equals(FVector(.8, .8, .75)));
			Test->TestTrue(TEXT("proxy mesh offset"), Character->GetMesh()->GetRelativeLocation().Equals(FVector(0, 0, -69)));
			Test->TestEqual(TEXT("proxy walk"), Character->GetCharacterMovement()->MaxWalkSpeed, 145.f);
			Test->TestEqual(TEXT("proxy run"), Character->GetRunSpeed(), 380.f);
			Test->TestEqual(TEXT("proxy boom"), Character->GetCameraBoom()->TargetArmLength, 260.f);
			Test->TestTrue(TEXT("proxy socket"), Character->GetCameraBoom()->SocketOffset.Equals(FVector(0, 35, 45)));
			Test->TestEqual(TEXT("proxy FOV"), Character->GetFollowCamera()->FieldOfView, 75.f);

			// A roof fits 135 cm, but blocks the 184 cm default capsule.
			AActor* Roof = World->SpawnActor<AActor>();
			UBoxComponent* Box = NewObject<UBoxComponent>(Roof);
			Roof->SetRootComponent(Box);
			Box->SetBoxExtent(FVector(100, 100, 5));
			Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
			Box->SetCollisionObjectType(ECC_WorldStatic);
			Box->SetCollisionResponseToAllChannels(ECR_Block);
			Box->RegisterComponent();
			Roof->SetActorLocation(FVector(500, 0, Feet + 160));
			const FVector Before = Character->GetActorLocation();
			Test->TestFalse(TEXT("blocked growth rejected"), System->SelectCharacter(TEXT("manny"), Message));
			Test->TestTrue(TEXT("blocked growth keeps position"), Character->GetActorLocation().Equals(Before));
			Test->TestEqual(TEXT("blocked growth keeps selection"), System->GetCurrentId(), FString(TEXT("proxy135")));
			Test->TestEqual(TEXT("blocked growth keeps speed"), Character->GetWalkSpeed(), 145.f);
			Test->TestEqual(TEXT("blocked growth keeps camera"), Character->GetFollowCamera()->FieldOfView, 75.f);
			Roof->Destroy();

			Character->GetCharacterMovement()->MaxWalkSpeed = Character->GetRunSpeed();
			Test->TestTrue(TEXT("switch while running"), System->SelectCharacter(TEXT("proxy110"), Message));
			Test->TestEqual(TEXT("running state preserved"), Character->GetCharacterMovement()->MaxWalkSpeed, 310.f);
			Test->TestTrue(TEXT("110 feet preserved"), FMath::IsNearlyEqual(Character->GetActorLocation().Z -
				Character->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight(), Feet, 1e-4));

			AActor* PhotoView = World->SpawnActor<AActor>();
			PC->SetViewTarget(PhotoView);
			Character->SetActorHiddenInGame(true);
			Test->TestFalse(TEXT("photo view rejects selection"), System->SelectCharacter(TEXT("manny"), Message));
			Test->TestTrue(TEXT("hidden flag untouched"), Character->IsHidden());
			Test->TestTrue(TEXT("view target untouched"), PC->GetViewTarget() == PhotoView);
			PC->SetViewTarget(Character);
			Character->SetActorHiddenInGame(false);
			PhotoView->Destroy();
			UGameplayStatics::SetGamePaused(World, true);
			Test->TestFalse(TEXT("pause rejects selection"), System->SelectCharacter(TEXT("manny"), Message));
			UGameplayStatics::SetGamePaused(World, false);

			APawn* TemporaryPawn = World->SpawnActor<APawn>();
			PC->Possess(TemporaryPawn);
			Test->TestFalse(TEXT("non-character pawn rejects selection"), System->SelectCharacter(TEXT("manny"), Message));
			Test->TestEqual(TEXT("temporary pawn keeps world selection"), System->GetCurrentId(), FString(TEXT("proxy110")));
			Character->GetCameraBoom()->TargetArmLength = 999.f;
			PC->Possess(Character);
			PC->SetViewTarget(Character);
			Test->TestTrue(TEXT("repossess reapplies selected camera"), FMath::IsNearlyEqual(Character->GetCameraBoom()->TargetArmLength, 226.66667f, 1e-3f));
			TemporaryPawn->Destroy();

			Character->GetCharacterMovement()->MaxWalkSpeed = Character->GetWalkSpeed();
			IConsoleCommand* Command = IConsoleManager::Get().FindConsoleObject(TEXT("golmok.character"))->AsCommand();
			if (Test->TestNotNull(TEXT("registered character command"), Command))
			{
				Command->Execute({TEXT("list")}, World, *GLog);
				Command->Execute({TEXT("quinn")}, World, *GLog);
				Test->TestEqual(TEXT("console selects Quinn"), System->GetCurrentId(), FString(TEXT("quinn")));
				Test->TestEqual(TEXT("Quinn mesh loaded"), Character->GetMesh()->GetSkeletalMeshAsset()->GetPathName(), FString(QuinnPath));
				Test->TestNotNull(TEXT("Quinn uses compatible animation"), Character->GetMesh()->GetAnimInstance());
			}
			Test->TestTrue(TEXT("restore default"), System->SelectCharacter(TEXT("manny"), Message));
			CheckDefault(Test, Character);
			return true;
		}
	private:
		FAutomationTestBase* Test;
		double Started;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokCharacterRosterConfigTest, "Golmok.Character.Config",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokCharacterRosterConfigTest::RunTest(const FString& Parameters)
{
	FGolmokCharacterRoster Roster;
	FString Error;
	if (!TestTrue(TEXT("load JSON"), GolmokCharacters::LoadRoster(Roster, Error))) { AddError(Error); return false; }
	TestEqual(TEXT("four placeholders"), Roster.Entries.Num(), 4);
	TestEqual(TEXT("default id"), Roster.DefaultId, FString(TEXT("manny")));
	TestTrue(TEXT("localized name loaded"), Roster.Find(TEXT("manny"))->NameKo == TEXT("매니"));
	FString Text;
	FFileHelper::LoadFileToString(Text, *FPaths::Combine(FPaths::ProjectConfigDir(), TEXT("Golmok/characters.json")));
	const TArray<FString> Invalid = {
		TEXT("{}"), TEXT("[]"), TEXT("{broken}"),
		Text.Replace(TEXT("\"schema_version\": 1"), TEXT("\"schema_version\": 2")),
		Text.Replace(TEXT("\"default\": \"manny\""), TEXT("\"default\": \"missing\"")),
		Text.Replace(TEXT("\"id\": \"quinn\""), TEXT("\"id\": \"manny\"")),
		Text.Replace(TEXT("\"height_cm\": 180"), TEXT("\"height_cm\": true")),
		Text.Replace(TEXT("\"radius_cm\": 42"), TEXT("\"radius_cm\": 99")),
		Text.Replace(TEXT("\"run_cm_s\": 500"), TEXT("\"run_cm_s\": 180")),
		Text.Replace(TEXT("\"footstep_set\": null"), TEXT("\"footstep_set\": 123")),
		Text.Replace(TEXT("\"schema_version\": 1"), TEXT("\"extra\": 1, \"schema_version\": 1"))
	};
	for (const FString& Bad : Invalid)
	{
		TestFalse(TEXT("invalid document rejected"), GolmokCharacters::ParseRoster(Bad, Roster, Error));
		TestFalse(TEXT("error explains rejection"), Error.IsEmpty());
		TestEqual(TEXT("failure preserves roster"), Roster.Entries.Num(), 4);
		TestEqual(TEXT("failure preserves default"), Roster.DefaultId, FString(TEXT("manny")));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokCharacterRosterRuntimeTest, "Golmok.Character.Runtime",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokCharacterRosterRuntimeTest::RunTest(const FString& Parameters)
{
	using namespace GolmokCharacterRosterTest;
	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(TEXT("L_Dev missing; run test.ps1 -SetupDevLevel"));
		return false;
	}
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FRosterScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}
#endif
