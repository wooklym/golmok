"""Audio manifests reject unsafe provenance, paths, and broken playback references."""

import copy
import importlib
import json
import sys
import warnings
from pathlib import Path

import pytest

PYTHON = Path(__file__).resolve().parents[2] / "unreal/Golmok/Content/Python"
sys.path.insert(0, str(PYTHON))
audio = importlib.import_module("golmok.audio_pure")


def test_manifest_and_credit_contract():
    data = audio.load_config()
    assert set(data["ambience"]) == {"outdoor_day", "outdoor_night", "interior"}
    assert data["footsteps"]["sets"]["default"]
    credits = audio.attribution(data)
    assert (audio.AUDIO / "ATTRIBUTION.md").read_text(encoding="utf-8") == credits
    assert (audio.AUDIO / "Credits/audio-credits.txt").read_text(encoding="utf-8") == credits
    for item in data["assets"].values():
        assert item["author"] in credits
        assert item["changes"] in credits
        assert item["source_url"] in credits


def test_all_lighting_cycle_presets_are_mapped():
    lighting = json.loads((audio.CONFIG.parent / "lighting_presets.json").read_text(encoding="utf-8"))
    assert set(audio.load_config()["preset_states"]) == set(lighting["cycle"])


@pytest.mark.parametrize(
    "source", ["../bad.wav", "src/../../bad.wav", "C:/tmp/a.wav", "src/a/../../x.wav", "src\\a\\b.wav"]
)
def test_unsafe_source(source):
    data = audio.load_config()
    data["assets"]["asphalt"]["source"] = source
    with pytest.raises(ValueError):
        audio.parse_config(data)


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(master_volume=float("nan")),
        lambda d: d.update(master_volume=True),
        lambda d: d.update(schema_version=True),
        lambda d: d["assets"]["tile"].update(license="CC-BY-NC-4.0"),
        lambda d: d["assets"]["tile"].update(asset=d["assets"]["asphalt"]["asset"]),
        lambda d: d["ambience"].update(outdoor_day="asphalt"),
        lambda d: d["footsteps"]["sets"].update(tile=[]),
        lambda d: d["footsteps"].update(landing="missing"),
        lambda d: d["footsteps"].update(pitch_range=[1.2, 0.8]),
    ],
)
def test_invalid_playback_contract(change):
    data = audio.load_config()
    change(data)
    with pytest.raises(ValueError):
        audio.parse_config(data)


def test_adopted_cc_by_survives_credit_pipeline():
    data = copy.deepcopy(audio.load_config())
    data["assets"]["tile"].update(
        placeholder=False,
        license="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        author="Test author",
        changes="Trimmed and normalized",
    )
    assert "Test author" in audio.attribution(data)
    assert "Trimmed and normalized" in audio.attribution(data)
    assert "https://creativecommons.org/licenses/by/4.0/" in audio.attribution(data)
    assert data["assets"]["tile"]["verified"] in audio.attribution(data)


def test_source_symlink_cannot_escape(tmp_path):
    outside = tmp_path / "outside.wav"
    outside.write_bytes(b"not audio")
    root = tmp_path / "Audio"
    root.mkdir()
    try:
        (root / "escape.wav").symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError):
        audio.source_path(root, "escape.wav")


@pytest.mark.parametrize(
    "value", [None, [], {"missing": 1}, {"interior": -1}, {"interior": True}, {"interior": float("nan")}]
)
def test_invalid_state_fade(value):
    data = audio.load_config()
    data["crossfade_seconds_by_state"] = value
    with pytest.raises(ValueError):
        audio.parse_config(data)


def test_partial_state_fade_and_legacy_default():
    data = audio.load_config()
    data["crossfade_seconds_by_state"] = {"interior": 1.0}
    audio.parse_config(data)
    del data["crossfade_seconds_by_state"]
    audio.parse_config(data)


@pytest.mark.parametrize("value", [None, "", "2026-9-28", "2026-02-30", "0000-01-01", "2026-09-28T00:00:00"])
def test_invalid_verified_date(value):
    data = audio.load_config()
    data["assets"]["tile"]["verified"] = value
    with pytest.raises(ValueError):
        audio.parse_config(data)


