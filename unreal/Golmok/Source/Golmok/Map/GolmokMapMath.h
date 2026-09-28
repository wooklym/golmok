#pragma once

// Pure, header-only map math for WP-15 (15a writes it, the 15b Slate map widget uses it): WGS84 bbox <-> texture
// pixel and Web Mercator z16 cell <-> pixel. No Unreal headers: tools/tests/test_ue_travel_math.py compiles it with g++
// and cross-checks it against golmok_tools.zone.index (lonlat_to_tile / tile_bounds) and numpy.
//
// A map texture covers a bbox (west, south, east, north) in degrees with Width x Height pixels, pixel (0, 0) at the
// north-west corner, x to the east, y to the south; pixel centers are at +0.5. Two projections:
//   Linear     equirectangular inside the bbox: y proportional to latitude (a basemap export in EPSG:4326)
//   Mercator   Web Mercator (EPSG:3857): y proportional to asinh(tan(lat)) (XYZ tiles, ortho mosaics from tiles)
// Web Mercator formulas are those of GolmokGeoMath::LonLatToCell / CellBounds (spec §6): same expression order.

#include <cmath>

namespace GolmokMapMath
{
	// Named Pi, not the upper-case spelling: Unreal defines that as a preprocessor macro.
	constexpr double Pi = 3.14159265358979323846;
	constexpr double MaxMercatorLatDeg = 85.0511287798066; // GolmokGeoMath::MaxMercatorLatDeg
	constexpr int CellZoom = 16;

	inline double DegToRad(double Deg) { return Deg * (Pi / 180.0); }
	inline double RadToDeg(double Rad) { return Rad * (180.0 / Pi); }

	struct BBox
	{
		double West = 0.0;
		double South = 0.0;
		double East = 0.0;
		double North = 0.0;
	};

	inline bool IsValid(const BBox& B) { return B.East > B.West && B.North > B.South; }

	inline double ClampLat(double LatDeg)
	{
		return (LatDeg < -MaxMercatorLatDeg) ? -MaxMercatorLatDeg : ((LatDeg > MaxMercatorLatDeg) ? MaxMercatorLatDeg : LatDeg);
	}

	/** Normalized Web Mercator row in [0, 1] (0 = north edge of the world): (1 - asinh(tan(lat)) / pi) / 2. */
	inline double MercatorY(double LatDeg) { return (1.0 - std::asinh(std::tan(DegToRad(ClampLat(LatDeg)))) / Pi) / 2.0; }

	/** Inverse of MercatorY. */
	inline double MercatorLat(double Y) { return RadToDeg(std::atan(std::sinh(Pi * (1.0 - 2.0 * Y)))); }

	/** Normalized Web Mercator column in [0, 1]: (lon + 180) / 360. */
	inline double MercatorX(double LonDeg) { return (LonDeg + 180.0) / 360.0; }

	/** (lon, lat) -> texture pixel (continuous; the pixel index is floor). Returns false outside the bbox (values still set). */
	inline bool LonLatToPixel(const BBox& B, int Width, int Height, bool bMercator, double LonDeg, double LatDeg, double& OutPx, double& OutPy)
	{
		OutPx = 0.0;
		OutPy = 0.0;
		if (!IsValid(B) || Width <= 0 || Height <= 0)
		{
			return false;
		}
		const double U = (LonDeg - B.West) / (B.East - B.West);
		double V = 0.0;
		if (bMercator)
		{
			const double Top = MercatorY(B.North);
			const double Bottom = MercatorY(B.South);
			V = (MercatorY(LatDeg) - Top) / (Bottom - Top);
		}
		else
		{
			V = (B.North - LatDeg) / (B.North - B.South);
		}
		OutPx = U * static_cast<double>(Width);
		OutPy = V * static_cast<double>(Height);
		return U >= 0.0 && U <= 1.0 && V >= 0.0 && V <= 1.0;
	}

