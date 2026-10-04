#include "GolmokAudioMath.h"
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

int main()
{
	GolmokAudioMath::DistanceStepper Step;
	GolmokAudioMath::Envelope Gain, Photo(false);
	std::cout << std::setprecision(17);
	std::string Command;
	while (std::cin >> Command)
	{
		if (Command == "step")
		{
			double Distance, Stride, Limit;
			int Ground, Enabled;
			std::cin >> Distance >> Ground >> Enabled >> Stride >> Limit;
			const auto Result = Step.Advance(Distance, Ground != 0, Enabled != 0, Stride, Limit);
			std::cout << Result.Steps << ' ' << Result.Landed << ' ' << Step.Remainder << '\n';
		}
		else if (Command == "target")
		{
			double Target, Seconds;
			std::cin >> Target >> Seconds; Gain.Set(Target, Seconds);
		}
		else if (Command == "advance")
		{
			double Dt; std::cin >> Dt; Gain.Advance(Dt);
			std::cout << Gain.Value << '\n';
		}
		else if (Command == "photo_target")
		{
			double Target, Seconds; std::cin >> Target >> Seconds; Photo.Set(Target, Seconds);
		}
		else if (Command == "photo_advance")
		{
			double Dt; std::cin >> Dt; Photo.Advance(Dt); std::cout << Photo.Value << '\n';
		}
		else if (Command == "surface")
		{
			int Mapped, Tagged;
			std::cin >> Mapped >> Tagged;
			std::cout << static_cast<int>(GolmokAudioMath::ChooseSurface(Mapped != 0, Tagged != 0)) << '\n';
		}
		else if (Command == "rain")
		{
			struct Point { double X, Y; };
			int Count; std::string Input; std::cin >> Count >> Input;
			std::vector<Point> Points(Count);
			for (auto& P : Points) std::cin >> P.X >> P.Y;
			std::cout << GolmokAudioMath::RainGain(Points.data(), Count, std::stod(Input)) << '\n';
		}
		else return 2;
	}
}
