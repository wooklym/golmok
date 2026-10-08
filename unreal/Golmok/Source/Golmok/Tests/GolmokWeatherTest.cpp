// Weather tests (WP-16a design section 14).
//
// Golmok.Weather.Config (no PIE): Config/Golmok/weather.json parses through GolmokWeather::LoadConfigFile with the
// design section 6 values; the error table below (tools/tests/test_ue_config_weather.py ERROR_CASES, same rows and
// order, checked by that test) fails with byte-identical messages; the pure rules of Weather/GolmokWeatherMath.h are
// compiled into the engine build and spot-checked (identity bit-identical, Rain(0.05) ~ overcast, precipitation
// delay boundaries, puddle <= wetness, schedule across midnight). All pass under -nullrhi.
//
// Golmok.Weather.Lighting (L_Dev PIE): the subsystem drives the level's AGolmokTimeOfDay. On the level-lighting base
// rain turns the exposure override on and clear restores the authored flag; each cycle preset x {clear, overcast, rain
// 0.6} applied instantly reads back as GolmokWeatherMath::Apply(the clear preset state), and clear returns to the clear
// state bit for bit; the interior overlay keeps its own fog / bias over the weather-reduced sun and sky; a weather
// transition driven by hand (StepWeather) is the formula at alpha 0.5 and lands on the target; weather never changes
// IsNight() (at a minute whose base lux is just above the night threshold, found in the loaded presets) or fires
// OnPresetChanged / OnNightChanged; Clock (60 min/s) + Schedule fires OnWeatherChanged exactly once at the 15:00 slot
// boundary with its arguments; a weather change during a running time-of-day transition makes the transition end on the
// new composition.
// Golmok.Weather.Runtime (L_Dev PIE): golmok.weather parsing (rain heavy / 0.42 / out of range / instant, an explicit
// state in schedule mode -> fixed), OnWeatherChanged counts and what a subscriber reads inside the callback, the
// precipitation delay (rising: 0 below alpha 0.5, falling: 0 at alpha 0.5), the surface integration table, photo mode
// (GamePause: no progress, changes refused, the transition continues after Exit), the HUD line, the rain fx activity
// rules (interior, fx off, travel reset: the OnTraveled binding plus ResetRainFx() itself, no broadcast) when
// NS_GolmokRain exists and the MPC instance values when MPC_GolmokWeather exists. Without those assets the steps are
// skipped with an Info line ("MPC_GolmokWeather missing - skipped", "NS_GolmokRain missing - skipped"), so both pass
// under -nullrhi on a clone before V-16.
//
// Headless: .\tools\ue\test.ps1 -Filter Golmok.Weather   (or in the editor console: Automation RunTests Golmok.Weather)

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Camera/PlayerCameraManager.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Editor.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "GameFramework/PlayerController.h"
#include "Lighting/GolmokClockMath.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Map/GolmokTravelSubsystem.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Particles/ParticleSystemComponent.h"
#include "Photo/GolmokPhotoModeSubsystem.h"
#include "Tests/AutomationEditorCommon.h"
#include "UObject/SoftObjectPath.h"
#include "Weather/GolmokWeatherConfig.h"
#include "Weather/GolmokWeatherMath.h"
#include "Weather/GolmokWeatherRainFx.h"
#include "Weather/GolmokWeatherSubsystem.h"
#include <cstring>

namespace GolmokWeatherTests
{
	/** One error case: replace Old (exactly one occurrence in the repo file) with New, expect Message. */
	struct FErrorCase
	{
		const TCHAR* Old;
		const TCHAR* New;
		const TCHAR* Message;
	};

	// ---- error table begin (tools/tests/test_ue_config_weather.py ERROR_CASES; keep rows identical) ----
	const FErrorCase ErrorCases[] = {
		{TEXT("\"schema_version\": 1,"), TEXT("\"schema_version\": 1,,"), TEXT("weather.json: root: not a JSON object")},
		{TEXT("\"schema_version\": 1,"), TEXT("\"schema_version\": 2,"), TEXT("weather.json: schema_version: must be 1")},
		{TEXT("\"schema_version\": 1,"), TEXT("\"schema_version\": true,"), TEXT("weather.json: schema_version: must be 1")},
		{TEXT("\"mpc\": \"/Game/"), TEXT("\"snow\": 1, \"mpc\": \"/Game/"), TEXT("weather.json: root: unknown key \"snow\"")},
		{TEXT("\"transition_seconds\": 20.0,"), TEXT(""), TEXT("weather.json: root: missing key \"transition_seconds\"")},
		{TEXT("\"initial\": {\"state\": \"clear\", \"mode\": \"fixed\"}"), TEXT("\"initial\": \"clear\""), TEXT("weather.json: initial: must be an object")},
		{TEXT("{\"state\": \"clear\", \"mode\""), TEXT("{\"state\": \"snow\", \"mode\""), TEXT("weather.json: initial.state: must be clear, overcast or rain")},
		{TEXT("\"initial\": {\"state\": \"clear\""), TEXT("\"initial\": {\"state\": \"rain\""), TEXT("weather.json: initial.intensity: required for rain")},
		{TEXT("{\"state\": \"clear\", \"mode\": \"fixed\"}"), TEXT("{\"state\": \"overcast\", \"mode\": \"fixed\", \"intensity\": 0.5}"), TEXT("weather.json: initial.intensity: only allowed for rain")},
		{TEXT("\"mode\": \"fixed\""), TEXT("\"mode\": \"random\""), TEXT("weather.json: initial.mode: must be fixed or schedule")},
		{TEXT("\"transition_seconds\": 20.0"), TEXT("\"transition_seconds\": 601"), TEXT("weather.json: transition_seconds: must be a number in [0, 600]")},
		{TEXT("\"heavy\": 1.0}"), TEXT("\"heavy\": 1.5}"), TEXT("weather.json: rain_levels.heavy: must be a number in [0.05, 1]")},
		{TEXT("\"moderate\": 0.6"), TEXT("\"moderate\": 0.3"), TEXT("weather.json: rain_levels: must increase strictly (light < moderate < heavy)")},
		{TEXT("\"modifiers\": {"), TEXT("\"modifiers\": {\"clear\": {},"), TEXT("weather.json: modifiers.clear: clear is the identity and must not be listed")},
		{TEXT("\"lux_scale\": 0.3,"), TEXT("\"lux_scale\": 0,"), TEXT("weather.json: modifiers.overcast.lux_scale: must be a number in (0, 2]")},
		{TEXT("\"lux_scale\": 0.12"), TEXT("\"lux_scale\": true"), TEXT("weather.json: modifiers.rain.lux_scale: must be a number in (0, 2]")},
		{TEXT("\"kelvin_target\": 7200.0"), TEXT("\"kelvin_target\": 12000.5"), TEXT("weather.json: modifiers.rain.kelvin_target: must be a number in [2000, 12000]")},
		{TEXT("\"exposure_offset\": -0.2}"), TEXT("\"exposure_offset\": -2.5}"), TEXT("weather.json: modifiers.overcast.exposure_offset: must be a number in [-2, 2]")},
		{TEXT("\"exposure_offset\": -0.4}"), TEXT("\"exposure_offset\": -0.4, \"tint\": 1}"), TEXT("weather.json: modifiers.rain: unknown key \"tint\"")},
		{TEXT("\"sky_scale\": 0.8, "), TEXT(""), TEXT("weather.json: modifiers.rain: missing key \"sky_scale\"")},
		{TEXT("\"wet_seconds\""), TEXT("\"Wet_seconds\""), TEXT("weather.json: surface: missing key \"wet_seconds\"")},
		{TEXT("\"dry_seconds\": 600.0"), TEXT("\"dry_seconds\": 0"), TEXT("weather.json: surface.dry_seconds: must be a positive number")},
		{TEXT("\"puddle_min_intensity\": 0.4"), TEXT("\"puddle_min_intensity\": 1.0"), TEXT("weather.json: surface.puddle_min_intensity: must be a number in [0, 1)")},
		{TEXT("\"time\": \"03:00\""), TEXT("\"time\": \"3:00\""), TEXT("weather.json: schedule[1].time: must be HH:MM (00:00-23:59)")},
		{TEXT("\"time\": \"22:30\""), TEXT("\"time\": \"24:00\""), TEXT("weather.json: schedule[9].time: must be HH:MM (00:00-23:59)")},
		{TEXT("\"time\": \"13:00\""), TEXT("\"time\": \"08:30\""), TEXT("weather.json: schedule[3].time: must be later than schedule[2].time")},
		{TEXT("{\"time\": \"16:30\", \"state\": \"rain\", \"intensity\": 1.0}"), TEXT("{\"time\": \"16:30\", \"state\": \"rain\"}"), TEXT("weather.json: schedule[5].intensity: required for rain")},
		{TEXT("\"intensity\": 0.6}"), TEXT("\"intensity\": 0.01}"), TEXT("weather.json: schedule[4].intensity: must be a number in [0.05, 1]")},
		{TEXT("{\"time\": \"03:00\", \"state\": \"overcast\"}"), TEXT("{\"time\": \"03:00\", \"state\": \"overcast\", \"intensity\": 0.3}"), TEXT("weather.json: schedule[1].intensity: only allowed for rain")},
		{TEXT("\"system\": \"/Game/Golmok"), TEXT("\"system\": \"/Engine/Golmok"), TEXT("weather.json: rain_fx.system: must be an object path /Game/.../Package.Object")},
		{TEXT("\"enabled\": true"), TEXT("\"enabled\": 1"), TEXT("weather.json: rain_fx.enabled: must be true or false")},
		{TEXT("\"max_spawn_rate\": 12000"), TEXT("\"max_spawn_rate\": 0"), TEXT("weather.json: rain_fx.max_spawn_rate: must be a number in (0, 20000]")},
		{TEXT("[1000, 1000, 500]"), TEXT("[1000, 1000]"), TEXT("weather.json: rain_fx.box_half_extent_cm: must be an array of 3 numbers")},
		{TEXT("[1000, 1000, 500]"), TEXT("[1000, 99, 500]"), TEXT("weather.json: rain_fx.box_half_extent_cm[1]: must be a number in [100, 5000]")},
		{TEXT("\"height_offset_cm\": 300"), TEXT("\"height_offset_cm\": 3001"), TEXT("weather.json: rain_fx.height_offset_cm: must be a number in [-1000, 3000]")},
		{TEXT("MPC_GolmokWeather.MPC_GolmokWeather"), TEXT("MPC_GolmokWeather"), TEXT("weather.json: mpc: must be an object path /Game/.../Package.Object")},
	};
	// ---- error table end ----