	/** Texture pixel (continuous) -> (lon, lat). Inverse of LonLatToPixel. */
	inline bool PixelToLonLat(const BBox& B, int Width, int Height, bool bMercator, double Px, double Py, double& OutLonDeg, double& OutLatDeg)
	{
		OutLonDeg = 0.0;
		OutLatDeg = 0.0;
		if (!IsValid(B) || Width <= 0 || Height <= 0)
		{
			return false;
		}
		const double U = Px / static_cast<double>(Width);
		const double V = Py / static_cast<double>(Height);
		OutLonDeg = B.West + U * (B.East - B.West);
		if (bMercator)
		{
			const double Top = MercatorY(B.North);
			const double Bottom = MercatorY(B.South);
			OutLatDeg = MercatorLat(Top + V * (Bottom - Top));
		}
		else
		{
			OutLatDeg = B.North - V * (B.North - B.South);
		}
		return true;
	}

	/** XYZ tile of (lon, lat) at Zoom: GolmokGeoMath::LonLatToCell (floor, clamped to [0, 2^z - 1], Zoom 0..30). */
	inline void LonLatToCell(double LonDeg, double LatDeg, int Zoom, int& OutX, int& OutY)
	{
		const int Z = (Zoom < 0) ? 0 : ((Zoom > 30) ? 30 : Zoom);
		const double N = std::ldexp(1.0, Z);
		const double Lat = ClampLat(LatDeg);
		const double X = std::floor((LonDeg + 180.0) / 360.0 * N);
		const double Y = std::floor((1.0 - std::asinh(std::tan(DegToRad(Lat))) / Pi) / 2.0 * N);
		const double Max = N - 1.0;
		OutX = static_cast<int>((X < 0.0) ? 0.0 : ((X > Max) ? Max : X));
		OutY = static_cast<int>((Y < 0.0) ? 0.0 : ((Y > Max) ? Max : Y));
	}

	/** (west, south, east, north) of tile (X, Y) at Zoom: GolmokGeoMath::CellBounds. */
	inline BBox CellBounds(int X, int Y, int Zoom)
	{
		const int Z = (Zoom < 0) ? 0 : ((Zoom > 30) ? 30 : Zoom);
		const double N = std::ldexp(1.0, Z);
		BBox B;
		B.West = static_cast<double>(X) / N * 360.0 - 180.0;
		B.East = static_cast<double>(X + 1) / N * 360.0 - 180.0;
		B.South = MercatorLat(static_cast<double>(Y + 1) / N);
		B.North = MercatorLat(static_cast<double>(Y) / N);
		return B;
	}

	/** Pixel rectangle of tile (X, Y) at Zoom on a texture over B: (x0, y0) north-west, (x1, y1) south-east corner. */
	inline void CellToPixelRect(int X, int Y, int Zoom, const BBox& B, int Width, int Height, bool bMercator, double& OutX0, double& OutY0,
		double& OutX1, double& OutY1)
	{
		const BBox C = CellBounds(X, Y, Zoom);
		LonLatToPixel(B, Width, Height, bMercator, C.West, C.North, OutX0, OutY0);
		LonLatToPixel(B, Width, Height, bMercator, C.East, C.South, OutX1, OutY1);
	}

	/** Tile under a texture pixel (the pixel center) at Zoom. False when the pixel is off the texture. */
	inline bool PixelToCell(const BBox& B, int Width, int Height, bool bMercator, int Px, int Py, int Zoom, int& OutX, int& OutY)
	{
		OutX = 0;
		OutY = 0;
		if (Px < 0 || Py < 0 || Px >= Width || Py >= Height)
		{
			return false;
		}
		double Lon = 0.0, Lat = 0.0;
		if (!PixelToLonLat(B, Width, Height, bMercator, static_cast<double>(Px) + 0.5, static_cast<double>(Py) + 0.5, Lon, Lat))
		{
			return false;
		}
		LonLatToCell(Lon, Lat, Zoom, OutX, OutY);
		return true;
	}

	/** Web Mercator world pixel at Zoom for TileSize px tiles (the global XYZ pixel grid). */
	inline void LonLatToWorldPixel(double LonDeg, double LatDeg, int Zoom, int TileSize, double& OutPx, double& OutPy)
	{
		const int Z = (Zoom < 0) ? 0 : ((Zoom > 30) ? 30 : Zoom);
		const double Size = std::ldexp(static_cast<double>(TileSize), Z);
		OutPx = MercatorX(LonDeg) * Size;
		OutPy = MercatorY(LatDeg) * Size;
	}
} // namespace GolmokMapMath
