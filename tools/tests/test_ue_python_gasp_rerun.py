"""WP-19a-2 (review R76 T1, T2, T4): add-gasp re-runs, recovery, the acquired-GASP digest and package names.

golmok.gasp_import on fake_unreal (one fake registry plays both the GASP project and Golmok; tests
re-register the GASP packages when a scenario needs the GASP project again). No GASP content is used:
package names and ini lines are synthetic stand-ins.

T1  a -Force run over an installed /Game/GASP and leftovers of an earlier run at the Migrate paths stop
    *before* anything is copied, naming what to delete (never the mannequin pack); relocate refuses an empty
    migration and keeps the previous manifest; the GASP ini text is parsed before anything moves;
    local_files rewrites only the DDCvar / tag files.
T2  migrate hashes the GASP project's own files (source_digest, original /Game paths) before and after the
    copy; the manifest carries it and compare_expected pins source_digest + package_count + engine_version,
    so two installs with different local conflicts agree.
T4  /Game dependencies with '-' or non-ASCII names stay in the closure; a /Game name UE cannot hold fails the
    migrate before copying; relocation_plan no longer validates the pre-existing packages.
"""

from __future__ import annotations

import importlib
import json
import shutil
from pathlib import Path

import fake_unreal
import pytest
from test_ue_python_gasp_import import (
    ABP,
    ANIMATION,
    BPI,
    CLOSURE,
    EXPECTED,
    MANNY_OURS,
    UEFN,
    _content,
    synthetic_engine_ini,
    synthetic_tags_ini,
)

pure = importlib.import_module("golmok.gasp_pure")

DB = "/Game/Blueprints/Data/DB"
A1 = "/Game/Characters/UEFN_Mannequin/Anims/A1"
SOURCE = (ABP, BPI, UEFN, DB, A1)


@pytest.fixture
def setup(monkeypatch, tmp_path):
    deps = {ABP: [BPI, DB, "/Script/PoseSearch"], DB: [UEFN, A1]}
    fake = fake_unreal.install(monkeypatch, tmp_path, dependencies=deps)
    module = importlib.import_module("golmok.gasp_import")
    content = Path(fake.content_dir)
    _content(content, [MANNY_OURS])  # the mannequin pack already in Golmok/Content/Characters
    gasp_project = tmp_path / "GASP_58"
    (gasp_project / "Config").mkdir(parents=True)
    (gasp_project / "Config/DefaultEngine.ini").write_text(synthetic_engine_ini(), encoding="utf-8")
    (gasp_project / "Config/DefaultGameplayTags.ini").write_text(synthetic_tags_ini(), encoding="utf-8")
    work = tmp_path / "work"
    work.mkdir()
    env = {
        "fake": fake,
        "module": module,
        "content": content,
        "gasp": gasp_project,
        "source": gasp_project / "Content",
        "local": tmp_path / "local",
        "tags": tmp_path / "Tags/GASP.ini",
        "work": work,
    }
    open_gasp_project(env)
    return env


def open_gasp_project(env, packages=SOURCE):
    """(Re-)register the GASP packages and their files in the GASP project's Content (bytes = a copy's)."""
    for package in packages:
        env["fake"].registry[package] = fake_unreal.FakeAsset(env["fake"], package)
    _content(env["source"], packages)


def job(env, step, **extra):
    base = {
        "migrate": {
            "closure": str(CLOSURE),
            "dest_content": str(env["content"]),
            "source_content": str(env["source"]),
            "history": str(env["work"] / "migrated-history.json"),
        },
        "relocate": {
            "migrate_report": str(env["work"] / "migrate.json"),
            "content_dir": str(env["content"]),
            "local_dir": str(env["local"]),
            "tags_ini": str(env["tags"]),
            "gasp_project": str(env["gasp"]),
        },
        "local_files": {
            "local_dir": str(env["local"]),
            "tags_ini": str(env["tags"]),
            "gasp_project": str(env["gasp"]),
        },
        "manifest": {
            "migrate_report": str(env["work"] / "migrate.json"),
            "content_dir": str(env["content"]),
            "local_dir": str(env["local"]),
            "gasp_project": str(env["gasp"]),
        },
        "verify": {
            "content_dir": str(env["content"]),
            "local_dir": str(env["local"]),
            "tags_ini": str(env["tags"]),
            "expected": str(EXPECTED),
            "git_status": str(env["work"] / "git-status.txt"),
        },
    }[step]
    return {"step": step, **base, **extra}


