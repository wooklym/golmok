#pragma once

#include "CoreMinimal.h"
#include "Weather/GolmokWeatherMath.h"

/**
 * WP-16a weather configuration: Config/Golmok/weather.json schema 1 (design section 6). Parsing is all-or-nothing
 * and strict (exact key sets); golmok/weather_pure.py parse_config applies the same rules with the same messages
 * ("weather.json: <where>: <reason>"), checked by tools/tests/test_ue_config_weather.py and Golmok.Weather.Config.
 */
namespace GolmokWeather
{
	/** One schedule slot: "time" HH:MM, a state, and an intensity for rain (0 otherwise). */
	struct FScheduleSlot
	{
		double Minutes = 0.0;
		GolmokWeatherMath::State State = GolmokWeatherMath::State::Clear;
		double Intensity = 0.0;
	};

	struct GOLMOK_API FConfig
	{
		int32 SchemaVersion = 1;
		GolmokWeatherMath::State InitialState = GolmokWeatherMath::State::Clear;
		double InitialIntensity = 0.0;
		/** initial.mode == "schedule". */
		bool bInitialSchedule = false;
		double TransitionSeconds = 20.0;
		/** rain_levels light / moderate / heavy. */
		double RainLight = 0.3;
		double RainModerate = 0.6;
		double RainHeavy = 1.0;
		GolmokWeatherMath::Modifier Overcast;
		GolmokWeatherMath::Modifier Rain;
		GolmokWeatherMath::SurfaceParams Surface;
		TArray<FScheduleSlot> Schedule;
		/** Minutes of Schedule (same order) for GolmokWeatherMath::ScheduleIndexAt. */
		TArray<double> ScheduleTimes;
		FString RainFxSystem;
		bool bRainFxEnabled = true;
		double MaxSpawnRate = 12000.0;
		FVector BoxHalfExtentCm = FVector(1000.0, 1000.0, 500.0);
		double HeightOffsetCm = 300.0;
		FString Mpc;
	};

	/** All or nothing: false leaves Out untouched and sets Error to "weather.json: <where>: <reason>". */
	GOLMOK_API bool ParseConfigText(const FString& Json, FConfig& Out, FString& Error);
	GOLMOK_API bool LoadConfigFile(const FString& FilePath, FConfig& Out, FString& Error);
	/** FPaths::ProjectConfigDir() / "Golmok/weather.json". */
	GOLMOK_API FString DefaultConfigPath();
	/** "light" | "moderate" | "heavy" -> the config's level; false for anything else. */
	GOLMOK_API bool ResolveRainLevel(const FConfig& Config, const FString& Word, double& OutIntensity);
} // namespace GolmokWeather
