"""Fixed viewpoints for repeatable comparison screenshots (spike 1.1: mesh vs splat, before/after).

Save viewpoints by flying the editor viewport and calling:
    import golmok.viewpoints as v; v.save("near_door_05m")
Capture every viewpoint (optionally under several lighting presets):
    v.capture("spike_a_mesh", presets=["overcast_morning", "clear_noon"])

Viewpoints live in unreal/Golmok/Config/Golmok/Viewpoints/<level>.json (text, reviewable in git).
Screenshots go to Saved/Screenshots/Golmok/<tag>/<preset>/<viewpoint>.png. Captures are spread
over editor ticks because high-res screenshots are taken asynchronously on the next frame.
"""

import json
import os

import unreal

from . import lighting

RES_X, RES_Y = 2560, 1440
WAIT_TICKS = 30  # frames to let Lumen/VSM/TSR settle after each camera or lighting change


def _level_name():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    return world.get_name() if world else "Untitled"


def _store_path():
    root = unreal.Paths.project_config_dir()
    folder = os.path.join(root, "Golmok", "Viewpoints")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{_level_name()}.json")


def _load():
    path = _store_path()
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(name):
    ed = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    loc, rot = ed.get_level_viewport_camera_info()
    data = _load()
    data[name] = {"location": [loc.x, loc.y, loc.z], "rotation": [rot.roll, rot.pitch, rot.yaw]}
    with open(_store_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    unreal.log(f"Saved viewpoint '{name}' ({len(data)} total) -> {_store_path()}")


def goto(name):
    vp = _load()[name]
    ed = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    ed.set_level_viewport_camera_info(unreal.Vector(*vp["location"]), unreal.Rotator(*vp["rotation"]))


class _Capture:
    def __init__(self, tag, names, presets):
        self.jobs = [(p, n) for p in presets for n in names]
        self.tag = tag
        self.wait = 0
        self.current = None
        self.out_root = os.path.join(unreal.Paths.project_saved_dir(), "Screenshots", "Golmok", tag)
        self.handle = unreal.register_slate_post_tick_callback(self._tick)
        unreal.log(f"Capturing {len(self.jobs)} screenshots -> {self.out_root}")

    def _tick(self, _dt):
        if self.wait > 0:
            self.wait -= 1
            return
        if self.current is not None:
            preset, name = self.current
            folder = os.path.join(self.out_root, preset or "current")
            os.makedirs(folder, exist_ok=True)
            unreal.AutomationLibrary.take_high_res_screenshot(RES_X, RES_Y, os.path.join(folder, f"{name}.png"))
            self.current = None
            self.wait = 5  # let the screenshot finish before moving
            return
        if not self.jobs:
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.log(f"Capture '{self.tag}' done -> {self.out_root}")
            return
        preset, name = self.jobs.pop(0)
        if preset:
            lighting.apply(preset)
        goto(name)
        self.current = (preset, name)
        self.wait = WAIT_TICKS


def capture(tag, names=None, presets=None):
    names = names or sorted(_load())
    if not names:
        unreal.log_warning("No viewpoints saved for this level. Use save('<name>') first.")
        return None
    return _Capture(tag, names, presets or [None])
