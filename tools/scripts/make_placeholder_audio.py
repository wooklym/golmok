"""Generate deterministic WP-13 test WAVs. Never overwrites adopted audio."""

import argparse
import sys
import wave
from pathlib import Path

import numpy as np

PYTHON = Path(__file__).resolve().parents[2] / "unreal/Golmok/Content/Python"
sys.path.insert(0, str(PYTHON))
from golmok.audio_pure import AUDIO, CONFIG, load_config, source_path, write_credits  # noqa: E402


def samples(seed, loop, rate=48000, synthesis="default", seconds=None):
    if synthesis not in ("default", "rain") or (synthesis == "rain" and not loop):
        raise ValueError("synthesis: expected default, or rain for a loop")
    if seconds is not None and (
        type(seconds) is not int or not 16 <= seconds <= 30 or synthesis != "rain" or not loop
    ):
        raise ValueError("seconds: expected integer 16..30 for rain loops")
    count = rate * (seconds or 4) if loop else rate // 3
    rng = np.random.default_rng(seed)
    noise = rng.uniform(-1, 1, count)
    if synthesis == "rain":
        # Periodic FFT filtering keeps both the noise and droplets continuous at the seam.
        frequencies = np.fft.rfftfreq(count, 1 / rate)
        band = np.minimum(
            np.clip((frequencies - 1000) / 500, 0, 1), np.clip((8000 - frequencies) / 1500, 0, 1)
        )
        noise = np.fft.irfft(np.fft.rfft(noise) * band, n=count)
        # Minimum circular gap prevents conspicuous coincident clusters; exponential
        # residual gaps avoid a regular tick grid. Filter the summed droplets once.
        drops = round(count / rate * 9)
        gaps = rng.exponential(size=drops)
        gaps = 0.03 + gaps / gaps.sum() * (count / rate - drops * 0.03)
        offsets = (np.cumsum(gaps) * rate + rng.integers(count)).astype(int) % count
        burst = np.zeros(count)
        for offset in offsets:
            amplitude = np.exp(rng.uniform(np.log(0.6), np.log(3.3)))
            decay = rng.uniform(0.003, 0.015)
            length = int(rate * decay * 8)
            time = np.arange(length) / rate
            envelope = np.minimum(time / 0.001, 1) * np.exp(-time / decay)
            droplet = amplitude * rng.uniform(-1, 1, length) * envelope
            burst[(offset + np.arange(length)) % count] += droplet
        drop_band = np.minimum(
            np.clip((frequencies - 1000) / 500, 0, 1),
            np.clip((4000 - frequencies) / 500, 0, 1),
        )
        noise += np.fft.irfft(np.fft.rfft(burst) * drop_band, n=count)
        envelope = np.ones(count)
    elif loop:
        # Circular low-pass avoids an artificial filter startup transient at the seam.
        noise = sum(np.roll(noise, i) for i in range(32)) / 32
        envelope = np.ones(count)
    else:
        time = np.arange(count) / rate
        noise = 0.6 * noise + 0.4 * np.sin(2 * np.pi * 95 * time)
        envelope = np.exp(-time * 26) * np.minimum(time / 0.004, 1)
    signal = noise * envelope
    peak = np.max(np.abs(signal))
    return np.rint(signal * (0.2 * 32767 / peak)).astype("<i2").tobytes()


def generate(config=CONFIG, root=AUDIO):
    data = load_config(config)
    # All checks before writes; a mixed manifest may contain real adopted recordings.
    pending = []
    for item in data["assets"].values():
        if item["placeholder"] and item["license"] == "project-generated":
            pending.append((source_path(root, item["source"]), item))
    for path, item in pending:
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(48000)
            wav.writeframes(
                samples(
                    item["seed"],
                    item["loop"],
                    synthesis=item.get("synthesis", "default"),
                    seconds=item.get("seconds"),
                )
            )
    write_credits(data, root)
    return [str(path) for path, _ in pending]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--out", type=Path, default=AUDIO)
    args = parser.parse_args()
    for output in generate(args.config, args.out):
        print(output)
