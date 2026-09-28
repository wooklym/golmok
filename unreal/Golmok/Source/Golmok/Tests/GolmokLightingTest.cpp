// Lighting preset tests (WP-05 design section 8-6).
//
// Golmok.Lighting.PresetsFile: Config/Golmok/lighting_presets.json loads through AGolmokTimeOfDay::LoadPresetsFile
// with the same rules as tools/tests/test_lighting_presets.py; broken texts fail with an error message.
// Golmok.Lighting.PresetApply: on L_Dev (golmok.setup_dev_level tags the lighting actors GolmokLighting) a preset is
// applied instantly, then transitions, the interior overlay and NextPreset() are checked on the component values.
// Golmok.Lighting.Clock (WP-14a design section 7): keyframe times reproduce the presets, a time between keyframes is
// the GolmokClockMath interpolation (checked against the formula here), midnight wrap, mode / rate changes, the
// OnPresetChanged midpoint contract and OnNightChanged, ApplyPreset moving the clock, the Fixed-mode PresetApply
// sequence, and the interior overlay returning to the clock state. Design 2a: inside the night hold (21:30 -> 05:30)
// the state is the night preset and IsNight() holds; the ramp to 07:30 fires OnPresetChanged once at 06:30.
// PR #51 review: NextPreset() on the clock goes to the next keyframe in time (R51-4); IsNight() inside OnPresetChanged
// is already the target's value and OnNightChanged follows OnPresetChanged (R51-5); Fixed -> Clock and
// Realtime -> Clock keep the minutes without a jump (R51-11).
// All pass under -nullrhi (no rendering is inspected).
//
// Headless: .\tools\ue\test.ps1 -Filter Golmok.Lighting   (or in the editor console: Automation RunTests Golmok.Lighting)

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Components/DirectionalLightComponent.h"
#include "Editor.h"
#include "Engine/DirectionalLight.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Lighting/GolmokClockMath.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Tests/AutomationEditorCommon.h"

namespace GolmokLightingTest
{
	const TCHAR* DevMap = TEXT("/Game/Golmok/Maps/L_Dev");
	const TCHAR* LightingTag = TEXT("GolmokLighting");

	// One complete preset body (the overcast_morning values) for synthetic JSON texts.
	const TCHAR* CompleteBody = TEXT("\"pitch\": -35.0, \"yaw\": 110.0, \"lux\": 2.5, \"kelvin\": 6500.0, \"sky\": 1.4, ")
								 TEXT("\"fog\": 0.035, \"fog_height_falloff\": 0.15, \"volumetric\": false, \"exposure_bias\": 0.3");

	/**
	 * Cycle a b c d at 07:30 / TimeB / 18:00 / 21:30 (schema 2); TimeB empty = b has no time; InteriorExtra is spliced
	 * into interior, ExtraD into d (the last keyframe: its hold wraps past midnight to a at 07:30, design 2a).
	 */
	FString MakeJson(int32 SchemaVersion, const TCHAR* InteriorFog, const TCHAR* TimeB = TEXT("12:30"), const TCHAR* InteriorExtra = TEXT(""),
		const TCHAR* ExtraD = TEXT(""))
	{
		const FString TimeBKey = FString(TimeB).IsEmpty() ? FString() : FString::Printf(TEXT("\"time\": \"%s\", "), TimeB);
		return FString::Printf(TEXT("{\"schema_version\": %d, \"cycle\": [\"a\", \"b\", \"c\", \"d\"], \"presets\": {")
								   TEXT("\"a\": {\"time\": \"07:30\", %s}, \"b\": {%s%s}, \"c\": {\"time\": \"18:00\", %s}, \"d\": {\"time\": \"21:30\", %s%s}, ")
								   TEXT("\"interior\": {%s\"fog\": %s, \"fog_height_falloff\": 0.2, \"volumetric\": false, \"exposure_bias\": 1.0}}}"),
			SchemaVersion, CompleteBody, *TimeBKey, CompleteBody, CompleteBody, ExtraD, CompleteBody, InteriorExtra, InteriorFog);
	}

	const FGolmokLightingPreset* FindPreset(const TArray<FGolmokLightingPreset>& Presets, const TCHAR* Name)
	{
		const FName Key(Name);
		for (const FGolmokLightingPreset& P : Presets)
		{
			if (P.Name == Key)
			{
				return &P;
			}
		}
		return nullptr;
	}

	/** The tagged (or first) DirectionalLight component of the PIE world, for the visibility check. */
	UDirectionalLightComponent* SunComponent(UWorld* World)
	{
		UDirectionalLightComponent* First = nullptr;
		for (TActorIterator<ADirectionalLight> It(World); It; ++It)
		{
			UDirectionalLightComponent* Component = (*It)->FindComponentByClass<UDirectionalLightComponent>();
			if (!Component)
			{
				continue;
			}
			if ((*It)->ActorHasTag(LightingTag))
			{
				return Component;
			}
			if (!First)
			{
				First = Component;
			}
		}
		return First;
	}

	enum class EPhase : uint8
	{
		Start,
		NightDone,
		InteriorDone,
		InteriorNoonDone,
		ExitDone,
		Done,
	};

	// Transitions run with TransitionSeconds = 0.2 and only the end values (0.6 s later) are asserted.
	constexpr float ShortTransition = 0.2f;
	constexpr double SettleSeconds = 0.6;

