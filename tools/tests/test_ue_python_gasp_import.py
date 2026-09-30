"""WP-19a: golmok.gasp_pure (closure, relocation, manifest, DDCvar / tag text), golmok.gasp_import (fake).

No GASP content is used or committed: package names and ini lines are synthetic stand-ins with the GASP shapes
(V-08: 27 DDCvars with both DDCvar. / DDCVar. spellings, 39 gameplay tags, Migrate lands at the Content root).
"""

from __future__ import annotations

import importlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import fake_unreal
import pytest

REPO = Path(__file__).resolve().parents[2]
pure = importlib.import_module("golmok.gasp_pure")
CLOSURE = REPO / "tools/ue/gasp/closure.json"
EXPECTED = REPO / "tools/ue/gasp/expected.json"
ANIMATION = REPO / "unreal/Golmok/Config/Golmok/animation.json"

ABP = "/Game/Blueprints/SandboxCharacter_CMC_ABP"
BPI = "/Game/Blueprints/Interfaces/BPI_SandboxCharacter_Pawn"
UEFN = "/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin"
MANNY_OURS = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"


def synthetic_engine_ini(n: int = 27) -> str:
    kinds = ("CVarInt", "CVarFloat", "CVarBool")
    lines = [
        "[/Script/Engine.RendererSettings]",
        "r.Foo=1",
        "",
        "[/Script/Engine.DataDrivenConsoleVariableSettings]",
    ]
    for i in range(n):
        kind = kinds[i % 3]
        prefix = "DDCvar." if i % 2 else "DDCVar."
        lines.append(
            f'+CVarsArray=(Type={kind},Name="{prefix}Test{i}",ToolTip="tip {i}, with comma",'
            f"DefaultValueFloat={i / 2:.6f},DefaultValueInt={i},"
            f"DefaultValueBool={'True' if i % 4 == 2 else 'False'})"
        )
    lines += ["", "[/Script/Engine.OtherSettings]", '+CVarsArray=(Type=CVarInt,Name="NotThisSection")']
    return "\n".join(lines) + "\n"


def synthetic_tags_ini(n: int = 39) -> str:
    lines = ["[/Script/GameplayTags.GameplayTagsSettings]", "ImportTagsFromConfig=True"]
    lines += [f'+GameplayTagList=(Tag="Test.Tag{i}.Leaf",DevComment="c{i}")' for i in range(n)]
    return "\n".join(lines) + "\n"


# ---- pure: closure / relocation ----------------------------------------------------------------------------


def test_closure_keeps_game_packages_and_handles_cycles():
    deps = {
        ABP: [BPI, "/Script/Engine", "/PoseSearch/Foo", "/Game/Blueprints/Data/DB", "/Engine/X"],
        BPI: [ABP],  # cycle
        "/Game/Blueprints/Data/DB": ["/Game/Characters/UEFN_Mannequin/Anims/A1"],
    }
    got, rejected = pure.closure([ABP, "/Script/Nope"], lambda p: deps.get(p))
    assert got == sorted([ABP, BPI, "/Game/Blueprints/Data/DB", "/Game/Characters/UEFN_Mannequin/Anims/A1"])
    assert rejected == []


def test_map_to_root():
    assert pure.map_to_root("/Game/Blueprints/X", "/Game/GASP") == "/Game/GASP/Blueprints/X"
    assert pure.map_to_root("/Game/Blueprints/X", "/Game") == "/Game/Blueprints/X"
    with pytest.raises(ValueError):
        pure.map_to_root("/Game/X", "/Game/Other")
    with pytest.raises(ValueError):
        pure.map_to_root("/Script/Engine", "/Game/GASP")


