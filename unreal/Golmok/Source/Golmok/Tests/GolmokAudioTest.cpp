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
#include "PhysicsEngine/PhysicsSettings.h"
#include "Photo/GolmokPhotoModeSubsystem.h"
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
			Test->TestTrue(TEXT("exactly one audio HUD line"), Debug && Debug->GetHudLines().FilterByPredicate([](const FString& Line) { return Line.StartsWith(TEXT("audio: ")); }).Num() == 1);
			if (Debug)
			{
				const int32 Before = Debug->NumExtraHudLineProviders();
				const auto First = Debug->AddExtraHudLineProvider([]() { return FString(TEXT("audio_test_first")); });
				const auto Second = Debug->AddExtraHudLineProvider([]() { return FString(TEXT("audio_test_second")); });
				Test->TestEqual(TEXT("two temporary providers added"), Debug->NumExtraHudLineProviders(), Before + 2);
				Debug->RemoveExtraHudLineProvider(First);
				Test->TestTrue(TEXT("removing earlier provider preserves later provider"), Debug->GetHudLines().Contains(TEXT("audio_test_second")));
				Debug->RemoveExtraHudLineProvider(First); // An expired handle must not remove its neighbor.
				Debug->RemoveExtraHudLineProvider(Second);
				Test->TestEqual(TEXT("original providers remain after out-of-order removal"), Debug->NumExtraHudLineProviders(), Before);
				Test->TestFalse(TEXT("removed provider is absent from refreshed HUD"), Debug->GetHudLines().Contains(TEXT("audio_test_second")));
			}
			Test->AddExpectedMessagePlain(TEXT("audio: R55 fixture surface 61"), ELogVerbosity::Warning, EAutomationExpectedMessageFlags::Contains, 1);
			Test->AddExpectedMessagePlain(TEXT("audio: R55 fixture surface 62"), ELogVerbosity::Warning, EAutomationExpectedMessageFlags::Contains, 1);
			Audio->SetSurfaceDiagnostic(61, TEXT("R55 fixture surface 61"));
			Audio->SetSurfaceDiagnostic(61, TEXT("R55 fixture surface 61"));
			Audio->SetSurfaceDiagnostic(62, TEXT("R55 fixture surface 62"));
			Test->TestTrue(TEXT("surface diagnostic retained in HUD text"), Audio->Describe().Contains(TEXT("error: R55 fixture surface 62")));
			Audio->SetSurfaceDiagnostic(0, FString());
			Audio->SetSurfaceDiagnostic(61, TEXT("R55 fixture surface 61")); // Clearing HUD does not reset once-per-number logging.
			Audio->SetSurfaceDiagnostic(0, FString());
			Tod->EnterInterior(TEXT("audio_destroy"));
			Test->TestEqual(TEXT("destruction starts in interior"), Audio->GetState(), FString(TEXT("interior")));
			Tod->Destroy();
			Audio->RefreshBindings();
			Test->TestEqual(TEXT("destroyed ToD resets auto state"), Audio->GetState(), FString(TEXT("outdoor_day")));
			Tod = AGolmokTimeOfDay::FindOrSpawn(World);
			Audio->RefreshBindings();
			Tod->ApplyPreset(TEXT("night"), true);
			Test->TestEqual(TEXT("replacement ToD event rebinds"), Audio->GetState(), FString(TEXT("outdoor_night")));
			Tod->Destroy();
			Audio->RefreshBindings();
			Test->TestEqual(TEXT("destroyed night preset resets too"), Audio->GetState(), FString(TEXT("outdoor_day")));
			Test->AddInfo(TEXT("EXECUTED actual Lighting preset/interior events -> audio, nested sources, force/auto, mute, credits, footstep attachment"));
			return true;
		}
	private:
		FAutomationTestBase* Test;
		double Started;
	};
	class FPhotoFadeScenario : public IAutomationLatentCommand
	{
	public:
		explicit FPhotoFadeScenario(FAutomationTestBase* InTest) : Test(InTest) {}
		bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			auto* Audio = World ? World->GetSubsystem<UGolmokAmbienceSubsystem>() : nullptr;
			auto* Photo = World ? World->GetSubsystem<UGolmokPhotoModeSubsystem>() : nullptr;
			if (!Audio || !Photo) { Test->AddError(TEXT("photo fade world unavailable")); return true; }
			const double Now = FPlatformTime::Seconds();
			if (Phase == 0)
			{
				if (!Audio->GetConfig().bMuteInPhoto || Audio->GetConfig().PhotoMuteFadeSeconds <= 0)
				{ Test->AddInfo(TEXT("NOT EXECUTED photo fade: requires mute policy and nonzero duration")); return true; }
				FString Message;
				PreviousPause = Photo->PauseMode; Photo->PauseMode = EGolmokPhotoPauseMode::GamePause;
				if (!Photo->Enter(Message)) { Photo->PauseMode = PreviousPause; Test->AddError(Message); return true; }
				At = Now; Phase = 1; return false;
			}
			if (Now - At > 10) { Photo->Exit(TEXT("audio fade timeout")); Photo->PauseMode = PreviousPause; Test->AddError(TEXT("photo audio fade timed out")); return true; }
			// Poll the target rather than assuming wall time equals clamped audio Tick time.
			if (Phase == 1 && Audio->GetPhotoGain() < .0001)
			{
				Test->AddInfo(TEXT("EXECUTED GamePause photo gain reached zero"));
				Photo->Exit(TEXT("audio fade test")); At = Now; Phase = 2;
			}
			if (Phase == 2 && Audio->GetPhotoGain() > .9999)
			{
				Test->AddInfo(TEXT("EXECUTED photo gain restored"));
				Photo->PauseMode = PreviousPause; return true;
			}
			return false;
		}
	private:
		FAutomationTestBase* Test; int32 Phase = 0; double At = 0;
		EGolmokPhotoPauseMode PreviousPause = EGolmokPhotoPauseMode::GamePause;
	};

}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokAudioStateMachineTest, "Golmok.Audio.StateMachine", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FGolmokAudioStateMachineTest::RunTest(const FString& Parameters)
{
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(TEXT("/Game/Golmok/Maps/L_Dev")));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(GolmokAudioTest::FStateScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(GolmokAudioTest::FPhotoFadeScenario(this));
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
	Gain.Set(1, 2); Gain.Advance(.5); TestEqual(TEXT("sin fade at quarter duration"), Gain.Value, FMath::Sin(UE_DOUBLE_PI / 8));
	Gain.Set(0, 1); Gain.Advance(.5); TestEqual(TEXT("interrupted fade retains starting gain"), Gain.Value, FMath::Sin(UE_DOUBLE_PI / 8) / FMath::Sqrt(2.0));
	Gain.Advance(10); TestEqual(TEXT("fade clamps at target"), Gain.Value, 0.0);
	GolmokAudioMath::Envelope Outgoing, Incoming;
	Outgoing.Set(1, 0); Outgoing.Set(0, 2); Incoming.Set(1, 2);
	Outgoing.Advance(.5); Incoming.Advance(.5);
	TestTrue(TEXT("crossfade conserves complementary power"), FMath::IsNearlyEqual(FMath::Square(Outgoing.Value) + FMath::Square(Incoming.Value), 1.0));
	Outgoing.Set(1, 1); Incoming.Set(0, 1);
	Outgoing.Advance(.25); Incoming.Advance(.25);
	TestTrue(TEXT("interrupted reversal conserves power"), FMath::IsNearlyEqual(FMath::Square(Outgoing.Value) + FMath::Square(Incoming.Value), 1.0));
	const double BeforeReplacement = Incoming.Value;
	Incoming.Set(0, .05); Incoming.Advance(0);
	TestEqual(TEXT("third clip fade retains current gain"), Incoming.Value, BeforeReplacement);
	Incoming.Advance(.025); TestTrue(TEXT("50 ms replacement midpoint still audible"), Incoming.Value > 0 && Incoming.Value < BeforeReplacement);
	Incoming.Advance(.025); TestEqual(TEXT("replacement reaches zero before swapping"), Incoming.Value, 0.0);
	Incoming.Set(1, 0); TestEqual(TEXT("zero duration is immediate"), Incoming.Value, 1.0);
	GolmokAudioMath::Envelope PhotoEnvelope(false);
	PhotoEnvelope.Set(1, .25); PhotoEnvelope.Advance(.0625);
	TestTrue(TEXT("photo amplitude raised cosine"), FMath::IsNearlyEqual(PhotoEnvelope.Value, (1.0 - FMath::Cos(UE_DOUBLE_PI / 4)) / 2));
	PhotoEnvelope.Set(0, .25); PhotoEnvelope.Advance(.125);
	TestTrue(TEXT("photo retarget amplitude continuity"), FMath::IsNearlyEqual(PhotoEnvelope.Value, (1.0 - FMath::Cos(UE_DOUBLE_PI / 4)) / 4));
	FGolmokAudioConfig Config; FString Error;
	TestTrue(TEXT("production audio config"), GolmokAudio::LoadConfig(Config, Error));
	Config.StateCrossfadeSeconds.Add(TEXT("interior"), 1.0);
	TestEqual(TEXT("destination fade override"), Config.FadeSeconds(TEXT("interior")), 1.0);
	Config.StateCrossfadeSeconds.Remove(TEXT("outdoor_day"));
	TestEqual(TEXT("unspecified destination uses global duration"), Config.FadeSeconds(TEXT("outdoor_day")), 2.0);
	TestEqual(TEXT("measured proxy walk stride"), Config.StrideFor(TEXT("proxy110"), false), 45.0);
	TestEqual(TEXT("measured quinn run stride"), Config.StrideFor(TEXT("quinn"), true), 146.0);
	TestEqual(TEXT("unknown roster uses global stride"), Config.StrideFor(TEXT("future"), false), 70.0);
	TestEqual(TEXT("production photo fade setting"), Config.PhotoMuteFadeSeconds, .25);
	FString Manifest;
	TestTrue(TEXT("read manifest for invalid date tests"), FFileHelper::LoadFileToString(Manifest, *(FPaths::ProjectConfigDir() / TEXT("Golmok/audio.json"))));
	for (const TCHAR* Invalid : {TEXT("null"), TEXT("true"), TEXT("-0.01"), TEXT("5.01"), TEXT("\"0.25\"")})
	{
		const FString InvalidJson = Manifest.Replace(TEXT("\"photo_mute_fade_seconds\": 0.25"), *FString::Printf(TEXT("\"photo_mute_fade_seconds\": %s"), Invalid));
		TestFalse(TEXT("invalid photo fade rejected"), GolmokAudio::ParseConfig(InvalidJson, Config, Error));
		TestEqual(TEXT("invalid parse preserves photo fade"), Config.PhotoMuteFadeSeconds, .25);
	}
	for (const TCHAR* Invalid : {TEXT("null"), TEXT("[]"), TEXT("{\"Manny\":{\"walk\":67,\"run\":146}}"), TEXT("{\"manny\":{\"walk\":67}}"), TEXT("{\"manny\":{\"walk\":true,\"run\":146}}"), TEXT("{\"manny\":{\"walk\":0,\"run\":146}}"), TEXT("{\"manny\":{\"walk\":67,\"run\":146,\"extra\":1}}")})
	{
		// Rename the production field so each malformed replacement is the only active mapping.
		FString InvalidJson = Manifest.Replace(TEXT("\"stride_cm_by_character\""), TEXT("\"unused_stride_fixture\""));
		InvalidJson.ReplaceInline(TEXT("\"walk_stride_cm\":"), *FString::Printf(TEXT("\"stride_cm_by_character\":%s, \"walk_stride_cm\":"), Invalid));
		TestFalse(TEXT("invalid character stride rejected"), GolmokAudio::ParseConfig(InvalidJson, Config, Error));
		TestEqual(TEXT("invalid parse preserves roster stride"), Config.StrideFor(TEXT("proxy110"), false), 45.0);
	}
	FGolmokAudioConfig LegacyConfig;
	const FString Legacy = Manifest.Replace(TEXT("\"stride_cm_by_character\""), TEXT("\"unused_stride_fixture\"")).Replace(TEXT("\"photo_mute_fade_seconds\""), TEXT("\"unused_photo_fixture\""));
	TestTrue(TEXT("optional fields support legacy manifest"), GolmokAudio::ParseConfig(Legacy, LegacyConfig, Error));
	TestEqual(TEXT("legacy roster uses global stride"), LegacyConfig.StrideFor(TEXT("proxy110"), false), 70.0);
	TestEqual(TEXT("legacy photo fade defaults to quarter second"), LegacyConfig.PhotoMuteFadeSeconds, .25);
	TestFalse(TEXT("obsolete mesh scale rejected"), GolmokAudio::ParseConfig(Manifest.Replace(TEXT("\"walk_stride_cm\":"), TEXT("\"stride_scale_by_mesh\":true, \"walk_stride_cm\":")), LegacyConfig, Error));
	TestTrue(TEXT("zero photo fade accepted"), GolmokAudio::ParseConfig(Manifest.Replace(TEXT("\"photo_mute_fade_seconds\": 0.25"), TEXT("\"photo_mute_fade_seconds\": 0")), LegacyConfig, Error));
	TestEqual(TEXT("zero photo fade retained"), LegacyConfig.PhotoMuteFadeSeconds, 0.0);
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
	{
		auto* Settings = GetMutableDefault<UPhysicsSettings>();
		TGuardValue<TArray<FPhysicalSurfaceName>> RestoreSurfaces(Settings->PhysicalSurfaces, {});
		TestEqual(TEXT("unnamed surface mapping falls back"), UGolmokFootstepComponent::ResolveSurfaceSet(Config, 1, false), FString(TEXT("default")));
		TestEqual(TEXT("explicit stairs survives unnamed material"), UGolmokFootstepComponent::ResolveSurfaceSet(Config, 1, true), FString(TEXT("stairs")));
		FPhysicalSurfaceName Named; Named.Type = SurfaceType1; Named.Name = TEXT("AsPhAlT");
		TestTrue(TEXT("undefined mapped surface diagnosed"), !UGolmokFootstepComponent::SurfaceDiagnostic(Config, 1).IsEmpty());
		Settings->PhysicalSurfaces.Add(Named);
		TestTrue(TEXT("surface name matches set id case-insensitively"), UGolmokFootstepComponent::SurfaceDiagnostic(Config, 1).IsEmpty());
		TestEqual(TEXT("named surface uses audio mapping"), UGolmokFootstepComponent::ResolveSurfaceSet(Config, 1, false), Config.Surfaces.FindRef(1));
		Settings->PhysicalSurfaces[0].Name = TEXT("Tile");
		TestEqual(TEXT("wrong surface name falls back"), UGolmokFootstepComponent::ResolveSurfaceSet(Config, 1, false), FString(TEXT("default")));
		TestEqual(TEXT("unknown surface number falls back"), UGolmokFootstepComponent::ResolveSurfaceSet(Config, 63, false), FString(TEXT("default")));
	}
	AddInfo(TEXT("EXECUTED distance/air/landing/teleport/repossess and interrupted fade math; audible playback remains V-10"));
	return true;
}
#endif
