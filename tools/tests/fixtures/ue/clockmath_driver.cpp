#include "GolmokClockMath.h"
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

// One command per line on stdin, one result line on stdout (tools/tests/test_ue_clock_math.py).

// Numbers go through strtod so "inf" / "nan" parse (operator>> rejects them).
struct Num
{
	double Value = 0.0;
	operator double() const { return Value; }
};
static std::istream& operator>>(std::istream& In, Num& Out)
{
	std::string Token;
	if (In >> Token)
	{
		Out.Value = std::strtod(Token.c_str(), nullptr);
	}
	return In;
}

int main()
{
	std::cout << std::setprecision(17);
	std::string Command;
	while (std::cin >> Command)
	{
		if (Command == "wrap")
		{
			Num M; std::cin >> M;
			std::cout << GolmokClockMath::WrapMinutes(M) << '\n';
		}
		else if (Command == "dist")
		{
			Num A, B; std::cin >> A >> B;
			std::cout << GolmokClockMath::CircularDistance(A, B) << '\n';
		}
		else if (Command == "parse")
		{
			std::string Text; std::cin >> Text;
			if (Text == "<empty>") Text.clear();
			int M = -1;
			const bool bOk = GolmokClockMath::ParseHHMM(Text.c_str(), M);
			std::wstring Wide(Text.begin(), Text.end());
			int WideM = -1;
			const bool bWideOk = GolmokClockMath::ParseHHMM(Wide.c_str(), WideM);
			std::cout << (bOk ? 1 : 0) << ' ' << M << ' ' << (bWideOk ? 1 : 0) << ' ' << WideM << '\n';
		}
		else if (Command == "format")
		{
			Num M; std::cin >> M;
			char Out[6];
			GolmokClockMath::FormatHHMM(M, Out);
			std::cout << Out << '\n';
		}
		else if (Command == "advance")
		{
			Num M, Rate, Dt; std::cin >> M >> Rate >> Dt;
			std::cout << GolmokClockMath::Advance(M, Rate, Dt) << '\n';
		}
		else if (Command == "rate")
		{
			Num Rate; std::cin >> Rate;
			std::cout << (GolmokClockMath::IsValidRate(Rate) ? 1 : 0) << '\n';
		}
		else if (Command == "find")
		{
			Num M; int Count; std::cin >> M >> Count;
			std::vector<double> Times(static_cast<size_t>(Count > 0 ? Count : 0));
			for (double& T : Times) std::cin >> T;
			const GolmokClockMath::KeyframeSpan Span = GolmokClockMath::FindKeyframes(M, Times.data(), Count);
			std::cout << Span.Prev << ' ' << Span.Next << ' ' << Span.Alpha << ' ' << (Span.IsValid() ? Span.Nearest() : -1) << ' '
					  << (Span.bHeld ? 1 : 0) << '\n';
		}
		else if (Command == "findh")
		{
			// findh <minutes> <count> <times...> <holds...> (design 2a)
			Num M; int Count; std::cin >> M >> Count;
			std::vector<double> Times(static_cast<size_t>(Count > 0 ? Count : 0));
			std::vector<Num> Holds(Times.size());
			for (double& T : Times) std::cin >> T;
			for (Num& H : Holds) std::cin >> H;
			std::vector<double> HoldValues(Holds.begin(), Holds.end());
			const GolmokClockMath::KeyframeSpan Span = GolmokClockMath::FindKeyframes(M, Times.data(), HoldValues.data(), Count);
			std::cout << Span.Prev << ' ' << Span.Next << ' ' << Span.Alpha << ' ' << (Span.IsValid() ? Span.Nearest() : -1) << ' '
					  << (Span.bHeld ? 1 : 0) << '\n';
		}
		else if (Command == "hold")
		{
			Num Hold; std::cin >> Hold;
			std::cout << (GolmokClockMath::IsValidHold(Hold) ? 1 : 0) << '\n';
		}
		else if (Command == "holdend")
		{
			Num Time, Hold; std::cin >> Time >> Hold;
			std::cout << GolmokClockMath::HoldEnd(Time, Hold) << '\n';
		}
		else if (Command == "holds")
		{
			// holds <count> <times...> <holds...> -> CheckKeyframeHolds result and index
			int Count; std::cin >> Count;
			std::vector<double> Times(static_cast<size_t>(Count));
			std::vector<Num> Holds(Times.size());
			for (double& T : Times) std::cin >> T;
			for (Num& H : Holds) std::cin >> H;
			std::vector<double> HoldValues(Holds.begin(), Holds.end());
			int Index = -1;
			const int Result = GolmokClockMath::CheckKeyframeHolds(Times.data(), HoldValues.data(), Count, Index);
			std::cout << Result << ' ' << Index << '\n';
		}
		else if (Command == "yaw")
		{
			Num A, B, Alpha; std::cin >> A >> B >> Alpha;
			std::cout << GolmokClockMath::LerpYawShortest(A, B, Alpha) << '\n';
		}
		else if (Command == "interp")
		{
			GolmokClockMath::LightKey K[2];
			for (GolmokClockMath::LightKey& Key : K)
			{
				int Vol = 0;
				std::cin >> Key.Pitch >> Key.Yaw >> Key.Lux >> Key.Kelvin >> Key.Sky >> Key.Fog >> Key.FogHeightFalloff >> Key.ExposureBias >> Vol;
				Key.bVolumetric = Vol != 0;
			}
			Num Alpha; std::cin >> Alpha;
			const GolmokClockMath::LightKey R = GolmokClockMath::Interpolate(K[0], K[1], Alpha);
			std::cout << R.Pitch << ' ' << R.Yaw << ' ' << R.Lux << ' ' << R.Kelvin << ' ' << R.Sky << ' ' << R.Fog << ' '
					  << R.FogHeightFalloff << ' ' << R.ExposureBias << ' ' << (R.bVolumetric ? 1 : 0) << '\n';
		}
		else if (Command == "sun")
		{
			Num Lux; std::cin >> Lux;
			std::cout << (GolmokClockMath::IsSunVisible(Lux) ? 1 : 0) << '\n';
		}
		else if (Command == "night")
		{
			Num Lux, Threshold; std::cin >> Lux >> Threshold;
			std::cout << (GolmokClockMath::IsNight(Lux, Threshold) ? 1 : 0) << '\n';
		}
		else if (Command == "order")
		{
			int Count; std::cin >> Count;
			std::vector<double> Times(static_cast<size_t>(Count));
			for (double& T : Times) std::cin >> T;
			int Index = -1;
			const int Result = GolmokClockMath::CheckKeyframeOrder(Times.data(), Count, Index);
			std::cout << Result << ' ' << Index << '\n';
		}
		else return 2;
	}
}
