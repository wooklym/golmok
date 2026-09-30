#pragma once

#include <array>
#include <cmath>

// WP-19 design section 2: locomotion state rules for the GASP state provider (D-021).
// Centimetres, seconds, degrees. No engine or Windows types/macros (g++ cross-checked by
// tools/tests/test_ue_locomotion_math.py). GASP enums are not mirrored; the 19b Blueprint maps ours to GASP's.
namespace GolmokLocomotionMath
{

enum class Gait : int
{
	Walk = 0,
	Run = 1,
};

enum class MovementMode : int
{
	OnGround = 0,
	InAir = 1,
};

enum class MovingState : int
{
	Idle = 0,
	Moving = 1,
};

// |MaxWalkSpeed - Run| at or below this is running (the WP-18 hook keeps MaxWalkSpeed exactly at Walk or Run).
constexpr double GaitToleranceCmS = 0.5;
// Input intent below this length is no intent.
constexpr double IntentDeadzone = 0.05;
// Moving starts at this horizontal speed (or with any intent) ...
constexpr double MovingStartCmS = 10.0;
// ... and stops below this speed with no intent (hysteresis in between).
constexpr double MovingStopCmS = 3.0;
// Defaults of animation.json gasp.state (just_landed_seconds, teleport_jump_cm).
constexpr double DefaultJustLandedSeconds = 0.3;
constexpr double DefaultTeleportSlackCm = 100.0;
// V-08 table A: a foot bone is planted within this height above its flat-ground minimum.
constexpr double PlantedToleranceCm = 2.5;

inline bool InRange(double Value, double Low, double High)
{
	return std::isfinite(Value) && Value >= Low && Value <= High;
}

// Run when MaxWalkSpeed is the character's run speed, otherwise Walk (roster 145/380 and 120/310 included).
// No Sprint and no Crouch (stance is always Stand). A roster with Run <= Walk is invalid and reads as Walk.
inline Gait ClassifyGait(double MaxWalkSpeed, double Walk, double Run)
{
	if (!std::isfinite(MaxWalkSpeed) || !std::isfinite(Walk) || !std::isfinite(Run) || Run <= Walk)
	{
		return Gait::Walk;
	}
	return std::fabs(MaxWalkSpeed - Run) <= GaitToleranceCmS ? Gait::Run : Gait::Walk;
}

// EMovementMode values: MOVE_Walking 1, MOVE_NavWalking 2, MOVE_Falling 3. Anything else (none, swimming,
// flying, custom; not used by the game) is treated as on the ground.
inline MovementMode MapMovementMode(int EngineMode)
{
	return EngineMode == 3 ? MovementMode::InAir : MovementMode::OnGround;
}

// Horizontal acceleration / max acceleration, length clamped to 1 and zeroed below Deadzone. The CMC scales the
// acceleration by the analog input size, so a half-tilted stick gives an intent of about 0.5.
inline std::array<double, 2> Intent(double AccelX, double AccelY, double MaxAcceleration, double Deadzone)
{
	const std::array<double, 2> Zero{0.0, 0.0};
	if (!std::isfinite(AccelX) || !std::isfinite(AccelY) || !std::isfinite(MaxAcceleration) || MaxAcceleration <= 0.0)
	{
		return Zero;
	}
	double X = AccelX / MaxAcceleration;
	double Y = AccelY / MaxAcceleration;
	const double Length = std::sqrt(X * X + Y * Y);
	if (!std::isfinite(Length) || Length < Deadzone)
	{
		return Zero;
	}
	if (Length > 1.0)
	{
		X /= Length;
		Y /= Length;
	}
	return {X, Y};
}

inline double Length2(const std::array<double, 2>& Value)
{
	return std::sqrt(Value[0] * Value[0] + Value[1] * Value[1]);
}

// Moving at >= MovingStartCmS or with any intent; Idle below MovingStopCmS with no intent; otherwise unchanged.
inline MovingState UpdateMoving(MovingState Previous, double Speed2D, double IntentLength)
{
	const bool bIntent = IntentLength > 0.0;
	if (Speed2D >= MovingStartCmS || bIntent)
	{
		return MovingState::Moving;
	}
	if (Speed2D < MovingStopCmS)
	{
		return MovingState::Idle;
	}
	return Previous;
}

// Just-landed window: OnLanded(Vz, Now) opens it for Window seconds and keeps the landing vertical speed.
struct LandingWindow
{
	bool bHasLanded = false;
	double LandedAt = 0.0;
	double LandVelocityZ = 0.0;

	void OnLanded(double VelocityZ, double Now)
	{
		bHasLanded = true;
		LandedAt = Now;
		LandVelocityZ = std::isfinite(VelocityZ) ? VelocityZ : 0.0;
	}

