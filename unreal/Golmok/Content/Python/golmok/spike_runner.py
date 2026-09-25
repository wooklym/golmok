"""Spike 1.1 capture and measurement helpers (research/08). Unattended screenshots run in PIE (design D11);
performance numbers come from -game runs (D12); the PIE CSV is a reference value only.

    import golmok.spike_runner as s
    s.prepare()                                    # which of the 10 viewpoints are missing
    s.capture_all()                                # tags a b c ac x 3 presets x 10 viewpoints in PIE
                                                   #   -> Saved/Screenshots/Golmok/<tag>/<preset>/<name>.png
    s.capture_all(quit_editor=True)                # unattended -ExecCmds launch: quit the editor at the end
    s.capture_all(tags=("a",), presets=("clear_noon", "night"), mode="editor")   # attended, editor viewport
    s.save_layer_levels(); s.game_scripts(paths=("walk_01",))   # -game CSV runs -> Saved/Golmok/spike/*.ps1
    s.game_scripts(paths=("walk_01",), res=(2560, 1440))        # labels *_1440p (label_suffix= for DLSS)
    s.perf_all(paths=("walk_01",))                 # PIE CSV (reference only)
    s.contact_sheet(); s.report_template(perf_markdown=open(...).read())

The PIE path is a slate post-tick state machine (one PIE session per tag). editor_request_begin_play() plays
in the first active level viewport (the engine hard-wires that destination; the play-mode and new-window
settings are not consulted), so the shot size cannot come from a window: every viewpoint becomes a two-sample
600 s dwell path (Saved/Golmok/Paths/vp_<name>.json) that the C++ `golmok.path play` follows with the
character hidden, then `HighResShot 2560x1440 filename="<stem>"` (viewpoints.RES_X/RES_Y, explicit) renders
the PIE game viewport at that size into <name>00000.png, which is renamed to <name>.png; a PNG of another
size is kept but warned about (runbook #35). Whether a level-viewport PIE keeps drawing with the editor window
in the background is unverified (V-01: the editor viewport stopped drawing; runbook #35). All waits are
seconds on `_now` (tests use a fake clock). quit_editor=True ends the editor once the run is over (V-03: a
trailing `Quit` in -ExecCmds does not; runbook #34).
Layers: tag a = zone visual, b = Spike_b_* actors, c = Spike_c_* actors, ac = zone + Spike_c_* (design D13).
Every uncertain editor call sits behind hasattr with a warning naming its row in
docs/runbooks/pc-verify-wp06.md section 12; log lines come from _pure.LOG (the runbooks quote them).
"""

import glob
import json
import os
import time

import unreal

from . import _pure, viewpoints

_now = time.monotonic  # tests replace it with a fake clock (tools/tests fake unreal, tick())

PIE_START_TIMEOUT_S = 60.0
PIE_STOP_TIMEOUT_S = 30.0
WARMUP_S = 3.0
TOD_WAIT_S = 3.0
SETTLE_S = 1.5
FILE_TIMEOUT_S = 30.0
STOPPLAY_WAIT_S = 0.3
PIE_RESTART_GAP_S = 1.0  # between the end of one tag's PIE and the next editor_request_begin_play
QUIT_WAIT_S = 5.0  # quit_editor: at most this long for PIE to end (end_play is deferred) before quitting
CSV_GRACE_S = 60.0  # WAIT_CSV timeout = path length + this
LAYER_LEVEL_PREFIX = "/Game/Golmok/Maps/L_Spike_"
MANUAL_WINDOW_HOW = "manual: Editor Preferences > Level Editor > Play > New Window Size (runbook #21)"
PHOTO_EXTENSIONS = ("jpg", "jpeg", "png", "JPG", "JPEG", "PNG")

_TICK_CHAIN_LIMIT = 32  # immediate state transitions allowed inside one slate tick


# ---- small helpers -----------------------------------------------------------------------------------------


def _log(key, **kw):
    unreal.log(_pure.fmt(key, **kw))


def _warn(message):
    unreal.log_warning(_pure.fmt("sr.warn", message=message))


def _abs(path):
    """Absolute, normalized OS path (the editor may hand out paths relative to its binaries folder)."""
    paths = unreal.Paths
    if hasattr(paths, "convert_relative_path_to_full"):
        path = paths.convert_relative_path_to_full(path)
    return os.path.normpath(os.path.abspath(path))


def _saved_dir():
    return _abs(unreal.Paths.project_saved_dir())


def _level_editor():
    return unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def _editor_actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()


