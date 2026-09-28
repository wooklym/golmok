"""WAV analysis for PC audio verification (R53-5): the V-10 §7-1 measurements on synthetic signals.

Beds follow the WP-13 placeholder generator: uniform white noise through a 32-tap moving average at
48 kHz, about −26 dBFS RMS. Crossfades use the envelope shapes under test (linear amplitude, as in V-10,
and equal power, the T8 policy).
"""

import json
import struct
import wave

import numpy as np
import pytest

from golmok_tools.audio_analysis import (
    CLICK_Z,
    STOP_WITHIN_MS,
    abrupt_stop,
    analyse,
    click_score,
    clipping,
    dip,
    format_report,
    main,
    read_wav,
    rms_envelope,
    settle_time,
    silence_fraction,
    to_mono,
)

SR = 48000


def bed(seed, seconds, taps=32, sr=SR):
    """Placeholder-style bed: 0.5 × (32-tap moving average of uniform white noise) ≈ −26 dBFS RMS."""
    u = np.random.default_rng(seed).uniform(-1.0, 1.0, int(sr * seconds) + taps - 1)
    return 0.5 * np.convolve(u, np.ones(taps) / taps, mode="valid")


def crossfade(a, b, start, fade, curve="linear", sr=SR):
    """a → b from ``start`` over ``fade`` s (0 = hard switch)."""
    t = np.arange(len(a)) / sr
    x = np.clip((t - start) / fade, 0.0, 1.0) if fade > 0 else (t >= start).astype(float)
    if curve == "linear":
        return (1.0 - x) * a + x * b
    return np.cos(0.5 * np.pi * x) * a + np.sin(0.5 * np.pi * x) * b


def cut(y, at, ramp=0.0, sr=SR):
    """``y`` faded linearly to digital silence from ``at`` over ``ramp`` s (0 = hard cut)."""
    t = np.arange(len(y)) / sr
    a = np.clip(1.0 - (t - at) / ramp, 0.0, 1.0) if ramp > 0 else (t < at).astype(float)
    return a * y


def settle_of(fade, seed):
    # 1 s before, the fade, 1 s after: the final level is the post-fade second (tail_s = 1).
    seconds = 1.0 + fade + 1.0
    y = crossfade(bed(seed, seconds), bed(seed + 1, seconds), 1.0, fade)
    times, env = rms_envelope(y, SR)
    return settle_time(times, env, 1.0)


@pytest.mark.parametrize(("fade", "lo", "hi"), [(2.0, 1.6, 2.3), (1.0, 0.7, 1.1)])
def test_settle_time_of_linear_crossfade(fade, lo, hi):
    # Equal-level uncorrelated beds: power (1-a)² + a² is within 1 dB of the bed from a = 0.883, so the
    # expected settle is 0.883 × fade (1.77 s / 0.88 s) to the nearest 100 ms window centre. One window of
    # these beds scatters ±0.4 dB, and an excursion after the fade moves the settle time late (V-10: one
    # 3.0 s case among 12), so the median over five bed pairs is checked.
    values = [settle_of(fade, seed) for seed in range(10, 20, 2)]
    assert all(v is not None for v in values)
    assert lo <= float(np.median(values)) <= hi
    assert min(values) >= 0.7 * fade  # never settled before the crossfade was mostly done


def test_settle_time_edge_cases():
    times = np.arange(20) * 0.1 + 0.05
    flat = np.full(20, -30.0)
    assert settle_time(times, flat, 0.0) == pytest.approx(0.05)
    step = np.where(times < 0.8, -20.0, -30.0)
    assert settle_time(times, step, 0.0) == pytest.approx(0.85)
    assert settle_time(times, step, 5.0) is None  # nothing after start
    last_off = flat.copy()
    last_off[-1] = -20.0  # pulls the 1 s tail mean to −27.2 dB, and the last window is 7 dB off it
    assert settle_time(times, last_off, 0.0) is None
    assert settle_time(times, last_off, 0.0, tail_s=0.1) == pytest.approx(1.95)


