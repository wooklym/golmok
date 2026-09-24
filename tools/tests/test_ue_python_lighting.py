"""unreal/.../golmok/lighting.py with a stub `unreal` module (WP-05 design section 8-4).

lighting.py re-exports the pure parser (lighting_presets.py) and applies presets to fake lighting actors here:
a partial preset ("interior") must only touch the fog component and the post-process volume.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest

PY_DIR = Path(__file__).resolve().parents[2] / "unreal" / "Golmok" / "Content" / "Python"


class Recorder:
    """Records every method call as (name, args); attribute access returns a recording callable."""

    def __init__(self, label: str):
        self.label = label
        self.calls: list[tuple[str, tuple]] = []

    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)

        def call(*args):
            self.calls.append((attr, args))

        return call

    def names(self) -> list[str]:
        return [name for name, _ in self.calls]


class FakeActor(Recorder):
    def __init__(self, label: str, component: Recorder | None = None, unbound: bool = False):
        super().__init__(label)
        self.component = component
        self.unbound = unbound
        self.settings = Recorder(f"{label}.settings")

    def get_component_by_class(self, cls):
        return self.component

    def get_editor_property(self, name):
        return {"unbound": self.unbound, "settings": self.settings}[name]


class Rotator:
    def __init__(self, roll, pitch, yaw):
        self.roll, self.pitch, self.yaw = roll, pitch, yaw

    def __eq__(self, other):
        return isinstance(other, Rotator) and (self.roll, self.pitch, self.yaw) == (
            other.roll,
            other.pitch,
            other.yaw,
        )

    def __repr__(self):
        return f"Rotator({self.roll}, {self.pitch}, {self.yaw})"


@pytest.fixture(scope="module")
def unreal():
    """The shared stub `unreal` module (other UE Python tests create it the same way) plus lighting names."""
    module = sys.modules.setdefault("unreal", types.ModuleType("unreal"))
    module.DirectionalLight = type("DirectionalLight", (FakeActor,), {})
    module.SkyLight = type("SkyLight", (FakeActor,), {})
    module.ExponentialHeightFog = type("ExponentialHeightFog", (FakeActor,), {})
    module.PostProcessVolume = type("PostProcessVolume", (FakeActor,), {})
    module.DirectionalLightComponent = object()
    module.SkyLightComponent = object()
    module.ExponentialHeightFogComponent = object()
    module.EditorActorSubsystem = object()
    module.Rotator = Rotator
    module.logged = []
    module.log = module.logged.append
    return module


@pytest.fixture(scope="module")
def mod(unreal):
    sys.path.insert(0, str(PY_DIR))
    try:
        yield importlib.import_module("golmok.lighting")
    finally:
        sys.path.remove(str(PY_DIR))


@pytest.fixture
def scene(unreal, mod, monkeypatch):
    """Fake level: one actor of each lighting class; _first and get_all_level_actors both read this list."""
    sun = unreal.DirectionalLight("Sun", Recorder("SunComponent"))
    sky = unreal.SkyLight("SkyLight", Recorder("SkyComponent"))
    fog = unreal.ExponentialHeightFog("HeightFog", Recorder("FogComponent"))
    bound = unreal.PostProcessVolume("PPV_bound", unbound=False)
    ppv = unreal.PostProcessVolume("PostProcess", unbound=True)
    actors = [bound, sun, sky, fog, ppv]

    class Subsystem:
        def get_all_level_actors(self):
            return list(actors)

    monkeypatch.setattr(unreal, "get_editor_subsystem", lambda cls: Subsystem(), raising=False)
    monkeypatch.setattr(mod, "_first", lambda cls: next((a for a in actors if isinstance(a, cls)), None))
    unreal.logged.clear()
    return {"sun": sun, "sky": sky, "fog": fog, "ppv": ppv, "bound": bound}


def test_import_and_reexports(mod):
    from golmok import lighting_presets

    assert mod.load_presets is lighting_presets.load_presets
    assert mod.parse_presets is lighting_presets.parse_presets
    assert mod.PRESETS_FILE == lighting_presets.PRESETS_FILE
    assert mod.REQUIRED_KEYS == lighting_presets.REQUIRED_KEYS and mod.RANGES == lighting_presets.RANGES
    assert not hasattr(mod, "PRESETS")


def test_presets_and_cycle_match_the_pure_loader(mod):
    from golmok import lighting_presets

    cycle, presets = lighting_presets.load_presets()
    assert mod.presets() == presets
    assert mod.cycle() == cycle == ["overcast_morning", "clear_noon", "golden_evening", "night"]
    assert mod.presets() is mod.presets()  # cached
    assert mod.reload() == presets and mod.presets() is not presets


def test_list_presets_logs_every_preset(mod, unreal):
    unreal.logged.clear()
    names = mod.list_presets()
    assert names == list(mod.presets())
    assert [line.split(":")[0] for line in unreal.logged] == names


def test_apply_complete_preset_touches_everything(mod, unreal, scene):
    mod.apply("clear_noon")
    sun, sky, fog, ppv = scene["sun"], scene["sky"], scene["fog"], scene["ppv"]
    assert sun.calls == [("set_actor_rotation", (Rotator(0.0, -62.0, 180.0), False))]
    assert sun.component.calls == [
        ("set_intensity", (10.0,)),
        ("set_editor_property", ("use_temperature", True)),
        ("set_editor_property", ("temperature", 5600.0)),
        ("set_visibility", (True,)),
    ]
    assert sky.component.calls == [("set_intensity", (1.0,)), ("recapture_sky", ())]
    assert fog.component.calls == [
        ("set_fog_density", (0.015,)),
        ("set_fog_height_falloff", (0.2,)),
        ("set_volumetric_fog", (False,)),
    ]
    assert ppv.settings.calls == [
        ("set_editor_property", ("override_auto_exposure_bias", True)),
        ("set_editor_property", ("auto_exposure_bias", 0.0)),
    ]
    assert ppv.calls == [("set_editor_property", ("settings", ppv.settings))]
    assert scene["bound"].calls == [] and scene["bound"].settings.calls == []  # only the unbound volume
    assert unreal.logged == ["Lighting preset applied: clear_noon"]


def test_apply_night_hides_the_sun(mod, scene):
    mod.apply("night")
    assert ("set_visibility", (False,)) in scene["sun"].component.calls
    assert ("set_volumetric_fog", (True,)) in scene["fog"].component.calls


def test_apply_partial_interior_only_touches_fog_and_post_process(mod, unreal, scene):
    mod.apply("interior")
    sun, sky, fog, ppv = scene["sun"], scene["sky"], scene["fog"], scene["ppv"]
    assert sun.calls == [] and sun.component.calls == []
    assert sky.calls == [] and sky.component.calls == []
    assert fog.component.calls == [
        ("set_fog_density", (0.0,)),
        ("set_fog_height_falloff", (0.2,)),
        ("set_volumetric_fog", (False,)),
    ]
    assert ppv.settings.calls == [
        ("set_editor_property", ("override_auto_exposure_bias", True)),
        ("set_editor_property", ("auto_exposure_bias", 1.0)),
    ]
    assert unreal.logged == ["Lighting preset applied: interior"]


def test_apply_unknown_preset_raises_before_touching_actors(mod, scene):
    with pytest.raises(KeyError):
        mod.apply("dusk")
    assert scene["sun"].calls == [] and scene["fog"].component.calls == []


def test_apply_survives_missing_actors(mod, unreal, monkeypatch):
    class Empty:
        def get_all_level_actors(self):
            return []

    monkeypatch.setattr(unreal, "get_editor_subsystem", lambda cls: Empty(), raising=False)
    monkeypatch.setattr(mod, "_first", lambda cls: None)
    unreal.logged.clear()
    mod.apply("overcast_morning")
    assert unreal.logged == ["Lighting preset applied: overcast_morning"]
