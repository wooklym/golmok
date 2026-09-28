"""Pure parser for Config/Golmok/lighting_presets.json (WP-05 design section 2-2).

No `import unreal` anywhere in this module: tools/tests/test_lighting_presets.py imports it directly and the
C++ loader (Lighting/GolmokTimeOfDay.cpp) applies the same rules, so the JSON file is the single source of the
lighting preset values.

Rules (shared with the tests and the C++ parser):
- schema_version == 2 (WP-14a: cycle presets carry a keyframe "time"; a schema 1 file is an error);
  top-level keys are exactly {schema_version, cycle, presets}
- preset names match ^[a-z][a-z0-9_]*$
- cycle has exactly 4 distinct names, all in presets, each with all 9 keys (complete presets)
- other presets may be partial (missing key = keep the current value); unknown keys are errors
- the sun keys (pitch, yaw, lux, kelvin) and the fog keys (fog, fog_height_falloff) are set together
- "interior" must exist, is not in cycle, has fog == 0 and exposure_bias > 0
- every cycle preset has "time": "HH:MM" (00:00-23:59); the times strictly increase in cycle order; a preset
  outside the cycle (interior) must not have a time
- WP-14a design 2a: a cycle preset may have "hold_minutes" (a finite number >= 0, default 0): its state is held
  that long from its time, then ramps to the next keyframe. time + hold_minutes must be strictly before the next
  keyframe time along the cycle (the last keyframe's hold may cross 00:00 but ends before the first keyframe's
  time); a preset outside the cycle must not have it. find_keyframes / check_keyframe_holds mirror
  GolmokClockMath::FindKeyframes / CheckKeyframeHolds.
"""

from __future__ import annotations

import json
import math
import os
import re

REQUIRED_KEYS = (
    "pitch",
    "yaw",
    "lux",
    "kelvin",
    "sky",
    "fog",
    "fog_height_falloff",
    "volumetric",
    "exposure_bias",
)
RANGES = {
    "pitch": (-90.0, 90.0),
    "yaw": (0.0, 360.0),
    "lux": (0.0, 150000.0),
    "kelvin": (1700.0, 12000.0),
    "sky": (0.0, 10.0),
    "fog": (0.0, 1.0),
    "fog_height_falloff": (0.001, 2.0),
    "exposure_bias": (-5.0, 5.0),
}
HALF_OPEN = ("yaw",)  # lo <= v < hi; others lo <= v <= hi
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
PRESETS_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Config", "Golmok", "lighting_presets.json")
)  # unreal/Golmok/Config/Golmok/lighting_presets.json

SCHEMA_VERSION = 2
TIME_KEY = "time"  # keyframe time of a cycle preset, "HH:MM" (WP-14a design section 2)
HOLD_KEY = "hold_minutes"  # optional keyframe hold of a cycle preset, minutes >= 0 (WP-14a design section 2a)
MINUTES_PER_DAY = 1440.0
HHMM_RE = re.compile(r"^([0-9]{2}):([0-9]{2})$")
TOP_LEVEL_KEYS = frozenset({"schema_version", "cycle", "presets"})
CYCLE_LENGTH = 4
INTERIOR = "interior"
# Keys that are only meaningful together (one UE call / one rotation uses all of them).
KEY_GROUPS = (("pitch", "yaw", "lux", "kelvin"), ("fog", "fog_height_falloff"))
_FILE = "lighting_presets.json"


def _error(reason: str, preset: str | None = None) -> ValueError:
    if preset is None:
        return ValueError(f"{_FILE}: {reason}")
    return ValueError(f"{_FILE}: {preset}: {reason}")


def parse_hhmm(text: str) -> int:
    """ "HH:MM" (two digits each, 00:00-23:59) -> minutes of the day; ValueError otherwise (GolmokClockMath::ParseHHMM)."""
    m = HHMM_RE.fullmatch(text) if isinstance(text, str) else None  # fullmatch: "$" would allow a trailing "\n"
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise ValueError(f"time must be HH:MM (00:00-23:59), got {text!r}")
    return int(m.group(1)) * 60 + int(m.group(2))


def format_hhmm(minutes: float) -> str:
    """Minutes (wrapped into the day, floored) -> "HH:MM" (GolmokClockMath::FormatHHMM)."""
    m = int(math.floor(minutes % 1440.0)) % 1440 if math.isfinite(minutes) else 0
    return f"{m // 60:02d}:{m % 60:02d}"


def keyframes(cycle: list[str], presets: dict[str, dict]) -> list[tuple[str, int]]:
    """(name, minutes) of the cycle presets in cycle order (the clock keyframes)."""
    return [(name, parse_hhmm(presets[name][TIME_KEY])) for name in cycle]


def holds(cycle: list[str], presets: dict[str, dict]) -> list[float]:
    """hold_minutes of the cycle presets in cycle order (0.0 when absent; design 2a)."""
    return [float(presets[name].get(HOLD_KEY, 0.0)) for name in cycle]