def test_dip_linear_vs_equal_power_crossfade():
    # T8 rationale: a linear-amplitude crossfade of two uncorrelated equal-level beds halves the power at
    # the midpoint (−3.0 dB below the line), an equal-power (sin/cos) one keeps it. White-noise beds keep
    # the 100 ms RMS scatter at ±0.09 dB so the value itself is checked.
    a, b = bed(1, 4.0, taps=1), bed(2, 4.0, taps=1)
    for fade in (2.0, 1.0):
        lin_t, lin_env = rms_envelope(crossfade(a, b, 1.0, fade), SR)
        eq_t, eq_env = rms_envelope(crossfade(a, b, 1.0, fade, curve="equal_power"), SR)
        assert 2.5 <= dip(lin_t, lin_env, 1.0, 1.0 + fade) <= 3.5
        assert dip(eq_t, eq_env, 1.0, 1.0 + fade) < 0.5
    # On placeholder beds the ±0.4 dB scatter alone reads as a dip of up to ~1 dB; the linear crossfade
    # still dips clearly more than the equal-power one on the same material.
    a, b = bed(3, 4.0), bed(4, 4.0)
    lin = dip(*rms_envelope(crossfade(a, b, 1.0, 2.0), SR), 1.0, 3.0)
    eq = dip(*rms_envelope(crossfade(a, b, 1.0, 2.0, curve="equal_power"), SR), 1.0, 3.0)
    assert lin - eq > 1.0


def test_dip_uses_levels_either_side_and_validates_span():
    times = np.arange(40) * 0.1 + 0.05
    ramp = np.interp(times, [1.0, 3.0], [-20.0, -30.0])  # a straight dB ramp has no dip
    assert dip(times, ramp, 1.0, 3.0) == pytest.approx(0.0, abs=1e-9)
    notch = ramp.copy()
    notch[20] -= 4.0
    assert dip(times, notch, 1.0, 3.0) == pytest.approx(4.0, abs=0.05)
    assert dip(times, notch, 1.0, 3.0, level_s=0) == pytest.approx(4.0, abs=0.05)
    with pytest.raises(ValueError):
        dip(times, ramp, 2.0, 2.0)


def test_hard_cut_to_silence_is_an_abrupt_stop_not_an_inflated_click():
    y = cut(bed(5, 3.0), 2.0)  # the bed cut to digital silence at 2.0 s, no ramp
    ((t, drop, ramp),) = abrupt_stop(y, SR)
    assert t == pytest.approx(2.0, abs=0.001)
    assert drop > 60  # −26 dBFS bed to silence (levels are floored at −120 dB)
    assert 0.0 <= ramp <= STOP_WITHIN_MS
    # Silence is left out of the MAD, so the step at the cut is scored against the bed's own sigma:
    # |x| before the cut is 0.048 (0.93 × the bed RMS), z 3.5. With the silent half of the window in
    # the MAD it was 4769 (the PC self-test's hard cut: 160).
    z, zt = click_score(y, SR)
    assert z < CLICK_Z
    assert zt == pytest.approx(2.0, abs=0.001)
    assert silence_fraction(y, SR, zt) == pytest.approx(0.5, abs=0.02)
    y[int(1.95 * SR)] += 0.3  # a click in the audible material next to the silence still stands out
    z, zt = click_score(y, SR)
    assert z > 2 * CLICK_Z
    assert zt == pytest.approx(1.95, abs=0.001)


@pytest.mark.parametrize("ramp", [0.02, 0.25])
def test_fade_to_silence_is_neither_click_nor_abrupt_stop(ramp):
    y = cut(bed(6, 3.0), 2.0, ramp)
    assert abrupt_stop(y, SR) == []
    z, _ = click_score(y, SR)
    assert z < 5  # 2.6 and 2.8; with the silent part in the MAD 12.0 (20 ms) and 7.6 (250 ms)


def test_crossfades_stay_low():
    a, b = bed(5, 4.0), bed(6, 4.0)
    for fade in (2.0, 1.0):
        y = crossfade(a, b, 1.0, fade)
        z, _ = click_score(y, SR)
        assert z < 5  # steady placeholder beds stay at a few units
        assert abrupt_stop(y, SR) == []


@pytest.mark.parametrize(("ramp_ms", "listed"), [(0, True), (2, True), (5, True), (8, True), (12, False)])
def test_abrupt_stop_boundary_is_an_equivalent_linear_ramp(ramp_ms, listed):
    # A drop is abrupt when the 10 ms before the silence keep >= 1/3 of the reference power, which a
    # 10 ms linear ramp leaves; the duration is the ramp with the same power. White noise keeps 10 ms of
    # power within about ±0.3 dB, so the reported duration is the ramp itself.
    y = cut(bed(8, 0.5, taps=1), 0.3, ramp_ms / 1000.0)
    stops = abrupt_stop(y, SR)
    if not listed:
        assert stops == []
        return
    ((t, drop, dur),) = stops
    assert t == pytest.approx(0.3 + ramp_ms / 1000.0, abs=0.0005)  # where the silence starts
    assert dur == pytest.approx(ramp_ms, abs=1.0)
    assert drop > 60