	bool SameBits(double A, double B)
	{
		return std::memcmp(&A, &B, sizeof(double)) == 0;
	}

	bool SameBits(const GolmokWeatherMath::Light& A, const GolmokWeatherMath::Light& B)
	{
		return SameBits(A.Lux, B.Lux) && A.bUseTemperature == B.bUseTemperature && SameBits(A.Kelvin, B.Kelvin) && SameBits(A.Sky, B.Sky)
			&& SameBits(A.Fog, B.Fog) && SameBits(A.FogHeightFalloff, B.FogHeightFalloff) && A.bExposureOverridden == B.bExposureOverridden
			&& SameBits(A.ExposureBias, B.ExposureBias);
	}

	bool SameBits(const GolmokWeatherMath::Modifier& A, const GolmokWeatherMath::Modifier& B)
	{
		for (int32 Index = 0; Index < GolmokWeatherMath::ModifierFieldCount; ++Index)
		{
			if (!SameBits(GolmokWeatherMath::GetField(A, Index), GolmokWeatherMath::GetField(B, Index)))
			{
				return false;
			}
		}
		return true;
	}

	/** Field by field within 1e-12 relative: a non-identity modifier computed here and in the subsystem (another translation
	 * unit, exp2 / log2 Lerp) may differ in the last bits under the compiler's floating-point flags (review R112-U3). Copies
	 * and the identity keep SameBits. */
	bool NearlySame(const GolmokWeatherMath::Modifier& A, const GolmokWeatherMath::Modifier& B)
	{
		for (int32 Index = 0; Index < GolmokWeatherMath::ModifierFieldCount; ++Index)
		{
			const double X = GolmokWeatherMath::GetField(A, Index);
			const double Y = GolmokWeatherMath::GetField(B, Index);
			if (FMath::Abs(X - Y) > 1e-12 * FMath::Max(1.0, FMath::Max(FMath::Abs(X), FMath::Abs(Y))))
			{
				return false;
			}
		}
		return true;
	}

	GolmokWeatherMath::Modifier MakeModifier(double Lux, double Sky, double Fog, double Falloff, double KelvinTarget, double KelvinWeight,
		double Exposure)
	{
		GolmokWeatherMath::Modifier M;
		M.LuxScale = Lux;
		M.SkyScale = Sky;
		M.FogScale = Fog;
		M.FogHeightFalloffScale = Falloff;
		M.KelvinTarget = KelvinTarget;
		M.KelvinWeight = KelvinWeight;
		M.ExposureOffset = Exposure;
		return M;
	}
}

// ---- Golmok.Weather.Config -----------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokWeatherConfigTest, "Golmok.Weather.Config",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokWeatherConfigTest::RunTest(const FString& Parameters)
{
	using namespace GolmokWeatherTests;
	using GolmokWeatherMath::State;

	// The committed file: design section 6 values, initial clear + fixed (every earlier expectation unchanged).
	GolmokWeather::FConfig Config;
	{
		FString Error;
		if (!TestTrue(TEXT("Config/Golmok/weather.json parses"), GolmokWeather::LoadConfigFile(GolmokWeather::DefaultConfigPath(), Config, Error)))
		{
			AddError(Error);
			return false;
		}
		TestEqual(TEXT("schema_version"), Config.SchemaVersion, 1);
		TestTrue(TEXT("initial is clear + fixed"), Config.InitialState == State::Clear && !Config.bInitialSchedule && Config.InitialIntensity == 0.0);
		TestEqual(TEXT("transition_seconds"), Config.TransitionSeconds, 20.0);
		TestTrue(TEXT("rain_levels 0.3 / 0.6 / 1.0"), Config.RainLight == 0.3 && Config.RainModerate == 0.6 && Config.RainHeavy == 1.0);
		TestTrue(TEXT("overcast modifier"), SameBits(Config.Overcast, MakeModifier(0.3, 1.0, 1.4, 0.8, 6800.0, 0.5, -0.2)));
		TestTrue(TEXT("rain modifier"), SameBits(Config.Rain, MakeModifier(0.12, 0.8, 2.0, 0.6, 7200.0, 0.7, -0.4)));
		TestTrue(TEXT("surface 60 / 600 / 0.4 / 240 / 1200"), Config.Surface.WetSeconds == 60.0 && Config.Surface.DrySeconds == 600.0
			&& Config.Surface.PuddleMinIntensity == 0.4 && Config.Surface.PuddleFillSeconds == 240.0 && Config.Surface.PuddleDrySeconds == 1200.0);
		if (TestEqual(TEXT("ten schedule slots"), Config.Schedule.Num(), 10) && TestEqual(TEXT("schedule times"), Config.ScheduleTimes.Num(), 10))
		{
			TestTrue(TEXT("00:00 rain 0.3"), Config.Schedule[0].Minutes == 0.0 && Config.Schedule[0].State == State::Rain && Config.Schedule[0].Intensity == 0.3);
			TestTrue(TEXT("08:30 clear"), Config.Schedule[2].Minutes == 510.0 && Config.Schedule[2].State == State::Clear && Config.Schedule[2].Intensity == 0.0);
			TestTrue(TEXT("16:30 rain 1.0"), Config.Schedule[5].Minutes == 990.0 && Config.Schedule[5].State == State::Rain && Config.Schedule[5].Intensity == 1.0);
			TestTrue(TEXT("22:30 overcast"), Config.Schedule[9].Minutes == 1350.0 && Config.Schedule[9].State == State::Overcast);
			for (int32 Index = 0; Index < Config.Schedule.Num(); ++Index)
			{
				TestEqual(*FString::Printf(TEXT("ScheduleTimes[%d] == Schedule[%d].Minutes"), Index, Index), Config.ScheduleTimes[Index], Config.Schedule[Index].Minutes);
			}
		}
		TestEqual(TEXT("rain_fx.system"), Config.RainFxSystem, FString(TEXT("/Game/Golmok/Weather/NS_GolmokRain.NS_GolmokRain")));
		TestTrue(TEXT("rain_fx.enabled"), Config.bRainFxEnabled);
		TestEqual(TEXT("rain_fx.max_spawn_rate"), Config.MaxSpawnRate, 12000.0);
		TestTrue(TEXT("rain_fx.box_half_extent_cm"), Config.BoxHalfExtentCm == FVector(1000.0, 1000.0, 500.0));
		TestEqual(TEXT("rain_fx.height_offset_cm"), Config.HeightOffsetCm, 300.0);
		TestEqual(TEXT("mpc"), Config.Mpc, FString(TEXT("/Game/Golmok/Weather/MPC_GolmokWeather.MPC_GolmokWeather")));

		double Level = 0.0;
		TestTrue(TEXT("rain level heavy"), GolmokWeather::ResolveRainLevel(Config, TEXT("heavy"), Level) && Level == 1.0);
		TestTrue(TEXT("rain level light"), GolmokWeather::ResolveRainLevel(Config, TEXT("light"), Level) && Level == 0.3);
		TestFalse(TEXT("rain level is case-sensitive"), GolmokWeather::ResolveRainLevel(Config, TEXT("Heavy"), Level));
		TestFalse(TEXT("unknown rain level"), GolmokWeather::ResolveRainLevel(Config, TEXT("drizzle"), Level));
	}

	// The error table: the same inputs and messages as the Python parser.
	{
		FString Text;
		TestTrue(TEXT("weather.json readable"), FFileHelper::LoadFileToString(Text, *GolmokWeather::DefaultConfigPath()));
		Text.ReplaceInline(TEXT("\r\n"), TEXT("\n"), ESearchCase::CaseSensitive);
		TestTrue(TEXT("error table has at least 12 cases"), UE_ARRAY_COUNT(ErrorCases) >= 12);
		for (const FErrorCase& Case : ErrorCases)
		{
			const int32 First = Text.Find(Case.Old, ESearchCase::CaseSensitive);
			const bool bOnce = First != INDEX_NONE && Text.Find(Case.Old, ESearchCase::CaseSensitive, ESearchDir::FromStart, First + 1) == INDEX_NONE;
			if (!TestTrue(*FString::Printf(TEXT("snippet occurs once: %s"), Case.Old), bOnce))
			{
				continue;
			}
			const FString Broken = Text.Replace(Case.Old, Case.New, ESearchCase::CaseSensitive);
			GolmokWeather::FConfig Untouched = Config;
			FString Error;
			const bool bParsed = GolmokWeather::ParseConfigText(Broken, Untouched, Error);
			TestFalse(*FString::Printf(TEXT("rejected: %s"), Case.Message), bParsed);
			TestEqual(*FString::Printf(TEXT("message for %s -> %s"), Case.Old, Case.New), Error, FString(Case.Message));
			TestTrue(*FString::Printf(TEXT("all or nothing: %s"), Case.Message), Untouched.Schedule.Num() == Config.Schedule.Num()
				&& Untouched.RainFxSystem == Config.RainFxSystem && SameBits(Untouched.Rain, Config.Rain));
		}
		GolmokWeather::FConfig Missing;
		FString Error;
		TestFalse(TEXT("missing file fails"), GolmokWeather::LoadConfigFile(TEXT("Z:/golmok/no/such/weather.json"), Missing, Error));
		TestTrue(TEXT("missing file message"), Error.StartsWith(TEXT("weather.json: ")) && Error.EndsWith(TEXT(": cannot read file")));
	}

	// The pure rules in the engine build (tools/tests/test_ue_weather_math.py checks them in depth with g++).
	{
		using namespace GolmokWeatherMath;
		const Modifier Identity;
		Light Noon;
		Noon.Lux = 10.0;
		Noon.bUseTemperature = true;
		Noon.Kelvin = 5600.0;
		Noon.Sky = 1.0;
		Noon.Fog = 0.015;
		Noon.FogHeightFalloff = 0.2;
		Noon.bExposureOverridden = false;
		Noon.ExposureBias = -0.0;
		TestTrue(TEXT("identity returns the input bit for bit"), SameBits(Apply(Noon, Identity), Noon));
		TestTrue(TEXT("kelvin_target alone is still the identity"), SameBits(Apply(Noon, MakeModifier(1, 1, 1, 1, 9000, 0, 0)), Noon));
		TestTrue(TEXT("clear target is the identity"), IsIdentity(ForState(State::Clear, 0.7, Config.Overcast, Config.Rain)));
		const Light Overcast = Apply(Noon, Config.Overcast);
		TestTrue(TEXT("overcast: lux x0.3, override on, bias -0.2"), FMath::IsNearlyEqual(Overcast.Lux, 3.0, 1e-12) && Overcast.bExposureOverridden
			&& FMath::IsNearlyEqual(Overcast.ExposureBias, -0.2, 1e-12) && FMath::IsNearlyEqual(Overcast.Kelvin, 6200.0, 1e-9));

		// Rain(0.05) sits 5 % of the way from overcast to rain (log2 space for the scales).
		const Modifier Drizzle = ForState(State::Rain, MinRainIntensity, Config.Overcast, Config.Rain);
		bool bNearOvercast = true;
		for (int32 Index = 0; Index < ModifierFieldCount; ++Index)
		{
			double O = GetField(Config.Overcast, Index), R = GetField(Config.Rain, Index), D = GetField(Drizzle, Index);
			if (Index < 4)
			{
				O = FMath::Log2(O);
				R = FMath::Log2(R);
				D = FMath::Log2(D);
			}
			bNearOvercast &= FMath::IsNearlyEqual(D - O, 0.05 * (R - O), 1e-9);
		}
		TestTrue(TEXT("Rain(0.05) ~ overcast"), bNearOvercast);
		TestTrue(TEXT("Rain(1) == rain modifier"), SameBits(ForState(State::Rain, 1.0, Config.Overcast, Config.Rain), Config.Rain));

		// Precipitation delay: rising rain waits for alpha 0.5, falling rain is over at alpha 0.5.
		TestEqual(TEXT("rising rain at alpha 0.25"), PrecipAt(0.0, 0.6, 0.25), 0.0);
		TestEqual(TEXT("rising rain at alpha 0.4999"), PrecipAt(0.0, 0.6, 0.4999), 0.0);
		TestTrue(TEXT("rising rain at alpha 0.75 is half"), FMath::IsNearlyEqual(PrecipAt(0.0, 0.6, 0.75), 0.3, 1e-12));
		TestEqual(TEXT("falling rain at alpha 0.5"), PrecipAt(0.6, 0.0, 0.5), 0.0);
		TestTrue(TEXT("falling rain at alpha 0.25 is half"), FMath::IsNearlyEqual(PrecipAt(0.6, 0.0, 0.25), 0.3, 1e-12));
		TestEqual(TEXT("alpha 1 is the target"), PrecipAt(0.0, 0.6, 1.0), 0.6);
		TestTrue(TEXT("modifier at alpha 1 is the target"), SameBits(ModifierAt(Identity, Config.Rain, 1.0), Config.Rain));

		// Surface: heavy rain soaks in 60 s; drying keeps puddle <= wetness.
		Surface S;
		S = StepSurface(S, 1.0, 60.0, Config.Surface);
		TestTrue(TEXT("heavy rain 60 s: wetness 1, puddle 0.25"), S.Wetness == 1.0 && FMath::IsNearlyEqual(S.Puddle, 0.25, 1e-12));
		S = StepSurface(S, 1.0, 600.0, Config.Surface);
		S = StepSurface(S, 0.0, 300.0, Config.Surface);
		TestTrue(TEXT("dry 300 s: wetness 0.5, puddle capped at wetness"), FMath::IsNearlyEqual(S.Wetness, 0.5, 1e-12) && S.Puddle == S.Wetness);
		bool bPuddleBelow = true;
		for (int32 Step = 0; Step < 200; ++Step)
		{
			S = StepSurface(S, (Step / 20) % 3 == 0 ? 0.0 : ((Step / 20) % 3 == 1 ? 0.45 : 1.0), 17.0, Config.Surface);
			bPuddleBelow &= S.Puddle <= S.Wetness && S.Wetness <= 1.0 && S.Puddle >= 0.0;
		}
		TestTrue(TEXT("puddle <= wetness over a rain / dry sequence"), bPuddleBelow);
		const Surface Clamped = ClampSurface(0.3, 0.8);
		TestTrue(TEXT("ClampSurface caps puddle"), Clamped.Wetness == 0.3 && Clamped.Puddle == 0.3);

		// Schedule: 00:00 first slot; a schedule whose first slot is 01:00 runs its last slot across midnight.
		const double* Times = Config.ScheduleTimes.GetData();
		const int32 Count = Config.ScheduleTimes.Num();
		TestEqual(TEXT("00:00 -> slot 0"), ScheduleIndexAt(0.0, Times, Count), 0);
		TestEqual(TEXT("23:59 -> slot 9"), ScheduleIndexAt(1439.0, Times, Count), 9);
		TestEqual(TEXT("24:00 wraps to slot 0"), ScheduleIndexAt(1440.0, Times, Count), 0);
		TestEqual(TEXT("-1 min wraps to slot 9"), ScheduleIndexAt(-1.0, Times, Count), 9);
		const double Late[] = {60.0, 600.0, 1200.0};
		TestEqual(TEXT("before the first slot -> last slot"), ScheduleIndexAt(30.0, Late, 3), 2);
		TestEqual(TEXT("at the first slot"), ScheduleIndexAt(60.0, Late, 3), 0);
		TestEqual(TEXT("empty schedule"), ScheduleIndexAt(30.0, Late, 0), -1);
	}
	return true;
}

