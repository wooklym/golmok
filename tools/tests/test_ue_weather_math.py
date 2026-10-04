"""WP-16a: Weather/GolmokWeatherMath.h compiled with g++, checked against tables and golmok/weather_pure.py.

The header is the only home of the weather rules UGolmokWeatherSubsystem and AGolmokTimeOfDay use (design
sections 2-5 and 8): state names, the lighting modifier (identity, Apply, log2 Lerp, ForState), the transition
(smoothstep, precipitation delay), the surface integration and the schedule lookup across midnight.
golmok/weather_pure.py mirrors every rule; the tables pin the design's boundaries and 600 seeded random cases
compare header and mirror (doubles cross the pipe as hexfloat, so equal means bit-equal).
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
SOURCE_DIR = ROOT / "unreal/Golmok/Source/Golmok"  # the header includes "Lighting/GolmokClockMath.h"
HEADER = SOURCE_DIR / "Weather/GolmokWeatherMath.h"
DRIVER = Path(__file__).parent / "fixtures/ue/weathermath_driver.cpp"
sys.path.insert(0, str(ROOT / "unreal" / "Golmok" / "Content" / "Python"))
from golmok import weather_pure as wp  # noqa: E402

CONFIG = wp.load_config()
OVERCAST = CONFIG.overcast
RAIN = CONFIG.rain
IDENTITY = wp.Modifier()
PARAMS = CONFIG.surface
SEED = 16_0416


@pytest.fixture(scope="module")
def driver(tmp_path_factory):
    compiler = next((p for name in ("g++", "clang++", "c++") if (p := shutil.which(name))), None)
    if not compiler:
        pytest.skip("no g++/clang++ on PATH")
    output = tmp_path_factory.mktemp("weathermath") / ("driver.exe" if sys.platform == "win32" else "driver")
    result = subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-Wshadow",
            f"-I{SOURCE_DIR}",
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
    assert all(line != ["unknown"] for line in lines)
    return lines


def h(x: float) -> str:
    """Exact text for the driver's strtod."""
    return float(x).hex()


def f(token: str) -> float:
    return float.fromhex(token)


def mod_args(m: wp.Modifier) -> str:
    return " ".join(h(v) for v in m.values())


def light_args(light: wp.Light) -> str:
    return " ".join(
        [
            h(light.lux),
            str(int(light.use_temperature)),
            h(light.kelvin),
            h(light.sky),
            h(light.fog),
            h(light.fog_height_falloff),
            str(int(light.exposure_overridden)),
            h(light.exposure_bias),
        ]
    )


def light_tokens(light: wp.Light) -> list[str]:
    return light_args(light).split()


def mod_bits(m: wp.Modifier) -> list[str]:
    return [h(v) for v in m.values()]


def bits(tokens: list[str]) -> list[str]:
    """Driver output normalized to Python's hex spelling (ints / bools stay as they are)."""
    return [t if t in ("0", "1") else h(f(t)) for t in tokens]


def apply_out(tokens: list[str]) -> list[str]:
    out = bits(tokens)
    out[1] = tokens[1]  # use_temperature
    out[6] = tokens[6]  # exposure_overridden
    return out


# ---- constants and contract names ---------------------------------------------------------------------


def test_constants_and_names(driver):
    (consts, contract, *names) = run(driver, ["consts", "contract"] + [f"name {i}" for i in (0, 1, 2, 7, -1)])
    assert int(consts[0]) == wp.STATE_COUNT == len(wp.STATE_NAMES)
    assert [f(t) for t in consts[1:6]] == [
        wp.MIN_RAIN_INTENSITY,
        wp.MAX_RAIN_INTENSITY,
        wp.WET_RAIN_THRESHOLD,
        wp.VALUE_EPSILON,
        wp.MAX_TRANSITION_SECONDS,
    ]
    assert int(consts[6]) == wp.MODIFIER_FIELD_COUNT == len(wp.MODIFIER_FIELDS)
    assert tuple(contract) == wp.MPC_PARAMETERS + wp.USER_PARAMETERS
    assert [n[0] for n in names] == ["clear", "overcast", "rain", "clear", "clear"]
    assert [wp.state_name(i) for i in (0, 1, 2, 7, -1)] == ["clear", "overcast", "rain", "clear", "clear"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("clear", 0),
        ("overcast", 1),
        ("rain", 2),
        ("Rain", None),
        ("rainy", None),
        ("rai", None),
        ("<empty>", None),
        ("snow", None),
    ],
)
def test_parse_state(driver, text, expected):
    (out,) = run(driver, [f"parse_state {text}"])
    want = -1 if expected is None else expected
    assert out == [str(want), str(want)]  # char and wchar_t
    assert wp.parse_state("" if text == "<empty>" else text) == expected


