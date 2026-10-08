// g++ driver for tools/tests/test_ue_travel_math.py (WP-15a): reads one command per stdin line, prints one result line.
// Exercises unreal/Golmok/Source/Golmok/Map/GolmokTravelMath.h and GolmokMapMath.h without Unreal.
#include "GolmokMapMath.h"
#include "GolmokTravelMath.h"

#include <cstdlib>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>

namespace
{
	GolmokTravelMath::Mat4 ReadMat(std::istringstream& In)
	{
		GolmokTravelMath::Mat4 M{};
		for (double& V : M)
		{
			In >> V;
		}
		return M;
	}

	GolmokMapMath::BBox ReadBox(std::istringstream& In)
	{
		GolmokMapMath::BBox B;
		In >> B.West >> B.South >> B.East >> B.North;
		return B;
	}

	// One number token, with Python repr()'s non-finite spellings ("nan", "inf", "-inf"; WP-09 V-07 memo 5) matched
	// here: istream >> double rejects them, and whether strtod does depends on the C runtime (Windows CI MinGW).
	double ParseNum(const std::string& Tok)
	{
		if (Tok == "nan")
		{
			return std::numeric_limits<double>::quiet_NaN();
		}
		if (Tok == "inf")
		{
			return std::numeric_limits<double>::infinity();
		}
		if (Tok == "-inf")
		{
			return -std::numeric_limits<double>::infinity();
		}
		return std::strtod(Tok.c_str(), nullptr);
	}

	void Print(std::ostream& Out, std::initializer_list<double> Values)
	{
		bool bFirst = true;
		for (const double V : Values)
		{
			Out << (bFirst ? "" : " ") << V;
			bFirst = false;
		}
		Out << "\n";
	}
} // namespace

