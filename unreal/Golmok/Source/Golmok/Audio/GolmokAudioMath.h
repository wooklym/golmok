#pragma once
#include <cmath>

namespace GolmokAudioMath
{
	inline double Clamp01(double Value) { return !std::isfinite(Value) || Value < 0.0 ? 0.0 : (Value > 1.0 ? 1.0 : Value); }

	struct Envelope
	{
		explicit Envelope(bool bPower = true) : Power(bPower) {}
		bool Power;
		double Value = 0.0, From = 0.0, To = 0.0, Elapsed = 0.0, Seconds = 0.0;
		void Set(double Target, double Duration)
		{
			From = Value; To = Clamp01(Target); Elapsed = 0.0;
			Seconds = std::isfinite(Duration) && Duration > 0.0 ? Duration : 0.0;
			if (Seconds == 0.0) Value = To;
		}
		void Advance(double Dt)
		{
			if (!std::isfinite(Dt) || Dt < 0.0) return;
			Elapsed += Dt;
			const double Alpha = Seconds > 0.0 ? Clamp01(Elapsed / Seconds) : 1.0;
			// Raised-cosine progress gives sin/cos crossfades and smooth amplitude fades.
			const double Shaped = 0.5 - 0.5 * std::cos(3.14159265358979323846 * Alpha);
			Value = Power ? std::sqrt(From * From * (1.0 - Shaped) + To * To * Shaped)
				: From + (To - From) * Shaped;
		}
		bool Done() const { return Seconds == 0.0 || Elapsed >= Seconds; }
	};

	struct StepResult { int Steps = 0; bool Landed = false; };
	struct DistanceStepper
	{
		double Remainder = 0.0;
		bool Initialized = false, WasGrounded = true;
		void Reset() { Remainder = 0.0; Initialized = false; WasGrounded = true; }
		StepResult Advance(double Distance, bool Grounded, bool Enabled, double Stride, double TeleportLimit)
		{
			StepResult Result;
			if (!Enabled || !std::isfinite(Distance) || Distance < 0.0 || !std::isfinite(Stride) || Stride <= 0.0
				|| !std::isfinite(TeleportLimit) || TeleportLimit <= 0.0 || Distance > TeleportLimit)
			{ Reset(); return Result; }
			if (!Initialized) { Initialized = true; WasGrounded = Grounded; return Result; }
			Result.Landed = Grounded && !WasGrounded;
			WasGrounded = Grounded;
			if (!Grounded || Result.Landed) { Remainder = 0.0; return Result; }
			Remainder += Distance;
			Result.Steps = static_cast<int>(std::floor(Remainder / Stride));
			Remainder = std::fmod(Remainder, Stride);
			return Result;
		}
	};

	inline int State(bool Interior, bool Night) { return Interior ? 2 : (Night ? 1 : 0); }
	enum class SurfaceChoice { Default, PhysicalMaterial, StairsTag };
	inline SurfaceChoice ChooseSurface(bool HasPhysicalMapping, bool TaggedStairs)
	{
		return TaggedStairs ? SurfaceChoice::StairsTag : (HasPhysicalMapping ? SurfaceChoice::PhysicalMaterial : SurfaceChoice::Default);
	}
}
