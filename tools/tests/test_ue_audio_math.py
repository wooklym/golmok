"""Production audio math, independently exercised in g++ CI."""

import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "unreal/Golmok/Source/Golmok/Audio"
DRIVER = Path(__file__).parent / "fixtures/ue/audiomath_driver.cpp"


@pytest.fixture(scope="module")
def driver(tmp_path_factory):
    compiler = next((p for name in ("g++", "clang++", "c++") if (p := shutil.which(name))), None)
    if not compiler:
        pytest.skip("no g++/clang++ on PATH")
    output = tmp_path_factory.mktemp("audiomath") / ("driver.exe" if sys.platform == "win32" else "driver")
    result = subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            f"-I{HEADER}",
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


def run(driver, commands):
    result = subprocess.run(
        [str(driver)],
        input="\n".join(commands) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return [list(map(float, line.split())) for line in result.stdout.splitlines()]


def test_frame_partition_preserves_distance(driver):
    rng = random.Random(13)
    distances = [rng.uniform(0, 8) for _ in range(1000)]
    values = run(driver, ["step 0 1 1 70 300"] + [f"step {d:.17g} 1 1 70 300" for d in distances])
    assert sum(v[0] for v in values) == int(sum(distances) // 70)
    assert values[-1][2] == pytest.approx(sum(distances) % 70, abs=1e-9)


def test_air_landing_and_teleport_reset(driver):
    values = run(
        driver,
        [
            "step 0 1 1 70 300",
            "step 69 1 1 70 300",
            "step 50 0 1 70 300",
            "step 50 0 1 70 300",
            "step 1 1 1 70 300",
            "step 1 1 1 70 300",
            "step 500 1 1 70 300",
            "step 0 1 1 70 300",
            "step 70 1 1 70 300",
        ],
    )
    assert [v[0] for v in values] == [0, 0, 0, 0, 0, 0, 0, 0, 1]
    assert [v[1] for v in values] == [0, 0, 0, 0, 1, 0, 0, 0, 0]


def test_retarget_continuity_and_endpoints(driver):
    values = run(
        driver,
        [
            "target 1 2",
            "advance .5",
            "target 0 1",
            "advance 0",
            "advance .5",
            "advance 9",
            "target 1 0",
            "advance 0",
        ],
    )
    assert [v[0] for v in values] == pytest.approx(
        [math.sin(math.pi / 8), math.sin(math.pi / 8), math.sin(math.pi / 8) / math.sqrt(2), 0, 1]
    )


def test_surface_priority(driver):
    values = run(driver, ["surface 0 0", "surface 1 0", "surface 0 1", "surface 1 1"])
    assert [v[0] for v in values] == [0, 1, 2, 2]


def test_complementary_power_and_interrupted_reversal(driver):
    incoming = run(driver, ["target 1 2", "advance .5", "target 0 1", "advance .25"])
    outgoing = run(driver, ["target 1 0", "target 0 2", "advance .5", "target 1 1", "advance .25"])
    for first, second in zip(incoming, outgoing, strict=True):
        assert first[0] ** 2 + second[0] ** 2 == pytest.approx(1)


def test_third_clip_replacement_reaches_zero_in_50ms(driver):
    values = run(
        driver,
        [
            "target 1 2",
            "advance .5",
            "target 0 .05",
            "advance 0",
            "advance .025",
            "advance .025",
            "target 1 1",
            "advance 0",
            "advance .25",
        ],
    )
    assert [v[0] for v in values] == pytest.approx(
        [
            math.sin(math.pi / 8),
            math.sin(math.pi / 8),
            math.sin(math.pi / 8) / math.sqrt(2),
            0,
            0,
            math.sin(math.pi / 8),
        ]
    )


def test_photo_amplitude_s_curve_and_retarget(driver):
    values = run(
        driver,
        [
            "photo_target 1 .25",
            "photo_advance .0625",
            "photo_target 0 .25",
            "photo_advance 0",
            "photo_advance .125",
            "photo_advance 1",
        ],
    )
    quarter = (1 - math.cos(math.pi / 4)) / 2
    assert [v[0] for v in values] == pytest.approx([quarter, quarter, quarter / 2, 0])


def test_sin_cos_endpoints_at_60fps(driver):
    incoming = run(driver, ["target 1 1", "advance 0", "advance .016666666666666666", "advance 1"])
    outgoing = run(
        driver, ["target 1 0", "target 0 1", "advance 0", "advance .016666666666666666", "advance 1"]
    )
    assert [v[0] for v in incoming] == pytest.approx([0, math.sin(math.pi / 120), 1])
    assert [v[0] for v in outgoing] == pytest.approx([1, math.cos(math.pi / 120), 0])


def rain_gain_mirror(curve, intensity):
    if not math.isfinite(intensity) or intensity <= 0 or len(curve) < 2:
        return 0
    for (x0, y0), (x1, y1) in zip(curve, curve[1:], strict=False):
        if intensity <= x1:
            return y0 + (y1 - y0) * (intensity - x0) / (x1 - x0)
    return curve[-1][1]


def test_rain_curve_cpp_mirror(driver):
    rng = random.Random(28)
    commands, expected = [], []
    for _ in range(40):
        size = rng.randint(2, 32)
        xs = [0, *sorted(rng.uniform(0.001, 0.999) for _ in range(size - 2)), 1]
        ys = [0, *sorted(rng.random() for _ in range(size - 1))]
        curve = list(zip(xs, ys, strict=True))
        points = " ".join(f"{x:.17g} {y:.17g}" for x, y in curve)
        for intensity in [-1, 0, 1, 2, float("nan"), float("inf"), *xs, rng.random()]:
            commands.append(f"rain {size} {intensity:.17g} {points}")
            expected.append(rain_gain_mirror(curve, intensity))
    commands += ["rain 0 .5", "rain 1 .5 0 0.7"]
    expected += [0, 0]
    assert [row[0] for row in run(driver, commands)] == pytest.approx(expected, abs=1e-12)


def should_send_volume_mirror(current, target):
    # Match the float32 component property and subtraction, not Python double.
    current, target = np.float32(current), np.float32(target)
    if target == 0:
        return current != 0
    return abs(current - target) >= np.float32(1e-4)


def volume_cases():
    threshold = np.float32(1e-4)
    below = np.nextafter(threshold, np.float32(0))
    above = np.nextafter(threshold, np.float32(1))
    return [
        (0, 0, False),
        (0, -0.0, False),
        (0, below, False),
        (0, threshold, True),
        (0, above, True),
        (below, 0, True),
        (threshold, 0, True),
        (above, 0, True),
        (np.finfo(np.float32).tiny, 0, True),
        (1, 1, False),
        (1, 0, True),
        (0, 1, True),
        (np.nextafter(np.float32(1), np.float32(0)), 1, False),
        (0.99995, 1, False),
        (0.9998, 1, True),
        (1, 0.99995, False),
        (1, 0.9998, True),
    ]


def test_volume_mirror_boundaries():
    for current, target, expected in volume_cases():
        assert should_send_volume_mirror(current, target) == expected


def test_volume_cpp_mirror(driver):
    cases = volume_cases()
    rng = random.Random(29)
    cases += [
        (c, t, should_send_volume_mirror(c, t))
        for c, t in ((rng.random(), rng.choice([0, 1, rng.random()])) for _ in range(500))
    ]
    assert [row[0] for row in run(driver, [f"volume {c:.17g} {t:.17g}" for c, t, _ in cases])] == [
        expected for _, _, expected in cases
    ]