// ---- PIE scenarios (Golmok.Weather.Lighting / Runtime) -------------------------------------------------------------

namespace GolmokWeatherTests
{
	const TCHAR* DevMap = TEXT("/Game/Golmok/Maps/L_Dev");
	const TCHAR* InteriorSource = TEXT("weather_test");
	const TCHAR* MpcSkipped = TEXT("MPC_GolmokWeather missing - skipped");
	const TCHAR* NsSkipped = TEXT("NS_GolmokRain missing - skipped");
	/** The design section 10 refusal (GolmokWeatherSubsystem.cpp). */
	const TCHAR* PhotoRefusal = TEXT("weather: photo mode is active - change the weather before entering photo mode");
	/** Time-of-day transitions in the tests (the Lighting tests' precedent): 0.2 s, end values checked 1 s later. */
	constexpr float ShortTransition = 0.2f;
	constexpr double SettleSeconds = 1.0;

	/** The part of a read-back state the weather touches (the same field copy as AGolmokTimeOfDay::ApplyWeather). */
	GolmokWeatherMath::Light ToLight(const FGolmokLightingState& S)
	{
		GolmokWeatherMath::Light L;
		L.Lux = S.Lux;
		L.bUseTemperature = S.bUseTemperature;
		L.Kelvin = S.Kelvin;
		L.Sky = S.Sky;
		L.Fog = S.Fog;
		L.FogHeightFalloff = S.FogHeightFalloff;
		L.bExposureOverridden = S.bExposureOverridden;
		L.ExposureBias = S.ExposureBias;
		return L;
	}

	/** Every field of two read-back states, bit for bit. */
	bool SameBits(const FGolmokLightingState& A, const FGolmokLightingState& B)
	{
		return SameBits(A.SunRotation.Pitch, B.SunRotation.Pitch) && SameBits(A.SunRotation.Yaw, B.SunRotation.Yaw)
			&& SameBits(A.SunRotation.Roll, B.SunRotation.Roll) && A.bVolumetric == B.bVolumetric && SameBits(ToLight(A), ToLight(B));
	}

	/** The components store floats: a value computed in double from a float read-back matches within float rounding. */
	bool NearlyRel(double Actual, double Expected)
	{
		return FMath::Abs(Actual - Expected) <= 1e-5 * FMath::Max(1.0, FMath::Abs(Expected));
	}

	/** Captured state == Expected on the weather fields, and the sun rotation / volumetric of Base unchanged. */
	void CheckLight(FAutomationTestBase* Test, const FGolmokLightingState& S, const GolmokWeatherMath::Light& E, const FGolmokLightingState& Base,
		const FString& What)
	{
		Test->TestTrue(*FString::Printf(TEXT("%s: Lux %g ~ %g"), *What, S.Lux, E.Lux), NearlyRel(S.Lux, E.Lux));
		Test->TestTrue(*FString::Printf(TEXT("%s: Sky %g ~ %g"), *What, S.Sky, E.Sky), NearlyRel(S.Sky, E.Sky));
		Test->TestTrue(*FString::Printf(TEXT("%s: Kelvin %g ~ %g"), *What, S.Kelvin, E.Kelvin), NearlyRel(S.Kelvin, E.Kelvin));
		Test->TestTrue(*FString::Printf(TEXT("%s: Fog %g ~ %g"), *What, S.Fog, E.Fog), NearlyRel(S.Fog, E.Fog));
		Test->TestTrue(*FString::Printf(TEXT("%s: FogHeightFalloff %g ~ %g"), *What, S.FogHeightFalloff, E.FogHeightFalloff),
			NearlyRel(S.FogHeightFalloff, E.FogHeightFalloff));
		Test->TestTrue(*FString::Printf(TEXT("%s: ExposureBias %g ~ %g"), *What, S.ExposureBias, E.ExposureBias), NearlyRel(S.ExposureBias, E.ExposureBias));
		Test->TestTrue(*FString::Printf(TEXT("%s: bUseTemperature"), *What), S.bUseTemperature == E.bUseTemperature);
		Test->TestTrue(*FString::Printf(TEXT("%s: bExposureOverridden %d == %d"), *What, S.bExposureOverridden ? 1 : 0, E.bExposureOverridden ? 1 : 0),
			S.bExposureOverridden == E.bExposureOverridden);
		// Rotation goes through the actor's quaternion, so a rewrite of a read-back rotation is compared with a tolerance.
		Test->TestTrue(*FString::Printf(TEXT("%s: sun rotation unchanged"), *What), S.SunRotation.Equals(Base.SunRotation, 1e-4));
		Test->TestTrue(*FString::Printf(TEXT("%s: volumetric unchanged"), *What), S.bVolumetric == Base.bVolumetric);
	}

	/** The target modifier the subsystem builds for a state (the stored intensity is the float the caller passed). */
	GolmokWeatherMath::Modifier TargetModifier(const GolmokWeather::FConfig& Config, EGolmokWeather Weather, float Intensity)
	{
		const GolmokWeatherMath::State State = static_cast<GolmokWeatherMath::State>(static_cast<uint8>(Weather));
		return GolmokWeatherMath::ForState(State, GolmokWeatherMath::TargetRain(State, static_cast<double>(Intensity)), Config.Overcast, Config.Rain);
	}

	/** The rain fx actor (the component's owner); nullptr without NS_GolmokRain. */
	AActor* RainFxActor(const UGolmokWeatherSubsystem* Weather)
	{
		UFXSystemComponent* Component = Weather ? Weather->GetRainFxComponent() : nullptr;
		return Component ? Component->GetOwner() : nullptr;
	}

	/** What one OnWeatherChanged callback saw. */
	struct FEventLog
	{
		int32 Count = 0;
		EGolmokWeather Target = EGolmokWeather::Clear;
		float Intensity = -1.f;
		bool bInstant = false;
		/** Read inside the callback (design section 9 "target first"). */
		EGolmokWeather TargetInside = EGolmokWeather::Clear;
		float TargetIntensityInside = -1.f;
		float RainInside = -1.f;
	};