@pytest.mark.parametrize("value", [None, True, -0.01, 5.01, float("nan"), "0.25"])
def test_invalid_photo_fade(value):
    data = audio.load_config()
    data["photo_mute_fade_seconds"] = value
    with pytest.raises(ValueError):
        audio.parse_config(data)


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {"Manny": {"walk": 67, "run": 146}},
        {"manny": {"walk": 67}},
        {"manny": {"walk": True, "run": 146}},
        {"manny": {"walk": 0, "run": 146}},
        {"manny": {"walk": 67, "run": float("nan")}},
        {"manny": {"walk": 67, "run": 146, "extra": 1}},
    ],
)
def test_invalid_character_strides(value):
    data = audio.load_config()
    data["footsteps"]["stride_cm_by_character"] = value
    with pytest.raises(ValueError):
        audio.parse_config(data)


def test_optional_stride_and_photo_fade_contract():
    data = audio.load_config()
    assert data["footsteps"]["stride_cm_by_character"]["proxy110"] == {"walk": 45, "run": 115}
    data["photo_mute_fade_seconds"] = 0
    audio.parse_config(data)
    del data["photo_mute_fade_seconds"]
    del data["footsteps"]["stride_cm_by_character"]
    audio.parse_config(data)
    data["footsteps"]["stride_scale_by_mesh"] = True
    with pytest.raises(ValueError, match="superseded"):
        audio.parse_config(data)


def test_stride_ids_match_character_roster():
    roster = json.loads((audio.CONFIG.parent / "characters.json").read_text(encoding="utf-8"))
    ids = {entry["id"] for entry in roster["characters"]}
    steps = audio.load_config()["footsteps"]
    configured = set(steps.get("stride_cm_by_character", {}))
    assert configured <= ids, (
        f"Unknown audio stride ids: {sorted(configured - ids)}; "
        "roster id를 바꾸거나 지웠다면 footsteps.stride_cm_by_character도 같은 PR에서 갱신"
    )
    missing = ids - configured
    if missing:
        warnings.warn(
            f"Character ids without audio strides use {steps['walk_stride_cm']}/"
            f"{steps['run_stride_cm']} cm fallback: {sorted(missing)}",
            UserWarning,
            stacklevel=1,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("loop", 1),
        ("loop", "true"),
        ("placeholder", 1),
        ("placeholder", "true"),
        ("author", 1),
        ("author", True),
    ],
)
def test_asset_field_types_reject_coercion(field, value):
    data = audio.load_config()
    data["assets"]["tile"][field] = value
    with pytest.raises(
        ValueError,
        match=rf"assets\.tile\.{field}:.*" + ("single-line text" if field == "author" else "booleans"),
    ):
        audio.parse_config(data)


@pytest.mark.parametrize(
    ("path", "value", "expected"),
    [
        (("master_volume",), True, "master_volume: expected finite number"),
        (("assets", "tile", "gain"), "0.5", "assets.tile.gain: expected finite number"),
        (("assets", "tile", "verified"), "2026-02-30", "assets.tile.verified: expected valid calendar date"),
        (
            ("footsteps", "stride_cm_by_character", "manny", "walk"),
            0,
            "footsteps.stride_cm_by_character.manny.walk: expected finite number",
        ),
        (("footsteps", "pitch_range"), [True, 1], "footsteps.pitch_range[0]: expected finite number"),
        (("footsteps", "sets", "tile"), [True], "footsteps.sets.tile[0]: expected nonempty single-line text"),
        (
            ("preset_states", "overcast_morning"),
            True,
            "preset_states.overcast_morning: expected nonempty single-line text",
        ),
        (("assets", "tile"), None, "assets.tile: expected object"),
    ],
)
def test_diagnostic_identifies_field_and_expectation(path, value, expected):
    data = audio.load_config()
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError) as caught:
        audio.parse_config(data)
    assert expected in str(caught.value)


def test_numeric_surface_value_is_not_a_string_set_id():
    data = audio.load_config()
    data["footsteps"]["sets"]["1"] = ["asphalt"]
    data["footsteps"]["surface_sets"]["4"] = 1
    with pytest.raises(ValueError, match=r"footsteps\.surface_sets\.4:.*single-line text"):
        audio.parse_config(data)