def run(env, step, monkeypatch=None, **extra) -> dict:
    """Runs one add-gasp step like the editor would (main(): the result file, never an exception)."""
    data = job(env, step, **extra)
    data["result"] = str(env["work"] / f"{step}.json")
    job_path = env["work"] / f"{step}-job.json"
    job_path.write_text(json.dumps(data), encoding="utf-8")
    patcher = monkeypatch or pytest.MonkeyPatch()
    patcher.setenv(env["module"].JOB_ENV, str(job_path))
    try:
        env["module"].main()
    finally:
        if monkeypatch is None:
            patcher.undo()
    return json.loads(Path(data["result"]).read_text(encoding="utf-8"))


def install(env) -> dict:
    migrated = run(env, "migrate")
    assert migrated["ok"], migrated
    relocated = run(env, "relocate")
    assert relocated["ok"] and relocated["exit"] == 0, relocated
    (env["work"] / "git-status.txt").write_text("", encoding="utf-8")
    return relocated


def manifest(env) -> dict:
    return json.loads((env["local"] / "gasp_manifest.json").read_text(encoding="utf-8"))


# ---- T1 ----------------------------------------------------------------------------------------------------


def test_force_rerun_over_an_installed_gasp_stops_before_copying(setup):
    install(setup)
    assert (setup["content"] / "GASP/Blueprints/SandboxCharacter_CMC_ABP.uasset").is_file()
    open_gasp_project(setup)  # the GASP project again (runbook A3 "fix closure.json, then -Force")
    report = run(setup, "migrate")
    assert not report["ok"] and report["exit"] == 1
    assert any("Content/GASP" in m for m in report["messages"]), report["messages"]
    assert len(setup["fake"].calls_of("migrate")) == 1  # the second run copied nothing
    assert not (setup["content"] / "Blueprints").exists()
    assert not (setup["content"] / "Characters/UEFN_Mannequin").exists()


def test_leftovers_of_an_earlier_run_stop_the_migrate_and_name_what_to_delete(setup):
    # An interrupted / old-runbook run left a full copy at the Migrate paths (same bytes as the GASP files).
    _content(setup["content"], SOURCE)
    report = run(setup, "migrate")
    assert not report["ok"] and report["exit"] == 1
    assert setup["fake"].calls_of("migrate") == []
    assert report["delete"] == ["Content/Blueprints", "Content/Characters/UEFN_Mannequin"]
    assert sorted(report["leftovers"]) == sorted(SOURCE)
    assert not any(
        "Characters/Mannequins" in m for m in report["messages"]
    )  # the mannequin pack is never listed
    assert (setup["content"] / "Characters/Mannequins/Meshes/SKM_Manny_Simple.uasset").is_file()


def test_leftovers_are_found_through_the_history_when_the_bytes_differ(setup):
    install(setup)
    history = json.loads((setup["work"] / "migrated-history.json").read_text(encoding="utf-8"))
    assert sorted(history["migrated"]) == sorted(SOURCE)
    # Content/GASP deleted by hand; a (resaved) leftover of the ABP sits at its Migrate path.
    shutil.rmtree(setup["content"] / "GASP")
    for key in [k for k in setup["fake"].registry if k.startswith("/Game/GASP/")]:
        del setup["fake"].registry[key]
    leftover = setup["content"] / "Blueprints/SandboxCharacter_CMC_ABP.uasset"
    leftover.parent.mkdir(parents=True)
    leftover.write_bytes(b"resaved")
    open_gasp_project(setup)
    report = run(setup, "migrate")
    assert not report["ok"] and report["leftovers"] == [ABP]
    assert report["delete"] == ["Content/Blueprints"]
    assert len(setup["fake"].calls_of("migrate")) == 1