	class FPresetApplyScenario : public IAutomationLatentCommand
	{
	public:
		explicit FPresetApplyScenario(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

		virtual bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			if (!World)
			{
				return Fail(TEXT("PIE world not running"), 60.0, FPlatformTime::Seconds() - CreatedAt);
			}
			const double Now = World->GetTimeSeconds();
			if (PhaseStart < 0.0)
			{
				PhaseStart = Now;
			}
			const double Elapsed = Now - PhaseStart;

			switch (Phase)
			{
			case EPhase::Start:
			{
				if (Elapsed < 0.5)
				{
					return false; // let the level actors finish BeginPlay
				}
				TimeOfDay = AGolmokTimeOfDay::FindOrSpawn(World);
				if (!TimeOfDay.IsValid())
				{
					Test->AddError(TEXT("AGolmokTimeOfDay::FindOrSpawn returned null in the PIE world"));
					return true;
				}
				AGolmokTimeOfDay* Tod = TimeOfDay.Get();
				Tod->TransitionSeconds = ShortTransition;
				if (!Test->TestTrue(TEXT("ApplyPreset(clear_noon, instant)"), Tod->ApplyPreset(TEXT("clear_noon"), /*bInstant*/ true)))
				{
					Test->AddError(FString::Printf(TEXT("LastError: %s"), *Tod->LastError));
					return true;
				}
				FGolmokLightingState S;
				Test->TestTrue(TEXT("CaptureState finds lighting actors on L_Dev"), Tod->CaptureState(S));
				Test->TestTrue(TEXT("clear_noon Lux ~ 10"), FMath::IsNearlyEqual(S.Lux, 10.0, 1e-3));
				Test->TestTrue(TEXT("clear_noon Kelvin ~ 5600"), FMath::IsNearlyEqual(S.Kelvin, 5600.0, 1e-2));
				Test->TestTrue(TEXT("clear_noon Fog ~ 0.015"), FMath::IsNearlyEqual(S.Fog, 0.015, 1e-4));
				Test->TestTrue(TEXT("clear_noon ExposureBias ~ 0"), FMath::IsNearlyEqual(S.ExposureBias, 0.0, 1e-4));
				Test->TestTrue(TEXT("clear_noon SunRotation.Pitch ~ -62"), FMath::IsNearlyEqual(S.SunRotation.Pitch, -62.0, 1e-2));
				Test->TestFalse(TEXT("instant apply leaves no transition"), Tod->IsTransitioning());
				Test->AddInfo(FString::Printf(TEXT("after clear_noon: %s"), *Tod->Describe()));

				Test->TestTrue(TEXT("ApplyPreset(night) with transition"), Tod->ApplyPreset(TEXT("night")));
				Test->TestTrue(TEXT("night transition started (tick enabled)"), Tod->IsTransitioning() && Tod->IsActorTickEnabled());
				return Next(EPhase::NightDone, Now);
			}

			case EPhase::NightDone:
			{
				if (Elapsed < SettleSeconds)
				{
					return false;
				}
				AGolmokTimeOfDay* Tod = Get();
				if (!Tod)
				{
					return true;
				}
				FGolmokLightingState S;
				Tod->CaptureState(S);
				Test->TestTrue(TEXT("night Lux == 0"), S.Lux == 0.0);
				Test->TestTrue(TEXT("night bVolumetric"), S.bVolumetric);
				Test->TestFalse(TEXT("night transition finished"), Tod->IsTransitioning());
				Test->TestFalse(TEXT("tick disabled after the transition"), Tod->IsActorTickEnabled());
				if (UDirectionalLightComponent* Sun = SunComponent(World))
				{
					Test->TestFalse(TEXT("sun hidden when Lux == 0"), Sun->GetVisibleFlag());
				}
				else
				{
					Test->AddError(TEXT("no DirectionalLight on L_Dev"));
				}
				NightPitch = S.SunRotation.Pitch;
				Tod->EnterInterior(TEXT("t"));
				return Next(EPhase::InteriorDone, Now);
			}

			case EPhase::InteriorDone:
			{
				if (Elapsed < SettleSeconds)
				{
					return false;
				}
				AGolmokTimeOfDay* Tod = Get();
				if (!Tod)
				{
					return true;
				}
				FGolmokLightingState S;
				Tod->CaptureState(S);
				Test->TestTrue(TEXT("interior overlay Fog == 0"), S.Fog == 0.0);
				Test->TestTrue(TEXT("interior overlay ExposureBias == 1.0"), FMath::IsNearlyEqual(S.ExposureBias, 1.0, 1e-4));
				Test->TestTrue(TEXT("interior keeps the night sun rotation"), FMath::IsNearlyEqual(S.SunRotation.Pitch, NightPitch, 1e-2));
				Test->TestTrue(TEXT("IsInterior()"), Tod->IsInterior());
				Test->AddInfo(FString::Printf(TEXT("interior: %s"), *Tod->Describe()));
				Test->TestTrue(TEXT("ApplyPreset(clear_noon) while interior"), Tod->ApplyPreset(TEXT("clear_noon")));
				return Next(EPhase::InteriorNoonDone, Now);
			}

			case EPhase::InteriorNoonDone:
			{
				if (Elapsed < SettleSeconds)
				{
					return false;
				}
				AGolmokTimeOfDay* Tod = Get();
				if (!Tod)
				{
					return true;
				}
				FGolmokLightingState S;
				Tod->CaptureState(S);
				Test->TestTrue(TEXT("base change while interior: Lux ~ 10"), FMath::IsNearlyEqual(S.Lux, 10.0, 1e-3));
				Test->TestTrue(TEXT("base change while interior keeps Fog == 0"), S.Fog == 0.0);
				Test->TestTrue(TEXT("still interior"), Tod->IsInterior());
				Tod->ExitInterior(TEXT("t"));
				return Next(EPhase::ExitDone, Now);
			}

			case EPhase::ExitDone:
			{
				if (Elapsed < SettleSeconds)
				{
					return false;
				}
				AGolmokTimeOfDay* Tod = Get();
				if (!Tod)
				{
					return true;
				}
				FGolmokLightingState S;
				Tod->CaptureState(S);
				Test->TestFalse(TEXT("ExitInterior clears the overlay"), Tod->IsInterior());
				Test->TestTrue(TEXT("after exit Fog ~ 0.015 (clear_noon)"), FMath::IsNearlyEqual(S.Fog, 0.015, 1e-4));
				Test->TestTrue(TEXT("NextPreset()"), Tod->NextPreset());
				Test->TestEqual(TEXT("NextPreset after clear_noon is golden_evening"), Tod->CurrentPreset.ToString(), FString(TEXT("golden_evening")));
				Test->AddInfo(FString::Printf(TEXT("end: %s"), *Tod->Describe()));
				return Next(EPhase::Done, Now);
			}

			case EPhase::Done:
				return true;
			}
			return true;
		}

	private:
		AGolmokTimeOfDay* Get()
		{
			if (!TimeOfDay.IsValid())
			{
				Test->AddError(FString::Printf(TEXT("AGolmokTimeOfDay disappeared (phase %d)"), static_cast<int32>(Phase)));
				return nullptr;
			}
			return TimeOfDay.Get();
		}

		bool Next(EPhase NextPhase, double Now)
		{
			Phase = NextPhase;
			PhaseStart = Now;
			return false;
		}

		/** Keeps waiting until Timeout, then records the error and stops. */
		bool Fail(const TCHAR* What, double Timeout, double Elapsed = 0.0)
		{
			if (Elapsed < Timeout)
			{
				return false;
			}
			Test->AddError(FString::Printf(TEXT("%s (phase %d, %.1f s)"), What, static_cast<int32>(Phase), Elapsed));
			return true;
		}

		FAutomationTestBase* Test;
		double CreatedAt;
		EPhase Phase = EPhase::Start;
		double PhaseStart = -1.0;
		TWeakObjectPtr<AGolmokTimeOfDay> TimeOfDay;
		double NightPitch = 0.0;
	};

	// ---- Golmok.Lighting.Clock (WP-14a) ------------------------------------------------------------------------

	/** Expected base values at a time: the design section 3 formula written out here (not EvaluateClock()). */
	struct FExpected
	{
		double Pitch = 0.0;
		double Yaw = 0.0;
		double Lux = 0.0;
		double Kelvin = 0.0;
		double Sky = 0.0;
		double Fog = 0.0;
		double FogHeightFalloff = 0.0;
		double ExposureBias = 0.0;
		bool bVolumetric = false;
	};