def test_abrupt_stop_to_quieter_bed_and_dropout():
    a, b = bed(9, 1.0), bed(10, 1.0)
    t = np.arange(len(a)) / SR
    ((ts, drop, _),) = abrupt_stop(np.where(t < 0.5, a, 10 ** (-30 / 20) * b), SR)
    assert ts == pytest.approx(0.5, abs=0.001)
    assert 25.0 < drop < 35.0
    assert abrupt_stop(np.where(t < 0.5, a, 10 ** (-10 / 20) * b), SR) == []  # a 10 dB step is no stop
    assert abrupt_stop(np.where(t < 0.5, a, b), SR) == []  # nor is a hard switch between equal beds
    gap = a.copy()
    gap[int(0.5 * SR) : int(0.51 * SR)] = 0.0  # a 10 ms dropout
    ((ts, drop, _),) = abrupt_stop(gap, SR)
    assert ts == pytest.approx(0.5, abs=0.001)
    assert drop > 60
    assert abrupt_stop(np.zeros(SR), SR) == []
    assert abrupt_stop(a[:100], SR) == []


def test_click_spike_and_exclude():
    y = bed(7, 3.0)
    y[int(1.5 * SR)] += 0.3  # a one-sample spike, above the bed's peak of about 0.2
    z, t = click_score(y, SR)
    assert z > 2 * CLICK_Z
    assert t == pytest.approx(1.5, abs=0.001)
    z_ex, t_ex = click_score(y, SR, exclude=[(1.45, 1.55)])
    assert z_ex < CLICK_Z
    assert not 1.45 <= t_ex <= 1.55
    assert click_score(y, SR, exclude=[(0.0, 3.0)]) == (0.0, None)
    assert click_score(np.zeros(1), SR) == (0.0, None)


def test_clipping_and_peak():
    y = np.stack([bed(8, 1.0), bed(9, 1.0)], axis=1)
    count, peak = clipping(y)
    assert count == 0
    assert -16.0 < peak < -10.0
    y[100, 0] = 1.0
    y[200:204, 1] = -1.0
    y[300, 1] = 0.9995
    count, peak = clipping(y)
    assert count == 6
    assert peak == pytest.approx(0.0)
    assert clipping(np.zeros((10, 2))) == (0, pytest.approx(-120.0))


def test_rms_envelope_levels_and_times():
    square = np.tile([0.5, -0.5], SR // 2 * 3 // 2 + 7)  # 1.5 s + 14 samples: the partial window drops
    times, env = rms_envelope(square, SR)
    assert len(times) == 15
    assert times[:2] == pytest.approx([0.05, 0.15])
    assert env == pytest.approx(np.full(15, 20 * np.log10(0.5)))
    times, env = rms_envelope(np.zeros(SR), SR, window_ms=50.0)
    assert len(env) == 20
    assert env == pytest.approx(np.full(20, -120.0))


def write_pcm(path, frames, width):
    """Stereo/mono PCM via the stdlib writer (16- and 24-bit)."""
    scale = 2 ** (8 * width - 1)
    ints = np.clip(np.rint(frames * scale), -scale, scale - 1).astype(np.int64)
    raw = ints.astype("<i4").view(np.uint8).reshape(-1, 4)[:, :width] if width == 3 else ints.astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(frames.shape[1])
        w.setsampwidth(width)
        w.setframerate(SR)
        w.writeframes(raw.tobytes())
    return ints / scale


@pytest.mark.parametrize("width", [2, 3])
def test_read_wav_pcm_round_trip_and_mono(tmp_path, width):
    left, right = bed(10, 0.5), -0.5 * bed(11, 0.5)
    left[:4] = [0.999, -1.0, 0.0, -0.25]
    expected = write_pcm(tmp_path / "s.wav", np.stack([left, right], axis=1), width)
    samples, sr = read_wav(tmp_path / "s.wav")
    assert sr == SR
    assert samples.dtype == np.float32
    assert samples.shape == (len(left), 2)
    assert samples == pytest.approx(expected, abs=1e-6)
    assert to_mono(samples) == pytest.approx(expected.mean(axis=1), abs=1e-6)
    mono_expected = write_pcm(tmp_path / "m.wav", left[:, None], width)
    mono, _ = read_wav(tmp_path / "m.wav")
    assert mono.shape == (len(left), 1)
    assert to_mono(mono) == pytest.approx(mono_expected[:, 0], abs=1e-6)


def riff(fmt_body, data, data_size=None):
    size = len(data) if data_size is None else data_size
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt_body)) + fmt_body
    body += b"LIST" + struct.pack("<I", 3) + b"abc\0"  # odd-sized chunk before data, padded
    body += b"data" + struct.pack("<I", size) + data
    return b"RIFF" + struct.pack("<I", len(body)) + body


