"""unreal/.../golmok/spike_runner.py on the fake unreal (design section 5-5).

The PIE state machines are driven with fake_unreal.tick (fake clock on spike_runner._now, delayed screenshot
and CSV files), so every wait is checked in seconds, not ticks; the attended editor path is checked through
viewpoints.capture's on_done chain.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

import fake_unreal
import golmok.spike_runner as sr
import golmok.viewpoints as viewpoints
import pytest
from fake_unreal import DEFAULT_LEVEL
from golmok import _pure as pure

LEVEL_NAME = "L_ZoneTest"
L_SPIKE = "/Game/Golmok/Maps/L_Spike_"
PLAY_KINDS = ("begin_play", "end_play", "console", "set_visual_visible", "play_settings", "quit_editor")


@pytest.fixture
def fake(monkeypatch, tmp_path):
    return fake_unreal.install(monkeypatch, tmp_path)


@pytest.fixture
def unreal(fake):
    return fake.module


def _save_viewpoints(fake, names):
    """Write Config/Golmok/Viewpoints/L_ZoneTest.json the way viewpoints.save does; returns the data."""
    store = Path(fake.config_dir) / "Golmok" / "Viewpoints" / f"{LEVEL_NAME}.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    data = {
        name: {"location": [100.0 * i, -200.0, 150.0], "rotation": [0.0, -10.0, 90.0 + i]}
        for i, name in enumerate(names)
    }
    store.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    return data


def _write_walk(fake, name="walk_01", length_s=5.0):
    folder = Path(fake.saved_dir) / "Golmok" / "Paths"
    folder.mkdir(parents=True, exist_ok=True)
    walk = {
        "version": 1,
        "name": name,
        "samples": [
            {"t": 0.0, "p": [0.0, 0.0, 0.0], "r": [0.0, 0.0, 0.0]},
            {"t": length_s, "p": [100.0, 0.0, 0.0], "r": [0.0, 90.0, 0.0]},
        ],
    }
    path = folder / f"{name}.json"
    path.write_text(json.dumps(walk), encoding="utf-8")
    return path


def _play_calls(fake):
    return [c for c in fake.calls if c[0] in PLAY_KINDS]


def _shot_command(fake, tag, preset, name):
    """The explicit-size HighResShot the PIE capture sends (stem with "/" so FParse keeps the backslash-free
    quoted path; the engine appends the 00000 counter)."""
    stem = os.path.splitext(_shot(fake, tag, preset, name))[0].replace("\\", "/")
    return f'HighResShot 2560x1440 filename="{stem}"'


def _pie_tag_calls(fake, tag, presets, names, zone_id="z_x"):
    """The play-relevant records of one tag's PIE session (design D11; F1: explicit 2560x1440, no window)."""
    out = [
        ("set_visual_visible", zone_id, tag in ("a", "ac")),  # LAYERS (editor level)
        ("begin_play",),
        ("console", "golmok.hud 0"),
        ("set_visual_visible", zone_id, tag in ("a", "ac")),  # LAYERS_PIE
    ]
    for preset in presets:
        out.append(("console", f"golmok.tod {preset}"))
        for name in names:
            out += [
                ("console", f"golmok.path play vp_{name}"),
                ("console", _shot_command(fake, tag, preset, name)),
                ("console", "golmok.path stopplay"),
            ]
    out.append(("end_play",))
    return out


def _shot(fake, tag, preset, name):
    return os.path.normpath(pure.screenshot_path(fake.saved_dir, tag, preset, name))


