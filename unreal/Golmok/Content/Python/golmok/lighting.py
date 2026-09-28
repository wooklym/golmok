"""Lighting presets for comparisons and look development (ROADMAP 1.1 / 1.3).

    import golmok.lighting as l; l.apply("overcast_morning")
    l.list_presets()
    l.set_time("18:30"); l.mode("clock"); l.mode(); l.status()     # WP-14a clock (PIE)

Presets act on the first DirectionalLight, SkyLight, ExponentialHeightFog and unbound
PostProcessVolume in the level (setup_dev_level.py creates them). Values are starting points for
look development, not physical measurements.

The values live in Config/Golmok/lighting_presets.json (single source, also read by the C++
AGolmokTimeOfDay at runtime); lighting_presets.py parses and validates it without `unreal`.
A partial preset ("interior": fog, fog_height_falloff, volumetric, exposure_bias) only touches the
keys it has, so the sun and sky keep their current values.

WP-14a: set_time / mode / status drive the runtime clock of AGolmokTimeOfDay through the console command
golmok.tod (time HH:MM | mode fixed|clock|realtime | status) in the PIE world (the editor world when no PIE
runs; the C++ spawns an AGolmokTimeOfDay only in game worlds). apply() stays the editor-only preset writer.
"""

import unreal

from .lighting_presets import (
    PRESETS_FILE,
    RANGES,
    REQUIRED_KEYS,
    format_hhmm,
    load_presets,
    parse_hhmm,
    parse_presets,
)

__all__ = [
    "PRESETS_FILE",
    "RANGES",
    "REQUIRED_KEYS",
    "CLOCK_MODES",
    "apply",
    "cycle",
    "list_presets",
    "load_presets",
    "mode",
    "parse_presets",
    "presets",
    "reload",
    "set_time",
    "status",
]

CLOCK_MODES = ("fixed", "clock", "realtime")  # EGolmokClockMode, lower case (golmok.tod mode <name>)

_cache = None  # (cycle, presets) once loaded; reload() clears it


def _loaded():
    global _cache
    if _cache is None:
        _cache = load_presets()
    return _cache


def presets():
    """Name -> preset dict (cached; reload() re-reads the JSON)."""
    return _loaded()[1]


def cycle():
    """The four presets bound to keys 1-4 / F5, in order."""
    return list(_loaded()[0])


def reload():
    global _cache
    _cache = None
    return presets()


def list_presets():
    for name, p in presets().items():
        unreal.log(f"{name}: {p}")
    return list(presets())


def _first(cls):
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    return next((a for a in actors if isinstance(a, cls)), None)


def apply(name):
    p = presets()[name]

    # Sun group: pitch, yaw, lux and kelvin are always given together (lighting_presets.py enforces it).
    if "pitch" in p:
        sun = _first(unreal.DirectionalLight)
        if sun:
            # unreal.Rotator(roll, pitch, yaw); C++ builds FRotator(Pitch, Yaw, Roll) for the same rotation.
            sun.set_actor_rotation(unreal.Rotator(0.0, p["pitch"], p["yaw"]), False)
            comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
            comp.set_intensity(p["lux"])
            comp.set_editor_property("use_temperature", True)
            comp.set_editor_property("temperature", p["kelvin"])
            comp.set_visibility(p["lux"] > 0.0)

    if "sky" in p:
        sky = _first(unreal.SkyLight)
        if sky:
            comp = sky.get_component_by_class(unreal.SkyLightComponent)
            comp.set_intensity(p["sky"])
            comp.recapture_sky()

    if "fog" in p or "volumetric" in p:
        fog = _first(unreal.ExponentialHeightFog)
        if fog:
            comp = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
            if "fog" in p:
                comp.set_fog_density(p["fog"])
                comp.set_fog_height_falloff(p["fog_height_falloff"])
            if "volumetric" in p:
                comp.set_volumetric_fog(p["volumetric"])

    if "exposure_bias" in p:
        ppv = next(
            (
                a
                for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                if isinstance(a, unreal.PostProcessVolume) and a.get_editor_property("unbound")
            ),
            None,
        )
        if ppv:
            settings = ppv.get_editor_property("settings")
            settings.set_editor_property("override_auto_exposure_bias", True)
            settings.set_editor_property("auto_exposure_bias", p["exposure_bias"])
            ppv.set_editor_property("settings", settings)

    unreal.log(f"Lighting preset applied: {name}")


# ---- WP-14a clock (runtime AGolmokTimeOfDay through golmok.tod) ------------------------------------------


def _world():
    """The PIE world while one runs (the clock lives there), else the editor world."""
    sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    return sub.get_game_world() or sub.get_editor_world()


def _tod(command):
    """Send `golmok.tod <command>`; returns the full console line."""
    line = f"golmok.tod {command}"
    unreal.SystemLibrary.execute_console_command(_world(), line)
    return line


def _time_of_day_actor():
    """The AGolmokTimeOfDay of the world, or None (no class exposed, no actor yet)."""
    cls = getattr(unreal, "GolmokTimeOfDay", None)
    statics = getattr(unreal, "GameplayStatics", None)
    if cls is None or statics is None:
        return None
    actors = statics.get_all_actors_of_class(_world(), cls)
    return actors[0] if actors else None


def _mode_name(value):
    """EGolmokClockMode as read from Python (an enum member such as GolmokClockMode.CLOCK) -> "clock"."""
    return str(getattr(value, "name", value)).rsplit(".", 1)[-1].lower()


def set_time(hhmm):
    """Jump the clock to "HH:MM" (transition over TransitionSeconds). ValueError before anything is sent."""
    minutes = parse_hhmm(hhmm)
    return _tod(f"time {format_hhmm(minutes)}")


def mode(name=None):
    """mode("fixed" | "clock" | "realtime") sets the clock mode; mode() returns the current one (None without
    an AGolmokTimeOfDay in the world) and logs the status line."""
    if name is None:
        _tod("status")
        actor = _time_of_day_actor()
        return _mode_name(actor.get_editor_property("clock_mode")) if actor else None
    key = str(name).lower()
    if key not in CLOCK_MODES:
        raise ValueError(f"mode must be one of {', '.join(CLOCK_MODES)}, got {name!r}")
    return _tod(f"mode {key}")


def status():
    """Log `golmok.tod status` and return {"time", "mode", "rate"} read off the actor (None without one)."""
    _tod("status")
    actor = _time_of_day_actor()
    if actor is None:
        return None
    return {
        "time": format_hhmm(float(actor.get_editor_property("time_of_day_minutes"))),
        "mode": _mode_name(actor.get_editor_property("clock_mode")),
        "rate": float(actor.get_editor_property("clock_minutes_per_real_second")),
    }
