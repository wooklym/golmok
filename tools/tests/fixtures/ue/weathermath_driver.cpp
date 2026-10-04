#include "Weather/GolmokWeatherMath.h"
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

// One command per line on stdin, one result line on stdout (tools/tests/test_ue_weather_math.py).
// Doubles go out as hexfloat so the test can compare bits; inputs go through strtod (hexfloat, "inf", "nan").

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

using GolmokWeatherMath::Light;
using GolmokWeatherMath::Modifier;

static Modifier ReadModifier()
{
	Modifier M;
	for (int I = 0; I < GolmokWeatherMath::ModifierFieldCount; ++I)
	{
		Num V;
		std::cin >> V;
		GolmokWeatherMath::SetField(M, I, V);
	}
	return M;
}

static void WriteModifier(const Modifier& M)
{
	for (int I = 0; I < GolmokWeatherMath::ModifierFieldCount; ++I)
	{
		std::cout << (I ? " " : "") << GolmokWeatherMath::GetField(M, I);
	}
	std::cout << '\n';
}

static GolmokWeatherMath::SurfaceParams ReadParams()
{
	Num Wet, Dry, Min, Fill, Drain;
	std::cin >> Wet >> Dry >> Min >> Fill >> Drain;
	GolmokWeatherMath::SurfaceParams P;
	P.WetSeconds = Wet;
	P.DrySeconds = Dry;
	P.PuddleMinIntensity = Min;
	P.PuddleFillSeconds = Fill;
	P.PuddleDrySeconds = Drain;
	return P;
}

