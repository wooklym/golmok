"""WAV analysis for PC audio verification (R53-5): the V-10 §7-1 measurements on synthetic signals.

Beds follow the WP-13 placeholder generator: uniform white noise through a 32-tap moving average at
48 kHz, about −26 dBFS RMS. Crossfades use the envelope shapes under test (linear amplitude, as in V-10,
and equal power, the T8 policy).
"""

import json
import math
import re
import struct
import wave

import numpy as np
import pytest

from golmok_tools import audio_analysis
from golmok_tools.audio_analysis import (
    CLICK_Z,
    MIN_AUDIBLE,
    SILENCE_FLOOR,
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
    smooth_envelope,
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


@pytest.mark.parametrize(("fade", "lo", "hi"), [(2.0, 1.7, 2.0), (1.0, 0.8, 1.0)])
def test_settle_time_of_linear_crossfade(fade, lo, hi):
    # Equal-level uncorrelated beds: power (1-a)² + a² is within 1 dB of the bed from a = 0.883, so the
    # expected settle is 0.883 × fade (1.77 s / 0.88 s) to the nearest 100 ms window centre. One window of
    # these beds scatters ±0.4 dB, and an excursion after the fade moves the settle time late (V-10: one
    # 3.0 s case among 12), so the median over five bed pairs is checked (1.85 s and 0.95 s; over 60 pairs
    # the median is the same).
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
    rms = float(np.sqrt(np.mean(y[: int(2.0 * SR)] ** 2)))
    assert z == pytest.approx(3.7 * abs(y[int(2.0 * SR) - 1]) / rms, rel=0.05)
    assert z < CLICK_Z
    assert zt == pytest.approx(2.0, abs=0.001)
    assert silence_fraction(y, SR, zt) == pytest.approx(0.5, abs=0.02)
    y[int(1.95 * SR)] += 0.3  # a click in the audible material next to the silence still stands out
    z, zt = click_score(y, SR)
    assert z > 2 * CLICK_Z
    assert zt == pytest.approx(1.95, abs=0.001)


def test_hard_cut_z_is_the_cut_sample_against_the_bed_sigma():
    # z at a hard cut to silence is |x at the cut| / the bed's sigma, 3.7 × |x_cut| / RMS for these beds
    # (RMS / sigma of a 32-tap moving average of uniform noise: 3.76; the local MAD scatters, 0.91-1.07
    # over 40 seeds). Where the cut sample is small the maximum is the bed's own (about 2.3), so the
    # maximum is the larger of the two for any seed; seeds 1 and 3 cut on a large sample and read z ≈ 10.
    k = int(0.3 * SR)
    for seed in range(8):
        y = cut(bed(seed, 0.45), 0.3)
        step = 3.7 * abs(y[k - 1]) / float(np.sqrt(np.mean(y[:k] ** 2)))
        rest, _ = click_score(y, SR, exclude=[(0.3, 0.3)])  # every sample but the cut (timed at 0.3 s)
        z, zt = click_score(y, SR)
        assert z == pytest.approx(max(step, rest), rel=0.1), seed
        if step > 1.1 * rest:
            assert zt == pytest.approx(0.3, abs=1e-6)


@pytest.mark.parametrize("ramp", [0.02, 0.04, 0.25])
def test_fade_to_silence_is_neither_click_nor_abrupt_stop(ramp):
    y = cut(bed(6, 3.0), 2.0, ramp)
    assert abrupt_stop(y, SR) == []
    z, _ = click_score(y, SR)
    assert z < 5  # 2.6, 2.9 and 2.8; with the silent part in the MAD 12.0 (20 ms) and 7.6 (250 ms)


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


@pytest.mark.parametrize(("t_step", "at_start"), [(0.14, True), (0.072, False)])
def test_exclude_ranges_include_both_ends(t_step, at_start):
    # A level step at sample k is one difference, timed at k. 0.14 × 48000 and 0.072 × 48000 are 6720 and
    # 3456 only up to rounding (6720.000000000001, 3455.9999999999995), which must not lose the step.
    k = round(t_step * SR)
    y = bed(14, 0.3)
    y[k:] += 0.3
    z, t = click_score(y, SR)
    assert z > 2 * CLICK_Z and t == pytest.approx(k / SR, abs=1e-9)
    z_ex, t_ex = click_score(y, SR, exclude=[(t_step, 0.25) if at_start else (0.01, t_step)])
    assert z_ex < CLICK_Z and t_ex != pytest.approx(k / SR, abs=1e-9)
    assert click_score(y, SR, exclude=[(t_step, t_step)])[0] < CLICK_Z  # a single instant
    off_by_one = ((k + 1) / SR, 0.25) if at_start else (0.01, (k - 1) / SR)
    assert click_score(y, SR, exclude=[off_by_one])[0] > 2 * CLICK_Z


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
    assert clipping(y.astype(np.float32)) == (6, pytest.approx(0.0))  # one channel at a time, in float64
    assert clipping(y[:, 1]) == (5, pytest.approx(0.0))
    y[400, 0] = np.nan  # not a clip and not the peak; analyse counts it as non-finite
    assert clipping(y) == (6, pytest.approx(0.0))
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


def chunk(chunk_id, body, pad=True):
    return chunk_id + struct.pack("<I", len(body)) + body + (b"\0" if pad and len(body) & 1 else b"")


def riff(fmt_body, data, data_size=None, after=b"", pad=True):
    size = len(data) if data_size is None else data_size
    body = b"WAVE" + chunk(b"fmt ", fmt_body)
    body += chunk(b"LIST", b"abc", pad=pad)  # odd-sized chunk before data, padded unless pad=False
    body += b"data" + struct.pack("<I", size) + data + after
    return b"RIFF" + struct.pack("<I", len(body)) + body


def fmt_chunk(tag, channels, bits, subformat=None, valid=None):
    block = channels * bits // 8
    body = struct.pack("<HHIIHH", tag, channels, SR, SR * block, block, bits)
    if subformat is not None:  # WAVE_FORMAT_EXTENSIBLE: cbSize, valid bits, channel mask, SubFormat GUID
        guid = struct.pack("<H", subformat) + bytes.fromhex("000000001000800000aa00389b71")
        body = struct.pack("<HHIIHH", 0xFFFE, channels, SR, SR * block, block, bits)
        body += struct.pack("<HHI", 22, valid or bits, 3) + guid
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
    with pytest.raises(ValueError, match="missing fmt"):
        read_wav(path)
    path.write_bytes(riff(fmt_chunk(7, 1, 8), b"\0\0"))  # mu-law
    with pytest.raises(ValueError, match="unsupported"):
        read_wav(path)
    path.write_bytes(b"not a wav file")
    with pytest.raises(ValueError, match="RIFF"):
        read_wav(path)


def test_read_wav_8_and_32_bit_pcm_float64_and_24_in_32(tmp_path):
    path = tmp_path / "w.wav"
    u8 = np.array([[0, 255], [128, 64]], dtype=np.uint8)  # unsigned, 128 is zero
    path.write_bytes(riff(fmt_chunk(1, 2, 8), u8.tobytes()))
    assert read_wav(path)[0] == pytest.approx((u8 - 128.0) / 128.0)
    i32 = np.array([[2**31 - 1, -(2**31)], [256, -12345678]], dtype="<i4")
    path.write_bytes(riff(fmt_chunk(1, 2, 32), i32.tobytes()))
    samples = read_wav(path)[0]
    assert samples.dtype == np.float32
    assert samples == pytest.approx(i32 / 2.0**31, rel=1e-7)
    f64 = np.array([[0.1, -0.7], [1.5, -(2.0**-30)]])
    path.write_bytes(riff(fmt_chunk(3, 2, 64), f64.tobytes()))
    assert np.array_equal(read_wav(path)[0], f64.astype(np.float32))
    # WAVE_FORMAT_EXTENSIBLE with 24 valid bits in 32-bit containers, left-justified (low byte zero).
    v24 = np.array([[2**23 - 1, -(2**23)], [1, -1]], dtype=np.int64)
    path.write_bytes(riff(fmt_chunk(0, 2, 32, subformat=1, valid=24), (v24 * 256).astype("<i4").tobytes()))
    assert np.array_equal(read_wav(path)[0], (v24 / 2.0**23).astype(np.float32))


def test_read_wav_zero_size_data_empty_data_and_unpadded_chunk(tmp_path, capsys):
    pcm = np.array([[16384, -32768], [-1, 32767], [5, -7]], dtype="<i2")
    path = tmp_path / "u.wav"
    # A streaming writer that stopped before patching the header: data size 0, the audio after it.
    path.write_bytes(riff(fmt_chunk(1, 2, 16), pcm.tobytes(), data_size=0))
    assert read_wav(path)[0] == pytest.approx(pcm / 32768.0)
    # Audio whose first four bytes happen to be printable is still audio: its "size" runs past the file.
    floats = np.array([[np.frombuffer(b"xyz>", "<f4")[0], 0.5], [-0.125, 0.75]], dtype=np.float32)  # 0.245
    path.write_bytes(riff(fmt_chunk(3, 2, 32), floats.tobytes(), data_size=0))
    assert np.array_equal(read_wav(path)[0], floats)
    # A really empty data chunk (at the end, or followed by another chunk) has no frames: an error, exit 2.
    for tail in (b"", chunk(b"LIST", b"INFOxy")):
        path.write_bytes(riff(fmt_chunk(1, 2, 16), b"", after=tail))
        with pytest.raises(ValueError, match="no audio frames"):
            read_wav(path)
        assert main([str(path), "--json"]) == 2
        assert "no audio frames (empty or unfinalised data chunk)" in capsys.readouterr().err
    path.write_bytes(riff(fmt_chunk(1, 2, 16), b"\x01\x02"))  # half a frame
    assert main([str(path)]) == 2
    capsys.readouterr()
    path.write_bytes(riff(fmt_chunk(1, 2, 16)[:14], pcm.tobytes()))
    with pytest.raises(ValueError, match=r"truncated fmt chunk \(14 bytes"):
        read_wav(path)
    # An odd-sized chunk written without its pad byte is still followed to the data chunk.
    path.write_bytes(riff(fmt_chunk(1, 2, 16), pcm.tobytes(), pad=False))
    assert read_wav(path)[0] == pytest.approx(pcm / 32768.0)


SR_SMALL = 4000  # brute force (one median of ±window per sample) stays fast at this rate


def brute_click_z(y, sr):
    """z of every sample by the definition of click_score (-1 where it is not scored); z[j] is at j + 1."""
    d = np.diff(y)
    audible = np.abs(y) >= SILENCE_FLOOR
    usable = audible[:-1] & audible[1:]
    half = round(sr * 0.1)
    z = np.full(d.size, -1.0)
    for j in range(d.size):
        lo, hi = max(0, j - half), min(d.size, j + half + 1)
        seg = d[lo:hi][usable[lo:hi]]
        if seg.size < MIN_AUDIBLE * (hi - lo):
            continue
        sigma = 1.4826 * np.median(np.abs(seg - np.median(seg))) if seg.size else 0.0
        z[j] = abs(d[j]) / max(sigma, 1e-5)
    return z


def edge_material(case):
    t = np.arange(int(1.5 * SR_SMALL)) / SR_SMALL
    if case == "silence":  # bed, 0.3 s of digital silence, bed
        y = bed(0, 1.5, taps=4, sr=SR_SMALL)
        y[(t >= 0.5) & (t < 0.8)] = 0.0
        return y
    if case == "gated":  # 20 ms gates, every other one 30 dB down
        return bed(1, 1.5, sr=SR_SMALL) * np.where((t * 1000 // 20) % 2 == 0, 1.0, 10 ** (-30 / 20))
    y = bed(0, 1.5, taps=4, sr=SR_SMALL)  # a -64 dBFS bed with +2 and -3 LSB steps, quantised to 16 bit
    y = y / np.sqrt(np.mean(y**2)) * 10 ** (-64 / 20) + (2 * (t >= 0.5) - 3 * (t >= 1.0)) / 32768
    return np.round(y * 32768) / 32768


@pytest.mark.parametrize("case", ["silence", "gated", "quantised"])
def test_click_score_matches_brute_force_on_edge_material(case):
    # The grid heuristic (pass 1) alone read 67.6 instead of 99.1 on the gated case and 2.43 instead of
    # 2.55 on the quantised one; the proven bound (pass 2) makes the maximum exact.
    y = edge_material(case)
    z_all = brute_click_z(y, SR_SMALL)
    z, t = click_score(y, SR_SMALL)
    assert z == pytest.approx(z_all.max(), rel=1e-12)
    assert z_all[round(t * SR_SMALL) - 1] == pytest.approx(z_all.max(), rel=1e-12)


def test_click_verdict_is_exact_when_the_maximum_is_not_proven(monkeypatch):
    y = edge_material("gated")
    top = brute_click_z(y, SR_SMALL).max()
    # More candidates than _MAX_EXACT (forced here): pass 2 only settles z >= threshold.
    monkeypatch.setattr(audio_analysis, "_MAX_EXACT", 0)
    first, _ = click_score(y, SR_SMALL, threshold=math.inf)  # nothing reaches it: the pass 1 value
    assert first < 0.75 * top
    for threshold in (0.8 * top, top, 1.01 * top):
        z, _ = click_score(y, SR_SMALL, threshold=threshold)
        assert (z >= threshold) == (top >= threshold)
        assert first <= z <= top


def test_one_channel_spike_and_cut_are_found_per_channel():
    left, right = bed(20, 3.0), bed(21, 3.0)
    left[int(1.5 * SR)] += 0.3
    report = analyse(np.stack([left, right], axis=1), SR)
    click = report["click"]
    assert click["click"] and click["channel"] == 0
    assert click["max_z"] > 2 * CLICK_Z  # 22.2 on the channel …
    assert click["mix"]["max_z"] < 0.8 * click["max_z"]  # … 15.5 in the mix of two uncorrelated beds
    assert click["t"] == pytest.approx(1.5, abs=0.001)
    assert click["channels"][0]["max_z"] == click["max_z"] and click["channels"][1]["max_z"] < 5
    text = format_report(report, "lr.wav")
    assert "click z max  22.2 at 1.500 s on ch 0 (threshold 8: click;" in text
    assert re.search(
        r"^ +mix 15\.5 at 1\.500 s, ch 0 22\.2 at 1\.500 s, ch 1 \d\.\d at \d\.\d{3} s$", text, re.M
    )
    left, right = bed(22, 3.0), bed(23, 3.0)
    report = analyse(np.stack([cut(left, 2.0), right], axis=1), SR)
    stops = report["abrupt_stops"]
    assert stops["count"] == 0  # the mix only halves in level
    ((stop,),) = [row["first"] for row in stops["channels"] if row["count"]]
    assert stops["channels"][0]["count"] == 1 and stops["channels"][1]["count"] == 0
    assert stop["t"] == pytest.approx(2.0, abs=0.001) and stop["drop_db"] > 60
    text = format_report(report, "lr.wav")
    assert "abrupt stops 0 in the mix (drop >= 20 dB" in text
    assert re.search(r"^ +ch 0: 1: 2\.000 s \(drop \d+ dB, ramp \d\.\d ms\)$", text, re.M)
    assert re.search(r"^ +ch 1: 0$", text, re.M)


def test_cli_json_and_text(tmp_path, capsys):
    # 1 s bed A, 2 s linear crossfade to bed B, then a one-sample click at 3.5 s inside an excluded range.
    a, b = bed(12, 5.0), bed(13, 5.0)
    y = crossfade(a, b, 1.0, 2.0)
    y[int(3.5 * SR)] += 0.3
    write_pcm(tmp_path / "rec.wav", np.stack([y, y], axis=1), 2)
    wav = str(tmp_path / "rec.wav")
    assert main([wav, "--event", "1.0", "--fade", "2", "--exclude", "3.4:3.6", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["channels"] == 2 and report["clipping_count"] == 0 and report["nonfinite_count"] == 0
    assert report["rms_dbfs"] == pytest.approx(-26.0, abs=1.0)
    assert report["click"]["max_z"] < CLICK_Z and not report["click"]["click"]
    assert report["click"]["channel"] is None  # equal channels: the mix is as high as either
    assert report["abrupt_stops"] == {
        "count": 0,
        "drop_db": 20.0,
        "within_ms": STOP_WITHIN_MS,
        "window_ms": 5.0,
        "first": [],
        "channels": [{"count": 0, "first": []}, {"count": 0, "first": []}],
    }
    (event,) = report["events"]
    assert event["settle_span"] == [1.0, 4.0]
    assert 1.5 <= event["settle_s"] <= 2.3
    assert 2.0 <= event["dip_db"] <= 4.5
    assert event["before_db"] == pytest.approx(event["final_db"], abs=1.0)
    assert "trace" not in event and "settle_s_smoothed" not in event and "check" not in report
    assert main([wav, "--event", "1.0"]) == 0
    text = capsys.readouterr().out
    assert "click z max" in text and "(threshold 8: click;" in text  # the spike is not excluded here
    assert "abrupt stops 0 in the mix (" in text
    # The event row: before, final, settle, dip and the dip span [1.0, 1.0 + settle] (no --fade).
    row = re.search(r"^  1\.000 +(-\d+\.\d) +(-\d+\.\d) +(\d\.\d\d) +(\d\.\d)  1\.00-(\d\.\d\d)$", text, re.M)
    assert row is not None
    assert float(row[3]) == pytest.approx(float(row[5]) - 1.0, abs=0.006)
    assert "within ±1 dB of the final level, the energy mean of the last 1 s of [t, t + 3 s])" in text
    assert main([wav, "--silence-floor", "0.5", "--json"]) == 0  # everything below the floor: nothing scored
    report = json.loads(capsys.readouterr().out)
    assert report["click"]["max_z"] == 0.0 and report["click"]["t"] is None
    assert main([str(tmp_path / "missing.wav")]) == 2
    assert "error:" in capsys.readouterr().err


def test_report_uses_the_given_settle_tolerance_and_tail():
    y = crossfade(bed(12, 4.0), bed(13, 4.0), 1.0, 2.0)
    text = format_report(analyse(y, SR, events=[1.0], tol_db=0.5, tail_s=0.5), "x.wav")
    assert (
        "settle = within ±0.5 dB of the final level, the energy mean of the last 0.5 s of [t, t + 3 s]"
        in text
    )


def test_trace_adds_the_envelope_and_a_smoothed_settle(tmp_path, capsys):
    y = crossfade(bed(12, 5.0), bed(13, 5.0), 1.0, 2.0)
    (row,) = analyse(y, SR, events=[1.0], fade_s=2.0, trace=True)["events"]
    times, env = rms_envelope(y, SR)
    shown = (times >= 0.7) & (times < 4.0)  # from 0.3 s before the event to the end of its span
    assert row["trace"]["t"] == pytest.approx(times[shown])
    assert row["trace"]["db"] == pytest.approx(env[shown], abs=0.005)
    assert row["trace"]["t"][0] == pytest.approx(0.75) and len(row["trace"]["t"]) == 33
    assert 1.5 <= row["settle_s_smoothed"] <= 2.0  # 1.85; the 100 ms envelope reads 1.75 on this pair
    write_pcm(tmp_path / "rec.wav", y[:, None], 2)
    assert main([str(tmp_path / "rec.wav"), "--event", "1", "--fade", "2", "--trace", "--json"]) == 0
    (event,) = json.loads(capsys.readouterr().out)["events"]
    assert len(event["trace"]["db"]) == 33 and event["settle_s_smoothed"] is not None
    assert main([str(tmp_path / "rec.wav"), "--event", "1", "--fade", "2", "--trace"]) == 0
    text = capsys.readouterr().out
    assert "trace (100 ms RMS dB from t - 0.3 s; smoothed settle on the 300 ms energy mean)" in text
    assert re.search(r"^  1\.000 s: smoothed settle \d\.\d\d s$", text, re.M)
    assert re.search(r"^ +0\.750 ( +-\d+\.\d){10}$", text, re.M)


def test_smooth_envelope():
    env = np.array([-30.0, -20.0, -30.0, -30.0])
    power = 10 ** (env / 10)
    smooth = smooth_envelope(env, 0.1)  # 300 ms: three windows, two at the ends
    assert smooth == pytest.approx(
        10 * np.log10([power[:2].mean(), power[:3].mean(), power[1:].mean(), 1e-3])
    )
    assert smooth_envelope(env, 0.3) == pytest.approx(env)  # one window is already 300 ms


def test_check_exit_status(tmp_path, capsys):
    clean = bed(16, 1.0)
    cases = {
        "clean": clean.copy(),
        "click": clean.copy(),
        "abrupt stop": cut(clean, 0.6),
        "clipping": clean.copy(),
    }
    cases["click"][SR // 2] += 0.3
    cases["clipping"][SR // 2 : SR // 2 + 3] = 1.0
    for name, y in cases.items():
        wav = str(tmp_path / f"{name.replace(' ', '_')}.wav")
        write_pcm(wav, y[:, None], 2)
        assert main([wav]) == 0  # without --check the exit status only says that the analysis ran
        assert not re.search(r"^check ", capsys.readouterr().out, re.M)
        assert main([wav, "--check"]) == (0 if name == "clean" else 1), name
        verdict = capsys.readouterr().out.splitlines()[-1]
        if name == "clean":
            assert verdict == "check        pass (no click, abrupt stop, clipping or NaN/Inf)"
        else:
            assert verdict.startswith("check        FAIL: ") and name in verdict, verdict
        assert main([wav, "--check", "--json"]) == (0 if name == "clean" else 1)
        check = json.loads(capsys.readouterr().out)["check"]
        assert check == {"pass": name == "clean", "failed": [] if name == "clean" else check["failed"]}
        assert name == "clean" or name in check["failed"]


def test_json_has_no_nan_or_infinity(tmp_path, capsys):
    y = bed(17, 0.5).astype(np.float32)
    y[100], y[200] = np.nan, np.inf
    path = tmp_path / "nan.wav"
    path.write_bytes(riff(fmt_chunk(3, 1, 32), y.tobytes()))
    assert main([str(path), "--json", "--check"]) == 1
    out = capsys.readouterr().out
    report = json.loads(out, parse_constant=lambda c: pytest.fail(f"JSON constant {c}"))
    assert report["nonfinite_count"] == 2
    assert report["rms_dbfs"] is None and report["peak_dbfs"] is None
    assert "non-finite samples" in report["check"]["failed"]
    assert main([str(path)]) == 0
    assert "non-finite   2 samples (NaN/Inf)" in capsys.readouterr().out


def test_report_lists_abrupt_stop_at_silence_boundary():
    report = analyse(cut(bed(5, 3.0), 2.0), SR)
    assert not report["click"]["click"]
    assert report["click"]["t"] == pytest.approx(2.0, abs=0.001)
    assert report["click"]["silence_fraction"] > 0.3
    assert report["click"]["channel"] is None and len(report["click"]["channels"]) == 1
    stops = report["abrupt_stops"]
    assert stops["count"] == 1
    assert stops["first"][0]["t"] == pytest.approx(2.0, abs=0.001)
    assert stops["channels"] == [{"count": 1, "first": stops["first"]}]
    assert report["events"] == [] and report["channels"] == 1
    text = format_report(report, "cut.wav")
    assert "is silence (|x| < 0.0001)" in text
    assert "abrupt stops 1 (drop >= 20 dB within <= 10 ms, 5 ms RMS): 2.000 s (drop 95 dB, ramp" in text
    assert not re.search(r"^ +(ch \d|mix )", text, re.M) and "in the mix" not in text  # one channel
