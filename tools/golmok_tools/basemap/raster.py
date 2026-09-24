"""DEM sampling and orthophoto cropping from one or more GeoTIFF sheets (NGII)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import rasterio
from rasterio.merge import merge
from pyproj import CRS, Transformer


def _raster_crs(paths: list[Path], override: str | None = None) -> CRS:
    if override:
        return CRS.from_user_input(override)
    crss = set()
    for p in paths:
        with rasterio.open(p) as ds:
            if ds.crs is None:
                raise ValueError(f"{p} has no CRS: pass --raster-crs (e.g. EPSG:5186)")
            crss.add(ds.crs.to_wkt())
    if len(crss) != 1:
        raise ValueError("all raster sheets must share one CRS")
    return CRS.from_wkt(crss.pop())


def _bounds_in(crs: CRS, lon, lat, margin: float):
    t = Transformer.from_crs(CRS.from_epsg(4326), crs, always_xy=True)
    x, y = t.transform(np.asarray(lon), np.asarray(lat))
    return float(np.min(x) - margin), float(np.min(y) - margin), float(np.max(x) + margin), float(np.max(y) + margin)


class DemSampler:
    """Bilinear DEM sampling for lon/lat points. Heights are orthometric (above sea level)."""

    def __init__(self, paths: list[Path], lon_bounds, lat_bounds, margin: float = 50.0,
                 crs_override: str | None = None):
        self.paths = [Path(p) for p in paths]
        self.crs = _raster_crs(self.paths, crs_override)
        bounds = _bounds_in(self.crs, lon_bounds, lat_bounds, margin)
        arr, self.transform = merge([str(p) for p in self.paths], bounds=bounds, indexes=[1],
                                    nodata=np.nan, dtype="float64")
        self.data = arr[0]
        valid = np.isfinite(self.data)
        if not valid.any():
            raise ValueError("DEM has no data inside the requested area")
        if not valid.all():
            self.data = _fill_nan(self.data)
        self._from_lonlat = Transformer.from_crs(CRS.from_epsg(4326), self.crs, always_xy=True)
        self._inv = ~self.transform

    def sample_lonlat(self, lon, lat) -> np.ndarray:
        x, y = self._from_lonlat.transform(np.asarray(lon, dtype=np.float64), np.asarray(lat, dtype=np.float64))
        col, row = self._inv * (np.asarray(x), np.asarray(y))
        return _bilinear(self.data, np.asarray(row) - 0.5, np.asarray(col) - 0.5)


def _fill_nan(a: np.ndarray) -> np.ndarray:
    mask = ~np.isfinite(a)
    filled = np.where(mask, 0, a).astype(np.float32)
    return cv2.inpaint(filled, mask.astype(np.uint8), 3, cv2.INPAINT_NS).astype(np.float64)


def _bilinear(a: np.ndarray, r: np.ndarray, c: np.ndarray) -> np.ndarray:
    h, w = a.shape
    r = np.clip(r, 0, h - 1)
    c = np.clip(c, 0, w - 1)
    r0 = np.floor(r).astype(int)
    c0 = np.floor(c).astype(int)
    r1 = np.minimum(r0 + 1, h - 1)
    c1 = np.minimum(c0 + 1, w - 1)
    fr, fc = r - r0, c - c0
    top = a[r0, c0] * (1 - fc) + a[r0, c1] * fc
    bot = a[r1, c0] * (1 - fc) + a[r1, c1] * fc
    return top * (1 - fr) + bot * fr


class OrthoSource:
    """Crops the orthophoto mosaic for a tile and returns a JPEG plus UVs for given lon/lat points."""

    def __init__(self, paths: list[Path], crs_override: str | None = None):
        self.paths = [Path(p) for p in paths]
        self.crs = _raster_crs(self.paths, crs_override)
        self._from_lonlat = Transformer.from_crs(CRS.from_epsg(4326), self.crs, always_xy=True)
        with rasterio.open(self.paths[0]) as ds:
            self.band_count = min(ds.count, 3)

    def crop(self, lon, lat, max_size: int = 4096, jpeg_quality: int = 90):
        """Returns (jpeg_bytes, uv) or (None, None) when the tile has no imagery."""
        x, y = self._from_lonlat.transform(np.asarray(lon, dtype=np.float64), np.asarray(lat, dtype=np.float64))
        bounds = (float(np.min(x)), float(np.min(y)), float(np.max(x)), float(np.max(y)))
        arr, transform = merge([str(p) for p in self.paths], bounds=bounds,
                               indexes=list(range(1, self.band_count + 1)), nodata=0)
        if arr.size == 0 or not arr.any():
            return None, None
        img = np.moveaxis(arr, 0, -1)
        if img.shape[2] == 1:
            img = np.repeat(img, 3, axis=2)
        if img.dtype != np.uint8:
            hi = np.percentile(img, 99.5) or 1
            img = np.clip(img.astype(np.float64) / hi * 255, 0, 255).astype(np.uint8)
        h, w = img.shape[:2]
        col, row = (~transform) * (np.asarray(x), np.asarray(y))
        uv = np.stack([np.asarray(col) / w, np.asarray(row) / h], axis=1)
        # Square power-of-two texture so Unreal can build mips and stream it; UVs are normalized.
        side = min(max_size, 1 << int(np.ceil(np.log2(max(h, w, 2)))))
        interp = cv2.INTER_AREA if side < max(h, w) else cv2.INTER_CUBIC
        img = cv2.resize(img, (side, side), interpolation=interp)
        ok, buf = cv2.imencode(".jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
        if not ok:
            raise RuntimeError("JPEG encode failed")
        return buf.tobytes(), np.clip(uv, 0.0, 1.0)
