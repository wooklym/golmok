"""Cross-check unreal/.../Debug/GolmokStatsMath.h (pure C++) against numpy and a Python reference (§8-2).

The header has no Unreal dependency, so it is compiled with g++ (fixtures/ue/statsmath_driver.cpp) into a
small command-line driver: percentile (numpy 'linear'), the HUD window statistics (same window rule as the
design and the same formulas as golmok_tools.perf_report), the ring buffer, fixed-decimal formatting, the
camera-path JSON writer/reader and the pose interpolation. Skipped when no C++ compiler is on PATH.
"""

from __future__ import annotations

import json
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from zone_util import REPO

HEADER = REPO / "unreal" / "Golmok" / "Source" / "Golmok" / "Debug" / "GolmokStatsMath.h"
DRIVER_SRC = Path(__file__).parent / "fixtures" / "ue" / "statsmath_driver.cpp"
ALLOWED_INCLUDES = {"algorithm", "array", "cmath", "cstddef", "cstdint", "string", "vector"}
PATH_KEYS = ["version", "name", "level", "hz", "created", "samples"]
SAMPLE_KEYS = ["t", "p", "r"]
# docs/plan/WP-05 §4-4: the exact file layout
EXAMPLE_JSON = (
    '{"version": 1, "name": "walk_01", "level": "L_ZoneTest", "hz": 10, "created": "2026-09-25T10:11:12Z", '
    '"samples": [\n'
    '{"t": 0.000, "p": [17670.59, -22698.00, 1190.00], "r": [-5.000, 90.000, 0.000]},\n'
    '{"t": 0.100, "p": [17670.59, -22690.12, 1190.00], "r": [-5.000, 90.000, 0.000]}\n'
    "]}\n"
)


def _compiler() -> list[str] | None:
    for name in ("g++", "clang++", "c++"):
        exe = shutil.which(name)
        if exe:
            return [exe, "-std=c++17", "-O1", "-Wall", "-Wextra", "-Werror", "-pedantic"]
    return None