def test_modifier_fields_match(driver):
    rows = run(driver, [f"field {i}" for i in range(wp.MODIFIER_FIELD_COUNT)])
    assert [(r[0], f(r[1]), f(r[2]), r[3] == "1") for r in rows] == list(wp.MODIFIER_FIELDS)
    # the clamp of an out-of-range index
    assert run(driver, ["field -3", "field 99"]) == [rows[0], rows[-1]]


@pytest.mark.parametrize(
    ("index", "value", "ok"),
    [
        (0, 0.0, False),
        (0, 1e-9, True),
        (0, 2.0, True),
        (0, 2.0000001, False),
        (2, 5.0, True),
        (2, 5.01, False),
        (4, 2000.0, True),
        (4, 1999.9, False),
        (4, 12000.0, True),
        (5, 0.0, True),
        (5, -0.0, True),
        (5, 1.0, True),
        (5, 1.01, False),
        (6, -2.0, True),
        (6, 2.0, True),
        (6, -2.01, False),
        (1, math.nan, False),
        (1, math.inf, False),
        (6, -math.inf, False),
    ],
)
def test_field_ranges(driver, index, value, ok):
    (out,) = run(driver, [f"inrange {index} {h(value)}"])
    assert out == [str(int(ok))]
    assert wp.is_field_in_range(index, value) is ok


@pytest.mark.parametrize(
    ("value", "ok"),
    [(0.05, True), (0.0499, False), (1.0, True), (1.0001, False), (0.0, False), (math.nan, False)],
)
def test_rain_intensity_range(driver, value, ok):
    assert run(driver, [f"validint {h(value)}"]) == [[str(int(ok))]]
    assert wp.is_valid_rain_intensity(value) is ok


def test_target_rain(driver):
    out = run(driver, ["target 0 0.5", "target 1 0.5", "target 2 0.5"])
    assert [f(o[0]) for o in out] == [0.0, 0.0, 0.5]
    assert [wp.target_rain(s, 0.5) for s in wp.STATE_NAMES] == [0.0, 0.0, 0.5]


# ---- modifier: identity, Apply, Lerp, ForState ---------------------------------------------------------

LIGHTS = [
    wp.Light(10.0, True, 5600.0, 1.0, 0.015, 0.2, False, 0.0),  # clear_noon-like
    wp.Light(2.5, True, 6500.0, 1.4, 0.035, 0.15, True, 0.3),  # overcast_morning-like
    wp.Light(0.0, True, 4000.0, 0.15, 0.03, 0.2, True, 1.5),  # night-like
    wp.Light(3.14, False, 6500.0, 0.8, 0.0, 0.2, False, -0.0),  # level lighting, no temperature, -0.0 bias
    wp.Light(-0.0, False, 1700.0, 0.0, -0.0, 0.001, True, -5.0),  # signed zeros
]


@pytest.mark.parametrize("light", LIGHTS)
def test_identity_returns_input_bit_identical(driver, light):
    (out,) = run(driver, [f"apply {light_args(light)} {mod_args(IDENTITY)}"])
    assert apply_out(out) == light_tokens(light)
    assert wp.apply(light, IDENTITY) is light
    # kelvin_target alone changes nothing: still the identity
    other_target = wp.Modifier(kelvin_target=9000.0)
    assert run(driver, [f"identity {mod_args(other_target)}"]) == [["1"]]
    (out2,) = run(driver, [f"apply {light_args(light)} {mod_args(other_target)}"])
    assert apply_out(out2) == light_tokens(light)