	FExpected ExpectedBetween(const FGolmokLightingPreset& A, const FGolmokLightingPreset& B, double Alpha)
	{
		auto L = [Alpha](double X, double Y) { return X + (Y - X) * Alpha; };
		double D = FMath::Fmod(B.YawDeg - A.YawDeg, 360.0);
		D = D > 180.0 ? D - 360.0 : (D <= -180.0 ? D + 360.0 : D);
		FExpected E;
		E.Pitch = L(A.PitchDeg, B.PitchDeg);
		E.Yaw = A.YawDeg + D * Alpha;
		E.Lux = L(A.Lux, B.Lux);
		E.Kelvin = L(A.Kelvin, B.Kelvin);
		E.Sky = L(A.Sky, B.Sky);
		E.Fog = L(A.Fog, B.Fog);
		E.FogHeightFalloff = L(A.FogHeightFalloff, B.FogHeightFalloff);
		E.ExposureBias = L(A.ExposureBias, B.ExposureBias);
		E.bVolumetric = Alpha < 0.5 ? A.bVolumetric : B.bVolumetric;
		return E;
	}

	enum class EClockPhase : uint8
	{
		Start,
		ClockRunning,
		FixedStopped,
		NightDone,
		InteriorDone,
		ExitDone,
		Done,
	};