	/** Shared latent-command plumbing; every wait uses FPlatformTime (the world clock stops in photo mode). */
	class FWeatherScenarioBase : public IAutomationLatentCommand
	{
	public:
		explicit FWeatherScenarioBase(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

		virtual ~FWeatherScenarioBase() override
		{
			if (UGolmokWeatherSubsystem* W = Weather.Get())
			{
				W->OnWeatherChanged.Remove(EventHandle);
			}
		}

	protected:
		UWorld* PlayWorld()
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			if (World && PhaseStart < 0.0)
			{
				PhaseStart = FPlatformTime::Seconds();
			}
			return World;
		}

		double Elapsed() const
		{
			return FPlatformTime::Seconds() - PhaseStart;
		}

		bool Next(int32 NextPhase)
		{
			Phase = NextPhase;
			PhaseStart = FPlatformTime::Seconds();
			return false;
		}

		bool NoWorld()
		{
			if (FPlatformTime::Seconds() - CreatedAt < 60.0)
			{
				return false;
			}
			Test->AddError(TEXT("PIE world not running after 60 s"));
			return true;
		}

		/** The weather subsystem and the time of day of the PIE world (errors when missing or weather.json is off). */
		bool Resolve(UWorld* World)
		{
			UGolmokWeatherSubsystem* W = UGolmokWeatherSubsystem::Get(World);
			if (!W)
			{
				Test->AddError(TEXT("UGolmokWeatherSubsystem missing in the PIE world"));
				return false;
			}
			if (!W->IsEnabled())
			{
				Test->AddError(FString::Printf(TEXT("weather is off: %s"), *W->GetConfigError()));
				return false;
			}
			AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::FindOrSpawn(World);
			if (!Tod || !Tod->EnsurePresets() || Tod->GetCycle().Num() != 4)
			{
				Test->AddError(TEXT("AGolmokTimeOfDay with 4 keyframes not available in the PIE world"));
				return false;
			}
			Weather = W;
			TimeOfDay = Tod;
			EventHandle = W->OnWeatherChanged.AddLambda(
				[this](EGolmokWeather Target, float Intensity, bool bInstant)
				{
					++Events.Count;
					Events.Target = Target;
					Events.Intensity = Intensity;
					Events.bInstant = bInstant;
					if (const UGolmokWeatherSubsystem* Inside = Weather.Get())
					{
						Events.TargetInside = Inside->GetTargetWeather();
						Events.TargetIntensityInside = Inside->GetTargetIntensity();
						Events.RainInside = Inside->GetRainIntensity();
					}
				});
			return true;
		}

		/** Set (expected to succeed) or record the refusal. */
		bool Set(EGolmokWeather State, float Intensity, bool bInstant)
		{
			FString Message;
			const bool bOk = Weather->SetWeather(State, Intensity, bInstant, Message);
			if (!bOk)
			{
				Test->AddError(FString::Printf(TEXT("SetWeather(%s %.2f) refused: %s"), UGolmokWeatherSubsystem::WeatherName(State), Intensity, *Message));
			}
			return bOk;
		}

		/** golmok.weather with these arguments (the console path without the world lookup). */
		bool Run(const TArray<FString>& Args, FString& OutMessage)
		{
			return Weather->RunCommand(Args, OutMessage);
		}

		bool Valid()
		{
			if (Weather.IsValid() && TimeOfDay.IsValid())
			{
				return true;
			}
			Test->AddError(FString::Printf(TEXT("weather subsystem / time of day disappeared (phase %d)"), Phase));
			return false;
		}

		FAutomationTestBase* Test;
		double CreatedAt;
		int32 Phase = 0;
		double PhaseStart = -1.0;
		TWeakObjectPtr<UGolmokWeatherSubsystem> Weather;
		TWeakObjectPtr<AGolmokTimeOfDay> TimeOfDay;
		FDelegateHandle EventHandle;
		FEventLog Events;
	};

	// ---- Golmok.Weather.Lighting -------------------------------------------------------------------------------

	enum class ELightingPhase : int32
	{
		Start,
		TodTransitionDone,
		Done,
	};

	class FLightingScenario : public FWeatherScenarioBase
	{
	public:
		explicit FLightingScenario(FAutomationTestBase* InTest) : FWeatherScenarioBase(InTest) {}

		virtual ~FLightingScenario() override
		{
			if (AGolmokTimeOfDay* Tod = TimeOfDay.Get())
			{
				Tod->OnPresetChanged.Remove(PresetHandle);
				Tod->OnNightChanged.Remove(NightHandle);
			}
		}

		virtual bool Update() override
		{
			UWorld* World = PlayWorld();
			if (!World)
			{
				return NoWorld();
			}
			switch (static_cast<ELightingPhase>(Phase))
			{
			case ELightingPhase::Start:
			{
				if (Elapsed() < 0.5)
				{
					return false; // let the level actors finish BeginPlay
				}
				if (!Resolve(World))
				{
					return true;
				}
				AGolmokTimeOfDay* Tod = TimeOfDay.Get();
				Tod->TransitionSeconds = 0.f; // preset / interior changes below are instant; one step uses ShortTransition
				Tod->SetClockMode(EGolmokClockMode::Fixed);
				PresetHandle = Tod->OnPresetChanged.AddLambda([this](FName, bool) { ++PresetEvents; });
				NightHandle = Tod->OnNightChanged.AddLambda([this](bool) { ++NightEvents; });

				LevelLightingBase();
				PresetMatrix();
				NightUnaffected();
				Interior();
				TransitionByHand();
				ScheduleOnClock();
				return StartTodTransition();
			}

			case ELightingPhase::TodTransitionDone:
			{
				if (Elapsed() < SettleSeconds)
				{
					return false;
				}
				if (!Valid())
				{
					return true;
				}
				AGolmokTimeOfDay* Tod = TimeOfDay.Get();
				Test->TestFalse(TEXT("time-of-day transition finished"), Tod->IsTransitioning());
				FGolmokLightingState S;
				Tod->CaptureState(S);
				const GolmokWeatherMath::Light E = GolmokWeatherMath::Apply(ToLight(EveningClear), TargetModifier(Weather->GetConfig(), EGolmokWeather::Rain, 0.6f));
				CheckLight(Test, S, E, EveningClear, TEXT("rain 0.6 set during the ToD transition: its end is the new composition"));
				Set(EGolmokWeather::Clear, 0.f, true);
				Tod->TransitionSeconds = 2.f;
				Test->AddInfo(FString::Printf(TEXT("end: %s"), *Weather->BuildHudLine()));
				return Next(static_cast<int32>(ELightingPhase::Done));
			}

			case ELightingPhase::Done:
				return true;
			}
			return true;
		}

	private:
		/** Rain on the level's authored lighting turns the exposure override on; clear gives the authored flag back. */
		void LevelLightingBase()
		{
			AGolmokTimeOfDay* Tod = TimeOfDay.Get();
			if (Tod->HasTimeOfDay())
			{
				Test->AddInfo(TEXT("level-lighting base not available (a preset or the clock is applied) - skipped"));
				return;
			}
			FGolmokLightingState Authored;
			if (!Test->TestTrue(TEXT("CaptureState finds the L_Dev lighting actors"), Tod->CaptureState(Authored)))
			{
				return;
			}
			const GolmokWeatherMath::Modifier M = TargetModifier(Weather->GetConfig(), EGolmokWeather::Rain, 0.6f);
			Set(EGolmokWeather::Rain, 0.6f, true);
			Test->TestTrue(TEXT("the subsystem drives this time of day (its modifier == the weather's)"), SameBits(Tod->GetWeatherModifier(), Weather->GetCurrentModifier()));
			Test->TestTrue(TEXT("rain 0.6 instant: the current modifier is the target"), NearlySame(Weather->GetCurrentModifier(), M));
			FGolmokLightingState Rain;
			Tod->CaptureState(Rain);
			CheckLight(Test, Rain, GolmokWeatherMath::Apply(ToLight(Authored), M), Authored, TEXT("level lighting + rain 0.6"));
			Test->TestTrue(TEXT("level lighting + rain: exposure override on"), Rain.bExposureOverridden);
			Set(EGolmokWeather::Clear, 0.f, true);
			FGolmokLightingState Back;
			Tod->CaptureState(Back);
			Test->TestTrue(*FString::Printf(TEXT("level lighting rain -> clear: bExposureOverridden back to %d"), Authored.bExposureOverridden ? 1 : 0),
				Back.bExposureOverridden == Authored.bExposureOverridden);
			CheckLight(Test, Back, ToLight(Authored), Authored, TEXT("level lighting rain -> clear"));
		}

		/** Design section 14: preset x {clear, overcast, rain 0.6} == Apply(the clear preset state); clear is bit-identical. */
		void PresetMatrix()
		{
			AGolmokTimeOfDay* Tod = TimeOfDay.Get();
			const GolmokWeather::FConfig& Config = Weather->GetConfig();
			for (const FName& Name : Tod->GetCycle())
			{
				Set(EGolmokWeather::Clear, 0.f, true);
				if (!Test->TestTrue(*FString::Printf(TEXT("ApplyPreset(%s, instant)"), *Name.ToString()), Tod->ApplyPreset(Name, true)))
				{
					continue;
				}
				FGolmokLightingState Clear;
				Tod->CaptureState(Clear);
				FGolmokLightingPreset P;
				if (Tod->FindPreset(Name, P))
				{
					// The Golmok.Lighting.PresetApply expectations: clear changes nothing.
					Test->TestTrue(*FString::Printf(TEXT("%s clear: Lux == preset"), *Name.ToString()), NearlyRel(Clear.Lux, P.Lux));
					Test->TestTrue(*FString::Printf(TEXT("%s clear: Fog == preset"), *Name.ToString()), NearlyRel(Clear.Fog, P.Fog));
					Test->TestTrue(*FString::Printf(TEXT("%s clear: ExposureBias == preset"), *Name.ToString()), NearlyRel(Clear.ExposureBias, P.ExposureBias));
				}
				struct FCase
				{
					EGolmokWeather State;
					float Intensity;
				};
				for (const FCase& Case : {FCase{EGolmokWeather::Overcast, 0.f}, FCase{EGolmokWeather::Rain, 0.6f}})
				{
					PresetEvents = 0;
					NightEvents = 0;
					const bool bNight = Tod->IsNight();
					if (!Set(Case.State, Case.Intensity, true))
					{
						continue;
					}
					const FString What = FString::Printf(TEXT("%s + %s %.1f"), *Name.ToString(), UGolmokWeatherSubsystem::WeatherName(Case.State), Case.Intensity);
					FGolmokLightingState S;
					Tod->CaptureState(S);
					CheckLight(Test, S, GolmokWeatherMath::Apply(ToLight(Clear), TargetModifier(Config, Case.State, Case.Intensity)), Clear, What);
					Test->TestEqual(*FString::Printf(TEXT("%s: no OnPresetChanged"), *What), PresetEvents, 0);
					Test->TestEqual(*FString::Printf(TEXT("%s: no OnNightChanged"), *What), NightEvents, 0);
					Test->TestTrue(*FString::Printf(TEXT("%s: IsNight unchanged"), *What), Tod->IsNight() == bNight);
					Test->TestEqual(*FString::Printf(TEXT("%s: CurrentPreset unchanged"), *What), Tod->CurrentPreset.ToString(), Name.ToString());
				}
				Set(EGolmokWeather::Clear, 0.f, true);
				FGolmokLightingState Back;
				Tod->CaptureState(Back);
				Test->TestTrue(*FString::Printf(TEXT("%s: back to clear is the clear state bit for bit"), *Name.ToString()), SameBits(Back, Clear));
			}
		}