def test_identity_flags(driver):
    cases = [IDENTITY, OVERCAST, RAIN, wp.Modifier(kelvin_weight=1e-12), wp.Modifier(exposure_offset=-0.0)]
    one_field = [
        wp.Modifier(lux_scale=0.5),
        wp.Modifier(sky_scale=0.5),
        wp.Modifier(fog_scale=1.5),
        wp.Modifier(fog_height_falloff_scale=0.5),
        wp.Modifier(exposure_offset=0.1),
    ]
    cases += one_field
    expected = [1, 0, 0, 0, 1] + [0] * len(one_field)
    out = run(driver, [f"identity {mod_args(m)}" for m in cases])
    assert [int(o[0]) for o in out] == expected
    assert [int(wp.is_identity(m)) for m in cases] == expected


def test_apply_rules(driver):
    noon = LIGHTS[0]
    level = LIGHTS[3]
    out = run(
        driver,
        [f"apply {light_args(noon)} {mod_args(OVERCAST)}", f"apply {light_args(level)} {mod_args(RAIN)}"],
    )
    a = [f(t) for t in out[0]]
    assert (
        a[0] == pytest.approx(3.0)
        and a[3] == 1.0
        and a[4] == pytest.approx(0.021)
        and a[5] == pytest.approx(0.16)
    )
    assert a[2] == pytest.approx(5600.0 + (6800.0 - 5600.0) * 0.5)  # temperature sun: kelvin moves halfway
    assert out[0][6] == "1" and a[7] == pytest.approx(-0.2)  # exposure override on, bias + offset
    b = [f(t) for t in out[1]]
    assert b[2] == 6500.0  # no temperature: kelvin untouched
    assert out[1][1] == "0" and out[1][6] == "1" and b[7] == pytest.approx(-0.4)
    # zero exposure offset leaves the override flag alone
    no_exposure = wp.Modifier(lux_scale=0.5)
    (c,) = run(driver, [f"apply {light_args(noon)} {mod_args(no_exposure)}"])
    assert c[6] == "0" and f(c[7]) == 0.0 and f(c[0]) == 5.0
    for light, m, got in ((noon, OVERCAST, out[0]), (level, RAIN, out[1]), (noon, no_exposure, c)):
        assert apply_out(got) == light_tokens(wp.apply(light, m))


def test_lerp_endpoints_exact(driver):
    out = run(
        driver,
        [
            f"lerp {mod_args(OVERCAST)} {mod_args(RAIN)} {h(t)}"
            for t in (0.0, -1.0, math.nan, 1.0, 1.5, math.inf, -math.inf)
        ],
    )
    for row, want in zip(out, (OVERCAST, OVERCAST, OVERCAST, RAIN, RAIN, RAIN, OVERCAST), strict=True):
        assert bits(row) == mod_bits(want)


def test_lerp_scales_are_log_space(driver):
    (row,) = run(driver, [f"lerp {mod_args(OVERCAST)} {mod_args(RAIN)} {h(0.5)}"])
    v = [f(t) for t in row]
    assert v[0] == pytest.approx(math.sqrt(0.3 * 0.12), rel=1e-12)  # geometric mean, not 0.21
    assert v[2] == pytest.approx(math.sqrt(1.4 * 2.0), rel=1e-12)
    assert v[4] == pytest.approx(7000.0) and v[5] == pytest.approx(0.6) and v[6] == pytest.approx(-0.3)


def test_for_state(driver):
    cmds = [
        f"forstate 0 0.7 {mod_args(OVERCAST)} {mod_args(RAIN)}",
        f"forstate 1 0.7 {mod_args(OVERCAST)} {mod_args(RAIN)}",
        f"forstate 2 1 {mod_args(OVERCAST)} {mod_args(RAIN)}",
        f"forstate 2 0.05 {mod_args(OVERCAST)} {mod_args(RAIN)}",
        f"forstate 2 1.7 {mod_args(OVERCAST)} {mod_args(RAIN)}",
    ]
    clear, overcast, heavy, drizzle, over = run(driver, cmds)
    assert bits(clear) == mod_bits(IDENTITY)
    assert bits(overcast) == mod_bits(OVERCAST)
    assert bits(heavy) == mod_bits(RAIN)
    assert bits(over) == mod_bits(RAIN)  # intensity clamped into [0, 1]
    # Rain(0.05) is close to overcast: 5 % of the overcast -> rain gap per field (log2 space for the scales)
    for k, (o, r, d) in enumerate(
        zip(OVERCAST.values(), RAIN.values(), (f(t) for t in drizzle), strict=True)
    ):
        if k < 4:
            o, r, d = math.log2(o), math.log2(r), math.log2(d)
        assert abs(d - o) <= 0.05 * abs(r - o) + 1e-12, wp.MODIFIER_FIELDS[k][0]
        assert abs(d - o) >= 0.05 * abs(r - o) - 1e-12, wp.MODIFIER_FIELDS[k][0]
    assert bits(drizzle) == mod_bits(wp.for_state("rain", 0.05, OVERCAST, RAIN))
    assert wp.for_state("clear", 0.7, OVERCAST, RAIN) == IDENTITY


