import csv
from pathlib import Path

import numpy as np
import pytest

from golmok_tools.imageio import read_image, write_image
from golmok_tools.privacy.blur import blur_regions, run, scale_box
from golmok_tools.privacy.detector import detect_scaled


class FakeDetector:
    """Returns a fixed box expressed as fractions of the image it receives."""

    def __init__(self, name, frac_box):
        self.name = name
        self.frac_box = frac_box
        self.seen_shapes = []

    def __call__(self, bgr_u8):
        self.seen_shapes.append(bgr_u8.shape)
        h, w = bgr_u8.shape[:2]
        fx1, fy1, fx2, fy2 = self.frac_box
        return [(fx1 * w, fy1 * h, fx2 * w, fy2 * h)]


def noise(h, w, dtype=np.uint8, seed=0):
    rng = np.random.default_rng(seed)
    hi = 255 if dtype == np.uint8 else 65535
    return rng.integers(0, hi, size=(h, w, 3), dtype=dtype)


def test_scale_box_clamps_to_image():
    assert scale_box((0, 0, 10, 10), 10, 10, 2.0) == (0.0, 0.0, 10.0, 10.0)
    x1, y1, x2, y2 = scale_box((40, 40, 60, 60), 100, 100, 1.5)
    assert (x1, y1, x2, y2) == (35.0, 35.0, 65.0, 65.0)


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16])
def test_blur_regions_smooths_inside_and_keeps_outside(dtype):
    img = noise(200, 300, dtype)
    out = blur_regions(img, [(100, 50, 200, 150)], scale=1.0)
    assert out.dtype == dtype
    center = out[90:110, 140:160].astype(np.float64)
    assert center.std() < img[90:110, 140:160].astype(np.float64).std() * 0.2
    np.testing.assert_array_equal(out[:40], img[:40])  # far outside the box untouched
    np.testing.assert_array_equal(out[:, :90], img[:, :90])


def test_blur_regions_no_boxes_is_identity():
    img = noise(10, 10)
    assert blur_regions(img, []) is img


def test_detect_scaled_maps_boxes_back_to_full_resolution():
    det = FakeDetector("face", (0.25, 0.25, 0.5, 0.5))
    img = noise(3000, 4000)
    boxes = detect_scaled(det, img, max_side=1000)
    assert det.seen_shapes[0][:2] == (750, 1000)
    x1, y1, x2, y2 = boxes[0]
    assert x1 == pytest.approx(1000, abs=2) and y2 == pytest.approx(1500, abs=2)


def test_run_mirrors_tree_and_writes_logs(tmp_path: Path):
    src = tmp_path / "촬영" / "photos"
    (src / "sub").mkdir(parents=True)
    write_image(noise(120, 160), src / "a.jpg")
    write_image(noise(120, 160, np.uint16), src / "sub" / "b.tif")
    write_image(noise(120, 160), src / "sub" / "c.png")
    (src / "notes.md").write_text("not an image")

    out = tmp_path / "blurred"
    dets = [FakeDetector("face", (0.1, 0.1, 0.4, 0.4)), FakeDetector("plate", (0.6, 0.6, 0.9, 0.9))]
    results = run(src, out, dets, max_side=0)

    assert sorted(r.status for r in results) == ["ok", "ok", "ok"]
    assert (out / "a.jpg").exists() and (out / "sub" / "b.tif").exists() and (out / "sub" / "c.png").exists()
    assert read_image(out / "sub" / "b.tif").dtype == np.uint16
    assert all(r.faces == 1 and r.plates == 1 for r in results)
    with open(out / "_golmok" / "blur_log.csv", encoding="utf-8-sig") as f:
        assert len(list(csv.DictReader(f))) == 3
    assert (out / "_golmok" / "preview" / "sub__b.jpg").exists()

    # second run skips existing outputs unless overwrite
    again = run(src, out, dets, max_side=0)
    assert {r.status for r in again} == {"skipped"}


def test_run_records_decode_errors(tmp_path: Path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "broken.jpg").write_bytes(b"not a jpeg")
    results = run(src, tmp_path / "out", [FakeDetector("face", (0, 0, 0.1, 0.1))], max_side=0)
    assert results[0].status == "decode_error"
