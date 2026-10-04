"""Pure weather rules and the Config/Golmok/weather.json parser (WP-16a design sections 2-6 and 8).

No `import unreal` anywhere in this module. It mirrors Source/Golmok/Weather/GolmokWeatherMath.h (every rule
and contract name, snake_case) and GolmokWeather::ParseConfigText (GolmokWeatherConfig.cpp: same rules, same
check order, byte-identical messages "weather.json: <where>: <reason>"). tools/tests/test_ue_weather_math.py
compiles the header with g++ and compares it with this module; tools/tests/test_ue_config_weather.py runs the
error table that Golmok.Weather.Config runs against the C++ parser.

<where> is the JSON path of the offending value: "root" for the top-level object, dotted keys below it and
[index] for array elements, e.g. "modifiers.rain.fog_scale", "schedule[3].time",
"rain_fx.box_half_extent_cm[1]".
Key-set errors report the first missing key in schema order, then the first unknown key in code-point order.
Numbers are JSON numbers (a bool is not a number) and must be finite.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field

from .lighting_presets import parse_hhmm, wrap_minutes

# ---- states (design section 2) ----------------------------------------------------------------------------

STATE_NAMES = ("clear", "overcast", "rain")  # GolmokWeatherMath::State / EGolmokWeather order
STATE_COUNT = 3
MIN_RAIN_INTENSITY = 0.05
MAX_RAIN_INTENSITY = 1.0
WET_RAIN_THRESHOLD = 0.01
VALUE_EPSILON = 0.001
MAX_TRANSITION_SECONDS = 600.0

# ---- contract names (design sections 7-2 and 8) -----------------------------------------------------------

MPC_RAIN_INTENSITY = "RainIntensity"
MPC_WETNESS = "Wetness"
MPC_PUDDLE_AMOUNT = "PuddleAmount"
MPC_PARAMETERS = (MPC_RAIN_INTENSITY, MPC_WETNESS, MPC_PUDDLE_AMOUNT)
USER_RAIN_INTENSITY = "User.RainIntensity"
USER_SPAWN_RATE = "User.SpawnRate"
USER_BOX_HALF_EXTENT = "User.BoxHalfExtent"
USER_PARAMETERS = (USER_RAIN_INTENSITY, USER_SPAWN_RATE, USER_BOX_HALF_EXTENT)

# (weather.json key, min, max, min exclusive) in Modifier field order (GolmokWeatherMath::ModifierField).
MODIFIER_FIELDS = (
    ("lux_scale", 0.0, 2.0, True),
    ("sky_scale", 0.0, 2.0, True),
    ("fog_scale", 0.0, 5.0, True),
    ("fog_height_falloff_scale", 0.0, 2.0, True),
    ("kelvin_target", 2000.0, 12000.0, False),
    ("kelvin_weight", 0.0, 1.0, False),
    ("exposure_offset", -2.0, 2.0, False),
)
MODIFIER_FIELD_COUNT = 7


def state_name(state: int) -> str:
    """GolmokWeatherMath::StateName: an out-of-range index is "clear"."""
    return STATE_NAMES[state] if isinstance(state, int) and 0 <= state < STATE_COUNT else STATE_NAMES[0]


def parse_state(text: object) -> int | None:
    """Exact, case-sensitive state name -> index; None otherwise (GolmokWeatherMath::ParseState)."""
    return STATE_NAMES.index(text) if isinstance(text, str) and text in STATE_NAMES else None


def is_valid_rain_intensity(intensity: float) -> bool:
    return (
        _is_number(intensity) and _finite(intensity) and MIN_RAIN_INTENSITY <= intensity <= MAX_RAIN_INTENSITY
    )


def target_rain(state: str, intensity: float) -> float:
    """The rain the target asks for: intensity for rain, 0 otherwise (GolmokWeatherMath::TargetRain)."""
    return intensity if state == "rain" else 0.0


# ---- lighting modifier (design section 5) -----------------------------------------------------------------


@dataclass(frozen=True)
class Modifier:
    """Seven fields; the defaults are the identity (clear)."""

    lux_scale: float = 1.0
    sky_scale: float = 1.0
    fog_scale: float = 1.0
    fog_height_falloff_scale: float = 1.0
    kelvin_target: float = 6500.0
    kelvin_weight: float = 0.0
    exposure_offset: float = 0.0

    def values(self) -> tuple[float, ...]:
        return tuple(getattr(self, key) for key, _, _, _ in MODIFIER_FIELDS)


@dataclass(frozen=True)
class Light:
    """The part of FGolmokLightingState the modifier touches (GolmokWeatherMath::Light)."""

    lux: float = 0.0
    use_temperature: bool = False
    kelvin: float = 6500.0
    sky: float = 1.0
    fog: float = 0.0
    fog_height_falloff: float = 0.2
    exposure_overridden: bool = False
    exposure_bias: float = 0.0


def is_field_in_range(index: int, value: object) -> bool:
    """GolmokWeatherMath::IsFieldInRange (NaN / inf / bools never are)."""
    _, lo, hi, lo_exclusive = MODIFIER_FIELDS[min(max(index, 0), MODIFIER_FIELD_COUNT - 1)]
    if not _is_number(value) or not _finite(value) or value > hi:
        return False
    return value > lo if lo_exclusive else value >= lo


def is_identity(m: Modifier) -> bool:
    """Every field that changes a value is at its identity (kelvin_target alone changes nothing)."""
    return (
        m.lux_scale == 1.0
        and m.sky_scale == 1.0
        and m.fog_scale == 1.0
        and m.fog_height_falloff_scale == 1.0
        and m.kelvin_weight == 0.0
        and m.exposure_offset == 0.0
    )


def apply(light: Light, m: Modifier) -> Light:
    """Design 5-1 (GolmokWeatherMath::Apply): the identity returns the input object unchanged."""
    if is_identity(m):
        return light
    kelvin = light.kelvin
    if light.use_temperature and m.kelvin_weight != 0.0:
        kelvin = light.kelvin + (m.kelvin_target - light.kelvin) * m.kelvin_weight
    overridden, bias = light.exposure_overridden, light.exposure_bias
    if m.exposure_offset != 0.0:
        overridden, bias = True, light.exposure_bias + m.exposure_offset
    return Light(
        lux=light.lux * m.lux_scale,
        use_temperature=light.use_temperature,
        kelvin=kelvin,
        sky=light.sky * m.sky_scale,
        fog=light.fog * m.fog_scale,
        fog_height_falloff=light.fog_height_falloff * m.fog_height_falloff_scale,
        exposure_overridden=overridden,
        exposure_bias=bias,
    )


def clamp01(x: float) -> float:
    if not (x > 0.0):  # NaN -> 0
        return 0.0
    return 1.0 if x > 1.0 else x


def lerp_modifier(a: Modifier, b: Modifier, t: float) -> Modifier:
    """log2-linear scales, linear rest; t <= 0 -> a, t >= 1 -> b (GolmokWeatherMath::Lerp)."""
    if not (t > 0.0):
        return a
    if t >= 1.0:
        return b

    def log_lerp(x: float, y: float) -> float:
        return math.exp2(math.log2(x) + (math.log2(y) - math.log2(x)) * t)

    def lin_lerp(x: float, y: float) -> float:
        return x + (y - x) * t

    return Modifier(
        lux_scale=log_lerp(a.lux_scale, b.lux_scale),
        sky_scale=log_lerp(a.sky_scale, b.sky_scale),
        fog_scale=log_lerp(a.fog_scale, b.fog_scale),
        fog_height_falloff_scale=log_lerp(a.fog_height_falloff_scale, b.fog_height_falloff_scale),
        kelvin_target=lin_lerp(a.kelvin_target, b.kelvin_target),
        kelvin_weight=lin_lerp(a.kelvin_weight, b.kelvin_weight),
        exposure_offset=lin_lerp(a.exposure_offset, b.exposure_offset),
    )


def for_state(state: str, intensity: float, overcast: Modifier, rain: Modifier) -> Modifier:
    """Target modifier: clear = identity, overcast = overcast, rain(I) = lerp(overcast, rain, I)."""
    if state == "overcast":
        return overcast
    if state == "rain":
        return lerp_modifier(overcast, rain, clamp01(intensity))
    return Modifier()


# ---- transition (design section 3) ------------------------------------------------------------------------


def smoothstep(x: float) -> float:
    t = clamp01(x)
    return t * t * (3.0 - 2.0 * t)


def precip_alpha(alpha: float, increasing: bool) -> float:
    """Increasing rain waits for the sky's first half; decreasing rain stops in the first half."""
    return smoothstep(2.0 * alpha - 1.0) if increasing else smoothstep(2.0 * alpha)