def test_relocation_plan_moves_exclusive_folders_and_splits_shared_ones():
    migrated = [
        ABP,
        BPI,
        UEFN,
        "/Game/Characters/UEFN_Mannequin/Anims/A1",
        "/Game/Characters/Loose",
        "/Game/Root",
    ]
    existing = [MANNY_OURS, "/Game/Golmok/Maps/L_Dev"]
    plan = pure.relocation_plan(migrated, existing)
    assert ("dir", "/Game/Blueprints", "/Game/GASP/Blueprints") in plan
    assert ("dir", "/Game/Characters/UEFN_Mannequin", "/Game/GASP/Characters/UEFN_Mannequin") in plan
    assert ("asset", "/Game/Characters/Loose", "/Game/GASP/Characters/Loose") in plan
    assert ("asset", "/Game/Root", "/Game/GASP/Root") in plan
    assert not any(src in ("/Game/Characters", "/Game/Golmok", "/Game") for _, src, _ in plan)
    # Every migrated package ends up under /Game/GASP; no existing package is touched.
    moved = set()
    for package in migrated:
        for kind, src, dst in plan:
            if package == src or (kind == "dir" and package.startswith(src + "/")):
                moved.add(dst + package[len(src) :])
    assert moved == {pure.map_to_root(p, "/Game/GASP") for p in migrated}
    for package in existing:
        assert not any(package == src or package.startswith(src + "/") for _, src, _ in plan)
    assert pure.relocation_plan(migrated, existing, "/Game") == []
    with pytest.raises(ValueError):
        pure.relocation_plan(["/Game/GASP/Blueprints/X"], [])
    # add-gasp -Force with /Game/GASP already there: stop instead of a failing rename and a /Game rollback.
    with pytest.raises(ValueError, match="delete Content/GASP"):
        pure.relocation_plan([ABP], ["/Game/GASP/Blueprints/SandboxCharacter_CMC_ABP"])


def test_packages_on_disk(tmp_path):
    (tmp_path / "A/B").mkdir(parents=True)
    (tmp_path / "A/B/C.uasset").write_bytes(b"x")
    (tmp_path / "A/L.umap").write_bytes(b"x")
    (tmp_path / "A/readme.txt").write_text("x")
    assert pure.packages_on_disk(tmp_path) == {"/Game/A/B/C", "/Game/A/L"}
    assert pure.packages_on_disk(tmp_path / "missing") == set()


# ---- pure: manifest / expected -----------------------------------------------------------------------------


def _content(tmp_path, packages):
    for package in packages:
        path = tmp_path / (package[len("/Game/") :] + ".uasset")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(package.encode())
    return tmp_path


def test_manifest_digest_is_stable_and_detects_changes(tmp_path):
    packages = ["/Game/GASP/Blueprints/B", "/Game/GASP/Blueprints/A", "/Game/GASP/Characters/C"]
    content = _content(tmp_path, packages)
    now = datetime(2026, 9, 30, tzinfo=UTC)
    first = pure.build_manifest(content, packages, "/Game/GASP", "C:/UE/GASP_58", "5.8.3", now)
    second = pure.build_manifest(
        content, list(reversed(packages)), "/Game/GASP", "C:/UE/GASP_58", "5.8.3", now
    )
    assert first == second and first["package_count"] == 3
    assert [e["path"] for e in first["packages"]] == ["Blueprints/A", "Blueprints/B", "Characters/C"]
    assert first["generated_utc"] == "2026-09-30T00:00:00Z"
    assert pure.check_manifest(content, first) == []
    (content / "GASP/Blueprints/A.uasset").write_bytes(b"changed")
    (content / "GASP/Characters/C.uasset").unlink()
    assert sorted(pure.check_manifest(content, first)) == [
        "changed: /Game/GASP/Blueprints/A",
        "missing: /Game/GASP/Characters/C",
    ]
    edited = dict(first, package_count=2)
    assert any("digest" in p for p in pure.check_manifest(content, edited))
    with pytest.raises(FileNotFoundError):
        pure.build_manifest(content, ["/Game/GASP/Nope"], "/Game/GASP", "x", "5.8.3")


