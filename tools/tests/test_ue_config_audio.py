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
    configured = set(audio.load_config()["footsteps"].get("stride_cm_by_character", {}))
    assert configured <= ids, f"Unknown audio stride ids: {sorted(configured - ids)}"
    missing = ids - configured
    if missing:
        warnings.warn(
            f"Character ids without audio strides use 70/110 cm fallback: {sorted(missing)}",
            UserWarning,
            stacklevel=1,
        )


@pytest.mark.parametrize("field", ["loop", "placeholder", "author"])
@pytest.mark.parametrize("value", [1, "true"])
def test_asset_field_types_reject_coercion(field, value):
    if field == "author" and value == "true":
        value = True
    data = audio.load_config()
    data["assets"]["tile"][field] = value
    with pytest.raises(ValueError):
        audio.parse_config(data)
