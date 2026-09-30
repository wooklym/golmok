"""WP-19a: Animation/GolmokLocomotionMath.h compiled with g++, checked against tables and a Python reference.

The header holds the state rules of UGolmokLocomotionStateComponent (design section 2): gait, movement mode,
input intent, moving hysteresis, the just-landed window, teleport jumps, profile / state ranges and the V-08
table A planted-foot slip that Golmok.Animation.GaspSmoke and V-15 share.
"""

from __future__ import annotations

import math
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HEADER_DIR = ROOT / "unreal/Golmok/Source/Golmok/Animation"
HEADER = HEADER_DIR / "GolmokLocomotionMath.h"
DRIVER = Path(__file__).parent / "fixtures/ue/locomotionmath_driver.cpp"


@pytest.fixture(scope="module")
def driver(tmp_path_factory):
    compiler = next((p for name in ("g++", "clang++", "c++") if (p := shutil.which(name))), None)
    if not compiler:
        pytest.skip("no g++/clang++ on PATH")
    output = tmp_path_factory.mktemp("locomotionmath") / (
        "driver.exe" if sys.platform == "win32" else "driver"
    )
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


def ints(driver, commands: list[str]) -> list[int]:
    return [int(v[0]) for v in run(driver, commands)]


# ---- Python reference (independent of the header) ----------------------------------------------------------

WALK, RUN = 0, 1
ON_GROUND, IN_AIR = 0, 1
IDLE, MOVING = 0, 1


def _finite(*values: float) -> bool:
    return all(math.isfinite(v) for v in values)


def ref_gait(max_walk: float, walk: float, run_speed: float) -> int:
    if not _finite(max_walk, walk, run_speed) or run_speed <= walk:
        return WALK
    return RUN if abs(max_walk - run_speed) <= 0.5 else WALK


def ref_mode(mode: int) -> int:
    return IN_AIR if mode == 3 else ON_GROUND


def ref_intent(ax: float, ay: float, max_accel: float, deadzone: float) -> tuple[float, float]:
    if not _finite(ax, ay, max_accel) or max_accel <= 0:
        return 0.0, 0.0
    x, y = ax / max_accel, ay / max_accel
    length = math.hypot(x, y)
    if not math.isfinite(length) or length < deadzone:
        return 0.0, 0.0
    if length > 1:
        x, y = x / length, y / length
    return x, y


def ref_moving(prev: int, speed: float, intent_len: float) -> int:
    if speed >= 10.0 or intent_len > 0:
        return MOVING
    if speed < 3.0:
        return IDLE
    return prev


def ref_teleport(px, py, cx, cy, speed, dt, slack) -> bool:
    distance = math.hypot(cx - px, cy - py)
    if not math.isfinite(distance):
        return False

    def positive(v):
        return v if math.isfinite(v) and v > 0 else 0.0

    return distance > positive(speed) * positive(dt) + positive(slack)


PROFILE_RANGES = (
    ("max_acceleration", 100.0, 10000.0),
    ("braking_deceleration_walking", 0.0, 10000.0),
    ("ground_friction", 0.0, 20.0),
    ("braking_friction_factor", 0.0, 10.0),
    ("braking_friction", 0.0, 20.0),
)


def ref_planted(samples: list[tuple[float, float, float, bool]]) -> float:
    grounded = [z for _x, _y, z, g in samples if g]
    if len(samples) < 2 or not grounded:
        return 0.0
    floor = min(grounded)

    def planted(s):
        return s[3] and s[2] <= floor + 2.5

    return sum(
        math.hypot(b[0] - a[0], b[1] - a[1])
        for a, b in zip(samples, samples[1:], strict=False)
        if planted(a) and planted(b)
    )


# ---- the header --------------------------------------------------------------------------------------------


def test_header_is_pure():
    text = HEADER.read_text(encoding="utf-8")
    assert text.lstrip().startswith("#pragma once")
    assert re.findall(r'^#include\s+"', text, re.M) == []
    assert set(re.findall(r"^#include\s+<([^>]+)>", text, re.M)) == {"array", "cmath"}
    for banned in ("CoreMinimal", "UCLASS", "UE_LOG", "std::min", "std::max", "printf", "FVector", "FMath"):
        assert banned not in text, banned
    assert "namespace GolmokLocomotionMath" in text