	class FClockScenario : public IAutomationLatentCommand
	{
	public:
		explicit FClockScenario(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

		virtual ~FClockScenario() override
		{
			if (AGolmokTimeOfDay* Tod = TimeOfDay.Get())
			{
				Tod->OnPresetChanged.Remove(PresetHandle);
				Tod->OnNightChanged.Remove(NightHandle);
			}
		}

		virtual bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			if (!World)
			{
				return Fail(TEXT("PIE world not running"), 60.0, FPlatformTime::Seconds() - CreatedAt);
			}
			const double Now = World->GetTimeSeconds();
			if (PhaseStart < 0.0)
			{
				PhaseStart = Now;
			}
			const double Elapsed = Now - PhaseStart;

			switch (Phase)
			{
			case EClockPhase::Start:
			{
				if (Elapsed < 0.5)
				{
					return false; // let the level actors finish BeginPlay
				}
				TimeOfDay = AGolmokTimeOfDay::FindOrSpawn(World);
				AGolmokTimeOfDay* Tod = TimeOfDay.Get();
				if (!Tod || !Tod->EnsurePresets() || Tod->GetCycle().Num() != 4 || Tod->GetCycleTimes().Num() != 4)
				{
					Test->AddError(TEXT("AGolmokTimeOfDay with 4 keyframes not available in the PIE world"));
					return true;
				}
				Tod->TransitionSeconds = ShortTransition;
				Tod->RealtimeOffsetMinutes = 0.f;
				Tod->ClockMinutesPerRealSecond = 0.5f;
				Test->TestTrue(TEXT("SetClockMode(Fixed)"), Tod->SetClockMode(EGolmokClockMode::Fixed));
				PresetHandle = Tod->OnPresetChanged.AddLambda(
					[this](FName Name, bool bInstant)
					{
						++PresetEvents;
						LastPreset = Name;
						bLastInstant = bInstant;
						// R51-5: what a subscriber sees inside the callback.
						bNightAtPresetEvent = TimeOfDay.IsValid() && TimeOfDay->IsNight();
						NightEventsAtPresetEvent = NightEvents;
					});
				NightHandle = Tod->OnNightChanged.AddLambda([this](bool bValue) { ++NightEvents; bLastNight = bValue; });
				for (const FName& Name : Tod->GetCycle())
				{
					Tod->FindPreset(Name, Keys.Add(Name));
				}
				const FGolmokLightingPreset& Morning = Keys[TEXT("overcast_morning")];
				const FGolmokLightingPreset& Noon = Keys[TEXT("clear_noon")];
				const FGolmokLightingPreset& Evening = Keys[TEXT("golden_evening")];
				const FGolmokLightingPreset& Night = Keys[TEXT("night")];

				// 1. Keyframe time == preset.
				for (int32 i = 0; i < 4; ++i)
				{
					const FName Name = Tod->GetCycle()[i];
					const double T = Tod->GetCycleTimes()[i];
					Test->TestTrue(*FString::Printf(TEXT("SetTimeOfDay(%g) instant"), T), Tod->SetTimeOfDay(static_cast<float>(T), /*bInstant*/ true));
					Test->TestEqual(*FString::Printf(TEXT("CurrentPreset at %g"), T), Tod->CurrentPreset.ToString(), Name.ToString());
					Test->TestTrue(*FString::Printf(TEXT("time == %g"), T), FMath::IsNearlyEqual(static_cast<double>(Tod->GetTimeOfDayMinutes()), T, 1e-3));
					CheckState(*Tod, ExpectedBetween(Keys[Name], Keys[Name], 0.0), *FString::Printf(TEXT("keyframe %s"), *Name.ToString()));
				}

				// 2. Between keyframes: 09:00 = 0.3 of 07:30 -> 12:30.
				Tod->SetTimeOfDay(540.f, true);
				CheckState(*Tod, ExpectedBetween(Morning, Noon, 0.3), TEXT("09:00"));
				Test->TestEqual(TEXT("09:00 nearest overcast_morning"), Tod->CurrentPreset.ToString(), FString(TEXT("overcast_morning")));
				Test->TestFalse(TEXT("instant SetTimeOfDay leaves no transition"), Tod->IsTransitioning());

				// 3. Midnight lies inside the night hold (design 2a): night 21:30 is held 480 min to 05:30, then a 120 min
				//    ramp reaches overcast_morning at 07:30.
				Test->TestTrue(TEXT("night hold_minutes == 480"), Night.bHasHold && Night.HoldMinutes == 480.0);
				Test->TestTrue(TEXT("overcast_morning has no hold"), !Morning.bHasHold && Morning.HoldMinutes == 0.0);
				Tod->SetTimeOfDay(30.f, true);
				CheckState(*Tod, ExpectedBetween(Night, Night, 0.0), TEXT("00:30 (night hold)"));
				Test->TestEqual(TEXT("00:30 nearest night"), Tod->CurrentPreset.ToString(), FString(TEXT("night")));
				Test->TestTrue(TEXT("00:30 inside the hold is night"), Tod->IsNight());
				Tod->SetTimeOfDay(1380.f, true);
				CheckState(*Tod, ExpectedBetween(Night, Night, 0.0), TEXT("23:00 (night hold)"));
				Tod->SetTimeOfDay(390.f, true);
				CheckState(*Tod, ExpectedBetween(Night, Morning, 0.5), TEXT("06:30 (ramp midpoint)"));
				Test->TestEqual(TEXT("06:30 nearest overcast_morning (ramp midpoint)"), Tod->CurrentPreset.ToString(), FString(TEXT("overcast_morning")));

				// 4. Shortest arc: golden_evening 265 -> night 0 passes 312.5 at the midpoint (19:45), volumetric = next.
				ResetEvents();
				Tod->SetTimeOfDay(1185.f, true);
				CheckState(*Tod, ExpectedBetween(Evening, Night, 0.5), TEXT("19:45"));
				Test->TestEqual(TEXT("19:45 nearest night (midpoint)"), Tod->CurrentPreset.ToString(), FString(TEXT("night")));
				// R51-5: the switch to the night keyframe at 19:45 is not night yet (lux 2.0): IsNight() false inside the callback.
				Test->TestEqual(TEXT("19:45 night switch: OnPresetChanged once"), PresetEvents, 1);
				Test->TestEqual(TEXT("... to night"), LastPreset.ToString(), FString(TEXT("night")));
				Test->TestFalse(TEXT("... IsNight() inside the callback is false at 19:45 (lux 2.0)"), bNightAtPresetEvent);

				// 4b. R51-5 contract: a jump that changes the keyframe and the night state together (18:00 day -> 23:00 in
				//     the night hold, with a transition). Inside OnPresetChanged IsNight() is already the target's (true)
				//     while the transition has only started; OnNightChanged comes after OnPresetChanged.
				Tod->SetTimeOfDay(1080.f, true);
				Test->TestFalse(TEXT("18:00 is not night"), Tod->IsNight());
				ResetEvents();
				Tod->SetTimeOfDay(1380.f, /*bInstant*/ false);
				Test->TestTrue(TEXT("18:00 -> 23:00 jump is a transition"), Tod->IsTransitioning());
				Test->TestEqual(TEXT("18:00 -> 23:00: OnPresetChanged once"), PresetEvents, 1);
				Test->TestEqual(TEXT("... to night"), LastPreset.ToString(), FString(TEXT("night")));
				Test->TestTrue(TEXT("... IsNight() inside the callback is already the target's (true)"), bNightAtPresetEvent);
				Test->TestEqual(TEXT("... OnNightChanged had not fired yet inside OnPresetChanged"), NightEventsAtPresetEvent, 0);
				Test->TestEqual(TEXT("... OnNightChanged(true) once, after it"), NightEvents, 1);
				Test->TestTrue(TEXT("... IsNight() is the target's from the start of the jump"), bLastNight && Tod->IsNight());

				// 5. ApplyPreset / NextPreset move the clock to the keyframe.
				Test->TestTrue(TEXT("ApplyPreset(golden_evening, instant)"), Tod->ApplyPreset(TEXT("golden_evening"), true));
				Test->TestTrue(TEXT("ApplyPreset sets 18:00"), FMath::IsNearlyEqual(static_cast<double>(Tod->GetTimeOfDayMinutes()), 1080.0, 1e-3));
				CheckState(*Tod, ExpectedBetween(Evening, Evening, 0.0), TEXT("ApplyPreset golden_evening"));
				Test->TestTrue(TEXT("NextPreset()"), Tod->NextPreset());
				Test->TestTrue(TEXT("NextPreset sets 21:30"), FMath::IsNearlyEqual(static_cast<double>(Tod->GetTimeOfDayMinutes()), 1290.0, 1e-3));
				// R51-4: on the clock NextPreset() goes to the next keyframe in time: at 10:01 (nearest clear_noon) that is
				//        clear_noon 12:30, not golden_evening (the cycle successor of the nearest keyframe).
				Tod->SetTimeOfDay(601.f, true);
				Test->TestEqual(TEXT("10:01 nearest clear_noon"), Tod->CurrentPreset.ToString(), FString(TEXT("clear_noon")));
				Test->TestTrue(TEXT("NextPreset() at 10:01"), Tod->NextPreset());
				Test->TestEqual(TEXT("NextPreset at 10:01 -> clear_noon (not golden_evening)"), Tod->CurrentPreset.ToString(), FString(TEXT("clear_noon")));
				Test->TestTrue(TEXT("NextPreset at 10:01 sets 12:30"), FMath::IsNearlyEqual(static_cast<double>(Tod->GetTimeOfDayMinutes()), 750.0, 1e-3));
				Tod->ApplyPreset(TEXT("clear_noon"), true);
				Test->TestTrue(TEXT("ApplyPreset sets 12:30"), FMath::IsNearlyEqual(static_cast<double>(Tod->GetTimeOfDayMinutes()), 750.0, 1e-3));

				// 6. Clock mode: OnPresetChanged exactly once at the 10:00 midpoint, with bInstant false.
				Test->TestTrue(TEXT("SetClockMode(Clock)"), Tod->SetClockMode(EGolmokClockMode::Clock));
				Test->TestTrue(TEXT("clock mode ticks"), Tod->GetClockMode() == EGolmokClockMode::Clock && Tod->IsActorTickEnabled());
				Tod->ClockMinutesPerRealSecond = 1.f;
				Tod->SetTimeOfDay(599.f, true);
				ResetEvents();
				Tod->AdvanceClock(0.5); // 09:59.5
				Test->TestEqual(TEXT("no event before the midpoint"), PresetEvents, 0);
				Tod->AdvanceClock(1.0); // 10:00.5
				Tod->AdvanceClock(1.0); // 10:01.5
				Test->TestEqual(TEXT("OnPresetChanged exactly once across the midpoint"), PresetEvents, 1);
				Test->TestEqual(TEXT("... with the next keyframe"), LastPreset.ToString(), FString(TEXT("clear_noon")));
				Test->TestFalse(TEXT("... and bInstant false (clock progression)"), bLastInstant);
				Test->TestEqual(TEXT("CurrentPreset follows the nearest keyframe"), Tod->CurrentPreset.ToString(), FString(TEXT("clear_noon")));
				CheckState(*Tod, ExpectedBetween(Morning, Noon, 151.5 / 300.0), TEXT("clock 10:01.5"));

				// 7. OnNightChanged at lux < 0.1 (golden_evening -> night: after 21:24:45), kept through the night hold,
				//    and back on the ramp after 05:34:48 (lux 2.5 x alpha >= 0.1).
				Tod->SetTimeOfDay(1284.f, true);
				Test->TestFalse(TEXT("21:24 is not night yet (lux 0.114)"), Tod->IsNight());
				ResetEvents();
				Tod->AdvanceClock(1.0); // 21:25, lux 0.095
				Test->TestEqual(TEXT("OnNightChanged once"), NightEvents, 1);
				Test->TestTrue(TEXT("OnNightChanged(true)"), bLastNight && Tod->IsNight());
				Test->TestEqual(TEXT("no preset event inside the night span"), PresetEvents, 0);
				if (UDirectionalLightComponent* SunLight = SunComponent(World))
				{
					Test->TestTrue(TEXT("sun visible at lux 0.095 (> 0.01)"), SunLight->GetVisibleFlag());
					Tod->SetTimeOfDay(1289.9f, true); // lux 0.0019
					Test->TestFalse(TEXT("sun hidden at lux 0.0019 on the clock (<= 0.01)"), SunLight->GetVisibleFlag());
				}
				Tod->SetTimeOfDay(1320.f, true); // 22:00 inside the night hold, lux 0
				Test->TestEqual(TEXT("22:00 inside the hold: no OnNightChanged"), NightEvents, 1);
				Test->TestTrue(TEXT("22:00 inside the hold is night"), Tod->IsNight());
				if (UDirectionalLightComponent* SunLight = SunComponent(World))
				{
					Test->TestFalse(TEXT("sun hidden inside the night hold"), SunLight->GetVisibleFlag());
				}
				Tod->SetTimeOfDay(340.f, true); // 05:40 on the ramp, lux 0.208
				Test->TestEqual(TEXT("OnNightChanged again"), NightEvents, 2);
				Test->TestFalse(TEXT("OnNightChanged(false)"), bLastNight || Tod->IsNight());
				Test->TestEqual(TEXT("05:40 nearest night (before the 06:30 ramp midpoint)"), Tod->CurrentPreset.ToString(), FString(TEXT("night")));

				// 7b. Night hold on the running clock (design 2a): no OnPresetChanged at 02:30 (the old midpoint of the
				//     whole span) or at the hold end 05:30; exactly one, to overcast_morning, at the ramp midpoint 06:30.
				Tod->ClockMinutesPerRealSecond = 1.f;
				Tod->SetTimeOfDay(149.f, true); // 02:29
				ResetEvents();
				Tod->AdvanceClock(2.0); // 02:31
				Test->TestEqual(TEXT("no OnPresetChanged at 02:30 inside the hold"), PresetEvents, 0);
				CheckState(*Tod, ExpectedBetween(Night, Night, 0.0), TEXT("clock 02:31 (night hold)"));
				Test->TestTrue(TEXT("02:31 inside the hold is night"), Tod->IsNight() && Tod->CurrentPreset == FName(TEXT("night")));
				Tod->SetTimeOfDay(329.f, true); // 05:29
				Tod->AdvanceClock(0.5); // 05:29.5, still held
				CheckState(*Tod, ExpectedBetween(Night, Night, 0.0), TEXT("clock 05:29.5 (night hold)"));
				Tod->AdvanceClock(1.0); // 05:30.5, the ramp has started
				CheckState(*Tod, ExpectedBetween(Night, Morning, 0.5 / 120.0), TEXT("clock 05:30.5 (ramp start)"));
				Test->TestEqual(TEXT("no OnPresetChanged at the hold end"), PresetEvents, 0);
				Tod->SetTimeOfDay(389.f, true); // 06:29
				Tod->AdvanceClock(0.5); // 06:29.5
				Test->TestEqual(TEXT("no OnPresetChanged before the ramp midpoint"), PresetEvents, 0);
				Tod->AdvanceClock(1.0); // 06:30.5
				Tod->AdvanceClock(1.0); // 06:31.5
				Test->TestEqual(TEXT("OnPresetChanged exactly once across the ramp midpoint"), PresetEvents, 1);
				Test->TestEqual(TEXT("... to overcast_morning"), LastPreset.ToString(), FString(TEXT("overcast_morning")));
				Test->TestFalse(TEXT("... with bInstant false"), bLastInstant);
				Test->TestFalse(TEXT("... IsNight() inside the callback is false at 06:30 (lux 1.26 on the ramp, R51-5)"), bNightAtPresetEvent);
				CheckState(*Tod, ExpectedBetween(Night, Morning, 61.5 / 120.0), TEXT("clock 06:31.5 (ramp)"));

				// 8. Rate and midnight wrap on the clock.
				Tod->ClockMinutesPerRealSecond = 10.f;
				Tod->SetTimeOfDay(1435.f, true);
				Tod->AdvanceClock(1.0);
				Test->TestTrue(TEXT("rate 10: 23:55 + 1 s -> 00:05"), FMath::IsNearlyEqual(static_cast<double>(Tod->GetTimeOfDayMinutes()), 5.0, 1e-3));
				Test->TestEqual(TEXT("00:05 nearest night"), Tod->CurrentPreset.ToString(), FString(TEXT("night")));

				// 8b. Slow rate at a high frame rate still advances (double accumulator, not float steps near 1440).
				Tod->ClockMinutesPerRealSecond = 1.f / 60.f;
				Tod->SetTimeOfDay(1400.f, true);
				for (int32 Step = 0; Step < 2400; ++Step)
				{
					Tod->AdvanceClock(1.0 / 240.0); // 10 s at 240 fps
				}
				Test->TestTrue(*FString::Printf(TEXT("rate 1/60 at 240 fps: 10 s -> +%.4f min"), static_cast<double>(Tod->GetTimeOfDayMinutes()) - 1400.0),
					FMath::IsNearlyEqual(static_cast<double>(Tod->GetTimeOfDayMinutes()), 1400.0 + 10.0 / 60.0, 1e-3));

				// 9. Realtime jumps (with a transition) to the local time.
				Test->TestTrue(TEXT("SetClockMode(Realtime)"), Tod->SetClockMode(EGolmokClockMode::Realtime));
				const double Local = Tod->RealtimeTargetMinutes();
				Test->TestTrue(TEXT("realtime time == local time"),
					GolmokClockMath::CircularDistance(static_cast<double>(Tod->GetTimeOfDayMinutes()), Local) < 0.1);
				Test->TestTrue(TEXT("realtime re-sync is a transition"), Tod->IsTransitioning());
				Test->AddInfo(FString::Printf(TEXT("realtime:%s"), *Tod->DescribeClock()));
				// An explicit time cannot hold in Realtime: SetTimeOfDay falls back to Fixed (like ApplyPreset).
				Test->TestTrue(TEXT("SetTimeOfDay in realtime"), Tod->SetTimeOfDay(600.f, true));
				Test->TestTrue(TEXT("... switches to Fixed"), Tod->GetClockMode() == EGolmokClockMode::Fixed);
				Test->TestTrue(TEXT("... and keeps 10:00"), FMath::IsNearlyEqual(static_cast<double>(Tod->GetTimeOfDayMinutes()), 600.0, 1e-3));

				// 10. Fixed -> Clock (the SetTimeOfDay above switched Realtime to Fixed) and Realtime -> Clock: both keep the
				//     minutes, neither jumps (R51-11).
				Test->TestTrue(TEXT("SetClockMode(Clock) from fixed"), Tod->SetClockMode(EGolmokClockMode::Clock));
				Test->TestTrue(TEXT("fixed -> clock keeps 10:00"), FMath::IsNearlyEqual(static_cast<double>(Tod->GetTimeOfDayMinutes()), 600.0, 1e-3));
				Test->TestTrue(TEXT("SetClockMode(Realtime) before realtime -> clock"), Tod->SetClockMode(EGolmokClockMode::Realtime));
				const float RealtimeAt = Tod->GetTimeOfDayMinutes();
				ResetEvents();
				Test->TestTrue(TEXT("SetClockMode(Clock) from realtime"), Tod->SetClockMode(EGolmokClockMode::Clock));
				Test->TestTrue(TEXT("realtime -> clock is clock mode"), Tod->GetClockMode() == EGolmokClockMode::Clock);
				Test->TestEqual(TEXT("realtime -> clock keeps the minutes (no jump)"), Tod->GetTimeOfDayMinutes(), RealtimeAt);
				Test->TestEqual(TEXT("realtime -> clock: no OnPresetChanged (no jump)"), PresetEvents, 0);

				// 11. Clock at 60 min/s on real ticks.
				Tod->ClockMinutesPerRealSecond = 60.f;
				ClockStart = Tod->GetTimeOfDayMinutes();
				return Next(EClockPhase::ClockRunning, Now);
			}

			case EClockPhase::ClockRunning:
			{
				if (Elapsed < SettleSeconds)
				{
					return false;
				}
				AGolmokTimeOfDay* Tod = Get();
				if (!Tod)
				{
					return true;
				}
				const double Moved = GolmokClockMath::WrapMinutes(static_cast<double>(Tod->GetTimeOfDayMinutes()) - ClockStart);
				const double Expected = Elapsed * 60.0;
				Test->AddInfo(FString::Printf(TEXT("clock moved %.2f min in %.2f s (rate 60)"), Moved, Elapsed));
				Test->TestTrue(TEXT("the clock runs on world time"), Moved > 0.5 * Expected && Moved < 1.5 * Expected + 2.0);
				Test->TestTrue(TEXT("SetClockMode(Fixed)"), Tod->SetClockMode(EGolmokClockMode::Fixed));
				FixedAt = Tod->GetTimeOfDayMinutes();
				return Next(EClockPhase::FixedStopped, Now);
			}

			case EClockPhase::FixedStopped:
			{
				if (Elapsed < SettleSeconds)
				{
					return false;
				}
				AGolmokTimeOfDay* Tod = Get();
				if (!Tod)
				{
					return true;
				}
				Test->TestEqual(TEXT("Fixed stops the clock"), Tod->GetTimeOfDayMinutes(), FixedAt);
				Test->TestFalse(TEXT("Fixed: no tick without a transition"), Tod->IsActorTickEnabled());

				// Fixed mode: the PresetApply sequence gives the WP-05 values.
				Test->TestTrue(TEXT("Fixed ApplyPreset(clear_noon, instant)"), Tod->ApplyPreset(TEXT("clear_noon"), true));
				FGolmokLightingState S;
				Tod->CaptureState(S);
				Test->TestTrue(TEXT("Fixed clear_noon Lux ~ 10"), FMath::IsNearlyEqual(S.Lux, 10.0, 1e-3));
				Test->TestTrue(TEXT("Fixed clear_noon Kelvin ~ 5600"), FMath::IsNearlyEqual(S.Kelvin, 5600.0, 1e-2));
				Test->TestTrue(TEXT("Fixed clear_noon Fog ~ 0.015"), FMath::IsNearlyEqual(S.Fog, 0.015, 1e-4));
				Test->TestTrue(TEXT("Fixed clear_noon ExposureBias ~ 0"), FMath::IsNearlyEqual(S.ExposureBias, 0.0, 1e-4));
				Test->TestTrue(TEXT("Fixed clear_noon SunRotation.Pitch ~ -62"), FMath::IsNearlyEqual(S.SunRotation.Pitch, -62.0, 1e-2));
				Test->TestFalse(TEXT("Fixed instant apply leaves no transition"), Tod->IsTransitioning());
				Test->TestFalse(TEXT("Fixed instant apply leaves no tick"), Tod->IsActorTickEnabled());
				Test->TestTrue(TEXT("Fixed ApplyPreset(night)"), Tod->ApplyPreset(TEXT("night")));
				Test->TestTrue(TEXT("Fixed night transition ticks"), Tod->IsTransitioning() && Tod->IsActorTickEnabled());
				return Next(EClockPhase::NightDone, Now);
			}

			case EClockPhase::NightDone:
			{
				if (Elapsed < SettleSeconds)
				{
					return false;
				}
				AGolmokTimeOfDay* Tod = Get();
				if (!Tod)
				{
					return true;
				}
				FGolmokLightingState S;
				Tod->CaptureState(S);
				Test->TestTrue(TEXT("Fixed night Lux == 0"), S.Lux == 0.0);
				Test->TestTrue(TEXT("Fixed night bVolumetric"), S.bVolumetric);
				Test->TestFalse(TEXT("Fixed night: tick disabled after the transition"), Tod->IsActorTickEnabled());
				Test->TestTrue(TEXT("Fixed night time 21:30"), FMath::IsNearlyEqual(static_cast<double>(Tod->GetTimeOfDayMinutes()), 1290.0, 1e-3));
				if (UDirectionalLightComponent* SunLight = SunComponent(World))
				{
					Test->TestFalse(TEXT("Fixed night: sun hidden"), SunLight->GetVisibleFlag());
				}
				// Interior overlay on a time between keyframes (Fixed): exit returns to the 09:00 clock state.
				Tod->SetTimeOfDay(540.f, true);
				Tod->EnterInterior(TEXT("t"));
				return Next(EClockPhase::InteriorDone, Now);
			}

			case EClockPhase::InteriorDone:
			{
				if (Elapsed < SettleSeconds)
				{
					return false;
				}
				AGolmokTimeOfDay* Tod = Get();
				if (!Tod)
				{
					return true;
				}
				FGolmokLightingState S;
				Tod->CaptureState(S);
				const FExpected E = ExpectedBetween(Keys[TEXT("overcast_morning")], Keys[TEXT("clear_noon")], 0.3);
				Test->TestTrue(TEXT("interior Fog == 0"), S.Fog == 0.0);
				Test->TestTrue(TEXT("interior ExposureBias == 1"), FMath::IsNearlyEqual(S.ExposureBias, 1.0, 1e-4));
				Test->TestTrue(TEXT("interior keeps the 09:00 sun"), FMath::IsNearlyEqual(S.Lux, E.Lux, 1e-3));
				Tod->ExitInterior(TEXT("t"));
				return Next(EClockPhase::ExitDone, Now);
			}

			case EClockPhase::ExitDone:
			{
				if (Elapsed < SettleSeconds)
				{
					return false;
				}
				AGolmokTimeOfDay* Tod = Get();
				if (!Tod)
				{
					return true;
				}
				Test->TestFalse(TEXT("ExitInterior clears the overlay"), Tod->IsInterior());
				CheckState(*Tod, ExpectedBetween(Keys[TEXT("overcast_morning")], Keys[TEXT("clear_noon")], 0.3), TEXT("after exit (09:00, not overcast_morning)"));
				Test->TestTrue(TEXT("time still 09:00"), FMath::IsNearlyEqual(static_cast<double>(Tod->GetTimeOfDayMinutes()), 540.0, 1e-3));
				Test->AddInfo(FString::Printf(TEXT("end: %s%s"), *Tod->Describe(), *Tod->DescribeClock()));
				return Next(EClockPhase::Done, Now);
			}

			case EClockPhase::Done:
				return true;
			}
			return true;
		}