		/**
		 * A day minute whose base lux lies in [threshold, threshold / rain lux_scale) - just above the night threshold, so
		 * heavy rain cuts the sun below it - but IsNight() reads the base only (R112-U11: found from the loaded presets
		 * through EvaluateClock, so a 14b night-lux retune moves the minute instead of breaking the test).
		 */
		void NightUnaffected()
		{
			AGolmokTimeOfDay* Tod = TimeOfDay.Get();
			UGolmokWeatherSubsystem* W = Weather.Get();
			const double Threshold = static_cast<double>(Tod->NightLuxThreshold);
			const double RainLuxScale = W->GetConfig().Rain.LuxScale;
			// 1 % margins on both sides keep float rounding (the float threshold, the composed lux) out of the decision.
			const double Low = Threshold * 1.01;
			const double High = Threshold / RainLuxScale * 0.99;
			float Minute = -1.f;
			double BaseLux = 0.0;
			for (int32 M = 0; static_cast<double>(M) < GolmokClockMath::MinutesPerDay && Minute < 0.f; ++M)
			{
				FGolmokLightingState Base;
				if (Tod->EvaluateClock(static_cast<double>(M), Base) && Base.Lux >= Low && Base.Lux < High)
				{
					Minute = static_cast<float>(M);
					BaseLux = Base.Lux;
				}
			}
			// R113-6: without the minute (or when it reads as night) only the night checks drop; the weather changes still
			// run at the current state, so the OnPresetChanged / OnNightChanged counts below are always asserted.
			FString When;
			bool bNearThreshold = false;
			if (Minute < 0.f)
			{
				Test->AddInfo(FString::Printf(TEXT("no minute with base lux in [%g, %g) (threshold %g, rain lux_scale %g) - NightUnaffected skipped"), Low,
					High, Threshold, RainLuxScale));
			}
			else
			{
				When = FString::Printf(TEXT("%02d:%02d (base lux %g)"), static_cast<int32>(Minute) / 60, static_cast<int32>(Minute) % 60, BaseLux);
				Test->AddInfo(FString::Printf(TEXT("NightUnaffected at %s"), *When)); // passing assertions print nothing: V-16 §3 reads this line
				Set(EGolmokWeather::Clear, 0.f, true);
				Tod->SetTimeOfDay(Minute, /*bInstant*/ true);
				bNearThreshold = Test->TestFalse(*FString::Printf(TEXT("%s is not night"), *When), Tod->IsNight());
			}
			PresetEvents = 0;
			NightEvents = 0;
			Set(EGolmokWeather::Rain, 1.f, true);
			if (bNearThreshold)
			{
				FGolmokLightingState S;
				Tod->CaptureState(S);
				Test->TestTrue(*FString::Printf(TEXT("%s rain 1.0: lux %g < the night threshold"), *When, S.Lux), S.Lux < Threshold);
				Test->TestFalse(*FString::Printf(TEXT("%s rain 1.0: still not night"), *When), Tod->IsNight());
			}
			Set(EGolmokWeather::Overcast, 0.f, true);
			Set(EGolmokWeather::Clear, 0.f, true);
			Test->TestEqual(TEXT("weather changes fire no OnPresetChanged"), PresetEvents, 0);
			Test->TestEqual(TEXT("weather changes fire no OnNightChanged"), NightEvents, 0);
		}

		/** Interior overlay over rain: fog / bias are the interior preset's, lux / sky keep the weather reduction. */
		void Interior()
		{
			AGolmokTimeOfDay* Tod = TimeOfDay.Get();
			FGolmokLightingPreset Overlay;
			if (!Test->TestTrue(TEXT("interior preset exists"), Tod->FindPreset(Tod->InteriorPreset, Overlay)))
			{
				return;
			}
			Set(EGolmokWeather::Clear, 0.f, true);
			Tod->ApplyPreset(TEXT("clear_noon"), true);
			Set(EGolmokWeather::Rain, 0.6f, true);
			FGolmokLightingState Rain;
			Tod->CaptureState(Rain);
			Tod->EnterInterior(InteriorSource);
			FGolmokLightingState S;
			Tod->CaptureState(S);
			Test->TestTrue(TEXT("interior + rain: IsInterior"), Tod->IsInterior());
			Test->TestTrue(*FString::Printf(TEXT("interior + rain: Fog %g == interior %g"), S.Fog, Overlay.Fog), NearlyRel(S.Fog, Overlay.Fog));
			Test->TestTrue(*FString::Printf(TEXT("interior + rain: ExposureBias %g == interior %g"), S.ExposureBias, Overlay.ExposureBias),
				NearlyRel(S.ExposureBias, Overlay.ExposureBias));
			Test->TestTrue(*FString::Printf(TEXT("interior + rain: Lux %g keeps the rain reduction %g"), S.Lux, Rain.Lux), NearlyRel(S.Lux, Rain.Lux));
			Test->TestTrue(*FString::Printf(TEXT("interior + rain: Sky %g keeps the rain reduction %g"), S.Sky, Rain.Sky), NearlyRel(S.Sky, Rain.Sky));
			Tod->ExitInterior(InteriorSource);
			FGolmokLightingState Out;
			Tod->CaptureState(Out);
			CheckLight(Test, Out, ToLight(Rain), Rain, TEXT("exit interior -> rain state"));
			Set(EGolmokWeather::Clear, 0.f, true);
		}

		/** A weather transition driven by StepWeather: alpha 0.5 is the design section 3 formula, alpha 1 the target. */
		void TransitionByHand()
		{
			AGolmokTimeOfDay* Tod = TimeOfDay.Get();
			UGolmokWeatherSubsystem* W = Weather.Get();
			const GolmokWeather::FConfig& Config = W->GetConfig();
			Set(EGolmokWeather::Clear, 0.f, true);
			Tod->ApplyPreset(TEXT("clear_noon"), true);
			FGolmokLightingState Clear;
			Tod->CaptureState(Clear);
			if (!Set(EGolmokWeather::Rain, 0.6f, false) || !Test->TestTrue(TEXT("rain 0.6 starts a weather transition"), W->IsTransitioning()))
			{
				return;
			}
			const GolmokWeatherMath::Modifier Target = TargetModifier(Config, EGolmokWeather::Rain, 0.6f);
			W->StepWeather(0.5 * Config.TransitionSeconds);
			Test->TestTrue(*FString::Printf(TEXT("alpha 0.5 after half the transition (%.4f)"), W->GetTransitionAlpha()), FMath::IsNearlyEqual(W->GetTransitionAlpha(), 0.5f, 1e-5f));
			const GolmokWeatherMath::Modifier Half = GolmokWeatherMath::ModifierAt(GolmokWeatherMath::Modifier(), Target, 0.5);
			Test->TestTrue(TEXT("alpha 0.5: modifier == Lerp(identity, rain 0.6, smoothstep(0.5))"), NearlySame(W->GetCurrentModifier(), Half));
			Test->TestTrue(TEXT("alpha 0.5: the time of day holds that modifier"), SameBits(Tod->GetWeatherModifier(), W->GetCurrentModifier()));
			Test->TestTrue(TEXT("alpha 0.5: rising rain not started yet"), W->GetRainIntensity() == 0.f);
			FGolmokLightingState S;
			Tod->CaptureState(S);
			CheckLight(Test, S, GolmokWeatherMath::Apply(ToLight(Clear), Half), Clear, TEXT("weather transition alpha 0.5"));
			W->StepWeather(0.5 * Config.TransitionSeconds);
			Test->TestFalse(TEXT("alpha 1: transition finished"), W->IsTransitioning());
			Test->TestTrue(TEXT("alpha 1: modifier == target"), NearlySame(W->GetCurrentModifier(), Target) && SameBits(Tod->GetWeatherModifier(), W->GetCurrentModifier()));
			Test->TestEqual(TEXT("alpha 1: rain == target"), W->GetRainIntensity(), 0.6f);
			Tod->CaptureState(S);
			CheckLight(Test, S, GolmokWeatherMath::Apply(ToLight(Clear), Target), Clear, TEXT("weather transition alpha 1"));
			Set(EGolmokWeather::Clear, 0.f, true);
		}