def _layer_level(tag):
    _pure.layer_state(tag)  # validates the tag
    return f"{LAYER_LEVEL_PREFIX}{tag}"


def _viewpoints(level=None):
    """(level name, {name: {location, rotation}}) from Config/Golmok/Viewpoints/<level>.json."""
    if level is None:
        return viewpoints._level_name(), viewpoints._load()
    name = str(level).replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].split(".")[0]
    path = os.path.join(unreal.Paths.project_config_dir(), "Golmok", "Viewpoints", f"{name}.json")
    if not os.path.exists(path):
        return name, {}
    with open(path, encoding="utf-8") as f:
        return name, json.load(f)


def _path_file(saved_dir, walk):
    return os.path.join(saved_dir, *_pure.PATH_FOLDER.split("/"), f"{_pure.validate_name(walk)}.json")


def _require_path_files(saved_dir, walks):
    files = []
    for walk in walks:
        path = _path_file(saved_dir, walk)
        if not os.path.isfile(path):
            raise RuntimeError(f"path file {path} missing: record it first: golmok.path record {walk}")
        files.append(path)
    return files


def _path_length_s(path):
    """Last sample time of a recorded camera path JSON (GolmokStatsMath::FormatPathJson)."""
    with open(path, encoding="utf-8") as f:
        samples = json.load(f).get("samples") or []
    return float(samples[-1]["t"]) if samples else 0.0


def _fresh(path, requested_at):
    return os.path.isfile(path) and os.path.getmtime(path) >= requested_at


def _console(world, cmd):
    """Send one console command to the PIE world (logged as sr.cmd)."""
    _log("sr.cmd", command=cmd)
    system = getattr(unreal, "SystemLibrary", None)
    if system is None or not hasattr(system, "execute_console_command"):
        raise RuntimeError("unreal.SystemLibrary.execute_console_command unavailable (runbook #15)")
    system.execute_console_command(world, cmd)


