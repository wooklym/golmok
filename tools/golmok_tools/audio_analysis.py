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
  of the span (V-10 saw one 3.0 s case among 12); read it with the level trace.
- ``click_score``: first difference of the mono signal divided by a local robust sigma
  (1.4826 × MAD over ±``window_ms``, centred), maximum |z| outside excluded ranges (footstep one-shots).
  The runbook threshold is z ≥ 8 (``CLICK_Z``). On a continuous bed z stays at a few units and a spike
  or a large level jump stands out. Two limits of the method, measured on synthetic beds:
  (1) where half or more of the ±window is digital silence the MAD collapses and z is inflated: an
  abrupt stop/start saturates against ``sigma_floor`` (z in the hundreds or thousands; the PC self-test's
  hard cut z 160), but a fade into silence reads high as well (250 ms: z ≈ 7–11, 20 ms: 10–20), so the
  report gives the silence fraction at the maximum and such boundaries need the level trace or ``exclude``;
  (2) a hard switch between two uncorrelated beds of similar level is a step of about one bed amplitude,
  only a few times the bed's own sample-to-sample change for 32-tap moving-average noise (z ≈ 2–13), so
  a low z does not show that a crossfade happened; the settle time does.
- ``dip``: largest drop of the envelope below the straight line (in dB) between the levels before and
  after a transition (the crossfade "중간 dip": 3 dB for a linear-amplitude crossfade of two uncorrelated
  equal-level beds, 0 dB for equal-power). On the placeholder beds the ±0.4 dB window scatter alone
  reads as a dip of up to ~1 dB, so compare curves on the same material.
- ``clipping``: samples at or above 0.999 of full scale and the peak level.

Usage (run from ``tools/``; deliberately no console script, pyproject is a shared file)::

    python -m golmok_tools.audio_analysis rec.wav --event 12.3 40.2 --fade 2 --exclude 30.1:30.5 [--json]

``--event`` times are key presses/state changes in seconds from the start of the file. For each event the
settle time is measured over ``[event, event + --span]`` (default: crossfade + 1 s with ``--fade``, else
3 s; never past the next event). Keep the span short: over a long steady stretch one 1 dB noise excursion
is almost certain and moves the settle time to its end. The dip is measured over ``[event, event + --fade]``
(or ``[event, event + settle]`` without ``--fade``).
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
MAD_TO_SIGMA = 1.4826  # MAD of a normal distribution × 1.4826 = sigma

_WAVE_FORMAT_PCM = 0x0001
_WAVE_FORMAT_IEEE_FLOAT = 0x0003
_WAVE_FORMAT_EXTENSIBLE = 0xFFFE


# ---------------------------------------------------------------------------------------------------------
# Reading