def fmt_chunk(tag, channels, bits, subformat=None):
    block = channels * bits // 8
    body = struct.pack("<HHIIHH", tag, channels, SR, SR * block, block, bits)
    if subformat is not None:  # WAVE_FORMAT_EXTENSIBLE: cbSize, valid bits, channel mask, SubFormat GUID
        guid = struct.pack("<H", subformat) + bytes.fromhex("000000001000800000aa00389b71")
        body = struct.pack("<HHIIHH", 0xFFFE, channels, SR, SR * block, block, bits)
        body += struct.pack("<HHI", 22, bits, 3) + guid
    return body


def test_read_wav_float_extensible_and_unfinalised(tmp_path):
    frames = np.array([[0.5, -0.25], [1.25, 0.0], [-1.0, 0.125]], dtype=np.float32)
    path = tmp_path / "f.wav"
    path.write_bytes(riff(fmt_chunk(3, 2, 32), frames.tobytes()))
    samples, sr = read_wav(path)
    assert sr == SR
    assert np.array_equal(samples, frames)  # float is returned as stored, even above full scale
    path.write_bytes(riff(fmt_chunk(0, 2, 32, subformat=3), frames.tobytes()))
    assert np.array_equal(read_wav(path)[0], frames)
    pcm = np.array([[16384, -32768], [-1, 32767]], dtype="<i2")
    # An unfinalised capture: data size 0xFFFFFFFF and a trailing half frame.
    path.write_bytes(
        riff(fmt_chunk(0, 2, 16, subformat=1), pcm.tobytes() + b"\x01\x02", data_size=0xFFFFFFFF)
    )
    assert read_wav(path)[0] == pytest.approx(pcm / 32768.0)
    path.write_bytes(b"RIFF\0\0\0\0WAVEjunk")
    with pytest.raises(ValueError, match="fmt"):
        read_wav(path)
    path.write_bytes(riff(fmt_chunk(7, 1, 8), b"\0\0"))  # mu-law
    with pytest.raises(ValueError, match="unsupported"):
        read_wav(path)
    path.write_bytes(b"not a wav file")
    with pytest.raises(ValueError, match="RIFF"):
        read_wav(path)


def test_cli_json_and_text(tmp_path, capsys):
    # 1 s bed A, 2 s linear crossfade to bed B, then a one-sample click at 3.5 s inside an excluded range.
    a, b = bed(12, 5.0), bed(13, 5.0)
    y = crossfade(a, b, 1.0, 2.0)
    y[int(3.5 * SR)] += 0.3
    write_pcm(tmp_path / "rec.wav", np.stack([y, y], axis=1), 2)
    wav = str(tmp_path / "rec.wav")
    assert main([wav, "--event", "1.0", "--fade", "2", "--exclude", "3.4:3.6", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["channels"] == 2 and report["clipping_count"] == 0
    assert report["rms_dbfs"] == pytest.approx(-26.0, abs=1.0)
    assert report["click"]["max_z"] < CLICK_Z and not report["click"]["click"]
    assert report["abrupt_stops"] == {
        "count": 0,
        "drop_db": 20.0,
        "within_ms": STOP_WITHIN_MS,
        "window_ms": 5.0,
        "first": [],
    }
    (event,) = report["events"]
    assert event["settle_span"] == [1.0, 4.0]
    assert 1.5 <= event["settle_s"] <= 2.3
    assert 2.0 <= event["dip_db"] <= 4.5
    assert event["before_db"] == pytest.approx(event["final_db"], abs=1.0)
    assert main([wav, "--event", "1.0"]) == 0
    text = capsys.readouterr().out
    assert "click z max" in text and "(threshold 8: click;" in text  # the spike is not excluded here
    assert "abrupt stops 0 (" in text
    assert "1.000" in text
    assert main([wav, "--silence-floor", "0.5", "--json"]) == 0  # everything below the floor: nothing scored
    report = json.loads(capsys.readouterr().out)
    assert report["click"]["max_z"] == 0.0 and report["click"]["t"] is None
    assert main([str(tmp_path / "missing.wav")]) == 2
    assert "error:" in capsys.readouterr().err


def test_report_lists_abrupt_stop_at_silence_boundary():
    report = analyse(cut(bed(5, 3.0), 2.0), SR)
    assert not report["click"]["click"]
    assert report["click"]["t"] == pytest.approx(2.0, abs=0.001)
    assert report["click"]["silence_fraction"] > 0.3
    stops = report["abrupt_stops"]
    assert stops["count"] == 1
    assert stops["first"][0]["t"] == pytest.approx(2.0, abs=0.001)
    assert report["events"] == [] and report["channels"] == 1
    text = format_report(report, "cut.wav")
    assert "is silence (|x| < 0.0001)" in text
    assert "abrupt stops 1 (drop >= 20 dB within <= 10 ms, 5 ms RMS): 2.000 s (drop 95 dB, ramp" in text
