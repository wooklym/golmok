#pragma once

// Pure, header-only geodesy for Golmok. No Unreal headers on purpose: tools/tests/test_ue_geo_math.py compiles this file
// with g++ and cross-checks it against tools/golmok_tools/zone/transform.py and docs/spec/zone-manifest.md §4, so the
// coordinate math is verified in cloud CI without an engine. Geo/GolmokGeo.h wraps it with FVector3d / FMatrix44d.
//
// Conventions (docs/spec/zone-manifest.md §1, §5):
//   ENU        x=east, y=north, z=up, meters, right-handed. zone-local = ENU at the zone origin (turned by yaw_deg).
//   ECEF       EPSG:4978, meters.
//   Mat4       4x4 row-major: M[r*4+c]. Points are columns: p' = M * [x y z 1]^T. transform = zone-local -> ECEF.
//   UE         X=east, Y=south, Z=up, centimeters (left-handed): UE = S * ENU, S = diag(100, -100, 100).
//   yaw_deg    counter-clockwise from +x (east) about +z, seen from above. UE Yaw = -yaw_deg.
// All values are double.

#include <array>
#include <cmath>
#include <cstddef>

namespace GolmokGeoMath
{
	using Vec3 = std::array<double, 3>;
	using Mat4 = std::array<double, 16>;

	// WGS84 (NIMA TR8350.2). Same constants as golmok_tools.zone.transform.
	constexpr double WGS84_A = 6378137.0;
	constexpr double WGS84_F = 1.0 / 298.257223563;
	constexpr double WGS84_E2 = WGS84_F * (2.0 - WGS84_F);
	constexpr double WGS84_B = WGS84_A * (1.0 - WGS84_F);
	// Named Pi, not the upper-case spelling: Unreal defines that as a preprocessor macro in UnrealMathUtility.h.
	constexpr double Pi = 3.14159265358979323846;
	constexpr double ENU_TO_UE_SCALE = 100.0; // m -> cm

	inline double DegToRad(double Deg) { return Deg * (Pi / 180.0); }
	inline double RadToDeg(double Rad) { return Rad * (180.0 / Pi); }

