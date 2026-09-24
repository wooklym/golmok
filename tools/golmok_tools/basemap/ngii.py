"""NGII (국토지리정보원) map sheets and orthophoto georeferencing.

The 2025 정사영상 TIFFs from map.ngii.go.kr carry no GeoTIFF tags or world file; the metadata XML
only names the CRS (중부원점, GRS80, TM, 200000/600000 = EPSG:5186). Each image is one 1:5,000
sheet plus a ~50 m buffer, centered on the sheet's EPSG:5186 bounding box (checked on 37608077/078
against building footprints to ~1 m). `georef_orthos` writes tiled GeoTIFFs with that placement,
optionally refined by matching image edges to GIS building-footprint edges, and snaps overlapping
sheets to each other (their buffers match pixel for pixel) so no seam is left between them.

Sheet numbers: 1:50,000 = 5 digits (37608: 37°N band, 126°E, cell 08 of 4x4 15' cells numbered
row by row from the north-west); 1:5,000 = those 5 digits + 001..100 (10x10 cells of 1'30").
"""

from __future__ import annotations

import re
from pathlib import Path

import cv2
import numpy as np
import rasterio
import shapefile
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.windows import Window

SHEET_5000_RE = re.compile(r"(?<!\d)(\d{8})(?!\d)")


def sheet_5000_bounds(sheet: str) -> tuple[float, float, float, float]:
    """(lon0, lat0, lon1, lat1) of a 1:5,000 sheet such as '37608077'."""
    if not re.fullmatch(r"\d{8}", sheet):
        raise ValueError(f"not a 1:5,000 sheet number: {sheet}")
    lat_deg, lon_digit, cell50, cell5 = int(sheet[:2]), int(sheet[2]), int(sheet[3:5]), int(sheet[5:])
    if not (1 <= cell50 <= 16 and 1 <= cell5 <= 100):
        raise ValueError(f"not a 1:5,000 sheet number: {sheet}")
    lon_deg = 120 + lon_digit if lon_digit >= 4 else 130 + lon_digit
    r50, c50 = divmod(cell50 - 1, 4)
    r5, c5 = divmod(cell5 - 1, 10)
    lat1 = lat_deg + 1 - r50 * 0.25 - r5 * 0.025
    lon0 = lon_deg + c50 * 0.25 + c5 * 0.025
    return lon0, lat1 - 0.025, lon0 + 0.025, lat1


def sheet_bbox(sheet: str, crs: str = "EPSG:5186") -> tuple[float, float, float, float]:
    lon0, lat0, lon1, lat1 = sheet_5000_bounds(sheet)
    t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    x, y = t.transform([lon0, lon1, lon1, lon0], [lat0, lat0, lat1, lat1])
    return min(x), min(y), max(x), max(y)


def sheet_from_name(path: Path) -> str:
    m = SHEET_5000_RE.findall(Path(path).stem)
    if not m:
        raise ValueError(f"no 8-digit sheet number in {path.name}: pass --sheet")
    return m[-1]


def _gray(path: Path, res: float, pixel: float) -> np.ndarray:
    f = max(1, int(round(res / pixel)))
    with rasterio.open(path) as ds:
        a = ds.read(
            indexes=list(range(1, min(ds.count, 3) + 1)),
            out_shape=(min(ds.count, 3), ds.height // f, ds.width // f),
            resampling=Resampling.average,
        )
    return a.astype(np.float32).mean(axis=0)


def _edges(gray: np.ndarray) -> np.ndarray:
    gx, gy = cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1)
    return np.sqrt(gx * gx + gy * gy)


def footprint_rings(
    shp: Path, bbox: tuple[float, float, float, float], encoding: str = "cp949"
) -> list[np.ndarray]:
    """Polygon rings (same CRS as the SHP) whose bbox touches `bbox`."""
    x0, y0, x1, y1 = bbox
    rings = []
    with shapefile.Reader(str(shp), encoding=encoding) as r:
        for s in r.iterShapes():
            b = s.bbox
            if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
                continue
            parts = list(s.parts) + [len(s.points)]
            rings += [
                np.asarray(s.points[parts[i] : parts[i + 1]], np.float64) for i in range(len(parts) - 1)
            ]
    return rings


