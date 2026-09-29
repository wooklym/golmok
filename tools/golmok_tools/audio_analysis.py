"""WAV analysis for PC audio verification: the V-10 method (pc-verify-wp13.md §7-1) as a repository tool.

Input is a master-submix recording (``unreal.AudioMixerLibrary.start_recording_output`` →
``stop_recording_output(..., WAV_FILE, ...)``) or a WASAPI loopback capture. Measures:

- ``rms_envelope``: non-overlapping 100 ms RMS of the mono mix in dBFS (plain RMS re full scale, so a
  full-scale square wave is 0 dB and a full-scale sine −3 dB), floored at −120 dB.
- ``settle_time``: time after an event at which the envelope enters and then stays within ±1 dB of its
  final level ("1 dB 안착"). The final level is the energy mean of the last ``tail_s`` of the span. For a
  linear-amplitude crossfade between two uncorrelated equal-level beds the power is (1-a)² + a² of the
  bed, which is within 1 dB of it from a = 0.88, so the settle time is about 0.88 × the fade (1.77 s for
  2 s) to the nearest window. One 100 ms RMS value of the 32-tap moving-average placeholder beds
  scatters by about ±0.4 dB (1 σ), so a single late excursion can push the settle time towards the end
  of the span (V-10 saw one 3.0 s case among 12); read it with the level trace (``--trace``, which also
  gives the settle time on a 300 ms energy mean of the envelope).
- ``click_score``: first difference of the mono signal divided by a local robust sigma
  (1.4826 × MAD over ±``window_ms``, centred), maximum |z| outside excluded ranges (footstep one-shots).
  The runbook threshold is z ≥ 8 (``CLICK_Z``). On a continuous bed z stays at a few units (placeholder
  beds: 2.3) and a spike or a large level jump stands out (a one-sample 0.3 spike: z ≈ 22). Digital
  silence is kept out of the sigma: a sample is silent when |x| < ``silence_floor`` (1e-4 ≈ −80 dBFS),
  the MAD uses only differences between two non-silent samples, and a sample is scored only when at least
  ``min_audible`` (25 %) of its ±window are such differences. Measured on placeholder beds (six seeds):
  a 20 ms and a 250 ms linear fade to silence read z ≈ 2.5 and 2.9 (without the rule 12–16 and 7–11,
  because the MAD collapsed once half the window was silence), and a hard cut to silence is the step
  against the bed's own sigma, z ≈ 3.7 × |x at the cut| / bed RMS (2.4–6.5; without the rule thousands,
  the PC self-test's hard cut 160). A cut on a sample above about 2.1 × the RMS (~3 % of random cut
  points) still reads ≥ 8, which is a real step; ``abrupt_stop`` lists cuts either way. Material quieter
  than the floor counts as silence, and on beds close to it the waveform's near-zero samples drop out as
  well (bed at −65 dBFS RMS: 14 % of samples, z 6–8 % higher). A remaining limit: a hard switch
  between two uncorrelated beds of similar level is a step of about one bed amplitude, only a few times
  the bed's own sample-to-sample change for 32-tap moving-average noise (z ≈ 2–13), so a low z does not
  show that a crossfade happened; the settle time does.
  The report scores the mono mix and each channel and gives the largest z with its channel, so a defect
  on one channel is not diluted by the others (a one-sample 0.3 spike on the left channel of two
  uncorrelated beds: z 15.5 in the mix, 22.2 on the channel). Not every sample is scored with its own
  window (one median of ±window per sample): the MAD is evaluated on a grid of window/4 steps and
  samples are then re-scored exactly in two passes. Pass 1 takes those whose z against 0.95 × the smaller
  neighbouring grid sigma beats the running maximum, a heuristic bound that matches brute force on
  ordinary material but not always next to silence, on gated material or on 16-bit beds a few LSB loud.
  Pass 2 takes those whose z against a proven lower bound of the sigma between two grid points beats it
  (``_shorth_sigma``); when there are at most ``_MAX_EXACT`` (1000) of them the maximum is exact.
  Bounded-difference noise such as the placeholder beds has many samples close to its maximum; there
  the pass 1 maximum is kept and only samples whose bound reaches the threshold are re-scored, so the
  verdict (z ≥ 8 or not) is always exact.
- ``abrupt_stop``: level drops of ≥ 20 dB (``drop_db``) that complete within ≤ 10 ms (``within_ms``) on
  5 ms RMS windows (``window_ms``): hard cuts, cuts to silence or to a much quieter bed, and dropouts of
  about 5 ms or more. "Within 10 ms" is judged as an equivalent linear ramp: the 10 ms before the quiet
  onset must still carry at least 1/3 of the reference power (the 100 ms before them), which is what a
  linear ramp to silence of exactly 10 ms leaves; ``duration_ms`` is that equivalent ramp length. Linear
  ramps to silence on placeholder beds (300 seeds each): hard cut flagged 300/300 (0–9.4 ms; 2998/3000 in
  a larger run), 5 ms ramp 95 %, 10 ms 43 %, 12 ms 13 %, 15 ms 1 %, 20, 40 and 250 ms 0 %. The drop is
  read on one 5 ms window, so it scatters by about ±2 dB there (a hard cut to a bed 15 dB quieter was
  listed 2 times in 100, one 30 dB quieter 100 times).
  The report lists them for the mono mix and for each channel (a cut on one channel of a stereo bed
  lowers the mix by 3-6 dB only, so it is seen on the channel).
- ``dip``: largest drop of the envelope below the straight line (in dB) between the levels before and
  after a transition (the crossfade "중간 dip": 3 dB for a linear-amplitude crossfade of two uncorrelated
  equal-level beds, 0 dB for equal-power). On the placeholder beds the ±0.4 dB window scatter alone
  reads as a dip of up to ~1 dB, so compare curves on the same material.
- ``clipping``: samples at or above 0.999 of full scale and the peak level.

Usage (run from ``tools/``; deliberately no console script, pyproject is a shared file)::

    python -m golmok_tools.audio_analysis rec.wav --event 12.3 40.2 --fade 2 --exclude 30.1:30.5 [--json]
    [--silence-floor 1e-4] [--trace] [--check]

``--event`` times are key presses/state changes in seconds from the start of the file. For each event the
settle time is measured over ``[event, event + --span]`` (default: crossfade + 1 s with ``--fade``, else
3 s; never past the next event). Keep the span short: over a long steady stretch one 1 dB noise excursion
is almost certain and moves the settle time to its end. The dip is measured over ``[event, event + --fade]``
(or ``[event, event + settle]`` without ``--fade``). ``--trace`` adds each event's 100 ms envelope over
``[event − 0.3 s, end of span)`` and the settle time on its 300 ms energy mean. The exit status is 0 when
the analysis ran (not a pass), 2 when the file could not be read; with ``--check`` it is 1 when a click
(z ≥ 8), an abrupt stop (mix or any channel), clipping or a non-finite sample was found. JSON has no
NaN/Infinity: non-finite values are written as null.

Cost: the mix and each channel are click-scored one after the other. Scoring one signal takes about 35
bytes per sample at its peak (float64 difference, two z bounds, masks) besides the float32 samples and
the float64 mix. A 183 s 48 kHz stereo file of placeholder beds: about 20 s and 0.37 GB above the
samples (mix only, before per-channel scoring: 6 s and 0.45 GB).
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np

CLICK_Z = 8.0  # runbook §7-1: z >= 8 is a click
FLOOR_DB = -120.0
LEVEL_S = 0.3  # steady level before/after a transition: energy mean over this many seconds
SMOOTH_S = 0.3  # --trace: the smoothed settle uses the energy mean over this span of envelope windows
MAD_TO_SIGMA = 1.4826  # MAD of a normal distribution × 1.4826 = sigma
SILENCE_FLOOR = 1e-4  # |x| below this (−80 dBFS) is digital silence for the click sigma
MIN_AUDIBLE = 0.25  # a sample is click-scored only if this share of its ±window is non-silent
STOP_DROP_DB = 20.0  # abrupt stop: level drop of at least this …
STOP_WITHIN_MS = 10.0  # … completed within this (as an equivalent linear ramp)
STOP_WINDOW_MS = 5.0  # short-window RMS for abrupt stops
STOPS_LISTED = 5  # the report lists this many abrupt stops (and counts all)

_WAVE_FORMAT_PCM = 0x0001
_WAVE_FORMAT_IEEE_FLOAT = 0x0003
_WAVE_FORMAT_EXTENSIBLE = 0xFFFE


# ---------------------------------------------------------------------------------------------------------
# Reading


def _chunk_header_ok(raw: memoryview, pos: int, fits: bool = False) -> bool:
    """A plausible chunk header at ``pos``: four printable ASCII bytes and a size field (``fits``: whose
    chunk also ends within the file)."""
    if pos + 8 > len(raw) or not all(0x20 <= c <= 0x7E for c in raw[pos : pos + 4]):
        return False
    return not fits or pos + 8 + int.from_bytes(raw[pos + 4 : pos + 8], "little") <= len(raw)


def read_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Read a RIFF/WAVE file → (float32 samples [n, channels], sample rate).

    PCM 8/16/24/32-bit and IEEE float 32/64-bit, plain or WAVE_FORMAT_EXTENSIBLE. PCM maps to -1..1;
    float data is returned as stored (it may exceed ±1). A data chunk whose size runs past the end of the
    file (an unfinalised capture) is read up to the last whole frame, and so is one whose size is still 0
    with bytes after it (a streaming writer that stopped before patching the header), unless those bytes
    are another whole chunk. An odd-sized chunk written without its pad byte is followed when the padded
    position holds no chunk header and the unpadded one does. A file without a whole frame of audio is an
    error. The stdlib ``wave`` module is not used because Python 3.11's rejects float and
    WAVE_FORMAT_EXTENSIBLE files (common for loopback).
    """
    raw = memoryview(Path(path).read_bytes())
    if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise ValueError(f"{path}: not a RIFF/WAVE file")
    fmt = data = None
    pos = 12
    while pos + 8 <= len(raw):
        chunk_id = bytes(raw[pos : pos + 4])
        size = int.from_bytes(raw[pos + 4 : pos + 8], "little")
        start = pos + 8
        if chunk_id == b"fmt ":
            fmt = bytes(raw[start : start + size])
        elif chunk_id == b"data" and data is None:
            if size == 0 and start < len(raw) and not _chunk_header_ok(raw, start, fits=True):
                data = raw[start:]  # size never patched: the audio runs to the end of the file
                break
            data = raw[start : start + size]
        end = start + size
        if size & 1 and not _chunk_header_ok(raw, end + 1) and _chunk_header_ok(raw, end):
            pos = end  # the writer left out the pad byte
        else:
            pos = end + (size & 1)
    if fmt is None:
        raise ValueError(f"{path}: missing fmt chunk")
    if len(fmt) < 16:
        raise ValueError(f"{path}: truncated fmt chunk ({len(fmt)} bytes, need 16)")
    if data is None:
        raise ValueError(f"{path}: missing data chunk")
    tag, channels, rate, _byte_rate, block_align, _bits = struct.unpack("<HHIIHH", fmt[:16])
    if tag == _WAVE_FORMAT_EXTENSIBLE:
        if len(fmt) < 26:
            raise ValueError(f"{path}: truncated WAVE_FORMAT_EXTENSIBLE fmt chunk")
        tag = int.from_bytes(fmt[24:26], "little")  # first two bytes of the SubFormat GUID
    if channels < 1 or rate < 1 or block_align < channels or block_align % channels:
        raise ValueError(f"{path}: bad fmt (channels={channels}, rate={rate}, block_align={block_align})")
    width = block_align // channels  # container bytes per sample (24-in-32 files are left-justified)
    frames = len(data) // block_align
    if frames == 0:
        raise ValueError(f"{path}: no audio frames (empty or unfinalised data chunk)")
    buf = data[: frames * block_align]
    if tag == _WAVE_FORMAT_PCM and width == 1:
        x = np.frombuffer(buf, dtype=np.uint8).astype(np.float32)
        x -= 128.0
        x /= 128.0
    elif tag == _WAVE_FORMAT_PCM and width == 2:
        x = np.frombuffer(buf, dtype="<i2").astype(np.float32)
        x /= 32768.0
    elif tag == _WAVE_FORMAT_PCM and width == 3:
        wide = np.zeros((frames * channels, 4), dtype=np.uint8)  # 24 → left-justified 32 bit, sign kept
        wide[:, 1:] = np.frombuffer(buf, dtype=np.uint8).reshape(-1, 3)
        x = wide.view("<i4").reshape(-1).astype(np.float32)
        del wide
        x /= 2147483648.0
    elif tag == _WAVE_FORMAT_PCM and width == 4:
        x = np.frombuffer(buf, dtype="<i4").astype(np.float32)  # same rounding as via float64
        x /= 2147483648.0
    elif tag == _WAVE_FORMAT_IEEE_FLOAT and width in (4, 8):
        x = np.frombuffer(buf, dtype="<f4" if width == 4 else "<f8").astype(np.float32)
    else:
        raise ValueError(f"{path}: unsupported WAV format tag 0x{tag:04x} with {width * 8}-bit samples")
    return x.reshape(frames, channels), rate