def test_gait_table(driver):
    rows = [
        (180, 180, 500, WALK),
        (500, 180, 500, RUN),
        (500.4, 180, 500, RUN),
        (499.5, 180, 500, RUN),
        (499.4, 180, 500, WALK),
        (145, 145, 380, WALK),
        (380, 145, 380, RUN),  # WP-18 roster proxy135
        (310, 120, 310, RUN),  # proxy110
        (120, 120, 310, WALK),
        (300, 180, 500, WALK),  # analog / in between is walk (no sprint)
        (500, 500, 500, WALK),  # invalid roster (Run <= Walk)
    ]
    got = ints(driver, [f"gait {m} {w} {r}" for m, w, r, _ in rows])
    assert got == [expected for *_, expected in rows]


def test_gait_matches_reference(driver):
    rng = random.Random(19)
    cases = [(rng.uniform(0, 800), rng.uniform(50, 300), rng.uniform(50, 800)) for _ in range(300)]
    cases += [(r + rng.uniform(-1, 1), w, r) for _, w, r in cases[:100]]
    got = ints(driver, [f"gait {m!r} {w!r} {r!r}" for m, w, r in cases])
    assert got == [ref_gait(*c) for c in cases]


def test_movement_mode_table(driver):
    modes = list(range(-1, 8))
    assert ints(driver, [f"mode {m}" for m in modes]) == [ref_mode(m) for m in modes]
    assert ints(driver, ["mode 1", "mode 2", "mode 3"]) == [ON_GROUND, ON_GROUND, IN_AIR]


def test_intent(driver):
    rows = [
        (2048, 0, 2048, 0.05, (1.0, 0.0)),
        (0, 1024, 2048, 0.05, (0.0, 0.5)),  # half-tilted stick keeps its size
        (100, 0, 2048, 0.05, (0.0, 0.0)),  # 0.0488 < deadzone
        (103, 0, 2048, 0.05, (103 / 2048, 0.0)),
        (4096, 4096, 2048, 0.05, (math.sqrt(0.5), math.sqrt(0.5))),  # clamped to length 1
        (500, 0, 0, 0.05, (0.0, 0.0)),  # no max acceleration
        (500, 0, -1, 0.05, (0.0, 0.0)),
    ]
    out = run(driver, [f"intent {ax} {ay} {m} {d}" for ax, ay, m, d, _ in rows])
    for (*_, (ex, ey)), line in zip(rows, out, strict=True):
        assert float(line[0]) == pytest.approx(ex, abs=1e-12)
        assert float(line[1]) == pytest.approx(ey, abs=1e-12)
    rng = random.Random(7)
    cases = [
        (rng.uniform(-5000, 5000), rng.uniform(-5000, 5000), rng.uniform(1, 4000), 0.05) for _ in range(300)
    ]
    out = run(driver, [f"intent {a!r} {b!r} {m!r} {d!r}" for a, b, m, d in cases])
    for case, line in zip(cases, out, strict=True):
        x, y = ref_intent(*case)
        assert float(line[0]) == pytest.approx(x, rel=1e-12, abs=1e-15)
        assert float(line[1]) == pytest.approx(y, rel=1e-12, abs=1e-15)
        assert float(line[2]) <= 1.0 + 1e-12


def test_moving_hysteresis(driver):
    rows = [
        (IDLE, 0, 0, IDLE),
        (IDLE, 9.9, 0, IDLE),  # between stop and start: keeps Idle
        (IDLE, 10, 0, MOVING),
        (IDLE, 0, 0.06, MOVING),  # intent starts at once
        (MOVING, 5, 0, MOVING),  # braking: still Moving until below 3 cm/s
        (MOVING, 3, 0, MOVING),
        (MOVING, 2.99, 0, IDLE),
        (MOVING, 0, 0.5, MOVING),
    ]
    assert ints(driver, [f"moving {p} {s} {i}" for p, s, i, _ in rows]) == [e for *_, e in rows]
    rng = random.Random(3)
    cases = [
        (rng.choice((IDLE, MOVING)), rng.uniform(0, 20), rng.choice((0.0, 0.0, rng.uniform(0, 1))))
        for _ in range(300)
    ]
    assert ints(driver, [f"moving {p} {s!r} {i!r}" for p, s, i in cases]) == [ref_moving(*c) for c in cases]


def test_landing_window(driver):
    (line,) = run(driver, ["landing -512.5 10.0 0.3 0 5 9.9 10.0 10.1 10.299 10.3"])
    assert float(line[0]) == -512.5
    flags = [int(v) for v in line[1::2]]
    since = [float(v) for v in line[2::2]]
    assert flags == [0, 1, 1, 1, 0]  # before landing, [landed, landed + 0.3)
    assert since[0] == -1.0 and since[1] == 0.0 and since[3] == pytest.approx(0.299)
    (cleared,) = run(driver, ["landing -400 5 0.3 1 1 5.1"])
    assert cleared[1:] == ["0", "-1"]  # a new jump ends the window


