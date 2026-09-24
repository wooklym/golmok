"""Lighting presets for comparisons and look development (ROADMAP 1.1 / 1.3).

    import golmok.lighting as l; l.apply("overcast_morning")
    l.list_presets()

Presets act on the first DirectionalLight, SkyLight, ExponentialHeightFog and unbound
PostProcessVolume in the level (setup_dev_level.py creates them). Values are starting points for
look development, not physical measurements.

The values live in Config/Golmok/lighting_presets.json (single source, also read by the C++
AGolmokTimeOfDay at runtime); lighting_presets.py parses and validates it without `unreal`.
A partial preset ("interior": fog, fog_height_falloff, volumetric, exposure_bias) only touches the
keys it has, so the sun and sky keep their current values.
"""

import unreal

from .lighting_presets import PRESETS_FILE, RANGES, REQUIRED_KEYS, load_presets, parse_presets

__all__ = [
    "PRESETS_FILE",
    "RANGES",
    "REQUIRED_KEYS",
    "apply",
    "cycle",
    "list_presets",
    "load_presets",
    "parse_presets",
    "presets",
    "reload",
]

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
