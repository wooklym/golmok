"""Fixed viewpoints for repeatable comparison screenshots (spike 1.1: mesh vs splat, before/after).

Save viewpoints by flying the editor viewport and calling:
    import golmok.viewpoints as v; v.save("near_door_05m")
Capture every viewpoint (optionally under several lighting presets):
    v.capture("spike_a_mesh", presets=["overcast_morning", "clear_noon"])

Viewpoints live in unreal/Golmok/Config/Golmok/Viewpoints/<level>.json (text, reviewable in git).
Screenshots go to Saved/Screenshots/Golmok/<tag>/<preset>/<viewpoint>.png. Captures are spread
over editor ticks because a high-res screenshot is taken on the viewport's next draw: each request
waits until its file is written before the camera moves on, and the viewport is redrawn every tick
(an editor in the background otherwise stops drawing, and the shot would land on a later view).
"""

import json
import os
import time

import unreal

from . import lighting

RES_X, RES_Y = 2560, 1440
WAIT_TICKS = 30  # frames to let Lumen/VSM/TSR settle after each camera or lighting change
SCREENSHOT_TIMEOUT_TICKS = 300  # give up on a screenshot file after this many ticks


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
        self.pending = None  # (path, requested_at, ticks_left) while waiting for the screenshot file
        self.saved = []
        self.missing = []
        self.out_root = os.path.join(unreal.Paths.project_saved_dir(), "Screenshots", "Golmok", tag)
        self.level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        self.level_editor.editor_set_viewport_realtime(True)
        self.handle = unreal.register_slate_post_tick_callback(self._tick)
        unreal.log(f"Capturing {len(self.jobs)} screenshots -> {self.out_root}")

    def _tick(self, _dt):
        self.level_editor.editor_invalidate_viewports()
        if self.wait > 0:
            self.wait -= 1
            return
        if self.pending is not None:
            path, requested_at, ticks_left = self.pending
            if os.path.exists(path) and os.path.getmtime(path) >= requested_at:
                self.saved.append(path)
                self.pending = None
                self.wait = 5  # let the image writer finish before the camera moves
            elif ticks_left <= 0:
                unreal.log_warning(f"Screenshot not written: {path}")
                self.missing.append(path)
                self.pending = None
            else:
                self.pending = (path, requested_at, ticks_left - 1)
            return
        if self.current is not None:
            preset, name = self.current
            folder = os.path.join(self.out_root, preset or "current")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, f"{name}.png")
            requested_at = time.time() - 1.0  # file mtime resolution
            unreal.AutomationLibrary.take_high_res_screenshot(RES_X, RES_Y, path)
            self.pending = (path, requested_at, SCREENSHOT_TIMEOUT_TICKS)
            self.current = None
            return
        if not self.jobs:
            unreal.unregister_slate_post_tick_callback(self.handle)
            done = f"Capture '{self.tag}' done: {len(self.saved)} saved, {len(self.missing)} missing -> {self.out_root}"
            (unreal.log_warning if self.missing else unreal.log)(done)
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
