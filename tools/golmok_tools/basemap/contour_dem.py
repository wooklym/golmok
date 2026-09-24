"""DEM from digital topographic maps (수치지형도): contour lines + spot heights -> GeoTIFF.

NGII's public DEM is a 90 m grid (D-012). The 1:5,000 수치지형도 carries 5 m contours and spot
heights (표고점), enough for a ~5 m background terrain. Contour vertices are resampled every
`step` m, spot heights are added, the points are interpolated linearly on their Delaunay TIN, cells
outside the points' hull come from an optional coarse DEM, and a light Gaussian blur softens the
flat terraces a TIN leaves between neighbouring contours.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
import shapefile
from pyproj import CRS, Transformer
from rasterio.transform import from_origin
from scipy.interpolate import LinearNDInterpolator
from scipy.ndimage import gaussian_filter

from .buildings import shapefile_crs
from .raster import DemSampler

# Elevation attribute names seen in 수치지형도 exports; override with --contour-field / --spot-field.
HEIGHT_FIELDS = ("등고수치", "표고수치", "수치", "높이", "HEIGHT", "ELEV", "CONT", "Z")


@dataclass
class ElevationPoints:
    xy: np.ndarray  # (n, 2) in the source CRS
    z: np.ndarray  # (n,) orthometric height, m
    kind: np.ndarray  # (n,) 0 contour, 1 spot height


def _height_field(reader: shapefile.Reader, requested: str | None) -> str:
    names = [f[0] for f in reader.fields[1:]]
    if requested:
        if requested not in names:
            raise ValueError(f"field {requested!r} not in {names}")
        return requested
    for cand in HEIGHT_FIELDS:
        if cand in names:
            return cand
    raise ValueError(f"no elevation field among {names}: pass --contour-field/--spot-field")


def _densify(pts: np.ndarray, step: float) -> np.ndarray:
    seg = np.diff(pts, axis=0)
    lengths = np.hypot(seg[:, 0], seg[:, 1])
    out = [pts[:1]]
    for p0, d, length in zip(pts[:-1], seg, lengths, strict=True):
        n = max(1, int(np.ceil(length / step)))
        t = np.arange(1, n + 1)[:, None] / n
        out.append(p0 + d * t)
    return np.concatenate(out)


def read_points(
    paths: list[Path],
    bbox: tuple[float, float, float, float],
    kind: int,
    field: str | None = None,
    step: float = 5.0,
    encoding: str = "cp949",
) -> tuple[ElevationPoints, int]:
    """Points with heights from line (contour) or point (spot height) shapefiles inside bbox.

    Returns the points and the number of features skipped for a missing/implausible height."""
    x0, y0, x1, y1 = bbox
    xy, z, skipped = [], [], 0
    for path in paths:
        with shapefile.Reader(str(path), encoding=encoding) as r:
            fi = [f[0] for f in r.fields[1:]].index(_height_field(r, field))
            for sr in r.iterShapeRecords():
                s = sr.shape
                if not s.points:
                    continue
                b = s.bbox if len(s.points) > 1 else (*s.points[0], *s.points[0])
                if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
                    continue
                try:
                    h = float(sr.record[fi])
                except (TypeError, ValueError):
                    h = float("nan")
                if not np.isfinite(h) or h < -50 or h > 2000:
                    skipped += 1
                    continue
                if kind == 0:
                    parts = list(s.parts) + [len(s.points)]
                    for i in range(len(parts) - 1):
                        line = np.asarray(s.points[parts[i] : parts[i + 1]], np.float64)[:, :2]
                        if len(line) > 1:
                            dense = _densify(line, step)
                            xy.append(dense)
                            z.append(np.full(len(dense), h))
                else:
                    pts = np.asarray(s.points, np.float64)[:, :2]
                    xy.append(pts)
                    z.append(np.full(len(pts), h))
    if not xy:
        return ElevationPoints(np.zeros((0, 2)), np.zeros(0), np.zeros(0, int)), skipped
    xy_all = np.concatenate(xy)
    inside = (xy_all[:, 0] >= x0) & (xy_all[:, 0] <= x1) & (xy_all[:, 1] >= y0) & (xy_all[:, 1] <= y1)
    z_all = np.concatenate(z)
    return ElevationPoints(xy_all[inside], z_all[inside], np.full(int(inside.sum()), kind)), skipped


def _merge(a: ElevationPoints, b: ElevationPoints) -> ElevationPoints:
    kind = np.concatenate([a.kind, b.kind])
    return ElevationPoints(np.vstack([a.xy, b.xy]), np.concatenate([a.z, b.z]), kind)


def interpolate(points: ElevationPoints, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Linear TIN interpolation at grid cell centres (NaN outside the points' convex hull)."""
    # Duplicate positions (touching contour ends, spots on lines) would make the TIN degenerate.
    _, keep = np.unique(np.round(points.xy, 2), axis=0, return_index=True)
    f = LinearNDInterpolator(points.xy[keep], points.z[keep])
    gx, gy = np.meshgrid(xs, ys)
    return f(gx, gy)


