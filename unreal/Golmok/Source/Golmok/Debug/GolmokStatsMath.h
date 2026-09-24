#pragma once

// Pure, header-only statistics and camera-path math for the Golmok debug tools (WP-05 design §4-3, §4-4).
// No Unreal headers on purpose: tools/tests/test_ue_stats_math.py compiles this file with g++ (via
// fixtures/ue/statsmath_driver.cpp) and cross-checks it against numpy / a Python reference, so the HUD numbers and
// the path JSON format are verified in cloud CI without an engine. Debug/GolmokDebugSubsystem wraps it.
//
// Rules for this file: only the seven standard headers below, everything inline, double precision, no use of the
// standard min/max templates (Windows.h defines macros with those names), no C stdio, no identifiers that collide
// with Unreal macros. It must build with g++ -std=c++17 -Wall -Wextra -Werror -pedantic and with MSVC as part of
// the Golmok module.
//
// Conventions:
//   FrameSample.DtSec   frame delta in seconds (FApp::GetDeltaTime()); Game/Render/GpuMs in milliseconds.
//   Percentile          numpy 'linear' (the default of np.percentile), so 1% low == np.percentile(fps, 1).
//   PoseSample          t seconds, p level UE cm (x, y, z), r degrees (pitch, yaw, roll).
//   Path JSON           fixed key order, one sample per line, t 3 decimals, p 2, r 3, trailing newline (§4-4).

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace GolmokStatsMath
{
	// ---------------------------------------------------------------------------------------------------------
	// Small helpers (own min/max: Windows.h defines macros with those names)
	// ---------------------------------------------------------------------------------------------------------

	inline double MinDouble(double A, double B) { return (B < A) ? B : A; }
	inline double MaxDouble(double A, double B) { return (A < B) ? B : A; }
	inline double ClampDouble(double V, double Lo, double Hi) { return MinDouble(MaxDouble(V, Lo), Hi); }
	inline int ClampInt(int V, int Lo, int Hi) { return (V < Lo) ? Lo : ((V > Hi) ? Hi : V); }
	inline bool IsDigitChar(char C) { return C >= '0' && C <= '9'; }

	// ---------------------------------------------------------------------------------------------------------
	// Frame statistics
	// ---------------------------------------------------------------------------------------------------------

	struct FrameSample
	{
		double DtSec = 0.0;
		double GameMs = 0.0;
		double RenderMs = 0.0;
		double GpuMs = 0.0;
	};

	/** Fixed-capacity ring buffer: when full, Push overwrites the oldest sample. */
	class RingBuffer
	{
	public:
		explicit RingBuffer(std::size_t InCapacity = 2048)
			: Buf((InCapacity > 0) ? InCapacity : 1)
		{
		}

		void Push(const FrameSample& S)
		{
			Buf[Head] = S;
			Head = (Head + 1) % Buf.size();
			if (Count < Buf.size())
			{
				++Count;
			}
		}

		void Clear()
		{
			Head = 0;
			Count = 0;
		}

		std::size_t Size() const { return Count; }
		std::size_t Capacity() const { return Buf.size(); }

		/** i = 0 is the newest sample. The caller keeps i < Size(); the index wraps regardless so it never overruns. */
		const FrameSample& FromNewest(std::size_t i) const
		{
			const std::size_t Cap = Buf.size();
			const std::size_t Index = (Head + Cap - 1 - (i % Cap)) % Cap;
			return Buf[Index];
		}

	private:
		std::vector<FrameSample> Buf;
		std::size_t Head = 0;
		std::size_t Count = 0;
	};

	struct Stats
	{
		std::size_t Frames = 0;
		double WindowSec = 0.0; // sum of DtSec over the frames used
		double AvgFps = 0.0;
		double OnePercentLowFps = 0.0;
		double AvgFrameMs = 0.0;
		double P99FrameMs = 0.0;
		double AvgGameMs = 0.0;
		double AvgRenderMs = 0.0;
		double AvgGpuMs = 0.0;
		bool HasGpu = false;
	};

	/** Same expression as the engine's ToMilliseconds: cycles * seconds-per-cycle * 1000. */
	inline double CyclesToMs(std::uint64_t Cycles, double SecondsPerCycle)
	{
		return static_cast<double>(Cycles) * SecondsPerCycle * 1000.0;
	}

	/**
	 * numpy 'linear' percentile: sort, h = (P / 100) * (N - 1), lo = floor(h), x[lo] + (h - lo) * (x[lo + 1] - x[lo]).
	 * N == 0 -> 0. P is clamped to [0, 100].
	 */
	inline double Percentile(std::vector<double> Values, double P)
	{
		if (Values.empty())
		{
			return 0.0;
		}
		std::sort(Values.begin(), Values.end());
		const std::size_t N = Values.size();
		if (N == 1)
		{
			return Values[0];
		}
		const double Q = ClampDouble(std::isfinite(P) ? P : 0.0, 0.0, 100.0) / 100.0;
		const double H = Q * static_cast<double>(N - 1);
		const double LoD = std::floor(H);
		const std::size_t Lo = static_cast<std::size_t>(LoD);
		if (Lo + 1 >= N)
		{
			return Values[N - 1];
		}
		const double Gamma = H - LoD;
		return Values[Lo] + Gamma * (Values[Lo + 1] - Values[Lo]);
	}

	/**
	 * Window rule: walk from the newest sample; samples with DtSec <= 0 are skipped; the first usable sample is
	 * always included; further samples are included while the accumulated DtSec stays <= WindowSec.
	 *   AvgFps           = Frames / sum(Dt)                  (perf_report.fps_avg)
	 *   OnePercentLowFps = Percentile({1 / Dt_i}, 1)         (perf_report: np.percentile(fps, 1))
	 *   P99FrameMs       = Percentile({1000 * Dt_i}, 99)
	 *   Avg*Ms           = arithmetic means; HasGpu = any(GpuMs > 0)
	 */
	inline Stats Compute(const RingBuffer& Ring, double WindowSec)
	{
		Stats Out;
		std::vector<double> Fps;
		std::vector<double> FrameMs;
		double SumDt = 0.0;
		double SumFrameMs = 0.0;
		double SumGame = 0.0;
		double SumRender = 0.0;
		double SumGpu = 0.0;
		bool AnyGpu = false;
		const std::size_t Size = Ring.Size();
		for (std::size_t i = 0; i < Size; ++i)
		{
			const FrameSample& S = Ring.FromNewest(i);
			if (!(S.DtSec > 0.0)) // also skips NaN
			{
				continue;
			}
			if (!Fps.empty() && SumDt + S.DtSec > WindowSec)
			{
				break;
			}
			SumDt += S.DtSec;
			Fps.push_back(1.0 / S.DtSec);
			FrameMs.push_back(1000.0 * S.DtSec);
			SumFrameMs += 1000.0 * S.DtSec;
			SumGame += S.GameMs;
			SumRender += S.RenderMs;
			SumGpu += S.GpuMs;
			if (S.GpuMs > 0.0)
			{
				AnyGpu = true;
			}
		}
		if (Fps.empty())
		{
			return Out;
		}
		const double N = static_cast<double>(Fps.size());
		Out.Frames = Fps.size();
		Out.WindowSec = SumDt;
		Out.AvgFps = N / SumDt;
		Out.OnePercentLowFps = Percentile(Fps, 1.0);
		Out.AvgFrameMs = SumFrameMs / N;
		Out.P99FrameMs = Percentile(FrameMs, 99.0);
		Out.AvgGameMs = SumGame / N;
		Out.AvgRenderMs = SumRender / N;
		Out.AvgGpuMs = SumGpu / N;
		Out.HasGpu = AnyGpu;
		return Out;
	}

	// ---------------------------------------------------------------------------------------------------------
	// Number formatting / parsing (locale independent, no C stdio)
	// ---------------------------------------------------------------------------------------------------------

	/** Decimal digits of a non-negative integer-valued double of any magnitude (exact: mantissa * 2^exp, big int). */
	inline std::string IntegerDoubleToString(double X)
	{
		if (!(X >= 1.0))
		{
			return "0";
		}
		if (X < 9.0e18)
		{
			return std::to_string(static_cast<unsigned long long>(X));
		}
		// X >= 2^53: X = Mant * 2^Exp with an integer Mant < 2^53 and Exp > 0. Little-endian base 1e9 limbs.
		int Exp = 0;
		const double Frac = std::frexp(X, &Exp); // X = Frac * 2^Exp, Frac in [0.5, 1)
		unsigned long long Mant = static_cast<unsigned long long>(std::ldexp(Frac, 53));
		Exp -= 53;
		const std::uint64_t Base = 1000000000ULL;
		std::vector<std::uint64_t> Limbs;
		while (Mant > 0)
		{
			Limbs.push_back(Mant % Base);
			Mant /= Base;
		}
		for (int Step = 0; Step < Exp; ++Step)
		{
			std::uint64_t Carry = 0;
			for (std::size_t i = 0; i < Limbs.size(); ++i)
			{
				const std::uint64_t V = Limbs[i] * 2ULL + Carry;
				Limbs[i] = V % Base;
				Carry = V / Base;
			}
			if (Carry > 0)
			{
				Limbs.push_back(Carry);
			}
		}
		std::string Out = std::to_string(Limbs.back());
		for (std::size_t i = Limbs.size() - 1; i > 0; --i)
		{
			std::string Limb = std::to_string(Limbs[i - 1]);
			Out += std::string(9 - Limb.size(), '0') + Limb;
		}
		return Out;
	}

	/**
	 * Sign, integer part and exactly Decimals fraction digits (Decimals clamped to 0..9). Rounding is
	 * std::llround(|v| * 10^d), i.e. half away from zero. A result that rounds to zero prints "0.00", never "-0.00".
	 * NaN / Inf -> "0". Magnitudes beyond the llround range fall back to floor + fraction rounding (still exact digits).
	 */
	inline std::string FormatFixed(double Value, int Decimals)
	{
		if (!std::isfinite(Value))
		{
			return "0";
		}
		const int D = ClampInt(Decimals, 0, 9);
		unsigned long long Scale = 1;
		for (int i = 0; i < D; ++i)
		{
			Scale *= 10ULL;
		}
		const double ScaleD = static_cast<double>(Scale);
		const bool bNegative = Value < 0.0;
		const double A = bNegative ? -Value : Value;

		std::string IntText;
		unsigned long long FracPart = 0;
		const double Scaled = A * ScaleD;
		if (Scaled < 9.0e18)
		{
			const unsigned long long R = static_cast<unsigned long long>(std::llround(Scaled));
			IntText = std::to_string(R / Scale);
			FracPart = R % Scale;
		}
		else if (A < 9.0e18)
		{
			const double IntD = std::floor(A);
			unsigned long long IntPart = static_cast<unsigned long long>(IntD);
			FracPart = static_cast<unsigned long long>(std::llround((A - IntD) * ScaleD));
			if (FracPart >= Scale)
			{
				FracPart = 0;
				++IntPart;
			}
			IntText = std::to_string(IntPart);
		}
		else
		{
			IntText = IntegerDoubleToString(A); // already an integer at this magnitude
			FracPart = 0;
		}

		std::string Out;
		const bool bZero = (IntText == "0") && (FracPart == 0);
		if (bNegative && !bZero)
		{
			Out += '-';
		}
		Out += IntText;
		if (D > 0)
		{
			std::string FracText = std::to_string(FracPart);
			Out += '.';
			Out += std::string(static_cast<std::size_t>(D) - FracText.size(), '0');
			Out += FracText;
		}
		return Out;
	}

	/**
	 * JSON number grammar at Text[Pos]: -? (0 | [1-9][0-9]*) (. [0-9]+)? ([eE] [+-]? [0-9]+)? -> std::stod.
	 * Pos moves past the number on success. Exponents that would overflow return false; extreme underflow gives 0,
	 * so std::stod never throws (the module builds without exceptions).
	 */
	inline bool ParseNumber(const std::string& Text, std::size_t& Pos, double& Out)
	{
		const std::size_t N = Text.size();
		std::size_t i = Pos;
		if (i < N && Text[i] == '-')
		{
			++i;
		}
		if (i >= N || !IsDigitChar(Text[i]))
		{
			return false;
		}
		long long IntDigits = 0;
		if (Text[i] == '0')
		{
			++i;
		}
		else
		{
			while (i < N && IsDigitChar(Text[i]))
			{
				++i;
				++IntDigits;
			}
		}
		long long LeadingFracZeros = 0;
		bool bFracHasNonZero = false;
		if (i < N && Text[i] == '.')
		{
			++i;
			if (i >= N || !IsDigitChar(Text[i]))
			{
				return false;
			}
			while (i < N && IsDigitChar(Text[i]))
			{
				if (!bFracHasNonZero)
				{
					if (Text[i] == '0')
					{
						++LeadingFracZeros;
					}
					else
					{
						bFracHasNonZero = true;
					}
				}
				++i;
			}
		}
		long long ExpValue = 0;
		if (i < N && (Text[i] == 'e' || Text[i] == 'E'))
		{
			++i;
			bool bExpNegative = false;
			if (i < N && (Text[i] == '+' || Text[i] == '-'))
			{
				bExpNegative = (Text[i] == '-');
				++i;
			}
			if (i >= N || !IsDigitChar(Text[i]))
			{
				return false;
			}
			while (i < N && IsDigitChar(Text[i]))
			{
				if (ExpValue < 100000)
				{
					ExpValue = ExpValue * 10 + (Text[i] - '0');
				}
				++i;
			}
			if (bExpNegative)
			{
				ExpValue = -ExpValue;
			}
		}
		// Keep std::stod away from ERANGE (it would throw): reject overflow, flush deep underflow to zero.
		// Decimal magnitude estimate: digits before the point (or -leading zeros after it) plus the exponent.
		const bool bZeroMantissa = (IntDigits == 0) && !bFracHasNonZero;
		const long long Magnitude = (IntDigits > 0) ? (IntDigits - 1 + ExpValue) : (-LeadingFracZeros - 1 + ExpValue);
		if (bZeroMantissa || Magnitude < -307)
		{
			Out = (Text[Pos] == '-') ? -0.0 : 0.0;
			Pos = i;
			return true;
		}
		if (Magnitude > 308)
		{
			return false;
		}
		if (Magnitude == 308)
		{
			// Compare the first 17 significant digits against DBL_MAX (1.7976931348623157e308); above it is overflow.
			std::string Digits;
			for (std::size_t k = Pos; k < i && Digits.size() < 17; ++k)
			{
				const char C = Text[k];
				if (C == 'e' || C == 'E')
				{
					break;
				}
				if (IsDigitChar(C) && (!Digits.empty() || C != '0'))
				{
					Digits += C;
				}
			}
			while (Digits.size() < 17)
			{
				Digits += '0';
			}
			if (Digits > "17976931348623157")
			{
				return false;
			}
		}
		Out = std::stod(Text.substr(Pos, i - Pos));
		Pos = i;
		return true;
	}

	// ---------------------------------------------------------------------------------------------------------
	// Camera path
	// ---------------------------------------------------------------------------------------------------------

	struct PoseSample
	{
		double T = 0.0;
		std::array<double, 3> P{}; // level UE cm (x, y, z)
		std::array<double, 3> R{}; // degrees (pitch, yaw, roll)
	};

	struct CameraPath
	{
		int Version = 1;
		std::string Name;
		std::string Level;
		std::string Created;
		int Hz = 10;
		std::vector<PoseSample> Samples;

		/** t of the last sample, 0 when empty. */
		double Duration() const { return Samples.empty() ? 0.0 : Samples.back().T; }
	};

	/** JSON string literal: escapes " \ \n \t, other control characters as \u00XX; bytes >= 0x20 pass through. */
	inline std::string JsonQuote(const std::string& S)
	{
		static const char Hex[] = "0123456789abcdef";
		std::string Out;
		Out.reserve(S.size() + 2);
		Out += '"';
		for (std::size_t i = 0; i < S.size(); ++i)
		{
			const char C = S[i];
			const unsigned char U = static_cast<unsigned char>(C);
			if (C == '"')
			{
				Out += "\\\"";
			}
			else if (C == '\\')
			{
				Out += "\\\\";
			}
			else if (C == '\n')
			{
				Out += "\\n";
			}
			else if (C == '\t')
			{
				Out += "\\t";
			}
			else if (U < 0x20)
			{
				Out += "\\u00";
				Out += Hex[(U >> 4) & 0xF];
				Out += Hex[U & 0xF];
			}
			else
			{
				Out += C;
			}
		}
		Out += '"';
		return Out;
	}

	/** Exact §4-4 layout (see the file comment). Never fails; an empty path prints an empty samples array. */
	inline std::string FormatPathJson(const CameraPath& Path)
	{
		std::string Out;
		Out += "{\"version\": ";
		Out += std::to_string(Path.Version);
		Out += ", \"name\": ";
		Out += JsonQuote(Path.Name);
		Out += ", \"level\": ";
		Out += JsonQuote(Path.Level);
		Out += ", \"hz\": ";
		Out += std::to_string(Path.Hz);
		Out += ", \"created\": ";
		Out += JsonQuote(Path.Created);
		Out += ", \"samples\": [\n";
		const std::size_t N = Path.Samples.size();
		for (std::size_t i = 0; i < N; ++i)
		{
			const PoseSample& S = Path.Samples[i];
			Out += "{\"t\": ";
			Out += FormatFixed(S.T, 3);
			Out += ", \"p\": [";
			Out += FormatFixed(S.P[0], 2);
			Out += ", ";
			Out += FormatFixed(S.P[1], 2);
			Out += ", ";
			Out += FormatFixed(S.P[2], 2);
			Out += "], \"r\": [";
			Out += FormatFixed(S.R[0], 3);
			Out += ", ";
			Out += FormatFixed(S.R[1], 3);
			Out += ", ";
			Out += FormatFixed(S.R[2], 3);
			Out += "]}";
			if (i + 1 < N)
			{
				Out += ',';
			}
			Out += '\n';
		}
		Out += "]}\n";
		return Out;
	}

	// ---- Small dedicated JSON reader (objects, arrays, strings, numbers, true/false/null, whitespace) ----

	struct JsonValue
	{
		enum class EType
		{
			Null,
			Bool,
			Number,
			String,
			Array,
			Object
		};

		EType Type = EType::Null;
		bool BoolValue = false;
		double NumberValue = 0.0;
		std::string StringValue;
		std::vector<JsonValue> Items;  // array elements, or object values
		std::vector<std::string> Keys; // object keys, parallel to Items (empty for arrays)

		/** First value stored under Key (objects only), nullptr when absent. */
		const JsonValue* Find(const std::string& Key) const
		{
			if (Type != EType::Object)
			{
				return nullptr;
			}
			for (std::size_t i = 0; i < Keys.size(); ++i)
			{
				if (Keys[i] == Key)
				{
					return &Items[i];
				}
			}
			return nullptr;
		}
	};

	inline std::string PathJsonError(std::size_t Pos, const std::string& Reason)
	{
		return "path json: at " + std::to_string(Pos) + ": " + Reason;
	}

	class JsonReader
	{
	public:
		explicit JsonReader(const std::string& InText)
			: Text(InText)
		{
		}

		/** Parses one document; trailing non-whitespace is an error. */
		bool Parse(JsonValue& Out)
		{
			Pos = 0;
			Depth = 0;
			Error.clear();
			if (!ParseValue(Out))
			{
				return false;
			}
			SkipWhitespace();
			if (Pos < Text.size())
			{
				return Fail("trailing characters after the document");
			}
			return true;
		}

		const std::string& GetError() const { return Error; }

	private:
		static constexpr int MaxDepth = 64;

		bool Fail(const std::string& Reason)
		{
			if (Error.empty())
			{
				Error = PathJsonError(Pos, Reason);
			}
			return false;
		}

		void SkipWhitespace()
		{
			while (Pos < Text.size())
			{
				const char C = Text[Pos];
				if (C == ' ' || C == '\t' || C == '\n' || C == '\r')
				{
					++Pos;
				}
				else
				{
					break;
				}
			}
		}

		bool Match(const char* Literal)
		{
			std::size_t i = 0;
			while (Literal[i] != '\0')
			{
				if (Pos + i >= Text.size() || Text[Pos + i] != Literal[i])
				{
					return false;
				}
				++i;
			}
			Pos += i;
			return true;
		}

		static void AppendUtf8(std::string& Out, std::uint32_t Code)
		{
			if (Code < 0x80)
			{
				Out += static_cast<char>(Code);
			}
			else if (Code < 0x800)
			{
				Out += static_cast<char>(0xC0 | (Code >> 6));
				Out += static_cast<char>(0x80 | (Code & 0x3F));
			}
			else if (Code < 0x10000)
			{
				Out += static_cast<char>(0xE0 | (Code >> 12));
				Out += static_cast<char>(0x80 | ((Code >> 6) & 0x3F));
				Out += static_cast<char>(0x80 | (Code & 0x3F));
			}
			else
			{
				Out += static_cast<char>(0xF0 | (Code >> 18));
				Out += static_cast<char>(0x80 | ((Code >> 12) & 0x3F));
				Out += static_cast<char>(0x80 | ((Code >> 6) & 0x3F));
				Out += static_cast<char>(0x80 | (Code & 0x3F));
			}
		}

		bool ReadHex4(std::uint32_t& Out)
		{
			if (Pos + 4 > Text.size())
			{
				return Fail("truncated \\u escape");
			}
			std::uint32_t V = 0;
			for (int i = 0; i < 4; ++i)
			{
				const char C = Text[Pos + static_cast<std::size_t>(i)];
				std::uint32_t Digit = 0;
				if (C >= '0' && C <= '9')
				{
					Digit = static_cast<std::uint32_t>(C - '0');
				}
				else if (C >= 'a' && C <= 'f')
				{
					Digit = static_cast<std::uint32_t>(C - 'a' + 10);
				}
				else if (C >= 'A' && C <= 'F')
				{
					Digit = static_cast<std::uint32_t>(C - 'A' + 10);
				}
				else
				{
					return Fail("bad hex digit in \\u escape");
				}
				V = (V << 4) | Digit;
			}
			Pos += 4;
			Out = V;
			return true;
		}

		bool ParseString(std::string& Out)
		{
			if (Pos >= Text.size() || Text[Pos] != '"')
			{
				return Fail("expected string");
			}
			++Pos;
			Out.clear();
			while (true)
			{
				if (Pos >= Text.size())
				{
					return Fail("unterminated string");
				}
				const char C = Text[Pos];
				const unsigned char U = static_cast<unsigned char>(C);
				if (C == '"')
				{
					++Pos;
					return true;
				}
				if (U < 0x20)
				{
					return Fail("control character in string");
				}
				if (C != '\\')
				{
					Out += C;
					++Pos;
					continue;
				}
				++Pos;
				if (Pos >= Text.size())
				{
					return Fail("unterminated escape");
				}
				const char E = Text[Pos];
				++Pos;
				switch (E)
				{
				case '"': Out += '"'; break;
				case '\\': Out += '\\'; break;
				case '/': Out += '/'; break;
				case 'b': Out += '\b'; break;
				case 'f': Out += '\f'; break;
				case 'n': Out += '\n'; break;
				case 'r': Out += '\r'; break;
				case 't': Out += '\t'; break;
				case 'u':
				{
					std::uint32_t Code = 0;
					if (!ReadHex4(Code))
					{
						return false;
					}
					if (Code >= 0xD800 && Code <= 0xDBFF && Pos + 6 <= Text.size() && Text[Pos] == '\\' && Text[Pos + 1] == 'u')
					{
						const std::size_t Saved = Pos;
						Pos += 2;
						std::uint32_t Low = 0;
						if (!ReadHex4(Low))
						{
							return false;
						}
						if (Low >= 0xDC00 && Low <= 0xDFFF)
						{
							Code = 0x10000 + ((Code - 0xD800) << 10) + (Low - 0xDC00);
						}
						else
						{
							Pos = Saved; // lone high surrogate: keep it as is, re-read the next escape normally
						}
					}
					AppendUtf8(Out, Code);
					break;
				}
				default:
					--Pos;
					return Fail("unknown escape");
				}
			}
		}

		bool ParseValue(JsonValue& Out)
		{
			SkipWhitespace();
			if (Pos >= Text.size())
			{
				return Fail("unexpected end of text");
			}
			const char C = Text[Pos];
			if (C == '{')
			{
				return ParseObject(Out);
			}
			if (C == '[')
			{
				return ParseArray(Out);
			}
			if (C == '"')
			{
				Out.Type = JsonValue::EType::String;
				return ParseString(Out.StringValue);
			}
			if (Match("true"))
			{
				Out.Type = JsonValue::EType::Bool;
				Out.BoolValue = true;
				return true;
			}
			if (Match("false"))
			{
				Out.Type = JsonValue::EType::Bool;
				Out.BoolValue = false;
				return true;
			}
			if (Match("null"))
			{
				Out.Type = JsonValue::EType::Null;
				return true;
			}
			if (C == '-' || IsDigitChar(C))
			{
				Out.Type = JsonValue::EType::Number;
				if (!ParseNumber(Text, Pos, Out.NumberValue))
				{
					return Fail("bad number");
				}
				return true;
			}
			return Fail("unexpected character");
		}

		bool ParseArray(JsonValue& Out)
		{
			if (++Depth > MaxDepth)
			{
				return Fail("nesting too deep");
			}
			++Pos; // '['
			Out.Type = JsonValue::EType::Array;
			Out.Items.clear();
			Out.Keys.clear();
			SkipWhitespace();
			if (Pos < Text.size() && Text[Pos] == ']')
			{
				++Pos;
				--Depth;
				return true;
			}
			while (true)
			{
				Out.Items.emplace_back();
				if (!ParseValue(Out.Items.back()))
				{
					return false;
				}
				SkipWhitespace();
				if (Pos >= Text.size())
				{
					return Fail("unterminated array");
				}
				if (Text[Pos] == ',')
				{
					++Pos;
					continue;
				}
				if (Text[Pos] == ']')
				{
					++Pos;
					--Depth;
					return true;
				}
				return Fail("expected ',' or ']'");
			}
		}

		bool ParseObject(JsonValue& Out)
		{
			if (++Depth > MaxDepth)
			{
				return Fail("nesting too deep");
			}
			++Pos; // '{'
			Out.Type = JsonValue::EType::Object;
			Out.Items.clear();
			Out.Keys.clear();
			SkipWhitespace();
			if (Pos < Text.size() && Text[Pos] == '}')
			{
				++Pos;
				--Depth;
				return true;
			}
			while (true)
			{
				SkipWhitespace();
				std::string Key;
				if (!ParseString(Key))
				{
					return false;
				}
				SkipWhitespace();
				if (Pos >= Text.size() || Text[Pos] != ':')
				{
					return Fail("expected ':'");
				}
				++Pos;
				Out.Keys.push_back(Key);
				Out.Items.emplace_back();
				if (!ParseValue(Out.Items.back()))
				{
					return false;
				}
				SkipWhitespace();
				if (Pos >= Text.size())
				{
					return Fail("unterminated object");
				}
				if (Text[Pos] == ',')
				{
					++Pos;
					continue;
				}
				if (Text[Pos] == '}')
				{
					++Pos;
					--Depth;
					return true;
				}
				return Fail("expected ',' or '}'");
			}
		}

		const std::string& Text;
		std::size_t Pos = 0;
		int Depth = 0;
		std::string Error;
	};

	/** Reads an array of exactly three numbers into Out. */
	inline bool ReadVec3(const JsonValue* V, std::array<double, 3>& Out)
	{
		if (V == nullptr || V->Type != JsonValue::EType::Array || V->Items.size() != 3)
		{
			return false;
		}
		for (std::size_t i = 0; i < 3; ++i)
		{
			if (V->Items[i].Type != JsonValue::EType::Number)
			{
				return false;
			}
			Out[i] = V->Items[i].NumberValue;
		}
		return true;
	}

	/**
	 * Parses a path file. Key order is irrelevant and unknown keys are ignored. Errors ("path json: at <pos>: <why>"):
	 * malformed or truncated text, version != 1, missing samples, a sample without t/p/r, t not monotonic
	 * (a t smaller than the previous one). Out is only written on success.
	 */
	inline bool ParsePathJson(const std::string& Text, CameraPath& Out, std::string& Error)
	{
		JsonValue Root;
		JsonReader Reader(Text);
		if (!Reader.Parse(Root))
		{
			Error = Reader.GetError();
			return false;
		}
		if (Root.Type != JsonValue::EType::Object)
		{
			Error = PathJsonError(0, "document is not an object");
			return false;
		}
		CameraPath Path;
		const JsonValue* Version = Root.Find("version");
		if (Version == nullptr || Version->Type != JsonValue::EType::Number)
		{
			Error = PathJsonError(0, "missing numeric 'version'");
			return false;
		}
		if (Version->NumberValue != 1.0)
		{
			Error = PathJsonError(0, "version must be 1 (got " + FormatFixed(Version->NumberValue, 0) + ")");
			return false;
		}
		Path.Version = 1;
		const char* StringKeys[3] = {"name", "level", "created"};
		std::string* StringTargets[3] = {&Path.Name, &Path.Level, &Path.Created};
		for (std::size_t k = 0; k < 3; ++k)
		{
			const JsonValue* V = Root.Find(StringKeys[k]);
			if (V == nullptr || V->Type == JsonValue::EType::Null)
			{
				continue;
			}
			if (V->Type != JsonValue::EType::String)
			{
				Error = PathJsonError(0, std::string("'") + StringKeys[k] + "' must be a string");
				return false;
			}
			*StringTargets[k] = V->StringValue;
		}
		const JsonValue* Hz = Root.Find("hz");
		if (Hz != nullptr && Hz->Type != JsonValue::EType::Null)
		{
			if (Hz->Type != JsonValue::EType::Number)
			{
				Error = PathJsonError(0, "'hz' must be a number");
				return false;
			}
			Path.Hz = static_cast<int>(std::llround(ClampDouble(Hz->NumberValue, -1.0e9, 1.0e9)));
		}
		const JsonValue* Samples = Root.Find("samples");
		if (Samples == nullptr || Samples->Type != JsonValue::EType::Array)
		{
			Error = PathJsonError(0, "missing 'samples' array");
			return false;
		}
		Path.Samples.reserve(Samples->Items.size());
		for (std::size_t i = 0; i < Samples->Items.size(); ++i)
		{
			const JsonValue& Item = Samples->Items[i];
			const std::string Where = "sample " + std::to_string(i) + ": ";
			if (Item.Type != JsonValue::EType::Object)
			{
				Error = PathJsonError(i, Where + "not an object");
				return false;
			}
			PoseSample S;
			const JsonValue* T = Item.Find("t");
			if (T == nullptr || T->Type != JsonValue::EType::Number || !std::isfinite(T->NumberValue))
			{
				Error = PathJsonError(i, Where + "missing numeric 't'");
				return false;
			}
			S.T = T->NumberValue;
			if (!ReadVec3(Item.Find("p"), S.P))
			{
				Error = PathJsonError(i, Where + "'p' must be [x, y, z]");
				return false;
			}
			if (!ReadVec3(Item.Find("r"), S.R))
			{
				Error = PathJsonError(i, Where + "'r' must be [pitch, yaw, roll]");
				return false;
			}
			if (!Path.Samples.empty() && S.T < Path.Samples.back().T)
			{
				Error = PathJsonError(i, Where + "t is not monotonic");
				return false;
			}
			Path.Samples.push_back(S);
		}
		Out = Path;
		Error.clear();
		return true;
	}

	// ---------------------------------------------------------------------------------------------------------
	// Interpolation
	// ---------------------------------------------------------------------------------------------------------

	/** A + Alpha * delta, with delta = B - A normalized to (-180, 180] (shortest arc). Result is not re-wrapped. */
	inline double LerpAngleDeg(double A, double B, double Alpha)
	{
		double Delta = B - A;
		Delta -= 360.0 * std::floor((Delta + 180.0) / 360.0); // [-180, 180)
		if (Delta <= -180.0)
		{
			Delta += 360.0;
		}
		return A + Delta * Alpha;
	}

	/**
	 * Piecewise-linear pose at time T: positions lerp, angles LerpAngleDeg. T before the first sample gives the
	 * first, after the last gives the last. False (Out untouched) when the path has no samples.
	 */
	inline bool PoseAt(const CameraPath& Path, double T, PoseSample& Out)
	{
		const std::vector<PoseSample>& S = Path.Samples;
		if (S.empty())
		{
			return false;
		}
		if (S.size() == 1 || !(T > S.front().T))
		{
			Out = S.front();
			return true;
		}
		if (!(T < S.back().T))
		{
			Out = S.back();
			return true;
		}
		// First sample with sample.T > T; S.front().T < T < S.back().T, so 1 <= Index <= size - 1.
		const auto Upper = std::upper_bound(
			S.begin(), S.end(), T, [](double Value, const PoseSample& Sample) { return Value < Sample.T; });
		const std::size_t Index = static_cast<std::size_t>(Upper - S.begin());
		const PoseSample& A = S[Index - 1];
		const PoseSample& B = S[Index];
		const double Span = B.T - A.T; // > 0 because A.T <= T < B.T
		const double U = ClampDouble((T - A.T) / Span, 0.0, 1.0);
		Out.T = T;
		for (std::size_t i = 0; i < 3; ++i)
		{
			Out.P[i] = A.P[i] + (B.P[i] - A.P[i]) * U;
			Out.R[i] = LerpAngleDeg(A.R[i], B.R[i], U);
		}
		return true;
	}
} // namespace GolmokStatsMath
