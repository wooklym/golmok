"""WP-14a: Lighting/GolmokClockMath.h compiled with g++ and checked against tables and a Python reference.

The header is the only home of the clock rules AGolmokTimeOfDay uses (design sections 1-3): wrap, HH:MM,
keyframe search across midnight, shortest-arc yaw, the per-field interpolation rule, sun visibility and night.
"""

from __future__ import annotations

import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HEADER_DIR = ROOT / "unreal/Golmok/Source/Golmok/Lighting"
HEADER = HEADER_DIR / "GolmokClockMath.h"
DRIVER = Path(__file__).parent / "fixtures/ue/clockmath_driver.cpp"
sys.path.insert(0, str(ROOT / "unreal" / "Golmok" / "Content" / "Python"))
from golmok import lighting_presets as lp  # noqa: E402

# The shipped keyframes (lighting_presets.json schema 2): 07:30, 12:30, 18:00, 21:30.
TIMES = [450.0, 750.0, 1080.0, 1290.0]
# pitch yaw lux kelvin sky fog fog_height_falloff exposure_bias volumetric (lighting_presets.json values)
KEYS = {
    "overcast_morning": (-35.0, 110.0, 2.5, 6500.0, 1.4, 0.035, 0.15, 0.3, 0),
    "clear_noon": (-62.0, 180.0, 10.0, 5600.0, 1.0, 0.015, 0.2, 0.0, 0),
    "golden_evening": (-8.0, 265.0, 4.0, 3600.0, 0.8, 0.05, 0.12, 0.5, 1),
    "night": (15.0, 0.0, 0.0, 4000.0, 0.15, 0.03, 0.2, 1.5, 1),
}


@pytest.fixture(scope="module")
def driver(tmp_path_factory):
    compiler = next((p for name in ("g++", "clang++", "c++") if (p := shutil.which(name))), None)
    if not compiler:
        pytest.skip("no g++/clang++ on PATH")
    output = tmp_path_factory.mktemp("clockmath") / ("driver.exe" if sys.platform == "win32" else "driver")
    result = subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-Wshadow",
            f"-I{HEADER_DIR}",
            str(DRIVER),
            "-o",
            str(output),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0 and not result.stderr.strip(), result.stdout + result.stderr
    return output


def run(driver, commands: list[str]) -> list[list[str]]:
    result = subprocess.run(
        [str(driver)],
        input="\n".join(commands) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    lines = [line.split() for line in result.stdout.splitlines()]
    assert len(lines) == len(commands)
    return lines


def floats(driver, commands: list[str]) -> list[float]:
    return [float(v[0]) for v in run(driver, commands)]


# ---- Python reference (independent of the header) -------------------------------------------------------


def ref_wrap(m: float) -> float:
    if not math.isfinite(m):
        return 0.0
    r = math.fmod(m, 1440.0)
    if r < 0:
        r += 1440.0
    return 0.0 if r >= 1440.0 else r


def ref_find(t: float, times: list[float]) -> tuple[int, int, float]:
    t = ref_wrap(t)
    n = len(times)
    if n == 1:
        return 0, 0, 0.0
    below = [i for i, k in enumerate(times) if k <= t]
    prev = below[-1] if below else n - 1
    nxt = (prev + 1) % n
    width = (times[nxt] - times[prev]) % 1440.0
    elapsed = (t - times[prev]) % 1440.0
    return prev, nxt, min(max(elapsed / width, 0.0), 1.0)


def ref_yaw(a: float, b: float, alpha: float) -> float:
    d = (b - a) % 360.0
    if d > 180.0:
        d -= 360.0
    return (a + d * alpha) % 360.0


def key_args(name: str) -> str:
    return " ".join(f"{v:.17g}" for v in KEYS[name])


# ---- tables ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [
        (0, 0),
        (1439.5, 1439.5),
        (1440, 0),
        (1500, 60),
        (-30, 1410),
        (-1440, 0),
        (2 * 1440 + 5, 5),
        (-1e-17, 0),
    ],
)
def test_wrap_minutes(driver, minutes, expected):
    assert floats(driver, [f"wrap {minutes!r}"]) == [pytest.approx(expected, abs=1e-9)]


def test_wrap_non_finite_is_zero(driver):
    assert floats(driver, ["wrap nan", "wrap inf", "wrap -inf"]) == [0.0, 0.0, 0.0]


