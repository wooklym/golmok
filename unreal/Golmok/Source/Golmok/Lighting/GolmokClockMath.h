#pragma once

// Pure time-of-day clock math (WP-14a design sections 1-3 and 2a, keyframe holds). No engine headers:
// AGolmokTimeOfDay uses it and tools/tests/test_ue_clock_math.py compiles it with g++
// (fixtures/ue/clockmath_driver.cpp) to pin the rules; golmok/lighting_presets.py mirrors the keyframe rules.

#include <cmath>

namespace GolmokClockMath
{
	constexpr double MinutesPerDay = 1440.0;
	/** The sun is shown while the interpolated lux is above this (every clock tick, not only at transition ends). */
	constexpr double SunVisibleLux = 0.01;
	/** golmok.tod rate range: (0, MaxRate] game minutes per real second (1440 = a day per second). */
	constexpr double MaxRate = 1440.0;
	/** Realtime: a gap larger than this between the clock and the local time (photo mode, a hitch, a pause) re-syncs with a transition. */
	constexpr double ResyncMinutes = 1.0;
	/** Realtime: a real-time gap between two clock steps longer than this (or than TransitionSeconds, whichever is larger) also re-syncs with a transition (a GamePause photo mode stops the tick). */
	constexpr double ResyncGapSeconds = 2.0;

	/** Any finite minutes -> [0, 1440); non-finite -> 0. */
	inline double WrapMinutes(double Minutes)
	{
		if (!std::isfinite(Minutes))
		{
			return 0.0;
		}
		double R = std::fmod(Minutes, MinutesPerDay);
		if (R < 0.0)
		{
			R += MinutesPerDay;
		}
		// -1e-17 + 1440 rounds to 1440.
		return R >= MinutesPerDay ? 0.0 : R;
	}

	/** Shortest distance around the day between two times (0..720). */
	inline double CircularDistance(double A, double B)
	{
		const double D = WrapMinutes(A - B);
		return D > MinutesPerDay * 0.5 ? MinutesPerDay - D : D;
	}

	/** "HH:MM" with exactly two digits each, HH 00-23, MM 00-59 -> 0..1439. Works for char / wchar_t / TCHAR. */
	template <typename CharT>
	bool ParseHHMM(const CharT* Text, int& OutMinutes)
	{
		OutMinutes = 0;
		if (!Text)
		{
			return false;
		}
		auto Digit = [](CharT C, int& Out) -> bool
		{
			if (C < CharT('0') || C > CharT('9'))
			{
				return false;
			}
			Out = static_cast<int>(C - CharT('0'));
			return true;
		};
		int H1 = 0, H2 = 0, M1 = 0, M2 = 0;
		if (!Digit(Text[0], H1) || !Digit(Text[1], H2) || Text[2] != CharT(':') || !Digit(Text[3], M1) || !Digit(Text[4], M2)
			|| Text[5] != CharT(0))
		{
			return false;
		}
		const int Hours = H1 * 10 + H2;
		const int Minutes = M1 * 10 + M2;
		if (Hours > 23 || Minutes > 59)
		{
			return false;
		}
		OutMinutes = Hours * 60 + Minutes;
		return true;
	}

	/** Whole minute of the day shown for Minutes (floor after wrapping): 0..1439. */
	inline int MinuteOfDay(double Minutes)
	{
		const int M = static_cast<int>(std::floor(WrapMinutes(Minutes)));
		return M < 0 ? 0 : (M > 1439 ? 1439 : M);
	}

	/** "HH:MM" (floor, wrapped) into Out[6] including the terminator. */
	template <typename CharT>
	void FormatHHMM(double Minutes, CharT (&Out)[6])
	{
		const int M = MinuteOfDay(Minutes);
		const int H = M / 60;
		const int Mm = M % 60;
		Out[0] = static_cast<CharT>(CharT('0') + H / 10);
		Out[1] = static_cast<CharT>(CharT('0') + H % 10);
		Out[2] = CharT(':');
		Out[3] = static_cast<CharT>(CharT('0') + Mm / 10);
		Out[4] = static_cast<CharT>(CharT('0') + Mm % 10);
		Out[5] = CharT(0);
	}

