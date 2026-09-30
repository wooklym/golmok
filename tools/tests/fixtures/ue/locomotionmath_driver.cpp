#include "GolmokLocomotionMath.h"
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

// One command per line on stdin, one result line per command (tools/tests/test_ue_locomotion_math.py).
// Numbers are read as tokens through strtod so "nan", "inf" and "-inf" reach the header (review R76 D10).
namespace Driver
{
bool ReadOne(double& Out)
{
	std::string Token;
	if (!(std::cin >> Token)) return false;
	char* End = nullptr;
	Out = std::strtod(Token.c_str(), &End);
	return End != Token.c_str() && *End == '\0';
}

bool ReadOne(int& Out)
{
	return static_cast<bool>(std::cin >> Out);
}

template <typename... T>
bool Read(T&... Values)
{
	return (ReadOne(Values) && ...);
}
} // namespace Driver

int main()
{
	using Driver::Read;
	namespace M = GolmokLocomotionMath;
	std::cout << std::setprecision(17);
	std::string Command;
	while (std::cin >> Command)
	{
		if (Command == "gait")
		{
			double MaxWalk, Walk, Run;
			if (!Read(MaxWalk, Walk, Run)) return 2;
			std::cout << static_cast<int>(M::ClassifyGait(MaxWalk, Walk, Run)) << '\n';
		}
		else if (Command == "mode")
		{
			int Mode;
			if (!Read(Mode)) return 2;
			std::cout << static_cast<int>(M::MapMovementMode(Mode)) << '\n';
		}
		else if (Command == "intent")
		{
			double AX, AY, Max, Deadzone;
			if (!Read(AX, AY, Max, Deadzone)) return 2;
			const std::array<double, 2> I = M::Intent(AX, AY, Max, Deadzone);
			std::cout << I[0] << ' ' << I[1] << ' ' << M::Length2(I) << '\n';
		}
		else if (Command == "moving")
		{
			int Previous;
			double Speed, IntentLength;
			if (!Read(Previous, Speed, IntentLength)) return 2;
			std::cout << static_cast<int>(M::UpdateMoving(static_cast<M::MovingState>(Previous), Speed, IntentLength)) << '\n';
		}
		else if (Command == "landing")
		{
			// landing <vz> <landed_at> <window> <clear 0|1> <n> <t1> ... <tn>
			double VZ, At, Window;
			int Clear, Count;
			if (!Read(VZ, At, Window, Clear, Count) || Count < 0) return 2;
			M::LandingWindow Landing;
			Landing.OnLanded(VZ, At);
			if (Clear) Landing.Clear();
			std::cout << Landing.LandVelocityZ;
			for (int Index = 0; Index < Count; ++Index)
			{
				double Now;
				if (!Read(Now)) return 2;
				std::cout << ' ' << Landing.IsJustLanded(Now, Window) << ' ' << Landing.SecondsSinceLanding(Now);
			}
			std::cout << '\n';
		}
		else if (Command == "teleport")
		{
			double PX, PY, CX, CY, Speed, Dt, Slack;
			if (!Read(PX, PY, CX, CY, Speed, Dt, Slack)) return 2;
			std::cout << M::IsTeleportJump(PX, PY, CX, CY, Speed, Dt, Slack) << '\n';
		}
		else if (Command == "profile")
		{
			M::MovementProfile P;
			int Separate;
			if (!Read(P.MaxAcceleration, P.BrakingDecelerationWalking, P.GroundFriction, P.BrakingFrictionFactor, Separate,
				P.BrakingFriction)) return 2;
			P.bUseSeparateBrakingFriction = Separate != 0;
			std::cout << M::ValidateProfile(P) << '\n';
		}
		else if (Command == "defaults")
		{
			const M::MovementProfile P;
			std::cout << P.MaxAcceleration << ' ' << P.BrakingDecelerationWalking << ' ' << P.GroundFriction << ' '
				<< P.BrakingFrictionFactor << ' ' << P.bUseSeparateBrakingFriction << ' ' << P.BrakingFriction << ' '
				<< M::DefaultJustLandedSeconds << ' ' << M::DefaultTeleportSlackCm << ' ' << M::PlantedToleranceCm << ' '
				<< M::IntentDeadzone << ' ' << M::MovingStartCmS << ' ' << M::MovingStopCmS << ' ' << M::GaitToleranceCmS
				<< '\n';
		}
		else if (Command == "state")
		{
			double JustLanded, Slack;
			if (!Read(JustLanded, Slack)) return 2;
			std::cout << M::ValidateStateSettings(JustLanded, Slack) << '\n';
		}
		else if (Command == "planted")
		{
			// planted <n> (<x> <y> <z> <on_ground>)*n
			int Count;
			if (!Read(Count) || Count < 0) return 2;
			std::vector<M::FootSample> Samples(static_cast<unsigned int>(Count));
			for (M::FootSample& S : Samples)
			{
				int OnGround;
				if (!Read(S.X, S.Y, S.Z, OnGround)) return 2;
				S.bCapsuleOnGround = OnGround != 0;
			}
			std::cout << M::PlantedTravelCm(Samples.empty() ? nullptr : Samples.data(), Count) << '\n';
		}
		else if (Command == "slip")
		{
			double Travel, Capsule;
			if (!Read(Travel, Capsule)) return 2;
			std::cout << M::PlantedSlipCmPerM(Travel, Capsule) << '\n';
		}
		else return 3;
	}
	return 0;
}