def to_mono(samples: np.ndarray) -> np.ndarray:
    """[n] or [n, channels] → float64 [n], the average of the channels."""
    a = np.asarray(samples)
    if a.ndim == 1:
        return a.astype(np.float64, copy=False)
    if a.ndim != 2:
        raise ValueError(f"expected [n] or [n, channels] samples, got shape {a.shape}")
    if a.shape[1] == 1:
        return a[:, 0].astype(np.float64)
    return a.mean(axis=1, dtype=np.float64)  # accumulates in float64 without a float64 copy of all channels


def _channels(samples: np.ndarray) -> list[np.ndarray]:
    a = np.asarray(samples)
    return [a] if a.ndim == 1 else [a[:, c] for c in range(a.shape[1])]


def _db_power(power) -> np.ndarray:
    return 10.0 * np.log10(np.maximum(power, 10.0 ** (FLOOR_DB / 10.0)))


def _db_amplitude(value: float) -> float:
    return float(20.0 * math.log10(max(value, 10.0 ** (FLOOR_DB / 20.0))))


# ---------------------------------------------------------------------------------------------------------
# Envelope, settle, dip


def rms_envelope(samples: np.ndarray, sr: int, window_ms: float = 100.0) -> tuple[np.ndarray, np.ndarray]:
    """Non-overlapping ``window_ms`` RMS of the mono mix → (window centre times [s], RMS [dBFS]).

    A partial window at the end is dropped. Silence reads −120 dB.
    """
    x = to_mono(samples)
    w = max(1, int(round(sr * window_ms / 1000.0)))
    n = len(x) // w
    power = np.mean(x[: n * w].reshape(n, w) ** 2, axis=1)
    times = (np.arange(n) + 0.5) * (w / sr)
    return times, _db_power(power)