def _holdout_rmse(points: ElevationPoints, fraction: float, seed: int = 0) -> tuple[float, float, int]:
    """Leave out a fraction of spot heights, interpolate from the rest, report (rmse, max abs, n)."""
    spots = np.flatnonzero(points.kind == 1)
    if len(spots) < 10:
        return float("nan"), float("nan"), 0
    rng = np.random.default_rng(seed)
    test = rng.choice(spots, size=max(1, int(len(spots) * fraction)), replace=False)
    train = np.setdiff1d(np.arange(len(points.z)), test)
    sub = ElevationPoints(points.xy[train], points.z[train], points.kind[train])
    _, keep = np.unique(np.round(sub.xy, 2), axis=0, return_index=True)
    pred = LinearNDInterpolator(sub.xy[keep], sub.z[keep])(points.xy[test])
    err = pred - points.z[test]
    err = err[np.isfinite(err)]
    if not len(err):
        return float("nan"), float("nan"), 0
    return float(np.sqrt(np.mean(err**2))), float(np.max(np.abs(err))), len(err)


def contour_dem(
    contours: list[Path],
    spots: list[Path],
    center_lat: float,
    center_lon: float,
    half_size: float,
    out: Path,
    res: float = 5.0,
    smooth: float = 1.0,
    fill_dem: list[Path] | None = None,
    contour_field: str | None = None,
    spot_field: str | None = None,
    src_crs: str | None = None,
    encoding: str = "cp949",
    margin: float = 300.0,
) -> dict:
    """Write a square DEM GeoTIFF (+-half_size m around the centre, in the SHPs' CRS) and return stats."""
    first = (contours or spots)[0]
    crs = shapefile_crs(Path(first), src_crs)
    to_crs = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    cx, cy = to_crs.transform(center_lon, center_lat)
    x0 = np.floor((cx - half_size) / res) * res
    y1 = np.ceil((cy + half_size) / res) * res
    n = int(np.ceil(2 * half_size / res))
    xs = x0 + (np.arange(n) + 0.5) * res
    ys = y1 - (np.arange(n) + 0.5) * res
    read_box = (x0 - margin, y1 - n * res - margin, x0 + n * res + margin, y1 + margin)

    pc, skip_c = read_points(contours, read_box, 0, contour_field, res, encoding)
    ps, skip_s = read_points(spots, read_box, 1, spot_field, res, encoding)
    pts = _merge(pc, ps)
    if len(pts.z) < 3:
        raise ValueError("fewer than 3 elevation points in the area")
    grid = interpolate(pts, xs, ys)

    stats = {
        "crs": f"EPSG:{crs.to_epsg()}" if crs.to_epsg() else crs.name,
        "size": n,
        "res": res,
        "contour_points": int(len(pc.z)),
        "spot_heights": int(len(ps.z)),
        "skipped_features": skip_c + skip_s,
        "tin_coverage": float(np.isfinite(grid).mean()),
    }
    rmse, maxerr, n_test = _holdout_rmse(pts, 0.1)
    stats.update(holdout_rmse=rmse, holdout_max=maxerr, holdout_n=n_test)

    gx, gy = np.meshgrid(xs, ys)
    coarse = None
    if fill_dem:
        to_ll = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
        lon, lat = to_ll.transform(gx.ravel(), gy.ravel())
        sampler = DemSampler(fill_dem, np.asarray(lon), np.asarray(lat), margin=500.0)
        coarse = sampler.sample_lonlat(np.asarray(lon), np.asarray(lat)).reshape(grid.shape)
        both = np.isfinite(grid)
        diff = grid[both] - coarse[both]
        stats.update(vs_fill_mean=float(diff.mean()), vs_fill_std=float(diff.std()))
    hole = ~np.isfinite(grid)
    if hole.any():
        if coarse is None:
            raise ValueError("points do not cover the whole area: pass --fill-dem (e.g. the 90 m DEM)")
        grid[hole] = coarse[hole]
    if smooth > 0:
        grid = gaussian_filter(grid, smooth, mode="nearest")
    stats.update(min=float(grid.min()), max=float(grid.max()))

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        out,
        "w",
        driver="GTiff",
        width=n,
        height=n,
        count=1,
        dtype="float32",
        crs=CRS.from_user_input(crs),
        transform=from_origin(x0, y1, res, res),
        compress="deflate",
        predictor=3,
        tiled=True,
    ) as ds:
        ds.write(grid.astype(np.float32), 1)
    return stats
