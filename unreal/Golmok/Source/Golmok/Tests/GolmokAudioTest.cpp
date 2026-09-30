#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "Audio/GolmokAmbienceSubsystem.h"
#include "Audio/GolmokFootstepComponent.h"
#include "Animation/GolmokGaspCharacter.h"
#include "Animation/GolmokAnimationConfig.h"
#include "Animation/AnimInstance.h"
#include "Animation/GolmokLocomotionStateComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Misc/ScopeExit.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Editor.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "PhysicsEngine/PhysicsSettings.h"
#include "Photo/GolmokPhotoModeSubsystem.h"
#include "Tests/AutomationEditorCommon.h"

namespace GolmokAudioTest
{
	class FFootEventScenario : public IAutomationLatentCommand
	{
	public:
		explicit FFootEventScenario(FAutomationTestBase* InTest) : Test(InTest), Started(FPlatformTime::Seconds()) {}
		bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			auto* PC = World ? World->GetFirstPlayerController() : nullptr;
			auto* Original = PC ? Cast<AGolmokCharacter>(PC->GetPawn()) : nullptr;
			auto* Audio = World ? World->GetSubsystem<UGolmokAmbienceSubsystem>() : nullptr;
			if (!Original || !Audio || World->GetTimeSeconds() < .6f)
			{
				if (FPlatformTime::Seconds() - Started < 30) return false;
				Test->AddError(TEXT("foot event PIE timeout")); return true;
			}
			FActorSpawnParameters Spawn; Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			auto* Plain = World->SpawnActor<AGolmokCharacter>(FVector(500,0,1000), FRotator::ZeroRotator, Spawn);
			if (!Test->TestNotNull(TEXT("explicit ordinary pawn"), Plain)) return true;
			ON_SCOPE_EXIT { PC->Possess(Original); PC->SetViewTarget(Original); Plain->Destroy(); };
			PC->Possess(Plain); Audio->RefreshBindings();
			auto* OriginalSteps = Plain->FindComponentByClass<UGolmokFootstepComponent>();
			if (!Test->TestNotNull(TEXT("original distance component"), OriginalSteps)) return true;
			auto& Config = const_cast<FGolmokAudioConfig&>(Audio->GetConfig());
			TGuardValue<FString> DriverGuard(Config.FootstepDriver, TEXT("auto"));
			Test->TestFalse(TEXT("auto on ordinary pawn stays distance"), OriginalSteps->UsesNotifyDriver());
			Plain->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
			const int32 OrdinaryBefore = Audio->GetFootstepRequests();
			OriginalSteps->TickComponent(.1f, LEVELTICK_All, nullptr);
			Plain->SetActorLocation(Plain->GetActorLocation() + FVector(100,0,0), false, nullptr, ETeleportType::TeleportPhysics);
			OriginalSteps->TickComponent(.1f, LEVELTICK_All, nullptr);
			Test->TestEqual(TEXT("ordinary auto still emits one distance step"), Audio->GetFootstepRequests(), OrdinaryBefore + 1);
			Test->TestTrue(TEXT("HUD shows ordinary auto distance"), Audio->Describe().Contains(TEXT("drv=distance(auto) ev=0")));
			auto* Pawn = World->SpawnActor<AGolmokGaspCharacter>(FVector(1500, 0, 1000), FRotator::ZeroRotator, Spawn);
			if (!Test->TestNotNull(TEXT("GASP native test pawn without assets"), Pawn)) return true;
			ON_SCOPE_EXIT { Pawn->Destroy(); };
			PC->Possess(Pawn); Audio->RefreshBindings();
			auto* Steps = Pawn->FindComponentByClass<UGolmokFootstepComponent>();
			auto* Provider = Pawn->FindComponentByClass<UGolmokLocomotionStateComponent>();
			if (!Test->TestNotNull(TEXT("GASP footstep component"), Steps) || !Test->TestNotNull(TEXT("GASP foot provider"), Provider))
			{ PC->Possess(Original); Pawn->Destroy(); return true; }
			Test->TestFalse(TEXT("GASP pawn with nonGASP source uses distance"), Steps->UsesNotifyDriver());
			bool bAutoPositiveExecuted = false;
			UClass* TestAnim = Pawn->GetMesh()->GetAnimClass();
			if (TestAnim && TestAnim->GetPathName().StartsWith(TEXT("/Game/")))
			{
				FString Text;
				FFileHelper::LoadFileToString(Text, *GolmokAnimation::ConfigFilePath());
				TSharedPtr<FJsonObject> Root;
				if (Test->TestTrue(TEXT("read test animation contract"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root)))
				{
					auto Gasp = Root->GetObjectField(TEXT("gasp"));
					Gasp->SetStringField(TEXT("content_root"), TEXT("/Game"));
					Gasp->SetStringField(TEXT("anim_class"), TestAnim->GetPathName().RightChop(6));
					Text.Reset(); FJsonSerializer::Serialize(Root.ToSharedRef(), TJsonWriterFactory<>::Create(&Text));
					GolmokAnimation::FScopedConfigOverride Override(Text);
					bAutoPositiveExecuted = true;
					const uint32 Evaluations = Steps->GetAnimContractEvaluationsForTest();
					Plain->GetMesh()->SetAnimInstanceClass(TestAnim);
					Test->TestFalse(TEXT("GASP contract alone cannot make ordinary pawn notify"), OriginalSteps->UsesNotifyDriver());
					Test->TestTrue(TEXT("auto class contract positive"), Steps->UsesNotifyDriver());
					Test->TestTrue(TEXT("auto cached class contract positive"), Steps->UsesNotifyDriver());
					const int32 Before = Audio->GetFootstepRequests();
					Provider->NotifyFootEvent(EGolmokFootEvent::Step, true);
					Test->TestEqual(TEXT("auto positive delivers one event"), Audio->GetFootstepRequests(), Before + 1);
					Test->TestTrue(TEXT("HUD positive driver and event count"), Audio->Describe().Contains(TEXT("drv=notify(auto) ev=1")));
					Steps->TickComponent(.1f, LEVELTICK_All, nullptr);
					Test->TestEqual(TEXT("repeat query event Tick and HUD evaluate contract only once"), Steps->GetAnimContractEvaluationsForTest(), Evaluations + 1);
					Pawn->GetMesh()->SetAnimInstanceClass(UAnimInstance::StaticClass());
					Test->TestFalse(TEXT("nonnull class change invalidates positive cache"), Steps->UsesNotifyDriver());
					Pawn->GetMesh()->SetAnimInstanceClass(TestAnim);
					Test->TestTrue(TEXT("class restored recomputes contract"), Steps->UsesNotifyDriver());
				}
				Test->TestFalse(TEXT("restored real config uses distance"), Steps->UsesNotifyDriver());
			}
			else Test->AddInfo(TEXT("NOT EXECUTED auto-positive fixture: installed test ABP unavailable"));
			Config.FootstepDriver = TEXT("notify");
			Test->TestTrue(TEXT("explicit notify before first synthetic event"), Steps->UsesNotifyDriver());
			Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
			const auto Tick = [&]() { Steps->TickComponent(.1f, LEVELTICK_All, nullptr); };
			const auto Move = [&]() { Pawn->SetActorLocation(Pawn->GetActorLocation() + FVector(100,0,0), false, nullptr, ETeleportType::TeleportPhysics); Tick(); };
			int32 Count = Audio->GetFootstepRequests();
			Tick(); Move();
			Test->TestEqual(TEXT("notify has no distance fallback before first event"), Audio->GetFootstepRequests(), Count);
			Provider->NotifyFootEvent(EGolmokFootEvent::Step, true);
			Test->TestEqual(TEXT("one synthetic step reaches playback exactly once"), Audio->GetFootstepRequests(), ++Count);
			Move(); Move();
			Test->TestEqual(TEXT("distance cannot duplicate notify step"), Audio->GetFootstepRequests(), Count);
			const int32 Landings = Audio->GetLandingRequests();
			Provider->NotifyFootEvent(EGolmokFootEvent::Land, false);
			Tick();
			Test->TestEqual(TEXT("one land reaches landing playback exactly once"), Audio->GetLandingRequests(), Landings + 1);
			Test->TestEqual(TEXT("land is not also a step"), Audio->GetFootstepRequests(), Count);
			const uint64 EventsBeforePause = Steps->GetFootEventCount();
			UGameplayStatics::SetGamePaused(World, true);
			Provider->NotifyFootEvent(EGolmokFootEvent::Step, false);
			UGameplayStatics::SetGamePaused(World, false);
			Test->TestEqual(TEXT("paused foot event ignored"), Audio->GetFootstepRequests(), Count);
			Test->TestEqual(TEXT("filtered event still increments diagnostic count"), Steps->GetFootEventCount(), EventsBeforePause + 1);
			if (auto* Photo = World->GetSubsystem<UGolmokPhotoModeSubsystem>())
			{
				TGuardValue<EGolmokPhotoPauseMode> PauseGuard(Photo->PauseMode, EGolmokPhotoPauseMode::TimeDilation);
				FString Message; PC->SetViewTarget(Pawn);
				if (Test->TestTrue(TEXT("time dilation photo enter"), Photo->Enter(Message)))
				{
					Test->TestFalse(TEXT("time dilation photo is not game pause"), UGameplayStatics::IsGamePaused(World));
					Provider->NotifyFootEvent(EGolmokFootEvent::Step, false);
					Test->TestEqual(TEXT("photo foot event ignored without game pause"), Audio->GetFootstepRequests(), Count);
					Photo->Exit(TEXT("foot event test"));
				}
			}
			Config.FootstepDriver = TEXT("distance");
			Tick();
			Provider->NotifyFootEvent(EGolmokFootEvent::Step, false);
			Test->TestEqual(TEXT("explicit distance ignores notify"), Audio->GetFootstepRequests(), Count);
			Move();
			Test->TestEqual(TEXT("distance driver resumes one stride"), Audio->GetFootstepRequests(), ++Count);
			Config.FootstepDriver = TEXT("notify");
			Move();
			Test->TestEqual(TEXT("switch to notify clears residual distance"), Audio->GetFootstepRequests(), Count);
			Steps->UnregisterComponent();
			Provider->NotifyFootEvent(EGolmokFootEvent::Step, false);
			Test->TestEqual(TEXT("unregister removes subscription"), Audio->GetFootstepRequests(), Count);
			Steps->RegisterComponent(); Steps->ReregisterComponent();
			Provider->NotifyFootEvent(EGolmokFootEvent::Step, false);
			Test->TestEqual(TEXT("repeated registration binds exactly once"), Audio->GetFootstepRequests(), ++Count);
			PC->Possess(Original); PC->SetViewTarget(Original);
			Provider->NotifyFootEvent(EGolmokFootEvent::Step, false);
			Test->TestEqual(TEXT("old pawn events ignored after possession"), Audio->GetFootstepRequests(), Count);
			Test->AddInfo(bAutoPositiveExecuted ? TEXT("EXECUTED auto positive cache/class/generation/HUD and ordinary-pawn conjunction") : TEXT("NOT EXECUTED auto-positive cache/class/generation/HUD fixture"));
			Test->AddInfo(TEXT("EXECUTED ordinary distance + auto negative; synthetic Step/Land -> one playback request each; no distance duplicate; pause/unregister/possession guards. Audible output and original GASP foley not tested."));
			return true;
		}
	private:
		FAutomationTestBase* Test; double Started;
	};

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
	// R55-5/R63: reject coercion and preserve the entire credit/asset snapshot.
	const FString PreviousCredits = Config.Credits;
	const int32 PreviousAssetCount = Config.Assets.Num();
	for (const TCHAR* Field : {TEXT("loop"), TEXT("placeholder")})
	{
		const FString Original = FString::Printf(TEXT("\"%s\": true"), Field);
		for (const TCHAR* Value : {TEXT("1"), TEXT("\"true\"")})
		{
			const FString Mutated = Manifest.Replace(*Original, *FString::Printf(TEXT("\"%s\": %s"), Field, Value));
			TestTrue(FString::Printf(TEXT("%s=%s mutation changed manifest"), Field, Value), Mutated != Manifest);
			TestFalse(FString::Printf(TEXT("%s=%s rejects coercion"), Field, Value), GolmokAudio::ParseConfig(Mutated, Config, Error));
			TestTrue(FString::Printf(TEXT("%s=%s diagnostic names field/type"), Field, Value), Error.Contains(FString::Printf(TEXT(".%s: expected boolean"), Field)) && Error.Contains(TEXT("audio.json assets.")));
			TestEqual(FString::Printf(TEXT("%s=%s preserves credits"), Field, Value), Config.Credits, PreviousCredits);
			TestEqual(FString::Printf(TEXT("%s=%s preserves asset count"), Field, Value), Config.Assets.Num(), PreviousAssetCount);
		}
	}
	for (const TCHAR* Value : {TEXT("123"), TEXT("true")})
	{
		const FString Mutated = Manifest.Replace(TEXT("\"author\": \"Golmok procedural generator\""), *FString::Printf(TEXT("\"author\": %s"), Value));
		TestTrue(FString::Printf(TEXT("author=%s mutation changed manifest"), Value), Mutated != Manifest);
		TestFalse(FString::Printf(TEXT("author=%s rejects coercion"), Value), GolmokAudio::ParseConfig(Mutated, Config, Error));
		TestTrue(FString::Printf(TEXT("author=%s diagnostic names field/type"), Value), Error.Contains(TEXT(".author: expected single-line string")));
		TestEqual(FString::Printf(TEXT("author=%s preserves credits"), Value), Config.Credits, PreviousCredits);
		TestEqual(FString::Printf(TEXT("author=%s preserves asset count"), Value), Config.Assets.Num(), PreviousAssetCount);
	}
	// A valid string set id "1" must not make numeric 1 a valid surface mapping.
	FString NumericSurface = Manifest.Replace(TEXT("\"sets\": {"), TEXT("\"sets\": {\"1\": [\"asphalt\"],"));
	NumericSurface.ReplaceInline(TEXT("\"surface_sets\": {"), TEXT("\"surface_sets\": {\"4\": 1,"));
	TestTrue(TEXT("numeric surface fixture adds string set and numeric reference"), NumericSurface != Manifest);
	TestFalse(TEXT("numeric surface reference rejects coercion"), GolmokAudio::ParseConfig(NumericSurface, Config, Error));
	TestEqual(TEXT("numeric surface diagnostic"), Error, FString(TEXT("audio.json footsteps.surface_sets.4: expected string")));
	TestEqual(TEXT("numeric surface preserves credits"), Config.Credits, PreviousCredits);
	TestEqual(TEXT("numeric surface preserves asset count"), Config.Assets.Num(), PreviousAssetCount);
	FGolmokAudioConfig ReferenceControl;
	TestTrue(TEXT("string surface reference control accepted"), GolmokAudio::ParseConfig(NumericSurface.Replace(TEXT("\"4\": 1"), TEXT("\"4\": \"1\"")), ReferenceControl, Error));
	TSharedPtr<FJsonObject> SampleObject;
	TestTrue(TEXT("sample fixture parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Manifest), SampleObject));
	FString CompactManifest;
	if (!SampleObject.IsValid()) return false;
	FJsonSerializer::Serialize(SampleObject.ToSharedRef(), TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&CompactManifest));
	FString BoolSample = CompactManifest.Replace(TEXT("\"asphalt\":{"), TEXT("\"true\":{"));
	BoolSample.ReplaceInline(TEXT("[\"asphalt\"]"), TEXT("[\"true\"]"));
	TestTrue(TEXT("string true asset reference control accepted"), GolmokAudio::ParseConfig(BoolSample, ReferenceControl, Error));
	BoolSample.ReplaceInline(TEXT("[\"true\"]"), TEXT("[true]"));
	TestFalse(TEXT("boolean sample reference rejects coercion"), GolmokAudio::ParseConfig(BoolSample, Config, Error));
	TestTrue(TEXT("sample diagnostic names indexed field/type"), Error.Contains(TEXT("footsteps.sets.")) && Error.Contains(TEXT("[0]: expected string")));
	TestFalse(TEXT("boolean preset rejects coercion"), GolmokAudio::ParseConfig(Manifest.Replace(TEXT("\"preset_states\": {"), TEXT("\"preset_states\": {\"invalid\": true,")), Config, Error));
	TestEqual(TEXT("preset diagnostic names field/type"), Error, FString(TEXT("audio.json preset_states.invalid: expected string")));
	TestEqual(TEXT("reference failures preserve credits"), Config.Credits, PreviousCredits);
	TestEqual(TEXT("reference failures preserve asset count"), Config.Assets.Num(), PreviousAssetCount);
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
	for (const TCHAR* Key : {TEXT("master_volume"), TEXT("photo_mute_fade_seconds"), TEXT("crossfade_seconds_by_state"), TEXT("assets"), TEXT("gain"), TEXT("outdoor_day"), TEXT("walk_stride_cm"), TEXT("walk")})
	{
		FString Mutated = Manifest;
		const FString Needle = FString::Printf(TEXT("\"%s\":"), Key);
		const FString Replacement = FString::Printf(TEXT("\"%s\":"), *FString(Key).ToUpper());
		TestTrue(TEXT("key mutation applied"), Mutated.ReplaceInline(*Needle, *Replacement, ESearchCase::CaseSensitive) > 0);
		FGolmokAudioConfig Parsed = Config;
		TestFalse(FString::Printf(TEXT("case alias key %s rejected"), Key), GolmokAudio::ParseConfig(Mutated, Parsed, Error));
		TestTrue(TEXT("key case failure names field"), Error.Contains(FString(Key).ToUpper(), ESearchCase::CaseSensitive));
		TestEqual(TEXT("key failure preserves assets"), Parsed.Assets.Num(), Config.Assets.Num());
	}
	for (const TCHAR* Value : {TEXT("\"auto\""), TEXT("\"distance\""), TEXT("\"notify\""), TEXT("\"Notify\""), TEXT("null"), TEXT("true"), TEXT("1"), TEXT("[]"), TEXT("{}"), TEXT("\"bad\"")})
	{
		TSharedPtr<FJsonObject> Root;
		FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Manifest), Root);
		Root->GetObjectField(TEXT("footsteps"))->RemoveField(TEXT("driver"));
		FString Base;
		FJsonSerializer::Serialize(Root.ToSharedRef(), TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Base));
		Base.ReplaceInline(TEXT("\"walk_stride_cm\":"), *FString::Printf(TEXT("\"driver\":%s,\"walk_stride_cm\":"), Value));
		FGolmokAudioConfig Parsed = Config;
		const bool bValid = FString(Value).Equals(TEXT("\"auto\""), ESearchCase::CaseSensitive) || FString(Value).Equals(TEXT("\"distance\""), ESearchCase::CaseSensitive) || FString(Value).Equals(TEXT("\"notify\""), ESearchCase::CaseSensitive);
		TestEqual(FString::Printf(TEXT("driver %s acceptance"), Value), GolmokAudio::ParseConfig(Base, Parsed, Error), bValid);
		if (!bValid)
		{
			TestTrue(TEXT("driver failure path diagnosis"), Error.Contains(TEXT("footsteps.driver")));
			TestEqual(TEXT("bad driver retains previous"), Parsed.FootstepDriver, Config.FootstepDriver);
		}
	}
	FGolmokAudioConfig LegacyConfig;
	const FString Legacy = Manifest.Replace(TEXT("\"driver\""), TEXT("\"unused_driver_fixture\"")).Replace(TEXT("\"stride_cm_by_character\""), TEXT("\"unused_stride_fixture\"")).Replace(TEXT("\"photo_mute_fade_seconds\""), TEXT("\"unused_photo_fixture\""));
	TestTrue(TEXT("optional fields support legacy manifest"), GolmokAudio::ParseConfig(Legacy, LegacyConfig, Error));
	TestEqual(TEXT("missing driver defaults auto"), LegacyConfig.FootstepDriver, FString(TEXT("auto")));
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
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(TEXT("/Game/Golmok/Maps/L_Dev")));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(GolmokAudioTest::FFootEventScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}
#endif
