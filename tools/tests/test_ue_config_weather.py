"""WP-16a: Config/Golmok/weather.json (design section 6) and the parser contract shared by C++ and Python.

golmok/weather_pure.py parse_config and GolmokWeather::ParseConfigText (Weather/GolmokWeatherConfig.cpp) apply
the same rules with byte-identical messages. ERROR_CASES is run here against the Python parser; the automation
test Golmok.Weather.Config (Tests/GolmokWeatherTest.cpp) runs the same table against the C++ parser, and
test_cpp_error_table_matches checks that its rows are exactly these. Each case replaces one single-line
snippet of the repo file (CRLF-safe: the file is read with newline translation, the C++ test strips "\\r").
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UE = ROOT / "unreal" / "Golmok"
WEATHER_JSON = UE / "Config" / "Golmok" / "weather.json"
MATH_H = UE / "Source" / "Golmok" / "Weather" / "GolmokWeatherMath.h"
CONFIG_CPP = UE / "Source" / "Golmok" / "Weather" / "GolmokWeatherConfig.cpp"
TEST_CPP = UE / "Source" / "Golmok" / "Tests" / "GolmokWeatherTest.cpp"
sys.path.insert(0, str(UE / "Content" / "Python"))
from golmok import weather_pure as wp  # noqa: E402

# (old snippet, replacement, expected message). Order and text are mirrored in GolmokWeatherTest.cpp.
ERROR_CASES = [
    ('"schema_version": 1,', '"schema_version": 1,,', "weather.json: root: not a JSON object"),
    ('"schema_version": 1,', '"schema_version": 2,', "weather.json: schema_version: must be 1"),
    ('"schema_version": 1,', '"schema_version": true,', "weather.json: schema_version: must be 1"),
    ('"mpc": "/Game/', '"snow": 1, "mpc": "/Game/', 'weather.json: root: unknown key "snow"'),
    ('"transition_seconds": 20.0,', "", 'weather.json: root: missing key "transition_seconds"'),
    (
        '"initial": {"state": "clear", "mode": "fixed"}',
        '"initial": "clear"',
        "weather.json: initial: must be an object",
    ),
    (
        '{"state": "clear", "mode"',
        '{"state": "snow", "mode"',
        "weather.json: initial.state: must be clear, overcast or rain",
    ),
    (
        '"initial": {"state": "clear"',
        '"initial": {"state": "rain"',
        "weather.json: initial.intensity: required for rain",
    ),
    (
        '{"state": "clear", "mode": "fixed"}',
        '{"state": "overcast", "mode": "fixed", "intensity": 0.5}',
        "weather.json: initial.intensity: only allowed for rain",
    ),
    ('"mode": "fixed"', '"mode": "random"', "weather.json: initial.mode: must be fixed or schedule"),
    (
        '"transition_seconds": 20.0',
        '"transition_seconds": 601',
        "weather.json: transition_seconds: must be a number in [0, 600]",
    ),
    ('"heavy": 1.0}', '"heavy": 1.5}', "weather.json: rain_levels.heavy: must be a number in [0.05, 1]"),
    (
        '"moderate": 0.6',
        '"moderate": 0.3',
        "weather.json: rain_levels: must increase strictly (light < moderate < heavy)",
    ),
    (
        '"modifiers": {',
        '"modifiers": {"clear": {},',
        "weather.json: modifiers.clear: clear is the identity and must not be listed",
    ),
    (
        '"lux_scale": 0.3,',
        '"lux_scale": 0,',
        "weather.json: modifiers.overcast.lux_scale: must be a number in (0, 2]",
    ),
    (
        '"lux_scale": 0.12',
        '"lux_scale": true',
        "weather.json: modifiers.rain.lux_scale: must be a number in (0, 2]",
    ),
    (
        '"kelvin_target": 7200.0',
        '"kelvin_target": 12000.5',
        "weather.json: modifiers.rain.kelvin_target: must be a number in [2000, 12000]",
    ),
    (
        '"exposure_offset": -0.2}',
        '"exposure_offset": -2.5}',
        "weather.json: modifiers.overcast.exposure_offset: must be a number in [-2, 2]",
    ),
    (
        '"exposure_offset": -0.4}',
        '"exposure_offset": -0.4, "tint": 1}',
        'weather.json: modifiers.rain: unknown key "tint"',
    ),
    ('"sky_scale": 0.8, ', "", 'weather.json: modifiers.rain: missing key "sky_scale"'),
    ('"wet_seconds"', '"Wet_seconds"', 'weather.json: surface: missing key "wet_seconds"'),
    (
        '"dry_seconds": 600.0',
        '"dry_seconds": 0',
        "weather.json: surface.dry_seconds: must be a positive number",
    ),
    (
        '"puddle_min_intensity": 0.4',
        '"puddle_min_intensity": 1.0',
        "weather.json: surface.puddle_min_intensity: must be a number in [0, 1)",
    ),
    ('"time": "03:00"', '"time": "3:00"', "weather.json: schedule[1].time: must be HH:MM (00:00-23:59)"),
    ('"time": "22:30"', '"time": "24:00"', "weather.json: schedule[9].time: must be HH:MM (00:00-23:59)"),
    (
        '"time": "13:00"',
        '"time": "08:30"',
        "weather.json: schedule[3].time: must be later than schedule[2].time",
    ),
    (
        '{"time": "16:30", "state": "rain", "intensity": 1.0}',
        '{"time": "16:30", "state": "rain"}',
        "weather.json: schedule[5].intensity: required for rain",
    ),
    (
        '"intensity": 0.6}',
        '"intensity": 0.01}',
        "weather.json: schedule[4].intensity: must be a number in [0.05, 1]",
    ),
    (
        '{"time": "03:00", "state": "overcast"}',
        '{"time": "03:00", "state": "overcast", "intensity": 0.3}',
        "weather.json: schedule[1].intensity: only allowed for rain",
    ),
    (
        '"system": "/Game/Golmok',
        '"system": "/Engine/Golmok',
        "weather.json: rain_fx.system: must be an object path /Game/.../Package.Object",
    ),
    ('"enabled": true', '"enabled": 1', "weather.json: rain_fx.enabled: must be true or false"),
    (
        '"max_spawn_rate": 12000',
        '"max_spawn_rate": 0',
        "weather.json: rain_fx.max_spawn_rate: must be a number in (0, 20000]",
    ),
    (
        "[1000, 1000, 500]",
        "[1000, 1000]",
        "weather.json: rain_fx.box_half_extent_cm: must be an array of 3 numbers",
    ),
    (
        "[1000, 1000, 500]",
        "[1000, 99, 500]",
        "weather.json: rain_fx.box_half_extent_cm[1]: must be a number in [100, 5000]",
    ),
    (
        '"height_offset_cm": 300',
        '"height_offset_cm": 3001',
        "weather.json: rain_fx.height_offset_cm: must be a number in [-1000, 3000]",
    ),
    (
        "MPC_GolmokWeather.MPC_GolmokWeather",
        "MPC_GolmokWeather",
        "weather.json: mpc: must be an object path /Game/.../Package.Object",
    ),
]


def repo_text() -> str:
    return WEATHER_JSON.read_text(encoding="utf-8")


# ---- the repo file ------------------------------------------------------------------------------------


def test_repo_weather_json_is_valid_with_design_values():
    c = wp.parse_config(repo_text())
    assert c == wp.load_config()
    assert c.schema_version == 1
    assert (c.initial_state, c.initial_intensity, c.initial_schedule) == ("clear", 0.0, False)
    assert c.transition_seconds == 20.0
    assert (c.rain_light, c.rain_moderate, c.rain_heavy) == (0.3, 0.6, 1.0)
    assert c.overcast == wp.Modifier(0.3, 1.0, 1.4, 0.8, 6800.0, 0.5, -0.2)
    assert c.rain == wp.Modifier(0.12, 0.8, 2.0, 0.6, 7200.0, 0.7, -0.4)
    assert c.surface == wp.SurfaceParams(60.0, 600.0, 0.4, 240.0, 1200.0)
    assert [(s.minutes, s.state, s.intensity) for s in c.schedule] == [
        (0.0, "rain", 0.3),
        (180.0, "overcast", 0.0),
        (510.0, "clear", 0.0),
        (780.0, "overcast", 0.0),
        (900.0, "rain", 0.6),
        (990.0, "rain", 1.0),
        (1020.0, "rain", 0.3),
        (1065.0, "overcast", 0.0),
        (1170.0, "clear", 0.0),
        (1350.0, "overcast", 0.0),
    ]
    assert c.schedule_times == tuple(s.minutes for s in c.schedule)
    assert c.rain_fx_system == "/Game/Golmok/Weather/NS_GolmokRain.NS_GolmokRain"
    assert c.rain_fx_enabled is True
    assert (c.max_spawn_rate, c.box_half_extent_cm, c.height_offset_cm) == (
        12000.0,
        (1000.0, 1000.0, 500.0),
        300.0,
    )
    assert c.mpc == "/Game/Golmok/Weather/MPC_GolmokWeather.MPC_GolmokWeather"


def test_initial_is_clear_fixed():
    """The default keeps every earlier screen, automation and runbook unchanged (design sections 0 and 4)."""
    raw = json.loads(repo_text())
    assert raw["initial"] == {"state": "clear", "mode": "fixed"}
    c = wp.load_config()
    assert wp.for_state(c.initial_state, c.initial_intensity, c.overcast, c.rain) == wp.Modifier()
    assert wp.is_identity(wp.for_state(c.initial_state, c.initial_intensity, c.overcast, c.rain))


def test_top_level_keys_in_schema_order():
    assert tuple(json.loads(repo_text())) == wp.TOP_LEVEL_KEYS


def test_cpp_defaults_match_repo_file():
    """FConfig's member defaults (GolmokWeatherConfig.h) are the shipped values."""
    header = (UE / "Source" / "Golmok" / "Weather" / "GolmokWeatherConfig.h").read_text(encoding="utf-8")
    c = wp.load_config()
    for member, value in (
        ("TransitionSeconds", c.transition_seconds),
        ("RainLight", c.rain_light),
        ("RainModerate", c.rain_moderate),
        ("RainHeavy", c.rain_heavy),
        ("MaxSpawnRate", c.max_spawn_rate),
        ("HeightOffsetCm", c.height_offset_cm),
    ):
        m = re.search(rf"\b{member}\s*=\s*([-0-9.]+)\s*;", header)
        assert m and float(m.group(1)) == value, member