def _energy_mean_db(env_db: np.ndarray) -> float:
    return float(_db_power(np.mean(10.0 ** (np.asarray(env_db, dtype=np.float64) / 10.0))))


def _tail_count(times: np.ndarray, tail_s: float) -> int:
    step = float(times[1] - times[0]) if len(times) > 1 else max(tail_s, 1e-9)
    return int(min(len(times), max(1, round(tail_s / step))))


def final_level(times: np.ndarray, env_db: np.ndarray, tail_s: float = 1.0) -> float:
    """Energy mean (dB) of the last ``tail_s`` of the envelope."""
    env = np.asarray(env_db, dtype=np.float64)
    if env.size == 0:
        raise ValueError("empty envelope")
    return _energy_mean_db(env[-_tail_count(np.asarray(times, dtype=np.float64), tail_s) :])


def settle_time(
    times: np.ndarray, env_db: np.ndarray, start_s: float, tol_db: float = 1.0, tail_s: float = 1.0
) -> float | None:
    """Seconds after ``start_s`` until the envelope enters and stays within ±``tol_db`` of its final level.

    The span analysed is every window whose centre is at or after ``start_s`` (pass the envelope sliced
    to the next event to stop there). The final level is the energy mean of the last ``tail_s``. The
    result is the centre time of the first window of the final in-tolerance run minus ``start_s``;
    ``None`` when the span is empty or its last window is itself out of tolerance.
    """
    t = np.asarray(times, dtype=np.float64)
    env = np.asarray(env_db, dtype=np.float64)
    keep = t >= start_s
    t, env = t[keep], env[keep]
    if t.size == 0:
        return None
    final = final_level(t, env, tail_s)
    outside = np.flatnonzero(np.abs(env - final) > tol_db)
    if outside.size == 0:
        return float(t[0] - start_s)
    first = int(outside[-1]) + 1
    if first >= t.size:
        return None
    return float(t[first] - start_s)


def smooth_envelope(env_db: np.ndarray, step_s: float, span_s: float = SMOOTH_S) -> np.ndarray:
    """Energy mean (dB) of the envelope over about ``span_s`` centred on each window.

    The span is the nearest odd number of windows (three 100 ms windows for 300 ms); at the ends only the
    windows present are averaged.
    """
    env = np.asarray(env_db, dtype=np.float64)
    side = max(0, int(round((span_s / step_s - 1.0) / 2.0))) if step_s > 0 else 0
    if env.size == 0 or side == 0:
        return env.copy()
    kernel = np.ones(2 * side + 1)
    power = np.convolve(10.0 ** (env / 10.0), kernel, mode="same")
    count = np.convolve(np.ones(env.size), kernel, mode="same")
    return _db_power(power / count)


