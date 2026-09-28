"""Deterministic WAV generation and manifest-driven replacement safety."""

import importlib.util
import json
import wave
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/make_placeholder_audio.py"
spec = importlib.util.spec_from_file_location("wp13_generator", SCRIPT)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def test_deterministic_seed_and_pcm():
    a = generator.samples(13, True)
    assert a == generator.samples(13, True)
    assert a != generator.samples(14, True)
    values = np.frombuffer(a, dtype="<i2")
    assert len(values) == 48000 * 4
    assert 0 < np.max(np.abs(values.astype(np.int32))) < 32767


def test_generation_budget_and_preserve_real_audio(tmp_path):
    data = generator.load_config()
    item = data["assets"]["tile"]
    item.update(
        placeholder=False, license="CC0-1.0", license_url="https://creativecommons.org/publicdomain/zero/1.0/"
    )
    adopted = tmp_path / item["source"]
    adopted.parent.mkdir(parents=True)
    adopted.write_bytes(b"preserve adopted source")
    config = tmp_path / "audio.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    paths = generator.generate(config, tmp_path)
    assert len(paths) == 6
    assert adopted.read_bytes() == b"preserve adopted source"
    assert sum(Path(p).stat().st_size for p in paths) <= 40_000_000
    for path in paths:
        assert Path(path).stat().st_size <= 5_000_000
        with wave.open(path) as wav:
            assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 48000)
    assert (tmp_path / "ATTRIBUTION.md").read_bytes() == (tmp_path / "Credits/audio-credits.txt").read_bytes()