def precip_at(r_start: float, r_target: float, alpha: float) -> float:
    if alpha >= 1.0:
        return r_target
    return r_start + (r_target - r_start) * precip_alpha(alpha, r_target > r_start)


def modifier_at(m_start: Modifier, m_target: Modifier, alpha: float) -> Modifier:
    if alpha >= 1.0:
        return m_target
    return lerp_modifier(m_start, m_target, smoothstep(alpha))


# ---- surface (design section 8) ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SurfaceParams:
    wet_seconds: float = 60.0
    dry_seconds: float = 600.0
    puddle_min_intensity: float = 0.4
    puddle_fill_seconds: float = 240.0
    puddle_dry_seconds: float = 1200.0


@dataclass(frozen=True)
class Surface:
    wetness: float = 0.0
    puddle: float = 0.0


def step_surface(s: Surface, rain: float, dt: float, p: SurfaceParams) -> Surface:
    """One step of dt world seconds; both values stay in [0, 1] and puddle <= wetness."""
    step = dt if (math.isfinite(dt) and dt > 0.0) else 0.0
    wetness, puddle = s.wetness, s.puddle
    if rain > WET_RAIN_THRESHOLD:
        wetness += step * rain / p.wet_seconds
    else:
        wetness -= step / p.dry_seconds
    if rain > p.puddle_min_intensity:
        puddle += (
            step * (rain - p.puddle_min_intensity) / (1.0 - p.puddle_min_intensity) / p.puddle_fill_seconds
        )
    else:
        puddle -= step / p.puddle_dry_seconds
    return clamp_surface(wetness, puddle)