def test_compare_expected():
    # The acquired GASP (source_digest / source_package_count) and the engine; never the local digest.
    manifest = {
        "digest": "local",
        "source_digest": "abc",
        "source_package_count": 3,
        "engine_version": "5.8.3",
    }
    filled = {"source_digest": "abc", "package_count": 3, "engine_version": "5.8.3"}
    assert "not filled" in pure.compare_expected(manifest, dict(filled, source_digest=None))
    assert "not filled" in pure.compare_expected(manifest, dict(filled, engine_version=None))
    assert pure.compare_expected(manifest, filled) is None
    assert pure.compare_expected(dict(manifest, digest="other"), filled) is None
    for key, value in (("source_digest", "abd"), ("package_count", 4), ("engine_version", "5.8.4")):
        assert pure.compare_expected(manifest, dict(filled, **{key: value})).startswith(
            "GASP 갱신 — V-08b/V-15 재확인"
        )
    old = {
        "digest": "local",
        "package_count": 3,
        "engine_version": "5.8.3",
    }  # a 19a manifest: no source_digest
    assert pure.compare_expected(old, filled).startswith("GASP 갱신")


def test_committed_expected_is_null_or_a_verified_install():
    # null until 19b records the first verified install (runbook A7); then all three are set together.
    data = json.loads(EXPECTED.read_text(encoding="utf-8"))
    assert data["schema_version"] == 2
    assert set(data) == {"schema_version", "comment", *pure.EXPECTED_KEYS}
    values = (data["source_digest"], data["package_count"], data["engine_version"])
    if data["source_digest"] is None:
        assert values == (None, None, None)
    else:
        assert re.fullmatch(r"[0-9a-f]{64}", data["source_digest"]) and type(data["package_count"]) is int
        assert isinstance(data["engine_version"], str) and data["engine_version"]


# ---- pure: ini text ----------------------------------------------------------------------------------------


def test_parse_cvars_three_types_and_both_spellings():
    cvars = pure.parse_cvars(synthetic_engine_ini())
    assert len(cvars) == pure.EXPECTED_DDCVARS == 27
    assert {c["type"] for c in cvars} == {"int", "float", "bool"}
    assert all(c["name"].lower().startswith("ddcvar.") for c in cvars)
    assert {c["name"].split(".")[0] for c in cvars} == {"DDCvar", "DDCVar"}
    by_name = {c["name"]: c for c in cvars}
    assert by_name["DDCVar.Test0"] == {
        "name": "DDCVar.Test0",
        "type": "int",
        "default": 0,
        "help": "tip 0, with comma",
    }
    assert by_name["DDCvar.Test1"]["type"] == "float" and by_name["DDCvar.Test1"]["default"] == 0.5
    assert by_name["DDCVar.Test2"]["type"] == "bool" and by_name["DDCVar.Test2"]["default"] is True
    assert by_name["DDCVar.Test8"]["default"] is False
    # Unprefixed and '.'-prefixed array lines are the same array; other sections are ignored.
    alt = "[/Script/Engine.DataDrivenConsoleVariableSettings]\n"
    alt += "CVarsArray=(Type=CVarInt,Name=DDCvar.A,DefaultValueInt=3)\n"
    alt += '.CVarsArray=(Type=CVarBool,Name="DDCvar.B",DefaultValueBool=True)\n'
    assert [(c["name"], c["default"]) for c in pure.parse_cvars(alt)] == [("DDCvar.A", 3), ("DDCvar.B", True)]
    with pytest.raises(ValueError):
        pure.parse_cvars(
            '[/Script/Engine.DataDrivenConsoleVariableSettings]\n+CVarsArray=(Type=CVarString,Name="X")\n'
        )
    with pytest.raises(ValueError):
        pure.parse_cvars(alt + "+CVarsArray=(Type=CVarInt,Name=ddcvar.a)\n")
    doc = pure.ddcvars_json(cvars, "C:/UE/GASP_58/Config/DefaultEngine.ini")
    assert doc["schema_version"] == 1 and len(doc["cvars"]) == 27
    assert set(doc["cvars"][0]) == {"name", "type", "default", "help"}