@pytest.mark.parametrize(
    ("text", "ok", "minutes"),
    [
        ("00:00", 1, 0),
        ("07:30", 1, 450),
        ("12:30", 1, 750),
        ("18:00", 1, 1080),
        ("21:30", 1, 1290),
        ("23:59", 1, 1439),
        ("24:00", 0, 0),
        ("12:60", 0, 0),
        ("7:30", 0, 0),
        ("07:3", 0, 0),
        ("07:300", 0, 0),
        ("0730", 0, 0),
        ("07-30", 0, 0),
        ("ab:cd", 0, 0),
        ("<empty>", 0, 0),
        ("+7:30", 0, 0),
    ],
)
def test_parse_hhmm_table_matches_python(driver, text, ok, minutes):
    (row,) = run(driver, [f"parse {text}"])
    assert row == [str(ok), str(minutes), str(ok), str(minutes)]  # char and wchar_t agree
    py = text if text != "<empty>" else ""
    if ok:
        assert lp.parse_hhmm(py) == minutes
    else:
        with pytest.raises(ValueError):
            lp.parse_hhmm(py)


@pytest.mark.parametrize("text", ["07:30\n", "07:30 ", " 07:30", "07:30\r"])
def test_python_parse_hhmm_rejects_what_cpp_rejects(driver, text):
    # C++ ParseHHMM needs the terminator right after MM; Python must not accept more (single source).
    with pytest.raises(ValueError):
        lp.parse_hhmm(text)


@pytest.mark.parametrize(
    ("minutes", "text"),
    [
        (0, "00:00"),
        (450, "07:30"),
        (749.999, "12:29"),
        (750, "12:30"),
        (1439.99, "23:59"),
        (1440, "00:00"),
        (-1, "23:59"),
    ],
)
def test_format_hhmm_floors_and_wraps(driver, minutes, text):
    assert run(driver, [f"format {minutes!r}"]) == [[text]]
    assert lp.format_hhmm(minutes) == text


def test_advance_and_rate(driver):
    got = floats(
        driver,
        [
            "advance 600 0.5 1",
            "advance 1435 10 1",
            "advance 600 10 -1",
            "advance 600 inf 1",
            "advance 600 0.5 0",
        ],
    )
    assert got == [pytest.approx(600.5), pytest.approx(5.0), 600.0, 600.0, 600.0]
    assert [
        int(v)
        for v in floats(driver, ["rate 0.5", "rate 1440", "rate 0", "rate -1", "rate 1441", "rate nan"])
    ] == [
        1,
        1,
        0,
        0,
        0,
        0,
    ]


def _times_arg(times: list[float]) -> str:
    return f"{len(times)} " + " ".join(f"{t!r}" for t in times)


@pytest.mark.parametrize(
    ("minutes", "prev", "nxt", "alpha", "nearest"),
    [
        (450, 0, 1, 0.0, 0),  # keyframe time: alpha 0, prev = that keyframe
        (750, 1, 2, 0.0, 1),
        (1080, 2, 3, 0.0, 2),
        (1290, 3, 0, 0.0, 3),
        (540, 0, 1, 0.3, 0),
        (600, 0, 1, 0.5, 1),  # midpoint: nearest turns to next
        (599.999, 0, 1, 149.999 / 300, 0),
        (1185, 2, 3, 0.5, 3),
        (1380, 3, 0, 90 / 600, 3),  # 23:00 before midnight
        (0, 3, 0, 150 / 600, 3),  # midnight
        (30, 3, 0, 180 / 600, 3),  # 00:30 after midnight
        (449.999, 3, 0, 599.999 / 600, 0),
        (1590, 3, 0, 300 / 600, 0),  # 1590 wraps to 02:30 = the night -> morning midpoint
    ],
)
def test_find_keyframes_table(driver, minutes, prev, nxt, alpha, nearest):
    (row,) = run(driver, [f"find {minutes!r} {_times_arg(TIMES)}"])
    assert (int(row[0]), int(row[1])) == (prev, nxt)
    assert float(row[2]) == pytest.approx(alpha, abs=1e-12)
    assert int(row[3]) == nearest


def test_find_keyframes_degenerate(driver):
    rows = run(driver, ["find 100 0", "find 100 1 450", "find 1000 2 0 720", "find 0 2 0 720"])
    assert rows[0][:2] == ["-1", "-1"] and rows[0][3] == "-1"
    assert rows[1][:3] == ["0", "0", "0"]
    assert rows[2][:2] == ["1", "0"] and float(rows[2][2]) == pytest.approx(280 / 720)
    assert rows[3][:3] == ["0", "1", "0"]


def test_find_keyframes_random_against_python(driver):
    rng = random.Random(14)
    cases = []
    for _ in range(400):
        n = rng.randint(2, 6)
        times = sorted(rng.sample(range(0, 1440), n))
        cases.append((rng.uniform(-3000, 4000), [float(t) for t in times]))
    rows = run(driver, [f"find {m!r} {_times_arg(t)}" for m, t in cases])
    for (m, times), row in zip(cases, rows, strict=True):
        prev, nxt, alpha = ref_find(m, times)
        assert (int(row[0]), int(row[1])) == (prev, nxt), (m, times)
        assert float(row[2]) == pytest.approx(alpha, abs=1e-9), (m, times)
        assert int(row[3]) == (prev if alpha < 0.5 else nxt)