def test_teleport(driver):
    rows = [
        (0, 0, 150, 0, 500, 0.1, 100, False),  # 150 = 50 + 100: not more than the reach
        (0, 0, 150.01, 0, 500, 0.1, 100, True),
        (0, 0, 3000, 4000, 500, 0.016, 100, True),  # golmok.travel
        (0, 0, 0, 0, 0, 0, 100, False),
        (0, 0, 80, 60, 0, 0, 100, False),  # capsule nudge (100 cm)
    ]
    got = ints(driver, [f"teleport {a} {b} {c} {d} {s} {t} {k}" for a, b, c, d, s, t, k, _ in rows])
    assert got == [int(e) for *_, e in rows]
    rng = random.Random(5)
    cases = [
        (rng.uniform(-1e4, 1e4), rng.uniform(-1e4, 1e4), rng.uniform(-1e4, 1e4), rng.uniform(-1e4, 1e4),
         rng.uniform(0, 800), rng.uniform(0, 0.2), rng.uniform(20, 1000))
        for _ in range(200)
    ]  # fmt: skip
    got = ints(driver, ["teleport " + " ".join(repr(v) for v in c) for c in cases])
    assert got == [int(ref_teleport(*c)) for c in cases]


def test_profile_ranges(driver):
    base = [2048.0, 2000.0, 8.0, 2.0, 0, 0.0]
    assert ints(driver, ["profile " + " ".join(map(str, base))]) == [1]
    field_index = {"max_acceleration": 0, "braking_deceleration_walking": 1, "ground_friction": 2,
                   "braking_friction_factor": 3, "braking_friction": 5}  # fmt: skip
    commands, expected = [], []
    for name, low, high in PROFILE_RANGES:
        for value, ok in ((low, True), (high, True), (low - 0.001, False), (high + 0.001, False)):
            row = list(base)
            row[field_index[name]] = value
            commands.append("profile " + " ".join(map(str, row)))
            expected.append(int(ok))
    assert ints(driver, commands) == expected


def test_state_ranges(driver):
    rows = [
        (0.3, 100, 1),
        (0.05, 20, 1),
        (2, 1000, 1),
        (0.049, 100, 0),
        (2.01, 100, 0),
        (0.3, 19.9, 0),
        (0.3, 1001, 0),
    ]
    assert ints(driver, [f"state {a} {b}" for a, b, _ in rows]) == [e for *_, e in rows]


def test_defaults_are_the_spec_values(driver):
    (line,) = run(driver, ["defaults"])
    assert [float(v) for v in line] == [2048, 2000, 8, 2, 0, 0, 0.3, 100, 2.5, 0.05, 10, 3, 0.5]


def _planted_command(samples) -> str:
    return f"planted {len(samples)} " + " ".join(f"{x!r} {y!r} {z!r} {int(g)}" for x, y, z, g in samples)


def test_planted_slip_table(driver):
    # Foot planted at z 10 for three samples sliding 1 cm each, then lifted, then planted again 40 cm ahead.
    samples = [(0, 0, 10, True), (1, 0, 10.5, True), (2, 0, 11, True), (20, 0, 30, True), (40, 0, 12.4, True),
               (40.5, 0, 12.5, True), (41, 0, 12.6, True)]  # fmt: skip
    (travel,) = run(driver, [_planted_command(samples)])
    assert float(travel[0]) == pytest.approx(2.0 + 0.5)  # 12.6 > 10 + 2.5 is not planted
    airborne = [(0, 0, 5, False), (10, 0, 5, False)]
    assert run(driver, [_planted_command(airborne), "planted 0 ", "slip 30 200", "slip 5 0.5"]) == [
        ["0"],
        ["0"],
        ["15"],
        ["0"],
    ]


def test_planted_slip_matches_reference(driver):
    rng = random.Random(11)
    for _ in range(40):
        n = rng.randint(0, 60)
        samples = [
            (rng.uniform(-50, 50), rng.uniform(-50, 50), rng.uniform(0, 8), rng.random() > 0.1)
            for _ in range(n)
        ]
        (line,) = run(driver, [_planted_command(samples)])
        assert float(line[0]) == pytest.approx(ref_planted(samples), rel=1e-12, abs=1e-12)


# ---- non-finite inputs (review R76 D10: the driver parses nan / inf tokens) --------------------------------

NAN, INF = math.nan, math.inf
SPECIAL = (NAN, INF, -INF)