	// Leaving the ground again (a new jump or a fall) ends the window early.
	void Clear()
	{
		bHasLanded = false;
	}

	bool IsJustLanded(double Now, double Window) const
	{
		return bHasLanded && std::isfinite(Now) && Now >= LandedAt && Now - LandedAt < Window;
	}

	double SecondsSinceLanding(double Now) const
	{
		return bHasLanded && Now >= LandedAt ? Now - LandedAt : -1.0;
	}
};

// A horizontal jump longer than Speed * Dt + Slack is a teleport (portal, golmok.travel, save restore).
inline bool IsTeleportJump(double PrevX, double PrevY, double CurX, double CurY, double Speed, double Dt, double Slack)
{
	const double DX = CurX - PrevX;
	const double DY = CurY - PrevY;
	const double Distance = std::sqrt(DX * DX + DY * DY);
	if (!std::isfinite(Distance))
	{
		return false;
	}
	const double Reach = (std::isfinite(Speed) && Speed > 0.0 ? Speed : 0.0) * (std::isfinite(Dt) && Dt > 0.0 ? Dt : 0.0)
		+ (std::isfinite(Slack) && Slack > 0.0 ? Slack : 0.0);
	return Distance > Reach;
}

// animation.json movement_profiles.<id> (design section 6). Top speed, rotation rate, jump and rotation mode are
// not profile fields (changing them needs a D-021 revision).
struct MovementProfile
{
	double MaxAcceleration = 2048.0;
	double BrakingDecelerationWalking = 2000.0;
	double GroundFriction = 8.0;
	double BrakingFrictionFactor = 2.0;
	bool bUseSeparateBrakingFriction = false;
	double BrakingFriction = 0.0;
};

inline bool ValidateProfile(const MovementProfile& Value)
{
	return InRange(Value.MaxAcceleration, 100.0, 10000.0) && InRange(Value.BrakingDecelerationWalking, 0.0, 10000.0)
		&& InRange(Value.GroundFriction, 0.0, 20.0) && InRange(Value.BrakingFrictionFactor, 0.0, 10.0)
		&& InRange(Value.BrakingFriction, 0.0, 20.0);
}

// animation.json gasp.state ranges (design section 7).
inline bool ValidateStateSettings(double JustLandedSeconds, double TeleportSlackCm)
{
	return InRange(JustLandedSeconds, 0.05, 2.0) && InRange(TeleportSlackCm, 20.0, 1000.0);
}

struct FootSample
{
	double X = 0.0;
	double Y = 0.0;
	double Z = 0.0;
	bool bCapsuleOnGround = true;
};

// V-08 table A, one foot bone: the horizontal distance the bone moves between consecutive samples in which it is
// planted (height <= its lowest on-ground height + PlantedToleranceCm and the capsule on the ground). Sum the
// feet and divide by the capsule's horizontal travel in metres (PlantedSlipCmPerM) for cm per metre.
inline double PlantedTravelCm(const FootSample* Samples, int Count)
{
	if (!Samples || Count < 2)
	{
		return 0.0;
	}
	bool bHasFloor = false;
	double Floor = 0.0;
	for (int Index = 0; Index < Count; ++Index)
	{
		const FootSample& S = Samples[Index];
		if (S.bCapsuleOnGround && std::isfinite(S.Z) && (!bHasFloor || S.Z < Floor))
		{
			Floor = S.Z;
			bHasFloor = true;
		}
	}
	if (!bHasFloor)
	{
		return 0.0;
	}
	double Travel = 0.0;
	for (int Index = 1; Index < Count; ++Index)
	{
		const FootSample& A = Samples[Index - 1];
		const FootSample& B = Samples[Index];
		const bool bPlantedA = A.bCapsuleOnGround && std::isfinite(A.Z) && A.Z <= Floor + PlantedToleranceCm;
		const bool bPlantedB = B.bCapsuleOnGround && std::isfinite(B.Z) && B.Z <= Floor + PlantedToleranceCm;
		if (bPlantedA && bPlantedB)
		{
			const double DX = B.X - A.X;
			const double DY = B.Y - A.Y;
			const double Step = std::sqrt(DX * DX + DY * DY);
			if (std::isfinite(Step))
			{
				Travel += Step;
			}
		}
	}
	return Travel;
}

// Planted-foot travel (cm, all feet summed) per metre of capsule travel; 0 when the capsule moved < 1 cm.
inline double PlantedSlipCmPerM(double PlantedTravelCmSum, double CapsuleTravelCm)
{
	if (!std::isfinite(PlantedTravelCmSum) || !std::isfinite(CapsuleTravelCm) || CapsuleTravelCm < 1.0)
	{
		return 0.0;
	}
	return PlantedTravelCmSum / (CapsuleTravelCm / 100.0);
}

} // namespace GolmokLocomotionMath