def test_resolve_rain_level():
    c = wp.load_config()
    assert [wp.resolve_rain_level(c, w) for w in ("light", "moderate", "heavy")] == [0.3, 0.6, 1.0]
    assert wp.resolve_rain_level(c, "Heavy") is None
    assert wp.resolve_rain_level(c, "drizzle") is None
    assert wp.resolve_rain_level(c, "") is None


# ---- error table --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("old", "new", "message"), ERROR_CASES, ids=[m.split(": ", 2)[1] for _, _, m in ERROR_CASES]
)
def test_error_cases(old, new, message):
    text = repo_text()
    assert text.count(old) == 1, f"snippet must occur exactly once: {old!r}"
    with pytest.raises(ValueError) as info:
        wp.parse_config(text.replace(old, new))
    assert str(info.value) == message


def test_error_table_covers_the_required_kinds():
    reasons = {m.split(": ", 2)[2].split(" in ")[0].split('"')[0] for _, _, m in ERROR_CASES}
    assert len(ERROR_CASES) >= 12 and len(reasons) >= 12


def test_cpp_error_table_matches():
    """Golmok.Weather.Config holds ERROR_CASES verbatim, in order, as {TEXT(old), TEXT(new), TEXT(msg)}."""
    source = TEST_CPP.read_text(encoding="utf-8")
    block = re.search(r"// ---- error table begin.*?\n(.*?)// ---- error table end", source, re.S)
    assert block, "error table markers missing in GolmokWeatherTest.cpp"
    rows = [line.strip() for line in block.group(1).splitlines() if line.strip().startswith("{TEXT(")]

    def lit(text: str) -> str:
        return 'TEXT("' + text.replace("\\", "\\\\").replace('"', '\\"') + '")'

    assert rows == [f"{{{lit(o)}, {lit(n)}, {lit(m)}}}," for o, n, m in ERROR_CASES]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d.update(schedule=[]), "weather.json: schedule: must be a non-empty array"),
        (lambda d: d.update(schedule={}), "weather.json: schedule: must be a non-empty array"),
        (lambda d: d["schedule"].__setitem__(2, "clear"), "weather.json: schedule[2]: must be an object"),
        (lambda d: d["schedule"][0].pop("time"), 'weather.json: schedule[0]: missing key "time"'),
        (lambda d: d["schedule"][0].update(wind=1), 'weather.json: schedule[0]: unknown key "wind"'),
        (
            lambda d: d["schedule"][0].update(time=930),
            "weather.json: schedule[0].time: must be HH:MM (00:00-23:59)",
        ),
        (
            lambda d: d["schedule"][1].update(time="00:00"),
            "weather.json: schedule[1].time: must be later than schedule[0].time",
        ),
        (lambda d: d["modifiers"].pop("rain"), 'weather.json: modifiers: missing key "rain"'),
        (lambda d: d["modifiers"].update(snow={}), 'weather.json: modifiers: unknown key "snow"'),
        (lambda d: d["modifiers"].update(overcast=[]), "weather.json: modifiers.overcast: must be an object"),
        (
            lambda d: d["rain_levels"].update(light=0.0),
            "weather.json: rain_levels.light: must be a number in [0.05, 1]",
        ),
        (
            lambda d: d["rain_fx"].update(box_half_extent_cm="big"),
            "weather.json: rain_fx.box_half_extent_cm: must be an array of 3 numbers",
        ),
        (
            lambda d: d["rain_fx"].update(system=None),
            "weather.json: rain_fx.system: must be an object path /Game/.../Package.Object",
        ),
        (
            lambda d: d["rain_fx"].update(max_spawn_rate=20000.5),
            "weather.json: rain_fx.max_spawn_rate: must be a number in (0, 20000]",
        ),
        (
            lambda d: d["initial"].update(intensity=None),
            "weather.json: initial.intensity: only allowed for rain",
        ),
        (
            lambda d: d["initial"].update(state="rain", intensity=None),
            "weather.json: initial.intensity: must be a number in [0.05, 1]",
        ),
        (
            lambda d: d["surface"].update(wet_seconds=10**400),
            "weather.json: surface.wet_seconds: must be a positive number",
        ),
        (
            lambda d: d.update(transition_seconds=-0.5),
            "weather.json: transition_seconds: must be a number in [0, 600]",
        ),
        (lambda d: d.pop("schema_version"), "weather.json: schema_version: must be 1"),
        (lambda d: d.update(zz=1, aa=2), 'weather.json: root: unknown key "aa"'),
        (lambda d: d.pop("mpc") and d.pop("initial"), 'weather.json: root: missing key "initial"'),
    ],
)
def test_more_error_cases_python(mutate, message):
    """Cases the single-line replace table cannot express (the C++ parser follows the same code path)."""
    data = json.loads(repo_text())
    mutate(data)
    with pytest.raises(ValueError) as info:
        wp.parse_config(json.dumps(data))
    assert str(info.value) == message


