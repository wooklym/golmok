#include "GolmokGeoMath.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

// Command-line driver for tools/tests/test_ue_geo_math.py. Prints doubles with 10-12 decimals.
// WP-09 cell commands: cell <lon> <lat> <z> -> "x y"; cells (stdin, one "lon lat z" per line -> one "x y" per line;
// Windows argv is limited to 32 KiB so batches go through stdin); cellbounds <x> <y> <z> -> "west south east north".
using namespace GolmokGeoMath;

static std::string readStdin()
{
	std::string in;
	char buf[4096];
	std::size_t n = 0;
	while ((n = std::fread(buf, 1, sizeof(buf), stdin)) > 0)
	{
		in.append(buf, n);
	}
	return in;
}

static void p3(const Vec3& v) { std::printf("%.17g %.17g %.17g\n", v[0], v[1], v[2]); }

static void p16(const Mat4& m)
{
	for (int i = 0; i < 16; ++i)
	{
		std::printf("%.17g%c", m[i], i == 15 ? '\n' : ' ');
	}
}

static Mat4 readMat(char** a)
{
	Mat4 m;
	for (int i = 0; i < 16; ++i)
	{
		m[i] = std::atof(a[i]);
	}
	return m;
}

static Vec3 readVec(char** a) { return Vec3{std::atof(a[0]), std::atof(a[1]), std::atof(a[2])}; }

int main(int argc, char** argv)
{
	if (argc < 2)
	{
		return 2;
	}
	const char* cmd = argv[1];
	if (!std::strcmp(cmd, "ecef"))
	{
		p3(GeodeticToEcef(std::atof(argv[2]), std::atof(argv[3]), std::atof(argv[4])));
	}
	else if (!std::strcmp(cmd, "geodetic"))
	{
		double la = 0, lo = 0, h = 0;
		EcefToGeodetic(readVec(argv + 2), la, lo, h);
		std::printf("%.17g %.17g %.17g\n", la, lo, h);
	}
	else if (!std::strcmp(cmd, "enuframe"))
	{
		p16(EnuFrame(std::atof(argv[2]), std::atof(argv[3]), std::atof(argv[4])));
	}
	else if (!std::strcmp(cmd, "zone"))
	{
		p16(ZoneTransform(std::atof(argv[2]), std::atof(argv[3]), std::atof(argv[4]), std::atof(argv[5])));
	}
	else if (!std::strcmp(cmd, "apply"))
	{
		p3(ApplyPoint(readMat(argv + 2), readVec(argv + 18)));
	}
	else if (!std::strcmp(cmd, "applyvec"))
	{
		p3(ApplyVector(readMat(argv + 2), readVec(argv + 18)));
	}
	else if (!std::strcmp(cmd, "inverse"))
	{
		p16(RigidInverse(readMat(argv + 2)));
	}
	else if (!std::strcmp(cmd, "toarea"))
	{
		p16(ZoneLocalToAreaEnu(readMat(argv + 2), std::atof(argv[18]), std::atof(argv[19]), std::atof(argv[20])));
	}
	else if (!std::strcmp(cmd, "actor"))
	{
		p16(UEActorMatrix(readMat(argv + 2)));
	}
	else if (!std::strcmp(cmd, "enu2ue"))
	{
		p3(EnuToUE(readVec(argv + 2)));
	}
	else if (!std::strcmp(cmd, "ue2enu"))
	{
		p3(UEToEnu(readVec(argv + 2)));
	}
	else if (!std::strcmp(cmd, "rigid"))
	{
		double det = 0;
		const double e = RigidityError(readMat(argv + 2), det);
		std::printf("%.15e %.12f\n", e, det);
	}
	else if (!std::strcmp(cmd, "yaw"))
	{
		std::printf("%.10f\n", UEYawDegFromZoneToArea(readMat(argv + 2)));
	}
	else if (!std::strcmp(cmd, "pip"))
	{
		const int n = std::atoi(argv[2]);
		double xs[64], ys[64];
		for (int i = 0; i < n && i < 64; ++i)
		{
			xs[i] = std::atof(argv[3 + 2 * i]);
			ys[i] = std::atof(argv[4 + 2 * i]);
		}
		const bool inside = PointInPolygon(xs, ys, static_cast<std::size_t>(n), std::atof(argv[3 + 2 * n]), std::atof(argv[4 + 2 * n]));
		std::printf("%d\n", inside ? 1 : 0);
	}
	else if (!std::strcmp(cmd, "dist"))
	{
		const int n = std::atoi(argv[2]);
		double xs[64], ys[64];
		for (int i = 0; i < n && i < 64; ++i)
		{
			xs[i] = std::atof(argv[3 + 2 * i]);
			ys[i] = std::atof(argv[4 + 2 * i]);
		}
		std::printf("%.17g\n", DistanceToPolygon(xs, ys, static_cast<std::size_t>(n), std::atof(argv[3 + 2 * n]), std::atof(argv[4 + 2 * n])));
	}
	else if (!std::strcmp(cmd, "overlap"))
	{
		const int na = std::atoi(argv[2]);
		double axs[64], ays[64], bxs[64], bys[64];
		for (int i = 0; i < na && i < 64; ++i)
		{
			axs[i] = std::atof(argv[3 + 2 * i]);
			ays[i] = std::atof(argv[4 + 2 * i]);
		}
		const int nb = std::atoi(argv[3 + 2 * na]);
		for (int i = 0; i < nb && i < 64; ++i)
		{
			bxs[i] = std::atof(argv[4 + 2 * na + 2 * i]);
			bys[i] = std::atof(argv[5 + 2 * na + 2 * i]);
		}
		std::printf("%d\n", PolygonsOverlap(axs, ays, static_cast<std::size_t>(na), bxs, bys, static_cast<std::size_t>(nb)) ? 1 : 0);
	}
	else if (!std::strcmp(cmd, "blocker"))
	{
		Vec3 w, h;
		BlockerAxes(readVec(argv + 2), w, h);
		p3(w);
		p3(h);
	}
	else if (!std::strcmp(cmd, "cell") && argc >= 5)
	{
		int x = 0, y = 0;
		LonLatToCell(std::atof(argv[2]), std::atof(argv[3]), std::atoi(argv[4]), x, y);
		std::printf("%d %d\n", x, y);
	}
	else if (!std::strcmp(cmd, "cells"))
	{
		// One "lon lat z" per stdin line; blank lines are skipped. Numbers are parsed with strtod / strtol so
		// Python repr() output round-trips exactly.
		const std::string in = readStdin();
		std::size_t pos = 0;
		while (pos < in.size())
		{
			std::size_t nl = in.find('\n', pos);
			if (nl == std::string::npos)
			{
				nl = in.size();
			}
			const std::string line = in.substr(pos, nl - pos);
			pos = nl + 1;
			const char* s = line.c_str();
			char* end = nullptr;
			const double lon = std::strtod(s, &end);
			if (end == s)
			{
				continue;
			}
			s = end;
			const double lat = std::strtod(s, &end);
			s = end;
			const int z = static_cast<int>(std::strtol(s, &end, 10));
			int x = 0, y = 0;
			LonLatToCell(lon, lat, z, x, y);
			std::printf("%d %d\n", x, y);
		}
	}
	else if (!std::strcmp(cmd, "cellbounds") && argc >= 5)
	{
		double w = 0, s = 0, e = 0, n = 0;
		CellBounds(std::atoi(argv[2]), std::atoi(argv[3]), std::atoi(argv[4]), w, s, e, n);
		std::printf("%.17g %.17g %.17g %.17g\n", w, s, e, n);
	}
	else
	{
		return 2;
	}
	return 0;
}