def _level_near(t: np.ndarray, env: np.ndarray, lo: float, hi: float, at: float) -> float:
    sel = (t >= lo) & (t <= hi)
    if sel.any():
        return _energy_mean_db(env[sel])
    return float(np.interp(at, t, env))


def dip(times: np.ndarray, env_db: np.ndarray, t0: float, t1: float, level_s: float = LEVEL_S) -> float:
    """Largest drop (dB, ≥ 0) of the envelope below the straight line between the levels at t0 and t1.

    ``[t0, t1]`` should bracket one transition (event → event + crossfade length). The endpoint levels are
    the energy means of the envelope over ``level_s`` just before t0 and just after t1 (the steady levels
    on either side, which damps the ±0.4 dB scatter of single windows); ``level_s=0`` uses the envelope
    interpolated at t0 and t1. Windows whose centres lie in ``[t0, t1]`` are compared with the line.
    """
    if not t1 > t0:
        raise ValueError(f"dip needs t1 > t0 (got {t0}, {t1})")
    t = np.asarray(times, dtype=np.float64)
    env = np.asarray(env_db, dtype=np.float64)
    if t.size == 0:
        raise ValueError("empty envelope")
    l0 = _level_near(t, env, t0 - level_s, t0, t0) if level_s > 0 else float(np.interp(t0, t, env))
    l1 = _level_near(t, env, t1, t1 + level_s, t1) if level_s > 0 else float(np.interp(t1, t, env))
    sel = (t >= t0) & (t <= t1)
    if not sel.any():
        return 0.0
    line = l0 + (l1 - l0) * (t[sel] - t0) / (t1 - t0)
    return float(max(0.0, np.max(line - env[sel])))


# ---------------------------------------------------------------------------------------------------------
# Clicks, clipping


def _sigma(seg: np.ndarray) -> float:
    """1.4826 × MAD of ``seg`` (0 when empty)."""
    if seg.size == 0:
        return 0.0
    return MAD_TO_SIGMA * float(np.median(np.abs(seg - np.median(seg))))


def _mad_sigma(d: np.ndarray, usable: np.ndarray, centre: int, half: int) -> float:
    lo, hi = max(0, centre - half), centre + half + 1
    return _sigma(d[lo:hi][usable[lo:hi]])


def _shorth_sigma(merged: np.ndarray, overlap: int) -> float:
    """Lower bound of the centred sigma of every sample between two grid points a < b.

    ``merged`` is the sorted concatenation of the usable differences of the windows of a and b, so the
    overlap O of the two windows is in it twice and the rest E of their union once; ``overlap`` is |O|.
    The window W of a sample between a and b has O ⊆ W ⊆ O ∪ E. Its MAD is at least the K-th smallest
    |w − median| with K = ⌈|W|/2⌉ (``np.median`` averages the two middle values for even |W|), so the
    interval J of half-width MAD around the median holds at least (|O| + e)/2 points of W, e = |W \\ O|.
    With c_o and c_e the points of O and E in J that needs c_o + min(c_e, e) ≥ (|O| + e)/2, hence
    2·c_o + c_e ≥ |O| (c_e ≥ e: 2·c_o + e ≥ |O|; c_e < e: 2·c_o + 2·c_e ≥ |O| + e > |O| + c_e): J holds
    at least ``overlap`` points of ``merged``. So the narrowest run of ``overlap`` consecutive points of
    ``merged`` is at most 2 × MAD, for every sample between a and b, whatever its window holds.
    """
    if overlap <= 1:
        return 0.0
    widths = merged[overlap - 1 :] - merged[: merged.size - overlap + 1]
    return MAD_TO_SIGMA * 0.5 * float(widths.min())


_BOUND_SLACK = 0.95  # pass 1: centred sigma between two grid points taken as 0.95 × the smaller one
_MAX_REFINE = 20000  # pass 1: at most this many samples re-scored exactly
_MAX_EXACT = 1000  # pass 2: the maximum is proven when at most this many need it (0.3 s at 48 kHz)
_BOUND_ROUNDING = 1.0 - 1e-9  # float rounding of the proven bound against the exact MAD


