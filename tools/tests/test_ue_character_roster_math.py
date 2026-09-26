"""Compile the production math header; compare dimensions and fixed-foot resizing with WP-18."""

from __future__ import annotations

import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from zone_util import REPO

HEADER = REPO / "unreal/Golmok/Source/Golmok/Characters/GolmokCharacterMath.h"
DRIVER = Path(__file__).parent / "fixtures/ue/charactermath_driver.cpp"


def test_header_is_pure():
    text = HEADER.read_text(encoding="utf-8")
    assert text.lstrip().startswith("#pragma once")
    assert re.findall(r'^#include\s+"', text, re.M) == []
    assert set(re.findall(r"^#include\s+<([^>]+)>", text, re.M)) <= {"array", "cmath"}
    for banned in ("CoreMinimal", "UCLASS", "UE_LOG", "std::min", "std::max", "printf", "cstdio"):
        assert banned not in text
    assert "namespace GolmokCharacterMath" in text
    assert re.search(r"^\s*(?:PI|check)\b", text, re.M) is None


@pytest.fixture(scope="module")
def driver(tmp_path_factory):
    compiler = next((p for n in ("g++", "clang++", "c++") if (p := shutil.which(n))), None)
    if not compiler:
        pytest.skip("no C++ compiler (g++/clang++) on PATH")
    exe = tmp_path_factory.mktemp("charactermath") / ("driver.exe" if sys.platform == "win32" else "driver")
    res = subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            f"-I{HEADER.parent}",
            str(DRIVER),
            "-o",
            str(exe),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert not res.stderr.strip(), res.stderr
    return exe


def run(driver, lines):
    res = subprocess.run(
        [str(driver)],
        input="\n".join(lines) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return [[float(v) for v in line.split()] for line in res.stdout.splitlines()]


def reference(height, width):
    s = height / 180
    return [
        1,
        height,
        42 * s * width,
        92 * s,
        0,
        0,
        -92 * s,
        s * width,
        s * width,
        s,
        -90,
        80 + 240 * s,
        0,
        5 + 40 * s,
        15 + 40 * s,
        60 + 20 * s,
        180,
        500,
    ]


def test_spec_examples_and_random_dimensions(driver):
    rng = random.Random(18)
    inputs = [(180, 1), (135, 0.8 / 0.75), (110, 0.8 / (110 / 180))]
    inputs += [(rng.uniform(90, 210), rng.uniform(0.8, 1.1)) for _ in range(1000)]
    results = run(driver, [f"calculate {h:.17g} {w:.17g}" for h, w in inputs])
    assert len(results) == len(inputs)
    for (h, w), got in zip(inputs, results, strict=True):
        assert got == pytest.approx(reference(h, w), rel=1e-12, abs=1e-10)


def test_bad_dimensions_leave_output_unchanged(driver):
    # The nominal input range also has coupled radius constraints at its corners.
    pairs = [(79.9, 1), (220.1, 1), (180, 0.749), (180, 1.351), (220, 1.35), (80, 0.75)]
    results = run(driver, [f"calculate {h} {w}" for h, w in pairs])
    for got in results:
        assert got == pytest.approx([0, *reference(180, 1)[1:]])
    assert run(driver, ["invalid"]) == [[1]]


def test_capsule_resize_keeps_feet_in_world_space(driver):
    rng = random.Random(11)
    cases = [(rng.uniform(-1e6, 1e6), rng.uniform(40, 120), rng.uniform(40, 120)) for _ in range(2000)]
    results = run(driver, [f"feet {z:.17g} {old:.17g} {new:.17g}" for z, old, new in cases])
    for (z, old, new), (got,) in zip(cases, results, strict=True):
        assert got - new == pytest.approx(z - old, rel=1e-12, abs=1e-8)
