// Opt-in rendered evidence. This is a capture aid, not a visual-quality assertion or V-12 approval.
#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "Camera/CameraComponent.h"
#include "Characters/GolmokCharacterSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Editor.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "HAL/FileManager.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Misc/App.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Player/GolmokCharacter.h"
#include "Tests/AutomationEditorCommon.h"
#include "UnrealClient.h"

namespace GolmokCharacterRosterRenderTest
{
	const TCHAR* Map = TEXT("/Game/Golmok/Maps/L_Dev");
	const TCHAR* Presets[] = {TEXT("overcast_morning"), TEXT("clear_noon"), TEXT("golden_evening"), TEXT("night")};

	class FScenario : public IAutomationLatentCommand
	{
	public:
		explicit FScenario(FAutomationTestBase* InTest) : Test(InTest), Started(FPlatformTime::Seconds())
		{
			Folder = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("Automation/WP18Render") /
				(FDateTime::UtcNow().ToString(TEXT("%Y%m%d-%H%M%S")) + TEXT("-") + FGuid::NewGuid().ToString(EGuidFormats::Digits)));
			IFileManager::Get().MakeDirectory(*Folder, true);
			Manifest = TEXT("WP-18 preliminary rendered evidence\nmap=L_Dev; material=stock template PBR; no final asset/retarget/Toon/photo-DOF validation\n")
				TEXT("All captures use only the game viewport. selection_cpu_ms is synchronous API duration, NOT frame hitch/GPU ms/VRAM.\n")
				TEXT("Night is captured unchanged and must not be averaged away if unreadable.\n");
		}

		virtual bool Update() override
		{
			const double Now = FPlatformTime::Seconds();
			if (Now - Started > 180.0)
			{
				Test->AddError(TEXT("render evidence timed out; inspect partial capture folder"));
				return true;
			}
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
			AGolmokCharacter* Character = PC ? Cast<AGolmokCharacter>(PC->GetPawn()) : nullptr;
			UGolmokCharacterSubsystem* Roster = World ? World->GetSubsystem<UGolmokCharacterSubsystem>() : nullptr;
			AGolmokTimeOfDay* Lighting = World ? AGolmokTimeOfDay::Find(World) : nullptr;
			if (!Character || !Roster || !Lighting || World->GetTimeSeconds() < 0.6f) return false;
			const TCHAR* Id = Case < 4 || Case == 10 ? TEXT("proxy135") : Case < 8 || Case == 11 ? TEXT("proxy110") : Case == 8 ? TEXT("quinn") : TEXT("manny");
			const TCHAR* Light = Presets[Case < 8 ? Case % 4 : 1];
			const TCHAR* View = Case >= 10 ? TEXT("feet_boom1p5_pitch0") : TEXT("default_pitch0");
			if (Phase == 0)
			{
				Character->GetCharacterMovement()->DisableMovement();
				Character->SetActorLocation(FVector(500, 0, Character->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight() + 2), false, nullptr, ETeleportType::TeleportPhysics);
				Character->SetActorRotation(FRotator(0, 180, 0));
				PC->SetControlRotation(FRotator::ZeroRotator);
				if (UGolmokDebugSubsystem* Debug = World->GetSubsystem<UGolmokDebugSubsystem>()) Debug->SetHudVisible(false);
				FString Message;
				const double Before = FPlatformTime::Seconds();
				const bool bSelected = Roster->SelectCharacter(Id, Message);
				const double SelectionMs = (FPlatformTime::Seconds() - Before) * 1000.0;
				if (!Test->TestTrue(TEXT("render evidence selects character"), bSelected))
				{
					Test->AddError(Message);
					return true;
				}
				// A diagnostic view only: the default shoulder camera crops feet at this aspect ratio.
				if (Case >= 10) Character->GetCameraBoom()->TargetArmLength *= 1.5f;
				if (!Test->TestTrue(TEXT("render evidence applies original lighting preset"), Lighting->ApplyPreset(FName(Light), true))) return true;
				File = Folder / FString::Printf(TEXT("%s_pbr_%s_%s.png"), Id, Light, View);
				Manifest += FString::Printf(TEXT("id=%s light=%s view=%s fov=%.4f boom_cm=%.4f selection_cpu_ms=%.3f capsule_center=%s file=%s\n"), Id, Light, View, Character->GetFollowCamera()->FieldOfView, Character->GetCameraBoom()->TargetArmLength, SelectionMs, *Character->GetActorLocation().ToString(), *FPaths::GetCleanFilename(File));
				FFileHelper::SaveStringToFile(Manifest, *(Folder / TEXT("capture.txt")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
				PhaseAt = Now;
				Phase = 1;
				return false;
			}
			if (Phase == 1)
			{
				if (Now - PhaseAt < 6.0) return false; // Camera lag, shader/texture streaming and exposure settling.
				// Restrict to game viewport: never capture the desktop/editor or another app.
				FScreenshotRequest::RequestScreenshot(File, false, false, false, FIntRect(), true);
				PhaseAt = Now;
				Phase = 2;
				return false;
			}
			if (IFileManager::Get().FileSize(*File) <= 0)
			{
				if (Now - PhaseAt < 15.0) return false;
				Test->AddError(FString::Printf(TEXT("game viewport screenshot was not written: %s"), *File));
				return true;
			}
			Test->AddInfo(FString::Printf(TEXT("CAPTURED %s (visual judgment pending)"), *File));
			++Case;
			Phase = 0;
			return Case == 12;
		}

	private:
		FAutomationTestBase* Test;
		double Started;
		double PhaseAt = 0.0;
		int32 Case = 0;
		int32 Phase = 0;
		FString Folder;
		FString File;
		FString Manifest;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokCharacterRosterRenderTest, "Golmok.Character.RenderEvidence",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokCharacterRosterRenderTest::RunTest(const FString& Parameters)
{
	if (!FParse::Param(FCommandLine::Get(), TEXT("GolmokCharacterRenderEvidence")))
	{
		AddWarning(TEXT("NOT EXECUTED: rendered evidence requires -GolmokCharacterRenderEvidence and a rendering RHI."));
		return true;
	}
	if (!FApp::CanEverRender())
	{
		AddError(TEXT("Rendered evidence explicitly requested without a rendering RHI; remove -nullrhi."));
		return false;
	}
	using namespace GolmokCharacterRosterRenderTest;
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
