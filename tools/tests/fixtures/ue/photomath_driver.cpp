#include "Photo/GolmokPhotoMath.h"

#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <cstring>

// Command-line driver for tools/tests/test_ue_photo_math.py (WP-12 design §8-2). Doubles print with %.17g.
// ALL inputs come through stdin (Windows limits a command line to 32 KiB and converts argv to the ANSI code page):
// numbers are whitespace-separated tokens, "nan" / "inf" are accepted (strtod).
// Commands (argv[1]) and their stdin:
//   clamp      v lo hi                                   ClampParam
//   quant      v min max step [dir]                      Quantize (dir is ignored)
//   steplin    v min max step [dir]                      StepLinear (dir defaults to 0)
//   stepgeo    v min max ratio dir                       StepGeometric
//   table      dir v n t1..tn                            "StepTable(table, v, dir) NearestIndex(table, v)"
//   wrap       deg                                       WrapDeg180
//   fov2mm     fov [w]                                   FovToFocalMm (w defaults to 36)
//   sphere     cx cy cz r x y z                          "moved x y z"
//   poly       ax ay inset n x1 y1 .. xn yn m px py ..   one "code x y" line per point (ClampToPolygonXY)
//   polyq      n x1 y1 .. xn yn m px py ..               one "dist qx qy edge" line per point (NearestBoundaryPoint)
//   constrain  ax ay az r inset n x1 y1 .. xn yn m px py pz ..
//                                                        one "code x y z" line per point (Constrain); a rejected
//                                                        point (-1) prints the untouched sentinel -999999 x3
//   meta       key=value lines                           FormatPhotoMetaJson text as is. Keys: version time_utc
//                                                        preset (or "preset=-" -> null) zone_id zone_version
//                                                        ("zone=-" -> both null) lon lat height_m ("geo=-" -> all
//                                                        null) ue_location ("x y z") rotation ("p y r") fov
//                                                        exposure_ev dof_enabled (0/1) focal_m fstop multiplier
//                                                        character_hidden (0/1). Values are raw bytes (UTF-8).
// Parse failures print "ERROR <message>" and exit 3; unknown commands exit 2.
using namespace GolmokPhotoMath;

namespace
{
	std::string ReadStdin()
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

	/** Whitespace-separated tokens. */
	std::vector<std::string> Tokenize(const std::string& In)
	{
		std::vector<std::string> Out;
		std::size_t Pos = 0;
		while (Pos < In.size())
		{
			while (Pos < In.size() && std::isspace(static_cast<unsigned char>(In[Pos])))
			{
				++Pos;
			}
			if (Pos >= In.size())
			{
				break;
			}
			const std::size_t Start = Pos;
			while (Pos < In.size() && !std::isspace(static_cast<unsigned char>(In[Pos])))
			{
				++Pos;
			}
			Out.push_back(In.substr(Start, Pos - Start));
		}
		return Out;
	}

	bool ParseDouble(const std::string& Token, double& Out)
	{
		if (Token.empty())
		{
			return false;
		}
		char* End = nullptr;
		Out = std::strtod(Token.c_str(), &End);
		return End != nullptr && *End == '\0';
	}

	bool ParseInt(const std::string& Token, long long& Out)
	{
		if (Token.empty())
		{
			return false;
		}
		char* End = nullptr;
		Out = std::strtoll(Token.c_str(), &End, 10);
		return End != nullptr && *End == '\0';
	}

	/** Sequential reader over the stdin tokens; every failure prints ERROR and is remembered. */
	class TokenReader
	{
	public:
		explicit TokenReader(const std::string& In)
			: Tokens(Tokenize(In))
		{
		}

		bool Failed() const { return bFailed; }
		bool HasMore() const { return Pos < Tokens.size(); }

		double Number(const char* What)
		{
			double V = 0.0;
			if (Pos >= Tokens.size() || !ParseDouble(Tokens[Pos], V))
			{
				Fail(What);
				return 0.0;
			}
			++Pos;
			return V;
		}

