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
		const double R = L + K * Step;
		return (std::fabs(R) < Step * 1e-6) ? 0.0 : R; // a grid point at zero is +0.0 (json step 0.3333333333 gives -3e-10, printed -0.00)
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

	/**
	 * Keep-height variant of ClampToSphere (D-013 decision 3): P's XY clamped into the ball's horizontal slice at P's own
	 * height (the nearest point of that disk), Z untouched. Returns true when it moved. The caller guarantees
	 * |P.z - Center.z| <= RadiusCm; a height beyond that collapses XY onto the center (the slice is empty).
	 */
	inline bool ClampToSphereXY(const Vec3& Center, double RadiusCm, Vec3& P)
	{
		const double Radius = (RadiusCm > 0.0) ? RadiusCm : 0.0;
		if (Distance3(P, Center) <= Radius)
		{
			return false;
		}
		const double Dz = P[2] - Center[2];
		const double Slice = std::sqrt(PhotoMax(Radius * Radius - Dz * Dz, 0.0));
		const double Dx = P[0] - Center[0];
		const double Dy = P[1] - Center[1];
		const double Dxy = std::sqrt(Dx * Dx + Dy * Dy);
		if (!(Dxy > Slice) || !std::isfinite(Dxy))
		{
			if (std::isfinite(Dxy))
			{
				return false; // outside only through the height (rounding at the slab's edge): nothing to do in the plane
			}
			P[0] = Center[0];
			P[1] = Center[1];
			return true;
		}
		const double Scale = Slice / Dxy;
		P[0] = Center[0] + Dx * Scale;
		P[1] = Center[1] + Dy * Scale;
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

	/** Tolerances of the footprint clamp (cm): accepted distance slack, smallest inset, near-zero lengths. */
	constexpr double FootprintTolCm = 1e-6;
	constexpr double FootprintMinInsetCm = 1e-3;
	/** Sphere / polygon rounds of Constrain (the sphere clamp can undo part of the polygon one near both limits). */
	constexpr int ConstrainMaxRounds = 16;
	/** Bisection steps of the Constrain fallback along Current -> P (2^-20 of a tick's move). */
	constexpr int ConstrainBisections = 20;

	/** Twice the signed area of the ring (> 0 counter-clockwise in X-right / Y-up axes). */
	inline double RingArea2(const double* Xs, const double* Ys, std::size_t N)
	{
		double A = 0.0;
		for (std::size_t j = 0; j < N; ++j)
		{
			const std::size_t k = (j + 1 < N) ? j + 1 : 0;
			A += Xs[j] * Ys[k] - Xs[k] * Ys[j];
		}
		return A;
	}

	/** Distance from (X, Y) to the ring boundary, positive inside (PointInPolygon) and negative outside. N < 3 -> 0. */
	inline double SignedBoundaryDistance(const double* Xs, const double* Ys, std::size_t N, double X, double Y)
	{
		if (N < 3 || Xs == nullptr || Ys == nullptr)
		{
			return 0.0;
		}
		double Qx = X;
		double Qy = Y;
		std::size_t Edge = 0;
		const double D = NearestBoundaryPoint(Xs, Ys, N, X, Y, Qx, Qy, Edge);
		return GolmokGeoMath::PointInPolygon(Xs, Ys, N, X, Y) ? D : -D;
	}

	/**
	 * The inset ClampToPolygonXY really uses: max(InsetCm, FootprintMinInsetCm), capped at the anchor's own distance to the
	 * boundary when the anchor is inside (a ring narrower than twice the margin keeps the anchor reachable; the floor keeps
	 * the result strictly inside for the even-odd test). N < 3 -> the floored InsetCm.
	 */
	inline double EffectiveInsetCm(const double* Xs, const double* Ys, std::size_t N, double AnchorX, double AnchorY, double InsetCm)
	{
		double Inset = (InsetCm > FootprintMinInsetCm) ? InsetCm : FootprintMinInsetCm; // also NaN -> the floor
		const double AnchorD = SignedBoundaryDistance(Xs, Ys, N, AnchorX, AnchorY);
		if (AnchorD > 0.0 && AnchorD < Inset)
		{
			Inset = PhotoMax(AnchorD, FootprintMinInsetCm);
		}
		return Inset;
	}

	/** True when (X, Y) is in the eroded ring: inside (PointInPolygon) and at least Inset - FootprintTolCm from the boundary. */
	inline bool InErodedRing(const double* Xs, const double* Ys, std::size_t N, double Inset, double X, double Y)
	{
		if (!std::isfinite(X) || !std::isfinite(Y) || !GolmokGeoMath::PointInPolygon(Xs, Ys, N, X, Y))
		{
			return false;
		}
		double Qx = X;
		double Qy = Y;
		std::size_t Edge = 0;
		return NearestBoundaryPoint(Xs, Ys, N, X, Y, Qx, Qy, Edge) >= Inset - FootprintTolCm;
	}

	/** One piece of the eroded ring's boundary: edge j shifted Inset inward (bLine) or the arc of radius Inset around vertex j. */
	struct FootprintPiece
	{
		bool bLine = false;
		double Ax = 0.0;  // line: start of the shifted edge; arc: the vertex
		double Ay = 0.0;
		double Ux = 0.0;  // line: unit direction
		double Uy = 0.0;
		double Nx = 0.0;  // line: unit inward normal
		double Ny = 0.0;
		double Len = 0.0; // line: edge length
	};

	/** Piece Index (2 j = shifted edge j, 2 j + 1 = arc of vertex j); false for a zero-length edge. Orient = sign of RingArea2. */
	inline bool MakeFootprintPiece(const double* Xs, const double* Ys, std::size_t N, double Orient, double Inset, std::size_t Index, FootprintPiece& Out)
	{
		const std::size_t j = (Index / 2) % N;
		Out = FootprintPiece();
		if (Index % 2 == 1)
		{
			Out.Ax = Xs[j];
			Out.Ay = Ys[j];
			return true;
		}
		const std::size_t k = (j + 1 < N) ? j + 1 : 0;
		const double Ex = Xs[k] - Xs[j];
		const double Ey = Ys[k] - Ys[j];
		const double Len = std::sqrt(Ex * Ex + Ey * Ey);
		if (!(Len > FootprintTolCm))
		{
			return false;
		}
		Out.bLine = true;
		Out.Ux = Ex / Len;
		Out.Uy = Ey / Len;
		Out.Nx = -Out.Uy * Orient;
		Out.Ny = Out.Ux * Orient;
		Out.Ax = Xs[j] + Out.Nx * Inset;
		Out.Ay = Ys[j] + Out.Ny * Inset;
		Out.Len = Len;
		return true;
	}

	/** Nearest point of the piece to (Px, Py) (arcs: the full circle; a point on the vertex itself has none) and its distance. */
	inline bool NearestOnPiece(const FootprintPiece& Piece, double Inset, double Px, double Py, double& OutX, double& OutY, double& OutDist)
	{
		if (Piece.bLine)
		{
			double T = (Px - Piece.Ax) * Piece.Ux + (Py - Piece.Ay) * Piece.Uy;
			T = (T < 0.0) ? 0.0 : ((T > Piece.Len) ? Piece.Len : T);
			OutX = Piece.Ax + Piece.Ux * T;
			OutY = Piece.Ay + Piece.Uy * T;
			OutDist = std::sqrt((Px - OutX) * (Px - OutX) + (Py - OutY) * (Py - OutY));
			return true;
		}
		const double Vx = Px - Piece.Ax;
		const double Vy = Py - Piece.Ay;
		const double Vl = std::sqrt(Vx * Vx + Vy * Vy);
		OutDist = std::fabs(Vl - Inset);
		if (!(Vl > FootprintTolCm))
		{
			return false;
		}
		OutX = Piece.Ax + Vx / Vl * Inset;
		OutY = Piece.Ay + Vy / Vl * Inset;
		return true;
	}

	/** Up to two intersection points of two pieces (lines as infinite lines, arcs as full circles); returns the count. */
	inline int IntersectPieces(const FootprintPiece& A, const FootprintPiece& B, double Inset, double OutX[2], double OutY[2])
	{
		if (A.bLine && B.bLine)
		{
			// nA . X = nA . A0, nB . X = nB . B0
			const double Ca = A.Nx * A.Ax + A.Ny * A.Ay;
			const double Cb = B.Nx * B.Ax + B.Ny * B.Ay;
			const double Det = A.Nx * B.Ny - A.Ny * B.Nx;
			if (!(std::fabs(Det) > 1e-12))
			{
				return 0;
			}
			OutX[0] = (Ca * B.Ny - Cb * A.Ny) / Det;
			OutY[0] = (A.Nx * Cb - B.Nx * Ca) / Det;
			return 1;
		}
		if (A.bLine != B.bLine)
		{
			const FootprintPiece& L = A.bLine ? A : B;
			const FootprintPiece& C = A.bLine ? B : A;
			// |L0 + t U - V|^2 = Inset^2
			const double Wx = L.Ax - C.Ax;
			const double Wy = L.Ay - C.Ay;
			const double Bh = Wx * L.Ux + Wy * L.Uy;
			const double Disc = Bh * Bh - (Wx * Wx + Wy * Wy - Inset * Inset);
			if (Disc < 0.0)
			{
				return 0;
			}
			const double Root = std::sqrt(Disc);
			OutX[0] = L.Ax + L.Ux * (-Bh - Root);
			OutY[0] = L.Ay + L.Uy * (-Bh - Root);
			OutX[1] = L.Ax + L.Ux * (-Bh + Root);
			OutY[1] = L.Ay + L.Uy * (-Bh + Root);
			return 2;
		}
		// two circles of radius Inset: on the perpendicular bisector, half-chord sqrt(Inset^2 - (d / 2)^2)
		const double Cx = B.Ax - A.Ax;
		const double Cy = B.Ay - A.Ay;
		const double Cd = std::sqrt(Cx * Cx + Cy * Cy);
		if (!(Cd > FootprintTolCm) || Cd > 2.0 * Inset)
		{
			return 0;
		}
		const double H = std::sqrt(PhotoMax(Inset * Inset - 0.25 * Cd * Cd, 0.0));
		const double Mx = A.Ax + 0.5 * Cx;
		const double My = A.Ay + 0.5 * Cy;
		OutX[0] = Mx - Cy / Cd * H;
		OutY[0] = My + Cx / Cd * H;
		OutX[1] = Mx + Cy / Cd * H;
		OutY[1] = My - Cx / Cd * H;
		return 2;
	}

	/**
	 * XY clamp into the eroded ring S = {inside (GolmokGeoMath::PointInPolygon) and boundary distance >= Inset}, Inset =
	 * EffectiveInsetCm(...) (V-09 #58: the old rule let every inside point through, so pushing at the edge saw-toothed
	 * inside the 0..Inset band, and nudged toward the anchor, so it also dragged sideways). A point already in S -> 0,
	 * unchanged. Otherwise the NEAREST point of S (exact, not iterated): the boundary of S is made of the edges shifted Inset
	 * inward (inward from the ring orientation) and arcs of radius Inset around the vertices, so the candidates are the
	 * nearest point on each piece and the pairwise intersections of pieces (the corners of S), plus the anchor (in S by
	 * EffectiveInsetCm); the nearest candidate that is in S wins. Cost: the pieces around the nearest boundary edge are tried
	 * first (pairwise too), which normally gives the answer; the other pieces are only tested against that distance, and
	 * pairs only among pieces closer than it. Pushing into an edge stops exactly Inset inside and keeps the tangential part
	 * (slides); corners, short / duplicate / collinear edges and reflex arcs have fixed points. Returns 1 with the projected
	 * point, or 2 when no candidate is in S (degenerate ring; X, Y unchanged, the caller keeps its previous position).
	 * N < 3 -> 0, unchanged. A non-finite X or Y -> 2, unchanged (PR #29 review A5).
	 */
	inline int ClampToPolygonXY(const double* Xs, const double* Ys, std::size_t N, double AnchorX, double AnchorY, double InsetCm, double& X, double& Y)
	{
		if (N < 3 || Xs == nullptr || Ys == nullptr)
		{
			return 0;
		}
		if (!std::isfinite(X) || !std::isfinite(Y))
		{
			return 2;
		}
		const double Inset = EffectiveInsetCm(Xs, Ys, N, AnchorX, AnchorY, InsetCm);
		const double Px = X;
		const double Py = Y;
		if (InErodedRing(Xs, Ys, N, Inset, Px, Py))
		{
			return 0;
		}
		const double Area2 = RingArea2(Xs, Ys, N);
		if (Area2 == 0.0 || !std::isfinite(Area2))
		{
			return 2;
		}
		const double Orient = (Area2 < 0.0) ? -1.0 : 1.0;
		const std::size_t NumPieces = 2 * N;

		bool bFound = false;
		double BestX = Px;
		double BestY = Py;
		double BestD2 = 0.0;
		auto Try = [&](double Cx, double Cy)
		{
			const double Ox = Cx - Px;
			const double Oy = Cy - Py;
			const double D2 = Ox * Ox + Oy * Oy;
			if ((!bFound || D2 < BestD2) && InErodedRing(Xs, Ys, N, Inset, Cx, Cy))
			{
				bFound = true;
				BestX = Cx;
				BestY = Cy;
				BestD2 = D2;
			}
		};
		auto TryPair = [&](const FootprintPiece& A, const FootprintPiece& B)
		{
			double Ix[2] = {0.0, 0.0};
			double Iy[2] = {0.0, 0.0};
			const int Count = IntersectPieces(A, B, Inset, Ix, Iy);
			for (int c = 0; c < Count; ++c)
			{
				Try(Ix[c], Iy[c]);
			}
		};

		// 1. local seed: the pieces of the nearest boundary edge and its neighbours (edges e-2..e+2, their vertices), pairwise.
		{
			double Qx = Px;
			double Qy = Py;
			std::size_t Edge = 0;
			NearestBoundaryPoint(Xs, Ys, N, Px, Py, Qx, Qy, Edge);
			constexpr std::size_t LocalCount = 11; // pieces 2(e-2) .. 2(e+2)+2: 6 edges (e-2..e+3), 5 vertex arcs (e-2..e+2)
			FootprintPiece Local[LocalCount];
			bool bLocal[LocalCount] = {};
			const std::size_t First = (2 * Edge + NumPieces * 2 - 4) % NumPieces;
			for (std::size_t i = 0; i < LocalCount && i < NumPieces; ++i)
			{
				bLocal[i] = MakeFootprintPiece(Xs, Ys, N, Orient, Inset, (First + i) % NumPieces, Local[i]);
				double Cx = 0.0;
				double Cy = 0.0;
				double Dist = 0.0;
				if (bLocal[i] && NearestOnPiece(Local[i], Inset, Px, Py, Cx, Cy, Dist))
				{
					Try(Cx, Cy);
				}
			}
			for (std::size_t a = 0; a < LocalCount && a < NumPieces; ++a)
			{
				for (std::size_t b = a + 1; b < LocalCount && b < NumPieces; ++b)
				{
					if (bLocal[a] && bLocal[b])
					{
						TryPair(Local[a], Local[b]);
					}
				}
			}
		}
		// 2. every piece's own nearest point, and the anchor (both only tested when nearer than the best so far).
		for (std::size_t i = 0; i < NumPieces; ++i)
		{
			FootprintPiece Piece;
			double Cx = 0.0;
			double Cy = 0.0;
			double Dist = 0.0;
			if (MakeFootprintPiece(Xs, Ys, N, Orient, Inset, i, Piece) && NearestOnPiece(Piece, Inset, Px, Py, Cx, Cy, Dist))
			{
				Try(Cx, Cy);
			}
		}
		Try(AnchorX, AnchorY);
		if (!bFound)
		{
			return 2;
		}
		// 3. corners of S among the pieces closer than the best candidate (a nearer point of S lies on such pieces only).
		std::vector<FootprintPiece> Near;
		const double Bound = std::sqrt(BestD2) + FootprintTolCm;
		for (std::size_t i = 0; i < NumPieces; ++i)
		{
			FootprintPiece Piece;
			double Cx = 0.0;
			double Cy = 0.0;
			double Dist = 0.0;
			if (MakeFootprintPiece(Xs, Ys, N, Orient, Inset, i, Piece))
			{
				NearestOnPiece(Piece, Inset, Px, Py, Cx, Cy, Dist);
				if (Dist <= Bound)
				{
					Near.push_back(Piece);
				}
			}
		}
		for (std::size_t a = 0; a < Near.size(); ++a)
		{
			for (std::size_t b = a + 1; b < Near.size(); ++b)
			{
				TryPair(Near[a], Near[b]);
			}
		}
		X = BestX;
		Y = BestY;
		return 1;
	}

	struct Constraint
	{
		Vec3 Anchor{};                     // character capsule center
		double RadiusCm = 300.0;           // MaxDistanceM * 100
		double InsetCm = 20.0;             // FootprintMarginM * 100
		const double* Xs = nullptr;        // footprint ring (level UE cm), N = 0 -> no polygon
		const double* Ys = nullptr;
		std::size_t N = 0;
		bool bHasCurrent = false;          // Current = the pawn's position before this move (MoveConstrained sets it)
		Vec3 Current{};
		bool bKeepHeight = false;          // no vertical input (D-013 decision 3): the constraint never changes Z, see Constrain
	};

	/**
	 * Inset for this move: C.InsetCm capped at the anchor's boundary distance (EffectiveInsetCm), lowered to the current position's boundary distance when the pawn already stands
	 * inside the ring closer than that (it can start there: the spring-arm camera). Such a pawn is never pushed inward by a
	 * move (no jump); it can only move to points at least as far from the boundary, so the margin ratchets back up to
	 * C.InsetCm as it moves inward. A current position outside the ring does not lower it (the first move snaps inside).
	 */
	inline double MoveInsetCm(const Constraint& C)
	{
		double Inset = C.InsetCm;
		if (C.bHasCurrent && C.N >= 3 && C.Xs != nullptr && C.Ys != nullptr)
		{
			// PR #29 review A1: compare against the anchor-capped inset, or an anchor closer to the boundary than InsetCm
			// lowers Inset to CurrentD on every tick and the 1e-6 cm ring tolerance ratchets the margin away at the junction.
			Inset = EffectiveInsetCm(C.Xs, C.Ys, C.N, C.Anchor[0], C.Anchor[1], Inset);
			const double CurrentD = SignedBoundaryDistance(C.Xs, C.Ys, C.N, C.Current[0], C.Current[1]);
			if (CurrentD > 0.0 && CurrentD < Inset - FootprintTolCm)
			{
				Inset = CurrentD;
			}
		}
		return Inset;
	}

	/** Inside the sphere (1e-12 relative + 1e-9 cm slack) and, with a polygon, a fixed point of ClampToPolygonXY at Inset. */
	inline bool MeetsConstraint(const Constraint& C, double Inset, const Vec3& P)
	{
		const double Radius = (C.RadiusCm > 0.0) ? C.RadiusCm : 0.0;
		if (!(Distance3(P, C.Anchor) <= Radius * (1.0 + 1e-12) + 1e-9))
		{
			return false;
		}
		if (C.N >= 3 && C.Xs != nullptr && C.Ys != nullptr)
		{
			double Cx = P[0];
			double Cy = P[1];
			return ClampToPolygonXY(C.Xs, C.Ys, C.N, C.Anchor[0], C.Anchor[1], Inset, Cx, Cy) == 0;
		}
		return true;
	}

	/**
	 * Sphere -> polygon, repeated up to ConstrainMaxRounds times while the polygon clamp leaves the sphere, then re-checked:
	 * the result must be inside the sphere AND (N == 0 or in the eroded ring of ClampToPolygonXY with MoveInsetCm(C)).
	 * Where the two limits meet at a shallow angle the rounds creep instead of converging: then, when C.Current is set and
	 * valid, a valid point of the segment Current -> last round's point found by bisection (the valid prefix is assumed
	 * contiguous; on a non-convex S it need not be the farthest) is taken, so the pawn keeps
	 * sliding into the junction instead of freezing. Returns 0 = accepted unchanged (Out written), 1 = accepted after a
	 * sphere clamp, 2 = after a polygon clamp, 3 = both, -1 = rejected (Out untouched; the pawn keeps its previous
	 * position). The pawn calls this before each of its (at most two) sweeps.
	 * C.bKeepHeight (D-013 decision 3, no Q/E input): every clamp works in the horizontal plane at the desired height, so
	 * the result's Z is Desired.z (or, when that height lies outside the sphere's slab, C.Current.z: the move goes on in
	 * the plane it starts in) - a push along the sphere or into the sphere/footprint junction slides or stops in that
	 * plane instead of following the sphere toward the anchor's height. The bisection fallback keeps Z between
	 * C.Current.z and that height.
	 */
	inline int Constrain(const Constraint& C, const Vec3& Desired, Vec3& Out)
	{
		Vec3 P = Desired;
		int Code = 0;
		const bool bPolygon = (C.N >= 3) && C.Xs != nullptr && C.Ys != nullptr;
		const double Inset = MoveInsetCm(C);
		const double Radius = (C.RadiusCm > 0.0) ? C.RadiusCm : 0.0;
		// Same slack as the sphere test in MeetsConstraint: a pawn left on the sphere's pole by a vertical move stays movable.
		const double SlabCm = Radius * (1.0 + 1e-12) + 1e-9;
		if (C.bKeepHeight && !(std::fabs(P[2] - C.Anchor[2]) <= SlabCm))
		{
			// No point of the sphere at the desired height: stay in the current plane (never a height the sphere clamp picked).
			if (!C.bHasCurrent || !(std::fabs(C.Current[2] - C.Anchor[2]) <= SlabCm))
			{
				return -1;
			}
			P[2] = C.Current[2];
			Code |= 1;
		}
		for (int Round = 0; Round < ConstrainMaxRounds; ++Round)
		{
			if (C.bKeepHeight ? ClampToSphereXY(C.Anchor, C.RadiusCm, P) : ClampToSphere(C.Anchor, C.RadiusCm, P))
			{
				Code |= 1;
			}
			if (bPolygon)
			{
				const int PolyCode = ClampToPolygonXY(C.Xs, C.Ys, C.N, C.Anchor[0], C.Anchor[1], Inset, P[0], P[1]);
				if (PolyCode == 2)
				{
					return -1;
				}
				if (PolyCode == 1)
				{
					Code |= 2;
				}
			}
			if (Distance3(P, C.Anchor) <= Radius * (1.0 + 1e-12) + 1e-9)
			{
				break;
			}
		}
		// Re-check both (design §6-2 ③).
		if (MeetsConstraint(C, Inset, P))
		{
			Out = P;
			return Code;
		}
		if (!C.bHasCurrent || !MeetsConstraint(C, Inset, C.Current))
		{
			return -1;
		}
		double Lo = 0.0; // Current: valid
		double Hi = 1.0; // P: not valid
		for (int i = 0; i < ConstrainBisections; ++i)
		{
			const double Mid = 0.5 * (Lo + Hi);
			const Vec3 M{C.Current[0] + (P[0] - C.Current[0]) * Mid, C.Current[1] + (P[1] - C.Current[1]) * Mid, C.Current[2] + (P[2] - C.Current[2]) * Mid};
			if (MeetsConstraint(C, Inset, M))
			{
				Lo = Mid;
			}
			else
			{
				Hi = Mid;
			}
		}
		if (!(Lo > 0.0))
		{
			return -1;
		}
		Out = {C.Current[0] + (P[0] - C.Current[0]) * Lo, C.Current[1] + (P[1] - C.Current[1]) * Lo, C.Current[2] + (P[2] - C.Current[2]) * Lo};
		return Code;
	}

	// ---- keep-height slide (MoveConstrained without Q/E: D-013 decision 3, V-09c runbook section 12 #68) ----------
	/**
	 * Direction of the slide leg after a blocked keep-height sweep. Slide = the rest of the blocked move already projected
	 * on the hit plane (the pawn's VectorPlaneProject), HitNormal = the sweep's unit hit normal. Out = Slide flattened to
	 * the horizontal plane (Out z = 0); then, only when the normal's horizontal part is LONGER than MinHorizontal (strict
	 * >), the part of the flattened slide that goes into the face along the face's unit outward horizontal normal is
	 * removed (one-sided: a part going away from the face stays). For a horizontal move R into the face that gives
	 * R - (R . u) u with u that outward normal: the move follows the obstacle's horizontal cross-section (Out . HitNormal
	 * = 0, |Out| <= |R|). The flattened slide alone has (R . HitNormal) Nz^2 < 0 along HitNormal on any face with
	 * Nz != 0, so the next sweep stopped at once on a ramp or a step edge. A vertical wall gives the flattened projection
	 * back (its into part is already 0). A normal whose horizontal part is MinHorizontal or shorter (a near-level hit), a
	 * zero normal and a NaN normal keep the flattened slide only. Returns true when the into part was removed, false when
	 * Out is the flattened slide. Out may alias Slide or HitNormal.
	 */
	inline bool KeepHeightSlide(const Vec3& Slide, const Vec3& HitNormal, double MinHorizontal, Vec3& Out)
	{
		double Sx = Slide[0];
		double Sy = Slide[1];
		bool bIntoRemoved = false;
		const double FaceOutLen2 = HitNormal[0] * HitNormal[0] + HitNormal[1] * HitNormal[1];
		if (FaceOutLen2 > MinHorizontal * MinHorizontal) // NaN -> false: flattened slide only
		{
			const double Scale = 1.0 / std::sqrt(FaceOutLen2);
			const double FaceOutX = HitNormal[0] * Scale; // unit outward horizontal normal of the hit face
			const double FaceOutY = HitNormal[1] * Scale;
			const double OutCm = Sx * FaceOutX + Sy * FaceOutY; // along FaceOut: negative = into the face
			if (OutCm < 0.0)
			{
				Sx -= FaceOutX * OutCm;
				Sy -= FaceOutY * OutCm;
				bIntoRemoved = true;
			}
		}
		Out = {Sx, Sy, 0.0};
		return bIntoRemoved;
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