		/** Clock at 60 min/s + Schedule: exactly one OnWeatherChanged at the 15:00 boundary (13:00 overcast -> 15:00 rain 0.6). */
		void ScheduleOnClock()
		{
			AGolmokTimeOfDay* Tod = TimeOfDay.Get();
			UGolmokWeatherSubsystem* W = Weather.Get();
			Set(EGolmokWeather::Clear, 0.f, true);
			if (!Test->TestTrue(TEXT("SetClockMode(Clock)"), Tod->SetClockMode(EGolmokClockMode::Clock)))
			{
				return;
			}
			Tod->ClockMinutesPerRealSecond = 60.f;
			Tod->SetTimeOfDay(899.f, true); // 14:59
			FString Message;
			Test->TestTrue(TEXT("mode schedule"), W->SetMode(EGolmokWeatherMode::Schedule, Message));
			Test->TestTrue(*FString::Printf(TEXT("14:59 is the 13:00 overcast slot: %s"), *Message),
				W->GetTargetWeather() == EGolmokWeather::Overcast && W->GetScheduleIndexNow() == 3);
			W->StepWeather(W->GetConfig().TransitionSeconds); // land on overcast
			Events = FEventLog();
			const double Step = 1.0 / 60.0; // one game minute at 60 min/s
			Tod->AdvanceClock(0.5 * Step);  // 14:59.5
			W->StepWeather(0.5 * Step);
			Test->TestEqual(TEXT("no OnWeatherChanged before 15:00"), Events.Count, 0);
			Tod->AdvanceClock(Step); // 15:00.5
			W->StepWeather(Step);
			Tod->AdvanceClock(Step); // 15:01.5
			W->StepWeather(Step);
			Test->TestEqual(TEXT("OnWeatherChanged exactly once across 15:00"), Events.Count, 1);
			Test->TestTrue(TEXT("... with (rain, 0.6, not instant)"), Events.Target == EGolmokWeather::Rain && Events.Intensity == 0.6f && !Events.bInstant);
			Test->TestTrue(TEXT("... the target is new inside the callback"), Events.TargetInside == EGolmokWeather::Rain && Events.TargetIntensityInside == 0.6f);
			Test->TestTrue(TEXT("... the rain has not moved inside the callback"), Events.RainInside == 0.f);
			Test->TestTrue(TEXT("15:01.5 is a schedule transition"), W->IsTransitioning() && W->GetMode() == EGolmokWeatherMode::Schedule);
			W->SetMode(EGolmokWeatherMode::Fixed, Message);
			Tod->SetClockMode(EGolmokClockMode::Fixed);
			Set(EGolmokWeather::Clear, 0.f, true);
		}

		/** golden_evening with a ToD transition; rain 0.6 is set while it runs (checked in TodTransitionDone). */
		bool StartTodTransition()
		{
			AGolmokTimeOfDay* Tod = TimeOfDay.Get();
			Set(EGolmokWeather::Clear, 0.f, true);
			Tod->ApplyPreset(TEXT("golden_evening"), true);
			Tod->CaptureState(EveningClear);
			Tod->ApplyPreset(TEXT("clear_noon"), true);
			Tod->TransitionSeconds = ShortTransition;
			Tod->ApplyPreset(TEXT("golden_evening"));
			if (!Test->TestTrue(TEXT("golden_evening transition running"), Tod->IsTransitioning()))
			{
				return true;
			}
			Set(EGolmokWeather::Rain, 0.6f, true);
			Test->TestTrue(TEXT("the ToD transition keeps running after the weather change"), Tod->IsTransitioning());
			return Next(static_cast<int32>(ELightingPhase::TodTransitionDone));
		}

		FDelegateHandle PresetHandle;
		FDelegateHandle NightHandle;
		int32 PresetEvents = 0;
		int32 NightEvents = 0;
		FGolmokLightingState EveningClear;
	};

	// ---- Golmok.Weather.Runtime --------------------------------------------------------------------------------

	enum class ERuntimePhase : int32
	{
		WaitForPlayer,
		PhotoActive,
		Done,
	};

	class FRuntimeScenario : public FWeatherScenarioBase
	{
	public:
		explicit FRuntimeScenario(FAutomationTestBase* InTest) : FWeatherScenarioBase(InTest) {}

		virtual bool Update() override
		{
			UWorld* World = PlayWorld();
			if (!World)
			{
				return NoWorld();
			}
			switch (static_cast<ERuntimePhase>(Phase))
			{
			case ERuntimePhase::WaitForPlayer:
			{
				const APlayerController* PC = World->GetFirstPlayerController();
				if (Elapsed() < 0.5 || !PC || !PC->PlayerCameraManager || !PC->GetPawn())
				{
					if (Elapsed() < 20.0)
					{
						return false;
					}
					Test->AddInfo(TEXT("no possessed pawn / camera manager after 20 s - camera follow and photo checks see none"));
				}
				if (!Resolve(World))
				{
					return true;
				}
				TimeOfDay->TransitionSeconds = 0.f; // interior changes below are instant
				LoadMpc();
				Console();
				EventsAndCallback();
				PrecipitationDelay();
				SurfaceTable();
				HudLine(World);
				RainFx(World);
				return EnterPhoto(World);
			}

			case ERuntimePhase::PhotoActive:
			{
				if (Elapsed() < 0.2)
				{
					return false; // a few editor frames with the game paused
				}
				if (!Valid())
				{
					return true;
				}
				ExitPhoto(World);
				return Next(static_cast<int32>(ERuntimePhase::Done));
			}

			case ERuntimePhase::Done:
				return true;
			}
			return true;
		}

	private:
		/** MPC_GolmokWeather when the subsystem found it (design section 8); null = the MPC steps are skipped. */
		void LoadMpc()
		{
			if (Weather->DescribeMpc() != TEXT("ok"))
			{
				Test->AddInfo(MpcSkipped);
				return;
			}
			Mpc = Cast<UMaterialParameterCollection>(FSoftObjectPath(Weather->GetConfig().Mpc).TryLoad());
			Test->TestNotNull(TEXT("MPC_GolmokWeather loads"), Mpc.Get());
		}

		/** MPC instance values == the queried values (+-1e-3: writes happen when a value moves more than 0.001). */
		void CheckMpc(const FString& What)
		{
			UMaterialParameterCollection* Collection = Mpc.Get();
			UWorld* World = Weather->GetWorld();
			UMaterialParameterCollectionInstance* Instance = Collection && World ? World->GetParameterCollectionInstance(Collection) : nullptr;
			if (!Collection)
			{
				return;
			}
			if (!Test->TestNotNull(*FString::Printf(TEXT("%s: MPC instance"), *What), Instance))
			{
				return;
			}
			struct FExpected
			{
				const char* Name;
				float Value;
			};
			const FExpected Expected[] = {
				{GolmokWeatherMath::MpcRainIntensity, Weather->GetRainIntensity()},
				{GolmokWeatherMath::MpcWetness, Weather->GetWetness()},
				{GolmokWeatherMath::MpcPuddleAmount, Weather->GetPuddleAmount()},
			};
			for (const FExpected& E : Expected)
			{
				const FString Name(E.Name);
				float Value = -1.f;
				const bool bFound = Instance->GetScalarParameterValue(FName(*Name), Value);
				Test->TestTrue(*FString::Printf(TEXT("%s: MPC %s %.4f == %.4f"), *What, *Name, Value, E.Value),
					bFound && FMath::Abs(Value - E.Value) <= 1.01e-3f);
			}
		}

		/** golmok.weather parsing (design section 13). */
		void Console()
		{
			UGolmokWeatherSubsystem* W = Weather.Get();
			FString M;
			Set(EGolmokWeather::Clear, 0.f, true);

			Test->TestTrue(TEXT("rain heavy"), Run({TEXT("rain"), TEXT("heavy")}, M));
			Test->TestTrue(*FString::Printf(TEXT("rain heavy -> rain 1.0, transition: %s"), *M),
				W->GetTargetWeather() == EGolmokWeather::Rain && W->GetTargetIntensity() == 1.f && W->IsTransitioning());
			Test->TestTrue(TEXT("rain 0.42 instant"), Run({TEXT("rain"), TEXT("0.42"), TEXT("instant")}, M));
			Test->TestTrue(*FString::Printf(TEXT("rain 0.42 instant -> settled 0.42: %s"), *M),
				W->GetTargetIntensity() == 0.42f && !W->IsTransitioning() && W->GetRainIntensity() == 0.42f);
			Test->TestEqual(TEXT("rain 0.42 instant reply"), M, FString(TEXT("weather: rain 0.42 (instant)")));
			for (const TCHAR* Bad : {TEXT("1.5"), TEXT("0.04"), TEXT("-0.3"), TEXT("drizzle"), TEXT("0.5x")})
			{
				Test->TestFalse(*FString::Printf(TEXT("rain %s refused"), Bad), Run({TEXT("rain"), Bad}, M));
				Test->TestTrue(*FString::Printf(TEXT("rain %s: message names the value (%s)"), Bad, *M), M.Contains(FString::Printf(TEXT("got '%s'"), Bad)));
			}
			Test->TestTrue(TEXT("refusals keep the target"), W->GetTargetWeather() == EGolmokWeather::Rain && W->GetTargetIntensity() == 0.42f);
			Test->TestFalse(TEXT("rain heavy now refused"), Run({TEXT("rain"), TEXT("heavy"), TEXT("now")}, M));
			Test->TestTrue(*FString::Printf(TEXT("... unknown word: %s"), *M), M.Contains(TEXT("unknown word 'now'")));
			Test->TestFalse(TEXT("clear soon refused"), Run({TEXT("clear"), TEXT("soon")}, M));
			Test->TestTrue(TEXT("overcast instant"), Run({TEXT("overcast"), TEXT("instant")}, M));
			Test->TestTrue(TEXT("overcast -> intensity 0"), W->GetTargetWeather() == EGolmokWeather::Overcast && W->GetTargetIntensity() == 0.f
				&& W->GetRainIntensity() == 0.f);

			// An explicit state in schedule mode switches to fixed (with or without a clock).
			Test->TestTrue(TEXT("mode schedule"), Run({TEXT("mode"), TEXT("schedule")}, M));
			Test->TestTrue(TEXT("mode is schedule"), W->GetMode() == EGolmokWeatherMode::Schedule);
			const FString Hud = W->BuildHudLine();
			Test->TestTrue(*FString::Printf(TEXT("schedule HUD tail: %s"), *Hud),
				W->GetScheduleIndexNow() < 0 ? Hud.EndsWith(TEXT(" | schedule no clock")) : Hud.Contains(TEXT(" | schedule next ")));
			Test->TestTrue(TEXT("rain light in schedule mode"), Run({TEXT("rain"), TEXT("light"), TEXT("instant")}, M));
			Test->TestTrue(TEXT("... switches to fixed"), W->GetMode() == EGolmokWeatherMode::Fixed);
			Test->TestTrue(TEXT("... rain 0.3"), W->GetTargetWeather() == EGolmokWeather::Rain && W->GetTargetIntensity() == 0.3f);

			Test->TestFalse(TEXT("mode sometimes refused"), Run({TEXT("mode"), TEXT("sometimes")}, M));
			Test->TestFalse(TEXT("fx maybe refused"), Run({TEXT("fx"), TEXT("maybe")}, M));
			Test->TestFalse(TEXT("surface 2 refused"), Run({TEXT("surface"), TEXT("2")}, M));
			Test->TestTrue(TEXT("surface 0.5 0.7"), Run({TEXT("surface"), TEXT("0.5"), TEXT("0.7")}, M));
			Test->TestTrue(TEXT("surface 0.5 0.7 -> puddle capped at wetness"), W->GetWetness() == 0.5f && W->GetPuddleAmount() == 0.5f);
			Test->TestFalse(TEXT("unknown command refused"), Run({TEXT("snow")}, M));
			Test->TestTrue(*FString::Printf(TEXT("... unknown command: %s"), *M), M.Contains(TEXT("unknown command 'snow'")));
			Test->TestTrue(TEXT("status"), Run({}, M));
			Test->TestTrue(*FString::Printf(TEXT("status text: %s"), *M), M.StartsWith(TEXT("weather: target rain 0.30 | current settled")));
			Test->TestTrue(TEXT("list"), Run({TEXT("list")}, M));
			Test->TestTrue(*FString::Printf(TEXT("list text: %s"), *M.Left(60)),
				M.StartsWith(FString::Printf(TEXT("weather: schedule (%d slots"), W->GetConfig().Schedule.Num())));

			Set(EGolmokWeather::Clear, 0.f, true);
			W->SetSurface(0.f, 0.f, M);
		}