@pytest.mark.parametrize("text", ["", "[]", "5", "null", '{"schema_version": NaN}', "{", '"weather"'])
def test_not_a_json_object(text):
    with pytest.raises(ValueError, match=r"^weather\.json: root: not a JSON object$"):
        wp.parse_config(text)


def test_accepted_edges():
    data = json.loads(repo_text())
    data["schema_version"] = 1.0
    data["transition_seconds"] = 0
    data["rain_levels"] = {"heavy": 1, "light": 0.05, "moderate": 0.5}  # key order is free
    data["initial"] = {"mode": "schedule", "intensity": 0.05, "state": "rain"}
    data["surface"]["puddle_min_intensity"] = 0
    data["schedule"] = [{"time": "23:59", "state": "rain", "intensity": 1}]
    data["rain_fx"]["box_half_extent_cm"] = [100, 5000, 100.0]
    data["rain_fx"]["max_spawn_rate"] = 20000
    data["rain_fx"]["height_offset_cm"] = -1000
    data["rain_fx"]["enabled"] = False
    data["modifiers"]["rain"]["kelvin_weight"] = 0
    c = wp.parse_config(json.dumps(data))
    assert (c.initial_state, c.initial_intensity, c.initial_schedule) == ("rain", 0.05, True)
    assert c.transition_seconds == 0.0 and c.rain_fx_enabled is False
    assert c.schedule_times == (1439.0,)
    assert c.box_half_extent_cm == (100.0, 5000.0, 100.0)
    assert isinstance(c.max_spawn_rate, float)