def test_non_finite_tokens_reach_the_header(driver):
    assert ints(
        driver, ["gait nan 180 500", "gait 500 180 inf", "gait inf 180 inf", "gait 500 -inf 500"]
    ) == [
        WALK,
        WALK,
        WALK,
        WALK,
    ]
    for line in run(driver, ["intent nan 0 2048 0.05", "intent 2048 0 inf 0.05", "intent inf inf 2048 0.05"]):
        assert [float(v) for v in line] == [0.0, 0.0, 0.0]
    assert ints(driver, ["moving 0 nan 0", "moving 1 nan 0", "moving 0 inf 0", "moving 1 -inf 0"]) == [
        IDLE,
        MOVING,
        MOVING,
        IDLE,
    ]
    assert ints(driver, ["teleport 0 0 inf 0 500 0.1 100", "teleport 0 0 nan 0 0 0 100",
                         "teleport 0 0 150 0 nan 0.1 100", "teleport 0 0 150 0 500 inf 100",
                         "teleport 0 0 150 0 inf 0.1 100"]) == [0, 0, 1, 1, 1]  # fmt: skip
    assert ints(
        driver, ["profile nan 2000 8 2 0 0", "profile 2048 inf 8 2 0 0", "state nan 100", "state 0.3 inf"]
    ) == [
        0,
        0,
        0,
        0,
    ]
    (landing,) = run(driver, ["landing nan 10 0.3 0 3 10.1 nan inf"])
    assert landing == ["0", "1", "0.099999999999999645", "0", "-1", "0", "inf"]
    assert run(driver, ["slip nan 200", "slip 30 inf", "slip inf 200"]) == [["0"], ["0"], ["0"]]
    planted = [(0, 0, NAN, True), (1, 0, 10, True), (2, 0, 10, True), (NAN, 0, 10, True), (4, 0, 10, True)]
    (travel,) = run(driver, [_planted_command(planted)])
    assert float(travel[0]) == ref_planted_finite(planted) == 1.0


def ref_planted_finite(samples) -> float:
    """ref_planted with the header's non-finite rules (a nan height is never the floor nor planted)."""
    grounded = [z for _x, _y, z, g in samples if g and math.isfinite(z)]
    if len(samples) < 2 or not grounded:
        return 0.0
    floor = min(grounded)

    def planted(s):
        return s[3] and math.isfinite(s[2]) and s[2] <= floor + 2.5

    total = 0.0
    for a, b in zip(samples, samples[1:], strict=False):
        if planted(a) and planted(b):
            step = math.hypot(b[0] - a[0], b[1] - a[1])
            total += step if math.isfinite(step) else 0.0
    return total


def test_non_finite_random_cases_match_the_reference(driver):
    rng = random.Random(1910)

    def value(low, high):
        return rng.choice(SPECIAL) if rng.random() < 0.3 else rng.uniform(low, high)

    gaits = [(value(0, 800), value(50, 300), value(50, 800)) for _ in range(200)]
    assert ints(driver, [f"gait {m!r} {w!r} {r!r}" for m, w, r in gaits]) == [ref_gait(*c) for c in gaits]
    intents = [(value(-5000, 5000), value(-5000, 5000), value(1, 4000), 0.05) for _ in range(200)]
    for case, line in zip(intents, run(driver, [f"intent {a!r} {b!r} {m!r} {d!r}" for a, b, m, d in intents]),
                          strict=True):  # fmt: skip
        x, y = ref_intent(*case)
        assert float(line[0]) == pytest.approx(x, rel=1e-12, abs=1e-15)
        assert float(line[1]) == pytest.approx(y, rel=1e-12, abs=1e-15)
    moves = [(rng.choice((IDLE, MOVING)), value(0, 20), rng.choice((0.0, 0.5))) for _ in range(200)]
    assert ints(driver, [f"moving {p} {s!r} {i!r}" for p, s, i in moves]) == [ref_moving(*c) for c in moves]
    jumps = [tuple(value(-1e4, 1e4) for _ in range(4)) + (value(0, 800), value(0, 0.2), value(20, 1000))
             for _ in range(200)]  # fmt: skip
    got = ints(driver, ["teleport " + " ".join(repr(v) for v in c) for c in jumps])
    assert got == [int(ref_teleport(*c)) for c in jumps]
    for _ in range(20):
        samples = [
            (value(-50, 50), value(-50, 50), value(0, 8), rng.random() > 0.1)
            for _ in range(rng.randint(0, 30))
        ]
        (line,) = run(driver, [_planted_command(samples)])
        assert float(line[0]) == pytest.approx(ref_planted_finite(samples), rel=1e-12, abs=1e-12)