	inline Mat4 Identity()
	{
		return Mat4{1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
	}

	inline double At(const Mat4& M, std::size_t Row, std::size_t Col) { return M[Row * 4 + Col]; }
	inline void Set(Mat4& M, std::size_t Row, std::size_t Col, double V) { M[Row * 4 + Col] = V; }

	inline Mat4 Multiply(const Mat4& A, const Mat4& B)
	{
		Mat4 R{};
		for (std::size_t i = 0; i < 4; ++i)
		{
			for (std::size_t j = 0; j < 4; ++j)
			{
				double S = 0.0;
				for (std::size_t k = 0; k < 4; ++k)
				{
					S += At(A, i, k) * At(B, k, j);
				}
				Set(R, i, j, S);
			}
		}
		return R;
	}

	/** Transform a point (applies rotation and translation). */
	inline Vec3 ApplyPoint(const Mat4& M, const Vec3& P)
	{
		return Vec3{
			At(M, 0, 0) * P[0] + At(M, 0, 1) * P[1] + At(M, 0, 2) * P[2] + At(M, 0, 3),
			At(M, 1, 0) * P[0] + At(M, 1, 1) * P[1] + At(M, 1, 2) * P[2] + At(M, 1, 3),
			At(M, 2, 0) * P[0] + At(M, 2, 1) * P[1] + At(M, 2, 2) * P[2] + At(M, 2, 3)};
	}

	/** Transform a direction (rotation only). */
	inline Vec3 ApplyVector(const Mat4& M, const Vec3& V)
	{
		return Vec3{
			At(M, 0, 0) * V[0] + At(M, 0, 1) * V[1] + At(M, 0, 2) * V[2],
			At(M, 1, 0) * V[0] + At(M, 1, 1) * V[1] + At(M, 1, 2) * V[2],
			At(M, 2, 0) * V[0] + At(M, 2, 1) * V[1] + At(M, 2, 2) * V[2]};
	}

	/** Inverse of a rigid transform (R^T, -R^T t). Only valid when the 3x3 part is orthonormal. */
	inline Mat4 RigidInverse(const Mat4& M)
	{
		Mat4 R = Identity();
		for (std::size_t i = 0; i < 3; ++i)
		{
			for (std::size_t j = 0; j < 3; ++j)
			{
				Set(R, i, j, At(M, j, i));
			}
		}
		for (std::size_t i = 0; i < 3; ++i)
		{
			double T = 0.0;
			for (std::size_t j = 0; j < 3; ++j)
			{
				T -= At(R, i, j) * At(M, j, 3);
			}
			Set(R, i, 3, T);
		}
		return R;
	}

	inline Vec3 Translation(const Mat4& M) { return Vec3{At(M, 0, 3), At(M, 1, 3), At(M, 2, 3)}; }

	/** WGS84 geodetic (deg, deg, ellipsoidal m) -> ECEF (m). Closed form, spec §4 table A. */
	inline Vec3 GeodeticToEcef(double LatDeg, double LonDeg, double H)
	{
		const double Phi = DegToRad(LatDeg);
		const double Lam = DegToRad(LonDeg);
		const double SinPhi = std::sin(Phi);
		const double CosPhi = std::cos(Phi);
		const double N = WGS84_A / std::sqrt(1.0 - WGS84_E2 * SinPhi * SinPhi);
		return Vec3{
			(N + H) * CosPhi * std::cos(Lam), (N + H) * CosPhi * std::sin(Lam), (N * (1.0 - WGS84_E2) + H) * SinPhi};
	}

	/**
	 * ECEF (m) -> WGS84 geodetic. Iterative (Bowring-style fixed point), converges below 1e-9 m in a few steps for any
	 * point outside the Earth's core; 12 iterations are plenty. Poles and the axis are handled explicitly.
	 */
	inline void EcefToGeodetic(const Vec3& Ecef, double& LatDeg, double& LonDeg, double& H)
	{
		const double X = Ecef[0];
		const double Y = Ecef[1];
		const double Z = Ecef[2];
		const double P = std::sqrt(X * X + Y * Y);
		LonDeg = RadToDeg(std::atan2(Y, X));
		if (P < 1e-9)
		{
			LatDeg = (Z >= 0.0) ? 90.0 : -90.0;
			H = std::fabs(Z) - WGS84_B;
			return;
		}
		double Lat = std::atan2(Z, P * (1.0 - WGS84_E2));
		double Height = 0.0;
		for (int i = 0; i < 12; ++i)
		{
			const double SinLat = std::sin(Lat);
			const double N = WGS84_A / std::sqrt(1.0 - WGS84_E2 * SinLat * SinLat);
			const double CosLat = std::cos(Lat);
			Height = (std::fabs(CosLat) > 1e-12) ? (P / CosLat - N) : (std::fabs(Z) / std::fabs(SinLat) - N * (1.0 - WGS84_E2));
			Lat = std::atan2(Z, P * (1.0 - WGS84_E2 * N / (N + Height)));
		}
		LatDeg = RadToDeg(Lat);
		H = Height;
	}

	/** 4x4: ENU at (lat, lon, h) -> ECEF. Rotation columns are the east, north, up unit vectors (spec §4 B). */
	inline Mat4 EnuFrame(double LatDeg, double LonDeg, double H)
	{
		const double Phi = DegToRad(LatDeg);
		const double Lam = DegToRad(LonDeg);
		const double SinPhi = std::sin(Phi);
		const double CosPhi = std::cos(Phi);
		const double SinLam = std::sin(Lam);
		const double CosLam = std::cos(Lam);
		const Vec3 East{-SinLam, CosLam, 0.0};
		const Vec3 North{-SinPhi * CosLam, -SinPhi * SinLam, CosPhi};
		const Vec3 Up{CosPhi * CosLam, CosPhi * SinLam, SinPhi};
		const Vec3 T = GeodeticToEcef(LatDeg, LonDeg, H);
		Mat4 M = Identity();
		for (std::size_t r = 0; r < 3; ++r)
		{
			Set(M, r, 0, East[r]);
			Set(M, r, 1, North[r]);
			Set(M, r, 2, Up[r]);
			Set(M, r, 3, T[r]);
		}
		return M;
	}

	/** Rotation about +z by yaw_deg (counter-clockwise from +x toward +y). */
	inline Mat4 RotZ(double YawDeg)
	{
		const double C = std::cos(DegToRad(YawDeg));
		const double S = std::sin(DegToRad(YawDeg));
		Mat4 M = Identity();
		Set(M, 0, 0, C);
		Set(M, 0, 1, -S);
		Set(M, 1, 0, S);
		Set(M, 1, 1, C);
		return M;
	}

	/** zone-local -> ECEF for a zone whose axes are the ENU axes at (lat, lon, h) turned by yaw_deg: EnuFrame * RotZ. */
	inline Mat4 ZoneTransform(double LatDeg, double LonDeg, double H, double YawDeg)
	{
		return Multiply(EnuFrame(LatDeg, LonDeg, H), RotZ(YawDeg));
	}

	/** zone-local (m) -> area ENU (m) at the area origin: inv(EnuFrame(area)) * ZoneToEcef. Full 4x4, never a pure yaw. */
	inline Mat4 ZoneLocalToAreaEnu(const Mat4& ZoneToEcef, double AreaLatDeg, double AreaLonDeg, double AreaH)
	{
		return Multiply(RigidInverse(EnuFrame(AreaLatDeg, AreaLonDeg, AreaH)), ZoneToEcef);
	}

	/** ENU point (m) -> UE (cm): X=east, Y=south, Z=up. */
	inline Vec3 EnuToUE(const Vec3& Enu)
	{
		return Vec3{Enu[0] * ENU_TO_UE_SCALE, -Enu[1] * ENU_TO_UE_SCALE, Enu[2] * ENU_TO_UE_SCALE};
	}

	/** UE point (cm) -> ENU (m). */
	inline Vec3 UEToEnu(const Vec3& UEPos)
	{
		return Vec3{UEPos[0] / ENU_TO_UE_SCALE, -UEPos[1] / ENU_TO_UE_SCALE, UEPos[2] / ENU_TO_UE_SCALE};
	}

	/** ENU direction -> UE direction (unit-preserving): D = diag(1, -1, 1). */
	inline Vec3 EnuDirToUE(const Vec3& Enu) { return Vec3{Enu[0], -Enu[1], Enu[2]}; }

	/**
	 * Zone root actor matrix in UE space (cm) from zone-local -> area ENU (m): S * M * S^-1.
	 * Rotation part = D R D (det +1), translation = S t. Chunk meshes already carry UE axes/cm vertices, so the actor
	 * gets exactly this matrix and chunk components use identity relative transforms (spec §5).
	 */
	inline Mat4 UEActorMatrix(const Mat4& ZoneToArea)
	{
		Mat4 S = Identity();
		Set(S, 0, 0, ENU_TO_UE_SCALE);
		Set(S, 1, 1, -ENU_TO_UE_SCALE);
		Set(S, 2, 2, ENU_TO_UE_SCALE);
		Mat4 SInv = Identity();
		Set(SInv, 0, 0, 1.0 / ENU_TO_UE_SCALE);
		Set(SInv, 1, 1, -1.0 / ENU_TO_UE_SCALE);
		Set(SInv, 2, 2, 1.0 / ENU_TO_UE_SCALE);
		return Multiply(Multiply(S, ZoneToArea), SInv);
	}

	/** max |R^T R - I| of the 3x3 part, and det(R); the last row is checked separately by the caller. */
	inline double RigidityError(const Mat4& M, double& OutDet)
	{
		double MaxErr = 0.0;
		for (std::size_t i = 0; i < 3; ++i)
		{
			for (std::size_t j = 0; j < 3; ++j)
			{
				double S = 0.0;
				for (std::size_t k = 0; k < 3; ++k)
				{
					S += At(M, k, i) * At(M, k, j);
				}
				const double E = std::fabs(S - ((i == j) ? 1.0 : 0.0));
				MaxErr = (E > MaxErr) ? E : MaxErr;
			}
		}
		OutDet = At(M, 0, 0) * (At(M, 1, 1) * At(M, 2, 2) - At(M, 1, 2) * At(M, 2, 1))
			   - At(M, 0, 1) * (At(M, 1, 0) * At(M, 2, 2) - At(M, 1, 2) * At(M, 2, 0))
			   + At(M, 0, 2) * (At(M, 1, 0) * At(M, 2, 1) - At(M, 1, 1) * At(M, 2, 0));
		return MaxErr;
	}

	/** Heading of the zone's +x axis in UE space (degrees, UE convention: clockwise from +X seen from above) = -yaw_deg. */
	inline double UEYawDegFromZoneToArea(const Mat4& ZoneToArea)
	{
		// zone +x expressed in area ENU
		const double Ex = At(ZoneToArea, 0, 0);
		const double Ny = At(ZoneToArea, 1, 0);
		return -RadToDeg(std::atan2(Ny, Ex));
	}

	/**
	 * Even-odd point-in-polygon on a closed or open ring given as parallel arrays (N >= 3). Points on an edge count as
	 * inside on one side only, which is fine for basemap hiding.
	 */
	inline bool PointInPolygon(const double* Xs, const double* Ys, std::size_t N, double X, double Y)
	{
		bool Inside = false;
		if (N < 3)
		{
			return false;
		}
		for (std::size_t i = 0, j = N - 1; i < N; j = i++)
		{
			const bool Crosses = (Ys[i] > Y) != (Ys[j] > Y);
			if (Crosses)
			{
				const double XAtY = (Xs[j] - Xs[i]) * (Y - Ys[i]) / (Ys[j] - Ys[i]) + Xs[i];
				if (X < XAtY)
				{
					Inside = !Inside;
				}
			}
		}
		return Inside;
	}

	/** Distance from a point to a segment (a-b), 2D. */
	inline double DistanceToSegment(double Ax, double Ay, double Bx, double By, double X, double Y)
	{
		const double Dx = Bx - Ax;
		const double Dy = By - Ay;
		const double L2 = Dx * Dx + Dy * Dy;
		double T = (L2 > 0.0) ? ((X - Ax) * Dx + (Y - Ay) * Dy) / L2 : 0.0;
		T = (T < 0.0) ? 0.0 : ((T > 1.0) ? 1.0 : T);
		const double Px = Ax + T * Dx - X;
		const double Py = Ay + T * Dy - Y;
		return std::sqrt(Px * Px + Py * Py);
	}

	/** 0 when the point is inside the polygon, else the distance to its nearest edge (same units as the inputs). */
	inline double DistanceToPolygon(const double* Xs, const double* Ys, std::size_t N, double X, double Y)
	{
		if (N < 3)
		{
			return 1e300;
		}
		if (PointInPolygon(Xs, Ys, N, X, Y))
		{
			return 0.0;
		}
		double Best = 1e300;
		for (std::size_t i = 0, j = N - 1; i < N; j = i++)
		{
			const double D = DistanceToSegment(Xs[j], Ys[j], Xs[i], Ys[i], X, Y);
			Best = (D < Best) ? D : Best;
		}
		return Best;
	}

	/** True when segments p1-p2 and p3-p4 intersect (including touching). */
	inline bool SegmentsIntersect(double X1, double Y1, double X2, double Y2, double X3, double Y3, double X4, double Y4)
	{
		auto Orient = [](double Ax, double Ay, double Bx, double By, double Cx, double Cy) {
			const double V = (Bx - Ax) * (Cy - Ay) - (By - Ay) * (Cx - Ax);
			return (V > 1e-12) ? 1 : ((V < -1e-12) ? -1 : 0);
		};
		auto OnSeg = [](double Ax, double Ay, double Bx, double By, double Px, double Py) {
			return Px <= ((Ax > Bx) ? Ax : Bx) + 1e-12 && Px + 1e-12 >= ((Ax < Bx) ? Ax : Bx) && Py <= ((Ay > By) ? Ay : By) + 1e-12
				   && Py + 1e-12 >= ((Ay < By) ? Ay : By);
		};
		const int O1 = Orient(X1, Y1, X2, Y2, X3, Y3);
		const int O2 = Orient(X1, Y1, X2, Y2, X4, Y4);
		const int O3 = Orient(X3, Y3, X4, Y4, X1, Y1);
		const int O4 = Orient(X3, Y3, X4, Y4, X2, Y2);
		if (O1 != O2 && O3 != O4)
		{
			return true;
		}
		if (O1 == 0 && OnSeg(X1, Y1, X2, Y2, X3, Y3)) return true;
		if (O2 == 0 && OnSeg(X1, Y1, X2, Y2, X4, Y4)) return true;
		if (O3 == 0 && OnSeg(X3, Y3, X4, Y4, X1, Y1)) return true;
		if (O4 == 0 && OnSeg(X3, Y3, X4, Y4, X2, Y2)) return true;
		return false;
	}

	/** True when two simple polygons overlap (a vertex of one inside the other, or any two edges intersect). */
	inline bool PolygonsOverlap(const double* AXs, const double* AYs, std::size_t NA, const double* BXs, const double* BYs, std::size_t NB)
	{
		if (NA < 3 || NB < 3)
		{
			return false;
		}
		if (PointInPolygon(BXs, BYs, NB, AXs[0], AYs[0]) || PointInPolygon(AXs, AYs, NA, BXs[0], BYs[0]))
		{
			return true;
		}
		for (std::size_t i = 0, j = NA - 1; i < NA; j = i++)
		{
			for (std::size_t k = 0, l = NB - 1; k < NB; l = k++)
			{
				if (SegmentsIntersect(AXs[j], AYs[j], AXs[i], AYs[i], BXs[l], BYs[l], BXs[k], BYs[k]))
				{
					return true;
				}
			}
		}
		return false;
	}

	/**
	 * Blocker plane axes (spec §3.1): height axis = zone +z projected onto the plane (or +y/north when the plane is
	 * horizontal), width axis = height x normal. Inputs and outputs are zone-local ENU unit vectors.
	 */
	inline void BlockerAxes(const Vec3& NormalIn, Vec3& OutWidth, Vec3& OutHeight)
	{
		const double Len = std::sqrt(NormalIn[0] * NormalIn[0] + NormalIn[1] * NormalIn[1] + NormalIn[2] * NormalIn[2]);
		const Vec3 N = (Len > 0.0) ? Vec3{NormalIn[0] / Len, NormalIn[1] / Len, NormalIn[2] / Len} : Vec3{0.0, -1.0, 0.0};
		// Same rule as golmok_tools.mesh.blockers.plane_axes: project +z; only a (numerically) horizontal plane
		// falls back to +y (north).
		auto Project = [&N](const Vec3& Ref) {
			const double D = Ref[0] * N[0] + Ref[1] * N[1] + Ref[2] * N[2];
			return Vec3{Ref[0] - D * N[0], Ref[1] - D * N[1], Ref[2] - D * N[2]};
		};
		Vec3 Hgt = Project(Vec3{0.0, 0.0, 1.0});
		double HL = std::sqrt(Hgt[0] * Hgt[0] + Hgt[1] * Hgt[1] + Hgt[2] * Hgt[2]);
		if (HL < 1e-6)
		{
			Hgt = Project(Vec3{0.0, 1.0, 0.0});
			HL = std::sqrt(Hgt[0] * Hgt[0] + Hgt[1] * Hgt[1] + Hgt[2] * Hgt[2]);
		}
		Hgt = Vec3{Hgt[0] / HL, Hgt[1] / HL, Hgt[2] / HL};
		OutHeight = Hgt;
		OutWidth = Vec3{Hgt[1] * N[2] - Hgt[2] * N[1], Hgt[2] * N[0] - Hgt[0] * N[2], Hgt[0] * N[1] - Hgt[1] * N[0]};
	}

	// ---------------------------------------------------------------------------------------------------------
	// Zone Index cells (WP-09, spec §6): Web Mercator XYZ tiles, same formulas as golmok_tools.zone.index
	// ---------------------------------------------------------------------------------------------------------

	/** Web Mercator latitude limit (deg). Same literal as golmok_tools.zone.index.MAX_LAT. */
	constexpr double MaxMercatorLatDeg = 85.0511287798066;

	/**
	 * XYZ tile of (lon, lat) at Zoom (spec §6): x = floor((lon+180)/360·2^z), y = floor((1 − asinh(tan φ)/π)/2·2^z).
	 * Same expression order as index.lonlat_to_tile (g++ cross-check). Lat clamped to ±MaxMercatorLatDeg, x/y clamped
	 * to [0, 2^Zoom − 1] (no wrap), Zoom clamped to 0..30 (fits int).
	 */
	inline void LonLatToCell(double LonDeg, double LatDeg, int Zoom, int& OutX, int& OutY)
	{
		const int Z = (Zoom < 0) ? 0 : ((Zoom > 30) ? 30 : Zoom);
		const double N = std::ldexp(1.0, Z);                                   // 2^z exactly
		const double Lat = (LatDeg < -MaxMercatorLatDeg) ? -MaxMercatorLatDeg : ((LatDeg > MaxMercatorLatDeg) ? MaxMercatorLatDeg : LatDeg);
		const double X = std::floor((LonDeg + 180.0) / 360.0 * N);
		const double Y = std::floor((1.0 - std::asinh(std::tan(DegToRad(Lat))) / Pi) / 2.0 * N);
		const double Max = N - 1.0;
		OutX = static_cast<int>((X < 0.0) ? 0.0 : ((X > Max) ? Max : X));
		OutY = static_cast<int>((Y < 0.0) ? 0.0 : ((Y > Max) ? Max : Y));
	}

	/** (west, south, east, north) degrees of tile (X, Y) at Zoom — index.tile_bounds. */
	inline void CellBounds(int X, int Y, int Zoom, double& OutWest, double& OutSouth, double& OutEast, double& OutNorth)
	{
		const int Z = (Zoom < 0) ? 0 : ((Zoom > 30) ? 30 : Zoom);
		const double N = std::ldexp(1.0, Z);
		auto LatOf = [N](double Row) { return RadToDeg(std::atan(std::sinh(Pi * (1.0 - 2.0 * Row / N)))); };
		OutWest = static_cast<double>(X) / N * 360.0 - 180.0;
		OutEast = static_cast<double>(X + 1) / N * 360.0 - 180.0;
		OutSouth = LatOf(static_cast<double>(Y + 1));
		OutNorth = LatOf(static_cast<double>(Y));
	}
} // namespace GolmokGeoMath