def _pie_world():
    """The PIE world: UnrealEditorSubsystem.get_game_world(), or the deprecated
    EditorLevelLibrary.get_pie_worlds fallback (runbook #15); None while no PIE world exists."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if world is not None:
        return world
    library = getattr(unreal, "EditorLevelLibrary", None)
    if library is not None and hasattr(library, "get_pie_worlds"):
        worlds = list(library.get_pie_worlds(False) or [])
        if worlds:
            _warn(
                "UnrealEditorSubsystem.get_game_world() is None; using EditorLevelLibrary.get_pie_worlds"
                " (deprecated, runbook #15)"
            )
            return worlds[0]
    return None


def _engine_dir():
    paths = getattr(unreal, "Paths", None)
    if paths is not None and hasattr(paths, "engine_dir"):
        folder = paths.engine_dir()
        if folder:
            return _abs(folder)
    root = os.environ.get("UE_ROOT")
    if root:
        _warn("unreal.Paths.engine_dir unavailable; using $env:UE_ROOT (runbook #27)")
        return os.path.normpath(root)
    raise RuntimeError(
        "engine folder unknown: unreal.Paths.engine_dir() unavailable and UE_ROOT is not set"
        " (runbook #27; tools/ue/common.ps1 convention)"
    )


def _editor_exe():
    return os.path.join(_engine_dir(), "Binaries", "Win64", "UnrealEditor.exe")


def _uproject():
    paths = unreal.Paths
    if hasattr(paths, "get_project_file_path"):
        path = paths.get_project_file_path()
        if path:
            return _abs(path)
    _warn("Paths.get_project_file_path unavailable; assuming <Content>/../Golmok.uproject (runbook #27)")
    return _abs(os.path.join(paths.project_content_dir(), "..", "Golmok.uproject"))


def _set_hidden(actor, hidden, editor):
    """Hide/show a Spike_* layer actor; plugin actors may lack the setters (runbook #19)."""
    try:
        actor.set_actor_hidden_in_game(hidden)
        if editor:
            actor.set_is_temporarily_hidden_in_editor(hidden)
    except Exception as e:
        label = actor.get_actor_label()
        _warn(f"{label}: set_actor_hidden_in_game failed ({e}); using the 'hidden' property (runbook #19)")
        actor.set_editor_property("hidden", hidden)


def _quit_editor(what):
    """End the editor (unattended -ExecCmds runs; V-03: a trailing `Quit` does not):
    SystemLibrary.quit_editor, else the QUIT_EDITOR console command (docs/runbooks/pc-setup.md), else a
    warning (runbook #34)."""
    _log("sr.quit", what=what)
    system = getattr(unreal, "SystemLibrary", None)
    try:
        if system is not None and hasattr(system, "quit_editor"):
            system.quit_editor()
            return True
        _warn("unreal.SystemLibrary.quit_editor unavailable; sending QUIT_EDITOR (runbook #34)")
        _console(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(), "QUIT_EDITOR")
        return True
    except Exception as e:
        _warn(f"could not quit the editor: close it by hand (runbook #34); {e}")
        return False


def _start(what, quit_editor, build):
    """build() the run; with quit_editor an error before the machine exists still ends the editor."""
    try:
        return build()
    except Exception as e:
        if quit_editor:
            _warn(f"{what} could not start: {e}")
            _quit_editor(f"{what} (setup failed)")
        raise


# ---- public: viewpoints, window, layers, layer levels ------------------------------------------------------


def prepare(level=None, names=_pure.VIEWPOINT_NAMES):
    """Which of `names` are not saved for the level (sorted); logs sr.prepare."""
    names = tuple(_pure.validate_name(n) for n in names)
    level_name, saved = _viewpoints(level)
    missing = _pure.missing_viewpoints(saved, names)
    _log("sr.prepare", level=level_name, saved=len(saved), missing=missing)
    return missing


def configure_pie_window(size=_pure.PIE_WINDOW):
    """Optional helper for an attended PIE started from the Play button in "New Editor Window (PIE)" mode
    (e.g. pc-spike S13 `golmok.screenshot`, whose size is the game viewport x ScreenshotMultiplier): sets the
    new-window size and that play mode; returns how the size was set. capture_all does NOT use it:
    editor_request_begin_play() always plays in the level viewport and ignores these settings."""
    w, h = (int(v) for v in size)
    how = "LevelEditorPlaySettings"
    try:
        if not (hasattr(unreal, "get_default_object") and hasattr(unreal, "LevelEditorPlaySettings")):
            raise AttributeError("unreal.LevelEditorPlaySettings / get_default_object not exposed")
        settings = unreal.get_default_object(unreal.LevelEditorPlaySettings)
        settings.set_editor_property("new_window_width", w)
        settings.set_editor_property("new_window_height", h)
    except Exception as e:
        how = MANUAL_WINDOW_HOW
        _warn(f"PIE window: {how}; {e}")
    else:
        # EPlayModeType::PlayMode_InEditorFloating, pythonized verbatim (runbook #21)
        mode = getattr(getattr(unreal, "PlayModeType", None), "PLAY_MODE_IN_EDITOR_FLOATING", None)
        try:
            if mode is None:
                raise AttributeError("unreal.PlayModeType.PLAY_MODE_IN_EDITOR_FLOATING not exposed")
            settings.set_editor_property("last_executed_play_mode_type", mode)
        except Exception as e:
            _warn(f"PIE play mode: set 'New Editor Window (PIE)' by hand (runbook #21); {e}")
    _log("sr.window", w=w, h=h, multiplier=_pure.SCREENSHOT_MULTIPLIER, how=how)
    return how


def apply_layers(tag, world=None):
    """Show the layers of `tag` (design D13) on the editor level (world None) or in a PIE world."""
    state = _pure.layer_state(tag)
    if world is None:
        actors, where = _editor_actors(), "editor"
    elif hasattr(unreal, "GameplayStatics"):
        actors, where = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor), "pie"
    else:
        _warn("unreal.GameplayStatics unavailable: PIE layers not applied (runbook #14, golmok.zone.unload)")
        actors, where = [], "pie"
    n = 0
    for actor in actors:
        if isinstance(actor, unreal.GolmokZone):
            actor.set_visual_visible(state["zone_visual"])
            n += 1
            continue
        group = _pure.spike_actor_group(str(actor.get_actor_label()))
        if group is None:
            continue
        _set_hidden(actor, not state[group], editor=world is None)
        n += 1
    _log(
        "sr.layers",
        tag=tag,
        zone_visual=state["zone_visual"],
        spike_b=state["spike_b"],
        spike_c=state["spike_c"],
        n=n,
        where=where,
    )
    return {**state, "actors": n}


