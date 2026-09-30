"""Fake-Unreal import verifies failure propagation and manifest-only source swaps."""

import importlib
import json
import sys
import types
import wave
from pathlib import Path

import pytest

PYTHON = Path(__file__).resolve().parents[2] / "unreal/Golmok/Content/Python"
sys.path.insert(0, str(PYTHON))
pure = importlib.import_module("golmok.audio_pure")


class Asset:
    def __init__(self):
        self.properties = {}

    def set_editor_property(self, key, value):
        self.properties[key] = value

    def get_editor_property(self, key):
        return self.properties[key]


@pytest.fixture
def setup(tmp_path, monkeypatch):
    data = pure.load_config()
    data["assets"]["tile"]["source"] = "src/replacement/other.wav"
    for item in data["assets"].values():
        path = tmp_path / item["source"]
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wav:
            wav.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
            wav.writeframes(b"\0\0" * 480)
    config = tmp_path / "audio.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    sounds, seen = {}, []

    def execute(tasks):
        seen.extend(tasks)
        for task in tasks:
            props = task.properties
            name = props["destination_name"]
            path = f"{props['destination_path']}/{name}.{name}"
            task.properties["imported_object_paths"] = [path]
            sounds[path] = Asset()

    fake = types.SimpleNamespace(
        AssetImportTask=Asset,
        SoundWave=Asset,
        AssetToolsHelpers=types.SimpleNamespace(
            get_asset_tools=lambda: types.SimpleNamespace(import_asset_tasks=execute)
        ),
        load_asset=sounds.get,
        EditorAssetLibrary=types.SimpleNamespace(save_loaded_asset=lambda *a, **kw: True),
        log=lambda s: None,
    )
    monkeypatch.setitem(sys.modules, "unreal", fake)
    module = importlib.import_module("golmok.audio_import")
    monkeypatch.setattr(module, "unreal", fake)
    return module, fake, config, data, sounds, seen


def test_import_and_credit_source_swap(setup, tmp_path):
    module, _, config, data, sounds, seen = setup
    assert len(module.run(config, tmp_path)) == 7
    tile = sounds[data["assets"]["tile"]["asset"]]
    assert tile.properties == {"looping": False, "volume": data["assets"]["tile"]["gain"]}
    assert any(t.properties["filename"].endswith("other.wav") for t in seen)
    assert (tmp_path / "Credits/audio-credits.txt").is_file()


def test_bad_wav_prevents_all_editor_changes(setup, tmp_path):
    module, _, config, data, _, seen = setup
    (tmp_path / data["assets"]["landing"]["source"]).write_bytes(b"invalid WAV")
    with pytest.raises((wave.Error, EOFError)):
        module.run(config, tmp_path)
    assert seen == []


def test_failed_save_does_not_publish_credits(setup, tmp_path):
    module, fake, config, _, _, _ = setup
    fake.EditorAssetLibrary.save_loaded_asset = lambda *a, **kw: False
    with pytest.raises(RuntimeError, match="save failed"):
        module.run(config, tmp_path)
    assert not (tmp_path / "Credits/audio-credits.txt").exists()


@pytest.mark.parametrize("failure", ["empty_paths", "not_soundwave"])
def test_failed_import_does_not_replace_existing_credits(setup, tmp_path, failure):
    module, fake, config, _, sounds, _ = setup
    original_execute = fake.AssetToolsHelpers.get_asset_tools().import_asset_tasks
    credits = tmp_path / "Credits/audio-credits.txt"
    credits.parent.mkdir()
    credits.write_text("previous credits", encoding="utf-8")
    attribution = tmp_path / "ATTRIBUTION.md"
    attribution.write_text("previous attribution", encoding="utf-8")

    def execute(tasks):
        original_execute(tasks)
        if failure == "empty_paths":
            tasks[0].properties["imported_object_paths"] = []
        else:
            path = tasks[0].properties["imported_object_paths"][0]
            sounds[path] = object()

    fake.AssetToolsHelpers.get_asset_tools = lambda: types.SimpleNamespace(import_asset_tasks=execute)
    error, message = (
        (RuntimeError, "audio import failed") if failure == "empty_paths" else (TypeError, "not a SoundWave")
    )
    with pytest.raises(error, match=message):
        module.run(config, tmp_path)
    assert credits.read_text(encoding="utf-8") == "previous credits"
    assert attribution.read_text(encoding="utf-8") == "previous attribution"
