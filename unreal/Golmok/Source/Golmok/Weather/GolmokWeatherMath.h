#pragma once

// Pure weather rules (WP-16a design sections 2-5 and 8). No engine headers: UGolmokWeatherSubsystem and
// AGolmokTimeOfDay use it, tools/tests/test_ue_weather_math.py compiles it with g++
// (fixtures/ue/weathermath_driver.cpp) and golmok/weather_pure.py mirrors every rule and contract name here.

#include <cmath>
#include <cstdint>

#include "Lighting/GolmokClockMath.h"

namespace GolmokWeatherMath
{
	/** Same order as the UENUM EGolmokWeather (static_assert in GolmokWeatherSubsystem.cpp). */
	enum class State : std::uint8_t
	{
		Clear = 0,
		Overcast = 1,
		Rain = 2,
	};
	constexpr int StateCount = 3;

	/** Rain intensity range (design section 2); clear / overcast carry 0. */
	constexpr double MinRainIntensity = 0.05;
	constexpr double MaxRainIntensity = 1.0;
	/** RainNow above this wets the surface (design section 8). */
	constexpr double WetRainThreshold = 0.01;
	/** MPC / Niagara values are written only when they move more than this; RainNow at or below it idles the rain fx. */
	constexpr double ValueEpsilon = 0.001;
	/** transition_seconds range [0, MaxTransitionSeconds]. */
	constexpr double MaxTransitionSeconds = 600.0;

	// ---- contract names (design sections 7-2 and 8; pytest checks them against weather_pure.py) ----
	/** MPC_GolmokWeather scalar parameters, in this order, default 0. */
	constexpr const char* MpcRainIntensity = "RainIntensity";
	constexpr const char* MpcWetness = "Wetness";
	constexpr const char* MpcPuddleAmount = "PuddleAmount";
	/** NS_GolmokRain user parameters. */
	constexpr const char* UserRainIntensity = "User.RainIntensity";
	constexpr const char* UserSpawnRate = "User.SpawnRate";
	constexpr const char* UserBoxHalfExtent = "User.BoxHalfExtent";

	inline const char* StateName(State S)
	{
		switch (S)
		{
		case State::Overcast:
			return "overcast";
		case State::Rain:
			return "rain";
		case State::Clear:
		default:
			return "clear";
		}
	}

	/** Exact, case-sensitive "clear" | "overcast" | "rain". Works for char / wchar_t / TCHAR. */
	template <typename CharT>
	bool ParseState(const CharT* Text, State& Out)
	{
		if (!Text)
		{
			return false;
		}
		for (int I = 0; I < StateCount; ++I)
		{
			const char* Name = StateName(static_cast<State>(I));
			int K = 0;
			while (Name[K] != '\0' && Text[K] == static_cast<CharT>(Name[K]))
			{
				++K;
			}
			if (Name[K] == '\0' && Text[K] == CharT(0))
			{
				Out = static_cast<State>(I);
				return true;
			}
		}
		return false;
	}

	inline bool IsValidRainIntensity(double I)
	{
		return std::isfinite(I) && I >= MinRainIntensity && I <= MaxRainIntensity;
	}

	/** The rain the target asks for: Intensity for Rain, 0 otherwise. */
	inline double TargetRain(State S, double Intensity)
	{
		return S == State::Rain ? Intensity : 0.0;
	}

	// ---- lighting modifier (design section 5) ----

	/** Seven fields; the defaults are the identity (clear). */
	struct Modifier
	{
		double LuxScale = 1.0;
		double SkyScale = 1.0;
		double FogScale = 1.0;
		double FogHeightFalloffScale = 1.0;
		double KelvinTarget = 6500.0;
		double KelvinWeight = 0.0;
		double ExposureOffset = 0.0;
	};

	constexpr int ModifierFieldCount = 7;

	/** weather.json key, parser range and whether the minimum is exclusive, in Modifier field order. */
	struct FieldRange
	{
		const char* Key;
		double Min;
		double Max;
		bool bMinExclusive;
	};

	inline const FieldRange& ModifierField(int Index)
	{
		static const FieldRange Fields[ModifierFieldCount] = {
			{"lux_scale", 0.0, 2.0, true},
			{"sky_scale", 0.0, 2.0, true},
			{"fog_scale", 0.0, 5.0, true},
			{"fog_height_falloff_scale", 0.0, 2.0, true},
			{"kelvin_target", 2000.0, 12000.0, false},
			{"kelvin_weight", 0.0, 1.0, false},
			{"exposure_offset", -2.0, 2.0, false},
		};
		return Fields[Index < 0 ? 0 : (Index >= ModifierFieldCount ? ModifierFieldCount - 1 : Index)];
	}