def test_tags_round_trip():
    tags = pure.parse_tags(synthetic_tags_ini())
    assert len(tags) == pure.EXPECTED_TAGS == 39
    text = pure.tags_ini(tags + [("Test.Quote", 'say "hi"')], "C:/UE/GASP_58/Config/DefaultGameplayTags.ini")
    lines = text.splitlines()
    assert lines[1] == "[/Script/GameplayTags.GameplayTagsList]"
    assert lines[2] == 'GameplayTagList=(Tag="Test.Tag0.Leaf",DevComment="c0")'
    assert lines[-1] == 'GameplayTagList=(Tag="Test.Quote",DevComment="say \\"hi\\"")'
    assert sum(1 for line in lines if line.startswith("GameplayTagList=")) == 40
    assert pure.parse_tags('[/Script/GameplayTags.GameplayTagsSettings]\n+GameplayTagList=(Tag="A.B")\n') == [
        ("A.B", "")
    ]
    with pytest.raises(ValueError):
        pure.parse_tags('[/Script/GameplayTags.GameplayTagsSettings]\n+GameplayTagList=(Tag="bad tag")\n')


def test_committable_local_paths():
    porcelain = "\n".join(
        [
            "?? unreal/Golmok/Content/GASP/Blueprints/X.uasset",
            "?? unreal/Golmok/Content/Golmok/Maps/L_New.umap",
            " M unreal/Golmok/Content/Python/golmok/lighting.py",
            "A  unreal/Golmok/Config/Golmok/local/gasp_manifest.json",
            "?? unreal/Golmok/Config/Tags/GASP.ini",
            "?? unreal/Golmok/Config/DefaultGameplayTags.ini",
            "?? unreal/Golmok/Config/Golmok/animation.json",
            'R  unreal/Golmok/Content/Golmok/A.uasset -> "unreal/Golmok/Content/Blueprints/A.uasset"',
        ]
    )
    assert pure.committable_local_paths(porcelain) == [
        "unreal/Golmok/Content/GASP/Blueprints/X.uasset",
        "unreal/Golmok/Config/Golmok/local/gasp_manifest.json",
        "unreal/Golmok/Config/Tags/GASP.ini",
        "unreal/Golmok/Config/DefaultGameplayTags.ini",
        "unreal/Golmok/Content/Blueprints/A.uasset",
    ]


def test_closure_json_matches_animation_json():
    roots = pure.parse_closure(json.loads(CLOSURE.read_text(encoding="utf-8")))
    data = json.loads(ANIMATION.read_text(encoding="utf-8"))
    gasp = data["gasp"]

    def package(relative):
        return "/Game/" + relative.split(".")[0]

    assert roots[0] == ABP == package(gasp["anim_class"])
    assert package(gasp["pawn_interface"]) in roots
    assert package(gasp["preview"]["source_mesh"]) in roots
    raw = json.loads(CLOSURE.read_text(encoding="utf-8"))["roots"]
    assert raw[0]["status"] == "confirmed"  # V-08; 19b (A7) confirms the estimated ones
    with pytest.raises(ValueError):
        pure.parse_closure(
            {"schema_version": 1, "roots": [{"path": "/Game/GASP/X", "status": "confirmed", "note": ""}]}
        )
    with pytest.raises(ValueError):
        pure.parse_closure(
            {"schema_version": 1, "roots": [{"path": "/Game/X", "status": "maybe", "note": ""}]}
        )


# ---- gasp_import on fake_unreal ----------------------------------------------------------------------------