	private:
		void CheckState(const AGolmokTimeOfDay& Tod, const FExpected& E, const TCHAR* What)
		{
			FGolmokLightingState S;
			if (!Test->TestTrue(*FString::Printf(TEXT("%s: CaptureState"), What), Tod.CaptureState(S)))
			{
				return;
			}
			const FRotator Rotation(E.Pitch, E.Yaw, 0.0);
			Test->TestTrue(*FString::Printf(TEXT("%s: sun rotation %s == %s"), What, *S.SunRotation.ToString(), *Rotation.ToString()),
				S.SunRotation.Equals(Rotation, 0.01));
			Test->TestTrue(*FString::Printf(TEXT("%s: Lux %g ~ %g"), What, S.Lux, E.Lux), FMath::IsNearlyEqual(S.Lux, E.Lux, 1e-3));
			Test->TestTrue(*FString::Printf(TEXT("%s: Kelvin %g ~ %g"), What, S.Kelvin, E.Kelvin), FMath::IsNearlyEqual(S.Kelvin, E.Kelvin, 1e-2));
			Test->TestTrue(*FString::Printf(TEXT("%s: Sky %g ~ %g"), What, S.Sky, E.Sky), FMath::IsNearlyEqual(S.Sky, E.Sky, 1e-4));
			Test->TestTrue(*FString::Printf(TEXT("%s: Fog %g ~ %g"), What, S.Fog, E.Fog), FMath::IsNearlyEqual(S.Fog, E.Fog, 1e-5));
			Test->TestTrue(*FString::Printf(TEXT("%s: FogHeightFalloff %g ~ %g"), What, S.FogHeightFalloff, E.FogHeightFalloff),
				FMath::IsNearlyEqual(S.FogHeightFalloff, E.FogHeightFalloff, 1e-5));
			Test->TestTrue(*FString::Printf(TEXT("%s: ExposureBias %g ~ %g"), What, S.ExposureBias, E.ExposureBias),
				FMath::IsNearlyEqual(S.ExposureBias, E.ExposureBias, 1e-4));
			Test->TestTrue(*FString::Printf(TEXT("%s: volumetric %d == %d"), What, S.bVolumetric ? 1 : 0, E.bVolumetric ? 1 : 0), S.bVolumetric == E.bVolumetric);
		}

