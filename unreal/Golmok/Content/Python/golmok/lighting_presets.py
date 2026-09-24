"""Pure parser for Config/Golmok/lighting_presets.json (WP-05 design section 2-2).

No `import unreal` anywhere in this module: tools/tests/test_lighting_presets.py imports it directly and the
C++ loader (Lighting/GolmokTimeOfDay.cpp) applies the same rules, so the JSON file is the single source of the
lighting preset values.

Rules (shared with the tests and the C++ parser):
- schema_version == 1; top-level keys are exactly {schema_version, cycle, presets}
- preset names match ^[a-z][a-z0-9_]*$
- cycle has exactly 4 distinct names, all in presets, each with all 9 keys (complete presets)
- other presets may be partial (missing key = keep the current value); unknown keys are errors
- the sun keys (pitch, yaw, lux, kelvin) and the fog keys (fog, fog_height_falloff) are set together
- "interior" must exist, is not in cycle, has fog == 0 and exposure_bias > 0
"""

from __future__ import annotations

import json
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

SCHEMA_VERSION = 1
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


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _check_preset(name: str, preset: object) -> dict:
    if not NAME_RE.match(name):
        raise _error("name must match ^[a-z][a-z0-9_]*$", name)
    if not isinstance(preset, dict):
        raise _error("preset must be an object", name)
    for key in preset:
        if key not in REQUIRED_KEYS:
            raise _error(f"unknown key '{key}'", name)
    for key, value in preset.items():
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
    return set(preset) < set(REQUIRED_KEYS)