		long long Integer(const char* What)
		{
			long long V = 0;
			if (Pos >= Tokens.size() || !ParseInt(Tokens[Pos], V))
			{
				Fail(What);
				return 0;
			}
			++Pos;
			return V;
		}

		/** Non-negative count; anything else is a parse failure. */
		std::size_t Count(const char* What)
		{
			const long long V = Integer(What);
			if (bFailed || V < 0)
			{
				Fail(What);
				return 0;
			}
			return static_cast<std::size_t>(V);
		}

		/** Optional trailing number: Default when the input is exhausted. */
		double NumberOr(const char* What, double Default)
		{
			return HasMore() ? Number(What) : Default;
		}

	private:
		void Fail(const char* What)
		{
			if (!bFailed)
			{
				std::printf("ERROR bad or missing %s at token %llu\n", What, static_cast<unsigned long long>(Pos));
			}
			bFailed = true;
		}

		std::vector<std::string> Tokens;
		std::size_t Pos = 0;
		bool bFailed = false;
	};

	int ReadRing(TokenReader& R, std::vector<double>& Xs, std::vector<double>& Ys)
	{
		const std::size_t N = R.Count("ring size");
		for (std::size_t i = 0; i < N && !R.Failed(); ++i)
		{
			Xs.push_back(R.Number("ring x"));
			Ys.push_back(R.Number("ring y"));
		}
		return R.Failed() ? 3 : 0;
	}

	bool ParseVec3Text(const std::string& Text, Vec3& Out)
	{
		const std::vector<std::string> Parts = Tokenize(Text);
		if (Parts.size() != 3)
		{
			return false;
		}
		for (std::size_t i = 0; i < 3; ++i)
		{
			if (!ParseDouble(Parts[i], Out[i]))
			{
				return false;
			}
		}
		return true;
	}

	int RunMeta(const std::string& In)
	{
		PhotoMeta M;
		std::size_t LineStart = 0;
		while (LineStart < In.size())
		{
			std::size_t LineEnd = In.find('\n', LineStart);
			if (LineEnd == std::string::npos)
			{
				LineEnd = In.size();
			}
			std::string Line = In.substr(LineStart, LineEnd - LineStart);
			LineStart = LineEnd + 1;
			if (!Line.empty() && Line.back() == '\r')
			{
				Line.pop_back();
			}
			if (Line.empty())
			{
				continue;
			}
			const std::size_t Eq = Line.find('=');
			if (Eq == std::string::npos)
			{
				std::printf("ERROR meta: line without '=': %s\n", Line.c_str());
				return 3;
			}
			const std::string Key = Line.substr(0, Eq);
			const std::string Value = Line.substr(Eq + 1);
			double D = 0.0;
			long long I = 0;
			bool bOk = true;
			if (Key == "version")
			{
				bOk = ParseInt(Value, I);
				M.Version = static_cast<int>(I);
			}
			else if (Key == "time_utc")
			{
				M.TimeUtc = Value;
			}
			else if (Key == "preset")
			{
				M.bHasPreset = (Value != "-");
				M.Preset = M.bHasPreset ? Value : std::string();
			}
			else if (Key == "zone")
			{
				bOk = (Value == "-");
				M.bHasZone = false;
			}
			else if (Key == "zone_id")
			{
				M.bHasZone = true;
				M.ZoneId = Value;
			}
			else if (Key == "zone_version")
			{
				bOk = ParseInt(Value, I);
				M.bHasZone = true;
				M.ZoneVersion = static_cast<int>(I);
			}
			else if (Key == "geo")
			{
				bOk = (Value == "-");
				M.bHasGeo = false;
			}
			else if (Key == "lon" || Key == "lat" || Key == "height_m")
			{
				bOk = ParseDouble(Value, D);
				M.bHasGeo = true;
				if (Key == "lon")
				{
					M.Lon = D;
				}
				else if (Key == "lat")
				{
					M.Lat = D;
				}
				else
				{
					M.HeightM = D;
				}
			}
			else if (Key == "ue_location")
			{
				bOk = ParseVec3Text(Value, M.UeLocation);
			}
			else if (Key == "rotation")
			{
				bOk = ParseVec3Text(Value, M.Rotation);
			}
			else if (Key == "fov")
			{
				bOk = ParseDouble(Value, M.Fov);
			}
			else if (Key == "exposure_ev")
			{
				bOk = ParseDouble(Value, M.ExposureEv);
			}
			else if (Key == "dof_enabled")
			{
				bOk = ParseInt(Value, I);
				M.bDofEnabled = (I != 0);
			}
			else if (Key == "focal_m")
			{
				bOk = ParseDouble(Value, M.FocalM);
			}
			else if (Key == "fstop")
			{
				bOk = ParseDouble(Value, M.Fstop);
			}
			else if (Key == "multiplier")
			{
				bOk = ParseInt(Value, I);
				M.Multiplier = static_cast<int>(I);
			}
			else if (Key == "character_hidden")
			{
				bOk = ParseInt(Value, I);
				M.bCharacterHidden = (I != 0);
			}
			else
			{
				std::printf("ERROR meta: unknown key '%s'\n", Key.c_str());
				return 3;
			}
			if (!bOk)
			{
				std::printf("ERROR meta: bad value for '%s'\n", Key.c_str());
				return 3;
			}
		}
		const std::string Text = FormatPhotoMetaJson(M);
		std::fwrite(Text.data(), 1, Text.size(), stdout);
		return 0;
	}
} // namespace