@pytest.fixture(scope="module")
def driver(tmp_path_factory) -> Path:
    cxx = _compiler()
    if cxx is None:
        pytest.skip("no C++ compiler (g++/clang++) on PATH")
    build = tmp_path_factory.mktemp("statsmath")
    exe = build / ("driver.exe" if sys.platform == "win32" else "driver")
    cmd = [*cxx, f"-I{HEADER.parent}", str(DRIVER_SRC), "-o", str(exe)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"compile failed:\n{' '.join(cmd)}\n{res.stdout}\n{res.stderr}"
    return exe


def run_raw(driver: Path, *args, stdin: str = "") -> subprocess.CompletedProcess:
    # encoding= on both pipes: Windows would otherwise use cp1252 (test_pathfmt_escapes_strings sends UTF-8)
    return subprocess.run(
        [str(driver), *(str(a) for a in args)], input=stdin, capture_output=True, text=True, encoding="utf-8"
    )


def run(driver: Path, *args, stdin: str = "") -> list[float]:
    res = run_raw(driver, *args, stdin=stdin)
    assert res.returncode == 0, res.stdout + res.stderr
    return [float(v) for v in res.stdout.split()]


def run_numbers(driver: Path, cmd: str, a, n: int, values) -> list[float]:
    """pct / stats / ring with the numbers piped through stdin (a Windows command line holds only 32 KiB)."""
    return run(driver, cmd, a, n, stdin=" ".join(repr(float(v)) for v in values))


def close(a, b, tol: float = 1e-9) -> bool:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return bool(np.all(np.abs(a - b) <= tol * np.maximum(1.0, np.abs(b))))


# -------------------------------------------------------------------------------------------------------- (a)


def assert_pure_header(header: Path) -> None:
    """Debug/GolmokStatsMath.h purity (shared with test_ue_wp05_fixture.py)."""
    text = header.read_text(encoding="utf-8")
    assert text.lstrip().startswith("#pragma once")
    assert re.findall(r'^#include\s+"', text, re.M) == []
    assert set(re.findall(r"^#include\s+<([^>]+)>", text, re.M)) <= ALLOWED_INCLUDES
    for banned in ("CoreMinimal", "UCLASS", "UE_LOG", "std::min", "std::max", "printf", "cstdio"):
        assert banned not in text, banned
    assert "namespace GolmokStatsMath" in text
    assert re.search(r"^\s*(?:PI|check)\b", text, re.M) is None


def test_header_is_pure():
    assert_pure_header(HEADER)


# -------------------------------------------------------------------------------------------------------- (b)


def test_percentile_matches_numpy_linear(driver):
    rng = np.random.default_rng(11)
    for _ in range(50):
        n = int(rng.integers(1, 120))
        values = rng.uniform(-50, 500, n)
        if rng.random() < 0.3:  # duplicates
            values = np.round(values, 0)
        for p in (0.0, 1.0, 50.0, 99.0, 100.0, float(rng.uniform(0, 100))):
            (got,) = run_numbers(driver, "pct", repr(p), n, values)
            assert close(got, np.percentile(values, p)), (n, p)
    # edge cases: n = 1, n = 2, all equal
    assert run(driver, "pct", 1, 1, 42.5) == [42.5]
    assert run(driver, "pct", 99, 1, 42.5) == [42.5]
    for p in (0, 1, 25, 50, 99, 100):
        (got,) = run(driver, "pct", p, 2, 10.0, 30.0)
        assert close(got, np.percentile([10.0, 30.0], p))
    assert run(driver, "pct", 37, 5, 7, 7, 7, 7, 7) == [7.0]
    assert run(driver, "pct", 50, 0) == [0.0]


# -------------------------------------------------------------------------------------------------------- (c)


Sample = tuple[float, float, float, float]


def ref_stats(samples: list[Sample], window: float, capacity: int = 2048) -> dict | None:
    """Python reference, design window rule: newest first, first sample always, DtSec <= 0 skipped."""
    kept: list[Sample] = []
    acc = 0.0
    for dt, game, render, gpu in reversed(samples[-capacity:]):
        if not dt > 0:
            continue
        if kept and acc + dt > window:
            break
        kept.append((dt, game, render, gpu))
        acc += dt
    if not kept:
        return None
    arr = np.array(kept)
    dts = arr[:, 0]
    return {
        "frames": len(kept),
        "avg_fps": len(kept) / acc,
        "one_pct_low": float(np.percentile(1.0 / dts, 1)),
        "avg_frame_ms": float(np.mean(1000.0 * dts)),
        "p99_ms": float(np.percentile(1000.0 * dts, 99)),
        "game": float(np.mean(arr[:, 1])),
        "render": float(np.mean(arr[:, 2])),
        "gpu": float(np.mean(arr[:, 3])),
        "has_gpu": bool(np.any(arr[:, 3] > 0)),
    }


def stats_values(samples) -> list[float]:
    return [float(v) for s in samples for v in s]


def assert_stats(driver, samples, window):
    got = run_numbers(driver, "stats", repr(window), len(samples), stats_values(samples))
    ref = ref_stats(samples, window)
    if ref is None:
        assert got == [0.0] * 9
        return
    keys = ["frames", "avg_fps", "one_pct_low", "avg_frame_ms", "p99_ms", "game", "render", "gpu"]
    for value, key in zip(got[:8], keys, strict=True):
        assert close(value, ref[key]), (key, value, ref[key], window)
    assert got[8] == (1.0 if ref["has_gpu"] else 0.0)


def test_stats_match_python_reference_over_windows(driver):
    rng = np.random.default_rng(5)
    for case in range(30):
        n = int(rng.integers(60, 500))
        dt = rng.uniform(0.006, 0.040, n)
        for i in rng.choice(n, size=int(rng.integers(1, 5)), replace=False):
            dt[i] = 0.2  # hitches
        game = rng.uniform(1, 8, n)
        render = rng.uniform(2, 12, n)
        gpu = rng.uniform(3, 15, n) if case % 4 else np.zeros(n)
        samples = list(zip(dt, game, render, gpu, strict=True))
        for window in (0.5, 2.0, 10.0):
            assert_stats(driver, samples, window)


def test_stats_skip_nonpositive_dt_and_respect_capacity(driver):
    samples = [(0.0, 1, 1, 1), (-0.01, 1, 1, 1), (0.02, 3, 4, 0), (0.0, 9, 9, 9), (0.01, 5, 6, 0)]
    assert_stats(driver, samples, 2.0)
    assert_stats(driver, [(0.0, 1, 1, 1)] * 5, 2.0)  # nothing usable -> zero stats
    assert run(driver, "stats", 2.0, 0) == [0.0] * 9
    # the first usable sample is always used even when it alone exceeds the window
    assert_stats(driver, [(0.5, 1, 2, 3), (3.0, 1, 2, 3)], 2.0)
    # more samples than the ring holds: only the newest 2048 remain
    rng = np.random.default_rng(9)
    dt = rng.uniform(0.005, 0.02, 3000)
    samples = list(zip(dt, dt * 100, dt * 200, dt * 300, strict=True))
    assert_stats(driver, samples, 100.0)


def test_perf_report_hitch_array_gives_one_percent_low_30(driver):
    # test_perf_report.py: 10 s at 60 fps with ten 33 ms frames -> 1% low ~30 fps, average ~59 fps
    frames_ms = [16.667] * 590 + [33.333] * 10
    samples = [(f / 1000.0, 4.0, 5.0, 12.0) for f in frames_ms]
    got = run_numbers(driver, "stats", 20.0, len(samples), stats_values(samples))
    frames, avg_fps, one_pct, avg_ms, p99, game, render, gpu, has_gpu = got
    assert frames == 600
    assert avg_fps == pytest.approx(59.0, abs=1.5)
    assert one_pct == pytest.approx(30.0, abs=0.01)
    assert p99 == pytest.approx(33.333, abs=1e-6)
    assert (game, render, gpu, has_gpu) == (4.0, 5.0, 12.0, 1.0)
    assert avg_ms == pytest.approx(1000.0 / avg_fps)
    assert_stats(driver, samples, 20.0)


def test_ring_buffer_overwrites_oldest(driver):
    assert run(driver, "ring", 4, 10, *range(1, 11)) == [4, 10, 9, 8]
    assert run(driver, "ring", 4, 4, 1, 2, 3, 4) == [4, 4, 3, 2]
    assert run(driver, "ring", 4, 2, 1, 2) == [2, 2, 1]
    assert run(driver, "ring", 4, 0) == [0]
    assert run(driver, "ring", 1, 3, 7, 8, 9) == [1, 9]


def test_cycles_to_ms(driver):
    assert run(driver, "cycles", 1000, "1e-6") == [1.0]
    assert close(run(driver, "cycles", 123456789, "2.5e-10"), [123456789 * 2.5e-10 * 1000.0])
    assert run(driver, "cycles", 0, "1e-7") == [0.0]


# -------------------------------------------------------------------------------------------------------- (d)


def fmt(driver: Path, value: float, decimals: int) -> str:
    res = run_raw(driver, "fmt", repr(value), decimals)
    assert res.returncode == 0, res.stderr
    return res.stdout.rstrip("\n")


def test_format_fixed_matches_python_on_non_tie_inputs(driver):
    rng = np.random.default_rng(3)
    for decimals in (0, 1, 2, 3, 6):
        scale = 10**decimals
        for _ in range(40):
            k = int(rng.integers(-2_000_000, 2_000_000))
            extra = int(rng.integers(0, 10_000))
            if extra == 5000:  # the only exact tie in four extra digits
                extra = 5001
            value = k / scale + extra / (scale * 10_000)
            expect = f"{value:.{decimals}f}"
            if expect == "-" + "0" * len(expect.lstrip("-0")) or set(expect) <= {"-", "0", "."}:
                expect = expect.lstrip("-")  # the header never prints "-0.00"
            assert fmt(driver, value, decimals) == expect, (value, decimals)
    special = [(0.0, 2), (-0.0, 2), (-0.004, 2), (-0.0004, 3), (1234.5678, 2), (0.5, 0), (2.5, 0)]
    for value, decimals in special:
        expect = f"{value:.{decimals}f}".replace("-0.00", "0.00").replace("-0.000", "0.000")
        if (value, decimals) == (2.5, 0):
            expect = "3"  # half away from zero (Python rounds half to even)
        if (value, decimals) == (0.5, 0):
            expect = "1"
        assert fmt(driver, value, decimals) == expect
    assert fmt(driver, -0.004, 2) == "0.00"
    assert fmt(driver, 1234.5678, 2) == "1234.57"
    assert fmt(driver, -123.456, 3) == "-123.456"
    for big in (1e12 + 0.3, 123456789012.7, 9.5e15, 1e20, 1.5e25, 1.7976931348623157e308):
        for decimals in (0, 2):
            assert fmt(driver, big, decimals) == f"{big:.{decimals}f}", (big, decimals)
            assert fmt(driver, -big, decimals) == f"{-big:.{decimals}f}", (big, decimals)
    for bad in ("nan", "inf", "-inf"):
        assert fmt(driver, float(bad), 2) == "0"
    assert fmt(driver, 1.23456789123, 12) == "1.234567891"  # decimals clamped to 9


# -------------------------------------------------------------------------------------------------------- (e)


def grid_path(rng: np.random.Generator, n: int, hz: int = 10) -> dict:
    ts = np.cumsum(rng.integers(50, 200, n)) / 1000.0
    ts[0] = 0.0
    samples = [
        {
            "t": float(t),
            "p": [int(v) / 100.0 for v in rng.integers(-3_000_000, 3_000_000, 3)],
            "r": [int(v) / 1000.0 for v in rng.integers(-180_000, 180_000, 3)],
        }
        for t in ts
    ]
    return {
        "version": 1,
        "name": "walk_01",
        "level": "L_ZoneTest",
        "hz": hz,
        "created": "2026-09-25T10:11:12Z",
        "samples": samples,
    }


def pathfmt(driver: Path, path: dict) -> str:
    # name / level / created go through stdin as raw UTF-8 (Windows converts argv to cp1252 and mangles them)
    strings = [path["name"], path["level"], path["created"]]
    lengths = " ".join(str(len(v.encode("utf-8"))) for v in strings)
    args = ["pathfmt", path["hz"], len(path["samples"])]
    for s in path["samples"]:
        args += [repr(float(s["t"])), *(repr(float(v)) for v in s["p"]), *(repr(float(v)) for v in s["r"])]
    res = run_raw(driver, *args, stdin=lengths + "\n" + "".join(strings))
    assert res.returncode == 0, res.stdout + res.stderr
    return res.stdout


def pathparse(driver: Path, text: str) -> dict:
    res = run_raw(driver, "pathparse", stdin=text)
    assert res.returncode == 0, res.stdout + res.stderr
    lines = res.stdout.splitlines()
    version, hz, n = (int(v) for v in lines[0].split())
    assert len(lines) == n + 1
    samples = []
    for line in lines[1:]:
        vals = [float(v) for v in line.split()]
        samples.append({"t": vals[0], "p": vals[1:4], "r": vals[4:7]})
    return {"version": version, "hz": hz, "samples": samples}


def pathmeta(driver: Path, text: str) -> str:
    res = run_raw(driver, "pathmeta", stdin=text)
    assert res.returncode == 0, res.stdout + res.stderr
    return res.stdout


def expect_parse_error(driver: Path, text: str) -> str:
    res = run_raw(driver, "pathparse", stdin=text)
    assert res.returncode == 3, (res.returncode, res.stdout)
    assert res.stdout.startswith("ERROR path json: "), res.stdout
    return res.stdout


def test_pathfmt_reproduces_the_design_example_byte_for_byte(driver):
    example = {
        "version": 1,
        "name": "walk_01",
        "level": "L_ZoneTest",
        "hz": 10,
        "created": "2026-09-25T10:11:12Z",
        "samples": [
            {"t": 0.0, "p": [17670.59, -22698.0, 1190.0], "r": [-5.0, 90.0, 0.0]},
            {"t": 0.1, "p": [17670.59, -22690.12, 1190.0], "r": [-5.0, 90.0, 0.0]},
        ],
    }
    assert pathfmt(driver, example) == EXAMPLE_JSON
    assert json.loads(EXAMPLE_JSON) == example


def test_pathfmt_layout_keys_and_values(driver):
    rng = np.random.default_rng(21)
    for n in (0, 1, 7):
        path = grid_path(rng, n) if n else {**grid_path(rng, 1), "samples": []}
        text = pathfmt(driver, path)
        assert text.endswith("]}\n") and not text.endswith("\n\n")
        lines = text.split("\n")
        assert lines[0].endswith('"samples": [') and lines[-2] == "]}" and lines[-1] == ""
        assert len(lines) == n + 3  # header, one line per sample, closing, trailing newline
        for i, line in enumerate(lines[1 : 1 + n]):
            assert line.startswith('{"t": ') and line.endswith("]}" if i == n - 1 else "]},"), line
        d = json.loads(text)
        assert list(d.keys()) == PATH_KEYS
        assert d["version"] == 1 and isinstance(d["hz"], int) and d["hz"] == path["hz"]
        assert (d["name"], d["level"], d["created"]) == (path["name"], path["level"], path["created"])
        assert len(d["samples"]) == n
        for got, ref in zip(d["samples"], path["samples"], strict=True):
            assert list(got.keys()) == SAMPLE_KEYS
            assert close(got["t"], ref["t"], 1e-6) and close(got["p"], ref["p"], 1e-6)
            assert close(got["r"], ref["r"], 1e-6)


def test_pathfmt_escapes_strings(driver):
    rng = np.random.default_rng(22)
    path = grid_path(rng, 1)
    path["name"] = 'a"b\\c\td\ne\x01f/g'
    path["level"] = "L_\x1f_\x7fend"
    path["created"] = "café"  # UTF-8 bytes pass through unescaped
    text = pathfmt(driver, path)
    d = json.loads(text)
    assert (d["name"], d["level"], d["created"]) == (path["name"], path["level"], path["created"])
    first = text.split("\n")[0]
    assert '\\"' in first and "\\\\" in first and "\\t" in first and "\\n" in first
    assert "\\u0001" in first and "\\u001f" in first and "\x7f" in first and "café" in first


# -------------------------------------------------------------------------------------------------------- (f)


def same_samples(got: dict, ref: dict) -> None:
    assert got["version"] == 1 and got["hz"] == ref["hz"]
    assert len(got["samples"]) == len(ref["samples"])
    for a, b in zip(got["samples"], ref["samples"], strict=True):
        assert a["t"] == b["t"] and a["p"] == b["p"] and a["r"] == b["r"], (a, b)


def test_pathparse_accepts_tolerant_inputs(driver):
    rng = np.random.default_rng(31)
    ref = grid_path(rng, 12)
    same_samples(pathparse(driver, json.dumps(ref)), ref)
    same_samples(pathparse(driver, json.dumps(ref, indent=2)), ref)
    same_samples(pathparse(driver, json.dumps(ref, separators=(",", ":"))), ref)
    # shuffled key order, unknown keys, hz as a float literal, extra whitespace
    shuffled = dict(ref)
    order = list(shuffled)
    random.Random(2).shuffle(order)
    shuffled = {k: shuffled[k] for k in order}
    shuffled["note"] = {"anything": [1, 2, {"deep": None}], "flag": True}
    shuffled["hz"] = 10.0
    shuffled["samples"] = [{"r": s["r"], "extra": "x", "p": s["p"], "t": s["t"]} for s in shuffled["samples"]]
    text = json.dumps(shuffled, indent=4).replace("\n", "\r\n")
    same_samples(pathparse(driver, "  \t" + text + "\n\n"), ref)
    # optional string keys missing or null; exponent / negative-zero number spellings
    minimal = (
        '{"version": 1.0, "samples": [{"t": 0, "p": [1e2, -0.0, 2.5E-1], "r": [0, 1e+1, -1]},'
        ' {"t": 1.5e0, "p": [0, 0, 0], "r": [0, 0, 0]}], "created": null}'
    )
    got = pathparse(driver, minimal)
    assert got["hz"] == 10 and got["samples"][0]["p"] == [100.0, 0.0, 0.25]
    assert got["samples"][0]["r"] == [0.0, 10.0, -1.0] and got["samples"][1]["t"] == 1.5
    assert pathmeta(driver, minimal) == "\n\n\n"
    # extreme exponents never reach std::stod's throwing paths: deep underflow -> 0, overflow -> error
    edge = '{"version": 1, "samples": [{"t": 0, "p": [1e-400, 0e999999, -1e-308], "r": [1.5e308, 0, 0]}]}'
    got = pathparse(driver, edge)
    assert got["samples"][0]["p"] == [0.0, 0.0, 0.0] and got["samples"][0]["r"][0] == 1.5e308
    dbl_max = pathparse(driver, edge.replace("1.5e308", "1.7976931348623157e308"))["samples"][0]["r"][0]
    assert dbl_max == sys.float_info.max
    for spelled in ("10e307", "0.1e309", "0.00001e313", "100000000000000000e291"):
        assert pathparse(driver, edge.replace("1.5e308", spelled))["samples"][0]["r"][0] == 1e308, spelled
    for over in ("2e308", "1.7976931348623158e308", "1e999", "18e307", "0.2e309", "100000000000000000e292"):
        assert "bad number" in expect_parse_error(driver, edge.replace("1.5e308", over)), over
    # equal consecutive t is monotonic (non-decreasing) and accepted
    twice = {**ref, "samples": [ref["samples"][0], ref["samples"][0]]}
    same_samples(pathparse(driver, json.dumps(twice)), twice)


def test_pathparse_decodes_string_escapes(driver):
    name = 'a"b\\c/d\tеé\U0001f600\n\x01'
    doc = {"version": 1, "name": name, "level": "lvl", "created": "2026-01-01T00:00:00Z", "samples": []}
    text = json.dumps(doc)  # ensure_ascii: everything non-ASCII becomes \uXXXX (incl. a surrogate pair)
    assert "\\ud83d" in text
    assert pathmeta(driver, text) == f"{name}\nlvl\n2026-01-01T00:00:00Z\n"
    assert pathmeta(driver, json.dumps(doc, ensure_ascii=False)) == f"{name}\nlvl\n2026-01-01T00:00:00Z\n"


def test_pathparse_rejects_bad_documents(driver):
    rng = np.random.default_rng(32)
    ref = grid_path(rng, 5)
    good = json.dumps(ref)
    assert "version must be 1" in expect_parse_error(driver, json.dumps({**ref, "version": 2}))
    for key in ("version", "samples"):
        assert key in expect_parse_error(driver, json.dumps({k: v for k, v in ref.items() if k != key}))
    bad_t = json.loads(good)
    bad_t["samples"][3]["t"] = bad_t["samples"][2]["t"] - 0.001
    assert "monotonic" in expect_parse_error(driver, json.dumps(bad_t))
    for cut in (len(good) - 1, len(good) // 2, 1, 0):
        expect_parse_error(driver, good[:cut])
    expect_parse_error(driver, good + " x")
    expect_parse_error(driver, "[1, 2]")
    expect_parse_error(driver, json.dumps({**ref, "samples": [{"t": 0, "p": [1, 2], "r": [0, 0, 0]}]}))
    expect_parse_error(driver, json.dumps({**ref, "samples": [{"p": [1, 2, 3], "r": [0, 0, 0]}]}))
    expect_parse_error(driver, json.dumps({**ref, "samples": [{"t": "0", "p": [1, 2, 3], "r": [0, 0, 0]}]}))
    expect_parse_error(driver, json.dumps({**ref, "name": 5}))
    expect_parse_error(driver, good.replace('"hz": 10', '"hz": 1e999'))
    expect_parse_error(driver, good.replace('"hz": 10', '"hz": 01'))
    expect_parse_error(driver, good.replace('"hz": 10', '"hz": +10'))
    expect_parse_error(driver, good.replace('"hz": 10', '"hz": 1.'))
    expect_parse_error(driver, good.replace('"name": "walk_01"', '"name": "walk\\x01"'))
    expect_parse_error(driver, good.replace('"name": "walk_01"', '"name": "walk\n01"'))
    expect_parse_error(driver, "[" * 100 + "]" * 100)
    for i in range(1, len(good), 37):  # truncations anywhere never crash
        res = run_raw(driver, "pathparse", stdin=good[:i])
        assert res.returncode == 3 and res.stdout.startswith("ERROR "), i


# -------------------------------------------------------------------------------------------------------- (g)


def test_path_round_trip_is_exact_on_grid_inputs(driver):
    rng = np.random.default_rng(41)
    for n in (1, 2, 25, 200):
        ref = grid_path(rng, n, hz=int(rng.integers(1, 60)))
        text = pathfmt(driver, ref)
        same_samples(pathparse(driver, text), ref)
        assert pathmeta(driver, text) == f"{ref['name']}\n{ref['level']}\n{ref['created']}\n"
        assert pathfmt(driver, {**ref, **json.loads(text)}) == text  # format(parse(format(x))) == format(x)


# -------------------------------------------------------------------------------------------------------- (h)


def ref_lerp_angle(a: float, b: float, alpha: float) -> float:
    d = (b - a + 180.0) % 360.0 - 180.0
    if d <= -180.0:
        d += 360.0
    return a + d * alpha


def angle_close(a, b, tol: float = 1e-9) -> bool:
    return bool(np.all(np.abs((np.asarray(a) - np.asarray(b) + 180.0) % 360.0 - 180.0) < tol))


def pose(driver: Path, text: str, t: float) -> list[float]:
    return run(driver, "pose", repr(t), stdin=text)


def test_pose_at_matches_np_interp_with_angle_unwrap(driver):
    rng = np.random.default_rng(51)
    ref = grid_path(rng, 20)
    text = json.dumps(ref)
    ts = np.array([s["t"] for s in ref["samples"]])
    ps = np.array([s["p"] for s in ref["samples"]])
    rs = np.array([s["r"] for s in ref["samples"]])
    unwrapped = np.rad2deg(np.unwrap(np.deg2rad(rs), axis=0))
    queries = list(rng.uniform(ts[0] - 1, ts[-1] + 1, 200))
    queries += [ts[0], ts[-1], ts[5], ts[6], ts[0] - 5, ts[-1] + 5]
    for t in queries:
        got = pose(driver, text, float(t))
        expect_p = [np.interp(t, ts, ps[:, k]) for k in range(3)]
        expect_r = [np.interp(t, ts, unwrapped[:, k]) for k in range(3)]
        assert close(got[:3], expect_p, 1e-9), t
        assert angle_close(got[3:], expect_r), t
    # single sample: any T gives that sample
    single = {**ref, "samples": [ref["samples"][3]]}
    s = ref["samples"][3]
    for t in (-1.0, s["t"], s["t"] + 100.0):
        assert pose(driver, json.dumps(single), t) == [*s["p"], *s["r"]]
    # empty path -> no pose
    res = run_raw(driver, "pose", 0.0, stdin=json.dumps({**ref, "samples": []}))
    assert res.returncode == 3 and res.stdout.startswith("ERROR")


def test_pose_at_turns_the_short_way_through_minus_180(driver):
    two = {
        "version": 1,
        "hz": 10,
        "samples": [
            {"t": 0.0, "p": [0, 0, 0], "r": [0, 170.0, 0]},
            {"t": 1.0, "p": [100, 0, 0], "r": [0, -170.0, 0]},
        ],
    }
    text = json.dumps(two)
    for alpha, yaw in ((0.0, 170.0), (0.25, 175.0), (0.5, 180.0), (0.75, -175.0), (1.0, -170.0)):
        got = pose(driver, text, alpha)
        assert close(got[0], 100.0 * alpha) and angle_close(got[4], yaw), alpha
    assert angle_close(pose(driver, text, 0.5)[4], -180.0)  # 20 degree turn, not 340


# -------------------------------------------------------------------------------------------------------- (i)


def test_lerp_angle_deg(driver):
    cases = [(0, 90, 0.5), (170, -170, 0.5), (-170, 170, 0.5), (10, 190, 0.5), (10, -170, 0.5)]
    cases += [(350, 10, 0.25), (0, 0, 0.7), (720, 30, 0.5), (-1000, 1000, 0.1), (45, 45.0001, 1.0)]
    rng = np.random.default_rng(61)
    ab = rng.uniform(-720, 720, (2, 40))
    cases += [tuple(map(float, v)) for v in zip(ab[0], ab[1], rng.uniform(0, 1, 40), strict=True)]
    for a, b, alpha in cases:
        (got,) = run(driver, "angle", repr(float(a)), repr(float(b)), repr(float(alpha)))
        assert close(got, ref_lerp_angle(a, b, alpha)), (a, b, alpha)
    assert run(driver, "angle", 170, -170, 0.5) == [180.0]
    assert run(driver, "angle", -170, 170, 0.5) == [-180.0]
    assert run(driver, "angle", 10, 190, 0.5) == [100.0]  # exactly opposite: +180 wins
    assert run(driver, "angle", 10, -170, 0.5) == [100.0]
    assert run(driver, "angle", 0, 90, 0.5) == [45.0]


# -------------------------------------------------------------------------------------------------------- (j)


def hold(driver: Path, tokens: str) -> tuple[list[str], list[float]]:
    """`hold`: (per-token outputs, final [Value, HeldCount, Total, bHeldLast])."""
    res = run_raw(driver, "hold", stdin=tokens)
    assert res.returncode == 0, res.stdout + res.stderr
    lines = res.stdout.splitlines()
    assert len(lines) == 2, res.stdout
    return lines[0].split(), [float(v) for v in lines[1].split()]


def test_hold_last_positive_sequence(driver):
    # WP-09 design §8-1: 0 / NaN / negative samples keep the last positive value; 0 until the first positive
    values, state = hold(driver, "0 5 0 0 6 nan -1 7")
    assert [float(v) for v in values] == [0, 5, 5, 5, 6, 6, 6, 7]
    assert state == [7.0, 5.0, 8.0, 0.0]  # Value 7, HeldCount 5, Total 8, last sample not held
    values, state = hold(driver, "0 0 nan")
    assert [float(v) for v in values] == [0, 0, 0]
    assert state == [0.0, 3.0, 3.0, 1.0]
    values, state = hold(driver, "2.5 inf 3")
    assert [float(v) for v in values] == [2.5, float("inf"), 3.0]
    assert state == [3.0, 0.0, 3.0, 0.0]


def test_hold_state_resets(driver):
    values, state = hold(driver, "5 0 reset")
    assert values == ["5", "5", "reset"]
    assert state == [0.0, 0.0, 0.0, 0.0]  # Reset(): Value 0, counters 0, bHeldLast false
    values, state = hold(driver, "5 0 reset 0 3 0")
    assert [v if v == "reset" else float(v) for v in values] == [5.0, 5.0, "reset", 0.0, 3.0, 3.0]
    assert state == [3.0, 2.0, 3.0, 1.0]  # counted from the reset only