def wrap_minutes(minutes: float) -> float:
    """Any finite minutes -> [0, 1440); non-finite -> 0 (GolmokClockMath::WrapMinutes)."""
    if not math.isfinite(minutes):
        return 0.0
    r = math.fmod(minutes, MINUTES_PER_DAY)
    if r < 0.0:
        r += MINUTES_PER_DAY
    return 0.0 if r >= MINUTES_PER_DAY else r


def is_valid_hold(hold: object) -> bool:
    """A finite number >= 0 (GolmokClockMath::IsValidHold); a bool is not a number."""
    return _is_number(hold) and math.isfinite(hold) and hold >= 0.0


def find_keyframes(
    minutes: float, times: list[float], hold_list: list[float] | None = None
) -> tuple[int, int, float, bool]:
    """(prev, next, alpha, held) of GolmokClockMath::FindKeyframes: times strictly increasing in [0, 1440);
    across midnight the last -> first span is 1440 - last + first wide. Inside keyframe i's hold (from times[i] for
    hold_list[i] minutes; an invalid hold counts as 0) alpha is 0 and held is True; after it alpha ramps from the
    hold end to the next keyframe: (elapsed - hold) / (width - hold). No times -> (-1, -1, 0.0, False)."""
    n = len(times)
    if n == 0:
        return -1, -1, 0.0, False

    def hold_of(i: int) -> float:
        return float(hold_list[i]) if hold_list and is_valid_hold(hold_list[i]) else 0.0

    t = wrap_minutes(minutes)
    if n == 1:
        return 0, 0, 0.0, wrap_minutes(t - times[0]) < hold_of(0)
    prev = n - 1
    for i, k in enumerate(times):
        if k <= t:
            prev = i
    nxt = prev + 1 if prev + 1 < n else 0
    width = times[nxt] - times[prev]
    elapsed = t - times[prev]
    if nxt == 0:
        width += MINUTES_PER_DAY
        if elapsed < 0.0:
            elapsed += MINUTES_PER_DAY
    hold = hold_of(prev)
    if elapsed < hold:
        return prev, nxt, 0.0, True
    ramp = width - hold
    alpha = (elapsed - hold) / ramp if ramp > 0.0 else 0.0
    return prev, nxt, min(max(alpha, 0.0), 1.0), False


def check_keyframe_holds(times: list[float], hold_list: list[float]) -> tuple[int, int]:
    """(result, index) of GolmokClockMath::CheckKeyframeHolds on ordered times: 0 fine, 1 = hold_list[index] is
    negative or not finite, 2 = times[index] + hold_list[index] is not strictly before the next keyframe time along
    the cycle (the last one wraps: before times[0] + 1440)."""
    n = len(times)
    for i in range(n):
        if not is_valid_hold(hold_list[i]):
            return 1, i
        next_time = times[i + 1] if i + 1 < n else times[0] + MINUTES_PER_DAY
        if not (times[i] + hold_list[i] < next_time):
            return 2, i
    return 0, -1


def describe_hold(minutes: float, cycle: list[str], presets: dict[str, dict]) -> str | None:
    """"night 23:10 hold until 05:30" while minutes is inside a keyframe hold, else None (golmok.tod status)."""
    times = [float(m) for _, m in keyframes(cycle, presets)]
    hold_list = holds(cycle, presets)
    prev, _, _, held = find_keyframes(minutes, times, hold_list)
    if not held:
        return None
    return f"{cycle[prev]} {format_hhmm(minutes)} hold until {format_hhmm(times[prev] + hold_list[prev])}"


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _check_preset(name: str, preset: object) -> dict:
    if not NAME_RE.match(name):
        raise _error("name must match ^[a-z][a-z0-9_]*$", name)
    if not isinstance(preset, dict):
        raise _error("preset must be an object", name)
    for key in preset:
        if key not in REQUIRED_KEYS and key not in (TIME_KEY, HOLD_KEY):
            raise _error(f"unknown key '{key}'", name)
    for key, value in preset.items():
        if key == TIME_KEY:
            try:
                parse_hhmm(value)
            except ValueError as e:
                raise _error(str(e), name) from None
            continue
        if key == HOLD_KEY:
            if not _is_number(value):
                raise _error(f"{HOLD_KEY} must be a number", name)
            if not is_valid_hold(value):
                raise _error(f"{HOLD_KEY} must be a finite number >= 0 (got {value:g})", name)
            continue
        if key == "volumetric":
            if not isinstance(value, bool):
                raise _error("volumetric must be a bool", name)
            continue
        if not _is_number(value):
            raise _error(f"{key} must be a number", name)
        lo, hi = RANGES[key]
        inside = lo <= value < hi if key in HALF_OPEN else lo <= value <= hi
        if not inside:
            close = ")" if key in HALF_OPEN else "]"
            raise _error(f"{key} {value} out of range [{lo}, {hi}{close}", name)
    for group in KEY_GROUPS:
        present = [k for k in group if k in preset]
        if present and len(present) != len(group):
            missing = next(k for k in group if k not in preset)
            raise _error(f"missing key '{missing}' ({', '.join(group)} are set together)", name)
    return dict(preset)