# ---- transition ----------------------------------------------------------------------------------------


def test_smoothstep(driver):
    xs = [-1.0, 0.0, 0.25, 0.5, 0.75, 1.0, 2.0, math.nan]
    out = [f(o[0]) for o in run(driver, [f"smooth {h(x)}" for x in xs])]
    assert out == [0.0, 0.0, 0.15625, 0.5, 0.84375, 1.0, 1.0, 0.0]
    assert [wp.smoothstep(x) for x in xs] == out


def test_precip_delay_boundaries(driver):
    # rain increasing (0 -> 0.6): nothing until the sky is half dark
    inc = [0.0, 0.1, 0.25, 0.4999, 0.5]
    out = [f(o[0]) for o in run(driver, [f"precip 0 {h(0.6)} {h(a)}" for a in inc])]
    assert out == [0.0] * 5
    assert f(run(driver, [f"precip 0 {h(0.6)} {h(0.75)}"])[0][0]) == pytest.approx(0.3)
    assert f(run(driver, [f"precip 0 {h(0.6)} {h(1.0)}"])[0][0]) == 0.6
    # rain decreasing (0.6 -> 0): over by alpha 0.5, before the sky clears
    dec = [0.5, 0.6, 0.9, 0.9999]
    out = [f(o[0]) for o in run(driver, [f"precip {h(0.6)} 0 {h(a)}" for a in dec])]
    assert out == [0.0] * 4
    assert f(run(driver, [f"precip {h(0.6)} 0 {h(0.25)}"])[0][0]) == pytest.approx(0.3)
    assert f(run(driver, [f"precip {h(0.6)} 0 0"])[0][0]) == 0.6
    # decreasing but not to zero (1.0 -> 0.3) lands on the target at 0.5
    assert f(run(driver, [f"precip 1 {h(0.3)} {h(0.5)}"])[0][0]) == pytest.approx(0.3, abs=1e-15)
    # equal start / target, alpha past 1
    assert f(run(driver, [f"precip {h(0.3)} {h(0.3)} {h(0.4)}"])[0][0]) == 0.3
    assert f(run(driver, [f"precip {h(0.3)} {h(0.9)} {h(7.0)}"])[0][0]) == 0.9
    assert [wp.precip_at(0.0, 0.6, a) for a in inc] == [0.0] * 5
    assert [wp.precip_at(0.6, 0.0, a) for a in dec] == [0.0] * 4
    assert wp.precip_alpha(0.25, True) == 0.0 and wp.precip_alpha(0.5, False) == 1.0


def test_modifier_at(driver):
    alphas = (0.0, 0.25, 0.5, 0.75, 1.0)
    out = run(driver, [f"modat {mod_args(IDENTITY)} {mod_args(RAIN)} {h(a)}" for a in alphas])
    for row, a in zip(out, alphas, strict=True):
        assert bits(row) == mod_bits(wp.lerp_modifier(IDENTITY, RAIN, wp.smoothstep(a)))
        assert mod_bits(wp.modifier_at(IDENTITY, RAIN, a)) == bits(row)
    assert bits(out[0]) == mod_bits(IDENTITY)
    assert bits(out[-1]) == mod_bits(RAIN)
    # smoothstep, not linear (design section 3): at alpha 0.25 the scales moved 15.625 % of the log2 gap
    assert math.log2(f(out[1][0])) == pytest.approx(0.15625 * math.log2(RAIN.lux_scale), rel=1e-12)


# ---- surface -------------------------------------------------------------------------------------------


def params_args(p: wp.SurfaceParams) -> str:
    return " ".join(
        h(v)
        for v in (
            p.wet_seconds,
            p.dry_seconds,
            p.puddle_min_intensity,
            p.puddle_fill_seconds,
            p.puddle_dry_seconds,
        )
    )