def test_an_editor_that_dies_mid_copy_leaves_no_leftover_the_next_run_misses(setup, monkeypatch):
    """R78-1: the history is written before copying, so a partly written copy is a leftover."""
    original = fake_unreal.FakeAssetTools.migrate_packages
    dying = {}

    def dies_mid_copy(self, names, dest, options=None):
        names = [str(n) for n in names]
        original(self, names[:3], dest, options)
        dying["package"] = names[2]
        partial = Path(dest) / (names[2][len("/Game/") :] + ".uasset")
        partial.write_bytes(partial.read_bytes()[:3])  # the file being written when the editor died
        raise SystemExit("editor process died")  # no result file: add-gasp.ps1 stops

    monkeypatch.setattr(fake_unreal.FakeAssetTools, "migrate_packages", dies_mid_copy)
    with pytest.raises(SystemExit):
        run(setup, "migrate")
    monkeypatch.setattr(fake_unreal.FakeAssetTools, "migrate_packages", original)
    open_gasp_project(setup)
    second = run(setup, "migrate")
    assert not second["ok"] and dying["package"] in second["leftovers"]
    for rel in second["delete"]:  # the user deletes exactly what the message lists
        target = setup["content"] / rel[len("Content/") :]
        shutil.rmtree(target) if target.is_dir() else target.unlink()
    open_gasp_project(setup)
    third = run(setup, "migrate")
    assert third["ok"] and third["conflicts"] == [] and dying["package"] in third["migrated"]


def test_relocate_refuses_an_empty_migration_and_keeps_the_manifest(setup):
    setup["local"].mkdir()
    (setup["local"] / "gasp_manifest.json").write_text('{"sentinel": 1}\n', encoding="utf-8")
    report = {
        "ok": True,
        "exit": 0,
        "packages": list(SOURCE),
        "existing_before": sorted(SOURCE),
        "migrated": [],
        "engine_version": fake_unreal.ENGINE_VERSION,
    }
    (setup["work"] / "migrate.json").write_text(json.dumps(report), encoding="utf-8")
    result = run(setup, "relocate")
    assert not result["ok"] and result["exit"] == 1
    assert any("no migrated package" in m for m in result["messages"]), result["messages"]
    assert (setup["local"] / "gasp_manifest.json").read_text(encoding="utf-8") == '{"sentinel": 1}\n'
    # A failed migrate report is refused the same way.
    (setup["work"] / "migrate.json").write_text(json.dumps(dict(report, ok=False, migrated=[ABP])), "utf-8")
    assert not run(setup, "relocate")["ok"]
    assert setup["fake"].calls_of("rename_directory") == []


def test_gasp_ini_is_checked_before_copying_and_before_moving(setup):
    bad = '[/Script/Engine.DataDrivenConsoleVariableSettings]\n+CVarsArray=(Type=CVarString,Name="X")\n'
    engine = setup["gasp"] / "Config/DefaultEngine.ini"
    engine.write_text(bad, encoding="utf-8")
    refused = run(setup, "migrate")
    assert not refused["ok"] and setup["fake"].calls_of("migrate") == []  # nothing copied
    assert any("CVarsArray" in m for m in refused["messages"]), refused["messages"]
    engine.write_text(synthetic_engine_ini(26), encoding="utf-8")  # a wrong count stops it as well
    assert not run(setup, "migrate")["ok"] and setup["fake"].calls_of("migrate") == []
    # Broken between migrate and relocate: relocate moves nothing and writes no manifest.
    engine.write_text(synthetic_engine_ini(), encoding="utf-8")
    assert run(setup, "migrate")["ok"]
    engine.write_text(bad, encoding="utf-8")
    result = run(setup, "relocate")
    assert not result["ok"] and result["exit"] == 1
    assert setup["fake"].calls_of("rename_directory") == [] and ABP in setup["fake"].registry
    assert not (setup["local"] / "gasp_manifest.json").exists()
    # Fixed ini: relocate runs on the same migrate report; local_files alone rewrites DDCvars / tags.
    engine.write_text(synthetic_engine_ini(), encoding="utf-8")
    assert run(setup, "relocate")["ok"]
    (setup["local"] / "gasp_ddcvars.json").unlink()
    setup["tags"].unlink()
    before = manifest(setup)
    files = run(setup, "local_files")
    assert files["ok"] and files["ddcvars"] == 27 and files["tags"] == 39
    assert manifest(setup) == before  # nothing but the two local files
    good = (setup["local"] / "gasp_ddcvars.json").read_text("utf-8")
    # A project without the ini files never overwrites good local files with empty ones.
    (setup["gasp"] / "Config/DefaultGameplayTags.ini").unlink()
    kept = run(setup, "local_files")
    assert not kept["ok"] and "local files kept" in kept["messages"][0]
    assert (setup["local"] / "gasp_ddcvars.json").read_text("utf-8") == good