int main()
{
	std::cout << std::hexfloat;
	std::string Command;
	while (std::cin >> Command)
	{
		if (Command == "consts")
		{
			std::cout << GolmokWeatherMath::StateCount << ' ' << GolmokWeatherMath::MinRainIntensity << ' '
					  << GolmokWeatherMath::MaxRainIntensity << ' ' << GolmokWeatherMath::WetRainThreshold << ' '
					  << GolmokWeatherMath::ValueEpsilon << ' ' << GolmokWeatherMath::MaxTransitionSeconds << ' '
					  << GolmokWeatherMath::ModifierFieldCount << '\n';
		}
		else if (Command == "contract")
		{
			std::cout << GolmokWeatherMath::MpcRainIntensity << ' ' << GolmokWeatherMath::MpcWetness << ' '
					  << GolmokWeatherMath::MpcPuddleAmount << ' ' << GolmokWeatherMath::UserRainIntensity << ' '
					  << GolmokWeatherMath::UserSpawnRate << ' ' << GolmokWeatherMath::UserBoxHalfExtent << '\n';
		}
		else if (Command == "name")
		{
			int S = 0; std::cin >> S;
			std::cout << GolmokWeatherMath::StateName(static_cast<GolmokWeatherMath::State>(S)) << '\n';
		}
		else if (Command == "parse_state")
		{
			std::string Text; std::cin >> Text;
			if (Text == "<empty>") Text.clear();
			GolmokWeatherMath::State S = GolmokWeatherMath::State::Clear;
			const bool bOk = GolmokWeatherMath::ParseState(Text.c_str(), S);
			const std::wstring Wide(Text.begin(), Text.end());
			GolmokWeatherMath::State WideS = GolmokWeatherMath::State::Clear;
			const bool bWideOk = GolmokWeatherMath::ParseState(Wide.c_str(), WideS);
			std::cout << (bOk ? static_cast<int>(S) : -1) << ' ' << (bWideOk ? static_cast<int>(WideS) : -1) << '\n';
		}
		else if (Command == "field")
		{
			int I = 0; std::cin >> I;
			const GolmokWeatherMath::FieldRange& R = GolmokWeatherMath::ModifierField(I);
			std::cout << R.Key << ' ' << R.Min << ' ' << R.Max << ' ' << (R.bMinExclusive ? 1 : 0) << '\n';
		}
		else if (Command == "inrange")
		{
			int I = 0; Num V; std::cin >> I >> V;
			std::cout << (GolmokWeatherMath::IsFieldInRange(I, V) ? 1 : 0) << '\n';
		}
		else if (Command == "validint")
		{
			Num V; std::cin >> V;
			std::cout << (GolmokWeatherMath::IsValidRainIntensity(V) ? 1 : 0) << '\n';
		}
		else if (Command == "target")
		{
			int S = 0; Num I; std::cin >> S >> I;
			std::cout << GolmokWeatherMath::TargetRain(static_cast<GolmokWeatherMath::State>(S), I) << '\n';
		}
		else if (Command == "identity")
		{
			const Modifier M = ReadModifier();
			std::cout << (GolmokWeatherMath::IsIdentity(M) ? 1 : 0) << '\n';
		}
		else if (Command == "apply")
		{
			// lux use_temperature kelvin sky fog falloff exposure_overridden bias, then the 7 modifier fields
			Num Lux, Kelvin, Sky, Fog, Falloff, Bias;
			int UseT = 0, Overridden = 0;
			std::cin >> Lux >> UseT >> Kelvin >> Sky >> Fog >> Falloff >> Overridden >> Bias;
			Light L;
			L.Lux = Lux;
			L.bUseTemperature = UseT != 0;
			L.Kelvin = Kelvin;
			L.Sky = Sky;
			L.Fog = Fog;
			L.FogHeightFalloff = Falloff;
			L.bExposureOverridden = Overridden != 0;
			L.ExposureBias = Bias;
			const Light R = GolmokWeatherMath::Apply(L, ReadModifier());
			std::cout << R.Lux << ' ' << (R.bUseTemperature ? 1 : 0) << ' ' << R.Kelvin << ' ' << R.Sky << ' ' << R.Fog << ' '
					  << R.FogHeightFalloff << ' ' << (R.bExposureOverridden ? 1 : 0) << ' ' << R.ExposureBias << '\n';
		}
		else if (Command == "lerp")
		{
			const Modifier A = ReadModifier();
			const Modifier B = ReadModifier();
			Num T; std::cin >> T;
			WriteModifier(GolmokWeatherMath::Lerp(A, B, T));
		}
		else if (Command == "forstate")
		{
			int S = 0; Num I; std::cin >> S >> I;
			const Modifier O = ReadModifier();
			const Modifier R = ReadModifier();
			WriteModifier(GolmokWeatherMath::ForState(static_cast<GolmokWeatherMath::State>(S), I, O, R));
		}
		else if (Command == "modat")
		{
			const Modifier A = ReadModifier();
			const Modifier B = ReadModifier();
			Num Alpha; std::cin >> Alpha;
			WriteModifier(GolmokWeatherMath::ModifierAt(A, B, Alpha));
		}
		else if (Command == "smooth")
		{
			Num X; std::cin >> X;
			std::cout << GolmokWeatherMath::Smoothstep(X) << '\n';
		}
		else if (Command == "palpha")
		{
			Num Alpha; int Inc = 0; std::cin >> Alpha >> Inc;
			std::cout << GolmokWeatherMath::PrecipAlpha(Alpha, Inc != 0) << '\n';
		}
		else if (Command == "precip")
		{
			Num Start, Target, Alpha; std::cin >> Start >> Target >> Alpha;
			std::cout << GolmokWeatherMath::PrecipAt(Start, Target, Alpha) << '\n';
		}
		else if (Command == "step")
		{
			Num W, P, Rain, Dt; std::cin >> W >> P >> Rain >> Dt;
			GolmokWeatherMath::Surface S;
			S.Wetness = W;
			S.Puddle = P;
			const GolmokWeatherMath::Surface R = GolmokWeatherMath::StepSurface(S, Rain, Dt, ReadParams());
			std::cout << R.Wetness << ' ' << R.Puddle << '\n';
		}
		else if (Command == "clampsurf")
		{
			Num W, P; std::cin >> W >> P;
			const GolmokWeatherMath::Surface R = GolmokWeatherMath::ClampSurface(W, P);
			std::cout << R.Wetness << ' ' << R.Puddle << '\n';
		}
		else if (Command == "sched")
		{
			Num M; int Count = 0; std::cin >> M >> Count;
			std::vector<double> Times(static_cast<size_t>(Count > 0 ? Count : 0));
			for (double& T : Times)
			{
				Num V; std::cin >> V; T = V;
			}
			std::cout << GolmokWeatherMath::ScheduleIndexAt(M, Times.empty() ? nullptr : Times.data(), Count) << '\n';
		}
		else
		{
			std::cout << "unknown\n";
		}
	}
	return 0;
}