		void ResetEvents()
		{
			PresetEvents = 0;
			NightEvents = 0;
			LastPreset = NAME_None;
			bNightAtPresetEvent = false;
			NightEventsAtPresetEvent = -1;
		}

		AGolmokTimeOfDay* Get()
		{
			if (!TimeOfDay.IsValid())
			{
				Test->AddError(FString::Printf(TEXT("AGolmokTimeOfDay disappeared (phase %d)"), static_cast<int32>(Phase)));
				return nullptr;
			}
			return TimeOfDay.Get();
		}

		bool Next(EClockPhase NextPhase, double Now)
		{
			Phase = NextPhase;
			PhaseStart = Now;
			return false;
		}

		bool Fail(const TCHAR* What, double Timeout, double Elapsed = 0.0)
		{
			if (Elapsed < Timeout)
			{
				return false;
			}
			Test->AddError(FString::Printf(TEXT("%s (phase %d, %.1f s)"), What, static_cast<int32>(Phase), Elapsed));
			return true;
		}

		FAutomationTestBase* Test;
		double CreatedAt;
		EClockPhase Phase = EClockPhase::Start;
		double PhaseStart = -1.0;
		TWeakObjectPtr<AGolmokTimeOfDay> TimeOfDay;
		TMap<FName, FGolmokLightingPreset> Keys;
		FDelegateHandle PresetHandle;
		FDelegateHandle NightHandle;
		int32 PresetEvents = 0;
		int32 NightEvents = 0;
		FName LastPreset;
		bool bLastInstant = true;
		bool bLastNight = false;
		/** R51-5: IsNight() and the OnNightChanged count seen inside the last OnPresetChanged callback. */
		bool bNightAtPresetEvent = false;
		int32 NightEventsAtPresetEvent = -1;
		double ClockStart = 0.0;
		float FixedAt = 0.f;
	};
} // namespace GolmokLightingTest

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokLightingPresetsFileTest, "Golmok.Lighting.PresetsFile",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokLightingPresetsFileTest::RunTest(const FString& Parameters)
{
	using namespace GolmokLightingTest;

	const FString Path = FPaths::Combine(FPaths::ProjectConfigDir(), TEXT("Golmok"), TEXT("lighting_presets.json"));
	TArray<FGolmokLightingPreset> Presets;
	TArray<FName> Cycle;
	FString Error;
	if (!AGolmokTimeOfDay::LoadPresetsFile(Path, Presets, Cycle, Error))
	{
		AddError(FString::Printf(TEXT("LoadPresetsFile(%s) failed: %s"), *Path, *Error));
		return false;
	}
	TestEqual(TEXT("5 presets"), Presets.Num(), 5);
	TestEqual(TEXT("4 cycle presets"), Cycle.Num(), 4);
	if (Cycle.Num() == 4)
	{
		TestEqual(TEXT("cycle[0]"), Cycle[0].ToString(), FString(TEXT("overcast_morning")));
		TestEqual(TEXT("cycle[3]"), Cycle[3].ToString(), FString(TEXT("night")));
		const double Times[] = {450.0, 750.0, 1080.0, 1290.0}; // 07:30 12:30 18:00 21:30
		const double Holds[] = {0.0, 0.0, 0.0, 480.0}; // design 2a: night held 21:30 -> 05:30
		for (int32 i = 0; i < 4; ++i)
		{
			const FGolmokLightingPreset* P = FindPreset(Presets, *Cycle[i].ToString());
			TestTrue(FString::Printf(TEXT("%s has a keyframe time"), *Cycle[i].ToString()), P && P->bHasTime);
			TestTrue(FString::Printf(TEXT("%s time == %g"), *Cycle[i].ToString(), Times[i]), P && P->TimeMinutes == Times[i]);
			TestTrue(FString::Printf(TEXT("%s hold_minutes == %g"), *Cycle[i].ToString(), Holds[i]),
				P && P->HoldMinutes == Holds[i] && P->bHasHold == (Holds[i] > 0.0));
		}
	}
	if (const FGolmokLightingPreset* Morning = FindPreset(Presets, TEXT("overcast_morning")))
	{
		TestTrue(TEXT("overcast_morning.Lux == 2.5"), FMath::IsNearlyEqual(Morning->Lux, 2.5, 1e-9));
		TestTrue(TEXT("overcast_morning.IsComplete()"), Morning->IsComplete());
	}
	else
	{
		AddError(TEXT("preset overcast_morning missing"));
	}
	if (const FGolmokLightingPreset* Interior = FindPreset(Presets, TEXT("interior")))
	{
		TestFalse(TEXT("interior.bHasSun == false (partial overlay)"), Interior->bHasSun);
		TestTrue(TEXT("interior.bHasFog"), Interior->bHasFog);
		TestTrue(TEXT("interior.Fog == 0"), Interior->Fog == 0.0);
		TestFalse(TEXT("interior is not complete"), Interior->IsComplete());
		TestFalse(TEXT("interior has no keyframe time"), Interior->bHasTime);
		TestFalse(TEXT("interior has no hold"), Interior->bHasHold);
	}
	else
	{
		AddError(TEXT("preset interior missing"));
	}

	// Broken inputs fail with a non-empty error.
	TArray<FGolmokLightingPreset> Bad;
	TArray<FName> BadCycle;
	FString BadError;
	TestFalse(TEXT("truncated text fails"), AGolmokTimeOfDay::ParsePresetsText(TEXT("{\"schema_version\": 2, \"cycle\": ["), Bad, BadCycle, BadError));
	TestFalse(TEXT("truncated text has an error message"), BadError.IsEmpty());
	// WP-14a: schema 2 (keyframe "time" on the cycle presets); a schema 1 file is an error.
	TestTrue(TEXT("synthetic text with schema_version 2 parses"), AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.0")), Bad, BadCycle, BadError));
	TestFalse(TEXT("schema_version 1 fails"), AGolmokTimeOfDay::ParsePresetsText(MakeJson(1, TEXT("0.0")), Bad, BadCycle, BadError));
	TestTrue(TEXT("schema_version 1 error names the key"), BadError.Contains(TEXT("schema_version")));
	TestFalse(TEXT("interior.fog 0.1 fails"), AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.1")), Bad, BadCycle, BadError));
	TestTrue(TEXT("interior.fog error names preset and key"), BadError.Contains(TEXT("interior")) && BadError.Contains(TEXT("fog")));
	TestFalse(TEXT("time 12:60 fails"), AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.0"), TEXT("12:60")), Bad, BadCycle, BadError));
	TestTrue(TEXT("time format error names preset and key"), BadError.Contains(TEXT("preset b")) && BadError.Contains(TEXT("time")));
	TestFalse(TEXT("missing time fails"), AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.0"), TEXT("")), Bad, BadCycle, BadError));
	TestTrue(TEXT("missing time error names preset and key"), BadError.Contains(TEXT("preset b")) && BadError.Contains(TEXT("'time'")));
	TestFalse(TEXT("duplicate time fails"), AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.0"), TEXT("07:30")), Bad, BadCycle, BadError));
	TestTrue(TEXT("duplicate time error"), BadError.Contains(TEXT("duplicate time 07:30")));
	TestFalse(TEXT("reverse time fails"), AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.0"), TEXT("19:00")), Bad, BadCycle, BadError));
	TestTrue(TEXT("reverse time error"), BadError.Contains(TEXT("must increase")) && BadError.Contains(TEXT("c 18:00")));
	TestFalse(TEXT("interior time fails"),
		AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.0"), TEXT("12:30"), TEXT("\"time\": \"12:00\", ")), Bad, BadCycle, BadError));
	TestTrue(TEXT("interior time error names preset and key"), BadError.Contains(TEXT("preset interior")) && BadError.Contains(TEXT("time")));
	// WP-14a design 2a: hold_minutes on a cycle keyframe ends strictly before the next keyframe (d wraps to a at 07:30).
	TestTrue(TEXT("d hold 599 (to 07:29) parses"),
		AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.0"), TEXT("12:30"), TEXT(""), TEXT("\"hold_minutes\": 599, ")), Bad, BadCycle, BadError));
	const FGolmokLightingPreset* HeldD = FindPreset(Bad, TEXT("d"));
	TestTrue(TEXT("d hold 599 is read"), HeldD && HeldD->bHasHold && HeldD->HoldMinutes == 599.0);
	TestFalse(TEXT("d hold 600 (to a 07:30) fails"),
		AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.0"), TEXT("12:30"), TEXT(""), TEXT("\"hold_minutes\": 600, ")), Bad, BadCycle, BadError));
	TestTrue(FString::Printf(TEXT("hold overlap error names preset, key and next keyframe: %s"), *BadError),
		BadError.Contains(TEXT("preset d")) && BadError.Contains(TEXT("hold_minutes 600 runs to 07:30")) && BadError.Contains(TEXT("next keyframe a 07:30")));
	TestFalse(TEXT("negative hold fails"),
		AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.0"), TEXT("12:30"), TEXT(""), TEXT("\"hold_minutes\": -1, ")), Bad, BadCycle, BadError));
	TestTrue(TEXT("negative hold error names preset and key"), BadError.Contains(TEXT("preset d")) && BadError.Contains(TEXT("hold_minutes")));
	TestFalse(TEXT("non-finite hold (1e999) fails"),
		AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.0"), TEXT("12:30"), TEXT(""), TEXT("\"hold_minutes\": 1e999, ")), Bad, BadCycle, BadError));
	TestFalse(TEXT("non-finite hold has an error message"), BadError.IsEmpty());
	TestFalse(TEXT("string hold fails"),
		AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.0"), TEXT("12:30"), TEXT(""), TEXT("\"hold_minutes\": \"480\", ")), Bad, BadCycle, BadError));
	TestTrue(TEXT("string hold error"), BadError.Contains(TEXT("preset d")) && BadError.Contains(TEXT("hold_minutes must be a number")));
	TestFalse(TEXT("interior hold fails"),
		AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.0"), TEXT("12:30"), TEXT("\"hold_minutes\": 10, ")), Bad, BadCycle, BadError));
	TestTrue(TEXT("interior hold error names preset and key"),
		BadError.Contains(TEXT("preset interior")) && BadError.Contains(TEXT("hold_minutes is only allowed on cycle presets")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokLightingPresetApplyTest, "Golmok.Lighting.PresetApply",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokLightingPresetApplyTest::RunTest(const FString& Parameters)
{
	using namespace GolmokLightingTest;

	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FPresetApplyScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokLightingClockTest, "Golmok.Lighting.Clock",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokLightingClockTest::RunTest(const FString& Parameters)
{
	using namespace GolmokLightingTest;

	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FClockScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

#endif