def test_byte_identical_mannequin_pack_file_is_never_a_leftover():
    pack = "/Game/Characters/Mannequins/Meshes/SK_Mannequin"
    pre = pure.migrate_preconditions([ABP, pack], {pack, ABP}, (), lambda p: True)
    assert pre["leftovers"] == [ABP] and pre["delete"] == ["Content/Blueprints"]
    assert pure.migrate_preconditions([pack], {pack}, {pack}, lambda p: False)["leftovers"] == [
        pack
    ]  # history


# ---- T2 ----------------------------------------------------------------------------------------------------


def test_source_digest_is_the_acquired_gasp_and_pins_expected(setup, tmp_path, monkeypatch):
    report = run(setup, "migrate")
    entries = pure.source_entries(setup["source"], SOURCE)
    assert report["source_digest"] == pure.aggregate_digest(entries)
    assert report["source_package_count"] == 5 and report["source_unchanged"] is True
    assert [e["path"] for e in entries][0] == "Blueprints/Data/DB"  # original /Game relative paths
    assert run(setup, "relocate")["ok"]
    first = manifest(setup)
    assert first["source_digest"] == report["source_digest"] and first["source_package_count"] == 5
    expected = {
        "schema_version": 2,
        "engine_version": fake_unreal.ENGINE_VERSION,
        "package_count": 5,
        "source_digest": report["source_digest"],
    }
    assert pure.compare_expected(first, expected) is None
    other_engine = pure.compare_expected(first, dict(expected, engine_version="5.8.4"))
    assert (
        other_engine and other_engine.startswith("GASP 갱신 — V-08b/V-15 재확인") and "5.8.4" in other_engine
    )
    changed = pure.compare_expected(first, dict(expected, source_digest="0" * 64))
    assert changed and changed.startswith("GASP 갱신")

    # A second PC whose Golmok already holds one of the closure packages (name conflict, skipped): the local
    # digest differs, the acquired-GASP digest does not.
    second = dict(setup)
    second["content"] = tmp_path / "pc2/Content"
    second["local"] = tmp_path / "pc2/local"
    second["work"] = tmp_path / "pc2/work"
    second["work"].mkdir(parents=True)
    _content(second["content"], [MANNY_OURS])
    (second["content"] / "Blueprints/Data").mkdir(parents=True)
    (second["content"] / "Blueprints/Data/DB.uasset").write_bytes(b"our own DB")
    open_gasp_project(second)
    report2 = run(second, "migrate", monkeypatch)
    assert report2["ok"] and report2["conflicts"] == [DB]
    assert report2["source_digest"] == report["source_digest"]


def test_migrate_notes_a_changed_gasp_project(setup, monkeypatch):
    tools = setup["fake"]

    original = fake_unreal.FakeAssetTools.migrate_packages

    def touching(self, package_names, destination_path, options=None):
        original(self, package_names, destination_path, options)
        (setup["source"] / "Blueprints/Data/DB.uasset").write_bytes(b"resaved by the editor")

    monkeypatch.setattr(fake_unreal.FakeAssetTools, "migrate_packages", touching)
    report = run(setup, "migrate")
    assert report["ok"] and report["source_unchanged"] is False and len(tools.calls_of("migrate")) == 1
    assert any("GASP project changed" in m for m in report["messages"])


# ---- T4 ----------------------------------------------------------------------------------------------------


