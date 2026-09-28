#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "Audio/GolmokAmbienceSubsystem.h"
#include "Audio/GolmokFootstepComponent.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Editor.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Tests/AutomationEditorCommon.h"

namespace GolmokAudioTest
{
	class FStateScenario : public IAutomationLatentCommand
	{
	public:
		explicit FStateScenario(FAutomationTestBase* InTest) : Test(InTest), Started(FPlatformTime::Seconds()) {}
		virtual bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			if (FPlatformTime::Seconds() - Started > 30) { Test->AddError(TEXT("audio PIE timeout")); return true; }
			if (!World || World->GetTimeSeconds() < .6f) return false;
			auto* Audio = World->GetSubsystem<UGolmokAmbienceSubsystem>();
			AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::FindOrSpawn(World);
			if (!Test->TestNotNull(TEXT("world audio subsystem"), Audio) || !Test->TestNotNull(TEXT("time of day"), Tod)) return true;
			Audio->RefreshBindings();
			Test->TestTrue(TEXT("actual preset event"), Tod->ApplyPreset(TEXT("night"), true));
			Test->TestEqual(TEXT("night event delivered synchronously"), Audio->GetState(), FString(TEXT("outdoor_night")));
			Tod->EnterInterior(TEXT("audio_test_a"));
			Tod->EnterInterior(TEXT("audio_test_b"));
			Test->TestEqual(TEXT("interior overrides night"), Audio->GetState(), FString(TEXT("interior")));
			Tod->ApplyPreset(TEXT("clear_noon"), true);
			Test->TestEqual(TEXT("preset cannot override interior"), Audio->GetState(), FString(TEXT("interior")));
			Tod->ExitInterior(TEXT("audio_test_a"));
			Test->TestEqual(TEXT("second interior source remains"), Audio->GetState(), FString(TEXT("interior")));
			Tod->ExitInterior(TEXT("audio_test_b"));
			Test->TestEqual(TEXT("last exit uses updated outdoor preset"), Audio->GetState(), FString(TEXT("outdoor_day")));
			Tod->ApplyPreset(TEXT("night"), true);
			Test->TestFalse(TEXT("unknown lighting preset rejected"), Tod->ApplyPreset(TEXT("audio_missing"), true));
			Test->TestEqual(TEXT("failed lighting change leaves audio state"), Audio->GetState(), FString(TEXT("outdoor_night")));
			Test->TestFalse(TEXT("unknown forced state rejected"), Audio->ForceState(TEXT("invalid")));
			Audio->ForceState(TEXT("outdoor_night")); Tod->EnterInterior(TEXT("audio_test_a"));
			Test->TestEqual(TEXT("forced state overrides events"), Audio->GetState(), FString(TEXT("outdoor_night")));
			Audio->ForceState(TEXT("auto"));
			Test->TestEqual(TEXT("auto returns to live interior"), Audio->GetState(), FString(TEXT("interior")));
			Tod->ExitInterior(TEXT("audio_test_a"));
			Audio->SetMuted(true); Test->TestTrue(TEXT("explicit mute"), Audio->IsMuted()); Audio->SetMuted(false);
			Test->TestTrue(TEXT("runtime credits present"), Audio->GetCredits().Contains(TEXT("Golmok procedural generator")));
			if (APlayerController* PC = World->GetFirstPlayerController())
			{
				APawn* Pawn = PC->GetPawn();
				if (Test->TestNotNull(TEXT("player pawn"), Pawn)) Test->TestNotNull(TEXT("footstep component attached without Player edit"), Pawn->FindComponentByClass<UGolmokFootstepComponent>());
			}
			auto* Debug = World->GetSubsystem<UGolmokDebugSubsystem>();
			Test->TestTrue(TEXT("HUD provider registered"), Debug && Debug->ExtraHudLineProviders.Num() == 1);
			Test->AddInfo(TEXT("EXECUTED actual Lighting preset/interior events -> audio, nested sources, force/auto, mute, credits, footstep attachment"));
			return true;
		}
	private:
		FAutomationTestBase* Test;
		double Started;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokAudioStateMachineTest, "Golmok.Audio.StateMachine", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FGolmokAudioStateMachineTest::RunTest(const FString& Parameters)
{
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(TEXT("/Game/Golmok/Maps/L_Dev")));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(GolmokAudioTest::FStateScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokAudioFootstepTest, "Golmok.Audio.Footstep", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FGolmokAudioFootstepTest::RunTest(const FString& Parameters)
{
	GolmokAudioMath::DistanceStepper Step;
	Step.Advance(0, true, true, 70, 300);
	TestEqual(TEXT("short walk below stride"), Step.Advance(40, true, true, 70, 300).Steps, 0);
	TestEqual(TEXT("accumulated walking stride"), Step.Advance(30, true, true, 70, 300).Steps, 1);
	TestEqual(TEXT("air suppresses footsteps"), Step.Advance(100, false, true, 70, 300).Steps, 0);
	const auto Land = Step.Advance(20, true, true, 70, 300);
	TestTrue(TEXT("air to grounded lands once"), Land.Landed); TestEqual(TEXT("no duplicate step on landing"), Land.Steps, 0);
	TestFalse(TEXT("steady ground not landing"), Step.Advance(0, true, true, 70, 300).Landed);
	TestEqual(TEXT("run distance two strides"), Step.Advance(220, true, true, 110, 300).Steps, 2);
	TestEqual(TEXT("teleport suppressed"), Step.Advance(1000, true, true, 70, 300).Steps, 0);
	TestEqual(TEXT("reinitialize after teleport"), Step.Advance(70, true, true, 70, 300).Steps, 0);
	Step.Advance(10, false, false, 70, 300);
	TestFalse(TEXT("repossess has no false landing"), Step.Advance(0, true, true, 70, 300).Landed);
	GolmokAudioMath::Envelope Gain;
	Gain.Set(1, 2); Gain.Advance(.5); TestEqual(TEXT("quarter fade"), Gain.Value, .25);
	Gain.Set(0, 1); Gain.Advance(.5); TestEqual(TEXT("interrupted fade retains starting gain"), Gain.Value, .125);
	Gain.Advance(10); TestEqual(TEXT("fade clamps at target"), Gain.Value, 0.0);
	FGolmokAudioConfig Config; FString Error;
	TestTrue(TEXT("production audio config"), GolmokAudio::LoadConfig(Config, Error));
	Config.StateCrossfadeSeconds.Add(TEXT("interior"), 1.0);
	TestEqual(TEXT("destination fade override"), Config.FadeSeconds(TEXT("interior")), 1.0);
	Config.StateCrossfadeSeconds.Remove(TEXT("outdoor_day"));
	TestEqual(TEXT("unspecified destination uses global duration"), Config.FadeSeconds(TEXT("outdoor_day")), 2.0);
	FString Manifest;
	TestTrue(TEXT("read manifest for invalid date tests"), FFileHelper::LoadFileToString(Manifest, *(FPaths::ProjectConfigDir() / TEXT("Golmok/audio.json"))));
	for (const TCHAR* Invalid : {TEXT("2026-02-30"), TEXT("2026-9-28"), TEXT("0000-01-01")})
	{
		const FString InvalidJson = Manifest.Replace(TEXT("2026-09-28"), Invalid);
		TestFalse(TEXT("invalid verified date rejected"), GolmokAudio::ParseConfig(InvalidJson, Config, Error));
	}
	TestTrue(TEXT("runtime credits include verified date"), Config.Credits.Contains(TEXT("Verified: 2026-09-28")));
	TestEqual(TEXT("default physical surface"), Config.Surfaces.FindRef(0), FString(TEXT("default")));
	TestFalse(TEXT("invalid config fails atomically"), GolmokAudio::ParseConfig(TEXT("{}"), Config, Error));
	TestTrue(TEXT("failed parse preserves prior config"), Config.Sets.Contains(TEXT("asphalt")));
	TestTrue(TEXT("unknown material uses default"), GolmokAudioMath::ChooseSurface(false, false) == GolmokAudioMath::SurfaceChoice::Default);
	TestTrue(TEXT("known material uses mapped set"), GolmokAudioMath::ChooseSurface(true, false) == GolmokAudioMath::SurfaceChoice::PhysicalMaterial);
	TestTrue(TEXT("explicit stairs tag overrides surface"), GolmokAudioMath::ChooseSurface(true, true) == GolmokAudioMath::SurfaceChoice::StairsTag);
	AddInfo(TEXT("EXECUTED distance/air/landing/teleport/repossess and interrupted fade math; audible playback remains V-10"));
	return true;
}
#endif
