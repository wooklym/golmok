"""Production audio math, independently exercised in g++ CI."""

import random
import shutil
import subprocess
import sys
from pathlib import Path

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
    assert [v[0] for v in values] == pytest.approx([0.25, 0.25, 0.125, 0, 1])


def test_surface_priority(driver):
    values = run(driver, ["surface 0 0", "surface 1 0", "surface 0 1", "surface 1 1"])
    assert [v[0] for v in values] == [0, 1, 2, 2]