def save_layer_levels(tags=("b", "c", "ac"), base_level=None):
    """Duplicate the level once per tag with that tag's layers applied and AutoManaged off where the zone
    visual layer is hidden (-game must not distance-load it): /Game/Golmok/Maps/L_Spike_<tag>."""
    from . import synthetic_zone as sz

    base = base_level or sz._current_level_path()
    level_editor = _level_editor()
    library = unreal.EditorAssetLibrary
    out = []
    try:
        for tag in tags:
            state = _pure.layer_state(tag)
            dst = _layer_level(tag)
            if library.does_asset_exist(dst):
                library.delete_asset(dst)
            if not library.duplicate_asset(base, dst):
                raise RuntimeError(
                    f"could not duplicate {base} -> {dst} (runbook #18: File > Save Current Level As, then"
                    f" apply_layers({tag!r}))"
                )
            if not level_editor.load_level(dst):
                raise RuntimeError(f"could not open {dst} (runbook #18)")
            apply_layers(tag)
            for actor in _editor_actors():
                if isinstance(actor, unreal.GolmokZone):
                    actor.set_editor_property("auto_managed", state["zone_visual"])
            level_editor.save_current_level()
            _log("sr.level", package=dst, tag=tag)
            out.append(dst)
    finally:
        if not level_editor.load_level(base):
            _warn(f"could not reopen {base} after the layer levels")
    return out


# ---- PIE state machines ------------------------------------------------------------------------------------


class _PieSession:
    """Slate post-tick state machine: one PIE session per tag, jobs (tag, preset, name) tag-major.

    IDLE -> LAYERS -> BEGIN_PIE -> WAIT_PIE -> WARMUP -> HUD_OFF -> LAYERS_PIE -> JOB -> [TOD] ->
    <subclass job states> -> JOB ... -> END_PIE -> WAIT_END -> RESTART_GAP -> IDLE (next tag) / DONE. Waits
    are seconds on _now(); tick(dt) is public so tests drive it directly. Errors end the run through _finish
    (never raise on an editor tick). With quit_editor the callback stays registered after DONE until PIE has
    ended (or QUIT_WAIT_S), then quits the editor - on every exit path, after the sr.done line."""

    what = "capture"
    first_job_state = "PATH"

    def __init__(self, jobs, quit_editor=False):
        self.quit_editor = bool(quit_editor)
        self.quit_pending = False
        self.jobs = list(jobs)
        self.saved = []
        self.missing = []
        self.saved_dir = _saved_dir()
        self.root = self.saved_dir
        self.level_editor = _level_editor()
        self.tag = None
        self.preset = None
        self.world = None
        self.job = None
        self.state = "IDLE"
        self.deadline = 0.0
        self.done = False
        self._statics_warned = False
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        if self.level_editor.is_in_play_in_editor():
            _warn("PIE is already running; ending it before the first tag")
            self.level_editor.editor_request_end_play()
            self._wait(PIE_STOP_TIMEOUT_S, "WAIT_END")

    # -- driving --

    def tick(self, dt=0.0):
        if self.done:
            if self.quit_pending:
                self._quit_step()
            return
        try:
            for _ in range(_TICK_CHAIN_LIMIT):
                if self.done or not self._step():
                    break
        except Exception as e:  # never raise on an editor tick
            self._finish(f"{self.what} stopped in state {self.state}: {e}", warn=True)

    def _wait(self, seconds, next_state):
        self.deadline = _now() + seconds
        self.state = next_state
        return False

    def _elapsed(self):
        return _now() >= self.deadline

    def _finish(self, message, warn=False):
        if self.done:
            return
        self.done = True
        if self.quit_editor:  # keep ticking: quit once PIE has ended (end_play is deferred), see _quit_step
            self.quit_pending = True
            self.deadline = _now() + QUIT_WAIT_S
        else:
            unreal.unregister_slate_post_tick_callback(self.handle)
        if warn:
            _warn(message)
        try:
            if self.level_editor.is_in_play_in_editor():
                self.level_editor.editor_request_end_play()
                _log("sr.pie", state="end", tag=self.tag)
        except Exception as e:
            _warn(f"could not end PIE: {e}")

    def _quit_step(self):
        """After DONE with quit_editor: wait for PIE to end (at most QUIT_WAIT_S), then quit the editor."""
        try:
            if self.level_editor.is_in_play_in_editor() and not self._elapsed():
                return
        except Exception:
            pass
        self.quit_pending = False
        unreal.unregister_slate_post_tick_callback(self.handle)
        _quit_editor(self.what)

    def _complete(self):
        self._finish("")
        text = _pure.fmt(
            "sr.done", what=self.what, saved=len(self.saved), missing=len(self.missing), root=self.root
        )
        (unreal.log_warning if self.missing else unreal.log)(text)

    def _pie_ready(self):
        """The PIE world once PIE runs and its PlayerController exists, else None."""
        if not self.level_editor.is_in_play_in_editor():
            return None
        world = _pie_world()
        if world is None:
            return None
        statics = getattr(unreal, "GameplayStatics", None)
        if statics is None:
            if not self._statics_warned:
                self._statics_warned = True
                _warn("unreal.GameplayStatics unavailable: not waiting for a PlayerController (runbook #14)")
        elif statics.get_player_controller(world, 0) is None:
            return None
        return world

    def _before_pie(self):
        """Hook: files the PIE session needs (dwell paths)."""

    def _job_step(self):
        raise RuntimeError(f"unknown state {self.state!r}")

    def _step(self):
        """One transition; True = run the next one now, False = wait for the next tick."""
        s = self.state
        if s == "IDLE":
            if not self.jobs:
                self._complete()
                return False
            self.tag, self.preset, self.world = self.jobs[0][0], None, None
            self.state = "LAYERS"
            return True
        if s == "LAYERS":
            apply_layers(self.tag)
            self.state = "BEGIN_PIE"
            return True
        if s == "BEGIN_PIE":
            self._before_pie()
            self.level_editor.editor_request_begin_play()
            _log("sr.pie", state="begin", tag=self.tag)
            return self._wait(PIE_START_TIMEOUT_S, "WAIT_PIE")
        if s == "WAIT_PIE":
            world = self._pie_ready()
            if world is not None:
                self.world = world
                return self._wait(WARMUP_S, "WARMUP")
            if self._elapsed():
                self._finish(f"PIE did not start within {PIE_START_TIMEOUT_S:.0f} s (runbook #16)", warn=True)
            return False
        if s == "WARMUP":
            if not self._elapsed():
                return False
            self.state = "HUD_OFF"
            return True
        if s == "HUD_OFF":
            _console(self.world, "golmok.hud 0")
            self.state = "LAYERS_PIE"
            return True
        if s == "LAYERS_PIE":
            apply_layers(self.tag, self.world)
            self.state = "JOB"
            return True
        if s == "JOB":
            if not self.jobs or self.jobs[0][0] != self.tag:
                self.state = "END_PIE"
                return True
            self.job = self.jobs.pop(0)
            preset = self.job[1]
            if preset != self.preset:
                self.preset = preset
                _console(self.world, f"golmok.tod {preset}")
                return self._wait(TOD_WAIT_S, "TOD")
            self.state = self.first_job_state
            return True
        if s == "TOD":
            if not self._elapsed():
                return False
            self.state = self.first_job_state
            return True
        if s == "END_PIE":
            self.level_editor.editor_request_end_play()
            _log("sr.pie", state="end", tag=self.tag)
            return self._wait(PIE_STOP_TIMEOUT_S, "WAIT_END")
        if s == "WAIT_END":
            if self.level_editor.is_in_play_in_editor():
                if not self._elapsed():
                    return False
                _warn(f"PIE did not stop within {PIE_STOP_TIMEOUT_S:.0f} s; continuing (runbook #16)")
            return self._wait(PIE_RESTART_GAP_S, "RESTART_GAP")
        if s == "RESTART_GAP":
            if not self._elapsed():
                return False
            self.state = "IDLE"
            return True
        return self._job_step()