def test_surface_table(driver):
    p = params_args(PARAMS)
    rows = run(
        driver,
        [
            f"step 0 0 1 60 {p}",  # heavy rain 60 s: soaked
            f"step 0 0 1 240 {p}",  # heavy rain 240 s: puddles full
            f"step 0 0 {h(0.01)} 1000 {p}",  # at the threshold: dries
            f"step 1 1 0 600 {p}",  # 10 minutes dry: wetness 0, puddle follows
            f"step 1 1 0 300 {p}",  # half dried; puddle 0.75 capped by wetness 0.5
            f"step {h(0.5)} {h(0.2)} {h(0.4)} 100 {p}",  # at puddle min: puddle drains
            f"step {h(0.5)} {h(0.2)} {h(0.7)} {h(-5.0)} {p}",  # negative dt: no change
            f"step {h(0.5)} {h(0.2)} {h(0.7)} nan {p}",  # NaN dt: no change
        ],
    )
    v = [(f(a), f(b)) for a, b in rows]
    assert v[0] == (1.0, pytest.approx(0.25))
    assert v[1] == (1.0, 1.0)
    assert v[2] == (0.0, 0.0)
    assert v[3] == (0.0, 0.0)
    assert v[4] == (pytest.approx(0.5), pytest.approx(0.5))
    assert v[5][1] == pytest.approx(0.2 - 100.0 / 1200.0)
    assert v[6] == (0.5, 0.2) and v[7] == (0.5, 0.2)
    clamp = run(
        driver, ["clampsurf 2 3", f"clampsurf {h(0.3)} {h(0.8)}", "clampsurf -1 nan", f"clampsurf {h(0.5)} 0"]
    )
    assert [(f(a), f(b)) for a, b in clamp] == [(1.0, 1.0), (0.3, 0.3), (0.0, 0.0), (0.5, 0.0)]
    assert wp.clamp_surface(0.3, 0.8) == wp.Surface(0.3, 0.3)


def test_puddle_never_exceeds_wetness(driver):
    rng = random.Random(SEED + 1)
    s = wp.Surface()
    cmds, expected = [], []
    for _ in range(200):
        rain = rng.choice([0.0, 0.2, 0.45, 0.8, 1.0])
        dt = rng.uniform(0.0, 120.0)
        cmds.append(f"step {h(s.wetness)} {h(s.puddle)} {h(rain)} {h(dt)} {params_args(PARAMS)}")
        s = wp.step_surface(s, rain, dt, PARAMS)
        expected.append(s)
    for row, want in zip(run(driver, cmds), expected, strict=True):
        w, p = f(row[0]), f(row[1])
        assert 0.0 <= p <= w <= 1.0
        assert (w, p) == (want.wetness, want.puddle)


# ---- schedule ------------------------------------------------------------------------------------------


def sched_cmd(minutes: float, times: list[float]) -> str:
    return f"sched {h(minutes)} {len(times)} " + " ".join(h(t) for t in times)


def test_schedule_midnight_wrap(driver):
    times = list(CONFIG.schedule_times)  # 00:00 first
    late = [60.0, 600.0, 1200.0]  # first slot 01:00: before it, the last slot runs across midnight
    cases = [
        (times, 0.0, 0),
        (times, 179.999, 0),
        (times, 180.0, 1),
        (times, 1349.0, 8),
        (times, 1350.0, 9),
        (times, 1439.99, 9),
        (times, 1440.0, 0),
        (times, -1.0, 9),
        (times, 2 * 1440.0 + 510.0, 2),
        (times, math.nan, 0),
        (late, 0.0, 2),
        (late, 59.9, 2),
        (late, 60.0, 0),
        (late, 1439.0, 2),
        ([720.0], 0.0, 0),
        ([], 100.0, -1),
    ]
    out = run(driver, [sched_cmd(m, t) for t, m, _ in cases])
    assert [int(o[0]) for o in out] == [want for _, _, want in cases]
    assert [wp.schedule_index_at(m, t) for t, m, _ in cases] == [want for _, _, want in cases]