@pytest.mark.parametrize(
    ("a", "b", "alpha", "expected"),
    [
        (350, 10, 0.5, 0.0),  # shortest arc passes 0, never 180
        (350, 10, 0.25, 355.0),
        (350, 10, 0.75, 5.0),
        (10, 350, 0.5, 0.0),
        (265, 0, 0.5, 312.5),  # golden_evening -> night
        (0, 110, 0.3, 33.0),  # night -> overcast_morning
        (110, 180, 0.0, 110.0),  # alpha 0 -> exactly A
        (110, 180, 1.0, 180.0),  # alpha 1 -> exactly B
        (0, 180, 0.5, 90.0),  # 180 tie turns positive
        (180, 0, 0.5, 270.0),
    ],
)
def test_lerp_yaw_shortest(driver, a, b, alpha, expected):
    (got,) = floats(driver, [f"yaw {a} {b} {alpha}"])
    assert got == pytest.approx(expected, abs=1e-9)
    assert 0.0 <= got < 360.0
    assert ref_yaw(a, b, alpha) == pytest.approx(expected, abs=1e-9)


def test_lerp_yaw_random_against_python(driver):
    rng = random.Random(1440)
    cases = [(rng.uniform(0, 360), rng.uniform(0, 360), rng.random()) for _ in range(500)]
    got = floats(driver, [f"yaw {a!r} {b!r} {t!r}" for a, b, t in cases])
    for (a, b, t), g in zip(cases, got, strict=True):
        want = ref_yaw(a, b, t)
        assert min(abs(g - want), 360 - abs(g - want)) < 1e-9, (a, b, t)


@pytest.mark.parametrize(
    ("a", "b", "alpha"),
    [
        ("overcast_morning", "clear_noon", 0.0),
        ("overcast_morning", "clear_noon", 0.3),
        ("clear_noon", "golden_evening", 0.4999),
        ("clear_noon", "golden_evening", 0.5),
        ("golden_evening", "night", 0.5),
        ("night", "overcast_morning", 0.3),
        ("night", "overcast_morning", 1.0),
    ],
)
def test_interpolate_rule(driver, a, b, alpha):
    (row,) = run(driver, [f"interp {key_args(a)} {key_args(b)} {alpha!r}"])
    got = [float(v) for v in row]
    ka, kb = KEYS[a], KEYS[b]
    for i in (0, 2, 3, 4, 5, 6, 7):  # linear fields
        assert got[i] == pytest.approx(ka[i] + (kb[i] - ka[i]) * alpha, abs=1e-12), i
    assert got[1] == pytest.approx(ref_yaw(ka[1], kb[1], alpha) % 360.0, abs=1e-9)
    assert int(got[8]) == (ka[8] if alpha < 0.5 else kb[8])
    if alpha == 0.0:
        assert got[:8] == [float(v) for v in ka[:8]]  # a keyframe time reproduces the preset exactly


def test_sun_visibility_and_night(driver):
    rows = run(
        driver,
        ["sun 0", "sun 0.01", "sun 0.0100001", "sun 2.5", "night 0.0999 0.1", "night 0.1 0.1", "night 4 0.1"],
    )
    assert [int(r[0]) for r in rows] == [0, 0, 1, 1, 1, 0, 0]


def test_night_boundary_on_the_shipped_keyframes(driver):
    # golden_evening (lux 4, 18:00) -> night (lux 0, 21:30): lux < 0.1 from alpha 0.975 = 21:24:45 on.
    rows = run(
        driver,
        [
            f"interp {key_args('golden_evening')} {key_args('night')} {(t - 1080) / 210!r}"
            for t in (1284.0, 1285.0)
        ],
    )
    assert float(rows[0][2]) > 0.1 > float(rows[1][2])


def test_check_keyframe_order(driver):
    rows = run(
        driver,
        ["order 4 450 750 1080 1290", "order 3 450 450 900", "order 3 450 900 800", "order 1 5", "order 0"],
    )
    assert rows == [["0", "-1"], ["1", "1"], ["2", "2"], ["0", "-1"], ["0", "-1"]]


def test_header_is_pure():
    text = HEADER.read_text(encoding="utf-8")
    includes = [line for line in text.splitlines() if line.startswith("#include")]
    assert includes == ["#include <cmath>"], includes
    assert "namespace GolmokClockMath" in text
