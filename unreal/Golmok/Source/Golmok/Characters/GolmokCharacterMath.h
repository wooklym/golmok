#pragma once

#include <array>
#include <cmath>

// Centimetres, degrees, mesh-local XYZ. No engine or Windows types/macros.
namespace GolmokCharacterMath
{

struct Dimensions
{
	double Height = 180.0;
	double Radius = 42.0;
	double HalfHeight = 92.0;
	std::array<double, 3> MeshOffset{0.0, 0.0, -92.0};
	std::array<double, 3> MeshScale{1.0, 1.0, 1.0};
	double MeshYaw = -90.0;
	double Boom = 320.0;
	std::array<double, 3> Socket{0.0, 45.0, 55.0};
	double Fov = 80.0;
	double Walk = 180.0;
	double Run = 500.0;
};

inline bool InRange(double Value, double Low, double High)
{
	return std::isfinite(Value) && Value >= Low && Value <= High;
}

inline bool Validate(const Dimensions& Value)
{
	if (!InRange(Value.Height, 80.0, 220.0) || !InRange(Value.Radius, 15.0, 60.0)
		|| !InRange(Value.HalfHeight, 40.0, 120.0) || Value.HalfHeight < Value.Radius
		|| !InRange(Value.MeshYaw, -180.0, 180.0) || !InRange(Value.Boom, 100.0, 500.0)
		|| !InRange(Value.Fov, 40.0, 110.0) || !InRange(Value.Walk, 50.0, 300.0)
		|| !InRange(Value.Run, 100.0, 800.0) || Value.Run <= Value.Walk)
	{
		return false;
	}
	for (unsigned int Axis = 0; Axis < 3; ++Axis)
	{
		if (!InRange(Value.MeshOffset[Axis], -250.0, 250.0)
			|| !InRange(Value.MeshScale[Axis], 0.25, 2.0) || !InRange(Value.Socket[Axis], -150.0, 150.0))
		{
			return false;
		}
	}
	return true;
}

// A design starting point. JSON may override the result, but must pass Validate.
// On failure Out is untouched.
inline bool Calculate(double Height, double WidthRatio, Dimensions& Out)
{
	if (!InRange(Height, 80.0, 220.0) || !InRange(WidthRatio, 0.75, 1.35))
	{
		return false;
	}
	const double Scale = Height / 180.0;
	Dimensions Candidate;
	Candidate.Height = Height;
	Candidate.Radius = 42.0 * Scale * WidthRatio;
	Candidate.HalfHeight = 92.0 * Scale;
	Candidate.MeshOffset[2] = -Candidate.HalfHeight;
	Candidate.MeshScale = {Scale * WidthRatio, Scale * WidthRatio, Scale};
	Candidate.Boom = 80.0 + 240.0 * Scale;
	Candidate.Socket = {0.0, 5.0 + 40.0 * Scale, 15.0 + 40.0 * Scale};
	Candidate.Fov = 60.0 + 20.0 * Scale;
	if (!Validate(Candidate))
	{
		return false;
	}
	Out = Candidate;
	return true;
}

inline double CenterForFixedFeet(double CenterZ, double OldHalfHeight, double NewHalfHeight)
{
	return CenterZ - OldHalfHeight + NewHalfHeight;
}

} // namespace GolmokCharacterMath
