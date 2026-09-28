"""Audio manifests reject unsafe provenance, paths, and broken playback references."""

import copy
import importlib
import json
import sys
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
