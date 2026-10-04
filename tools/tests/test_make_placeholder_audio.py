"""Deterministic WAV generation and manifest-driven replacement safety."""

import hashlib
import importlib.util
import json
import wave
from pathlib import Path

import numpy as np
import pytest
from audio_weighting import levels

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
            if Path(path).name == "rain.wav":
                assert wav.getnframes() == data["assets"]["rain"]["seconds"] * 48000
    rain_item = data["assets"]["rain"]
    with wave.open(str(tmp_path / rain_item["source"])) as wav:
        rain_pcm = wav.readframes(wav.getnframes())
    assert rain_pcm == generator.samples(
        rain_item["seed"], True, synthesis="rain", seconds=rain_item["seconds"]
    )
    assert rain_pcm != generator.samples(rain_item["seed"], True)
    assert (tmp_path / "ATTRIBUTION.md").read_bytes() == (tmp_path / "Credits/audio-credits.txt").read_bytes()


@pytest.mark.parametrize("seed", [0, 13, 1307, 2**32 - 1])
def test_rain_texture_spectrum_and_repeated_seams(seed, tmp_path):
    pcm = generator.samples(seed, True, synthesis="rain", seconds=24)
    assert pcm == generator.samples(seed, True, synthesis="rain", seconds=24)
    rain = np.frombuffer(pcm, dtype="<i2").astype(float)
    bed = np.frombuffer(generator.samples(seed, True), dtype="<i2").astype(float)
    frequency = np.fft.rfftfreq(len(rain), 1 / 48000)

    def spectrum(values):
        power = abs(np.fft.rfft(values)) ** 2
        return (np.fft.rfftfreq(len(values), 1 / 48000) * power).sum() / power.sum(), power

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


def test_rain_transients_change_envelope():
    seed = 1307
    rain = np.frombuffer(generator.samples(seed, True, synthesis="rain", seconds=24), dtype="<i2").astype(
        float
    )
    frequency = np.fft.rfftfreq(len(rain), 1 / 48000)
    band = np.minimum(np.clip((frequency - 1000) / 500, 0, 1), np.clip((8000 - frequency) / 1500, 0, 1))
    baseline = np.fft.irfft(np.fft.rfft(np.random.default_rng(seed).uniform(-1, 1, len(rain))) * band)

    def contrast(x):
        envelope = np.sqrt(np.mean(x.reshape(-1, 240) ** 2, axis=1))
        return 20 * np.log10(envelope.max() / np.median(envelope))

    assert contrast(rain) - contrast(baseline) >= 3


def test_generated_wavs_match_committed_lfs(tmp_path):
    for output in generator.generate(root=tmp_path):
        path = Path(output)
        committed = (generator.AUDIO / path.relative_to(tmp_path)).read_bytes()
        if committed.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
            expected = next(
                line.split(":", 1)[1]
                for line in committed.decode().splitlines()
                if line.startswith("oid sha256:")
            )
        else:
            expected = hashlib.sha256(committed).hexdigest()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, (
            f"{path.name}: regenerate WAVs and commit updated LFS objects"
        )


@pytest.mark.parametrize("field", ["Source", "Seed", "Synthesis", "Seconds"])
def test_python_only_aliases_rejected(field, tmp_path):
    data = generator.load_config()
    data["assets"]["rain"][field] = data["assets"]["rain"][field.lower()]
    config = tmp_path / "audio.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=f"assets.rain.{field}: expected {field.lower()}"):
        generator.generate(config, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_rain_k_weighted_gain_target():
    data = generator.load_config()
    weighted = {}
    for name in ("rain", "outdoor_day"):
        item = data["assets"][name]
        pcm = generator.samples(
            item["seed"], True, synthesis=item.get("synthesis", "default"), seconds=item.get("seconds")
        )
        samples = np.frombuffer(pcm, dtype="<i2").astype(float) / 32768 * item["gain"]
        if name == "rain":
            samples *= data["rain"]["gain_curve"][-1][1]
        weighted[name] = levels(samples)["K"]
    assert weighted["rain"] - weighted["outdoor_day"] == pytest.approx(-2, abs=0.02), (
        "C-08 목표를 바꾸면 목표값과 rain gain을 함께 고친다"
    )


@pytest.mark.parametrize("frequency, expected_a", [(100, -19.14), (1000, 0), (4000, 0.96), (10000, -2.49)])
def test_weighting_reference_tones(frequency, expected_a):
    x = np.sin(2 * np.pi * frequency * np.arange(48000) / 48000)
    measured = levels(x)
    assert measured["RMS"] == pytest.approx(-3.0103, abs=0.001)
    assert measured["A"] - measured["RMS"] == pytest.approx(expected_a, abs=0.03)
    # Independent scalar frequency-response calculation of the standard's two stages.
    z = np.exp(-2j * np.pi * frequency / 48000)
    response = np.polyval([1.19839281085285, -2.69169618940638, 1.53512485958697], z)
    response /= np.polyval([0.73248077421585, -1.69065929318241, 1], z)
    response *= (1 - z) ** 2 / np.polyval([0.99007225036621, -1.99004745483398, 1], z)
    assert measured["K"] == pytest.approx(-3.0103 + 20 * np.log10(abs(response)) - 0.691, abs=0.001)


@pytest.mark.parametrize("value", [None, True, 4, 15, 31, 24.0, "24"])
def test_invalid_rain_seconds_before_writes(value, tmp_path):
    data = generator.load_config()
    data["assets"]["rain"]["seconds"] = value
    config = tmp_path / "audio.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=r"assets.rain.seconds"):
        generator.generate(config, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_seconds_restricted_to_generated_rain(tmp_path):
    data = generator.load_config()
    data["assets"]["outdoor_day"]["seconds"] = 24
    config = tmp_path / "audio.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="only supported for rain loops"):
        generator.generate(config, tmp_path / "out")


def test_weighting_rate_and_997hz_reference():
    tone = np.sin(2 * np.pi * 997 * np.arange(48000) / 48000)
    assert levels(tone)["K"] == pytest.approx(-3.01, abs=0.01)
    with pytest.raises(ValueError, match="48000 Hz"):
        levels(tone, 44100)


@pytest.mark.parametrize("seed", [0, 13, 1307, 2**32 - 1])
def test_rain_schedule_properties(seed):
    count = 24 * 48000
    events = list(generator.rain_schedule(seed, count))
    assert len(events) == 24 * 9
    positions = np.sort([event[0] for event in events])
    gaps = np.diff(np.r_[positions, positions[0] + count])
    assert gaps.min() >= 1439
    assert gaps.std() / gaps.mean() > 0.5
    amplitudes = [event[1] for event in events]
    assert 20 * np.log10(max(amplitudes) / min(amplitudes)) >= 10
    assert all(0.003 <= event[2] <= 0.015 for event in events)
    with pytest.raises(ValueError, match="seconds"):
        generator.samples(seed, True, seconds=24)


def test_decreasing_rain_gain_rejected(tmp_path):
    data = generator.load_config()
    data["rain"]["gain_curve"] = [[0, 0], [0.5, 0.8], [1, 0.7]]
    config = tmp_path / "audio.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="rain.gain_curve: expected nondecreasing gains"):
        generator.generate(config, tmp_path / "out")