class _PieCapture(_PieSession):
    """Screenshots in PIE: per job PATH (golmok.path play vp_<name>) -> SETTLE -> SHOT (HighResShot at the
    explicit viewpoints.RES_X x RES_Y) -> WAIT_FILE (<name>00000.png renamed to <name>.png, or <name>.png;
    size checked) -> STOPPLAY (always)."""

    what = "capture"
    first_job_state = "PATH"

    def __init__(self, jobs, saved_viewpoints, level, quit_editor=False):
        self.viewpoints = dict(saved_viewpoints)
        self.level = level
        self.names = sorted({job[2] for job in jobs})
        self.created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.paths_written = False
        self.path = None
        self.requested_at = 0.0
        super().__init__(jobs, quit_editor)
        self.root = os.path.join(self.saved_dir, *_pure.SCREENSHOT_FOLDER.split("/"))

    def _before_pie(self):
        if self.paths_written:
            return
        folder = os.path.join(self.saved_dir, *_pure.PATH_FOLDER.split("/"))
        os.makedirs(folder, exist_ok=True)
        for name in self.names:
            vp = self.viewpoints[name]
            text = _pure.dwell_path_json(
                f"vp_{name}", self.level, vp["location"], vp["rotation"], created=self.created
            )
            with open(os.path.join(folder, f"vp_{name}.json"), "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
        self.paths_written = True

    def _screenshot_ready(self):
        """(w, h) once the requested PNG exists (fallback name renamed), else None."""
        path = self.path
        if not _fresh(path, self.requested_at):
            fallback = _pure.screenshot_fallback_path(path)
            if not _fresh(fallback, self.requested_at):
                return None
            try:
                os.replace(fallback, path)  # runbook #30
            except OSError:
                return None  # the engine may still hold the fallback file open (Windows); retry next tick
        try:
            with open(path, "rb") as f:
                return _pure.png_size(f.read(24))
        except (OSError, ValueError):
            return None  # still being written

    def _job_step(self):
        s = self.state
        tag, preset, name = self.job
        if s == "PATH":
            _console(self.world, f"golmok.path play vp_{name}")
            return self._wait(SETTLE_S, "SETTLE")
        if s == "SETTLE":
            if not self._elapsed():
                return False
            self.state = "SHOT"
            return True
        if s == "SHOT":
            # An explicit size: the PIE plays in the level viewport, so `golmok.screenshot` (viewport size x
            # ScreenshotMultiplier) would give whatever that panel measures (F1). HighResShot reaches the PIE
            # UGameViewportClient through the player controller and names the file <stem>00000.png (the next
            # unused counter, so a stale one from an aborted run is removed first). "/" keeps the quoted path
            # free of backslash escapes.
            self.requested_at = time.time() - 1.0  # file mtime resolution
            self.path = os.path.normpath(_pure.screenshot_path(self.saved_dir, tag, preset, name))
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            stale = _pure.screenshot_fallback_path(self.path)
            if os.path.isfile(stale):
                os.remove(stale)
            stem = os.path.splitext(self.path)[0].replace("\\", "/")
            _console(self.world, f'HighResShot {viewpoints.RES_X}x{viewpoints.RES_Y} filename="{stem}"')
            return self._wait(FILE_TIMEOUT_S, "WAIT_FILE")
        if s == "WAIT_FILE":
            size = self._screenshot_ready()
            if size is None and not self._elapsed():
                return False
            if size is not None:
                _log("sr.captured", path=self.path, w=size[0], h=size[1])
                if tuple(size) != (viewpoints.RES_X, viewpoints.RES_Y):
                    _warn(
                        f"{self.path}: {size[0]}x{size[1]}, expected {viewpoints.RES_X}x{viewpoints.RES_Y}"
                        " (runbook #35)"
                    )
                self.saved.append(self.path)
            else:
                why = "timeout: file exists but is not a PNG" if os.path.exists(self.path) else "timeout"
                unreal.log_warning(_pure.fmt("sr.missing", path=self.path, why=why))
                self.missing.append(self.path)
            self.state = "STOPPLAY"
            return True
        if s == "STOPPLAY":
            _console(self.world, "golmok.path stopplay")
            return self._wait(STOPPLAY_WAIT_S, "STOPPLAY_WAIT")
        if s == "STOPPLAY_WAIT":
            if not self._elapsed():
                return False
            self.state = "JOB"
            return True
        return super()._job_step()


class _PiePerf(_PieSession):
    """CSV in PIE (reference only): per job PLAY (golmok.path play <walk> --csv) -> WAIT_CSV (newest
    Profile*.csv in the Saved candidates, timeout = path length + CSV_GRACE_S)."""

    what = "perf (PIE, reference only)"
    first_job_state = "PLAY"

    def __init__(self, jobs, lengths_s, quit_editor=False):
        self.lengths = dict(lengths_s)
        self.not_before = 0.0
        super().__init__(jobs, quit_editor)
        self.root = os.path.join(self.saved_dir, "Profiling", "CSV")
        candidates = _pure.saved_dir_candidates(self.saved_dir, os.environ.get("LOCALAPPDATA"))
        self.csv_dirs = _pure.csv_dirs(candidates)

    def _job_step(self):
        s = self.state
        tag, preset, walk = self.job
        if s == "PLAY":
            self.not_before = time.time() - 1.0
            _console(self.world, f"golmok.path play {walk} --csv")
            return self._wait(self.lengths.get(walk, 0.0) + CSV_GRACE_S, "WAIT_CSV")
        if s == "WAIT_CSV":
            path = _pure.newest_file(
                self.csv_dirs, "Profile*.csv", self.not_before, os.path.isfile, os.path.getmtime, glob.glob
            )
            if path is None and not self._elapsed():
                return False
            label = _pure.perf_label(tag, preset, walk)
            if path is not None:
                path = os.path.normpath(path)
                _log("sr.csv", path=path, label=label)
                self.saved.append(path)
            else:
                pattern = os.path.normpath(os.path.join(self.root, "Profile*.csv"))
                unreal.log_warning(_pure.fmt("sr.missing", path=pattern, why=f"timeout, {label}"))
                self.missing.append(label)
            self.state = "JOB"
            return True
        return super()._job_step()


class _EditorCapture:
    """Attended path: viewpoints.capture per tag (editor viewport, window in front), chained with on_done."""

    what = "capture (editor)"

    def __init__(self, tags, presets, names):
        self.tags = list(tags)
        self.presets = list(presets)
        self.names = list(names)
        self.saved = []
        self.missing = []
        self.captures = []
        self.done = False
        self.root = os.path.join(_saved_dir(), *_pure.SCREENSHOT_FOLDER.split("/"))
        self._next()

    def _next(self, saved=(), missing=()):
        self.saved += list(saved)
        self.missing += list(missing)
        if not self.tags:
            self.done = True
            text = _pure.fmt(
                "sr.done", what=self.what, saved=len(self.saved), missing=len(self.missing), root=self.root
            )
            (unreal.log_warning if self.missing else unreal.log)(text)
            return
        tag = self.tags.pop(0)
        apply_layers(tag)
        index = len(self.captures)
        self.captures.append(None)  # slot first: on_done may run (and chain) before capture() returns
        capture = viewpoints.capture(tag, self.names, self.presets, on_done=self._next)
        self.captures[index] = capture
        if capture is None:
            self._next()


# ---- public: capture, perf, scripts, sheet, report ---------------------------------------------------------


def _resolve_names(names, saved):
    """Viewpoint names to capture: the saved subset of `names` (VIEWPOINT_NAMES by default), warning about the
    rest; RuntimeError when nothing is saved."""
    wanted = tuple(_pure.validate_name(n) for n in (names or _pure.VIEWPOINT_NAMES))
    unsaved = [n for n in wanted if n not in saved]
    chosen = tuple(n for n in wanted if n in saved)
    if not chosen:
        raise RuntimeError(
            f"no saved viewpoints for this level ({', '.join(wanted)}): viewpoints.save('<name>') first"
        )
    if unsaved:
        _warn(f"viewpoints: {', '.join(unsaved)} not saved (viewpoints.save); capturing {list(chosen)}")
    return chosen


def capture_all(tags=_pure.TAGS, presets=_pure.DEFAULT_PRESETS, names=None, mode="pie", quit_editor=False):
    """Screenshots of every (tag, preset, viewpoint): mode 'pie' = unattended PIE state machine (returns the
    _PieCapture; it runs on slate ticks), mode 'editor' = viewpoints.capture per tag (window in front).
    quit_editor=True (pie only; for -ExecCmds launches) quits the editor after the run, also after an
    error."""
    if mode not in ("pie", "editor"):
        raise ValueError(f"mode must be 'pie' or 'editor', not {mode!r}")
    if quit_editor and mode != "pie":
        raise ValueError("quit_editor needs mode='pie' (mode='editor' is the attended path)")

    def build():
        tags_ = tuple(tags)
        presets_ = tuple(_pure.validate_name(p) for p in presets)
        for tag in tags_:
            _pure.layer_state(tag)
        level, saved = _viewpoints()
        chosen = _resolve_names(names, saved)
        if mode == "pie":
            jobs = _pure.capture_jobs(tags_, presets_, chosen)
            return _PieCapture(jobs, saved, level, quit_editor=quit_editor)
        return _EditorCapture(tags_, presets_, chosen)

    return _start("capture", quit_editor, build)


def perf_all(paths=("walk_01",), tags=_pure.TAGS, presets=("clear_noon",), quit_editor=False):
    """PIE CSV per (tag, preset, path) — reference only; -game (game_scripts) is the measurement of record.
    quit_editor=True quits the editor after the run (unattended -ExecCmds launches)."""

    def build():
        tags_ = tuple(tags)
        presets_ = tuple(_pure.validate_name(p) for p in presets)
        for tag in tags_:
            _pure.layer_state(tag)
        walks = tuple(_pure.validate_name(w) for w in paths)
        files = _require_path_files(_saved_dir(), walks)
        lengths = {walk: _path_length_s(path) for walk, path in zip(walks, files, strict=True)}
        return _PiePerf(_pure.capture_jobs(tags_, presets_, walks), lengths, quit_editor=quit_editor)

    return _start("perf (PIE, reference only)", quit_editor, build)


def game_scripts(
    paths=("walk_01",),
    tags=_pure.TAGS,
    presets=("clear_noon",),
    res=(1920, 1080),
    base_level=None,
    timeout_s=900,
    label_suffix=None,
):
    """Write Saved/Golmok/spike/run_game_perf.ps1: one -game -RenderOffscreen CSV run per (tag, preset, path)
    on L_Spike_<tag> (tag a: the base level); returns the script path. Labels (CSV, game_<label>.log,
    golmok-perf --label) are <tag>_<preset>_<walk>[_<suffix>]: the suffix defaults to "<height>p" for a
    resolution other than 1920x1080 (so a 1440p run does not overwrite the 1080p CSVs); pass label_suffix
    (e.g. "1440p_dlss") for DLSS runs, "" for none. Only the .ps1 itself is overwritten by the next call."""
    from . import synthetic_zone as sz

    saved = _saved_dir()
    walks = tuple(_pure.validate_name(w) for w in paths)
    path_files = _require_path_files(saved, walks)
    exe, uproject = _editor_exe(), _uproject()
    base = base_level or sz._current_level_path()
    spike_dir = os.path.join(saved, "Golmok", "spike")
    if label_suffix is None:
        label_suffix = "" if tuple(int(v) for v in res) == (1920, 1080) else f"{int(res[1])}p"
    if label_suffix:
        _pure.validate_name(label_suffix)
    runs = []
    for tag in tags:
        _pure.layer_state(tag)
        map_path = base if tag == "a" else _layer_level(tag)
        for preset in presets:
            for walk in walks:
                label = _pure.perf_label(tag, preset, walk) + (f"_{label_suffix}" if label_suffix else "")
                argv = _pure.game_command_line(
                    exe,
                    uproject,
                    map_path,
                    walk=walk,
                    preset=preset,
                    res=res,
                    log_path=os.path.join(spike_dir, f"game_{label}.log"),
                )
                runs.append({"label": label, "argv": argv})
    candidates = _pure.saved_dir_candidates(saved, os.environ.get("LOCALAPPDATA"))
    text = _pure.powershell_script(runs, path_files, candidates, os.path.join(spike_dir, "csv"), timeout_s)
    os.makedirs(spike_dir, exist_ok=True)
    script = os.path.join(spike_dir, "run_game_perf.ps1")
    with open(script, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write(text)
    _log("sr.script", path=script, runs=len(runs))
    return script


def contact_sheet(tags=_pure.TAGS, presets=_pure.DEFAULT_PRESETS, names=None, photos_dir=None):
    """Saved/Screenshots/Golmok/contact_sheet.html: one table per preset, viewpoint rows, tag columns and an
    optional reference-photo column (photos_dir/<name>.jpg|jpeg|png)."""
    root = os.path.join(_saved_dir(), *_pure.SCREENSHOT_FOLDER.split("/"))
    names = tuple(names) if names else _pure.VIEWPOINT_NAMES

    def image_rel(tag, preset, name):
        rel = f"{tag}/{preset}/{name}.png"
        return rel if os.path.isfile(os.path.join(root, tag, preset, f"{name}.png")) else None

    def photo_rel(name):
        for ext in PHOTO_EXTENSIONS:
            path = os.path.abspath(os.path.join(photos_dir, f"{name}.{ext}"))
            if not os.path.isfile(path):
                continue
            try:
                inside = os.path.commonpath([os.path.abspath(root), path]) == os.path.abspath(root)
            except ValueError:  # different drives
                inside = False
            return os.path.relpath(path, root).replace("\\", "/") if inside else _pure.file_uri(path)
        return None

    html = _pure.contact_sheet_html(tags, presets, names, image_rel, photo_rel if photos_dir else None)
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, "contact_sheet.html")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    _log("sr.sheet", path=path)
    return path


def report_template(tags=_pure.TAGS, presets=_pure.DEFAULT_PRESETS, perf_markdown=""):
    """Saved/Golmok/spike/report_template.md (research/08 result tables); the CSV labels of
    Saved/Golmok/spike/csv/*.csv fill the golmok-perf command when perf_markdown is empty."""
    spike_dir = os.path.join(_saved_dir(), "Golmok", "spike")
    labels = sorted(
        os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(spike_dir, "csv", "*.csv"))
    )
    text = _pure.report_template(tags, presets, perf_markdown, csv_labels=labels)
    os.makedirs(spike_dir, exist_ok=True)
    with open(os.path.join(spike_dir, "report_template.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    unreal.log(text)
    return text