def clamp_surface(wetness: float, puddle: float) -> Surface:
    w = clamp01(wetness)
    p = clamp01(puddle)
    if p > w:
        p = w
    return Surface(wetness=w, puddle=p)


# ---- schedule (design section 4) --------------------------------------------------------------------------


def schedule_index_at(minutes: float, times: list[float]) -> int:
    """Last slot whose time is <= minutes (wrapped), or the last slot before the first one; -1 when empty."""
    if not times:
        return -1
    m = wrap_minutes(minutes)
    index = len(times) - 1
    for i, t in enumerate(times):
        if t <= m:
            index = i
        else:
            break
    return index


# ---- weather.json (design section 6) ----------------------------------------------------------------------

SCHEMA_VERSION = 1
CONFIG_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Config", "Golmok", "weather.json")
)  # unreal/Golmok/Config/Golmok/weather.json
TOP_LEVEL_KEYS = (
    "schema_version",
    "initial",
    "transition_seconds",
    "rain_levels",
    "modifiers",
    "surface",
    "schedule",
    "rain_fx",
    "mpc",
)
RAIN_LEVEL_NAMES = ("light", "moderate", "heavy")
MODIFIER_STATES = ("overcast", "rain")
SURFACE_KEYS = (
    "wet_seconds",
    "dry_seconds",
    "puddle_min_intensity",
    "puddle_fill_seconds",
    "puddle_dry_seconds",
)
MODE_NAMES = ("fixed", "schedule")
RAIN_FX_KEYS = ("system", "enabled", "max_spawn_rate", "box_half_extent_cm", "height_offset_cm")
MAX_SPAWN_RATE = 20000.0
BOX_HALF_EXTENT_RANGE = (100.0, 5000.0)
HEIGHT_OFFSET_RANGE = (-1000.0, 3000.0)
GAME_PREFIX = "/Game/"
_FILE = "weather.json"


@dataclass(frozen=True)
class ScheduleSlot:
    minutes: float
    state: str
    intensity: float = 0.0


@dataclass(frozen=True)
class WeatherConfig:
    """GolmokWeather::FConfig."""

    schema_version: int = 1
    initial_state: str = "clear"
    initial_intensity: float = 0.0
    initial_schedule: bool = False  # initial.mode == "schedule"
    transition_seconds: float = 20.0
    rain_light: float = 0.3
    rain_moderate: float = 0.6
    rain_heavy: float = 1.0
    overcast: Modifier = field(default_factory=Modifier)
    rain: Modifier = field(default_factory=Modifier)
    surface: SurfaceParams = field(default_factory=SurfaceParams)
    schedule: tuple[ScheduleSlot, ...] = ()
    schedule_times: tuple[float, ...] = ()
    rain_fx_system: str = ""
    rain_fx_enabled: bool = True
    max_spawn_rate: float = 12000.0
    box_half_extent_cm: tuple[float, float, float] = (1000.0, 1000.0, 500.0)
    height_offset_cm: float = 300.0
    mpc: str = ""


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _finite(value: int | float) -> bool:
    try:
        return math.isfinite(value)
    except OverflowError:  # a JSON integer beyond double range (the C++ reader makes it inf)
        return False