int main()
{
	namespace TM = GolmokTravelMath;
	namespace MM = GolmokMapMath;
	std::cout.precision(17);
	std::string Line;
	while (std::getline(std::cin, Line))
	{
		std::istringstream In(Line);
		std::string Cmd;
		In >> Cmd;
		if (Cmd == "spawn")
		{
			const TM::Mat4 M = ReadMat(In);
			double X = 0, Y = 0, Z = 0, Yaw = 0;
			In >> X >> Y >> Z >> Yaw;
			const TM::Vec3 F = TM::SpawnFeetUE(M, TM::Vec3{X, Y, Z});
			Print(std::cout, {F[0], F[1], F[2], TM::SpawnYawUE(M, Yaw)});
		}
		else if (Cmd == "fallback")
		{
			const TM::Mat4 M = ReadMat(In);
			int Hit = 0;
			double Hx = 0, Hy = 0, Hz = 0;
			In >> Hit >> Hx >> Hy >> Hz;
			TM::Vec3 S{}, E{};
			TM::FallbackTrace(M, S, E);
			const TM::Vec3 F = TM::FallbackFeetUE(M, Hit != 0, TM::Vec3{Hx, Hy, Hz});
			Print(std::cout, {S[0], S[1], S[2], E[0], E[1], E[2], F[0], F[1], F[2], TM::SpawnYawUE(M, 0.0)});
		}
		else if (Cmd == "stand")
		{
			double X = 0, Y = 0, Z = 0, H = 0;
			In >> X >> Y >> Z >> H;
			const TM::Vec3 S = TM::StandingLocationUE(TM::Vec3{X, Y, Z}, H);
			Print(std::cout, {S[0], S[1], S[2]});
		}
		else if (Cmd == "yaw")
		{
			double D = 0;
			In >> D;
			Print(std::cout, {TM::NormalizeYawDeg(D), TM::UEYawToEnuYaw(D), TM::EnuYawToUEYaw(D)});
		}
		else if (Cmd == "check")
		{
			int T = 0, P = 0, Po = 0, K = 0, Pl = 0;
			double Km = 0, Max = 0;
			In >> T >> P >> Po >> K >> Pl >> Km >> Max;
			Print(std::cout, {static_cast<double>(TM::CheckTravel(T != 0, P != 0, Po != 0, K != 0, Pl != 0, Km, Max))});
		}
		else if (Cmd == "poll")
		{
			int L = 0, F = 0;
			double E = 0, Fade = 0, Timeout = 0;
			In >> L >> F >> E >> Fade >> Timeout;
			Print(std::cout, {static_cast<double>(TM::PollTravel(L != 0, F != 0, E, Fade, Timeout))});
		}
		else if (Cmd == "restore")
		{
			int S = 0, P = 0, Ze = 0, Sv = 0, Iv = 0, H = 0;
			In >> S >> P >> Ze >> Sv >> Iv >> H;
			Print(std::cout, {static_cast<double>(TM::DecideRestore(S != 0, P != 0, Ze != 0, Sv, Iv, H != 0))});
		}
		else if (Cmd == "autosave")
		{
			double Now = 0, Last = 0, Interval = 0, Moved = 0, Turned = 0;
			int Dirty = 0;
			In >> Now >> Last >> Interval >> Dirty >> Moved >> Turned;
			Print(std::cout, {TM::ShouldAutosave(Now, Last, Interval, Dirty != 0, Moved, Turned) ? 1.0 : 0.0});
		}
		else if (Cmd == "l2p")
		{
			const MM::BBox B = ReadBox(In);
			int W = 0, H = 0, Merc = 0;
			double Lon = 0, Lat = 0;
			In >> W >> H >> Merc >> Lon >> Lat;
			double Px = 0, Py = 0;
			const bool bIn = MM::LonLatToPixel(B, W, H, Merc != 0, Lon, Lat, Px, Py);
			Print(std::cout, {Px, Py, bIn ? 1.0 : 0.0});
		}
		else if (Cmd == "p2l")
		{
			const MM::BBox B = ReadBox(In);
			int W = 0, H = 0, Merc = 0;
			double Px = 0, Py = 0;
			In >> W >> H >> Merc >> Px >> Py;
			double Lon = 0, Lat = 0;
			const bool bOk = MM::PixelToLonLat(B, W, H, Merc != 0, Px, Py, Lon, Lat);
			Print(std::cout, {Lon, Lat, bOk ? 1.0 : 0.0});
		}
		else if (Cmd == "cell")
		{
			std::string LonTok, LatTok;
			int Z = 0;
			In >> LonTok >> LatTok >> Z;
			int X = 0, Y = 0;
			MM::LonLatToCell(ParseNum(LonTok), ParseNum(LatTok), Z, X, Y);
			Print(std::cout, {static_cast<double>(X), static_cast<double>(Y)});
		}
		else if (Cmd == "bounds")
		{
			int X = 0, Y = 0, Z = 0;
			In >> X >> Y >> Z;
			const MM::BBox B = MM::CellBounds(X, Y, Z);
			Print(std::cout, {B.West, B.South, B.East, B.North});
		}
		else if (Cmd == "rect")
		{
			int X = 0, Y = 0, Z = 0;
			In >> X >> Y >> Z;
			const MM::BBox B = ReadBox(In);
			int W = 0, H = 0, Merc = 0;
			In >> W >> H >> Merc;
			double X0 = 0, Y0 = 0, X1 = 0, Y1 = 0;
			MM::CellToPixelRect(X, Y, Z, B, W, H, Merc != 0, X0, Y0, X1, Y1);
			Print(std::cout, {X0, Y0, X1, Y1});
		}
		else if (Cmd == "p2c")
		{
			const MM::BBox B = ReadBox(In);
			int W = 0, H = 0, Merc = 0, Px = 0, Py = 0, Z = 0;
			In >> W >> H >> Merc >> Px >> Py >> Z;
			int X = 0, Y = 0;
			const bool bOk = MM::PixelToCell(B, W, H, Merc != 0, Px, Py, Z, X, Y);
			Print(std::cout, {bOk ? 1.0 : 0.0, static_cast<double>(X), static_cast<double>(Y)});
		}
		else if (Cmd == "world")
		{
			double Lon = 0, Lat = 0;
			int Z = 0, Tile = 0;
			In >> Lon >> Lat >> Z >> Tile;
			double Px = 0, Py = 0;
			MM::LonLatToWorldPixel(Lon, Lat, Z, Tile, Px, Py);
			Print(std::cout, {Px, Py});
		}
		else
		{
			std::cout << "unknown\n";
		}
	}
	return 0;
}
