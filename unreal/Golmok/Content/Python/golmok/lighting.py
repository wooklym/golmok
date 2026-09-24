"""Lighting presets for comparisons and look development (ROADMAP 1.1 / 1.3).

    import golmok.lighting as l; l.apply("overcast_morning")
    l.list_presets()

Presets act on the first DirectionalLight, SkyLight, ExponentialHeightFog and unbound
PostProcessVolume in the level (setup_dev_level.py creates them). Values are starting points for
look development, not physical measurements.
"""

import unreal

# pitch: sun elevation (negative = above horizon), yaw: azimuth. lux for DirectionalLight intensity.
PRESETS = {
    "overcast_morning": dict(pitch=-35.0, yaw=110.0, lux=2.5, kelvin=6500.0, sky=1.4,
                             fog=0.035, fog_height_falloff=0.15, volumetric=False, exposure_bias=0.3),
    "clear_noon": dict(pitch=-62.0, yaw=180.0, lux=10.0, kelvin=5600.0, sky=1.0,
                       fog=0.015, fog_height_falloff=0.2, volumetric=False, exposure_bias=0.0),
    "golden_evening": dict(pitch=-8.0, yaw=265.0, lux=4.0, kelvin=3600.0, sky=0.8,
                           fog=0.05, fog_height_falloff=0.12, volumetric=True, exposure_bias=0.5),
    "night": dict(pitch=15.0, yaw=0.0, lux=0.0, kelvin=4000.0, sky=0.15,
                  fog=0.03, fog_height_falloff=0.2, volumetric=True, exposure_bias=1.5),
}


def list_presets():
    for name, p in PRESETS.items():
        unreal.log(f"{name}: {p}")
    return list(PRESETS)


def _first(cls):
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    return next((a for a in actors if isinstance(a, cls)), None)


def apply(name):
    p = PRESETS[name]

    sun = _first(unreal.DirectionalLight)
    if sun:
        sun.set_actor_rotation(unreal.Rotator(0.0, p["pitch"], p["yaw"]), False)
        comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
        comp.set_intensity(p["lux"])
        comp.set_editor_property("use_temperature", True)
        comp.set_editor_property("temperature", p["kelvin"])
        comp.set_visibility(p["lux"] > 0.0)

    sky = _first(unreal.SkyLight)
    if sky:
        comp = sky.get_component_by_class(unreal.SkyLightComponent)
        comp.set_intensity(p["sky"])
        comp.recapture_sky()

    fog = _first(unreal.ExponentialHeightFog)
    if fog:
        comp = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
        comp.set_fog_density(p["fog"])
        comp.set_fog_height_falloff(p["fog_height_falloff"])
        comp.set_volumetric_fog(p["volumetric"])

    ppv = next((a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                if isinstance(a, unreal.PostProcessVolume) and a.get_editor_property("unbound")), None)
    if ppv:
        settings = ppv.get_editor_property("settings")
        settings.set_editor_property("override_auto_exposure_bias", True)
        settings.set_editor_property("auto_exposure_bias", p["exposure_bias"])
        ppv.set_editor_property("settings", settings)

    unreal.log(f"Lighting preset applied: {name}")