@pytest.fixture
def gasp(monkeypatch, tmp_path):
    deps = {
        ABP: [BPI, "/Game/Blueprints/Data/DB", "/Script/PoseSearch"],
        "/Game/Blueprints/Data/DB": [UEFN, "/Game/Characters/UEFN_Mannequin/Anims/A1"],
    }
    fake = fake_unreal.install(monkeypatch, tmp_path, dependencies=deps)
    for package in (ABP, BPI, UEFN, "/Game/Blueprints/Data/DB", "/Game/Characters/UEFN_Mannequin/Anims/A1"):
        fake.registry[package] = fake_unreal.FakeAsset(fake, package)
    module = importlib.import_module("golmok.gasp_import")
    content = Path(fake.content_dir)
    _content(content, [MANNY_OURS])  # the mannequin pack already in Golmok/Content/Characters
    gasp_project = tmp_path / "GASP_58"
    (gasp_project / "Config").mkdir(parents=True)
    (gasp_project / "Config/DefaultEngine.ini").write_text(synthetic_engine_ini(), encoding="utf-8")
    (gasp_project / "Config/DefaultGameplayTags.ini").write_text(synthetic_tags_ini(), encoding="utf-8")
    _content(gasp_project / "Content", list(deps) + [BPI, UEFN, "/Game/Characters/UEFN_Mannequin/Anims/A1"])
    return fake, module, content, gasp_project


def _migrate(module, content, tmp_path):
    report = module.migrate(CLOSURE, content, tmp_path / "GASP_58/Content")
    path = tmp_path / "migrate.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return report, path


def test_migrate_copies_the_closure_and_reports_missing_roots(gasp, tmp_path):
    fake, module, content, _ = gasp
    report, _ = _migrate(module, content, tmp_path)
    (call,) = fake.calls_of("migrate")
    assert set(call[1]) == {
        ABP,
        BPI,
        UEFN,
        "/Game/Blueprints/Data/DB",
        "/Game/Characters/UEFN_Mannequin/Anims/A1",
    }
    assert call[2] == str(content)
    assert report["ok"] and report["exit"] == 0 and report["not_copied"] == []
    assert len(report["roots_missing"]) == 2  # the two estimated retarget roots are not in this fake project
    assert MANNY_OURS in report["existing_before"] and report["conflicts"] == []
    assert (content / "Blueprints/SandboxCharacter_CMC_ABP.uasset").read_bytes() == ABP.encode()


def test_relocate_moves_under_gasp_and_writes_local_files(gasp, tmp_path):
    fake, module, content, gasp_project = gasp
    _, report_path = _migrate(module, content, tmp_path)
    local = tmp_path / "local"
    tags = tmp_path / "Tags/GASP.ini"
    result = module.relocate(report_path, content, local, tags, gasp_project)
    assert result["exit"] == 0 and result["content_root"] == "/Game/GASP"
    assert ("rename_directory", "/Game/Blueprints", "/Game/GASP/Blueprints") in fake.calls
    assert (
        "rename_directory",
        "/Game/Characters/UEFN_Mannequin",
        "/Game/GASP/Characters/UEFN_Mannequin",
    ) in fake.calls
    assert (content / "Characters/Mannequins/Meshes/SKM_Manny_Simple.uasset").is_file()  # ours untouched
    assert (content / "GASP/Blueprints/SandboxCharacter_CMC_ABP.uasset").is_file()
    assert not (content / "Blueprints").exists()
    manifest = json.loads((local / "gasp_manifest.json").read_text(encoding="utf-8"))
    assert manifest["content_root"] == "/Game/GASP" and manifest["package_count"] == 5
    assert (
        manifest["gasp_project"] == str(gasp_project)
        and manifest["engine_version"] == fake_unreal.ENGINE_VERSION
    )
    assert len(json.loads((local / "gasp_ddcvars.json").read_text(encoding="utf-8"))["cvars"]) == 27
    assert tags.read_text(encoding="utf-8").count("GameplayTagList=") == 39
    assert ABP not in fake.registry and "/Game/GASP" + ABP[len("/Game") :] in fake.registry

    # verify on the same install: clean, then a committable GASP path and a changed file are problems.
    status = tmp_path / "git-status.txt"
    status.write_text("", encoding="utf-8")
    ok = module.verify(content, local, tags, EXPECTED, status, ANIMATION)
    assert ok["ok"] and ok["exit"] == 0, ok
    assert ok["messages"] == ["expected.json not filled yet (19b records the first verified source_digest)"]
    status.write_text("?? unreal/Golmok/Content/GASP/Blueprints/X.uasset\n", encoding="utf-8")
    (content / "GASP/Blueprints/Data/DB.uasset").write_bytes(b"edited")
    bad = module.verify(content, local, tags, EXPECTED, status, ANIMATION)
    assert not bad["ok"] and bad["exit"] == 1
    assert "changed: /Game/GASP/Blueprints/Data/DB" in bad["messages"]
    assert any("never git add" in m for m in bad["messages"])