def _run(fake, machine, max_ticks=5000, dt=0.1):
    """Tick until the state machine is done; returns the fake clock at that moment (seconds)."""
    for _ in range(max_ticks // 10):
        fake_unreal.tick(fake, 10, dt)
        if machine.done:
            return fake.clock
    raise AssertionError(f"not done after {max_ticks} ticks (state {machine.state})")


# ---- viewpoints, window, layers, layer levels ------------------------------------------------------------


def test_prepare_reports_missing(fake, unreal):
    _save_viewpoints(fake, ["far_01", "far_02", "mid_01", "near_01"])
    missing = sr.prepare()
    assert missing == ["far_03", "mid_02", "mid_03", "mid_04", "near_02", "near_03"]
    assert fake.logs[-1] == (
        "log",
        "spike_runner: viewpoints L_ZoneTest: 4 saved, "
        "missing=['far_03', 'mid_02', 'mid_03', 'mid_04', 'near_02', 'near_03']",
    )
    assert sr.prepare(level="/Game/Golmok/Maps/L_Other") == sorted(pure.VIEWPOINT_NAMES)
    assert fake.logs[-1][1].startswith("spike_runner: viewpoints L_Other: 0 saved, missing=[")
    assert sr.prepare(names=("far_01", "mid_01")) == [] and fake.logs[-1][1].endswith("4 saved, missing=[]")
    with pytest.raises(ValueError):
        sr.prepare(names=("far 01",))
    assert fake.calls == []


def test_configure_pie_window(fake, unreal, monkeypatch):
    assert sr.configure_pie_window() == "LevelEditorPlaySettings"
    assert fake.calls_of("play_settings") == [("play_settings", 1280, 720)]
    assert fake.play_settings.last_executed_play_mode_type == unreal.PlayModeType.PLAY_MODE_IN_EDITOR_FLOATING
    assert fake.logs[-1] == ("log", "spike_runner: PIE window 1280x720 x2 (LevelEditorPlaySettings)")
    assert not fake.logged("warning")
    assert sr.configure_pie_window((640, 360)) == "LevelEditorPlaySettings"
    assert fake.calls_of("play_settings") == [("play_settings", 640, 360)]  # consecutive sets collapse
    # the play-mode enum member missing: the size stays set, only the mode is left to the tester (#21)
    monkeypatch.delattr(unreal.PlayModeType, "PLAY_MODE_IN_EDITOR_FLOATING")
    fake.play_settings.last_executed_play_mode_type = None
    assert sr.configure_pie_window((800, 450)) == "LevelEditorPlaySettings"
    assert fake.calls_of("play_settings") == [("play_settings", 800, 450)]
    assert fake.play_settings.last_executed_play_mode_type is None
    assert fake.logged("warning") == [
        "spike_runner: WARNING PIE play mode: set 'New Editor Window (PIE)' by hand (runbook #21);"
        " unreal.PlayModeType.PLAY_MODE_IN_EDITOR_FLOATING not exposed"
    ]
    assert fake.logs[-1] == ("log", "spike_runner: PIE window 800x450 x2 (LevelEditorPlaySettings)")
    monkeypatch.delattr(unreal, "LevelEditorPlaySettings")
    how = sr.configure_pie_window()
    assert how == sr.MANUAL_WINDOW_HOW and how.startswith("manual: Editor Preferences") and "#21" in how
    assert fake.calls_of("play_settings") == [("play_settings", 800, 450)]  # nothing new recorded
    warning, done = fake.logs[-2:]
    assert warning[0] == "warning" and warning[1].startswith(
        "spike_runner: WARNING PIE window: manual: Editor Preferences > Level Editor > Play > New Window Size"
        " (runbook #21)"
    )
    assert done == ("log", f"spike_runner: PIE window 1280x720 x2 ({sr.MANUAL_WINDOW_HOW})")


def test_apply_layers_editor_and_pie(fake, unreal):
    fake.add_actor("GolmokZone", "Zone_x", zone_id="z_x")
    fake.add_actor(unreal.Actor, "Spike_b_lcc")
    fake.add_actor(unreal.Actor, "Spike_c_tiles")
    fake.add_actor(unreal.Actor, "Other")
    table = {
        "a": (True, False, False),
        "b": (False, True, False),
        "c": (False, False, True),
        "ac": (True, False, True),
    }
    for tag, (zone, b, c) in table.items():
        fake.calls.clear()
        state = sr.apply_layers(tag)
        assert state == {"zone_visual": zone, "spike_b": b, "spike_c": c, "actors": 3}
        assert fake.calls == [
            ("set_visual_visible", "z_x", zone),
            ("hidden_in_game", "Spike_b_lcc", not b),
            ("hidden_in_editor", "Spike_b_lcc", not b),
            ("hidden_in_game", "Spike_c_tiles", not c),
            ("hidden_in_editor", "Spike_c_tiles", not c),
        ]
        assert fake.logs[-1] == (
            "log",
            f"spike_runner: layers tag={tag} zone_visual={zone} Spike_b={b} Spike_c={c} (actors 3, editor)",
        )
    fake.level_editor.editor_request_begin_play()
    world = fake.editor_subsystem.get_game_world()
    fake.calls.clear()
    assert sr.apply_layers("ac", world)["actors"] == 3
    assert fake.calls == [  # PIE: no editor-only hiding
        ("set_visual_visible", "z_x", True),
        ("hidden_in_game", "Spike_b_lcc", True),
        ("hidden_in_game", "Spike_c_tiles", False),
    ]
    assert fake.logs[-1][1].endswith("(actors 3, pie)")
    with pytest.raises(ValueError):
        sr.apply_layers("d")

    class Plugin:  # a plugin actor without the hidden setters (runbook #19)
        props: dict = {}

        def get_actor_label(self):
            return "Spike_c_cesium"

        def set_actor_hidden_in_game(self, hidden):
            raise RuntimeError("not exposed")

        def set_editor_property(self, name, value):
            self.props[name] = value

    plugin = Plugin()
    fake.actors.append(plugin)
    assert sr.apply_layers("c")["actors"] == 4
    assert plugin.props == {"hidden": False}
    assert any("runbook #19" in text and "Spike_c_cesium" in text for _, text in fake.logs)


def test_save_layer_levels(fake, unreal):
    zone = fake.add_actor("GolmokZone", "Zone_x", zone_id="z_x")
    fake.add_actor(unreal.Actor, "Spike_b_lcc")
    assert sr.save_layer_levels(tags=("b",)) == [f"{L_SPIKE}b"]
    kinds = ("duplicate_asset", "delete_asset", "load_level", "set_visual_visible", "hidden_in_game",
             "hidden_in_editor", "save_current_level")  # fmt: skip
    assert [c for c in fake.calls if c[0] in kinds] == [
        ("duplicate_asset", DEFAULT_LEVEL, f"{L_SPIKE}b"),
        ("load_level", f"{L_SPIKE}b"),
        ("set_visual_visible", "z_x", False),
        ("hidden_in_game", "Spike_b_lcc", False),
        ("hidden_in_editor", "Spike_b_lcc", False),
        ("save_current_level",),
        ("load_level", DEFAULT_LEVEL),
    ]
    copies = {a.label: a for a in fake.levels[f"{L_SPIKE}b"]}
    assert copies["Zone_x"].get_editor_property("auto_managed") is False
    assert zone.get_editor_property("auto_managed") is True and fake.current_level == DEFAULT_LEVEL
    assert ("log", f"spike_runner: layer level {L_SPIKE}b saved (tag b)") in fake.logs
    # default tags b, c, ac; an existing layer level is deleted before the duplicate
    fake.calls.clear()
    assert sr.save_layer_levels() == [f"{L_SPIKE}b", f"{L_SPIKE}c", f"{L_SPIKE}ac"]
    assert fake.calls[:2] == [
        ("delete_asset", f"{L_SPIKE}b"),
        ("duplicate_asset", DEFAULT_LEVEL, f"{L_SPIKE}b"),
    ]
    assert fake.calls[-1] == ("load_level", DEFAULT_LEVEL)
    ac = {a.label: a for a in fake.levels[f"{L_SPIKE}ac"]}
    assert ac["Zone_x"].get_editor_property("auto_managed") is True and ac["Spike_b_lcc"].hidden_in_game


# ---- PIE capture -------------------------------------------------------------------------------------------


def test_pie_capture_sequence_and_files(fake, unreal):
    fake.add_actor("GolmokZone", "Zone_x", zone_id="z_x")
    data = _save_viewpoints(fake, ["far_01", "mid_01"])
    presets, names = ("clear_noon", "golden_evening"), ("far_01", "mid_01")
    cap = sr.capture_all(tags=("a", "b"), presets=presets, names=names)
    assert isinstance(cap, sr._PieCapture) and len(fake.callbacks) == 1 and not cap.done
    seconds = _run(fake, cap)
    assert cap.done and fake.callbacks == {} and 30.0 < seconds < 60.0  # waits are seconds, not ticks
    n_calls = len(fake.calls)
    fake_unreal.tick(fake, 50)
    assert len(fake.calls) == n_calls  # a finished machine ignores further ticks
    # no play-settings write: editor_request_begin_play() plays in the level viewport whatever they say (F1)
    assert _play_calls(fake) == _pie_tag_calls(fake, "a", presets, names) + _pie_tag_calls(
        fake, "b", presets, names
    )
    # dwell paths: one per viewpoint, GolmokStatsMath layout, accepted by the (fake) C++ parser
    folder = Path(fake.saved_dir) / "Golmok" / "Paths"
    assert sorted(p.name for p in folder.iterdir()) == ["vp_far_01.json", "vp_mid_01.json"]
    for name in names:
        vp = data[name]
        text = (folder / f"vp_{name}.json").read_text("utf-8")
        assert text == pure.dwell_path_json(
            f"vp_{name}", LEVEL_NAME, vp["location"], vp["rotation"], created=cap.created
        )
        assert json.loads(text)["samples"][-1]["t"] == 600.0
    assert fake.logged("error") == [] and fake.playing is None
    # screenshots: 8 PNGs at the explicit 2560x1440 (not the 1014x550 level viewport x 2), in job order; the
    # engine's <name>00000.png counter file is renamed to <name>.png
    shots = [_shot(fake, t, p, n) for t, p, n in pure.capture_jobs(("a", "b"), presets, names)]
    assert cap.saved == shots and cap.missing == []
    for path in shots:
        assert pure.png_size(Path(path).read_bytes()[:24]) == (2560, 1440)
        assert not Path(pure.screenshot_fallback_path(path)).exists()
    captured = [t for k, t in fake.logs if t.startswith("spike_runner: captured ")]
    assert captured == [f"spike_runner: captured {path} (2560x1440)" for path in shots]
    pie = [t for k, t in fake.logs if t.startswith("spike_runner: PIE ")]
    assert pie == [
        "spike_runner: PIE begin tag=a",
        "spike_runner: PIE end tag=a",
        "spike_runner: PIE begin tag=b",
        "spike_runner: PIE end tag=b",
    ]
    root = os.path.join(os.path.normpath(fake.saved_dir), "Screenshots", "Golmok")
    assert fake.logs[-1] == ("log", f"spike_runner: done capture: 8 saved, 0 missing -> {root}")
    assert [t for k, t in fake.logs if t.startswith("spike_runner: layers")] == [
        "spike_runner: layers tag=a zone_visual=True Spike_b=False Spike_c=False (actors 1, editor)",
        "spike_runner: layers tag=a zone_visual=True Spike_b=False Spike_c=False (actors 1, pie)",
        "spike_runner: layers tag=b zone_visual=False Spike_b=True Spike_c=False (actors 1, editor)",
        "spike_runner: layers tag=b zone_visual=False Spike_b=True Spike_c=False (actors 1, pie)",
    ]
    assert not fake.logged("warning")


def test_pie_capture_removes_stale_counter_file(fake, unreal):
    """A <name>00000.png left by an aborted run is deleted before the HighResShot, so the engine writes
    00000 again (not 00001, which WAIT_FILE would never see)."""
    _save_viewpoints(fake, ["far_01", "mid_01"])
    presets, names = ("clear_noon", "golden_evening"), ("far_01", "mid_01")
    shots = [_shot(fake, t, p, n) for t, p, n in pure.capture_jobs(("a", "b"), presets, names)]
    for path in shots:
        stale = Path(pure.screenshot_fallback_path(path))
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_bytes(fake_unreal.png_bytes(4, 4))
    cap = sr.capture_all(tags=("a", "b"), presets=presets, names=names)
    fake_unreal.tick(fake, 5000)
    assert cap.done and cap.saved == shots and cap.missing == []
    for path in shots:
        assert pure.png_size(Path(path).read_bytes()[:24]) == (2560, 1440)
        assert not Path(pure.screenshot_fallback_path(path)).exists()
        assert not Path(f"{path[:-4]}00001.png").exists()
    assert not fake.logged("warning") and fake.logs[-1][1].startswith("spike_runner: done capture: 8 saved")


def test_pie_capture_warns_on_wrong_size(fake, unreal, monkeypatch):
    """The engine writes another size (e.g. SetResolution refused): kept, but flagged with a warning."""
    _save_viewpoints(fake, ["far_01"])
    real = unreal.SystemLibrary.execute_console_command

    def smaller(world_context_object, command, specific_player=None):
        return real(world_context_object, command.replace("2560x1440", "1280x720"), specific_player)

    monkeypatch.setattr(unreal.SystemLibrary, "execute_console_command", smaller)
    cap = sr.capture_all(tags=("a",), presets=("clear_noon",), names=("far_01",))
    _run(fake, cap)
    shot = _shot(fake, "a", "clear_noon", "far_01")
    assert cap.saved == [shot] and cap.missing == []
    assert f"spike_runner: captured {shot} (1280x720)" in fake.logged("log")
    assert fake.logged("warning") == [
        f"spike_runner: WARNING {shot}: 1280x720, expected 2560x1440 (runbook #35)"
    ]


def test_pie_capture_missing_file_continues(monkeypatch, tmp_path):
    fake = fake_unreal.install(monkeypatch, tmp_path, screenshot_delay_s=10_000)
    fake.add_actor("GolmokZone", "Zone_x", zone_id="z_x")
    _save_viewpoints(fake, ["far_01", "mid_01"])
    cap = sr.capture_all(tags=("a",), presets=("clear_noon",), names=("far_01", "mid_01"))
    seconds = _run(fake, cap)
    shots = [_shot(fake, "a", "clear_noon", n) for n in ("far_01", "mid_01")]
    root = os.path.join(os.path.normpath(fake.saved_dir), "Screenshots", "Golmok")
    assert cap.done and cap.saved == [] and cap.missing == shots
    assert fake.logged("warning") == [
        f"spike_runner: missing {shots[0]} (timeout)",
        f"spike_runner: missing {shots[1]} (timeout)",
        f"spike_runner: done capture: 0 saved, 2 missing -> {root}",
    ]
    assert _play_calls(fake) == _pie_tag_calls(fake, "a", ("clear_noon",), ("far_01", "mid_01"))
    assert 60.0 < seconds < 90.0  # two FILE_TIMEOUT_S waits, then the run ended by itself


def test_pie_capture_exception_finishes_cleanly(fake, unreal, monkeypatch):
    _save_viewpoints(fake, ["far_01"])

    def boom(world_context_object, command, specific_player=None):
        raise RuntimeError("no console")

    monkeypatch.setattr(unreal.SystemLibrary, "execute_console_command", boom)
    cap = sr.capture_all(tags=("a",), presets=("clear_noon",), names=("far_01",))
    fake_unreal.tick(fake, 100)
    assert cap.done and fake.callbacks == {} and not fake.pie
    assert fake.calls_of("begin_play") == [("begin_play",)] and fake.calls_of("end_play") == [("end_play",)]
    assert fake.logged("warning") == ["spike_runner: WARNING capture stopped in state HUD_OFF: no console"]
    assert fake.logs[-1] == ("log", "spike_runner: PIE end tag=a")
    fake_unreal.tick(fake, 10)  # finished machines ignore further ticks
    assert fake.calls_of("end_play") == [("end_play",)]


def test_pie_start_timeout(monkeypatch, tmp_path):
    fake = fake_unreal.install(monkeypatch, tmp_path, begin_play_starts_pie=False)
    _save_viewpoints(fake, ["far_01"])
    cap = sr.capture_all(tags=("a",), presets=("clear_noon",), names=("far_01",))
    fake_unreal.tick(fake, 590)
    assert not cap.done and cap.state == "WAIT_PIE"
    fake_unreal.tick(fake, 20)
    assert cap.done and fake.callbacks == {}
    assert fake.logged("warning") == ["spike_runner: WARNING PIE did not start within 60 s (runbook #16)"]
    assert fake.calls_of("end_play") == [] and fake.calls_of("console") == []


def test_pie_world_fallback(fake, unreal, monkeypatch):
    monkeypatch.setattr(fake.editor_subsystem, "get_game_world", lambda: None)
    fake.level_editor.editor_request_begin_play()
    assert sr._pie_world() is None  # no EditorLevelLibrary by default
    monkeypatch.setattr(
        unreal,
        "EditorLevelLibrary",
        SimpleNamespace(get_pie_worlds=lambda b: [fake.pie_world]),
        raising=False,
    )
    assert sr._pie_world() is fake.pie_world
    assert fake.logged("warning") == [
        "spike_runner: WARNING UnrealEditorSubsystem.get_game_world() is None; using"
        " EditorLevelLibrary.get_pie_worlds (deprecated, runbook #15)"
    ]
    fake.level_editor.editor_request_end_play()
    _save_viewpoints(fake, ["far_01"])
    cap = sr.capture_all(tags=("a",), presets=("clear_noon",), names=("far_01",))
    fake_unreal.tick(fake, 500)
    assert cap.done and cap.saved == [_shot(fake, "a", "clear_noon", "far_01")]


def test_pie_already_running_is_ended_first(monkeypatch, tmp_path):
    fake = fake_unreal.install(monkeypatch, tmp_path, pie=True)
    _save_viewpoints(fake, ["far_01"])
    cap = sr.capture_all(tags=("a",), presets=("clear_noon",), names=("far_01",))
    assert fake.calls_of("end_play") == [("end_play",)] and cap.state == "WAIT_END"
    assert fake.logged("warning") == [
        "spike_runner: WARNING PIE is already running; ending it before the first tag"
    ]
    fake_unreal.tick(fake, 500)
    assert cap.done and cap.saved == [_shot(fake, "a", "clear_noon", "far_01")]
    assert fake.calls_of("begin_play") == [("begin_play",)] and len(fake.calls_of("end_play")) == 2


# ---- unattended exit: quit_editor (V-03 finding #3) --------------------------------------------------------


def _quit_line(what):
    return f"spike_runner: {what} finished; quitting the editor (quit_editor=True)"


def test_capture_quit_editor_after_done(fake, unreal):
    _save_viewpoints(fake, ["far_01"])
    cap = sr.capture_all(tags=("a",), presets=("clear_noon",), names=("far_01",), quit_editor=True)
    _run(fake, cap)
    fake_unreal.tick(fake, 5)  # the quit runs on a later tick, once PIE has really ended
    assert fake.calls[-2:] == [("end_play",), ("quit_editor",)] and fake.calls_of("quit_editor") == [
        ("quit_editor",)
    ]
    texts = fake.logged()
    done = texts.index(f"spike_runner: done capture: 1 saved, 0 missing -> {cap.root}")
    assert texts.index(_quit_line("capture")) > done and fake.callbacks == {}
    fake_unreal.tick(fake, 50)
    assert fake.calls_of("quit_editor") == [("quit_editor",)]  # once


def test_quit_waits_for_pie_to_end(fake, unreal, monkeypatch):
    """end_play is asynchronous: the quit waits until PIE is gone (or QUIT_WAIT_S), never in _finish."""
    _save_viewpoints(fake, ["far_01"])
    cap = sr.capture_all(tags=("a",), presets=("clear_noon",), names=("far_01",), quit_editor=True)
    fake_unreal.tick(fake, 45)  # in PIE, after the warm-up
    assert fake.pie and not cap.done
    monkeypatch.setattr(
        fake.level_editor, "editor_request_end_play", lambda: fake.calls.append(("end_play",))
    )
    cap._finish("stopped by hand", warn=True)  # PIE keeps running (a stuck end_play)
    assert cap.done and fake.calls_of("quit_editor") == [] and len(fake.callbacks) == 1
    fake_unreal.tick(fake, 10)
    assert fake.calls_of("quit_editor") == []
    fake_unreal.tick(fake, int(sr.QUIT_WAIT_S / 0.1) + 5)
    assert fake.calls_of("quit_editor") == [("quit_editor",)] and fake.callbacks == {}


def test_no_quit_by_default(fake, unreal):
    _save_viewpoints(fake, ["far_01"])
    _write_walk(fake, "walk_01", length_s=5.0)
    cap = sr.capture_all(tags=("a",), presets=("clear_noon",), names=("far_01",))
    _run(fake, cap)
    perf = sr.perf_all(paths=("walk_01",), tags=("a",))
    _run(fake, perf)
    fake_unreal.tick(fake, 100)
    assert fake.calls_of("quit_editor") == [] and fake.callbacks == {}
    assert not any("quitting the editor" in t for t in fake.logged())


def test_quit_after_pie_start_timeout(monkeypatch, tmp_path):
    fake = fake_unreal.install(monkeypatch, tmp_path, begin_play_starts_pie=False)
    _save_viewpoints(fake, ["far_01"])
    cap = sr.capture_all(tags=("a",), presets=("clear_noon",), names=("far_01",), quit_editor=True)
    fake_unreal.tick(fake, 620)
    assert cap.done and fake.calls_of("quit_editor") == [("quit_editor",)] and fake.callbacks == {}
    assert fake.logged("warning") == ["spike_runner: WARNING PIE did not start within 60 s (runbook #16)"]
    assert fake.logs[-1] == ("log", _quit_line("capture"))


def test_perf_quit_editor(fake, unreal):
    _write_walk(fake, "walk_01", length_s=5.0)
    perf = sr.perf_all(paths=("walk_01",), tags=("a",), quit_editor=True)
    _run(fake, perf)
    fake_unreal.tick(fake, 5)
    assert fake.calls[-2:] == [("end_play",), ("quit_editor",)]
    assert fake.logs[-1] == ("log", _quit_line("perf (PIE, reference only)"))


def test_quit_editor_fallbacks(fake, unreal, monkeypatch):
    _save_viewpoints(fake, ["far_01"])
    monkeypatch.delattr(unreal.SystemLibrary, "quit_editor")
    cap = sr.capture_all(tags=("a",), presets=("clear_noon",), names=("far_01",), quit_editor=True)
    _run(fake, cap)
    fake_unreal.tick(fake, 5)
    assert fake.calls[-2:] == [("end_play",), ("console", "QUIT_EDITOR")]  # console fallback (pc-setup.md)
    assert fake.logged("warning")[-1] == (
        "spike_runner: WARNING unreal.SystemLibrary.quit_editor unavailable;"
        " sending QUIT_EDITOR (runbook #34)"
    )
    # neither: a warning, no exception, the machine is gone
    monkeypatch.delattr(unreal.SystemLibrary, "execute_console_command")
    fake.calls.clear()
    cap = sr.capture_all(tags=("a",), presets=("clear_noon",), names=("far_01",), quit_editor=True)
    fake_unreal.tick(fake, 100)
    assert cap.done and fake.callbacks == {} and fake.calls_of("quit_editor") == []
    assert fake.logged("warning")[-1].startswith(
        "spike_runner: WARNING could not quit the editor: close it by hand (runbook #34)"
    )


def test_quit_editor_needs_pie_mode(fake, unreal):
    _save_viewpoints(fake, ["far_01"])
    with pytest.raises(ValueError, match="quit_editor needs mode='pie'"):
        sr.capture_all(mode="editor", quit_editor=True)
    assert fake.calls == [] and fake.callbacks == {}


def test_quit_editor_on_setup_error(fake, unreal):
    """A validation error before the machine exists still ends an unattended editor (then re-raises)."""
    with pytest.raises(RuntimeError, match="no saved viewpoints"):
        sr.capture_all(quit_editor=True)
    assert fake.calls == [("quit_editor",)]
    assert fake.logged("warning")[-1].startswith("spike_runner: WARNING capture could not start")
    assert fake.logs[-1] == ("log", _quit_line("capture (setup failed)"))
    fake.calls.clear()
    with pytest.raises(RuntimeError, match="record it first"):
        sr.perf_all(paths=("walk_01",), quit_editor=True)
    assert fake.calls == [("quit_editor",)]
    with pytest.raises(RuntimeError):
        sr.perf_all(paths=("walk_01",))
    assert fake.calls == [("quit_editor",)]  # default: no quit


def test_capture_all_validates_and_resolves_names(fake, unreal):
    with pytest.raises(RuntimeError, match="no saved viewpoints"):
        sr.capture_all()
    _save_viewpoints(fake, ["far_01", "mid_01"])
    with pytest.raises(ValueError):
        sr.capture_all(tags=("d",))
    with pytest.raises(ValueError):
        sr.capture_all(presets=("clear noon",))
    with pytest.raises(ValueError):
        sr.capture_all(mode="game")
    with pytest.raises(RuntimeError):
        sr.capture_all(names=("near_03",))
    assert fake.calls == [] and fake.callbacks == {} and not fake.logged("warning")
    cap = sr.capture_all(tags=("a",), presets=("clear_noon",))  # names None: the saved subset, with a warning
    assert cap.jobs == [("a", "clear_noon", "far_01"), ("a", "clear_noon", "mid_01")]
    assert fake.logged("warning") == [
        "spike_runner: WARNING viewpoints: far_02, far_03, mid_02, mid_03, mid_04, near_01, near_02, near_03"
        " not saved (viewpoints.save); capturing ['far_01', 'mid_01']"
    ]
    cap._finish("")


# ---- attended editor path ----------------------------------------------------------------------------------


def test_editor_capture_chains_tags(fake, unreal, monkeypatch):
    _save_viewpoints(fake, pure.VIEWPOINT_NAMES)
    calls = []

    def fake_capture(tag, names=None, presets=None, game_view=True, on_done=None):
        calls.append((tag, tuple(names), tuple(presets)))
        on_done([f"{tag}.png"], [])
        return SimpleNamespace(tag=tag)

    monkeypatch.setattr(viewpoints, "capture", fake_capture)
    cap = sr.capture_all(mode="editor")
    assert [c[0] for c in calls] == ["a", "b", "c", "ac"]
    assert all(c[1:] == (pure.VIEWPOINT_NAMES, pure.DEFAULT_PRESETS) for c in calls)
    assert cap.done and cap.saved == ["a.png", "b.png", "c.png", "ac.png"] and cap.missing == []
    assert [c.tag for c in cap.captures] == ["a", "b", "c", "ac"]
    layers = [t for _, t in fake.logs if t.startswith("spike_runner: layers")]
    assert [line.split()[2] for line in layers] == ["tag=a", "tag=b", "tag=c", "tag=ac"]
    assert all(line.endswith("(actors 0, editor)") for line in layers)
    assert fake.logs[-1][1].startswith("spike_runner: done capture (editor): 4 saved, 0 missing -> ")
    assert fake.callbacks == {}


def test_viewpoints_on_done_is_optional(fake, unreal):
    _save_viewpoints(fake, ["far_01"])
    plain = viewpoints.capture("a", names=["far_01"], presets=[None])
    assert plain.on_done is None
    fake_unreal.tick(fake, 60)
    assert plain.saved == [_shot(fake, "a", None, "far_01")]
    seen = []
    chained = viewpoints.capture(
        "b", names=["far_01"], presets=[None], on_done=lambda s, m: seen.append((s, m))
    )
    fake_unreal.tick(fake, 60)
    assert seen == [([_shot(fake, "b", None, "far_01")], [])] and chained.on_done is not None
    assert fake.callbacks == {}


# ---- PIE perf, -game scripts -------------------------------------------------------------------------------


def test_pie_perf_waits_for_csv(fake, unreal):
    with pytest.raises(RuntimeError, match="record it first: golmok.path record walk_01"):
        sr.perf_all(paths=("walk_01",), tags=("a",))
    _write_walk(fake, "walk_01", length_s=5.0)
    perf = sr.perf_all(paths=("walk_01",), tags=("a",), presets=("clear_noon",))
    assert isinstance(perf, sr._PiePerf) and perf.lengths == {"walk_01": 5.0}
    fake_unreal.tick(fake, 63)  # BEGIN_PIE, 3 s warm-up, hud, layers, tod (3 s): the path just started
    assert perf.state == "WAIT_CSV" and perf.saved == [] and not perf.done
    assert fake.calls_of("console") == [
        ("console", "golmok.hud 0"),
        ("console", "golmok.tod clear_noon"),
        ("console", "golmok.path play walk_01 --csv"),
    ]
    assert not fake.logged("warning")
    fake_unreal.tick(fake, 10)  # csv_delay_s 0.5 -> the CSV appears
    csv = os.path.normpath(os.path.join(fake.saved_dir, "Profiling", "CSV", "Profile(1).csv"))
    assert perf.saved == [csv]
    assert (
        "log",
        f'spike_runner: csv {csv} -> golmok-perf "{csv}" --label a_clear_noon_walk_01 --markdown',
    ) in fake.logs
    fake_unreal.tick(fake, 400)
    assert perf.done and fake.calls_of("end_play") == [("end_play",)] and fake.callbacks == {}
    root = os.path.join(os.path.normpath(fake.saved_dir), "Profiling", "CSV")
    assert fake.logs[-1] == (
        "log",
        f"spike_runner: done perf (PIE, reference only): 1 saved, 0 missing -> {root}",
    )
    assert fake.calls_of("play_settings") == []  # no window setup for the reference measurement


def test_pie_perf_csv_timeout(monkeypatch, tmp_path):
    fake = fake_unreal.install(monkeypatch, tmp_path, csv_delay_s=10_000)
    _write_walk(fake, "walk_01", length_s=5.0)
    perf = sr.perf_all(paths=("walk_01",), tags=("a",), presets=("clear_noon",))
    fake_unreal.tick(fake, 600)  # 3 + 3 + (5 + 60) s
    assert not perf.done
    fake_unreal.tick(fake, 200)
    assert perf.done and perf.saved == [] and perf.missing == ["a_clear_noon_walk_01"]
    pattern = os.path.normpath(os.path.join(fake.saved_dir, "Profiling", "CSV", "Profile*.csv"))
    assert fake.logged("warning") == [
        f"spike_runner: missing {pattern} (timeout, a_clear_noon_walk_01)",
        f"spike_runner: done perf (PIE, reference only): 0 saved, 1 missing -> {os.path.dirname(pattern)}",
    ]


def test_game_scripts_written(fake, unreal, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", "C:/Users/me/AppData/Local")
    with pytest.raises(RuntimeError, match="record it first"):
        sr.game_scripts(paths=("walk_01",))
    walk = _write_walk(fake, "walk_01")
    script = sr.game_scripts(paths=("walk_01",), tags=("a", "b"), presets=("clear_noon",))
    saved = os.path.normpath(fake.saved_dir)
    assert script == os.path.join(saved, "Golmok", "spike", "run_game_perf.ps1")
    raw = Path(script).read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") and b"\r\n" in raw and raw.replace(b"\r\n", b"").count(b"\n") == 0
    exe = os.path.join(os.path.normpath(str(fake.root / "Engine")), "Binaries", "Win64", "UnrealEditor.exe")
    assert sr._editor_exe() == exe and sr._uproject() == os.path.normpath(str(fake.root / "Golmok.uproject"))
    runs = []
    for tag, level in (("a", DEFAULT_LEVEL), ("b", f"{L_SPIKE}b")):
        label = f"{tag}_clear_noon_walk_01"
        argv = pure.game_command_line(
            exe, sr._uproject(), level, walk="walk_01", preset="clear_noon",
            log_path=os.path.join(saved, "Golmok", "spike", f"game_{label}.log"),
        )  # fmt: skip
        runs.append({"label": label, "argv": argv})
    expected = pure.powershell_script(
        runs,
        [os.path.normpath(str(walk))],
        pure.saved_dir_candidates(saved, "C:/Users/me/AppData/Local"),
        os.path.join(saved, "Golmok", "spike", "csv"),
        900,
    )
    body = raw.decode("utf-8-sig").replace("\r\n", "\n")
    assert body == expected
    assert body.count("\nInvoke-GolmokRun ") == 2 and "-csvCaptureFrames" not in body
    assert "UnrealEngine\\5.8\\Saved\\Profiling\\CSV" in body and f"{L_SPIKE}b" in body
    assert fake.logs[-1] == ("log", f"spike_runner: -game script -> {script} (2 runs)")
    # engine folder: Paths.engine_dir -> UE_ROOT -> error (runbook #27)
    monkeypatch.delattr(unreal.Paths, "engine_dir")
    monkeypatch.delenv("UE_ROOT", raising=False)
    with pytest.raises(RuntimeError, match="runbook #27"):
        sr.game_scripts(paths=("walk_01",), tags=("a",))
    monkeypatch.setenv("UE_ROOT", "D:/UE_5.8")
    assert sr._editor_exe() == os.path.join(
        os.path.normpath("D:/UE_5.8"), "Binaries", "Win64", "UnrealEditor.exe"
    )
    assert (
        fake.logs[-1][1]
        == "spike_runner: WARNING unreal.Paths.engine_dir unavailable; using $env:UE_ROOT (runbook #27)"
    )
    assert sr.game_scripts(paths=("walk_01",), tags=("a", "b", "c", "ac"), presets=("clear_noon", "night"))
    assert fake.logs[-1][1].endswith("(8 runs)")


def test_game_scripts_label_suffix(fake, unreal, monkeypatch):
    """A second resolution / DLSS run must not overwrite the first run's CSV and log (L4-03)."""
    monkeypatch.setenv("LOCALAPPDATA", "C:/Users/me/AppData/Local")
    _write_walk(fake, "walk_01")

    def body(**kw):
        path = sr.game_scripts(paths=("walk_01",), tags=("a",), **kw)
        return Path(path).read_text("utf-8-sig")

    text = body()  # 1080p default: unchanged names
    assert "game_a_clear_noon_walk_01.log" in text
    assert "a_clear_noon_walk_01.csv" in text and "_1080p" not in text
    text = body(res=(2560, 1440))
    assert "game_a_clear_noon_walk_01_1440p.log" in text
    assert "a_clear_noon_walk_01_1440p.csv" in text and "game_a_clear_noon_walk_01.log" not in text
    assert "--label a_clear_noon_walk_01_1440p" in text
    text = body(res=(2560, 1440), label_suffix="1440p_dlss")
    assert "a_clear_noon_walk_01_1440p_dlss.csv" in text
    assert "game_a_clear_noon_walk_01_1440p_dlss.log" in text
    text = body(label_suffix="dlss")
    assert "a_clear_noon_walk_01_dlss.csv" in text
    assert "a_clear_noon_walk_01.csv" in body(res=(2560, 1440), label_suffix="")  # explicit: no suffix
    with pytest.raises(ValueError):
        body(label_suffix="bad name")


# ---- contact sheet, report ---------------------------------------------------------------------------------


def test_contact_sheet_and_report_written(fake, unreal, tmp_path):
    root = Path(fake.saved_dir) / "Screenshots" / "Golmok"
    shot = root / "a" / "clear_noon" / "far_01.png"
    shot.parent.mkdir(parents=True)
    shot.write_bytes(fake_unreal.png_bytes(2560, 1440))
    path = sr.contact_sheet()
    # os.path.join of the UE-style "/" saved dir gives mixed separators on Windows: compare normalized.
    assert os.path.normpath(path) == os.path.normpath(root / "contact_sheet.html")
    assert fake.logs[-1] == (
        "log",
        f"spike_runner: contact sheet -> {path}",
    )
    html = Path(path).read_text("utf-8")
    assert html.count("<table>") == len(pure.DEFAULT_PRESETS) and html.count("<img ") == 1
    assert 'href="a/clear_noon/far_01.png"' in html and "\\" not in html
    assert (
        html.count('class="missing"')
        == len(pure.TAGS) * len(pure.DEFAULT_PRESETS) * len(pure.VIEWPOINT_NAMES) - 1
    )
    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "far_01.jpg").write_bytes(b"\xff\xd8")
    (root / "ref").mkdir()
    (root / "ref" / "mid_01.png").write_bytes(fake_unreal.png_bytes(4, 4))
    html = Path(sr.contact_sheet(tags=("a",), presets=("clear_noon",), photos_dir=str(photos))).read_text(
        "utf-8"
    )
    assert "<th>photo</th>" in html and f'href="{pure.file_uri(str(photos / "far_01.jpg"))}"' in html
    html = Path(
        sr.contact_sheet(tags=("a",), presets=("clear_noon",), photos_dir=str(root / "ref"))
    ).read_text("utf-8")
    assert 'href="ref/mid_01.png"' in html  # a photo under the screenshot root is linked relatively
    text = sr.report_template()
    report = Path(fake.saved_dir) / "Golmok" / "spike" / "report_template.md"
    assert report.read_text("utf-8") == text and fake.logs[-1] == ("log", text)
    assert "| 항목 | (a) 메시 Nanite+Lumen | (b) Cesium splat | (c) XGRIDS LCC | (a+c) 하이브리드 |" in text
    assert pure.PERF_HEADER in text and "### 컨택트 시트" in text and '"<csv>"' in text
    csv_dir = report.parent / "csv"
    csv_dir.mkdir()
    (csv_dir / "a_clear_noon_walk_01.csv").write_text("FrameTime\n", encoding="utf-8")
    text = sr.report_template(perf_markdown="")
    assert '"Saved/Golmok/spike/csv/a_clear_noon_walk_01.csv" --label a_clear_noon_walk_01' in text
    text = sr.report_template(
        perf_markdown="| a_clear_noon_walk_01 | 9000 | 150.0 | 90.0 | 6.6 | 12.0 | 3.0 | 4.0 | 5.5 |\n"
    )
    assert "| a_clear_noon_walk_01 | 9000 |" in text and "golmok-perf" not in text


# ---- runbook drift: pc-verify-wp06.md §8/§9 expected blocks ----------------------------------------------

RUNBOOK_WP06 = Path(__file__).resolve().parents[2] / "docs" / "runbooks" / "pc-verify-wp06.md"


def _runbook_block(marker):
    """The spike_runner lines of the first fenced block of pc-verify-wp06.md that contains `marker`."""
    blocks, current = [], None
    for line in RUNBOOK_WP06.read_text("utf-8").splitlines():
        if line.strip().startswith("```"):
            if current is None:
                current = []
            else:
                blocks.append(current)
                current = None
        elif current is not None:
            current.append(line.strip())
    block = next(b for b in blocks if any(marker in line for line in b))
    return [line for line in block if line.startswith("spike_runner:")]


def _spike_lines(fake):
    return [text for _, text in fake.logs if text.startswith("spike_runner:")]


def test_layer_level_log_block_matches_runbook(fake, unreal):
    fake.add_actor("GolmokZone", "Zone_z_synthetic_scan_001", zone_id="z_synthetic_scan_001")
    fake.logs.clear()
    sr.save_layer_levels()
    assert _spike_lines(fake) == _runbook_block("spike_runner: layer level /Game/Golmok/Maps/L_Spike_b saved")


def test_pie_perf_log_block_matches_runbook(fake, unreal):
    fake.add_actor("GolmokZone", "Zone_z_synthetic_scan_001", zone_id="z_synthetic_scan_001")
    _write_walk(fake, "walk_01", length_s=5.0)
    fake.logs.clear()
    perf = sr.perf_all(paths=("walk_01",), tags=("a",))
    _run(fake, perf)
    saved = os.path.normpath(fake.saved_dir)
    patterns = []
    for line in _runbook_block("spike_runner: done perf (PIE, reference only)"):
        line = line.replace("\\", os.sep).replace(os.path.join("<Project>", "Saved"), saved)
        patterns.append(re.escape(line).replace(re.escape("Profile(…)"), r"Profile\(\d+\)"))
    lines = _spike_lines(fake)
    assert len(lines) == len(patterns), "\n".join(lines)
    for line, pattern in zip(lines, patterns, strict=True):
        assert re.fullmatch(pattern, line), (line, pattern)