def _fail(where: str, reason: str) -> ValueError:
    return ValueError(f"{_FILE}: {where}: {reason}")


def _num_text(value: float) -> str:
    """Same as printf "%g" (FString::Printf in GolmokWeatherConfig.cpp)."""
    return f"{value:g}"


def _range_text(lo: float, hi: float, lo_exclusive: bool = False, hi_exclusive: bool = False) -> str:
    return f"{'(' if lo_exclusive else '['}{_num_text(lo)}, {_num_text(hi)}{')' if hi_exclusive else ']'}"


def _number(
    value: object, where: str, lo: float, hi: float, lo_ex: bool = False, hi_ex: bool = False
) -> float:
    ok = _is_number(value) and _finite(value)
    if ok:
        v = float(value)
        ok = (v > lo if lo_ex else v >= lo) and (v < hi if hi_ex else v <= hi)
    if not ok:
        raise _fail(where, f"must be a number in {_range_text(lo, hi, lo_ex, hi_ex)}")
    return float(value)


def _object(value: object, where: str) -> dict:
    if not isinstance(value, dict):
        raise _fail(where, "must be an object")
    return value


def _keys(obj: dict, where: str, required: tuple[str, ...], optional: tuple[str, ...] = ()) -> None:
    for key in required:
        if key not in obj:
            raise _fail(where, f'missing key "{key}"')
    unknown = sorted(key for key in obj if key not in required and key not in optional)
    if unknown:
        raise _fail(where, f'unknown key "{unknown[0]}"')


def _state_and_intensity(obj: dict, where: str) -> tuple[str, float]:
    state = obj["state"]
    if parse_state(state) is None:
        raise _fail(f"{where}.state", "must be clear, overcast or rain")
    if state == "rain":
        if "intensity" not in obj:
            raise _fail(f"{where}.intensity", "required for rain")
        return state, _number(obj["intensity"], f"{where}.intensity", MIN_RAIN_INTENSITY, MAX_RAIN_INTENSITY)
    if "intensity" in obj:
        raise _fail(f"{where}.intensity", "only allowed for rain")
    return state, 0.0


def _object_path(value: object, where: str) -> str:
    # "/Game/<...>/Package.Object": a /Game/ path whose last segment names an object.
    if not isinstance(value, str) or not value.startswith(GAME_PREFIX) or "." not in value.rsplit("/", 1)[-1]:
        raise _fail(where, "must be an object path /Game/.../Package.Object")
    return value


def _modifier(value: object, where: str) -> Modifier:
    obj = _object(value, where)
    _keys(obj, where, tuple(key for key, _, _, _ in MODIFIER_FIELDS))
    values = {}
    for key, lo, hi, lo_ex in MODIFIER_FIELDS:
        values[key] = _number(obj[key], f"{where}.{key}", lo, hi, lo_ex)
    return Modifier(**values)


def _reject_constant(name: str) -> None:
    raise ValueError(name)  # NaN / Infinity are not JSON (the UE reader rejects them too)