def test_roster_warning_uses_configured_fallback(monkeypatch):
    data = audio.load_config()
    data["footsteps"].update(walk_stride_cm=81, run_stride_cm=123)
    del data["footsteps"]["stride_cm_by_character"]["manny"]
    monkeypatch.setattr(audio, "load_config", lambda: data)
    with pytest.warns(UserWarning, match="81/123 cm fallback.*manny"):
        test_stride_ids_match_character_roster()


def test_unknown_roster_id_explains_same_pr_contract(monkeypatch):
    data = audio.load_config()
    data["footsteps"]["stride_cm_by_character"]["typo"] = {"walk": 70, "run": 110}
    monkeypatch.setattr(audio, "load_config", lambda: data)
    with pytest.raises(AssertionError, match="roster id.*같은 PR에서 갱신"):
        test_stride_ids_match_character_roster()


@pytest.mark.parametrize("value", [None, True, 1, [], {}, "", "Notify", "bad"])
def test_invalid_footstep_driver(value):
    data = audio.load_config()
    data["footsteps"]["driver"] = value
    with pytest.raises(ValueError, match="footsteps.driver: expected auto, distance or notify"):
        audio.parse_config(data)


@pytest.mark.parametrize("value", ["auto", "distance", "notify"])
def test_footstep_driver_keeps_credit_pipeline(value):
    data = audio.load_config()
    baseline = audio.attribution(data)
    data["footsteps"]["driver"] = value
    audio.parse_config(data)
    assert audio.attribution(data) == baseline
    del data["footsteps"]["driver"]
    audio.parse_config(data)  # Legacy manifests use auto at runtime.


@pytest.mark.parametrize(
    "path,key",
    [
        ((), "photo_mute_fade_seconds"),
        ((), "footsteps"),
        ((), "rain"),
        (("rain",), "gain_curve"),
        (("rain",), "interior_gain"),
        (("assets", "asphalt"), "placeholder"),
        (("assets", "asphalt"), "license_url"),
        (("ambience",), "outdoor_day"),
        (("crossfade_seconds_by_state",), "interior"),
        (("footsteps",), "driver"),
        (("footsteps",), "stride_cm_by_character"),
        (("footsteps", "stride_cm_by_character", "manny"), "walk"),
    ],
)
@pytest.mark.parametrize("keep_canonical", [False, True])
def test_runtime_known_key_alias_rejected(path, key, keep_canonical):
    data = audio.load_config()
    data.setdefault("crossfade_seconds_by_state", {})["interior"] = 1
    data["footsteps"].setdefault("stride_cm_by_character", {})["manny"] = {"walk": 100, "run": 150}
    obj = data
    for part in path:
        obj = obj[part]
    value = obj.get(key, "auto")
    if not keep_canonical:
        obj.pop(key, None)
    obj[key.upper()] = value
    field = ".".join((*path, key.upper()))
    with pytest.raises(ValueError) as error:
        audio.parse_config(data)
    assert str(error.value) == f"{field}: expected {key}"


def test_alias_validation_preserves_extensions_and_dynamic_ids():
    data = audio.load_config()
    data["Extension"] = {"DRIVER": "extension data"}
    data["assets"]["asphalt"]["Extension"] = True
    data["footsteps"]["Extension"] = True
    data["preset_states"]["DRIVER"] = "outdoor_day"
    data["footsteps"]["sets"]["DRIVER"] = data["footsteps"]["sets"]["default"]
    data["footsteps"]["stride_cm_by_character"] = {"driver": {"walk": 100, "run": 150}}
    assert audio.parse_config(data) is data