def test_load_config_missing_file(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(ValueError, match="cannot read file"):
        wp.load_config(missing)


# ---- contract constants (C++ header = Python) ---------------------------------------------------------


def header_string(name: str) -> str:
    m = re.search(rf'constexpr const char\* {name} = "([^"]*)";', MATH_H.read_text(encoding="utf-8"))
    assert m, name
    return m.group(1)


def test_contract_names_match_header():
    assert (
        tuple(header_string(n) for n in ("MpcRainIntensity", "MpcWetness", "MpcPuddleAmount"))
        == wp.MPC_PARAMETERS
    )
    assert tuple(header_string(n) for n in ("UserRainIntensity", "UserSpawnRate", "UserBoxHalfExtent")) == (
        wp.USER_PARAMETERS
    )
    assert wp.MPC_PARAMETERS == ("RainIntensity", "Wetness", "PuddleAmount")
    assert wp.USER_PARAMETERS == ("User.RainIntensity", "User.SpawnRate", "User.BoxHalfExtent")


def test_modifier_fields_match_header():
    text = MATH_H.read_text(encoding="utf-8")
    rows = re.findall(r'\{"([a-z_]+)", (-?[0-9.]+), (-?[0-9.]+), (true|false)\}', text)
    assert [(k, float(lo), float(hi), ex == "true") for k, lo, hi, ex in rows] == list(wp.MODIFIER_FIELDS)


def test_cpp_parser_uses_shared_ranges():
    """The C++ parser takes the modifier ranges from GolmokWeatherMath::ModifierField, not its own copy."""
    source = CONFIG_CPP.read_text(encoding="utf-8")
    assert "GolmokWeatherMath::ModifierField(" in source
    assert "GolmokClockMath::ParseHHMM(" in source
    for key in wp.TOP_LEVEL_KEYS + wp.SURFACE_KEYS + wp.RAIN_FX_KEYS + wp.RAIN_LEVEL_NAMES:
        assert f'TEXT("{key}")' in source, key
