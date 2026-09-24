"""NGII sheet math and orthophoto georeferencing on synthetic images."""

from pathlib import Path

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")
cv2 = pytest.importorskip("cv2")

from golmok_tools.basemap.ngii import (  # noqa: E402
    georef_orthos,
    refine_with_footprints,
    sheet_5000_bounds,
    sheet_bbox,
    sheet_from_name,
)


def test_sheet_bounds_yeonnam():
    # 37608 = 1:50,000 "서울" (37.5-37.75 N, 126.75-127.0 E); 077/078 cover Yeonnam-dong.
    assert sheet_5000_bounds("37608077") == pytest.approx((126.900, 37.550, 126.925, 37.575))
    assert sheet_5000_bounds("37608078") == pytest.approx((126.925, 37.550, 126.950, 37.575))
    assert sheet_5000_bounds("37608001") == pytest.approx((126.750, 37.725, 126.775, 37.750))
    assert sheet_5000_bounds("38701100") == pytest.approx((127.225, 38.750, 127.250, 38.775))


def test_sheet_bbox_size_and_name():
    x0, y0, x1, y1 = sheet_bbox("37608077")
    assert x1 - x0 == pytest.approx(2211.4, abs=1)  # 1'30" of longitude at 37.56 N
    assert y1 - y0 == pytest.approx(2776.8, abs=1)
    assert sheet_from_name(Path("(B060)정사영상_2025_37608077.tif")) == "37608077"
    with pytest.raises(ValueError):
        sheet_5000_bounds("3760807")


def _blocks(w, h, res, x0, y1, rng):
    """Random building rectangles (EPSG:5186 rings) and their rendering (roof bright, ground dark)."""
    img = np.full((h, w), 60, np.uint8)
    rings = []
    for _ in range(400):
        cx, cy = rng.uniform(0, w * res), rng.uniform(0, h * res)
        bw, bh = rng.uniform(8, 25), rng.uniform(8, 25)
        c0, r0 = int((cx - bw / 2) / res), int((cy - bh / 2) / res)
        c1, r1 = int((cx + bw / 2) / res), int((cy + bh / 2) / res)
        img[max(r0, 0) : r1, max(c0, 0) : c1] = rng.integers(140, 230)
        X0, X1 = x0 + c0 * res, x0 + c1 * res
        Y1, Y0 = y1 - r0 * res, y1 - r1 * res
        rings.append(np.array([(X0, Y0), (X0, Y1), (X1, Y1), (X1, Y0), (X0, Y0)], np.float64))
    return img, rings


def test_refine_with_footprints_recovers_shift():
    rng = np.random.default_rng(3)
    res, true_x0, true_y1 = 1.0, 193322.0, 552882.0
    img, rings = _blocks(600, 700, res, true_x0, true_y1, rng)
    x0, y1, peak, second = refine_with_footprints(
        img.astype(np.float32), true_x0 - 7, true_y1 + 4, res, rings, 30
    )
    assert (x0, y1) == pytest.approx((true_x0, true_y1), abs=1.0)
    assert peak > 1.3 * second


def _write_plain_tif(path, arr):
    with rasterio.open(
        path, "w", driver="GTiff", width=arr.shape[2], height=arr.shape[1], count=arr.shape[0], dtype="uint8"
    ) as ds:
        ds.write(arr)


def test_georef_orthos_centers_on_sheet_and_snaps_neighbor(tmp_path):
    # Sheets 077/078 at 2 m/px (2.31 x 2.88 km each) cut from one random mosaic. 077 sits exactly on
    # its sheet-centered guess; 078 is 1 px right and 1 px down of its own guess, as real placement
    # errors are ~1 m. The ~100 m overlap must snap 078 to its true position.
    pixel, w, h = 2.0, 1155, 1439

    def guess(sheet):
        bx0, by0, bx1, by1 = sheet_bbox(sheet)
        return (
            round(((bx0 + bx1) / 2 - w * pixel / 2) / pixel) * pixel,
            round(((by0 + by1) / 2 + h * pixel / 2) / pixel) * pixel,
        )

    (ax, ay), (bxg, byg) = guess("37608077"), guess("37608078")
    dc, dr = int(round((bxg - ax) / pixel)) + 1, int(round((ay - byg) / pixel)) + 1
    rng = np.random.default_rng(1)
    mosaic = cv2.GaussianBlur(rng.integers(0, 255, (h + dr + 2, w + dc + 2), np.uint8), (0, 0), 1.5)
    a_src, b_src = tmp_path / "x_37608077.tif", tmp_path / "x_37608078.tif"
    _write_plain_tif(a_src, np.repeat(mosaic[None, :h, :w], 3, axis=0))
    _write_plain_tif(b_src, np.repeat(mosaic[None, dr : dr + h, dc : dc + w], 3, axis=0))
    a, b = georef_orthos([a_src, b_src], tmp_path / "out", pixel=pixel)
    assert a["method"] == "sheet-centered" and (a["x0"], a["y1"]) == (ax, ay)
    assert b["method"] == "aligned to 37608077" and b["overlap_peak"] > 0.99
    assert (b["x0"], b["y1"]) == pytest.approx((ax + dc * pixel, ay - dr * pixel), abs=1e-6)
    with rasterio.open(b["out"]) as ds:
        assert ds.crs.to_epsg() == 5186 and ds.res == (pixel, pixel) and ds.overviews(1)
        assert ds.bounds.left == pytest.approx(b["x0"])
