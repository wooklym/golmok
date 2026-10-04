"""Deterministic WAV generation and manifest-driven replacement safety."""

import importlib.util
import json
import wave
from pathlib import Path

import numpy as np
import pytest

from golmok_tools import audio_analysis

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
    item["synthesis"] = "rain"  # Inert for adopted one-shots; replacement remains data-only.
    adopted = tmp_path / item["source"]
    adopted.parent.mkdir(parents=True)
    adopted.write_bytes(b"preserve adopted source")
    config = tmp_path / "audio.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    paths = generator.generate(config, tmp_path)
    assert len(paths) == len(data["assets"]) - 1
    assert adopted.read_bytes() == b"preserve adopted source"
    assert sum(Path(p).stat().st_size for p in paths) <= 40_000_000
    for path in paths:
        assert Path(path).stat().st_size <= 5_000_000
        with wave.open(path) as wav:
            assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 48000)
    rain_item = data["assets"]["rain"]
    with wave.open(str(tmp_path / rain_item["source"])) as wav:
        rain_pcm = wav.readframes(wav.getnframes())
    assert rain_pcm == generator.samples(rain_item["seed"], True, synthesis="rain")
    assert rain_pcm != generator.samples(rain_item["seed"], True)
    assert (tmp_path / "ATTRIBUTION.md").read_bytes() == (tmp_path / "Credits/audio-credits.txt").read_bytes()


@pytest.mark.parametrize("seed", [0, 13, 1307, 2**32 - 1])
def test_rain_texture_spectrum_and_repeated_seams(seed, tmp_path):
    pcm = generator.samples(seed, True, synthesis="rain")
    assert pcm == generator.samples(seed, True, synthesis="rain")
    rain = np.frombuffer(pcm, dtype="<i2").astype(float)
    bed = np.frombuffer(generator.samples(seed, True), dtype="<i2").astype(float)
    frequency = np.fft.rfftfreq(len(rain), 1 / 48000)

    def spectrum(values):
        power = abs(np.fft.rfft(values)) ** 2
        return (frequency * power).sum() / power.sum(), power

    centroid, power = spectrum(rain)
    bed_centroid, _ = spectrum(bed)
    assert 2500 < centroid < 6000
    assert centroid > 3 * bed_centroid
    assert power[(frequency >= 1000) & (frequency <= 8000)].sum() / power.sum() > 0.99
    path = tmp_path / "three-loops.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        wav.writeframes(pcm * 3)
    assert audio_analysis.main([str(path), "--check"]) == 0


@pytest.mark.parametrize("value", [None, True, 42, [], "Rain", "unknown"])
def test_invalid_synthesis_rejected_before_writes(value, tmp_path):
    data = generator.load_config()
    data["assets"]["rain"]["synthesis"] = value
    config = tmp_path / "audio.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=r"assets.rain.synthesis"):
        generator.generate(config, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_rain_synthesis_requires_generated_loop(tmp_path):
    data = generator.load_config()
    data["assets"]["tile"]["synthesis"] = "rain"
    config = tmp_path / "audio.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="rain requires a loop"):
        generator.generate(config, tmp_path / "out")