		/** One event per target change, the arguments, and the "target first" reads inside the callback (design 9). */
		void EventsAndCallback()
		{
			UGolmokWeatherSubsystem* W = Weather.Get();
			Set(EGolmokWeather::Clear, 0.f, true);
			Events = FEventLog();
			Set(EGolmokWeather::Rain, 0.6f, false);
			Test->TestEqual(TEXT("rain 0.6: one event"), Events.Count, 1);
			Test->TestTrue(TEXT("... (rain, 0.6, not instant)"), Events.Target == EGolmokWeather::Rain && Events.Intensity == 0.6f && !Events.bInstant);
			Test->TestTrue(TEXT("... GetTarget* are new inside the callback"), Events.TargetInside == EGolmokWeather::Rain && Events.TargetIntensityInside == 0.6f);
			Test->TestTrue(TEXT("... GetRainIntensity is still the old value inside the callback"), Events.RainInside == 0.f);
			FString M;
			Set(EGolmokWeather::Rain, 0.6f, false);
			Test->TestEqual(TEXT("the same target again: no event"), Events.Count, 1);
			W->StepWeather(0.1 * W->GetConfig().TransitionSeconds);
			Test->TestEqual(TEXT("ramp steps: no event"), Events.Count, 1);
			Test->TestTrue(TEXT("rain 0.6 instant during its own transition"), W->SetWeather(EGolmokWeather::Rain, 0.6f, true, M));
			Test->TestTrue(*FString::Printf(TEXT("... lands at once without an event: %s"), *M), Events.Count == 1 && !W->IsTransitioning()
				&& W->GetRainIntensity() == 0.6f && M.EndsWith(TEXT("(transition finished now)")));
			Set(EGolmokWeather::Clear, 0.f, true);
			Test->TestEqual(TEXT("clear instant: second event"), Events.Count, 2);
			Test->TestTrue(TEXT("... (clear, 0, instant)"), Events.Target == EGolmokWeather::Clear && Events.Intensity == 0.f && Events.bInstant);
			Test->TestTrue(TEXT("... the rain inside the callback is still 0.6"), Events.RainInside == 0.6f);
			Test->TestTrue(TEXT("... and 0 after it"), W->GetRainIntensity() == 0.f);
		}

		/** Design section 3: rising rain waits for alpha 0.5; falling rain is over at alpha 0.5. */
		void PrecipitationDelay()
		{
			UGolmokWeatherSubsystem* W = Weather.Get();
			const double T = W->GetConfig().TransitionSeconds;
			Set(EGolmokWeather::Clear, 0.f, true);
			Set(EGolmokWeather::Rain, 0.6f, false);
			W->StepWeather(0.25 * T);
			Test->TestTrue(*FString::Printf(TEXT("rising, alpha 0.25: rain %g == 0"), W->GetRainIntensity()), W->GetRainIntensity() == 0.f);
			W->StepWeather(0.24 * T);
			Test->TestTrue(*FString::Printf(TEXT("rising, alpha 0.49: rain %g == 0"), W->GetRainIntensity()), W->GetRainIntensity() == 0.f);
			W->StepWeather(0.26 * T);
			const double Rising = GolmokWeatherMath::PrecipAt(0.0, static_cast<double>(0.6f), 0.75);
			Test->TestTrue(*FString::Printf(TEXT("rising, alpha 0.75: rain %g == %g"), W->GetRainIntensity(), Rising),
				FMath::IsNearlyEqual(static_cast<double>(W->GetRainIntensity()), Rising, 1e-5) && Rising > 0.0);
			W->StepWeather(0.5 * T); // past alpha 1 (the summed steps are not exact)
			Test->TestTrue(TEXT("rising, alpha 1: rain 0.6"), !W->IsTransitioning() && W->GetRainIntensity() == 0.6f);

			Set(EGolmokWeather::Clear, 0.f, false);
			W->StepWeather(0.25 * T);
			const double Falling = GolmokWeatherMath::PrecipAt(static_cast<double>(0.6f), 0.0, 0.25);
			Test->TestTrue(*FString::Printf(TEXT("falling, alpha 0.25: rain %g == %g"), W->GetRainIntensity(), Falling),
				FMath::IsNearlyEqual(static_cast<double>(W->GetRainIntensity()), Falling, 1e-5) && Falling > 0.0);
			W->StepWeather(0.25 * T);
			Test->TestTrue(*FString::Printf(TEXT("falling, alpha 0.5 (%.4f): rain %g == 0"), W->GetTransitionAlpha(), W->GetRainIntensity()),
				W->GetRainIntensity() == 0.f && W->IsTransitioning());
			W->StepWeather(0.5 * T);
			Test->TestFalse(TEXT("falling, alpha 1: settled"), W->IsTransitioning());
		}

		/** Design section 8 with the repo surface values (60 / 600 / 0.4 / 240 / 1200 s). */
		void SurfaceTable()
		{
			UGolmokWeatherSubsystem* W = Weather.Get();
			struct FRow
			{
				const TCHAR* Label;
				bool bSetWeather;
				EGolmokWeather State;
				float Intensity;
				double Dt;
				float Wetness;
				float Puddle;
			};
			const FRow Rows[] = {
				{TEXT("rain 1.0, 30 s"), true, EGolmokWeather::Rain, 1.f, 30.0, 0.5f, 0.125f},
				{TEXT("rain 1.0, 60 s"), false, EGolmokWeather::Rain, 1.f, 30.0, 1.f, 0.25f},
				{TEXT("rain 0.3 (below puddle_min_intensity), 60 s"), true, EGolmokWeather::Rain, 0.3f, 60.0, 1.f, 0.2f},
				{TEXT("clear, 300 s"), true, EGolmokWeather::Clear, 0.f, 300.0, 0.5f, 0.f},
				{TEXT("clear, 600 s"), false, EGolmokWeather::Clear, 0.f, 300.0, 0.f, 0.f},
			};
			FString M;
			Set(EGolmokWeather::Clear, 0.f, true);
			W->SetSurface(0.f, 0.f, M);
			CheckMpc(TEXT("dry clear"));
			for (const FRow& Row : Rows)
			{
				if (Row.bSetWeather)
				{
					Set(Row.State, Row.Intensity, true);
				}
				W->StepWeather(Row.Dt);
				Test->TestTrue(*FString::Printf(TEXT("surface %s: wet %.4f puddle %.4f == %.4f / %.4f"), Row.Label, W->GetWetness(), W->GetPuddleAmount(), Row.Wetness,
								   Row.Puddle),
					FMath::IsNearlyEqual(W->GetWetness(), Row.Wetness, 1e-5f) && FMath::IsNearlyEqual(W->GetPuddleAmount(), Row.Puddle, 1e-5f));
				Test->TestTrue(*FString::Printf(TEXT("surface %s: puddle <= wetness"), Row.Label), W->GetPuddleAmount() <= W->GetWetness());
				CheckMpc(FString::Printf(TEXT("surface %s"), Row.Label));
			}
		}

		/** "weather: rain 0.60 (from clear 25%) | now 0.00 wet 0.00 puddle 0.00 | fixed | fx <state>" and the debug HUD carries it. */
		void HudLine(UWorld* World)
		{
			UGolmokWeatherSubsystem* W = Weather.Get();
			FString M;
			Set(EGolmokWeather::Clear, 0.f, true);
			W->SetSurface(0.f, 0.f, M);
			Test->TestEqual(TEXT("HUD settled clear"), W->BuildHudLine(),
				FString::Printf(TEXT("weather: clear | now 0.00 wet 0.00 puddle 0.00 | fixed | fx %s"), *W->DescribeFx()));
			Set(EGolmokWeather::Rain, 0.6f, false);
			W->StepWeather(0.25 * W->GetConfig().TransitionSeconds);
			Test->TestEqual(TEXT("HUD rain transition at 25%"), W->BuildHudLine(),
				FString::Printf(TEXT("weather: rain 0.60 (from clear 25%%) | now 0.00 wet 0.00 puddle 0.00 | fixed | fx %s"), *W->DescribeFx()));
			Set(EGolmokWeather::Clear, 0.f, true);
			if (UGolmokDebugSubsystem* Debug = World->GetSubsystem<UGolmokDebugSubsystem>())
			{
				const TArray<FString>& Lines = Debug->GetHudLines();
				Test->TestTrue(TEXT("the debug HUD has a 'weather: ' line (provider)"), Lines.ContainsByPredicate([](const FString& L) { return L.StartsWith(TEXT("weather: ")); }));
			}
			else
			{
				Test->AddError(TEXT("UGolmokDebugSubsystem missing in the PIE world"));
			}
		}