@pytest.mark.parametrize(
    "pairs",
    [
        '"driver":"auto","Driver":"notify"',
        '"Driver":"notify","driver":"auto"',
    ],
)
def test_python_retains_both_case_distinct_driver_keys(pairs):
    data = audio.load_config()
    data["footsteps"].pop("driver", None)
    data["footsteps"].update(json.loads("{" + pairs + "}"))
    assert list(data["footsteps"])[-2:] == list(json.loads("{" + pairs + "}"))
    with pytest.raises(ValueError, match=r"footsteps\.Driver: expected driver"):
        audio.parse_config(data)


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, "rain: expected object"),
        ({}, "rain.asset: expected nonempty single-line text without table separators"),
        ([], "rain: expected object"),
        (
            {"asset": "asphalt", "gain_curve": [[0, 0], [1, 1]], "interior_gain": 0.35},
            "rain.asset: expected looping asset id",
        ),
    ],
)
def test_invalid_rain_section(value, expected):
    data = audio.load_config()
    data["rain"] = value
    with pytest.raises(ValueError) as caught:
        audio.parse_config(data)
    assert str(caught.value) == expected


@pytest.mark.parametrize(
    "curve, expected",
    [
        pytest.param([], "rain.gain_curve: expected 2..32 [intensity, gain] points", id="empty"),
        pytest.param([[0, 0]], "rain.gain_curve: expected 2..32 [intensity, gain] points", id="one"),
        pytest.param(
            [
                [0.0, 0.0],
                [0.03125, 0.03125],
                [0.0625, 0.0625],
                [0.09375, 0.09375],
                [0.125, 0.125],
                [0.15625, 0.15625],
                [0.1875, 0.1875],
                [0.21875, 0.21875],
                [0.25, 0.25],
                [0.28125, 0.28125],
                [0.3125, 0.3125],
                [0.34375, 0.34375],
                [0.375, 0.375],
                [0.40625, 0.40625],
                [0.4375, 0.4375],
                [0.46875, 0.46875],
                [0.5, 0.5],
                [0.53125, 0.53125],
                [0.5625, 0.5625],
                [0.59375, 0.59375],
                [0.625, 0.625],
                [0.65625, 0.65625],
                [0.6875, 0.6875],
                [0.71875, 0.71875],
                [0.75, 0.75],
                [0.78125, 0.78125],
                [0.8125, 0.8125],
                [0.84375, 0.84375],
                [0.875, 0.875],
                [0.90625, 0.90625],
                [0.9375, 0.9375],
                [0.96875, 0.96875],
                [1.0, 1.0],
            ],
            "rain.gain_curve: expected 2..32 [intensity, gain] points",
            id="33 increasing points",
        ),
        pytest.param(
            [[0, 0], [0.5, 0.3], [0.5, 0.5], [1, 1]],
            "rain.gain_curve: expected strictly increasing intensities",
            id="duplicate x",
        ),
        pytest.param(
            [[0, 0], [0.7, 0.3], [0.5, 0.5], [1, 1]],
            "rain.gain_curve: expected strictly increasing intensities",
            id="descending x",
        ),
        pytest.param(
            [[0, 0], [0.5, 0.8], [1, 0.7]],
            "rain.gain_curve: expected nondecreasing gains",
            id="decreasing gain",
        ),
        pytest.param(
            [[0, 0], [0.5, 0.6], [0.5, 0.4], [1, 1]],
            "rain.gain_curve: expected strictly increasing intensities",
            id="x before gain",
        ),
        pytest.param(
            [[0.1, 0], [1, 1]],
            "rain.gain_curve: expected first point [0, 0] and final intensity 1",
            id="first x",
        ),
        pytest.param(
            [[0, 0.1], [1, 1]],
            "rain.gain_curve: expected first point [0, 0] and final intensity 1",
            id="first gain",
        ),
        pytest.param(
            [[0, 0], [0.9, 1]],
            "rain.gain_curve: expected first point [0, 0] and final intensity 1",
            id="last x",
        ),
        pytest.param(
            [[0, 0], [-0.1, 0.5], [1, 1]],
            "rain.gain_curve.intensity: expected finite number in [0, 1]: -0.1",
            id="negative x",
        ),
        pytest.param(
            [[0, 0], [1.01, 0.5], [1, 1]],
            "rain.gain_curve.intensity: expected finite number in [0, 1]: 1.01",
            id="high x",
        ),
        pytest.param(
            [[0, 0], [True, 0.5], [1, 1]],
            "rain.gain_curve.intensity: expected finite number in [0, 1]: True",
            id="bool x",
        ),
        pytest.param(
            [[0, 0], ["0.5", 0.5], [1, 1]],
            "rain.gain_curve.intensity: expected finite number in [0, 1]: '0.5'",
            id="string x",
        ),
        pytest.param(
            [[0, 0], [float("nan"), 0.5], [1, 1]],
            "rain.gain_curve.intensity: expected finite number in [0, 1]: nan",
            id="nan x",
        ),
        pytest.param(
            [[0, 0], [float("inf"), 0.5], [1, 1]],
            "rain.gain_curve.intensity: expected finite number in [0, 1]: inf",
            id="inf x",
        ),
        pytest.param(
            [[0, 0], [0.5, -0.1], [1, 1]],
            "rain.gain_curve.gain: expected finite number in [0, 1]: -0.1",
            id="negative gain",
        ),
        pytest.param(
            [[0, 0], [1, 1.01]],
            "rain.gain_curve.gain: expected finite number in [0, 1]: 1.01",
            id="high gain",
        ),
        pytest.param(
            [[0, 0], [1, True]],
            "rain.gain_curve.gain: expected finite number in [0, 1]: True",
            id="bool gain",
        ),
        pytest.param(
            [[0, 0], [1, float("nan")]],
            "rain.gain_curve.gain: expected finite number in [0, 1]: nan",
            id="nan gain",
        ),
        pytest.param([[0, 0], [1]], "rain.gain_curve: expected [intensity, gain]"),
        pytest.param([[0, 0], "bad"], "rain.gain_curve: expected [intensity, gain]"),
    ],
)
def test_invalid_rain_curve(curve, expected):
    data = audio.load_config()
    data["rain"]["gain_curve"] = curve
    with pytest.raises(ValueError) as caught:
        audio.parse_config(data)
    assert str(caught.value) == expected


