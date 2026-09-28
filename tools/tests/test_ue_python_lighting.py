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


# ---- WP-14a clock: set_time / mode / status through golmok.tod (fake_unreal records the console) ----


@pytest.fixture
def fake(mod, monkeypatch, tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import fake_unreal
    finally:
        sys.path.remove(str(Path(__file__).resolve().parent))
    return fake_unreal.install(monkeypatch, tmp_path, pie=True)


class ClockMode:
    """Stand-in for an unreal enum member (unreal.GolmokClockMode.CLOCK has .name == "CLOCK")."""

    def __init__(self, name):
        self.name = name


def _add_time_of_day(unreal, fake, monkeypatch, **props):
    cls = type("GolmokTimeOfDay", (object,), {})

    class Actor(cls):
        def __init__(self, values):
            self.values = values

        def get_editor_property(self, name):
            return self.values[name]

    actor = Actor(props)
    monkeypatch.setattr(unreal, "GolmokTimeOfDay", cls, raising=False)
    fake.actors.append(actor)
    return actor


def _tod_console(fake):
    return [c[1] for c in fake.calls if c[0] == "console" and c[1].startswith("golmok.tod")]


def test_clock_names_are_exported(mod):
    assert mod.CLOCK_MODES == ("fixed", "clock", "realtime")
    for name in ("set_time", "mode", "status", "CLOCK_MODES"):
        assert name in mod.__all__


def test_set_time_sends_the_console_command_to_the_pie_world(mod, unreal, fake):
    assert mod._world() is fake.pie_world
    assert mod.set_time("18:30") == "golmok.tod time 18:30"
    assert _tod_console(fake) == ["golmok.tod time 18:30"]
    assert fake.tod_commands == [["time", "18:30"]]
    assert fake.preset is None  # a clock subcommand is not a preset (screenshot folder unchanged)


def test_set_time_falls_back_to_the_editor_world(mod, unreal, fake):
    fake.pie = False
    assert mod._world() is fake.editor_world
    mod.set_time("07:05")
    assert fake.tod_commands == [["time", "07:05"]]


@pytest.mark.parametrize("bad", ["7:30", "24:00", "12:60", "noon", ""])
def test_set_time_rejects_bad_text_before_sending(mod, fake, bad):
    with pytest.raises(ValueError):
        mod.set_time(bad)
    assert _tod_console(fake) == []


def test_mode_sets_and_validates(mod, fake):
    assert mod.mode("clock") == "golmok.tod mode clock"
    assert mod.mode("Realtime") == "golmok.tod mode realtime"
    with pytest.raises(ValueError):
        mod.mode("dusk")
    assert fake.tod_commands == [["mode", "clock"], ["mode", "realtime"]]


def test_mode_query_reads_the_actor(mod, unreal, fake, monkeypatch):
    monkeypatch.delattr(unreal, "GolmokTimeOfDay", raising=False)
    assert mod.mode() is None  # no class exposed: status is still logged
    _add_time_of_day(unreal, fake, monkeypatch, clock_mode=ClockMode("CLOCK"))
    assert mod.mode() == "clock"
    assert fake.tod_commands == [["status"], ["status"]]


def test_status_returns_the_actor_values(mod, unreal, fake, monkeypatch):
    monkeypatch.delattr(unreal, "GolmokTimeOfDay", raising=False)
    assert mod.status() is None
    _add_time_of_day(
        unreal,
        fake,
        monkeypatch,
        time_of_day_minutes=1110.75,
        clock_mode=ClockMode("REALTIME"),
        clock_minutes_per_real_second=0.5,
    )
    assert mod.status() == {"time": "18:30", "mode": "realtime", "rate": 0.5, "hold": None}
    assert _tod_console(fake) == ["golmok.tod status", "golmok.tod status"]
    assert ("log", "golmok.lighting: status 18:30 realtime") in fake.logs


@pytest.mark.parametrize(
    ("minutes", "time", "hold"),
    [
        (1390.0, "23:10", "night 23:10 hold until 05:30"),  # WP-14a design 2a: night held 21:30 -> 05:30
        (1290.0, "21:30", "night 21:30 hold until 05:30"),
        (30.5, "00:30", "night 00:30 hold until 05:30"),  # across midnight
        (329.9, "05:29", "night 05:29 hold until 05:30"),
        (330.0, "05:30", None),  # hold end = ramp start
        (390.0, "06:30", None),
        (1289.5, "21:29", None),
    ],
)
def test_status_reports_the_night_hold(mod, unreal, fake, monkeypatch, minutes, time, hold):
    _add_time_of_day(
        unreal,
        fake,
        monkeypatch,
        time_of_day_minutes=minutes,
        clock_mode=ClockMode("CLOCK"),
        clock_minutes_per_real_second=10.0,
    )
    assert mod.status() == {"time": time, "mode": "clock", "rate": 10.0, "hold": hold}
    line = f"golmok.lighting: status {time} clock" + (f" | {hold}" if hold else "")
    assert [text for kind, text in fake.logs if text.startswith("golmok.lighting: status")] == [line]
    assert fake.tod_commands == [["status"]]


def test_preset_commands_still_pick_the_screenshot_folder(fake):
    import unreal as u

    u.SystemLibrary.execute_console_command(fake.pie_world, "golmok.tod golden_evening")
    u.SystemLibrary.execute_console_command(fake.pie_world, "golmok.tod mode clock")
    assert fake.preset == "golden_evening"
