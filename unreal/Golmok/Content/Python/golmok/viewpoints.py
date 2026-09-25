"""Fixed viewpoints for repeatable comparison screenshots (spike 1.1: mesh vs splat, before/after).

Save viewpoints by flying the editor viewport and calling:
    import golmok.viewpoints as v; v.save("near_door_05m")
Capture every viewpoint (optionally under several lighting presets):
    v.capture("spike_a_mesh", presets=["overcast_morning", "clear_noon"])

Viewpoints live in unreal/Golmok/Config/Golmok/Viewpoints/<level>.json (text, reviewable in git).
Screenshots go to Saved/Screenshots/Golmok/<tag>/<preset>/<viewpoint>.png, taken in Game View (no
editor icons; game_view=False keeps the current view mode).

Keep the editor window in front while capturing. A high-res screenshot is taken on the viewport's
next draw, and an editor that has been in the background stops drawing its viewport (seen on UE 5.8.3
even with "Use Less CPU when in Background" off). So each request waits until its file is written
before the camera moves on; a shot that never comes is reported as missing instead of landing on a
later view under the wrong name. For unattended runs capture in PIE or -game instead (HighResShot).
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
    def __init__(self, tag, names, presets, game_view, on_done=None):
        self.jobs = [(p, n) for p in presets for n in names]
        self.tag = tag
        self.on_done = on_done  # on_done(saved, missing) once the capture stopped (spike_runner chains tags)
        self.wait = 0
        self.current = None
        self.pending = None  # (path, requested_at, ticks_left) while waiting for the screenshot file
        self.saved = []
        self.missing = []
        # normpath: the UE saved dir uses "/" while os.path.join adds os.sep (mixed separators on Windows)
        saved_dir = unreal.Paths.project_saved_dir()
        self.out_root = os.path.normpath(os.path.join(saved_dir, "Screenshots", "Golmok", tag))
        self.level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        self.level_editor.editor_set_viewport_realtime(True)
        # Game View hides editor sprites and gizmos so screenshots show only what the player sees.
        self.game_view = self.level_editor.editor_get_game_view()
        self.level_editor.editor_set_game_view(game_view)
        self.handle = unreal.register_slate_post_tick_callback(self._tick)
        unreal.log(f"Capturing {len(self.jobs)} screenshots -> {self.out_root}")

    def _finish(self, message, warn):
        unreal.unregister_slate_post_tick_callback(self.handle)
        self.level_editor.editor_set_game_view(self.game_view)
        (unreal.log_warning if warn else unreal.log)(message)
        if self.on_done is not None:
            try:
                self.on_done(self.saved, self.missing)
            except Exception as e:  # the chain's problem must not re-enter _finish from _tick
                unreal.log_warning(f"Capture '{self.tag}' on_done failed: {e}")

    def _tick(self, dt):
        try:
            self._step()
        except Exception as e:  # stop instead of raising on every editor tick
            self._finish(f"Capture '{self.tag}' stopped: {e}", warn=True)

    def _step(self):
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
            counts = f"{len(self.saved)} saved, {len(self.missing)} missing"
            self._finish(f"Capture '{self.tag}' done: {counts} -> {self.out_root}", warn=bool(self.missing))
            return
        preset, name = self.jobs.pop(0)
        if preset:
            lighting.apply(preset)
        goto(name)
        self.current = (preset, name)
        self.wait = WAIT_TICKS


def capture(tag, names=None, presets=None, game_view=True, on_done=None):
    """Screenshot every viewpoint (all saved ones by default) under each preset; on_done(saved, missing)
    is called once the capture has stopped, normally or on an error."""
    names = names or sorted(_load())
    if not names:
        unreal.log_warning("No viewpoints saved for this level. Use save('<name>') first.")
        return None
    return _Capture(tag, names, presets or [None], game_view, on_done)
