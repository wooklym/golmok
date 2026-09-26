#pragma once
// Pure header (no Unreal types): tools/tests/test_ue_photo_math.py compiles it with g++ (fixtures/ue/photomath_driver.cpp)
// and cross-checks it against numpy / shapely. The only quoted includes are the two other pure headers of the module:
// Geo/GolmokGeoMath.h (PointInPolygon, DistanceToSegment) and Debug/GolmokStatsMath.h (FormatFixed, JsonQuote). Same
// rules as those headers (own min/max, no C stdio, C++17, -Wall -Wextra -Werror -pedantic). Units: cm for level UE
// positions, m for the JSON-facing values, degrees for angles.
//
// WP-12 design §3-1 (parameters, constraints, meta JSON) and §2-2 (meta layout). Every function is inline, double.
// The subsystem and the pawn call these with the GolmokPhotoMath:: qualifier (their member functions have similar
// names and MSVC C4458 is an error in the module).
#include "Debug/GolmokStatsMath.h"
#include "Geo/GolmokGeoMath.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace GolmokPhotoMath
{
	using Vec3 = std::array<double, 3>;

	// ---- small helpers (own min/max: Windows.h defines macros with those names) ---------------------------------

	inline double PhotoMin(double A, double B) { return (B < A) ? B : A; }
	inline double PhotoMax(double A, double B) { return (A < B) ? B : A; }
	/** -1, 0 or +1: any |Dir| >= 1 counts as one step in that direction. */
	inline int StepSign(int Dir) { return (Dir > 0) ? 1 : ((Dir < 0) ? -1 : 0); }
	/** Round half away from zero to the given number of decimals (0..9). */
	inline double RoundDecimals(double V, int Decimals)
	{
		if (!std::isfinite(V))
		{
			return V;
		}
		double Scale = 1.0;
		for (int i = 0; i < Decimals && i < 9; ++i)
		{
			Scale *= 10.0;
		}
		return std::round(V * Scale) / Scale;
	}
	inline double Distance3(const Vec3& A, const Vec3& B)
	{
		const double Dx = A[0] - B[0];
		const double Dy = A[1] - B[1];
		const double Dz = A[2] - B[2];
		return std::sqrt(Dx * Dx + Dy * Dy + Dz * Dz);
	}

	// ---- parameters ------------------------------------------------------------------------------------------
	/** Lo <= Hi assumed (swapped when not); NaN -> Lo. */
	inline double ClampParam(double V, double Lo, double Hi)
	{
		const double L = (Hi < Lo) ? Hi : Lo;
		const double H = (Hi < Lo) ? Lo : Hi;
		if (std::isnan(V))
		{
			return L;
		}
		return PhotoMin(PhotoMax(V, L), H);
	}

	/** k = round((V - Min) / Step) clamped to [0, floor((Max - Min) / Step + 1e-9)]; returns Min + k * Step. */
	inline double Quantize(double V, double Min, double Max, double Step)
	{
		const double L = (Max < Min) ? Max : Min;
		const double H = (Max < Min) ? Min : Max;
		if (!(Step > 0.0) || !std::isfinite(Step) || !std::isfinite(L) || !std::isfinite(H))
		{
			return ClampParam(V, L, H); // no usable grid: plain clamp (also catches a NaN step)
		}
		const double MaxK = std::floor((H - L) / Step + 1e-9);
		double K = std::isnan(V) ? 0.0 : std::round((V - L) / Step);
		if (!(K > 0.0))
		{
			K = 0.0; // negative, -0 or NaN
		}
		if (K > MaxK)
		{
			K = MaxK;
		}
		return L + K * Step;
	}

	/** Quantize(V + Dir * Step): Dir in {-1, 0, +1} (any |Dir| >= 1 counts as one step). */
	inline double StepLinear(double V, double Min, double Max, double Step, int Dir)
	{
		const double Base = std::isnan(V) ? Min : V;
		return Quantize(Base + static_cast<double>(StepSign(Dir)) * Step, Min, Max, Step);
	}

	/** V * Ratio^Dir clamped to [Min, Max], rounded to 3 decimals (focus distance). Dir 0 -> clamped V. */
	inline double StepGeometric(double V, double Min, double Max, double Ratio, int Dir)
	{
		double Next = std::isnan(V) ? Min : V;
		const int Sign = StepSign(Dir);
		if (Sign != 0 && std::isfinite(Ratio) && Ratio > 0.0)
		{
			Next = (Sign > 0) ? Next * Ratio : Next / Ratio;
		}
		return RoundDecimals(ClampParam(Next, Min, Max), 3);
	}

	/** Index of the nearest table value (ties: lower index); StepTable moves that index by Dir (clamped). Empty table -> V. */
	inline std::size_t NearestIndex(const std::vector<double>& Table, double V)
	{
		std::size_t Best = 0;
		double BestDist = 0.0;
		for (std::size_t i = 0; i < Table.size(); ++i)
		{
			const double D = std::fabs(Table[i] - V);
			if (i == 0 || D < BestDist) // NaN V: every D is NaN, the comparison fails, index 0 stays
			{
				Best = i;
				BestDist = D;
			}
		}
		return Best;
	}

	inline double StepTable(const std::vector<double>& Table, double V, int Dir)
	{
		if (Table.empty())
		{
			return V;
		}
		const std::size_t Index = NearestIndex(Table, V);
		const int Sign = StepSign(Dir);
		std::size_t Next = Index;
		if (Sign > 0 && Index + 1 < Table.size())
		{
			Next = Index + 1;
		}
		else if (Sign < 0 && Index > 0)
		{
			Next = Index - 1;
		}
		return Table[Next];
	}

	/** Wrap degrees into (-180, 180]. */
	inline double WrapDeg180(double Deg)
	{
		if (!std::isfinite(Deg))
		{
			return 0.0;
		}
		double W = Deg - 360.0 * std::floor((Deg + 180.0) / 360.0); // [-180, 180)
		if (W <= -180.0)
		{
			W += 360.0;
		}
		if (W > 180.0)
		{
			W -= 360.0; // rounding at the seam
		}
		return W;
	}

	/** 35 mm-equivalent focal length for a horizontal FOV: SensorWidthMm / (2 tan(fov / 2)); fov clamped to [1, 179]. Overlay only. */
	inline double FovToFocalMm(double FovDeg, double SensorWidthMm = 36.0)
	{
		const double Fov = ClampParam(FovDeg, 1.0, 179.0);
		return SensorWidthMm / (2.0 * std::tan(GolmokGeoMath::DegToRad(Fov) * 0.5));
	}

	// ---- constraints (level UE cm) ---------------------------------------------------------------------------
	/** P clamped into the closed ball (Center, RadiusCm). Returns true when it moved. RadiusCm <= 0 -> Center. */
	inline bool ClampToSphere(const Vec3& Center, double RadiusCm, Vec3& P)
	{
		const double Dist = Distance3(P, Center);
		if (!(RadiusCm > 0.0) || !std::isfinite(Dist))
		{
			const bool bMoved = !(P[0] == Center[0] && P[1] == Center[1] && P[2] == Center[2]);
			P = Center;
			return bMoved;
		}
		if (Dist <= RadiusCm)
		{
			return false;
		}
		const double Scale = RadiusCm / Dist;
		for (std::size_t i = 0; i < 3; ++i)
		{
			P[i] = Center[i] + (P[i] - Center[i]) * Scale;
		}
		return true;
	}

	/** Nearest point of the ring boundary (parallel arrays, N >= 3) to (X, Y); returns its distance, OutEdge = segment j (j -> j+1), ties: lowest j. */
	inline double NearestBoundaryPoint(const double* Xs, const double* Ys, std::size_t N, double X, double Y, double& OutX, double& OutY, std::size_t& OutEdge)
	{
		OutX = X;
		OutY = Y;
		OutEdge = 0;
		if (N == 0 || Xs == nullptr || Ys == nullptr)
		{
			return 0.0;
		}
		double Best = 0.0;
		for (std::size_t j = 0; j < N; ++j)
		{
			const std::size_t k = (j + 1 < N) ? j + 1 : 0;
			const double Ax = Xs[j];
			const double Ay = Ys[j];
			const double Bx = Xs[k];
			const double By = Ys[k];
			const double D = GolmokGeoMath::DistanceToSegment(Ax, Ay, Bx, By, X, Y);
			if (j == 0 || D < Best)
			{
				// Same projection as DistanceToSegment: t = ((P - A) . (B - A)) / |B - A|^2 clamped to [0, 1].
				const double Dx = Bx - Ax;
				const double Dy = By - Ay;
				const double L2 = Dx * Dx + Dy * Dy;
				double T = (L2 > 0.0) ? ((X - Ax) * Dx + (Y - Ay) * Dy) / L2 : 0.0;
				T = (T < 0.0) ? 0.0 : ((T > 1.0) ? 1.0 : T);
				Best = D;
				OutX = Ax + T * Dx;
				OutY = Ay + T * Dy;
				OutEdge = j;
			}
		}
		return Best;
	}

	/**
	 * XY clamp into the ring: inside (GolmokGeoMath::PointInPolygon) -> 0, unchanged. Outside -> nearest boundary point Q,
	 * then InsetCm toward (AnchorX, AnchorY) (the character, always inside), at most the distance to the anchor;
	 * returns 1 when the nudged point passes PointInPolygon, 2 when it does not (Out = Q on the boundary; the caller keeps
	 * its previous position). N < 3 -> 0, unchanged.
	 */
	inline int ClampToPolygonXY(const double* Xs, const double* Ys, std::size_t N, double AnchorX, double AnchorY, double InsetCm, double& X, double& Y)
	{
		if (N < 3 || Xs == nullptr || Ys == nullptr)
		{
			return 0;
		}
		if (GolmokGeoMath::PointInPolygon(Xs, Ys, N, X, Y))
		{
			return 0;
		}
		double Qx = X;
		double Qy = Y;
		std::size_t Edge = 0;
		NearestBoundaryPoint(Xs, Ys, N, X, Y, Qx, Qy, Edge);
		const double ToAnchorX = AnchorX - Qx;
		const double ToAnchorY = AnchorY - Qy;
		const double ToAnchor = std::sqrt(ToAnchorX * ToAnchorX + ToAnchorY * ToAnchorY);
		const double Inset = PhotoMin((InsetCm > 0.0) ? InsetCm : 0.0, ToAnchor);
		double Nx = Qx;
		double Ny = Qy;
		if (ToAnchor > 0.0 && Inset > 0.0)
		{
			Nx = Qx + ToAnchorX * (Inset / ToAnchor);
			Ny = Qy + ToAnchorY * (Inset / ToAnchor);
		}
		if (GolmokGeoMath::PointInPolygon(Xs, Ys, N, Nx, Ny))
		{
			X = Nx;
			Y = Ny;
			return 1;
		}
		X = Qx;
		Y = Qy;
		return 2;
	}

	struct Constraint
	{
		Vec3 Anchor{};                     // character capsule center
		double RadiusCm = 300.0;           // MaxDistanceM * 100
		double InsetCm = 20.0;             // FootprintMarginM * 100
		const double* Xs = nullptr;        // footprint ring (level UE cm), N = 0 -> no polygon
		const double* Ys = nullptr;
		std::size_t N = 0;
	};

	/**
	 * Sphere -> polygon, then re-checked: result must be inside the sphere AND (N == 0 or PointInPolygon). Returns 0 = accepted
	 * (Out written), 1 = accepted after a sphere clamp, 2 = accepted after a polygon clamp, 3 = both, -1 = rejected (Out untouched;
	 * the pawn keeps its previous position). The pawn calls this once per tick before the sweep.
	 */
	inline int Constrain(const Constraint& C, const Vec3& Desired, Vec3& Out)
	{
		Vec3 P = Desired;
		int Code = 0;
		if (ClampToSphere(C.Anchor, C.RadiusCm, P))
		{
			Code |= 1;
		}
		const bool bPolygon = (C.N >= 3) && C.Xs != nullptr && C.Ys != nullptr;
		if (bPolygon)
		{
			const int PolyCode = ClampToPolygonXY(C.Xs, C.Ys, C.N, C.Anchor[0], C.Anchor[1], C.InsetCm, P[0], P[1]);
			if (PolyCode == 2)
			{
				return -1;
			}
			if (PolyCode == 1)
			{
				Code |= 2;
			}
		}
		// Re-check both (design §6-2 ③): the polygon nudge can leave the sphere, and the accepted point must pass
		// PointInPolygon again (concave rings) before the pawn moves.
		const double Radius = (C.RadiusCm > 0.0) ? C.RadiusCm : 0.0;
		const double Dist = Distance3(P, C.Anchor);
		if (!(Dist <= Radius * (1.0 + 1e-12) + 1e-9))
		{
			return -1;
		}
		if (bPolygon && !GolmokGeoMath::PointInPolygon(C.Xs, C.Ys, C.N, P[0], P[1]))
		{
			return -1;
		}
		Out = P;
		return Code;
	}

	// ---- meta json -------------------------------------------------------------------------------------------
	struct PhotoMeta
	{
		int Version = 1;
		std::string TimeUtc;                       // "YYYY-MM-DDThh:mm:ssZ"
		bool bHasPreset = false;  std::string Preset;
		bool bHasZone = false;    std::string ZoneId;  int ZoneVersion = 0;
		bool bHasGeo = false;     double Lon = 0.0, Lat = 0.0, HeightM = 0.0;
		Vec3 UeLocation{};  Vec3 Rotation{};       // cm; pitch yaw roll deg
		double Fov = 65.0;  double ExposureEv = 0.0;
		bool bDofEnabled = false;  double FocalM = 3.0;  double Fstop = 2.8;
		int Multiplier = 2;  bool bCharacterHidden = false;
	};

	/** "[a, b, c]" with the given decimals (design §2-2: arrays on one line). */
	inline std::string FormatVec3Json(const Vec3& V, int Decimals)
	{
		std::string Out = "[";
		for (std::size_t i = 0; i < 3; ++i)
		{
			if (i > 0)
			{
				Out += ", ";
			}
			Out += GolmokStatsMath::FormatFixed(V[i], Decimals);
		}
		Out += ']';
		return Out;
	}

	/** Exact section 2-2 layout (fixed key order, one key per line, 2-space indent, trailing "\n"). Never fails. */
	inline std::string FormatPhotoMetaJson(const PhotoMeta& M)
	{
		using GolmokStatsMath::FormatFixed;
		using GolmokStatsMath::JsonQuote;
		std::string Out;
		Out += "{\n";
		Out += "  \"version\": " + std::to_string(M.Version) + ",\n";
		Out += "  \"time_utc\": " + JsonQuote(M.TimeUtc) + ",\n";
		Out += "  \"preset\": " + (M.bHasPreset ? JsonQuote(M.Preset) : std::string("null")) + ",\n";
		if (M.bHasZone)
		{
			Out += "  \"zone_id\": " + JsonQuote(M.ZoneId) + ",\n";
			Out += "  \"zone_version\": " + std::to_string(M.ZoneVersion) + ",\n";
		}
		else
		{
			Out += "  \"zone_id\": null,\n";
			Out += "  \"zone_version\": null,\n";
		}
		if (M.bHasGeo)
		{
			Out += "  \"lon\": " + FormatFixed(M.Lon, 7) + ",\n";
			Out += "  \"lat\": " + FormatFixed(M.Lat, 7) + ",\n";
			Out += "  \"height_m\": " + FormatFixed(M.HeightM, 3) + ",\n";
		}
		else
		{
			Out += "  \"lon\": null,\n";
			Out += "  \"lat\": null,\n";
			Out += "  \"height_m\": null,\n";
		}
		Out += "  \"ue_location\": " + FormatVec3Json(M.UeLocation, 2) + ",\n";
		Out += "  \"rotation\": " + FormatVec3Json(M.Rotation, 3) + ",\n";
		Out += "  \"fov\": " + FormatFixed(M.Fov, 1) + ",\n";
		Out += "  \"exposure_ev\": " + FormatFixed(M.ExposureEv, 2) + ",\n";
		Out += "  \"dof\": {\"enabled\": " + std::string(M.bDofEnabled ? "true" : "false") + ", \"focal_m\": "
			   + FormatFixed(M.FocalM, 3) + ", \"fstop\": " + FormatFixed(M.Fstop, 2) + "},\n";
		Out += "  \"multiplier\": " + std::to_string(M.Multiplier) + ",\n";
		Out += "  \"character_hidden\": " + std::string(M.bCharacterHidden ? "true" : "false") + "\n";
		Out += "}\n";
		return Out;
	}
} // namespace GolmokPhotoMath
