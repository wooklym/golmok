#include "GolmokAudioMath.h"
#include <iomanip>
#include <iostream>
#include <string>

int main()
{
	GolmokAudioMath::DistanceStepper Step;
	GolmokAudioMath::Envelope Gain;
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
		else if (Command == "surface")
		{
			int Mapped, Tagged;
			std::cin >> Mapped >> Tagged;
			std::cout << static_cast<int>(GolmokAudioMath::ChooseSurface(Mapped != 0, Tagged != 0)) << '\n';
		}
		else return 2;
	}
}