	inline double GetField(const Modifier& M, int Index)
	{
		switch (Index)
		{
		case 0: return M.LuxScale;
		case 1: return M.SkyScale;
		case 2: return M.FogScale;
		case 3: return M.FogHeightFalloffScale;
		case 4: return M.KelvinTarget;
		case 5: return M.KelvinWeight;
		default: return M.ExposureOffset;
		}
	}

	inline void SetField(Modifier& M, int Index, double Value)
	{
		switch (Index)
		{
		case 0: M.LuxScale = Value; break;
		case 1: M.SkyScale = Value; break;
		case 2: M.FogScale = Value; break;
		case 3: M.FogHeightFalloffScale = Value; break;
		case 4: M.KelvinTarget = Value; break;
		case 5: M.KelvinWeight = Value; break;
		default: M.ExposureOffset = Value; break;
		}
	}

	/** Value inside the field's parser range (NaN / inf never are). */
	inline bool IsFieldInRange(int Index, double Value)
	{
		const FieldRange& R = ModifierField(Index);
		if (!std::isfinite(Value) || Value > R.Max)
		{
			return false;
		}
		return R.bMinExclusive ? Value > R.Min : Value >= R.Min;
	}

	/** Every field that changes a value is at its identity (KelvinTarget alone does not change anything). */
	inline bool IsIdentity(const Modifier& M)
	{
		return M.LuxScale == 1.0 && M.SkyScale == 1.0 && M.FogScale == 1.0 && M.FogHeightFalloffScale == 1.0 && M.KelvinWeight == 0.0 &&
			M.ExposureOffset == 0.0;
	}

	/** The part of FGolmokLightingState the modifier touches (sun rotation and volumetric never change). */
	struct Light
	{
		double Lux = 0.0;
		bool bUseTemperature = false;
		double Kelvin = 6500.0;
		double Sky = 1.0;
		double Fog = 0.0;
		double FogHeightFalloff = 0.2;
		bool bExposureOverridden = false;
		double ExposureBias = 0.0;
	};

	/**
	 * Design 5-1. The identity returns In unchanged (bit for bit), so clear keeps every earlier expectation. Kelvin
	 * moves only while the sun uses a temperature; a non-zero exposure offset turns the override on and adds to the
	 * effective bias (the volume's value or the engine default the caller put in ExposureBias).
	 */
	inline Light Apply(const Light& In, const Modifier& M)
	{
		if (IsIdentity(M))
		{
			return In;
		}
		Light R = In;
		R.Lux = In.Lux * M.LuxScale;
		R.Sky = In.Sky * M.SkyScale;
		R.Fog = In.Fog * M.FogScale;
		R.FogHeightFalloff = In.FogHeightFalloff * M.FogHeightFalloffScale;
		if (In.bUseTemperature && M.KelvinWeight != 0.0)
		{
			R.Kelvin = In.Kelvin + (M.KelvinTarget - In.Kelvin) * M.KelvinWeight;
		}
		if (M.ExposureOffset != 0.0)
		{
			R.bExposureOverridden = true;
			R.ExposureBias = In.ExposureBias + M.ExposureOffset;
		}
		return R;
	}

	inline double Clamp01(double X)
	{
		if (!(X > 0.0)) // NaN -> 0
		{
			return 0.0;
		}
		return X > 1.0 ? 1.0 : X;
	}

	/** Linear in log2 for the four scales (all > 0), linear for the rest. T <= 0 returns A, T >= 1 returns B exactly. */
	inline Modifier Lerp(const Modifier& A, const Modifier& B, double T)
	{
		if (!(T > 0.0))
		{
			return A;
		}
		if (T >= 1.0)
		{
			return B;
		}
		auto LogLerp = [T](double X, double Y) { return std::exp2(std::log2(X) + (std::log2(Y) - std::log2(X)) * T); };
		auto LinLerp = [T](double X, double Y) { return X + (Y - X) * T; };
		Modifier R;
		R.LuxScale = LogLerp(A.LuxScale, B.LuxScale);
		R.SkyScale = LogLerp(A.SkyScale, B.SkyScale);
		R.FogScale = LogLerp(A.FogScale, B.FogScale);
		R.FogHeightFalloffScale = LogLerp(A.FogHeightFalloffScale, B.FogHeightFalloffScale);
		R.KelvinTarget = LinLerp(A.KelvinTarget, B.KelvinTarget);
		R.KelvinWeight = LinLerp(A.KelvinWeight, B.KelvinWeight);
		R.ExposureOffset = LinLerp(A.ExposureOffset, B.ExposureOffset);
		return R;
	}

