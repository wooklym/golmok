"""Cross-check unreal/.../Photo/GolmokPhotoMath.h (pure C++) against numpy / shapely (WP-12 design §8-2).

The header has no Unreal dependency (its only quoted includes are the two other pure headers,
Geo/GolmokGeoMath.h and Debug/GolmokStatsMath.h), so it is compiled with g++
(fixtures/ue/photomath_driver.cpp) into a small command-line driver: parameter steps / quantisation / f-stop
table, angle wrap, FOV -> 35 mm focal length, the sphere and footprint-polygon clamps, the combined
`Constrain` rule and the photo meta JSON writer. Every input goes through stdin (Windows argv limit / code
page). Skipped when no C++ compiler is on PATH; the polygon cases also need shapely (`zone` extra).
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from test_ue_stats_math import ALLOWED_INCLUDES, _compiler
from zone_util import FIXTURE_ZONES, REPO

SOURCE_ROOT = REPO / "unreal" / "Golmok" / "Source" / "Golmok"
HEADER = SOURCE_ROOT / "Photo" / "GolmokPhotoMath.h"
PHOTO_JSON = REPO / "unreal" / "Golmok" / "Config" / "Golmok" / "photo.json"
DRIVER_SRC = Path(__file__).parent / "fixtures" / "ue" / "photomath_driver.cpp"
FIXTURE_MANIFEST = FIXTURE_ZONES / "z_synthetic_001" / "v1" / "manifest.json"
AREA = (37.5600, 126.9230, 40.0)  # level origin used by test_ue_geo_math.py
QUOTED_INCLUDES = ["Debug/GolmokStatsMath.h", "Geo/GolmokGeoMath.h"]
BANNED = (
    "CoreMinimal",
    "UCLASS",
    "UE_LOG",
    "std::min",
    "std::max",
    "printf",
    "cstdio",
    "TEXT(",
    "FVector",
    "FString",
)
# design §3-1: every free function the subsystem / pawn / tests code against
FUNCTIONS = [
    "ClampParam",
    "Quantize",
    "StepLinear",
    "StepGeometric",
    "NearestIndex",
    "StepTable",
    "WrapDeg180",
    "FovToFocalMm",
    "ClampToSphere",
    "NearestBoundaryPoint",
    "ClampToPolygonXY",
    "Constrain",
    "FormatPhotoMetaJson",
]
# design §2-1 (photo.json is the single source; the constants here are the pytest regression copy)
FSTOP_VALUES = [1.4, 2.0, 2.8, 4.0, 5.6, 8.0, 11.0, 16.0]
EV_MIN, EV_MAX, EV_STEP_JSON = -3.0, 3.0, 0.3333333333
FOCUS_MIN, FOCUS_MAX, FOCUS_RATIO = 0.3, 50.0, 1.25
META_KEYS = [
    "version",
    "time_utc",
    "preset",
    "zone_id",
    "zone_version",
    "lon",
    "lat",
    "height_m",
    "ue_location",
    "rotation",
    "fov",
    "exposure_ev",
    "dof",
    "multiplier",
    "character_hidden",
]
DOF_KEYS = ["enabled", "focal_m", "fstop"]
# design §2-2: the exact file layout
EXAMPLE_META = {
    "version": 1,
    "time_utc": "2026-09-25T10:11:12Z",
    "preset": "overcast_morning",
    "zone_id": "z_synthetic_001",
    "zone_version": 1,
    "lon": 126.9250123,
    "lat": 37.5620456,
    "height_m": 51.234,
    "ue_location": [17670.59, -22698.0, 1190.0],
    "rotation": [-5.0, 90.0, 0.0],
    "fov": 65.0,
    "exposure_ev": 0.33,
    "dof": {"enabled": False, "focal_m": 3.0, "fstop": 2.8},
    "multiplier": 2,
    "character_hidden": False,
}
EXAMPLE_JSON = (
    "{\n"
    '  "version": 1,\n'
    '  "time_utc": "2026-09-25T10:11:12Z",\n'
    '  "preset": "overcast_morning",\n'
    '  "zone_id": "z_synthetic_001",\n'
    '  "zone_version": 1,\n'
    '  "lon": 126.9250123,\n'
    '  "lat": 37.5620456,\n'
    '  "height_m": 51.234,\n'
    '  "ue_location": [17670.59, -22698.00, 1190.00],\n'
    '  "rotation": [-5.000, 90.000, 0.000],\n'
    '  "fov": 65.0,\n'
    '  "exposure_ev": 0.33,\n'
    '  "dof": {"enabled": false, "focal_m": 3.000, "fstop": 2.80},\n'
    '  "multiplier": 2,\n'
    '  "character_hidden": false\n'
    "}\n"
)

# Test rings (level UE cm). The anchor of each is strictly inside.
SQUARE = [(-100.0, -100.0), (100.0, -100.0), (100.0, 100.0), (-100.0, 100.0)]
L_SHAPE = [(0.0, 0.0), (400.0, 0.0), (400.0, 100.0), (100.0, 100.0), (100.0, 400.0), (0.0, 400.0)]
STAR = [
    (
        round((300.0 if i % 2 == 0 else 120.0) * math.cos(math.radians(90 + 36 * i)), 6),
        round((300.0 if i % 2 == 0 else 120.0) * math.sin(math.radians(90 + 36 * i)), 6),
    )
    for i in range(10)
]
# a wide notch reaching almost to the anchor: the polygon nudge can leave the 100 cm sphere (design §6-2 ③)
NOTCHED = [
    (-300.0, -300.0),
    (300.0, -300.0),
    (300.0, -60.0),
    (10.0, -60.0),
    (10.0, 60.0),
    (300.0, 60.0),
    (300.0, 300.0),
    (-300.0, 300.0),
]


@pytest.fixture(scope="module")
def driver(tmp_path_factory) -> Path:
    cxx = _compiler()
    if cxx is None:
        pytest.skip("no C++ compiler (g++/clang++) on PATH")
    build = tmp_path_factory.mktemp("photomath")
    exe = build / ("driver.exe" if sys.platform == "win32" else "driver")
    cmd = [*cxx, f"-I{SOURCE_ROOT}", str(DRIVER_SRC), "-o", str(exe)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"compile failed:\n{' '.join(cmd)}\n{res.stdout}\n{res.stderr}"
    return exe


def nums(*values) -> str:
    return " ".join(repr(float(v)) for v in values)


def run_raw(driver: Path, cmd: str, stdin: str = "") -> subprocess.CompletedProcess:
    # encoding= on both pipes: Windows would otherwise use cp1252 (the meta test sends UTF-8)
    return subprocess.run([str(driver), cmd], input=stdin, capture_output=True, text=True, encoding="utf-8")


def run(driver: Path, cmd: str, stdin: str = "") -> list[float]:
    res = run_raw(driver, cmd, stdin)
    assert res.returncode == 0, res.stdout + res.stderr
    return [float(v) for v in res.stdout.split()]


def run_lines(driver: Path, cmd: str, stdin: str) -> list[list[float]]:
    res = run_raw(driver, cmd, stdin)
    assert res.returncode == 0, res.stdout + res.stderr
    return [[float(v) for v in line.split()] for line in res.stdout.splitlines()]


def one(driver: Path, cmd: str, *values) -> float:
    (got,) = run(driver, cmd, nums(*values))
    return got


def close(a, b, tol: float = 1e-9) -> bool:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return bool(np.all(np.abs(a - b) <= tol * np.maximum(1.0, np.abs(b))))


# -------------------------------------------------------------------------------------------------------- (a)


def test_photo_header_is_pure_and_declares_the_design_functions():
    text = HEADER.read_text(encoding="utf-8")
    assert text.lstrip().startswith("#pragma once")
    assert sorted(re.findall(r'^#include\s+"([^"]+)"', text, re.M)) == QUOTED_INCLUDES
    assert set(re.findall(r"^#include\s+<([^>]+)>", text, re.M)) <= ALLOWED_INCLUDES
    for banned in BANNED:
        assert banned not in text, banned
    assert "namespace GolmokPhotoMath" in text
    assert re.search(r"\bPI\b", text) is None  # Unreal macro; the header uses GolmokGeoMath::DegToRad
    assert re.search(r"^\s*(?:PI|check)\b", text, re.M) is None
    assert "inline " in text and " double " in text
    for name in FUNCTIONS:
        assert re.search(rf"^\s*inline\s+[\w:<>, ]+\s+{name}\(", text, re.M), name
    for struct in ("struct Constraint", "struct PhotoMeta", "using Vec3 = std::array<double, 3>;"):
        assert struct in text, struct
    # the two other pure headers stay pure (their own tests assert this too; this guards the include chain)
    for other in QUOTED_INCLUDES:
        other_text = (SOURCE_ROOT / other).read_text(encoding="utf-8")
        assert re.findall(r'^#include\s+"', other_text, re.M) == [], other


def test_driver_reports_parse_errors_and_unknown_commands(driver):
    res = run_raw(driver, "clamp", "x 0 1")
    assert res.returncode == 3 and res.stdout.startswith("ERROR "), res.stdout
    res = run_raw(driver, "sphere", "0 0 0 1")  # truncated
    assert res.returncode == 3 and res.stdout.startswith("ERROR "), res.stdout
    res = run_raw(driver, "meta", "version=1\nbogus=2\n")
    assert res.returncode == 3 and res.stdout.startswith("ERROR "), res.stdout
    res = run_raw(driver, "meta", "fov=abc\n")
    assert res.returncode == 3 and res.stdout.startswith("ERROR "), res.stdout
    assert run_raw(driver, "nosuch", "1 2 3").returncode == 2


# -------------------------------------------------------------------------------------------------------- (b)


def test_clamp_param(driver):
    assert one(driver, "clamp", 0.5, 0.0, 1.0) == 0.5
    assert one(driver, "clamp", -2.0, 0.0, 1.0) == 0.0
    assert one(driver, "clamp", 7.0, 0.0, 1.0) == 1.0
    assert one(driver, "clamp", 0.0, 0.0, 1.0) == 0.0 and one(driver, "clamp", 1.0, 0.0, 1.0) == 1.0
    assert one(driver, "clamp", float("nan"), -3.0, 3.0) == -3.0  # NaN -> lo
    assert one(driver, "clamp", 0.5, 1.0, 0.0) == 0.5  # lo > hi: swapped
    assert one(driver, "clamp", 9.0, 1.0, 0.0) == 1.0
    assert one(driver, "clamp", -9.0, 1.0, 0.0) == 0.0
    assert one(driver, "clamp", float("nan"), 1.0, 0.0) == 0.0
    assert one(driver, "clamp", float("inf"), 20.0, 110.0) == 110.0
    assert one(driver, "clamp", float("-inf"), 20.0, 110.0) == 20.0


# -------------------------------------------------------------------------------------------------------- (c)


def ref_quantize(v: float, lo: float, hi: float, step: float) -> float:
    k = round((v - lo) / step)
    k = max(0, min(k, int(math.floor((hi - lo) / step + 1e-9))))
    return lo + k * step


def test_quantize_and_step_linear_stay_on_the_grid(driver):
    third = 1.0 / 3.0
    # 1/3 EV: 9 steps up reach +3 exactly, 9 back give exactly 0.0 (no accumulated drift)
    v = 0.0
    for _ in range(9):
        v = one(driver, "steplin", v, EV_MIN, EV_MAX, third, 1)
    assert v == 3.0
    for _ in range(9):
        v = one(driver, "steplin", v, EV_MIN, EV_MAX, third, -1)
    assert v == 0.0
    # 18 steps each way: clamped at the ends, exactly the limits
    v = 0.0
    for _ in range(18):
        v = one(driver, "steplin", v, EV_MIN, EV_MAX, third, 1)
    assert v == EV_MAX
    for _ in range(18):
        v = one(driver, "steplin", v, EV_MIN, EV_MAX, third, -1)
    assert v == EV_MIN
    assert one(driver, "quant", 0.0, EV_MIN, EV_MAX, third) == 0.0
    # the photo.json spelling of the step (10 digits) walks the same grid within rounding
    v = 0.0
    for _ in range(9):
        v = one(driver, "steplin", v, EV_MIN, EV_MAX, EV_STEP_JSON, 1)
    assert v == pytest.approx(3.0, abs=1e-8)
    for _ in range(9):
        v = one(driver, "steplin", v, EV_MIN, EV_MAX, EV_STEP_JSON, -1)
    assert v == pytest.approx(0.0, abs=1e-8)
    assert one(driver, "quant", 0.34, EV_MIN, EV_MAX, EV_STEP_JSON) == pytest.approx(third, abs=1e-8)
    assert one(driver, "quant", -0.4, EV_MIN, EV_MAX, EV_STEP_JSON) == pytest.approx(-third, abs=1e-8)
    # 0.1 steps, 30 times: the result is a grid value (k * 0.1 from -1) and matches the Python reference
    v = -1.0
    for i in range(30):
        v = one(driver, "steplin", v, -1.0, 2.0, 0.1, 1)
        assert v == pytest.approx(-1.0 + 0.1 * (i + 1), abs=1e-12)
        assert v == ref_quantize(v, -1.0, 2.0, 0.1)
    assert v == pytest.approx(2.0)
    # clamping at the limits; dir 0 only quantises; any |dir| >= 1 is one step
    assert one(driver, "steplin", 110.0, 20.0, 110.0, 5.0, 1) == 110.0
    assert one(driver, "steplin", 20.0, 20.0, 110.0, 5.0, -1) == 20.0
    assert one(driver, "steplin", 200.0, 20.0, 110.0, 5.0, 1) == 110.0
    assert one(driver, "steplin", 63.0, 20.0, 110.0, 5.0, 0) == 65.0
    assert one(driver, "steplin", 62.0, 20.0, 110.0, 5.0, 0) == 60.0
    assert one(driver, "steplin", 65.0, 20.0, 110.0, 5.0, 7) == 70.0
    assert one(driver, "steplin", 65.0, 20.0, 110.0, 5.0, -3) == 60.0
    assert one(driver, "quant", 80.0, 20.0, 110.0, 5.0) == 80.0  # entry FOV of the character camera
    assert one(driver, "quant", 82.4, 20.0, 110.0, 5.0) == 80.0
    assert one(driver, "quant", 82.5, 20.0, 110.0, 5.0) == 85.0
    # a max that is not on the grid: k stops at floor((max - min) / step)
    assert one(driver, "quant", 100.0, 0.0, 10.5, 3.0) == 9.0
    assert one(driver, "quant", 9.4, 0.0, 10.5, 3.0) == 9.0
    # NaN -> min, degenerate step -> plain clamp
    assert one(driver, "quant", float("nan"), -3.0, 3.0, third) == -3.0
    assert one(driver, "quant", 1.7, 0.0, 3.0, 0.0) == 1.7
    assert one(driver, "quant", 1.7, 0.0, 3.0, -1.0) == 1.7
    assert one(driver, "quant", 1.5, 3.0, 0.0, 1.0) == 2.0  # swapped limits
    rng = np.random.default_rng(12)
    for _ in range(200):
        lo, span = float(rng.uniform(-50, 50)), float(rng.uniform(0.5, 100))
        step = float(rng.uniform(0.01, 5))
        v = float(rng.uniform(lo - 10, lo + span + 10))
        got = one(driver, "quant", v, lo, lo + span, step)
        assert got == pytest.approx(ref_quantize(v, lo, lo + span, step), abs=1e-9)
        assert lo - 1e-9 <= got <= lo + span + 1e-9


# -------------------------------------------------------------------------------------------------------- (d)


def test_step_geometric_focus_range(driver):
    steps = 0
    v = FOCUS_MIN
    while v < FOCUS_MAX:
        nxt = one(driver, "stepgeo", v, FOCUS_MIN, FOCUS_MAX, FOCUS_RATIO, 1)
        assert nxt > v and round(nxt, 3) == nxt, nxt
        v = nxt
        steps += 1
        assert steps < 100
    assert steps == math.ceil(math.log(FOCUS_MAX / FOCUS_MIN) / math.log(FOCUS_RATIO)) == 23
    assert v == FOCUS_MAX
    assert one(driver, "stepgeo", FOCUS_MAX, FOCUS_MIN, FOCUS_MAX, FOCUS_RATIO, 1) == FOCUS_MAX
    assert one(driver, "stepgeo", FOCUS_MIN, FOCUS_MIN, FOCUS_MAX, FOCUS_RATIO, -1) == FOCUS_MIN
    # round trips: up then down returns the 3-decimal value (within one rounding unit)
    for v in (0.3, 0.469, 1.0, 3.0, 7.5, 12.345, 40.0):
        up = one(driver, "stepgeo", v, FOCUS_MIN, FOCUS_MAX, FOCUS_RATIO, 1)
        back = one(driver, "stepgeo", up, FOCUS_MIN, FOCUS_MAX, FOCUS_RATIO, -1)
        assert up == pytest.approx(min(v * FOCUS_RATIO, FOCUS_MAX), abs=5e-4)
        assert back == pytest.approx(v, abs=2e-3), (v, up, back)
        assert round(up, 3) == up and round(back, 3) == back
    assert one(driver, "stepgeo", 3.0, FOCUS_MIN, FOCUS_MAX, FOCUS_RATIO, 1) == 3.75
    assert one(driver, "stepgeo", 3.75, FOCUS_MIN, FOCUS_MAX, FOCUS_RATIO, -1) == 3.0
    # dir 0: clamped (and rounded) value; out-of-range inputs clamp
    assert one(driver, "stepgeo", 3.14159, FOCUS_MIN, FOCUS_MAX, FOCUS_RATIO, 0) == 3.142
    assert one(driver, "stepgeo", 0.01, FOCUS_MIN, FOCUS_MAX, FOCUS_RATIO, 0) == FOCUS_MIN
    assert one(driver, "stepgeo", 999.0, FOCUS_MIN, FOCUS_MAX, FOCUS_RATIO, -1) == FOCUS_MAX
    assert one(driver, "stepgeo", 999.0, FOCUS_MIN, FOCUS_MAX, FOCUS_RATIO, 1) == FOCUS_MAX
    assert one(driver, "stepgeo", float("nan"), FOCUS_MIN, FOCUS_MAX, FOCUS_RATIO, 1) == pytest.approx(0.375)


# -------------------------------------------------------------------------------------------------------- (e)


def table(driver: Path, direction: int, v: float, values=FSTOP_VALUES) -> tuple[float, int]:
    got = run(driver, "table", f"{direction} {v!r} {len(values)} " + nums(*values))
    return got[0], int(got[1])


def test_fstop_table_nearest_and_steps(driver):
    if PHOTO_JSON.exists():  # single source: the pytest copy must match the shipped table
        shipped = json.loads(PHOTO_JSON.read_text(encoding="utf-8"))["params"]["fstop"]["values"]
        assert shipped == FSTOP_VALUES
    # nearest of an in-between value, both ends, ties -> lower index
    assert table(driver, 0, 2.9) == (2.8, 2)
    assert table(driver, 0, 3.5) == (4.0, 3)
    assert table(driver, 0, 1.0) == (1.4, 0)
    assert table(driver, 0, 99.0) == (16.0, 7)
    assert table(driver, 0, 2.4) == (2.0, 1)  # exact tie 2.0 / 2.8 -> lower index
    assert table(driver, 0, 4.8) == (4.0, 3)  # exact tie 4.0 / 5.6
    assert table(driver, 0, 13.5) == (11.0, 6)  # exact tie 11 / 16
    assert table(driver, 0, float("nan")) == (1.4, 0)
    # steps move the nearest index by one and clamp at the ends
    assert table(driver, 1, 2.8) == (4.0, 2)
    assert table(driver, -1, 2.8) == (2.0, 2)
    assert table(driver, 1, 2.9) == (4.0, 2)
    assert table(driver, -1, 3.5) == (2.8, 3)
    assert table(driver, 1, 16.0) == (16.0, 7)
    assert table(driver, -1, 1.4) == (1.4, 0)
    assert table(driver, 5, 2.8) == (4.0, 2)
    assert table(driver, -5, 2.8) == (2.0, 2)
    # 7 steps cross the whole table, 7 back return to the start
    v = 1.4
    for _ in range(7):
        v, _ = table(driver, 1, v)
    assert v == 16.0
    for _ in range(7):
        v, _ = table(driver, -1, v)
    assert v == 1.4
    # empty table -> V unchanged, index 0
    assert table(driver, 1, 2.8, []) == (2.8, 0)
    assert table(driver, 0, 7.0, [5.0]) == (5.0, 0)


# -------------------------------------------------------------------------------------------------------- (f)


def test_wrap_deg_180(driver):
    assert one(driver, "wrap", 180.0) == 180.0
    assert one(driver, "wrap", 181.0) == -179.0
    assert one(driver, "wrap", -180.0) == 180.0
    assert one(driver, "wrap", 720.0) == 0.0
    assert one(driver, "wrap", 0.0) == 0.0
    assert one(driver, "wrap", -181.0) == 179.0
    assert one(driver, "wrap", 540.0) == 180.0
    assert one(driver, "wrap", -540.0) == 180.0
    assert one(driver, "wrap", 359.5) == -0.5
    assert one(driver, "wrap", float("nan")) == 0.0
    rng = np.random.default_rng(13)
    for deg in rng.uniform(-2000, 2000, 100):
        got = one(driver, "wrap", float(deg))
        assert -180.0 < got <= 180.0
        assert math.isclose((got - deg) % 360.0, 0.0, abs_tol=1e-9) or math.isclose(
            (got - deg) % 360.0, 360.0
        )


# -------------------------------------------------------------------------------------------------------- (g)


def test_fov_to_focal_mm(driver):
    assert one(driver, "fov2mm", 65.0) == pytest.approx(28.2, abs=0.1)
    assert one(driver, "fov2mm", 39.6) == pytest.approx(50.0, abs=0.05)
    assert one(driver, "fov2mm", 20.0) == pytest.approx(102.07, abs=0.05)
    assert one(driver, "fov2mm", 110.0) == pytest.approx(12.60, abs=0.01)
    assert one(driver, "fov2mm", 90.0) == pytest.approx(18.0, abs=1e-9)
    assert one(driver, "fov2mm", 90.0, 24.0) == pytest.approx(12.0, abs=1e-9)
    for fov in (1.0, 27.5, 65.0, 120.0, 179.0):
        assert one(driver, "fov2mm", fov) == pytest.approx(36.0 / (2.0 * math.tan(math.radians(fov) / 2.0)))
    assert one(driver, "fov2mm", 0.0) == one(driver, "fov2mm", 1.0)  # clamped to [1, 179]
    assert one(driver, "fov2mm", 200.0) == one(driver, "fov2mm", 179.0)


# -------------------------------------------------------------------------------------------------------- (h)


def sphere(driver: Path, center, r: float, p) -> tuple[bool, np.ndarray]:
    got = run(driver, "sphere", nums(*center, r, *p))
    return got[0] == 1.0, np.array(got[1:])


def test_clamp_to_sphere_matches_numpy(driver):
    c = np.array([100.0, -200.0, 50.0])
    moved, out = sphere(driver, c, 300.0, c + [10.0, 20.0, -5.0])
    assert not moved and np.array_equal(out, c + [10.0, 20.0, -5.0])
    moved, out = sphere(driver, c, 300.0, c + [500.0, 0.0, 0.0])
    assert moved and np.allclose(out, c + [300.0, 0.0, 0.0], atol=1e-9)
    moved, out = sphere(driver, c, 300.0, c + [0.0, 300.0, 0.0])  # exactly on the boundary: inside
    assert not moved and np.array_equal(out, c + [0.0, 300.0, 0.0])
    moved, out = sphere(driver, c, 300.0, c)
    assert not moved and np.array_equal(out, c)
    moved, out = sphere(driver, c, 0.0, c + [1.0, 1.0, 1.0])  # r = 0 -> center
    assert moved and np.array_equal(out, c)
    moved, out = sphere(driver, c, 0.0, c)
    assert not moved and np.array_equal(out, c)
    moved, out = sphere(driver, c, -5.0, c + [1.0, 0.0, 0.0])
    assert moved and np.array_equal(out, c)
    rng = np.random.default_rng(14)
    for _ in range(200):
        center = rng.uniform(-3000, 3000, 3)
        r = float(rng.uniform(50, 500))
        p = center + rng.uniform(-2, 2, 3) * r
        moved, out = sphere(driver, center, r, p)
        d = float(np.linalg.norm(p - center))
        if d <= r:
            assert not moved and np.array_equal(out, p)
        else:
            assert moved
            assert abs(np.linalg.norm(out - center) - r) < 1e-9
            expect = center + (p - center) * (r / d)
            assert np.allclose(out, expect, atol=1e-9)


# -------------------------------------------------------------------------------------------------------- (i)


def ring_text(ring) -> str:
    return f"{len(ring)} " + nums(*(v for p in ring for v in p))


def poly(driver: Path, ring, anchor, inset: float, points) -> list[tuple[int, float, float]]:
    text = f"{anchor[0]!r} {anchor[1]!r} {inset!r} {ring_text(ring)} {len(points)} "
    text += nums(*(v for p in points for v in p))
    rows = run_lines(driver, "poly", text)
    assert len(rows) == len(points)
    return [(int(r[0]), r[1], r[2]) for r in rows]


def polyq(driver: Path, ring, points) -> list[tuple[float, float, float, int]]:
    text = f"{ring_text(ring)} {len(points)} " + nums(*(v for p in points for v in p))
    rows = run_lines(driver, "polyq", text)
    assert len(rows) == len(points)
    return [(r[0], r[1], r[2], int(r[3])) for r in rows]


def fixture_footprint_ue() -> list[tuple[float, float]]:
    """z_synthetic_001 footprint (WGS84) -> level UE cm at the area origin, like the zone actor does."""
    from golmok_tools.zone import transform as T

    d = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    ring = d["footprint_wgs84"]["coordinates"][0]
    if ring[0] == ring[-1]:
        ring = ring[:-1]
    lons = np.array([p[0] for p in ring])
    lats = np.array([p[1] for p in ring])
    enu = T.lonlat_to_enu(lons, lats, np.zeros(len(ring)), AREA)
    ue = T.enu_to_ue(enu)
    return [(float(x), float(y)) for x, y in ue[:, :2]]


def polygon_cases():
    fixture = fixture_footprint_ue()
    cx = sum(p[0] for p in fixture) / len(fixture)
    cy = sum(p[1] for p in fixture) / len(fixture)
    return [
        ("square", SQUARE, (0.0, 0.0)),
        ("L", L_SHAPE, (50.0, 350.0)),
        ("star", STAR, (0.0, 0.0)),
        ("fixture", fixture, (cx, cy)),
    ]


def check_clamp_against_shapely(driver, name, ring, anchor, inset, points):
    from shapely.geometry import LineString, Point, Polygon

    shape = Polygon(ring)
    assert shape.is_valid and shape.contains(Point(anchor)), name
    results = poly(driver, ring, anchor, inset, points)
    nearest = polyq(driver, ring, points)
    for p, (code, x, y), (dist, qx, qy, _edge) in zip(points, results, nearest, strict=True):
        pt = Point(p)
        boundary_dist = shape.exterior.distance(pt)
        if boundary_dist < 1e-6:
            continue  # on the boundary: even-odd side is arbitrary (tested separately)
        if shape.contains(pt):
            assert code == 0 and (x, y) == p, (name, p, code)
            continue
        assert code in (1, 2), (name, p, code)
        # Q is the nearest boundary point (same distance as shapely, 1e-9)
        assert abs(dist - boundary_dist) < 1e-9, (name, p, dist, boundary_dist)
        assert abs(math.dist(p, (qx, qy)) - boundary_dist) < 1e-9, (name, p)
        assert shape.exterior.distance(Point(qx, qy)) < 1e-9, (name, p)
        to_anchor = math.dist((qx, qy), anchor)
        nudge = min(inset, to_anchor)
        expect = (qx + (anchor[0] - qx) * nudge / to_anchor, qy + (anchor[1] - qy) * nudge / to_anchor)
        if code == 1:
            assert shape.contains(Point(x, y)), (name, p, (x, y))
            assert abs(math.dist((x, y), (qx, qy)) - nudge) < 1e-9, (name, p)
            assert LineString([(qx, qy), anchor]).distance(Point(x, y)) < 1e-9, (name, p)
            assert 0 < shape.exterior.distance(Point(x, y)) <= inset + 1e-6, (name, p)
            assert (x, y) == pytest.approx(expect, abs=1e-9)
        else:
            assert (x, y) == (qx, qy), (name, p)
            # the nudged point really is outside (or on the boundary) of the ring
            assert not shape.contains(Point(expect)) or shape.exterior.distance(Point(expect)) < 1e-9, (
                name,
                p,
            )


def test_clamp_to_polygon_matches_shapely(driver):
    pytest.importorskip("shapely")
    rng = np.random.default_rng(15)
    for name, ring, anchor in polygon_cases():
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        points = [
            (float(x), float(y))
            for x, y in zip(
                rng.uniform(min(xs) - 0.5 * w, max(xs) + 0.5 * w, 500),
                rng.uniform(min(ys) - 0.5 * h, max(ys) + 0.5 * h, 500),
                strict=True,
            )
        ]
        check_clamp_against_shapely(driver, name, ring, anchor, 20.0, points)
        check_clamp_against_shapely(driver, name, ring, anchor, 0.5 * max(w, h), points[:100])


def test_clamp_to_polygon_square_edges_and_perpendicular_inset(driver):
    pytest.importorskip("shapely")
    from shapely.geometry import Point, Polygon

    shape = Polygon(SQUARE)
    # straight out of an edge with the anchor behind it: exactly inset inside, code 1
    assert poly(driver, SQUARE, (0.0, 0.0), 20.0, [(150.0, 0.0)]) == [(1, 80.0, 0.0)]
    assert poly(driver, SQUARE, (0.0, 0.0), 20.0, [(0.0, -150.0)]) == [(1, 0.0, -80.0)]
    assert poly(driver, SQUARE, (0.0, 30.0), 20.0, [(-100.5, 30.0)]) == [(1, -80.0, 30.0)]
    # the nudge follows the anchor direction, not the edge normal (design §6-2: "toward the character")
    (code, x, y) = poly(driver, SQUARE, (0.0, 0.0), 20.0, [(-100.5, 30.0)])[0]
    assert code == 1 and (x, y) == pytest.approx(
        (-100.0 + 20.0 * 100.0 / math.hypot(100.0, 30.0), 30.0 - 20.0 * 30.0 / math.hypot(100.0, 30.0))
    )
    # inside: unchanged
    assert poly(driver, SQUARE, (0.0, 0.0), 20.0, [(10.0, -20.0)]) == [(0, 10.0, -20.0)]
    # the inset is capped at the distance to the anchor
    (code, x, y) = poly(driver, SQUARE, (90.0, 0.0), 50.0, [(150.0, 0.0)])[0]
    assert code == 1 and (x, y) == pytest.approx((90.0, 0.0))
    # boundary points (edge midpoints and vertices) end up covered by the ring
    boundary = [(100.0, 0.0), (0.0, 100.0), (-100.0, 0.0), (0.0, -100.0), *SQUARE]
    for p, (code, x, y) in zip(boundary, poly(driver, SQUARE, (0.0, 0.0), 20.0, boundary), strict=True):
        assert code in (0, 1), p
        assert shape.covers(Point(x, y)), (p, x, y)
        if code == 1:
            assert shape.contains(Point(x, y)) and abs(math.dist((x, y), p) - 20.0) < 1e-9, p
        else:
            assert (x, y) == p
    # nearest-point ties on the diagonals: the corner is shared by two edges -> the lower edge index
    ties = polyq(driver, SQUARE, [(150.0, 150.0), (150.0, -150.0), (-150.0, 150.0), (-150.0, -150.0)])
    assert [(qx, qy, edge) for _d, qx, qy, edge in ties] == [
        (100.0, 100.0, 1),
        (100.0, -100.0, 0),
        (-100.0, 100.0, 2),
        (-100.0, -100.0, 0),
    ]
    assert all(abs(d - math.hypot(50.0, 50.0)) < 1e-9 for d, *_ in ties)
    # inset 0: Q itself; on the boundary the even-odd test may say either side (code 1 or 2)
    (code, x, y) = poly(driver, SQUARE, (0.0, 0.0), 0.0, [(150.0, 40.0)])[0]
    assert code in (1, 2) and (x, y) == (100.0, 40.0)
    (code, x, y) = poly(driver, SQUARE, (0.0, 0.0), -5.0, [(150.0, 40.0)])[0]  # negative inset == 0
    assert code in (1, 2) and (x, y) == (100.0, 40.0)
    # fewer than three vertices: nothing to clamp against
    assert poly(driver, SQUARE[:2], (0.0, 0.0), 20.0, [(500.0, 500.0)]) == [(0, 500.0, 500.0)]
    assert poly(driver, [], (0.0, 0.0), 20.0, [(500.0, 500.0)]) == [(0, 500.0, 500.0)]


def test_clamp_to_polygon_concave_corner_gives_code_2(driver):
    # L shape, anchor in the vertical arm; a point in the notch is nearest to the notch's bottom edge (tie
    # with the inner vertical edge -> lower index 2) and the nudge toward the anchor stays in the notch:
    # code 2, Out = Q
    anchor = (50.0, 350.0)
    (dist, qx, qy, edge) = polyq(driver, L_SHAPE, [(350.0, 350.0)])[0]
    assert (dist, qx, qy, edge) == (250.0, 350.0, 100.0, 2)
    assert poly(driver, L_SHAPE, anchor, 20.0, [(350.0, 350.0)]) == [(2, 350.0, 100.0)]
    # the same point with a huge inset reaches the anchor's side of the notch: code 1
    (code, x, y) = poly(driver, L_SHAPE, anchor, 1000.0, [(350.0, 350.0)])[0]
    assert code == 1 and (x, y) == pytest.approx(anchor)
    # nearest edge index and point on the star's concave vertices
    pytest.importorskip("shapely")
    from shapely.geometry import Point, Polygon

    star = Polygon(STAR)
    rows = polyq(driver, STAR, [(0.0, 400.0), (0.0, -400.0), (400.0, 400.0)])
    for p, (dist, qx, qy, edge) in zip([(0.0, 400.0), (0.0, -400.0), (400.0, 400.0)], rows, strict=True):
        assert abs(dist - star.exterior.distance(Point(p))) < 1e-9, p
        assert star.exterior.distance(Point(qx, qy)) < 1e-9 and 0 <= edge < len(STAR), p


# -------------------------------------------------------------------------------------------------------- (j)


def ref_nearest(ring, p) -> tuple[float, float, float]:
    """Nearest boundary point with the C++ tie rule (lowest edge index)."""
    best = None
    for j in range(len(ring)):
        ax, ay = ring[j]
        bx, by = ring[(j + 1) % len(ring)]
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        t = ((p[0] - ax) * dx + (p[1] - ay) * dy) / l2 if l2 > 0 else 0.0
        t = min(1.0, max(0.0, t))
        qx, qy = ax + t * dx, ay + t * dy
        d = math.dist(p, (qx, qy))
        if best is None or d < best[0]:
            best = (d, qx, qy)
    assert best is not None
    return best


def ref_constrain(anchor, r, inset, ring, desired, shape) -> tuple[int, np.ndarray | None]:
    """design §6-2 ③ in Python: sphere -> polygon (nudge toward the anchor) -> re-check both, else -1."""
    from shapely.geometry import Point

    a = np.asarray(anchor, dtype=float)
    p = np.asarray(desired, dtype=float).copy()
    code = 0
    d = float(np.linalg.norm(p - a))
    if r <= 0:
        if not np.array_equal(p, a):
            code |= 1
        p = a.copy()
    elif d > r:
        p = a + (p - a) * (r / d)
        code |= 1
    if ring:
        if shape.exterior.distance(Point(p[:2])) < 1e-6:
            return -2, None  # ambiguous for an even-odd test: the caller skips it
        if not shape.contains(Point(p[:2])):
            _d, qx, qy = ref_nearest(ring, (p[0], p[1]))
            to_anchor = math.dist((qx, qy), (a[0], a[1]))
            nudge = min(max(inset, 0.0), to_anchor)
            nx = qx + (a[0] - qx) * nudge / to_anchor if to_anchor > 0 else qx
            ny = qy + (a[1] - qy) * nudge / to_anchor if to_anchor > 0 else qy
            if shape.exterior.distance(Point(nx, ny)) < 1e-6:
                return -2, None
            if not shape.contains(Point(nx, ny)):
                return -1, None
            p[0], p[1] = nx, ny
            code |= 2
    radius = max(r, 0.0)
    dist = float(np.linalg.norm(p - a))
    if abs(dist - radius) < 1e-6 and dist > radius:
        return -2, None
    if dist > radius * (1 + 1e-12) + 1e-9:
        return -1, None
    if ring and not shape.contains(Point(p[:2])):
        return -1, None
    return code, p


def constrain(driver: Path, anchor, r, inset, ring, points) -> list[tuple[int, np.ndarray]]:
    text = f"{nums(*anchor)} {r!r} {inset!r} {ring_text(ring)} {len(points)} "
    text += nums(*(v for p in points for v in p))
    rows = run_lines(driver, "constrain", text)
    assert len(rows) == len(points)
    return [(int(row[0]), np.array(row[1:])) for row in rows]


def test_constrain_combines_sphere_and_polygon(driver):
    pytest.importorskip("shapely")
    from shapely.geometry import Polygon

    sentinel = np.array([-999999.0] * 3)
    anchor = (0.0, 0.0, 90.0)
    r, inset = 300.0, 20.0
    shape = Polygon(SQUARE)
    pts = [
        (10.0, 10.0, 100.0),  # inside both -> 0
        (0.0, 0.0, 500.0),  # above the sphere, XY inside -> 1
        (500.0, 0.0, 90.0),  # sphere clamp to (300, 0) then polygon to (80, 0) -> 3
        (150.0, 0.0, 90.0),  # inside the sphere, outside the polygon -> 2
        (-150.0, 150.0, 90.0),  # corner: nudged along the diagonal -> 2
    ]
    got = constrain(driver, anchor, r, inset, SQUARE, pts)
    assert [c for c, _ in got] == [0, 1, 3, 2, 2]
    assert np.array_equal(got[0][1], pts[0])
    assert np.allclose(got[1][1], [0.0, 0.0, 390.0])
    assert np.allclose(got[2][1], [80.0, 0.0, 90.0])
    assert np.allclose(got[3][1], [80.0, 0.0, 90.0])
    assert np.allclose(got[4][1], [-100.0 + 20.0 / math.sqrt(2), 100.0 - 20.0 / math.sqrt(2), 90.0])
    # no polygon (N = 0): sphere only
    got = constrain(driver, anchor, r, inset, [], [(500.0, 0.0, 90.0), (10.0, 10.0, 90.0)])
    assert got[0][0] == 1 and np.allclose(got[0][1], [300.0, 0.0, 90.0])
    assert got[1][0] == 0 and np.array_equal(got[1][1], [10.0, 10.0, 90.0])
    # polygon nudge that leaves the sphere -> rejected, Out untouched (the driver prints its sentinel)
    notch_anchor = (0.0, 0.0, 0.0)
    got = constrain(driver, notch_anchor, 100.0, 5.0, NOTCHED, [(99.0, 0.0, 0.0), (99.0, 0.5, 0.0)])
    assert [c for c, _ in got] == [-1, -1]
    assert all(np.array_equal(out, sentinel) for _, out in got)
    assert ref_constrain(notch_anchor, 100.0, 5.0, NOTCHED, (99.0, 0.0, 0.0), Polygon(NOTCHED))[0] == -1
    # a concave notch where the nudge stays outside -> rejected (ClampToPolygonXY code 2)
    got = constrain(driver, (50.0, 350.0, 0.0), 1000.0, 20.0, L_SHAPE, [(350.0, 350.0, 0.0)])
    assert got[0][0] == -1 and np.array_equal(got[0][1], sentinel)
    # accepted results always satisfy both constraints; rejected ones match the Python rule
    rng = np.random.default_rng(16)
    for name, ring, ring_anchor in polygon_cases():
        shape = Polygon(ring)
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        for r_cm in (0.35 * max(w, h), 1.5 * max(w, h)):
            a3 = (ring_anchor[0], ring_anchor[1], 100.0)
            points = [
                (float(x), float(y), float(z))
                for x, y, z in zip(
                    rng.uniform(min(xs) - 0.5 * w, max(xs) + 0.5 * w, 150),
                    rng.uniform(min(ys) - 0.5 * h, max(ys) + 0.5 * h, 150),
                    rng.uniform(-200, 400, 150),
                    strict=True,
                )
            ]
            got = constrain(driver, a3, r_cm, inset, ring, points)
            for p, (code, out) in zip(points, got, strict=True):
                ref_code, ref_out = ref_constrain(a3, r_cm, inset, ring, p, shape)
                if ref_code == -2:
                    continue
                assert code == ref_code, (name, r_cm, p, code, ref_code)
                if code == -1:
                    assert np.array_equal(out, sentinel)
                    continue
                assert ref_out is not None and np.allclose(out, ref_out, atol=1e-6), (name, p)
                assert np.linalg.norm(out - a3) <= r_cm * (1 + 1e-12) + 1e-9
                from shapely.geometry import Point

                assert shape.covers(Point(out[0], out[1])), (name, p, out)


# -------------------------------------------------------------------------------------------------------- (k)


def meta_lines(m: dict) -> str:
    lines = [f"version={m['version']}", f"time_utc={m['time_utc']}"]
    lines.append("preset=-" if m["preset"] is None else f"preset={m['preset']}")
    if m["zone_id"] is None:
        lines.append("zone=-")
    else:
        lines += [f"zone_id={m['zone_id']}", f"zone_version={m['zone_version']}"]
    if m["lon"] is None:
        lines.append("geo=-")
    else:
        lines += [f"lon={m['lon']!r}", f"lat={m['lat']!r}", f"height_m={m['height_m']!r}"]
    lines.append("ue_location=" + nums(*m["ue_location"]))
    lines.append("rotation=" + nums(*m["rotation"]))
    lines += [f"fov={m['fov']!r}", f"exposure_ev={m['exposure_ev']!r}"]
    lines += [f"dof_enabled={int(m['dof']['enabled'])}", f"focal_m={m['dof']['focal_m']!r}"]
    lines += [f"fstop={m['dof']['fstop']!r}", f"multiplier={m['multiplier']}"]
    lines.append(f"character_hidden={int(m['character_hidden'])}")
    return "\n".join(lines) + "\n"


def meta(driver: Path, m: dict) -> str:
    res = run_raw(driver, "meta", meta_lines(m))
    assert res.returncode == 0, res.stdout + res.stderr
    return res.stdout.replace("\r\n", "\n")


def assert_meta_layout(text: str) -> dict:
    assert text.startswith("{\n") and text.endswith("\n}\n") and not text.endswith("\n\n")
    lines = text.split("\n")
    assert lines[0] == "{" and lines[-2] == "}" and lines[-1] == ""
    body = lines[1:-2]
    assert len(body) == len(META_KEYS)
    for line, key in zip(body, META_KEYS, strict=True):
        assert line.startswith(f'  "{key}": '), (line, key)
        assert not line.startswith("   "), line
    assert all(line.endswith(",") for line in body[:-1]) and not body[-1].endswith(",")
    assert re.search(r"-0\.0+(?![0-9])", text) is None, text  # never "-0.00": FormatFixed drops the sign
    d = json.loads(text)
    assert list(d) == META_KEYS and list(d["dof"]) == DOF_KEYS
    assert re.search(r'^  "fov": -?\d+\.\d,$', text, re.M), text
    assert re.search(r'^  "exposure_ev": -?\d+\.\d\d,$', text, re.M), text
    assert re.search(
        r'^  "dof": \{"enabled": (true|false), "focal_m": -?\d+\.\d{3}, "fstop": -?\d+\.\d\d\},$', text, re.M
    )
    assert re.search(r'^  "ue_location": \[-?\d+\.\d\d, -?\d+\.\d\d, -?\d+\.\d\d\],$', text, re.M), text
    assert re.search(r'^  "rotation": \[-?\d+\.\d{3}, -?\d+\.\d{3}, -?\d+\.\d{3}\],$', text, re.M), text
    return d


def test_meta_reproduces_the_design_example_byte_for_byte(driver):
    assert meta(driver, EXAMPLE_META) == EXAMPLE_JSON
    assert json.loads(EXAMPLE_JSON) == EXAMPLE_META
    assert_meta_layout(EXAMPLE_JSON)


def test_meta_null_groups(driver):
    for has_preset in (False, True):
        for has_zone in (False, True):
            for has_geo in (False, True):
                m = dict(EXAMPLE_META)
                if not has_preset:
                    m["preset"] = None
                if not has_zone:
                    m["zone_id"] = None
                    m["zone_version"] = None
                if not has_geo:
                    m["lon"] = m["lat"] = m["height_m"] = None
                text = meta(driver, m)
                d = assert_meta_layout(text)
                assert d == m, (has_preset, has_zone, has_geo)
                if not has_preset:
                    assert '\n  "preset": null,\n' in text
                if not has_zone:
                    assert '\n  "zone_id": null,\n  "zone_version": null,\n' in text
                if not has_geo:
                    assert '\n  "lon": null,\n  "lat": null,\n  "height_m": null,\n' in text


def test_meta_escapes_strings_like_the_path_json(driver):
    m = dict(EXAMPLE_META)
    m["preset"] = 'a"b\\c\td\x01e/f'
    m["zone_id"] = "골목 z_한글"  # UTF-8 bytes pass through unescaped
    m["time_utc"] = "2026-09-25T10:11:12Z\x1f"
    text = meta(driver, m)
    d = assert_meta_layout(text)
    assert d == m
    preset_line = [line for line in text.split("\n") if line.startswith('  "preset"')][0]
    assert (
        '\\"' in preset_line and "\\\\" in preset_line and "\\t" in preset_line and "\\u0001" in preset_line
    )
    assert "골목 z_한글" in text and "\\u001f" in text


def random_meta(rng: np.random.Generator) -> dict:
    return {
        "version": 1,
        "time_utc": f"2026-{int(rng.integers(1, 13)):02d}-{int(rng.integers(1, 29)):02d}T10:11:12Z",
        "preset": None if rng.random() < 0.3 else str(rng.choice(["overcast_morning", "clear_noon", "dusk"])),
        "zone_id": "z_synthetic_001",
        "zone_version": int(rng.integers(1, 40)),
        "lon": float(np.round(rng.uniform(-180, 180), 7)),
        "lat": float(np.round(rng.uniform(-90, 90), 7)),
        "height_m": float(np.round(rng.uniform(-100, 3000), 3)),
        "ue_location": [float(v) for v in np.round(rng.uniform(-300000, 300000, 3), 2)],
        "rotation": [float(v) for v in np.round(rng.uniform(-180, 180, 3), 3)],
        "fov": float(np.round(rng.uniform(20, 110), 1)),
        "exposure_ev": float(np.round(rng.uniform(-3, 3), 2)),
        "dof": {
            "enabled": bool(rng.random() < 0.5),
            "focal_m": float(np.round(rng.uniform(0.3, 50), 3)),
            "fstop": float(rng.choice(FSTOP_VALUES)),
        },
        "multiplier": int(rng.integers(1, 9)),
        "character_hidden": bool(rng.random() < 0.5),
    }


def test_meta_round_trips_random_values(driver):
    rng = np.random.default_rng(17)
    for _ in range(40):
        m = random_meta(rng)
        d = assert_meta_layout(meta(driver, m))
        for key in META_KEYS:
            if key == "dof":
                assert d["dof"]["enabled"] is m["dof"]["enabled"]
                assert d["dof"]["focal_m"] == pytest.approx(m["dof"]["focal_m"], abs=1e-6)
                assert d["dof"]["fstop"] == pytest.approx(m["dof"]["fstop"], abs=1e-6)
            elif isinstance(m[key], list):
                assert d[key] == pytest.approx(m[key], abs=1e-6), key
            elif isinstance(m[key], float):
                assert d[key] == pytest.approx(m[key], abs=1e-6), key
            else:
                assert d[key] == m[key], key
        for key in ("version", "zone_version", "multiplier"):
            assert isinstance(d[key], int)
        assert isinstance(d["character_hidden"], bool) and isinstance(d["dof"]["enabled"], bool)
    # values that round to zero never print a minus sign; unrounded inputs are rounded half away from zero
    m = dict(EXAMPLE_META)
    m["exposure_ev"] = -0.004
    m["rotation"] = [-0.0004, -0.0, 0.0]
    m["ue_location"] = [-0.004, 0.005, -0.005]
    m["fov"] = 64.96
    m["dof"] = {"enabled": True, "focal_m": 2.9995, "fstop": 2.805}
    text = meta(driver, m)
    d = assert_meta_layout(text)
    assert d["exposure_ev"] == 0.0 and d["rotation"] == [0.0, 0.0, 0.0]
    assert d["ue_location"] == [0.0, 0.01, -0.01] and d["fov"] == 65.0
    assert d["dof"] == {"enabled": True, "focal_m": 3.0, "fstop": 2.81}
    assert '"exposure_ev": 0.00,' in text and '"rotation": [0.000, 0.000, 0.000],' in text