@pytest.mark.parametrize("gain", [None, True, -1, 1.01, float("inf")])
def test_invalid_rain_indoor_gain(gain):
    data = audio.load_config()
    data["rain"]["interior_gain"] = gain
    with pytest.raises(ValueError) as caught:
        audio.parse_config(data)
    assert str(caught.value) == f"rain.interior_gain: expected finite number in [0, 1]: {gain!r}"


def test_rain_optional_and_asset_replacement_is_data_only():
    data = audio.load_config()
    data["rain"]["asset"] = "outdoor_night"
    assert audio.parse_config(data) is data
    del data["rain"]
    assert audio.parse_config(data) is data


@pytest.mark.parametrize("key", ["stride_scale_by_mesh", "STRIDE_SCALE_BY_MESH", "Stride_Scale_By_Mesh"])
def test_obsolete_stride_key_case_rejected(key):
    data = audio.load_config()
    data["footsteps"][key] = True
    with pytest.raises(ValueError, match="superseded by stride_cm_by_character"):
        audio.parse_config(data)


def test_runtime_python_known_key_names_match():
    # Compare the real key lists, including optional sections, not a duplicated expected registry.
    import ast
    import re
    from collections import Counter

    tree = ast.parse(Path(audio.__file__).read_text(encoding="utf-8"))
    python_lists = Counter(
        tuple(sorted(ast.literal_eval(node.args[1])))
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "key_case"
    )
    cpp = (audio.PROJECT / "Source/Golmok/Audio/GolmokAudioConfig.cpp").read_text(encoding="utf-8")
    cpp_lists = Counter(
        tuple(sorted(re.findall(r'TEXT\("([^"\n]+)"\)', body)))
        for body in re.findall(r"\.KeyCase\(\{(.*?)\}\)", cpp, re.S)
    )
    assert python_lists == cpp_lists


def test_unknown_rain_asset_has_exact_diagnostic():
    data = audio.load_config()
    data["rain"]["asset"] = "unregistered_rain"
    with pytest.raises(ValueError) as caught:
        audio.parse_config(data)
    assert str(caught.value) == "rain.asset: expected looping asset id"


@pytest.mark.parametrize(
    "curve",
    [
        [[0, 0], [0.5, 0.5], [1, 0.5]],
        [[i / 31, i / 31] for i in range(32)],
    ],
)
def test_rain_plateau_and_maximum_points_accepted(curve):
    data = audio.load_config()
    data["rain"]["gain_curve"] = curve
    assert audio.parse_config(data) is data