def test_closure_keeps_unusual_but_valid_names_and_rejects_impossible_ones():
    deps = {ABP: ["/Game/Audio/Foley-Step_01", "/Game/Audio/한글_소리", "/Game/Bad Name", "/Game/X.Y"]}
    packages, rejected = pure.closure([ABP], lambda p: deps.get(p))
    assert packages == sorted([ABP, "/Game/Audio/Foley-Step_01", "/Game/Audio/한글_소리"])
    assert rejected == ["/Game/Bad Name", "/Game/X.Y"]
    for name in ("/Game/A+B/C", "/Game/Audio/Foley-Step_01", "/Game/Audio/한글_소리", "/Game/A(1)/B[2]"):
        assert pure.is_package_name(name), name
    impossible = ("/Game/Bad Name", "/Game/X.Y", "/Game/A:B", "/Game/A,B", "/Game/A&B", "/Game/A@B",
                  "/Game/A#B", "/Game/A!B", "/Game/A~B", "/Game/A'B", '/Game/A"B', "/Game/A|B", "/Game",
                  "/Game/", "/Game//A", "/Script/Engine", "/Game/A\\B")  # fmt: skip
    for name in impossible:
        assert not pure.is_package_name(name), name
    # existing packages are only compared by prefix: an odd name elsewhere in Content does not stop it.
    plan = pure.relocation_plan([ABP], ["/Game/Odd Folder/x!", MANNY_OURS])
    assert plan == [("dir", "/Game/Blueprints", "/Game/GASP/Blueprints")]


def test_migrate_fails_before_copying_on_an_impossible_dependency(setup):
    setup["fake"].dependencies[DB] = [UEFN, A1, "/Game/Bad Name"]
    report = run(setup, "migrate")
    assert not report["ok"] and setup["fake"].calls_of("migrate") == []
    assert any("/Game/Bad Name" in m for m in report["messages"]), report["messages"]


def test_verify_still_passes_after_the_new_install(setup):
    install(setup)
    checked = run(setup, "verify", expected=str(EXPECTED))
    assert checked["ok"], checked
    assert checked["messages"] == [
        "expected.json not filled yet (19b records the first verified source_digest)"
    ]
    assert pure.load_animation_config(ANIMATION)["content_root"] == "/Game/GASP"


# ---- T5 (C): redirectors through the asset registry; -Manifest after a GUI move ----------------------------


def test_redirectors_left_by_the_moves_are_found_in_the_registry_and_fixed_up(setup):
    setup["fake"].leave_redirectors = True
    result = install(setup)
    assert result["content_root"] == "/Game/GASP"
    ((_, count),) = setup["fake"].calls_of("fixup_referencers")
    assert count == 5  # every old path held a redirector (found without loading any asset)
    assert not any(
        k.startswith(("/Game/Blueprints/", "/Game/Characters/UEFN")) for k in setup["fake"].registry
    )


def test_redirectors_that_stay_roll_back_and_manifest_follows_a_gui_move(setup):
    fake = setup["fake"]
    fake.leave_redirectors, fake.fixup_deletes_redirectors = True, False
    assert run(setup, "migrate")["ok"]
    result = run(setup, "relocate")
    assert result["ok"] and result["exit"] == 2 and result["content_root"] == "/Game"
    assert manifest(setup)["content_root"] == "/Game"
    # Runbook section C #16: GUI Move + Fix Up Redirectors to /Game/GASP, then add-gasp -Manifest.
    shutil.move(setup["content"] / "Blueprints", setup["content"] / "GASP/Blueprints")
    (setup["content"] / "GASP/Characters").mkdir(parents=True, exist_ok=True)
    shutil.move(
        setup["content"] / "Characters/UEFN_Mannequin", setup["content"] / "GASP/Characters/UEFN_Mannequin"
    )
    rebuilt = run(setup, "manifest")
    assert rebuilt["ok"] and rebuilt["content_root"] == "/Game/GASP" and rebuilt["package_count"] == 5
    data = manifest(setup)
    assert data["content_root"] == "/Game/GASP" and pure.check_manifest(setup["content"], data) == []
    assert (
        data["source_digest"]
        == json.loads((setup["work"] / "migrate.json").read_text("utf-8"))["source_digest"]
    )
    shutil.rmtree(setup["content"] / "GASP/Blueprints")
    assert not run(setup, "manifest")["ok"]  # half here, half gone: nothing written
    assert manifest(setup) == data