def parse_config(text: str) -> WeatherConfig:
    """Text -> WeatherConfig; ValueError("weather.json: <where>: <reason>") on the first error."""
    try:
        root = json.loads(text, parse_constant=_reject_constant)
    except (ValueError, TypeError):
        root = None
    if not isinstance(root, dict):
        raise _fail("root", "not a JSON object")

    version = root.get("schema_version")
    if not _is_number(version) or version != SCHEMA_VERSION:
        raise _fail("schema_version", f"must be {SCHEMA_VERSION}")
    _keys(root, "root", TOP_LEVEL_KEYS)

    initial = _object(root["initial"], "initial")
    _keys(initial, "initial", ("state", "mode"), ("intensity",))
    initial_state, initial_intensity = _state_and_intensity(initial, "initial")
    if not isinstance(initial["mode"], str) or initial["mode"] not in MODE_NAMES:
        raise _fail("initial.mode", "must be fixed or schedule")

    transition = _number(root["transition_seconds"], "transition_seconds", 0.0, MAX_TRANSITION_SECONDS)

    levels_obj = _object(root["rain_levels"], "rain_levels")
    _keys(levels_obj, "rain_levels", RAIN_LEVEL_NAMES)
    levels = [
        _number(levels_obj[name], f"rain_levels.{name}", MIN_RAIN_INTENSITY, MAX_RAIN_INTENSITY)
        for name in RAIN_LEVEL_NAMES
    ]
    if not (levels[0] < levels[1] < levels[2]):
        raise _fail("rain_levels", "must increase strictly (light < moderate < heavy)")

    modifiers = _object(root["modifiers"], "modifiers")
    if "clear" in modifiers:
        raise _fail("modifiers.clear", "clear is the identity and must not be listed")
    _keys(modifiers, "modifiers", MODIFIER_STATES)
    overcast = _modifier(modifiers["overcast"], "modifiers.overcast")
    rain = _modifier(modifiers["rain"], "modifiers.rain")

    surface_obj = _object(root["surface"], "surface")
    _keys(surface_obj, "surface", SURFACE_KEYS)
    surface_values = {}
    for key in SURFACE_KEYS:
        where = f"surface.{key}"
        if key == "puddle_min_intensity":
            surface_values[key] = _number(surface_obj[key], where, 0.0, 1.0, hi_ex=True)
        else:
            value = surface_obj[key]
            if not (_is_number(value) and _finite(value) and value > 0.0):
                raise _fail(where, "must be a positive number")
            surface_values[key] = float(value)

    schedule_list = root["schedule"]
    if not isinstance(schedule_list, list) or not schedule_list:
        raise _fail("schedule", "must be a non-empty array")
    slots = []
    for i, item in enumerate(schedule_list):
        where = f"schedule[{i}]"
        slot = _object(item, where)
        _keys(slot, where, ("time", "state"), ("intensity",))
        try:
            minutes = float(parse_hhmm(slot["time"]))
        except ValueError:
            raise _fail(f"{where}.time", "must be HH:MM (00:00-23:59)") from None
        if slots and minutes <= slots[-1].minutes:
            raise _fail(f"{where}.time", f"must be later than schedule[{i - 1}].time")
        state, intensity = _state_and_intensity(slot, where)
        slots.append(ScheduleSlot(minutes=minutes, state=state, intensity=intensity))

    fx = _object(root["rain_fx"], "rain_fx")
    _keys(fx, "rain_fx", RAIN_FX_KEYS)
    system = _object_path(fx["system"], "rain_fx.system")
    if not isinstance(fx["enabled"], bool):
        raise _fail("rain_fx.enabled", "must be true or false")
    spawn = _number(fx["max_spawn_rate"], "rain_fx.max_spawn_rate", 0.0, MAX_SPAWN_RATE, lo_ex=True)
    box = fx["box_half_extent_cm"]
    if not isinstance(box, list) or len(box) != 3:
        raise _fail("rain_fx.box_half_extent_cm", "must be an array of 3 numbers")
    extent = tuple(
        _number(v, f"rain_fx.box_half_extent_cm[{k}]", *BOX_HALF_EXTENT_RANGE) for k, v in enumerate(box)
    )
    height = _number(fx["height_offset_cm"], "rain_fx.height_offset_cm", *HEIGHT_OFFSET_RANGE)

    mpc = _object_path(root["mpc"], "mpc")

    return WeatherConfig(
        schema_version=SCHEMA_VERSION,
        initial_state=initial_state,
        initial_intensity=initial_intensity,
        initial_schedule=initial["mode"] == "schedule",
        transition_seconds=transition,
        rain_light=levels[0],
        rain_moderate=levels[1],
        rain_heavy=levels[2],
        overcast=overcast,
        rain=rain,
        surface=SurfaceParams(**surface_values),
        schedule=tuple(slots),
        schedule_times=tuple(s.minutes for s in slots),
        rain_fx_system=system,
        rain_fx_enabled=fx["enabled"],
        max_spawn_rate=spawn,
        box_half_extent_cm=extent,
        height_offset_cm=height,
        mpc=mpc,
    )


def load_config(path: str | os.PathLike | None = None) -> WeatherConfig:
    """Reads and parses weather.json (default: the repo file next to the project's Config/Golmok)."""
    file_path = os.fspath(path) if path is not None else CONFIG_FILE
    try:
        with open(file_path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        raise _fail(file_path, "cannot read file") from None
    return parse_config(text)


def resolve_rain_level(config: WeatherConfig, word: str) -> float | None:
    """ "light" | "moderate" | "heavy" -> the config's level, else None (GolmokWeather::ResolveRainLevel)."""
    if not isinstance(word, str):
        return None
    return {"light": config.rain_light, "moderate": config.rain_moderate, "heavy": config.rain_heavy}.get(
        word
    )