def _rasterize_edges(rings: list[np.ndarray], x0: float, y1: float, w: int, h: int, res: float) -> np.ndarray:
    img = np.zeros((h, w), np.uint8)
    for ring in rings:
        p = np.stack([(ring[:, 0] - x0) / res, (y1 - ring[:, 1]) / res], axis=1)
        if p[:, 0].max() < 0 or p[:, 1].max() < 0 or p[:, 0].min() > w or p[:, 1].min() > h:
            continue
        cv2.polylines(img, [np.round(p * 4).astype(np.int32)], True, 255, 1, cv2.LINE_AA, shift=2)
    return cv2.GaussianBlur(img.astype(np.float32), (0, 0), 1.0)


def refine_with_footprints(
    gray: np.ndarray, x0: float, y1: float, res: float, rings: list[np.ndarray], search: float = 150.0
) -> tuple[float, float, float, float]:
    """Best (x0, y1) of the image's top-left within +-search m, by normalized cross-correlation of
    image edges (gray at `res` m/px) with footprint edges. Returns (x0, y1, peak, runner_up)."""
    e = _edges(gray)
    s = int(round(search / res))
    ref = _rasterize_edges(rings, x0 - s * res, y1 + s * res, e.shape[1] + 2 * s, e.shape[0] + 2 * s, res)
    r = cv2.matchTemplate(ref, e, cv2.TM_CCOEFF_NORMED)
    _, peak, _, (cx, cy) = cv2.minMaxLoc(r)
    masked = r.copy()
    cv2.circle(masked, (cx, cy), max(2, int(10 / res)), -1.0, -1)
    return x0 + (cx - s) * res, y1 - (cy - s) * res, float(peak), float(masked.max())


def place_ortho(
    src: Path,
    sheet: str | None = None,
    pixel: float = 0.25,
    crs: str = "EPSG:5186",
    buildings: Path | None = None,
    encoding: str = "cp949",
) -> dict:
    """Top-left (x0, y1) of an un-georeferenced sheet image: sheet-centered, refined by footprints."""
    sheet = sheet or sheet_from_name(src)
    with rasterio.open(src) as ds:
        width, height = ds.width, ds.height
        if ds.crs is not None and not ds.transform.is_identity:
            raise ValueError(f"{src} is already georeferenced ({ds.crs})")
    bx0, by0, bx1, by1 = sheet_bbox(sheet, crs)
    w_m, h_m = width * pixel, height * pixel
    x0 = round(((bx0 + bx1) / 2 - w_m / 2) / pixel) * pixel
    y1 = round(((by0 + by1) / 2 + h_m / 2) / pixel) * pixel
    info = {
        "src": Path(src),
        "sheet": sheet,
        "method": "sheet-centered",
        "x0": x0,
        "y1": y1,
        "width": width,
        "height": height,
    }
    if buildings:
        res = 1.0
        rings = footprint_rings(buildings, (x0 - 200, y1 - h_m - 200, x0 + w_m + 200, y1 + 200), encoding)
        rx0, ry1, peak, second = refine_with_footprints(_gray(src, res, pixel), x0, y1, res, rings)
        info.update(
            peak=round(peak, 3),
            runner_up=round(second, 3),
            footprint_shift=(round(rx0 - x0, 2), round(ry1 - y1, 2)),
        )
        # Accept only a clear, nearby peak; otherwise keep the sheet-centered placement.
        if peak > 0.15 and peak > 1.3 * second and abs(rx0 - x0) < 20 and abs(ry1 - y1) < 20:
            info.update(
                method="footprint-refined", x0=round(rx0 / pixel) * pixel, y1=round(ry1 / pixel) * pixel
            )
    return info