def parse_presets(text: str) -> tuple[list[str], dict[str, dict]]:
    """Parse and validate the JSON text; returns (cycle, presets), raises ValueError naming preset and key."""
    root = json.loads(text)
    if not isinstance(root, dict):
        raise _error("root must be an object")
    if root.get("schema_version") != SCHEMA_VERSION or isinstance(root.get("schema_version"), bool):
        raise _error(f"schema_version {root.get('schema_version')!r} (expected {SCHEMA_VERSION})")
    extra = set(root) - TOP_LEVEL_KEYS
    if extra:
        raise _error(f"unknown top-level key '{sorted(extra)[0]}'")
    missing = TOP_LEVEL_KEYS - set(root)
    if missing:
        raise _error(f"missing top-level key '{sorted(missing)[0]}'")
    raw_cycle, raw_presets = root["cycle"], root["presets"]
    if not isinstance(raw_presets, dict) or not raw_presets:
        raise _error("presets must be a non-empty object")
    presets = {name: _check_preset(name, preset) for name, preset in raw_presets.items()}

    if not isinstance(raw_cycle, list) or len(raw_cycle) != CYCLE_LENGTH:
        raise _error(f"cycle must be a list of exactly {CYCLE_LENGTH} preset names")
    if any(not isinstance(n, str) for n in raw_cycle):
        raise _error("cycle entries must be strings")
    if len(set(raw_cycle)) != len(raw_cycle):
        raise _error("cycle has duplicate names")
    for name in raw_cycle:
        if name not in presets:
            raise _error(f"cycle names unknown preset '{name}'")
        for key in REQUIRED_KEYS:
            if key not in presets[name]:
                raise _error(f"missing key '{key}' (cycle presets need all 9 keys)", name)
        if TIME_KEY not in presets[name]:
            raise _error(f"missing key '{TIME_KEY}' (cycle presets need a keyframe time HH:MM)", name)
    for name, preset in presets.items():
        if name not in raw_cycle and TIME_KEY in preset:
            raise _error(f"{TIME_KEY} is only allowed on cycle presets", name)
        if name not in raw_cycle and HOLD_KEY in preset:
            raise _error(f"{HOLD_KEY} is only allowed on cycle presets", name)
    for before, after in zip(raw_cycle, raw_cycle[1:], strict=False):
        t0, t1 = parse_hhmm(presets[before][TIME_KEY]), parse_hhmm(presets[after][TIME_KEY])
        if t1 == t0:
            raise _error(f"cycle has duplicate time {presets[after][TIME_KEY]} ({before}, {after})")
        if t1 < t0:
            raise _error(
                f"cycle times must increase ({after} {presets[after][TIME_KEY]} is before "
                f"{before} {presets[before][TIME_KEY]})"
            )
    times = [float(m) for _, m in keyframes(raw_cycle, presets)]
    hold_list = holds(raw_cycle, presets)
    result, bad = check_keyframe_holds(times, hold_list)
    if result == 1:
        raise _error(f"{HOLD_KEY} must be a finite number >= 0 (got {hold_list[bad]:g})", raw_cycle[bad])
    if result == 2:
        nxt = raw_cycle[(bad + 1) % len(raw_cycle)]
        raise _error(
            f"{HOLD_KEY} {hold_list[bad]:g} runs to {format_hhmm(times[bad] + hold_list[bad])}, "
            f"not before the next keyframe {nxt} {presets[nxt][TIME_KEY]}",
            raw_cycle[bad],
        )

    if INTERIOR not in presets:
        raise _error(f"missing preset '{INTERIOR}'")
    if INTERIOR in raw_cycle:
        raise _error("must not be in cycle", INTERIOR)
    interior = presets[INTERIOR]
    if interior.get("fog") != 0:
        raise _error(f"fog must be 0 (got {interior.get('fog')!r})", INTERIOR)
    if not (_is_number(interior.get("exposure_bias")) and interior["exposure_bias"] > 0):
        raise _error(f"exposure_bias must be > 0 (got {interior.get('exposure_bias')!r})", INTERIOR)
    return list(raw_cycle), presets


def load_presets(path: str = PRESETS_FILE) -> tuple[list[str], dict[str, dict]]:
    with open(path, encoding="utf-8") as f:
        return parse_presets(f.read())


def is_partial(preset: dict) -> bool:
    return set(preset) - {TIME_KEY, HOLD_KEY} < set(REQUIRED_KEYS)