def test_shipped_schedule_slots():
    states = [(s.state, s.intensity) for s in CONFIG.schedule]
    by_time = {
        "02:59": ("rain", 0.3),
        "08:29": ("overcast", 0.0),
        "12:00": ("clear", 0.0),
        "16:45": ("rain", 1.0),
        "23:59": ("overcast", 0.0),
    }
    from golmok.lighting_presets import parse_hhmm

    for hhmm, want in by_time.items():
        assert states[wp.schedule_index_at(parse_hhmm(hhmm), list(CONFIG.schedule_times))] == want


# ---- 600 random cases vs weather_pure ------------------------------------------------------------------


def random_modifier(rng: random.Random) -> wp.Modifier:
    values = []
    for _, lo, hi, lo_ex in wp.MODIFIER_FIELDS:
        v = rng.uniform(lo, hi)
        if lo_ex and v <= lo:
            v = hi
        values.append(v)
    return wp.Modifier(*values)


def random_light(rng: random.Random) -> wp.Light:
    return wp.Light(
        lux=rng.uniform(0.0, 150000.0) if rng.random() < 0.3 else rng.uniform(0.0, 12.0),
        use_temperature=rng.random() < 0.7,
        kelvin=rng.uniform(1700.0, 12000.0),
        sky=rng.uniform(0.0, 10.0),
        fog=rng.uniform(0.0, 1.0),
        fog_height_falloff=rng.uniform(0.001, 2.0),
        exposure_overridden=rng.random() < 0.5,
        exposure_bias=rng.uniform(-5.0, 5.0),
    )


def test_random_cases_match_mirror(driver):
    rng = random.Random(SEED)
    cmds: list[str] = []
    checks: list[tuple[str, object]] = []
    for _ in range(120):
        light, m = random_light(rng), random_modifier(rng)
        if rng.random() < 0.1:
            m = IDENTITY
        cmds.append(f"apply {light_args(light)} {mod_args(m)}")
        checks.append(("apply", wp.apply(light, m)))
    for _ in range(120):
        a, b = random_modifier(rng), random_modifier(rng)
        t = rng.choice([rng.random(), rng.uniform(-0.5, 1.5)])
        cmds.append(f"lerp {mod_args(a)} {mod_args(b)} {h(t)}")
        checks.append(("lerp", wp.lerp_modifier(a, b, t)))
    for _ in range(120):
        alpha = rng.uniform(-0.2, 1.2)
        start, target = rng.random(), rng.random()
        cmds.append(f"precip {h(start)} {h(target)} {h(alpha)}")
        checks.append(("float", wp.precip_at(start, target, alpha)))
        cmds.append(f"palpha {h(alpha)} {int(target > start)}")
        checks.append(("float", wp.precip_alpha(alpha, target > start)))
    for _ in range(60):
        s = wp.clamp_surface(rng.random(), rng.random())
        rain = rng.choice([0.0, 0.005, 0.01, rng.random()])
        dt = rng.uniform(0.0, 300.0)
        p = wp.SurfaceParams(
            rng.uniform(1.0, 600.0),
            rng.uniform(1.0, 2000.0),
            rng.uniform(0.0, 0.99),
            rng.uniform(1.0, 900.0),
            900.0,
        )
        cmds.append(f"step {h(s.wetness)} {h(s.puddle)} {h(rain)} {h(dt)} {params_args(p)}")
        checks.append(("surface", wp.step_surface(s, rain, dt, p)))
    for _ in range(60):
        times = sorted(rng.sample(range(1440), rng.randint(1, 12)))
        minutes = rng.uniform(-1440.0, 3 * 1440.0)
        cmds.append(sched_cmd(minutes, [float(t) for t in times]))
        checks.append(("int", wp.schedule_index_at(minutes, [float(t) for t in times])))
    assert len(cmds) == 600
    for row, (kind, want) in zip(run(driver, cmds), checks, strict=True):
        if kind == "apply":
            assert apply_out(row) == light_tokens(want)
        elif kind == "lerp":
            got = [f(t) for t in row]
            for g, w in zip(got, want.values(), strict=True):
                assert g == pytest.approx(w, rel=1e-14, abs=1e-300)  # exp2/log2: same libm in practice
        elif kind == "float":
            assert bits(row) == [h(want)]
        elif kind == "surface":
            assert bits(row) == [h(want.wetness), h(want.puddle)]
        else:
            assert int(row[0]) == want