	/** Clock mode step: Minutes + Rate * DeltaSeconds, wrapped. A negative / non-finite step leaves Minutes as is. */
	inline double Advance(double Minutes, double Rate, double DeltaSeconds)
	{
		const double Step = Rate * DeltaSeconds;
		if (!std::isfinite(Step) || Step < 0.0)
		{
			return WrapMinutes(Minutes);
		}
		return WrapMinutes(Minutes + Step);
	}

	inline bool IsValidRate(double Rate)
	{
		return std::isfinite(Rate) && Rate > 0.0 && Rate <= MaxRate;
	}

	/** Design 2a: a keyframe "hold_minutes" is a finite number >= 0. */
	inline bool IsValidHold(double Hold)
	{
		return std::isfinite(Hold) && Hold >= 0.0;
	}

	/** Design 2a: where a keyframe's hold ends (Time + Hold wrapped; the last keyframe's hold may cross midnight). */
	inline double HoldEnd(double Time, double Hold)
	{
		return WrapMinutes(Time + Hold);
	}

	/** The two keyframes around a time and the 0..1 position between them. */
	struct KeyframeSpan
	{
		int Prev = -1;
		int Next = -1;
		double Alpha = 0.0;
		/** Design 2a: inside Prev's hold. Alpha is 0 (the state is Prev's) and Next is the keyframe the ramp heads to. */
		bool bHeld = false;
		bool IsValid() const { return Prev >= 0 && Next >= 0; }
		/** Nearest keyframe: Prev below the midpoint, Next from it on (CurrentPreset, OnPresetChanged). */
		int Nearest() const { return Alpha < 0.5 ? Prev : Next; }
	};

	/**
	 * Times[0..Count) strictly increasing in [0, 1440) (the parser guarantees it). At a keyframe time Alpha is 0 and
	 * Prev is that keyframe. Past the last keyframe the span wraps through midnight to the first one; its width is
	 * 1440 - last + first. Count 1 -> Prev = Next = 0, Alpha 0. Count <= 0 -> invalid span.
	 *
	 * Design 2a: Holds[0..Count) (nullptr = no holds; an invalid entry counts as 0) keeps keyframe i for Holds[i]
	 * minutes from Times[i] (Alpha 0, bHeld); after the hold the span ramps from the hold end to the next keyframe:
	 * Alpha = (elapsed - hold) / (width - hold). The hold end itself is the ramp start (Alpha 0, not held).
	 */
	inline KeyframeSpan FindKeyframes(double Minutes, const double* Times, const double* Holds, int Count)
	{
		KeyframeSpan Span;
		if (!Times || Count <= 0)
		{
			return Span;
		}
		auto HoldOf = [Holds](int Index) -> double { return Holds && IsValidHold(Holds[Index]) ? Holds[Index] : 0.0; };
		const double T = WrapMinutes(Minutes);
		if (Count == 1)
		{
			Span.Prev = Span.Next = 0;
			Span.bHeld = WrapMinutes(T - Times[0]) < HoldOf(0);
			return Span;
		}
		int Prev = Count - 1;
		for (int i = 0; i < Count; ++i)
		{
			if (Times[i] <= T)
			{
				Prev = i;
			}
		}
		const int Next = Prev + 1 < Count ? Prev + 1 : 0;
		double Width = Times[Next] - Times[Prev];
		double Elapsed = T - Times[Prev];
		if (Next == 0)
		{
			Width += MinutesPerDay;
			if (Elapsed < 0.0)
			{
				Elapsed += MinutesPerDay; // before the first keyframe: still in the last -> first span
			}
		}
		Span.Prev = Prev;
		Span.Next = Next;
		const double Hold = HoldOf(Prev);
		if (Elapsed < Hold)
		{
			Span.bHeld = true; // Alpha stays 0: the held keyframe's own values
			return Span;
		}
		const double Ramp = Width - Hold;
		const double Alpha = Ramp > 0.0 ? (Elapsed - Hold) / Ramp : 0.0;
		Span.Alpha = Alpha < 0.0 ? 0.0 : (Alpha > 1.0 ? 1.0 : Alpha);
		return Span;
	}