def test_relocate_failure_rolls_back_to_game_root(gasp, tmp_path):
    fake, module, content, gasp_project = gasp
    _, report_path = _migrate(module, content, tmp_path)
    fake.rename_directory_ok = False
    local = tmp_path / "local"
    result = module.relocate(report_path, content, local, tmp_path / "GASP.ini", gasp_project)
    assert result["exit"] == 2 and result["content_root"] == "/Game"
    assert "content_root to /Game" in result["messages"][0]
    manifest = json.loads((local / "gasp_manifest.json").read_text(encoding="utf-8"))
    assert manifest["content_root"] == "/Game" and manifest["packages"][0]["path"].startswith("Blueprints/")
    assert ABP in fake.registry and (content / "Blueprints/SandboxCharacter_CMC_ABP.uasset").is_file()
    # animation.json still says /Game/GASP: verify tells the user what to change.
    status = tmp_path / "git-status.txt"
    status.write_text("", encoding="utf-8")
    checked = module.verify(content, local, tmp_path / "GASP.ini", EXPECTED, status, ANIMATION)
    assert any("set animation.json content_root to /Game" in m for m in checked["messages"])


def test_main_runs_a_job_and_writes_the_result(gasp, tmp_path, monkeypatch):
    _, module, content, _ = gasp
    job = tmp_path / "job.json"
    result = tmp_path / "out/migrate.json"
    job.write_text(json.dumps({"step": "migrate", "closure": str(CLOSURE), "dest_content": str(content),
                               "source_content": str(tmp_path / "GASP_58/Content"),
                               "result": str(result)}), encoding="utf-8")  # fmt: skip
    monkeypatch.setenv(module.JOB_ENV, str(job))
    assert module.main() == 0
    assert json.loads(result.read_text(encoding="utf-8"))["ok"] is True
    job.write_text(json.dumps({"step": "nope", "result": str(result)}), encoding="utf-8")
    assert module.main() == 1
    assert "unknown add-gasp step" in json.loads(result.read_text(encoding="utf-8"))["messages"][0]
    monkeypatch.delenv(module.JOB_ENV)
    assert module.main() == 1


def test_add_gasp_script_drives_gasp_import():
    text = (REPO / "tools/ue/add-gasp.ps1").read_text(encoding="utf-8")
    assert '. (Join-Path $PSScriptRoot "common.ps1")' in text
    assert "golmok\\gasp_import.py" in text and "GOLMOK_GASP_JOB" in text
    for step in ('step = "migrate"', 'step = "relocate"', 'step = "verify"'):
        assert step in text
    assert (
        'param([string]$GaspProject = "C:\\UE\\GASP_58", [switch]$Verify, [switch]$Force, '
        "[switch]$LocalFiles, [switch]$Manifest)"
    ) in text
    assert "--untracked-files=all" in text and "$ExitCode" not in text
    for step in ('step = "local_files"', 'step = "manifest"', "source_content = ", "history = "):
        assert step in text, step
    # R76 T1 / T7: -Force stops before migrate over Content\GASP; the manifest alone means "installed";
    # a path with a space, a running editor and a missing mannequin pack stop before any editor session.
    force = text.index("add-gasp -Force never overwrites an install")
    assert force < text.index('step = "migrate"') and "Test-Path $ManifestFile" in text
    assert "$Script -match '\\s'" in text and "Get-CimInstance Win32_Process" in text
    assert text.index("add-mannequin.ps1 first") < text.index('step = "migrate"')
