#include "GolmokCharacterMath.h"
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>

int main()
{
	std::cout << std::setprecision(17);
	std::string Command;
	while (std::cin >> Command)
	{
		GolmokCharacterMath::Dimensions D;
		if (Command == "calculate")
		{
			double Height, Width;
			if (!(std::cin >> Height >> Width)) return 2;
			const bool Valid = GolmokCharacterMath::Calculate(Height, Width, D);
			std::cout << Valid << ' ' << D.Height << ' ' << D.Radius << ' ' << D.HalfHeight;
			for (const double V : D.MeshOffset) std::cout << ' ' << V;
			for (const double V : D.MeshScale) std::cout << ' ' << V;
			std::cout << ' ' << D.MeshYaw << ' ' << D.Boom;
			for (const double V : D.Socket) std::cout << ' ' << V;
			std::cout << ' ' << D.Fov << ' ' << D.Walk << ' ' << D.Run << '\n';
		}
		else if (Command == "feet")
		{
			double Z, OldHalf, NewHalf;
			if (!(std::cin >> Z >> OldHalf >> NewHalf)) return 2;
			std::cout << GolmokCharacterMath::CenterForFixedFeet(Z, OldHalf, NewHalf) << '\n';
		}
		else if (Command == "invalid")
		{
			const double Bad[] = {std::numeric_limits<double>::quiet_NaN(),
				std::numeric_limits<double>::infinity(), -std::numeric_limits<double>::infinity()};
			bool Rejected = true;
			for (const double V : Bad)
			{
				Rejected &= !GolmokCharacterMath::Calculate(V, 1.0, D);
				Rejected &= !GolmokCharacterMath::Calculate(180.0, V, D);
				D.MeshScale[2] = V;
				Rejected &= !GolmokCharacterMath::Validate(D);
			}
			D = {};
			D.Run = D.Walk;
			Rejected &= !GolmokCharacterMath::Validate(D);
			D = {};
			D.HalfHeight = 40.0;
			Rejected &= !GolmokCharacterMath::Validate(D);
			std::cout << Rejected << '\n';
		}
		else return 3;
	}
	return 0;
}