	/** Target modifier: clear = identity, overcast = Overcast, rain(I) = Lerp(Overcast, Rain, I). */
	inline Modifier ForState(State S, double Intensity, const Modifier& Overcast, const Modifier& Rain)
	{
		switch (S)
		{
		case State::Overcast:
			return Overcast;
		case State::Rain:
			return Lerp(Overcast, Rain, Clamp01(Intensity));
		case State::Clear:
		default:
			return Modifier();
		}
	}

	// ---- transition (design section 3) ----

	inline double Smoothstep(double X)
	{
		const double T = Clamp01(X);
		return T * T * (3.0 - 2.0 * T);
	}

	/** Precipitation progress at transition alpha: increasing rain waits for the sky's first half, decreasing rain stops in the first half. */
	inline double PrecipAlpha(double Alpha, bool bIncreasing)
	{
		return bIncreasing ? Smoothstep(2.0 * Alpha - 1.0) : Smoothstep(2.0 * Alpha);
	}

	/** RainNow during a transition from RStart to RTarget at alpha (RTarget at alpha >= 1). */
	inline double PrecipAt(double RStart, double RTarget, double Alpha)
	{
		if (Alpha >= 1.0)
		{
			return RTarget;
		}
		return RStart + (RTarget - RStart) * PrecipAlpha(Alpha, RTarget > RStart);
	}

	/** Lighting modifier during a transition at alpha (MTarget at alpha >= 1). */
	inline Modifier ModifierAt(const Modifier& MStart, const Modifier& MTarget, double Alpha)
	{
		if (Alpha >= 1.0)
		{
			return MTarget;
		}
		return Lerp(MStart, MTarget, Smoothstep(Alpha));
	}

	// ---- surface (design section 8) ----

	struct SurfaceParams
	{
		double WetSeconds = 60.0;
		double DrySeconds = 600.0;
		double PuddleMinIntensity = 0.4;
		double PuddleFillSeconds = 240.0;
		double PuddleDrySeconds = 1200.0;
	};

	struct Surface
	{
		double Wetness = 0.0;
		double Puddle = 0.0;
	};

	/** One step of Dt world seconds with RainNow = Rain; both values stay in [0, 1] and Puddle <= Wetness. */
	inline Surface StepSurface(const Surface& S, double Rain, double Dt, const SurfaceParams& P)
	{
		Surface R = S;
		const double Step = (std::isfinite(Dt) && Dt > 0.0) ? Dt : 0.0;
		if (Rain > WetRainThreshold)
		{
			R.Wetness += Step * Rain / P.WetSeconds;
		}
		else
		{
			R.Wetness -= Step / P.DrySeconds;
		}
		if (Rain > P.PuddleMinIntensity)
		{
			R.Puddle += Step * (Rain - P.PuddleMinIntensity) / (1.0 - P.PuddleMinIntensity) / P.PuddleFillSeconds;
		}
		else
		{
			R.Puddle -= Step / P.PuddleDrySeconds;
		}
		R.Wetness = Clamp01(R.Wetness);
		R.Puddle = Clamp01(R.Puddle);
		if (R.Puddle > R.Wetness)
		{
			R.Puddle = R.Wetness;
		}
		return R;
	}

	/** Clamps a set value (golmok.weather surface, a save) the same way: [0, 1] each, Puddle <= Wetness. */
	inline Surface ClampSurface(double Wetness, double Puddle)
	{
		Surface R;
		R.Wetness = Clamp01(Wetness);
		R.Puddle = Clamp01(Puddle);
		if (R.Puddle > R.Wetness)
		{
			R.Puddle = R.Wetness;
		}
		return R;
	}

	// ---- schedule (design section 4) ----

	/**
	 * Index of the slot in force at Minutes (wrapped into the day): the last slot whose time is <= Minutes, or the last
	 * slot before the first one (it runs across midnight). Times strictly increasing in [0, 1440); -1 when Count <= 0.
	 */
	inline int ScheduleIndexAt(double Minutes, const double* Times, int Count)
	{
		if (!Times || Count <= 0)
		{
			return -1;
		}
		const double M = GolmokClockMath::WrapMinutes(Minutes);
		int Index = Count - 1;
		for (int I = 0; I < Count; ++I)
		{
			if (Times[I] <= M)
			{
				Index = I;
			}
			else
			{
				break;
			}
		}
		return Index;
	}
} // namespace GolmokWeatherMath