int main(int argc, char** argv)
{
	if (argc < 2)
	{
		return 2;
	}
	const char* Cmd = argv[1];
	if (!std::strcmp(Cmd, "meta"))
	{
		return RunMeta(ReadStdin());
	}
	const std::string In = ReadStdin();
	TokenReader R(In);
	if (!std::strcmp(Cmd, "clamp"))
	{
		const double V = R.Number("v");
		const double Lo = R.Number("lo");
		const double Hi = R.Number("hi");
		if (R.Failed())
		{
			return 3;
		}
		std::printf("%.17g\n", ClampParam(V, Lo, Hi));
	}
	else if (!std::strcmp(Cmd, "quant") || !std::strcmp(Cmd, "steplin"))
	{
		const double V = R.Number("v");
		const double Min = R.Number("min");
		const double Max = R.Number("max");
		const double Step = R.Number("step");
		const int Dir = static_cast<int>(R.NumberOr("dir", 0.0));
		if (R.Failed())
		{
			return 3;
		}
		const double Result = (Cmd[0] == 'q') ? Quantize(V, Min, Max, Step) : StepLinear(V, Min, Max, Step, Dir);
		std::printf("%.17g\n", Result);
	}
	else if (!std::strcmp(Cmd, "stepgeo"))
	{
		const double V = R.Number("v");
		const double Min = R.Number("min");
		const double Max = R.Number("max");
		const double Ratio = R.Number("ratio");
		const int Dir = static_cast<int>(R.Number("dir"));
		if (R.Failed())
		{
			return 3;
		}
		std::printf("%.17g\n", StepGeometric(V, Min, Max, Ratio, Dir));
	}
	else if (!std::strcmp(Cmd, "table"))
	{
		const int Dir = static_cast<int>(R.Integer("dir"));
		const double V = R.Number("v");
		const std::size_t N = R.Count("n");
		std::vector<double> Table;
		for (std::size_t i = 0; i < N && !R.Failed(); ++i)
		{
			Table.push_back(R.Number("table value"));
		}
		if (R.Failed())
		{
			return 3;
		}
		std::printf("%.17g %llu\n", StepTable(Table, V, Dir), static_cast<unsigned long long>(NearestIndex(Table, V)));
	}
	else if (!std::strcmp(Cmd, "wrap"))
	{
		const double Deg = R.Number("deg");
		if (R.Failed())
		{
			return 3;
		}
		std::printf("%.17g\n", WrapDeg180(Deg));
	}
	else if (!std::strcmp(Cmd, "fov2mm"))
	{
		const double Fov = R.Number("fov");
		const double W = R.NumberOr("w", 36.0);
		if (R.Failed())
		{
			return 3;
		}
		std::printf("%.17g\n", FovToFocalMm(Fov, W));
	}
	else if (!std::strcmp(Cmd, "sphere"))
	{
		Vec3 Center{};
		Vec3 P{};
		for (std::size_t i = 0; i < 3; ++i)
		{
			Center[i] = R.Number("center");
		}
		const double Radius = R.Number("r");
		for (std::size_t i = 0; i < 3; ++i)
		{
			P[i] = R.Number("p");
		}
		if (R.Failed())
		{
			return 3;
		}
		const bool bMoved = ClampToSphere(Center, Radius, P);
		std::printf("%d %.17g %.17g %.17g\n", bMoved ? 1 : 0, P[0], P[1], P[2]);
	}
	else if (!std::strcmp(Cmd, "poly"))
	{
		const double Ax = R.Number("ax");
		const double Ay = R.Number("ay");
		const double Inset = R.Number("inset");
		std::vector<double> Xs;
		std::vector<double> Ys;
		if (ReadRing(R, Xs, Ys) != 0)
		{
			return 3;
		}
		const std::size_t M = R.Count("m");
		for (std::size_t i = 0; i < M; ++i)
		{
			double X = R.Number("px");
			double Y = R.Number("py");
			if (R.Failed())
			{
				return 3;
			}
			const int Code = ClampToPolygonXY(Xs.data(), Ys.data(), Xs.size(), Ax, Ay, Inset, X, Y);
			std::printf("%d %.17g %.17g\n", Code, X, Y);
		}
		if (R.Failed())
		{
			return 3;
		}
	}
	else if (!std::strcmp(Cmd, "polyq"))
	{
		std::vector<double> Xs;
		std::vector<double> Ys;
		if (ReadRing(R, Xs, Ys) != 0)
		{
			return 3;
		}
		const std::size_t M = R.Count("m");
		for (std::size_t i = 0; i < M; ++i)
		{
			const double X = R.Number("px");
			const double Y = R.Number("py");
			if (R.Failed())
			{
				return 3;
			}
			double Qx = 0.0;
			double Qy = 0.0;
			std::size_t Edge = 0;
			const double Dist = NearestBoundaryPoint(Xs.data(), Ys.data(), Xs.size(), X, Y, Qx, Qy, Edge);
			std::printf("%.17g %.17g %.17g %llu\n", Dist, Qx, Qy, static_cast<unsigned long long>(Edge));
		}
		if (R.Failed())
		{
			return 3;
		}
	}
	else if (!std::strcmp(Cmd, "constrain"))
	{
		Constraint C;
		for (std::size_t i = 0; i < 3; ++i)
		{
			C.Anchor[i] = R.Number("anchor");
		}
		C.RadiusCm = R.Number("r");
		C.InsetCm = R.Number("inset");
		std::vector<double> Xs;
		std::vector<double> Ys;
		if (ReadRing(R, Xs, Ys) != 0)
		{
			return 3;
		}
		C.Xs = Xs.empty() ? nullptr : Xs.data();
		C.Ys = Ys.empty() ? nullptr : Ys.data();
		C.N = Xs.size();
		const std::size_t M = R.Count("m");
		for (std::size_t i = 0; i < M; ++i)
		{
			Vec3 Desired{};
			for (std::size_t k = 0; k < 3; ++k)
			{
				Desired[k] = R.Number("p");
			}
			if (R.Failed())
			{
				return 3;
			}
			Vec3 Out{-999999.0, -999999.0, -999999.0};
			const int Code = Constrain(C, Desired, Out);
			std::printf("%d %.17g %.17g %.17g\n", Code, Out[0], Out[1], Out[2]);
		}
		if (R.Failed())
		{
			return 3;
		}
	}
	else
	{
		return 2;
	}
	return 0;
}