	/** Without holds (every hold 0). */
	inline KeyframeSpan FindKeyframes(double Minutes, const double* Times, int Count)
	{
		return FindKeyframes(Minutes, Times, nullptr, Count);
	}

	inline double Lerp(double A, double B, double Alpha)
	{
		return A + (B - A) * Alpha;
	}

	/** Yaw along the shorter arc (350 -> 10 passes 0), result in [0, 360). A 180 degree tie turns positive. */
	inline double LerpYawShortest(double A, double B, double Alpha)
	{
		double D = std::fmod(B - A, 360.0);
		if (D > 180.0)
		{
			D -= 360.0;
		}
		else if (D <= -180.0)
		{
			D += 360.0;
		}
		double R = std::fmod(A + D * Alpha, 360.0);
		if (R < 0.0)
		{
			R += 360.0;
		}
		return R >= 360.0 ? 0.0 : R;
	}

	/** The interpolated values of one keyframe (a complete cycle preset). */
	struct LightKey
	{
		double Pitch = 0.0;
		double Yaw = 0.0;
		double Lux = 0.0;
		double Kelvin = 6500.0;
		double Sky = 1.0;
		double Fog = 0.0;
		double FogHeightFalloff = 0.2;
		double ExposureBias = 0.0;
		bool bVolumetric = false;
	};

	/** Design section 3: yaw on the shortest arc, the other numbers linear, volumetric = A below alpha 0.5 else B. */
	inline LightKey Interpolate(const LightKey& A, const LightKey& B, double Alpha)
	{
		LightKey R;
		R.Pitch = Lerp(A.Pitch, B.Pitch, Alpha);
		R.Yaw = LerpYawShortest(A.Yaw, B.Yaw, Alpha);
		R.Lux = Lerp(A.Lux, B.Lux, Alpha);
		R.Kelvin = Lerp(A.Kelvin, B.Kelvin, Alpha);
		R.Sky = Lerp(A.Sky, B.Sky, Alpha);
		R.Fog = Lerp(A.Fog, B.Fog, Alpha);
		R.FogHeightFalloff = Lerp(A.FogHeightFalloff, B.FogHeightFalloff, Alpha);
		R.ExposureBias = Lerp(A.ExposureBias, B.ExposureBias, Alpha);
		R.bVolumetric = Alpha < 0.5 ? A.bVolumetric : B.bVolumetric;
		return R;
	}

	inline bool IsSunVisible(double Lux)
	{
		return Lux > SunVisibleLux;
	}

	inline bool IsNight(double Lux, double Threshold)
	{
		return Lux < Threshold;
	}

	/** Parser rule: keyframe times strictly increase in cycle order. 0 = fine, 1 = a duplicate at Index, 2 = Index goes back. */
	inline int CheckKeyframeOrder(const double* Times, int Count, int& OutIndex)
	{
		OutIndex = -1;
		for (int i = 1; i < Count; ++i)
		{
			if (Times[i] == Times[i - 1])
			{
				OutIndex = i;
				return 1;
			}
			if (Times[i] < Times[i - 1])
			{
				OutIndex = i;
				return 2;
			}
		}
		return 0;
	}

	/**
	 * Parser rule (design 2a), on times that passed CheckKeyframeOrder: 0 = fine, 1 = Holds[Index] is negative or not
	 * finite, 2 = Times[Index] + Holds[Index] is not strictly before the next keyframe time along the cycle (the last
	 * keyframe's hold may cross midnight but must end before Times[0] + 1440).
	 */
	inline int CheckKeyframeHolds(const double* Times, const double* Holds, int Count, int& OutIndex)
	{
		OutIndex = -1;
		for (int i = 0; i < Count; ++i)
		{
			if (!IsValidHold(Holds[i]))
			{
				OutIndex = i;
				return 1;
			}
			const double NextTime = i + 1 < Count ? Times[i + 1] : Times[0] + MinutesPerDay;
			if (!(Times[i] + Holds[i] < NextTime))
			{
				OutIndex = i;
				return 2;
			}
		}
		return 0;
	}
} // namespace GolmokClockMath