		/** Design 7-3: interior, fx off, idle, travel reset (NS_GolmokRain present), or the missing state. */
		void RainFx(UWorld* World)
		{
			UGolmokWeatherSubsystem* W = Weather.Get();
			AGolmokTimeOfDay* Tod = TimeOfDay.Get();
			Set(EGolmokWeather::Rain, 1.f, true);

			// Interior bookkeeping runs with or without the asset.
			Tod->EnterInterior(InteriorSource);
			Test->TestTrue(TEXT("interior: status says interior yes"), W->DescribeStatus().Contains(TEXT("interior yes")));
			Tod->ExitInterior(InteriorSource);
			Test->TestTrue(TEXT("outside: status says interior no"), W->DescribeStatus().Contains(TEXT("interior no")));

			AActor* Fx = RainFxActor(W);
			if (!Fx)
			{
				const FString Expected = W->GetConfig().bRainFxEnabled ? TEXT("missing") : TEXT("disabled");
				Test->TestEqual(TEXT("fx state without NS_GolmokRain"), W->DescribeFx(), Expected);
				Test->AddInfo(NsSkipped);
				Set(EGolmokWeather::Clear, 0.f, true);
				return;
			}
			Test->AddInfo(TEXT("NS_GolmokRain present: EXECUTED"));
			Test->TestEqual(TEXT("rain 1.0: fx on"), W->DescribeFx(), FString(TEXT("on")));
			Test->TestTrue(TEXT("rain 1.0: component active"), GolmokWeatherRainFx::IsActive(Fx));
			float Rain = -1.f, SpawnRate = -1.f;
			FVector Box = FVector::ZeroVector;
			Test->TestTrue(TEXT("NS_GolmokRain exposes the three user parameters (design 7-2)"), GolmokWeatherRainFx::HasUserParameters(Fx));
			if (Test->TestTrue(TEXT("the three user parameters exist on the component (design 17 #4)"), GolmokWeatherRainFx::ReadUserParameters(Fx, Rain, SpawnRate, Box)))
			{
				Test->TestTrue(*FString::Printf(TEXT("User.RainIntensity %g == RainNow"), Rain), FMath::IsNearlyEqual(Rain, W->GetRainIntensity(), 1e-6f));
				Test->TestTrue(*FString::Printf(TEXT("User.SpawnRate %g == RainNow x max_spawn_rate"), SpawnRate),
					FMath::IsNearlyEqual(static_cast<double>(SpawnRate), static_cast<double>(W->GetRainIntensity()) * W->GetConfig().MaxSpawnRate, 0.5));
				Test->TestTrue(*FString::Printf(TEXT("User.BoxHalfExtent %s"), *Box.ToString()), Box.Equals(W->GetConfig().BoxHalfExtentCm, 0.01));
			}
			const APlayerController* PC = World->GetFirstPlayerController();
			const APlayerCameraManager* Camera = PC ? PC->PlayerCameraManager.Get() : nullptr;
			if (Camera)
			{
				W->StepWeather(0.0);
				const FVector Expected = Camera->GetCameraLocation() + FVector(0.0, 0.0, W->GetConfig().HeightOffsetCm);
				Test->TestTrue(TEXT("the fx follows the camera + height_offset_cm"), Fx->GetActorLocation().Equals(Expected, 1.0));
			}

			Tod->EnterInterior(InteriorSource);
			Test->TestEqual(TEXT("interior: fx interior"), W->DescribeFx(), FString(TEXT("interior")));
			// Deactivate() lets live particles finish; whether IsActive() drops at once is engine detail [미확인 §17 #5]:
			// the subsystem's own state is asserted, the component flag is recorded for the runbook.
			Test->AddInfo(FString::Printf(TEXT("interior: component IsActive %d after Deactivate()"), GolmokWeatherRainFx::IsActive(Fx) ? 1 : 0));
			Tod->ExitInterior(InteriorSource);
			Test->TestEqual(TEXT("outside again: fx on"), W->DescribeFx(), FString(TEXT("on")));
			Test->TestTrue(TEXT("outside again: component active (Activate(true))"), GolmokWeatherRainFx::IsActive(Fx));

			W->SetFxEnabled(false);
			Test->TestEqual(TEXT("fx off"), W->DescribeFx(), FString(TEXT("off")));
			W->SetFxEnabled(true);
			Test->TestEqual(TEXT("fx on again"), W->DescribeFx(), FString(TEXT("on")));

			if (UGolmokTravelSubsystem* Travel = UGolmokTravelSubsystem::Get(World))
			{
				// R112-U7: the travel arrival reset is checked as its two halves, the OnTraveled binding and ResetRainFx()
				// itself. Broadcasting OnTraveled here would also run UGolmokSaveSubsystem::OnTraveled (a visit of a fake
				// zone, ReleaseHold, MarkDirty) in the PIE world.
				Test->TestTrue(TEXT("the weather subsystem is bound to OnTraveled"), Travel->OnTraveled.IsBoundToObject(W));
				const int32 ResetsBefore = W->GetRainFxResetCount();
				W->ResetRainFx(); // what UGolmokWeatherSubsystem::Traveled does on the travel arrival
				Test->TestEqual(TEXT("ResetRainFx counted once"), W->GetRainFxResetCount(), ResetsBefore + 1);
				Test->TestTrue(TEXT("after ResetRainFx: rain fx reset and still active"), GolmokWeatherRainFx::IsActive(Fx));
				Test->TestTrue(TEXT("after ResetRainFx: weather unchanged"), W->GetTargetWeather() == EGolmokWeather::Rain && W->GetRainIntensity() == 1.f);
				if (Camera)
				{
					const FVector Expected = Camera->GetCameraLocation() + FVector(0.0, 0.0, W->GetConfig().HeightOffsetCm);
					Test->TestTrue(TEXT("after ResetRainFx: the fx sits at the camera"), Fx->GetActorLocation().Equals(Expected, 1.0));
				}
			}
			else
			{
				Test->AddInfo(TEXT("UGolmokTravelSubsystem missing - travel reset skipped"));
			}

			Set(EGolmokWeather::Clear, 0.f, true);
			Test->TestEqual(TEXT("clear: fx idle"), W->DescribeFx(), FString(TEXT("idle")));
			Rain = -1.f;
			GolmokWeatherRainFx::ReadUserParameters(Fx, Rain, SpawnRate, Box);
			Test->TestTrue(TEXT("clear: User.RainIntensity 0"), Rain == 0.f);
		}

		/** Photo mode (GamePause): enter at alpha 0.6 of a rain transition (rain falling); ExitPhoto checks the continuation. */
		bool EnterPhoto(UWorld* World)
		{
			UGolmokWeatherSubsystem* W = Weather.Get();
			const double T = W->GetConfig().TransitionSeconds;
			Set(EGolmokWeather::Clear, 0.f, true);
			FString M;
			W->SetSurface(0.3f, 0.1f, M);
			Set(EGolmokWeather::Rain, 0.6f, false);
			W->StepWeather(0.6 * T); // alpha 0.6: the rain has started
			UGolmokPhotoModeSubsystem* Photo = UGolmokPhotoModeSubsystem::Get(World);
			FString Message;
			if (!Photo || !Photo->Enter(Message))
			{
				Test->AddInfo(FString::Printf(TEXT("photo mode refused (%s) - photo step skipped"), Photo ? *Message : TEXT("no subsystem")));
				Set(EGolmokWeather::Clear, 0.f, true);
				return Next(static_cast<int32>(ERuntimePhase::Done));
			}
			Test->TestTrue(TEXT("photo mode: IsFrozen"), W->IsFrozen());
			AlphaAtEnter = W->GetTransitionAlpha();
			RainAtEnter = W->GetRainIntensity();
			WetAtEnter = W->GetWetness();
			W->StepWeather(0.2 * T);
			CheckFrozen(TEXT("photo mode, StepWeather by hand"));
			Test->TestFalse(TEXT("photo mode: rain heavy refused"), Run({TEXT("rain"), TEXT("heavy")}, M));
			Test->TestEqual(TEXT("photo mode: refusal message"), M, FString(PhotoRefusal));
			Test->TestFalse(TEXT("photo mode: SetWeather refused"), W->SetWeather(EGolmokWeather::Clear, 0.f, true, M));
			Test->TestFalse(TEXT("photo mode: mode schedule refused"), Run({TEXT("mode"), TEXT("schedule")}, M));
			Test->TestFalse(TEXT("photo mode: surface refused"), Run({TEXT("surface"), TEXT("1")}, M));
			Test->TestFalse(TEXT("photo mode: fx off refused"), Run({TEXT("fx"), TEXT("off")}, M) || !W->IsFxEnabled());
			Test->TestTrue(TEXT("photo mode: status works"), Run({TEXT("status")}, M) && M.Contains(TEXT("frozen yes")));
			Test->TestTrue(TEXT("photo mode: list works"), Run({TEXT("list")}, M));
			Test->TestTrue(TEXT("photo mode: HUD ends with frozen"), W->BuildHudLine().EndsWith(TEXT(" | frozen")));
			Test->TestTrue(TEXT("photo mode: the target is unchanged"), W->GetTargetWeather() == EGolmokWeather::Rain && W->GetTargetIntensity() == 0.6f);
			return Next(static_cast<int32>(ERuntimePhase::PhotoActive));
		}

		void CheckFrozen(const TCHAR* What)
		{
			UGolmokWeatherSubsystem* W = Weather.Get();
			Test->TestTrue(*FString::Printf(TEXT("%s: alpha %.4f unchanged"), What, W->GetTransitionAlpha()), W->GetTransitionAlpha() == AlphaAtEnter);
			Test->TestTrue(*FString::Printf(TEXT("%s: rain unchanged"), What), W->GetRainIntensity() == RainAtEnter);
			Test->TestTrue(*FString::Printf(TEXT("%s: wetness unchanged"), What), W->GetWetness() == WetAtEnter);
		}

		void ExitPhoto(UWorld* World)
		{
			UGolmokWeatherSubsystem* W = Weather.Get();
			UGolmokPhotoModeSubsystem* Photo = UGolmokPhotoModeSubsystem::Get(World);
			CheckFrozen(TEXT("photo mode, editor frames while paused"));
			Test->TestTrue(TEXT("Exit(test)"), Photo && Photo->Exit(TEXT("test")));
			Test->TestFalse(TEXT("after Exit: not frozen"), W->IsFrozen());
			W->StepWeather(0.1 * W->GetConfig().TransitionSeconds);
			Test->TestTrue(*FString::Printf(TEXT("after Exit: alpha continues %.4f -> %.4f"), AlphaAtEnter, W->GetTransitionAlpha()),
				FMath::IsNearlyEqual(W->GetTransitionAlpha(), AlphaAtEnter + 0.1f, 1e-4f));
			Test->TestTrue(TEXT("after Exit: the rain moves on"), W->GetRainIntensity() > RainAtEnter);
			Set(EGolmokWeather::Clear, 0.f, true);
			FString M;
			W->SetSurface(0.f, 0.f, M);
			Test->AddInfo(FString::Printf(TEXT("end: %s"), *W->BuildHudLine()));
		}

		TWeakObjectPtr<UMaterialParameterCollection> Mpc;
		float AlphaAtEnter = 0.f;
		float RainAtEnter = 0.f;
		float WetAtEnter = 0.f;
	};
} // namespace GolmokWeatherTests

// ---- Golmok.Weather.Lighting / Golmok.Weather.Runtime ------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokWeatherLightingTest, "Golmok.Weather.Lighting",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokWeatherLightingTest::RunTest(const FString& Parameters)
{
	using namespace GolmokWeatherTests;

	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FLightingScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokWeatherRuntimeTest, "Golmok.Weather.Runtime",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokWeatherRuntimeTest::RunTest(const FString& Parameters)
{
	using namespace GolmokWeatherTests;

	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FRuntimeScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

#endif
