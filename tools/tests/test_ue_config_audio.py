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