def read_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Read a RIFF/WAVE file → (float32 samples [n, channels], sample rate).

    PCM 8/16/24/32-bit and IEEE float 32/64-bit, plain or WAVE_FORMAT_EXTENSIBLE. PCM maps to -1..1;
    float data is returned as stored (it may exceed ±1). A data chunk whose size runs past the end of the
    file (an unfinalised capture) is read up to the last whole frame. The stdlib ``wave`` module is not
    used because Python 3.11's rejects float and WAVE_FORMAT_EXTENSIBLE files (common for loopback).
    """
    raw = Path(path).read_bytes()
    if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise ValueError(f"{path}: not a RIFF/WAVE file")
    fmt = data = None
    pos = 12
    while pos + 8 <= len(raw):
        chunk_id = raw[pos : pos + 4]
        size = int.from_bytes(raw[pos + 4 : pos + 8], "little")
        body = raw[pos + 8 : pos + 8 + size]
        if chunk_id == b"fmt ":
            fmt = body
        elif chunk_id == b"data" and data is None:
            data = body
        pos += 8 + size + (size & 1)
    if fmt is None or len(fmt) < 16:
        raise ValueError(f"{path}: missing fmt chunk")
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
    buf = data[: frames * block_align]
    if tag == _WAVE_FORMAT_PCM and width == 1:
        x = (np.frombuffer(buf, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif tag == _WAVE_FORMAT_PCM and width == 2:
        x = np.frombuffer(buf, dtype="<i2").astype(np.float32) / 32768.0
    elif tag == _WAVE_FORMAT_PCM and width == 3:
        b = np.frombuffer(buf, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        v = (v ^ 0x800000) - 0x800000  # sign-extend 24 → 32 bit
        x = v.astype(np.float32) / 8388608.0
    elif tag == _WAVE_FORMAT_PCM and width == 4:
        x = (np.frombuffer(buf, dtype="<i4").astype(np.float64) / 2147483648.0).astype(np.float32)
    elif tag == _WAVE_FORMAT_IEEE_FLOAT and width in (4, 8):
        x = np.frombuffer(buf, dtype="<f4" if width == 4 else "<f8").astype(np.float32)
    else:
        raise ValueError(f"{path}: unsupported WAV format tag 0x{tag:04x} with {width * 8}-bit samples")
    return x.reshape(frames, channels), rate


def to_mono(samples: np.ndarray) -> np.ndarray:
    """[n] or [n, channels] → float64 [n], the average of the channels."""
    a = np.asarray(samples, dtype=np.float64)
    if a.ndim == 1:
        return a
    if a.ndim != 2:
        raise ValueError(f"expected [n] or [n, channels] samples, got shape {a.shape}")
    return a.mean(axis=1)


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


def _mad_sigma(d: np.ndarray, centre: int, half: int) -> float:
    seg = d[max(0, centre - half) : centre + half + 1]
    return MAD_TO_SIGMA * float(np.median(np.abs(seg - np.median(seg))))


_BOUND_SLACK = 0.95  # centred sigma between two grid points >= 0.95 × the smaller grid value
_MAX_REFINE = 20000


def click_score(
    samples: np.ndarray,
    sr: int,
    exclude: Iterable[tuple[float, float]] = (),
    window_ms: float = 100.0,
    sigma_floor: float = 1e-5,
) -> tuple[float, float | None]:
    """Largest click z outside ``exclude`` → (max |z|, its time in s; ``None`` if nothing was evaluated).

    z = (x[i] - x[i-1]) / max(1.4826 × MAD of the first difference over ±``window_ms`` centred on i,
    ``sigma_floor``). The MAD is evaluated exactly on a grid of window/4 steps; samples whose grid bound
    could exceed the running maximum are then re-scored with their own centred window, so the reported
    maximum uses the exact centred sigma. ``sigma_floor`` (1e-5 ≈ −100 dBFS) keeps digital silence finite.
    ``exclude`` ranges are inclusive, in seconds; the difference x[i] - x[i-1] is timed at sample i.
    """
    x = to_mono(samples)
    if x.size < 2:
        return 0.0, None
    d = np.diff(x)
    n = d.size
    half = max(1, int(round(sr * window_ms / 1000.0)))
    hop = max(1, half // 4)
    grid = np.arange(0, n, hop)
    if grid[-1] != n - 1:
        grid = np.append(grid, n - 1)
    grid_sigma = np.array([_mad_sigma(d, int(c), half) for c in grid])
    # Sample i lies between grid[i // hop] and the next grid point; bound its centred sigma from below.
    pair_min = np.minimum(grid_sigma[:-1], grid_sigma[1:]) if grid.size > 1 else grid_sigma
    bound_sigma = np.repeat(pair_min, hop)[:n]
    if bound_sigma.size < n:  # n - 1 is itself a grid point
        bound_sigma = np.append(bound_sigma, grid_sigma[-1:])
    z_bound = np.abs(d) / np.maximum(_BOUND_SLACK * bound_sigma, sigma_floor)
    for a, b in exclude:
        lo = max(0, math.ceil(a * sr) - 1)
        hi = min(n, math.floor(b * sr))
        if hi > lo:
            z_bound[lo:hi] = -1.0
    if not (z_bound >= 0).any():
        return 0.0, None

    def exact(i: int) -> float:
        return float(abs(d[i]) / max(_mad_sigma(d, i, half), sigma_floor))

    best_i = int(np.argmax(z_bound))
    best_z = exact(best_i)
    cand = np.flatnonzero(z_bound > best_z)
    if cand.size > _MAX_REFINE:
        cand = cand[np.argpartition(-z_bound[cand], _MAX_REFINE - 1)[:_MAX_REFINE]]
    cand = cand[np.argsort(-z_bound[cand], kind="stable")]
    for i in cand:
        if z_bound[i] <= best_z:
            break
        z = exact(int(i))
        if z > best_z:
            best_z, best_i = z, int(i)
    return best_z, (best_i + 1) / sr


def silence_fraction(samples: np.ndarray, sr: int, t: float, window_ms: float = 100.0) -> float:
    """Share of exactly-zero samples of the mono mix within ±``window_ms`` of time ``t``."""
    x = to_mono(samples)
    half = max(1, int(round(sr * window_ms / 1000.0)))
    i = int(round(t * sr))
    seg = x[max(0, i - half) : i + half + 1]
    return float(np.mean(seg == 0.0)) if seg.size else 0.0


def clipping(samples: np.ndarray, thresh: float = 0.999) -> tuple[int, float]:
    """(number of samples, any channel, with |x| >= ``thresh``; peak in dBFS, floored at −120)."""
    a = np.abs(np.asarray(samples, dtype=np.float64))
    if a.size == 0:
        return 0, FLOOR_DB
    return int(np.count_nonzero(a >= thresh)), _db_amplitude(float(a.max()))


# ---------------------------------------------------------------------------------------------------------
# Report / CLI


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
) -> dict:
    """The CLI report as a dict (levels in dBFS, times in s); see the module docstring for the spans."""
    samples = np.asarray(samples)
    mono = to_mono(samples)
    count, peak = clipping(samples)
    times, env = rms_envelope(mono, sr, window_ms)
    z, z_t = click_score(mono, sr, exclude=exclude, window_ms=window_ms)
    silent = 0.0 if z_t is None else silence_fraction(mono, sr, z_t, window_ms)
    report = {
        "sample_rate": sr,
        "channels": 1 if samples.ndim == 1 else int(samples.shape[1]),
        "duration_s": samples.shape[0] / sr,
        "peak_dbfs": peak,
        "clipping_count": count,
        "rms_dbfs": float(_db_power(np.mean(mono**2))) if mono.size else FLOOR_DB,
        "window_ms": window_ms,
        "click": {
            "max_z": z,
            "t": z_t,
            "threshold": CLICK_Z,
            "click": z >= CLICK_Z,
            "silence_fraction": silent,
        },
        "exclude": [list(r) for r in exclude],
        "events": [],
    }
    span_len = span_s if span_s is not None else (fade_s + tail_s if fade_s else 3.0)
    report["span_s"] = span_len
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
        report["events"].append(row)
    return report


def _fmt(value, spec: str) -> str:
    return "-" if value is None else format(value, spec)


def format_report(report: dict, name: str = "") -> str:
    """The report as the CLI's text table."""
    click = report["click"]
    verdict = "click" if click["click"] else "no click"
    at = "" if click["t"] is None else f" at {click['t']:.3f} s"
    lines = [
        f"file         {name} ({report['sample_rate']} Hz, {report['channels']} ch,"
        f" {report['duration_s']:.2f} s)",
        f"peak         {report['peak_dbfs']:.1f} dBFS",
        f"clipping     {report['clipping_count']} samples (|x| >= 0.999)",
        f"RMS          {report['rms_dbfs']:.1f} dBFS (mono mix, whole file)",
        f"click z max  {click['max_z']:.1f}{at} (threshold {click['threshold']:g}: {verdict};"
        f" {len(report['exclude'])} range(s) excluded)",
    ]
    if click["silence_fraction"] >= 0.3:
        lines.append(
            f"             {click['silence_fraction']:.0%} of the ±{report['window_ms']:g} ms window is"
            " digital silence: z is inflated at silence boundaries (a fade into silence also reads 7-20),"
            " check the level trace or exclude it"
        )
    if report["events"]:
        lines.append(
            f"events ({report['window_ms']:g} ms RMS; settle = within ±1 dB of the final level, the energy"
            f" mean of the last 1 s of [t, t + {report['span_s']:g} s])"
        )
        lines.append("  t (s)      before dB  final dB  settle s  dip dB  dip span (s)")
        for row in report["events"]:
            span = "-" if row["dip_span"] is None else f"{row['dip_span'][0]:.2f}-{row['dip_span'][1]:.2f}"
            lines.append(
                f"  {row['t']:<9.3f}  {_fmt(row['before_db'], '9.1f')}  {_fmt(row['final_db'], '8.1f')}"
                f"  {_fmt(row['settle_s'], '8.2f')}  {_fmt(row['dip_db'], '6.1f')}  {span}"
            )
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
        description="V-10 WAV analysis: peak/clipping, RMS, click z, and settle/dip per event.",
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
    p.add_argument("--json", action="store_true", help="print the report as JSON")
    args = p.parse_args(argv)
    try:
        samples, sr = read_wav(args.wav)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    report = analyse(samples, sr, args.event, args.exclude, args.window_ms, args.fade, args.span)
    if args.json:
        print(json.dumps({"file": str(args.wav), **report}, indent=2, ensure_ascii=False))
    else:
        print(format_report(report, str(args.wav)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