def align_to_neighbor(
    a: dict, b: dict, pixel: float = 0.25, search: float = 5.0
) -> tuple[float, float, float] | None:
    """Exact (x0, y1, peak) of sheet b from image matching in its overlap with already-placed sheet a.

    Adjacent NGII sheets are cut from one mosaic, so their ~100 m overlaps match pixel for pixel;
    aligning to a neighbor removes seams that independent placement (~1 m) would leave."""

    def bounds(s):
        return s["x0"], s["y1"] - s["height"] * pixel, s["x0"] + s["width"] * pixel, s["y1"]

    ax0, ay0, ax1, ay1 = bounds(a)
    bx0, by0, bx1, by1 = bounds(b)
    ox0, oy0, ox1, oy1 = (
        max(ax0, bx0) + search,
        max(ay0, by0) + search,
        min(ax1, bx1) - search,
        min(ay1, by1) - search,
    )
    if ox1 - ox0 < 20 or oy1 - oy0 < 20:
        return None
    # Template: the middle (up to 800 m) of the overlap, read from a at full resolution.
    if oy1 - oy0 > 800:
        oy0 = (oy0 + oy1) / 2 - 400
        oy1 = oy0 + 800
    if ox1 - ox0 > 800:
        ox0 = (ox0 + ox1) / 2 - 400
        ox1 = ox0 + 800
    s = int(round(search / pixel))
    ac, ar = int(round((ox0 - ax0) / pixel)), int(round((ay1 - oy1) / pixel))
    w, h = int((ox1 - ox0) / pixel), int((oy1 - oy0) / pixel)
    bc, br = int(round((ox0 - bx0) / pixel)) - s, int(round((by1 - oy1) / pixel)) - s
    with rasterio.open(a["src"]) as da, rasterio.open(b["src"]) as db:
        tpl = da.read(window=Window(ac, ar, w, h)).astype(np.float32).mean(axis=0)
        win = db.read(window=Window(bc, br, w + 2 * s, h + 2 * s)).astype(np.float32).mean(axis=0)
    r = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED)
    _, peak, _, (cx, cy) = cv2.minMaxLoc(r)
    # Template's world top-left sits at b-pixel (bc + cx, br + cy).
    x0 = ax0 + ac * pixel - (bc + cx) * pixel
    y1 = ay1 - ar * pixel + (br + cy) * pixel
    return x0, y1, float(peak)


def georef_orthos(
    srcs: list[Path],
    out_dir: Path,
    sheet: str | None = None,
    pixel: float = 0.25,
    crs: str = "EPSG:5186",
    buildings: Path | None = None,
    encoding: str = "cp949",
) -> list[dict]:
    """Place every sheet, snap overlapping sheets to the first placed one, write ortho_<sheet>.tif."""
    placed: list[dict] = []
    for src in srcs:
        info = place_ortho(src, sheet, pixel, crs, buildings, encoding)
        for prev in placed:
            hit = align_to_neighbor(prev, info, pixel, search=max(5.0, 4 * pixel))
            if hit and hit[2] > 0.9:
                info.update(
                    method=f"aligned to {prev['sheet']}",
                    overlap_peak=round(hit[2], 3),
                    neighbor_shift=(round(hit[0] - info["x0"], 2), round(hit[1] - info["y1"], 2)),
                    x0=hit[0],
                    y1=hit[1],
                )
                break
        placed.append(info)
    for info in placed:
        info["out"] = Path(out_dir) / f"ortho_{info['sheet']}.tif"
        write_georef(info["src"], info["out"], info["x0"], info["y1"], pixel, crs)
    return placed


def write_georef(src: Path, out: Path, x0: float, y1: float, pixel: float, crs: str) -> None:
    """Tiled, compressed GeoTIFF copy of `src` with the given top-left and pixel size."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(src) as ds:
        profile = ds.profile.copy()
        profile.update(
            driver="GTiff",
            crs=CRS.from_user_input(crs),
            transform=from_origin(x0, y1, pixel, pixel),
            tiled=True,
            blockxsize=512,
            blockysize=512,
            compress="deflate",
            predictor=2,
            BIGTIFF="IF_SAFER",
        )
        profile.pop("photometric", None)
        with rasterio.open(out, "w", **profile) as dst:
            for _, window in dst.block_windows(1):
                dst.write(ds.read(window=window), window=window)
            dst.build_overviews([2, 4, 8, 16], Resampling.average)
