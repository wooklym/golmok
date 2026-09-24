#include "GolmokStatsMath.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>

// Command-line driver for tools/tests/test_ue_stats_math.py (WP-05 design §8-2). Doubles print with %.17g.
// Commands:
//   pct <p> <n> v*n                                        Percentile
//   stats <window> <n> (dt game render gpu)*n              push oldest first, print the Stats fields
//   ring <cap> <n> v*n                                     Size then the newest (up to) 3 DtSec values
//   cycles <cycles> <spc>                                  CyclesToMs
//   fmt <value> <decimals>                                 FormatFixed
//   pathfmt <name> <hz> <level> <created> <n> (t x y z pitch yaw roll)*n     FormatPathJson text
//   pathparse            (stdin JSON)                      "version hz n" then one "t x y z pitch yaw roll" per sample
//   pathmeta             (stdin JSON)                      name, level, created on three lines
//   pose <t>             (stdin JSON)                      "px py pz pitch yaw roll"
//   angle <a> <b> <alpha>                                  LerpAngleDeg
// Parse failures print "ERROR <message>" and exit 3; unknown commands exit 2.
using namespace GolmokStatsMath;

static std::string ReadStdin()
{
	std::string In;
	char Buf[4096];
	std::size_t N = 0;
	while ((N = std::fread(Buf, 1, sizeof(Buf), stdin)) > 0)
	{
		In.append(Buf, N);
	}
	return In;
}

static bool ParseStdinPath(CameraPath& Path)
{
	std::string Error;
	if (!ParsePathJson(ReadStdin(), Path, Error))
	{
		std::printf("ERROR %s\n", Error.c_str());
		return false;
	}
	return true;
}

int main(int argc, char** argv)
{
	if (argc < 2)
	{
		return 2;
	}
	const char* Cmd = argv[1];
	if (!std::strcmp(Cmd, "pct") && argc >= 4)
	{
		const double P = std::atof(argv[2]);
		const int N = std::atoi(argv[3]);
		std::vector<double> Values;
		for (int i = 0; i < N && 4 + i < argc; ++i)
		{
			Values.push_back(std::atof(argv[4 + i]));
		}
		std::printf("%.17g\n", Percentile(Values, P));
	}
	else if (!std::strcmp(Cmd, "stats") && argc >= 4)
	{
		const double Window = std::atof(argv[2]);
		const int N = std::atoi(argv[3]);
		RingBuffer Ring;
		for (int i = 0; i < N && 4 + 4 * i + 3 < argc; ++i)
		{
			FrameSample S;
			S.DtSec = std::atof(argv[4 + 4 * i]);
			S.GameMs = std::atof(argv[5 + 4 * i]);
			S.RenderMs = std::atof(argv[6 + 4 * i]);
			S.GpuMs = std::atof(argv[7 + 4 * i]);
			Ring.Push(S);
		}
		const Stats St = Compute(Ring, Window);
		std::printf(
			"%llu %.17g %.17g %.17g %.17g %.17g %.17g %.17g %d\n", static_cast<unsigned long long>(St.Frames), St.AvgFps,
			St.OnePercentLowFps, St.AvgFrameMs, St.P99FrameMs, St.AvgGameMs, St.AvgRenderMs, St.AvgGpuMs,
			St.HasGpu ? 1 : 0);
	}
	else if (!std::strcmp(Cmd, "ring") && argc >= 4)
	{
		const int Cap = std::atoi(argv[2]);
		const int N = std::atoi(argv[3]);
		RingBuffer Ring(static_cast<std::size_t>(Cap));
		for (int i = 0; i < N && 4 + i < argc; ++i)
		{
			FrameSample S;
			S.DtSec = std::atof(argv[4 + i]);
			Ring.Push(S);
		}
		std::printf("%llu", static_cast<unsigned long long>(Ring.Size()));
		for (std::size_t i = 0; i < 3 && i < Ring.Size(); ++i)
		{
			std::printf(" %.17g", Ring.FromNewest(i).DtSec);
		}
		std::printf("\n");
	}
	else if (!std::strcmp(Cmd, "cycles") && argc >= 4)
	{
		const std::uint64_t Cycles = std::strtoull(argv[2], nullptr, 10);
		std::printf("%.17g\n", CyclesToMs(Cycles, std::atof(argv[3])));
	}
	else if (!std::strcmp(Cmd, "fmt") && argc >= 4)
	{
		std::printf("%s\n", FormatFixed(std::atof(argv[2]), std::atoi(argv[3])).c_str());
	}
	else if (!std::strcmp(Cmd, "pathfmt") && argc >= 7)
	{
		CameraPath Path;
		Path.Name = argv[2];
		Path.Hz = std::atoi(argv[3]);
		Path.Level = argv[4];
		Path.Created = argv[5];
		const int N = std::atoi(argv[6]);
		for (int i = 0; i < N && 7 + 7 * i + 6 < argc; ++i)
		{
			PoseSample S;
			S.T = std::atof(argv[7 + 7 * i]);
			for (int k = 0; k < 3; ++k)
			{
				S.P[static_cast<std::size_t>(k)] = std::atof(argv[8 + 7 * i + k]);
				S.R[static_cast<std::size_t>(k)] = std::atof(argv[11 + 7 * i + k]);
			}
			Path.Samples.push_back(S);
		}
		const std::string Text = FormatPathJson(Path);
		std::fwrite(Text.data(), 1, Text.size(), stdout);
	}
	else if (!std::strcmp(Cmd, "pathparse"))
	{
		CameraPath Path;
		if (!ParseStdinPath(Path))
		{
			return 3;
		}
		std::printf("%d %d %llu\n", Path.Version, Path.Hz, static_cast<unsigned long long>(Path.Samples.size()));
		for (std::size_t i = 0; i < Path.Samples.size(); ++i)
		{
			const PoseSample& S = Path.Samples[i];
			std::printf("%.17g %.17g %.17g %.17g %.17g %.17g %.17g\n", S.T, S.P[0], S.P[1], S.P[2], S.R[0], S.R[1], S.R[2]);
		}
	}
	else if (!std::strcmp(Cmd, "pathmeta"))
	{
		CameraPath Path;
		if (!ParseStdinPath(Path))
		{
			return 3;
		}
		std::printf("%s\n%s\n%s\n", Path.Name.c_str(), Path.Level.c_str(), Path.Created.c_str());
	}
	else if (!std::strcmp(Cmd, "pose") && argc >= 3)
	{
		CameraPath Path;
		if (!ParseStdinPath(Path))
		{
			return 3;
		}
		PoseSample S;
		if (!PoseAt(Path, std::atof(argv[2]), S))
		{
			std::printf("ERROR empty path\n");
			return 3;
		}
		std::printf("%.17g %.17g %.17g %.17g %.17g %.17g\n", S.P[0], S.P[1], S.P[2], S.R[0], S.R[1], S.R[2]);
	}
	else if (!std::strcmp(Cmd, "angle") && argc >= 5)
	{
		std::printf("%.17g\n", LerpAngleDeg(std::atof(argv[2]), std::atof(argv[3]), std::atof(argv[4])));
	}
	else
	{
		return 2;
	}
	return 0;
}