def click_score(
    samples: np.ndarray,
    sr: int,
    exclude: Iterable[tuple[float, float]] = (),
    window_ms: float = 100.0,
    sigma_floor: float = 1e-5,
    silence_floor: float = SILENCE_FLOOR,
    min_audible: float = MIN_AUDIBLE,
    threshold: float = CLICK_Z,
) -> tuple[float, float | None]:
    """Largest click z outside ``exclude`` → (max |z|, its time in s; ``None`` if nothing was evaluated).

    ``samples`` is scored as its mono mix (pass one channel to score that channel). z = (x[i] - x[i-1]) /
    max(1.4826 × MAD of the first difference over ±``window_ms`` centred on i, ``sigma_floor``). Digital
    silence is left out of the MAD: a sample is silent when |x| < ``silence_floor``, and only differences
    between two non-silent samples enter it. A sample whose ±window holds fewer than ``min_audible`` (a
    share) of such differences is not scored, so the inside of a silence and its edges far from sound are
    skipped, while the step into or out of silence is scored against the audible side's sigma.
    ``sigma_floor`` (1e-5 ≈ −100 dBFS) keeps the division finite. ``exclude`` ranges are inclusive, in
    seconds; x[i] - x[i-1] is timed at sample i.

    The MAD is evaluated exactly on a grid of window/4 steps. Pass 1 re-scores, with their own centred
    window, the samples whose z against 0.95 × the smaller neighbouring grid sigma beats the running
    maximum (at most ``_MAX_REFINE``): a heuristic bound, which matches brute force on ordinary material.
    Pass 2 bounds the sigma between two grid points from below with a proof (``_shorth_sigma``); every
    sample whose z against that bound beats the maximum is re-scored when there are at most
    ``_MAX_EXACT`` of them, so the maximum is then exact. With more (bounded-difference noise such as the
    placeholder beds has many samples near its maximum) and a maximum below ``threshold``, the samples
    whose bound reaches ``threshold`` are re-scored until one does, however many they are, so whether
    max |z| ≥ ``threshold`` is always exact; the value can then be below the true maximum.
    """
    x = to_mono(samples)
    if x.size < 2:
        return 0.0, None
    d = np.diff(x)
    n = d.size
    audible = np.abs(x) >= silence_floor
    del x
    usable = audible[:-1] & audible[1:]
    del audible
    half = max(1, int(round(sr * window_ms / 1000.0)))
    width = 2 * half + 1
    # Usable differences in each ±half window: a cumulative count over the usable mask padded by half.
    count = np.zeros(n + width, dtype=np.int32)
    np.cumsum(usable, dtype=np.int32, out=count[half + 1 : half + 1 + n])
    count[half + 1 + n :] = count[half + n]
    in_window = np.full(n, width, dtype=np.int32)  # the window's length inside the file
    left = np.arange(min(half, n))
    in_window[left] -= half - left
    right = np.arange(max(0, n - half), n)
    in_window[right] -= right + half + 1 - n
    skip = (count[width:] - count[:n]) < min_audible * in_window  # not scored
    del count, in_window
    for a, b in exclude:  # inclusive, with 1e-6 sample of slack so that a time k / sr covers sample k
        lo_i = max(0, math.ceil(a * sr - 1e-6) - 1)
        hi_i = min(n, math.floor(b * sr + 1e-6))
        if hi_i > lo_i:
            skip[lo_i:hi_i] = True
    if skip.all():
        return 0.0, None
    usable_before = np.concatenate(([0], np.cumsum(usable, dtype=np.int64)))  # usable in d[:k]
    hop = max(1, half // 4)
    grid = np.arange(0, n, hop)
    if grid[-1] != n - 1:
        grid = np.append(grid, n - 1)
    grid_sigma = np.empty(grid.size)
    proven = np.empty(grid.size - 1)  # pass 2 bound for the samples between grid[k] and grid[k + 1]
    prev = None
    for k, c in enumerate(grid.tolist()):
        lo, hi = max(0, c - half), min(n, c + half + 1)
        window = np.sort(d[lo:hi][usable[lo:hi]])
        grid_sigma[k] = _sigma(window)
        if prev is not None:
            a = int(grid[k - 1])
            overlap = int(usable_before[min(n, a + half + 1)] - usable_before[max(0, c - half)])
            proven[k - 1] = _shorth_sigma(np.sort(np.concatenate((prev, window)), kind="stable"), overlap)
        prev = window
    del usable_before, prev

    abs_d = np.abs(d)
    bounds = []
    for between, scale in (
        (np.minimum(grid_sigma[:-1], grid_sigma[1:]), _BOUND_SLACK),
        (proven, _BOUND_ROUNDING),
    ):
        # Sample i lies between grid[i // hop] and the next grid point; n - 1 may be a grid point itself.
        z = np.repeat(np.append(between, grid_sigma[-1]), hop)[:n]
        z *= scale
        np.maximum(z, sigma_floor, out=z)
        np.divide(abs_d, z, out=z)
        z[skip] = -1.0
        bounds.append(z)
    z_bound, z_limit = bounds  # pass 1 (heuristic) and pass 2 (proven) upper bounds of each sample's z
    del abs_d, skip, bounds, z

    def exact(i: int) -> float:
        return float(abs(d[i]) / max(_mad_sigma(d, usable, i, half), sigma_floor))

    def rescore(cand: np.ndarray, bound: np.ndarray, best: tuple[float, int], stop_at: float) -> tuple:
        cand = cand[np.argsort(-bound[cand], kind="stable")]
        best_z, best_i = best
        for i in cand.tolist():
            if bound[i] <= best_z or best_z >= stop_at:
                break
            z = exact(i)
            if z > best_z:
                best_z, best_i = z, i
        return best_z, best_i

    best_i = int(np.argmax(z_bound))
    best = (exact(best_i), best_i)
    cand = np.flatnonzero(z_bound > best[0])  # pass 1
    if cand.size > _MAX_REFINE:
        cand = cand[np.argpartition(-z_bound[cand], _MAX_REFINE - 1)[:_MAX_REFINE]]
    best = rescore(cand, z_bound, best, math.inf)
    del z_bound
    cand = np.flatnonzero(z_limit > best[0])  # pass 2
    if cand.size <= _MAX_EXACT:
        best = rescore(cand, z_limit, best, math.inf)
    elif best[0] < threshold:
        best = rescore(cand[z_limit[cand] >= threshold], z_limit, best, threshold)
    return best[0], (best[1] + 1) / sr


def silence_fraction(
    samples: np.ndarray, sr: int, t: float, window_ms: float = 100.0, silence_floor: float = SILENCE_FLOOR
) -> float:
    """Share of silent samples (|x| < ``silence_floor``) of the mono mix within ±``window_ms`` of ``t``."""
    half = max(1, int(round(sr * window_ms / 1000.0)))
    i = int(round(t * sr))
    seg = to_mono(np.asarray(samples)[max(0, i - half) : i + half + 1])
    return float(np.mean(np.abs(seg) < silence_floor)) if seg.size else 0.0


_STOP_HOP_MS = 0.25  # grid of the short windows
_STOP_REF_MS = 100.0  # reference: energy mean over this span, ending within_ms before the quiet onset
_STOP_POST_MS = 20.0  # the post-drop level is the lowest window within within_ms + this after the drop
_STOP_QUIET_DB = 10.0  # quiet onset: the first window within this of that lowest window
# Runs of candidate windows that start less than within_ms after a measured quiet onset are skipped, so a
# drop is listed once; two cuts further apart than that are listed separately.


def abrupt_stop(
    samples: np.ndarray,
    sr: int,
    drop_db: float = STOP_DROP_DB,
    within_ms: float = STOP_WITHIN_MS,
    window_ms: float = STOP_WINDOW_MS,
) -> list[tuple[float, float, float]]:
    """Level drops of ≥ ``drop_db`` completed within ≤ ``within_ms`` → [(t s, drop dB, duration ms), …].

    Levels are ``window_ms`` RMS of the mono mix in dB (windows [t, t + window) on a 0.25 ms grid,
    floored at −120). The reference R(t) is the energy mean over the 100 ms that end ``within_ms`` before
    t. A drop begins at the first window at or below R − ``drop_db``; its quiet onset t (reported) is the
    first window from there within 10 dB of the lowest window of the next ``within_ms`` + 20 ms, which for
    a cut to silence is where the silence starts (a gap has to last about ``window_ms`` to be seen). The
    drop is abrupt when the ``within_ms`` just before t still carry at least 1/3 of R's power: a linear
    ramp from R to silence of exactly ``within_ms`` leaves 1/3 there, a shorter ramp or a cut more.
    ``duration_ms`` is the length of the linear ramp that leaves the same power ratio p there,
    1.5 × within × (1 − p) (p clipped at 1, so a cut reads 0 ms up to the bed's scatter), and drop dB is R
    minus the level at t (floored at −120 dB, so a cut to silence reads about 120 dB + R). Boundary with
    the defaults: a 10 ms linear ramp to silence sits on it; a 20 ms ramp leaves p = 1/12 (6 dB under the
    boundary) and a 250 ms fade about 1/130 of the 100 ms before its last 10 ms, so neither is listed; the
    module docstring has the measured rates. Only drops are looked for: an abrupt start is not listed.
    Pass one channel to check that channel.
    """
    x = to_mono(samples)
    w = max(1, int(round(sr * window_ms / 1000.0)))
    step = max(1, int(round(sr * _STOP_HOP_MS / 1000.0)))
    within = max(1, int(round(sr * within_ms / 1000.0)))
    ref = max(1, int(round(sr * _STOP_REF_MS / 1000.0)))
    first = within + ref // 2  # the reference must cover at least half its span
    if x.size < first + w:
        return []
    energy = np.concatenate(([0.0], np.cumsum(x * x)))
    g = np.arange(first, x.size - w + 1, step)  # window starts
    level = _db_power((energy[g + w] - energy[g]) / w)
    ref_lo = np.maximum(0, g - within - ref)
    ref_power = (energy[g - within] - energy[ref_lo]) / (g - within - ref_lo)
    ref_db = _db_power(ref_power)
    cand = level <= ref_db - drop_db
    if not cand.any():
        return []
    span = int(round(sr * (within_ms + _STOP_POST_MS) / 1000.0 / step))  # in grid steps
    edges = np.flatnonzero(np.diff(np.concatenate(([False], cand, [False])).astype(np.int8)))
    runs = edges.reshape(-1, 2)  # [start, end) of each run of candidate windows
    out = []
    skip_to = -1
    for k0, _ in runs:
        if k0 < skip_to:  # a later piece of a drop already measured: its last within_ms hold that drop
            continue
        stop_k = min(level.size, k0 + span + 1)
        quiet = min(ref_db[k0] - drop_db, float(level[k0:stop_k].min()) + _STOP_QUIET_DB)
        k = k0 + int(np.argmax(level[k0:stop_k] <= quiet))
        skip_to = k + -(-within // step) + 1
        p = (energy[g[k]] - energy[g[k] - within]) / within / max(ref_power[k], 10.0 ** (FLOOR_DB / 10.0))
        drop = float(ref_db[k] - level[k])
        if p >= 1.0 / 3.0 and drop >= drop_db:
            duration = 1.5 * within_ms * (1.0 - min(p, 1.0))
            out.append((float(g[k] / sr), drop, float(duration)))
    return out


def clipping(samples: np.ndarray, thresh: float = 0.999) -> tuple[int, float]:
    """(number of samples, any channel, with |x| >= ``thresh``; peak in dBFS, floored at −120).

    Channels are taken one at a time (a float64 copy of one channel, not of all). NaN samples are neither
    clipped nor the peak (``analyse`` counts non-finite samples); an infinite one is both.
    """
    count, peak = 0, 0.0
    for channel in _channels(samples):
        if channel.size == 0:
            continue
        a = np.abs(channel.astype(np.float64))
        count += int(np.count_nonzero(a >= thresh))
        peak = max(peak, float(np.max(a, where=~np.isnan(a), initial=0.0)))
    return count, _db_amplitude(peak)


# ---------------------------------------------------------------------------------------------------------
# Report / CLI


def _stops_row(stops: list[tuple[float, float, float]]) -> dict:
    listed = [{"t": t, "drop_db": drop, "duration_ms": dur} for t, drop, dur in stops[:STOPS_LISTED]]
    return {"count": len(stops), "first": listed}


def analyse(
    samples: np.ndarray,
    sr: int,
    events: Sequence[float] = (),
    exclude: Sequence[tuple[float, float]] = (),
    window_ms: float = 100.0,
    fade_s: float | None = None,
    span_s: float | None = None,
    tol_db: float = 1.0,
    tail_s: float = 1.0,
    silence_floor: float = SILENCE_FLOOR,
    trace: bool = False,
) -> dict:
    """The CLI report as a dict (levels in dBFS, times in s); see the module docstring for the spans.

    Clicks and abrupt stops are looked for in the mono mix and in each channel (for one channel, the mix
    is the channel); ``click`` gives the largest z with its ``channel`` (``None``: the mix), and
    ``abrupt_stops`` the mix's stops with each channel's under ``channels``. Levels, settle and dip use
    the mono mix. ``trace`` adds each event's envelope and ``settle_s_smoothed``.
    """
    samples = np.asarray(samples)
    mono = to_mono(samples)
    count, peak = clipping(samples)
    times, env = rms_envelope(mono, sr, window_ms)
    channels = _channels(samples)

    def score(signal: np.ndarray) -> tuple[float, float | None]:
        return click_score(signal, sr, exclude=exclude, window_ms=window_ms, silence_floor=silence_floor)

    mix_click, mix_stops = score(mono), abrupt_stop(mono, sr)
    if len(channels) == 1:
        ch_clicks, ch_stops = [mix_click], [mix_stops]
    else:
        ch_clicks = [score(c) for c in channels]
        ch_stops = [abrupt_stop(c, sr) for c in channels]
    (z, z_t), where = mix_click, None
    for c, (cz, ct) in enumerate(ch_clicks if len(channels) > 1 else []):
        if cz > z:
            (z, z_t), where = (cz, ct), c
    source = mono if where is None else channels[where]
    silent = 0.0 if z_t is None else silence_fraction(source, sr, z_t, window_ms, silence_floor)
    report = {
        "sample_rate": sr,
        "channels": len(channels),
        "duration_s": samples.shape[0] / sr,
        "peak_dbfs": peak,
        "clipping_count": count,
        "nonfinite_count": int(sum(np.count_nonzero(~np.isfinite(c)) for c in channels)),
        "rms_dbfs": float(_db_power(np.mean(mono**2))) if mono.size else FLOOR_DB,
        "window_ms": window_ms,
        "click": {
            "max_z": z,
            "t": z_t,
            "channel": where,
            "threshold": CLICK_Z,
            "click": bool(z >= CLICK_Z),
            "silence_fraction": silent,
            "silence_floor": silence_floor,
            "mix": {"max_z": mix_click[0], "t": mix_click[1]},
            "channels": [{"max_z": cz, "t": ct} for cz, ct in ch_clicks],
        },
        "abrupt_stops": {
            "count": len(mix_stops),
            "drop_db": STOP_DROP_DB,
            "within_ms": STOP_WITHIN_MS,
            "window_ms": STOP_WINDOW_MS,
            "first": _stops_row(mix_stops)["first"],
            "channels": [_stops_row(s) for s in ch_stops],
        },
        "exclude": [list(r) for r in exclude],
        "tol_db": tol_db,
        "tail_s": tail_s,
        "events": [],
    }
    span_len = span_s if span_s is not None else (fade_s + tail_s if fade_s else 3.0)
    report["span_s"] = span_len
    step_s = float(times[1] - times[0]) if times.size > 1 else window_ms / 1000.0
    marks = sorted(float(e) for e in events)
    for k, t0 in enumerate(marks):
        prev = marks[k - 1] if k > 0 else -math.inf
        end = marks[k + 1] if k + 1 < len(marks) else math.inf
        seg = (times > prev) & (times < end)
        ts, es = times[seg], env[seg]
        stop = min(end, t0 + span_len)
        row = {"t": t0, "next": None if math.isinf(end) else end, "settle_span": [t0, stop]}
        row.update(before_db=None, final_db=None, settle_s=None, dip_db=None, dip_span=None)
        before = (ts >= t0 - LEVEL_S) & (ts <= t0)
        if before.any():
            row["before_db"] = _energy_mean_db(es[before])
        settle = (ts >= t0) & (ts < stop)
        if settle.any():
            row["final_db"] = final_level(ts[settle], es[settle], tail_s)
            row["settle_s"] = settle_time(ts[settle], es[settle], t0, tol_db=tol_db, tail_s=tail_s)
        length = fade_s if fade_s is not None else row["settle_s"]
        after = ts >= t0
        if length and after.any():
            t1 = min(t0 + length, float(ts[-1]))
            if t1 > t0:
                row["dip_db"] = dip(ts, es, t0, t1)
                row["dip_span"] = [t0, t1]
        if trace:
            shown = (ts >= t0 - LEVEL_S) & (ts < stop)  # the smoothing does not reach past the span
            tt, te = ts[shown], es[shown]
            smooth = smooth_envelope(te, step_s)
            row["trace"] = {"t": [round(float(v), 4) for v in tt], "db": [round(float(v), 2) for v in te]}
            row["settle_s_smoothed"] = settle_time(tt, smooth, t0, tol_db=tol_db, tail_s=tail_s)
        report["events"].append(row)
    return report


def check_failures(report: dict) -> list[str]:
    """What ``--check`` fails on: a click, an abrupt stop (mix or any channel), clipping, non-finite data."""
    failed = []
    if report["click"]["click"]:
        failed.append("click")
    stops = report["abrupt_stops"]
    if stops["count"] or any(c["count"] for c in stops["channels"]):
        failed.append("abrupt stop")
    if report["clipping_count"]:
        failed.append("clipping")
    if report.get("nonfinite_count"):
        failed.append("non-finite samples")
    return failed


def _finite(value):
    """The report with NaN/±Inf replaced by None (JSON has no NaN or Infinity)."""
    if isinstance(value, dict):
        return {k: _finite(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_finite(v) for v in value]
    if isinstance(value, float | np.floating) and not np.isfinite(value):
        return None
    return value


def _fmt(value, spec: str) -> str:
    return "-" if value is None else format(value, spec)


def _stops_text(row: dict) -> str:
    listed = ", ".join(
        f"{s['t']:.3f} s (drop {s['drop_db']:.0f} dB, ramp {s['duration_ms']:.1f} ms)" for s in row["first"]
    )
    more = row["count"] - len(row["first"])
    return (f": {listed}" if listed else "") + (f", +{more} more" if more > 0 else "")


def format_report(report: dict, name: str = "") -> str:
    """The report as the CLI's text table."""
    click = report["click"]
    verdict = "click" if click["click"] else "no click"
    at = "" if click["t"] is None else f" at {click['t']:.3f} s"
    multi = report["channels"] > 1
    if multi and click["t"] is not None:
        at += " in the mix" if click["channel"] is None else f" on ch {click['channel']}"
    lines = [
        f"file         {name} ({report['sample_rate']} Hz, {report['channels']} ch,"
        f" {report['duration_s']:.2f} s)",
        f"peak         {report['peak_dbfs']:.1f} dBFS",
        f"clipping     {report['clipping_count']} samples (|x| >= 0.999)",
    ]
    if report.get("nonfinite_count"):
        lines.append(f"non-finite   {report['nonfinite_count']} samples (NaN/Inf)")
    lines += [
        f"RMS          {report['rms_dbfs']:.1f} dBFS (mono mix, whole file)",
        f"click z max  {click['max_z']:.1f}{at} (threshold {click['threshold']:g}: {verdict};"
        f" {len(report['exclude'])} range(s) excluded)",
    ]
    if multi:
        parts = [("mix", click["mix"])] + [(f"ch {c}", row) for c, row in enumerate(click["channels"])]
        lines.append(
            "             "
            + ", ".join(
                f"{label} {row['max_z']:.1f}" + ("" if row["t"] is None else f" at {row['t']:.3f} s")
                for label, row in parts
            )
        )
    if click["silence_fraction"] >= 0.3:
        lines.append(
            f"             {click['silence_fraction']:.0%} of the ±{report['window_ms']:g} ms window is"
            f" silence (|x| < {click['silence_floor']:g}): z is the step against the audible side's sigma"
        )
    stops = report["abrupt_stops"]
    lines.append(
        f"abrupt stops {stops['count']}{' in the mix' if multi else ''} (drop >= {stops['drop_db']:g} dB"
        f" within <= {stops['within_ms']:g} ms, {stops['window_ms']:g} ms RMS)" + _stops_text(stops)
    )
    if multi:
        for c, row in enumerate(stops["channels"]):
            lines.append(f"             ch {c}: {row['count']}" + _stops_text(row))
    if report["events"]:
        lines.append(
            f"events ({report['window_ms']:g} ms RMS; settle = within ±{report['tol_db']:g} dB of the final"
            f" level, the energy mean of the last {report['tail_s']:g} s of [t, t + {report['span_s']:g} s])"
        )
        lines.append("  t (s)      before dB  final dB  settle s  dip dB  dip span (s)")
        for row in report["events"]:
            span = "-" if row["dip_span"] is None else f"{row['dip_span'][0]:.2f}-{row['dip_span'][1]:.2f}"
            lines.append(
                f"  {row['t']:<9.3f}  {_fmt(row['before_db'], '9.1f')}  {_fmt(row['final_db'], '8.1f')}"
                f"  {_fmt(row['settle_s'], '8.2f')}  {_fmt(row['dip_db'], '6.1f')}  {span}"
            )
    traced = [row for row in report["events"] if "trace" in row]
    if traced:
        lines.append(
            f"trace ({report['window_ms']:g} ms RMS dB from t - {LEVEL_S:g} s; smoothed settle on the"
            f" {SMOOTH_S * 1000:g} ms energy mean)"
        )
        for row in traced:
            lines.append(f"  {row['t']:.3f} s: smoothed settle {_fmt(row['settle_s_smoothed'], '.2f')} s")
            t, db = row["trace"]["t"], row["trace"]["db"]
            for i in range(0, len(t), 10):
                lines.append(f"    {t[i]:8.3f}  " + " ".join(f"{v:6.1f}" for v in db[i : i + 10]))
    if "check" in report:
        failed = report["check"]["failed"]
        verdict = (
            f"FAIL: {', '.join(failed)}" if failed else "pass (no click, abrupt stop, clipping or NaN/Inf)"
        )
        lines.append(f"check        {verdict}")
    return "\n".join(lines)


def _range(text: str) -> tuple[float, float]:
    try:
        a, b = (float(v) for v in text.split(":"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected T0:T1 in seconds, got {text!r}") from exc
    if not b > a:
        raise argparse.ArgumentTypeError(f"exclude range needs T1 > T0, got {text!r}")
    return a, b


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m golmok_tools.audio_analysis",
        description="V-10 WAV analysis: peak/clipping, RMS, click z, abrupt stops, and settle/dip per event."
        " Exit 0 means the analysis ran, not that the file passed; use --check for a verdict.",
    )
    p.add_argument("wav", type=Path)
    p.add_argument("--window-ms", type=float, default=100.0, help="RMS window and ±MAD window (default 100)")
    p.add_argument(
        "--event", type=float, nargs="+", action="extend", default=[], metavar="T", help="event times in s"
    )
    p.add_argument(
        "--exclude",
        type=_range,
        nargs="+",
        action="extend",
        default=[],
        metavar="T0:T1",
        help="time ranges left out of the click search (footstep one-shots)",
    )
    p.add_argument(
        "--fade",
        type=float,
        default=None,
        metavar="S",
        help="crossfade length: dip over [event, event+S] (default: [event, event+settle])",
    )
    p.add_argument(
        "--span",
        type=float,
        default=None,
        metavar="S",
        help="settle span after each event (default: fade + 1 s with --fade, else 3 s)",
    )
    p.add_argument(
        "--silence-floor",
        type=float,
        default=SILENCE_FLOOR,
        metavar="A",
        help=f"|x| below this is silence for the click sigma (default {SILENCE_FLOOR:g}, about -80 dBFS;"
        " 0 counts every sample, the V-10 behaviour)",
    )
    p.add_argument(
        "--trace",
        action="store_true",
        help="add each event's envelope from 0.3 s before it and the settle time on a 300 ms energy mean",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="exit 1 when a click (z >= 8), an abrupt stop, clipping or a non-finite sample is found",
    )
    p.add_argument("--json", action="store_true", help="print the report as JSON")
    args = p.parse_args(argv)
    try:
        samples, sr = read_wav(args.wav)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    report = analyse(
        samples,
        sr,
        args.event,
        args.exclude,
        args.window_ms,
        args.fade,
        args.span,
        silence_floor=args.silence_floor,
        trace=args.trace,
    )
    failed = check_failures(report)
    if args.check:
        report["check"] = {"pass": not failed, "failed": failed}
    if args.json:
        print(
            json.dumps(
                _finite({"file": str(args.wav), **report}), indent=2, ensure_ascii=False, allow_nan=False
            )
        )
    else:
        print(format_report(report, str(args.wav)))
    return 1 if args.check and failed else 0


if __name__ == "__main__":
    sys.exit(main())
