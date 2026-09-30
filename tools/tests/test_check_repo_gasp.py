"""WP-19a: the check_repo.py GASP guard (design section 9) on temporary git repositories.

Rules: a tracked or addable file under unreal/Golmok/Content/ outside Golmok/ and Python/ fails;
Config/Golmok/local/, Config/Tags/GASP*.ini and Config/DefaultGameplayTags.ini fail when tracked or addable;
"DDCvar." in Config/Default*.ini fails while GASP_INI_COMMIT_ALLOWED is False. A root that is not the top of a
git work tree is skipped (the synthetic repos of test_check_repo.py keep passing).
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "scripts" / "check_repo.py"
_spec = importlib.util.spec_from_file_location("check_repo_gasp", SCRIPT)
check_repo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_repo)

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def write(root: Path, rel: str, text: str = "x") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "test")
    shutil.copy(REPO / ".gitignore", root / ".gitignore")
    write(root, "unreal/Golmok/Config/DefaultEngine.ini", "[/Script/Engine.RendererSettings]\nr.Foo=1\n")
    write(root, "unreal/Golmok/Content/Golmok/Maps/L_Dev.umap")
    write(root, "unreal/Golmok/Content/Python/golmok/__init__.py")
    write(root, "unreal/Golmok/Config/Golmok/animation.json", "{}")
    git(root, "add", "-A")
    git(root, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "init")
    return root


def test_clean_git_repo_passes(repo):
    assert check_repo.check_gasp_guard(repo) == []


def test_non_git_folder_and_subfolder_are_skipped(tmp_path, repo):
    plain = tmp_path / "plain"
    write(plain, "unreal/Golmok/Content/GASP/X.uasset")
    write(plain, "unreal/Golmok/Config/DefaultEngine.ini", "+CVarsArray=(Name=DDCvar.X)\n")
    assert check_repo.check_gasp_guard(plain) == []
    write(repo, "unreal/Golmok/Config/DefaultGame.ini", "DDCvar.Y=1\n")
    assert check_repo.check_gasp_guard(repo / "unreal") == []  # not the work tree top


def test_ignored_local_files_pass_but_forced_ones_fail(repo):
    write(repo, "unreal/Golmok/Content/GASP/Blueprints/ABP.uasset")
    write(repo, "unreal/Golmok/Content/Blueprints/Migrated.uasset")
    write(repo, "unreal/Golmok/Config/Golmok/local/gasp_manifest.json", "{}")
    write(repo, "unreal/Golmok/Config/Tags/GASP.ini", "[/Script/GameplayTags.GameplayTagsList]\n")
    assert check_repo.check_gasp_guard(repo) == []  # .gitignore [WP-19 hook] keeps them out
    git(
        repo,
        "add",
        "-f",
        "unreal/Golmok/Content/GASP/Blueprints/ABP.uasset",
        "unreal/Golmok/Config/Tags/GASP.ini",
    )
    errors = check_repo.check_gasp_guard(repo)
    assert len(errors) == 2
    assert errors[0].startswith("unreal/Golmok/Config/Tags/GASP.ini: GASP 가드") or errors[1].startswith(
        "unreal/Golmok/Config/Tags/GASP.ini: GASP 가드"
    )
    assert all("추적 중" in e for e in errors)


def test_addable_files_fail_without_the_ignore_rules(repo):
    (repo / ".gitignore").write_text("", encoding="utf-8")
    write(repo, "unreal/Golmok/Content/Characters/UEFN/SKM.uasset")
    write(repo, "unreal/Golmok/Config/Golmok/local/gasp_ddcvars.json", "{}")
    write(
        repo, "unreal/Golmok/Config/DefaultGameplayTags.ini", "[/Script/GameplayTags.GameplayTagsSettings]\n"
    )
    write(repo, "unreal/Golmok/Content/Golmok/New.uasset")  # allowed
    errors = check_repo.check_gasp_guard(repo)
    assert sorted(e.split(":")[0] for e in errors) == [
        "unreal/Golmok/Config/DefaultGameplayTags.ini",
        "unreal/Golmok/Config/Golmok/local/gasp_ddcvars.json",
        "unreal/Golmok/Content/Characters/UEFN/SKM.uasset",
    ]
    assert all("추가 가능" in e for e in errors)


def test_ddcvar_text_in_default_ini_fails_until_allowed(repo, monkeypatch):
    write(
        repo,
        "unreal/Golmok/Config/DefaultEngine.ini",
        "[/Script/Engine.RendererSettings]\nr.Foo=1\n[/Script/Engine.DataDrivenConsoleVariableSettings]\n"
        '+CVarsArray=(Type=CVarInt,Name="DDCVar.FootPlacementMode")\n',
    )
    (error,) = check_repo.check_gasp_guard(repo)
    assert error.startswith("unreal/Golmok/Config/DefaultEngine.ini:3: GASP 가드")  # the section header
    monkeypatch.setattr(check_repo, "GASP_INI_COMMIT_ALLOWED", True)
    assert check_repo.check_gasp_guard(repo) == []


def test_guard_is_registered_and_the_real_repo_passes(capsys):
    assert check_repo.CHECKS["gasp"] is check_repo.check_gasp_guard
    assert check_repo.check_gasp_guard(REPO) == []
    assert check_repo.GASP_INI_COMMIT_ALLOWED is False


# ---- WP-19a-2 (review R76 T3, T8): content rules, case, location, one path table for both guards ----------

_pure_spec = importlib.util.spec_from_file_location(
    "gasp_pure_guard", REPO / "unreal/Golmok/Content/Python/golmok/gasp_pure.py"
)
gasp_pure = importlib.util.module_from_spec(_pure_spec)
_pure_spec.loader.exec_module(gasp_pure)

# (repo path, forbidden by the path rules) - check_gasp_guard (tracked / addable) and gasp_pure.is_local_only
# (add-gasp verify on git status) must agree on every row.
PATH_TABLE = (
    ("unreal/Golmok/Content/Golmok/Maps/L_New.umap", False),
    ("unreal/Golmok/Content/Golmok/Audio/A.uasset", False),
    ("unreal/Golmok/Content/Python/golmok/new.py", False),
    ("unreal/Golmok/Config/Golmok/animation.json", False),
    ("unreal/Golmok/Config/DefaultEngine.ini", False),
    ("unreal/Golmok/Config/Windows/WindowsEngine.ini", False),
    ("tools/ue/gasp/closure.json", False),
    ("docs/runbooks/pc-verify-wp19.md", False),
    ("unreal/Golmok/Content/GASP/Blueprints/ABP.uasset", True),
    ("unreal/Golmok/Content/Blueprints/Migrated.uasset", True),
    ("unreal/Golmok/Content/Characters/UEFN/SKM.uasset", True),
    ("unreal/Golmok/Content/gasp/X.uasset", True),
    ("unreal/Golmok/content/Blueprints/X.uasset", True),
    ("unreal/Golmok/Content/Golmok/GASP/ABP.uasset", True),
    ("unreal/Golmok/Content/Golmok/gasp/readme.txt", True),
    ("unreal/Golmok/Content/Golmok/GolmokLocal/BP.uasset", True),
    ("unreal/Golmok/Content/Python/golmok/stray.uasset", True),
    ("unreal/Golmok/Plugins/X/Content/A.uasset", True),
    ("unreal/Golmok/Content/Golmok/../Blueprints/A.UASSET", True),
    ("docs/A.umap", True),
    ("unreal/Golmok/Config/Golmok/local/gasp_manifest.json", True),
    ("unreal/Golmok/Config/golmok/LOCAL/x.json", True),
    ("unreal/Golmok/Config/Tags/GASP.ini", True),
    ("unreal/Golmok/Config/Tags/gasp.ini", True),
    ("unreal/Golmok/Config/Tags/Locomotion.ini", True),
    ("unreal/Golmok/Config/tags/Other.INI", True),
    ("unreal/Golmok/Config/DefaultGameplayTags.ini", True),
    ("unreal/Golmok/Config/DefaultGameplayTags.INI", True),
)


def test_one_path_table_for_check_repo_and_gasp_pure(repo):
    (repo / ".gitignore").write_text("", encoding="utf-8")  # everything addable
    for path, _ in PATH_TABLE:
        if ".." not in path:
            write(repo, path)
    errors = check_repo.check_gasp_guard(repo)
    # R78-5: the "x" written as Config/Golmok/local/gasp_manifest.json is an unreadable manifest: one line
    assert [e for e in errors if e.startswith("gasp:")] == [
        "gasp: unreal/Golmok/Config/Golmok/local/gasp_manifest.json를 읽지 못함(JSONDecodeError) — "
        "add-gasp -Manifest로 다시 만든다"
    ]
    errors = [e for e in errors if not e.startswith("gasp:")]
    # Lower case: on a case-insensitive file system (Windows CI) "content/…" lands in "Content/…" and git
    # lists the on-disk spelling.
    flagged = {e.split(": GASP 가드")[0].lower() for e in errors}
    for path, forbidden in PATH_TABLE:
        assert gasp_pure.is_local_only(path) is forbidden, path
        if ".." not in path:
            assert (path.lower() in flagged) is forbidden, (path, errors)
    assert all("추가 가능" in e for e in errors)


INI_TEXTS = (
    "[/Script/Engine.DataDrivenConsoleVariableSettings]\n",
    '+CVarsArray=(Type=CVarInt,Name="Foo.Bar")\n',
    'CVarsArray=(Type=CVarInt,Name="Foo.Bar")\n',
    "ddcvar.FootPlacement=1\n",
    '[/Script/GameplayTags.GameplayTagsList]\nGameplayTagList=(Tag="A.B")\n',
    '+gameplaytaglist=(Tag="A.B")\n',
)


@pytest.mark.parametrize("text", INI_TEXTS)
@pytest.mark.parametrize(
    "rel",
    [
        "unreal/Golmok/Config/Windows/WindowsEngine.ini",
        "unreal/Golmok/Config/DefaultGame.ini",
        "unreal/Golmok/Plugins/P/Config/DefaultP.ini",
    ],
)
def test_gasp_ini_text_fails_in_any_committable_config_ini(repo, monkeypatch, rel, text):
    write(repo, rel, "[/Script/Engine.RendererSettings]\nr.Foo=1\n" + text)
    errors = check_repo.check_gasp_guard(repo)
    assert len(errors) == 1 and errors[0].startswith(f"{rel}:") and "GASP 가드" in errors[0], errors
    monkeypatch.setattr(check_repo, "GASP_INI_COMMIT_ALLOWED", True)
    assert check_repo.check_gasp_guard(repo) == []


def test_ignored_config_ini_with_gasp_text_is_local_and_passes(repo):
    write(
        repo,
        "unreal/Golmok/Config/Tags/GASP.ini",
        '[/Script/GameplayTags.GameplayTagsList]\nGameplayTagList=(Tag="A")\n',
    )
    assert check_repo.check_gasp_guard(repo) == []


def test_git_failure_in_a_git_work_tree_is_reported(repo, monkeypatch):
    monkeypatch.setattr(check_repo, "_git_paths", lambda root, *args: None)
    (error,) = check_repo.check_gasp_guard(repo)
    assert error.startswith("gasp: git") and "safe.directory" in error


def test_git_ls_files_failure_after_a_good_rev_parse_is_reported(repo, monkeypatch):
    """R78-6: the ls-files branch, not only rev-parse, reports instead of skipping."""
    real = check_repo._git_paths
    monkeypatch.setattr(
        check_repo, "_git_paths", lambda root, *args: None if args[0] == "ls-files" else real(root, *args)
    )
    (error,) = check_repo.check_gasp_guard(repo)
    assert error.startswith("gasp: git") and "ls-files" in error


# ---- R78-5: GASP ini text in any Config text file; renamed GASP packages against the local manifest ----

CONFIG_TEXT_FAILS = (
    ("unreal/Golmok/Config/Golmok/ddcvars.json", '{\n  "DDCvar.FootPlacementMode": 1\n}\n', 2),
    ("unreal/Golmok/Config/Golmok/ddcvars.json", '{"x": "DDCVar.EnableFootPlacement=True"}\n', 1),
    (
        "unreal/Golmok/Config/Golmok/copied.json",
        '{\n "cvars": [\n  {"name": "DDCvar.X", "type": "int", "default": 1, "help": ""}\n ]\n}\n',
        3,
    ),
    ("unreal/Golmok/Config/Golmok/notes.txt", "a\n[/Script/Engine.DataDrivenConsoleVariableSettings]\n", 2),
    ("unreal/Golmok/Config/engine.txt", '+CVarsArray=(Type=CVarInt,Name="Foo.Bar")\n', 1),
    ("unreal/Golmok/Config/Windows/tags.TXT", '\n\n+GameplayTagList=(Tag="A.B")\n', 3),
    ("unreal/Golmok/Plugins/P/Config/p.json", '{"ddcvar.x" : 0.5}\n', 1),
)


CONFIG_TEXT_FAILS += (
    # verify round: key-sorted copy of add-gasp's list (json.dumps(sort_keys=True))
    (
        "unreal/Golmok/Config/Golmok/sorted.json",
        '{"cvars": [{"default": 1, "help": "tip", "name": "DDCvar.X", "type": "int"}]}\n',
        1,
    ),
    ("unreal/Golmok/Config/Golmok/cvars.yaml", "cvars:\n  DDCvar.X: 1\n", 2),  # any Config text file
    ("unreal/Golmok/Config/DefaultEngine.ini.orig", "a\nDDCvar.FootPlacementMode\n", 2),  # .ini rule
    ("unreal/Golmok/Config/DefaultEngine.ini.bak", "[/Script/Engine.DataDrivenConsoleVariableSettings]\n", 1),
)


@pytest.mark.parametrize(("rel", "text", "line"), CONFIG_TEXT_FAILS)
def test_gasp_ini_text_fails_in_config_json_and_txt(repo, monkeypatch, rel, text, line):
    write(repo, rel, text)
    errors = check_repo.check_gasp_guard(repo)
    assert len(errors) == 1 and errors[0].startswith(f"{rel}:{line}: GASP 가드"), errors
    monkeypatch.setattr(check_repo, "GASP_INI_COMMIT_ALLOWED", True)
    assert check_repo.check_gasp_guard(repo) == []


CONFIG_JSON_PASSES = (
    '{"gasp": {"abp": "/Game/GASP/Blueprints/ABP_SandboxCharacter", "cvars": ["DDCvar.FootPlacementMode"]}}',
    '{"note": "DDCvar.X names are allowed (D-021)", "path": "/Game/GASP/Chooser/CHT_Loco.CHT_Loco"}',
    '{"name": "DDCvar.X"}',
    '{"GameplayTag": "Gameplay.Locomotion", "tags": ["DDCvar"]}',
)


@pytest.mark.parametrize("text", CONFIG_JSON_PASSES)
def test_gasp_names_and_paths_in_our_config_json_pass(repo, text):
    """D-021: GASP names and path strings may be committed (animation.json, characters.json)."""
    write(repo, "unreal/Golmok/Config/Golmok/animation.json", text)
    write(repo, "unreal/Golmok/Config/Golmok/readme.txt", "CBP_SandboxCharacter, DDCvar.FootPlacementMode\n")
    assert check_repo.check_gasp_guard(repo) == []


@pytest.mark.parametrize("rel", ["unreal/Golmok/Config/u16.txt", "unreal/Golmok/Config/u16.ini"])
@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-be"])
def test_utf16_config_text_is_read_too(repo, rel, encoding):
    """UE writes a config file as UTF-16 when it holds non-ASCII text (verify round)."""
    path = repo / rel
    bom = "\ufeff" if encoding == "utf-16-be" else ""
    path.write_bytes((bom + "; 한글\n[/Script/Engine.DataDrivenConsoleVariableSettings]\n").encode(encoding))
    (error,) = check_repo.check_gasp_guard(repo)
    assert error.startswith(f"{rel}:2: GASP 가드"), error


def _manifest(repo, data: bytes, path="Blueprints/ABP_SandboxCharacter"):
    import hashlib
    import json

    entry = {"path": path, "file": ".uasset", "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    manifest = {"schema_version": 1, "content_root": "/Game", "package_count": 1, "packages": [entry]}
    write(repo, "unreal/Golmok/Config/Golmok/local/gasp_manifest.json", json.dumps(manifest))


def test_renamed_gasp_package_in_content_golmok_fails_against_the_local_manifest(repo):
    data = b"GASP package bytes"
    _manifest(repo, data)
    renamed = repo / "unreal/Golmok/Content/Golmok/Anim/ABP_Walk.uasset"
    renamed.parent.mkdir(parents=True)
    renamed.write_bytes(data)
    write(repo, "unreal/Golmok/Content/Golmok/Anim/ABP_Other.uasset", "GASP package byteZ")  # same size
    (error,) = check_repo.check_gasp_guard(repo)
    assert error.startswith("unreal/Golmok/Content/Golmok/Anim/ABP_Walk.uasset: GASP 가드"), error
    assert "Blueprints/ABP_SandboxCharacter" in error and "추가 가능" in error
    git(repo, "add", "unreal/Golmok/Content/Golmok/Anim/ABP_Walk.uasset")
    (error,) = check_repo.check_gasp_guard(repo)
    assert "추적 중" in error


def test_without_a_local_manifest_the_package_check_is_skipped(repo):
    write(repo, "unreal/Golmok/Content/Golmok/Anim/ABP_Walk.uasset", "GASP package bytes")
    assert check_repo.check_gasp_guard(repo) == []  # CI and every PC without add-gasp


@pytest.mark.parametrize(
    "text", ["{not json", "[]", '{"packages": [{"path": "A", "size": 1.5, "sha256": "x"}]}']
)
def test_an_unreadable_local_manifest_is_reported_not_skipped(repo, text):
    write(repo, "unreal/Golmok/Config/Golmok/local/gasp_manifest.json", text)
    (error,) = check_repo.check_gasp_guard(repo)
    assert error.startswith("gasp:") and "gasp_manifest.json" in error


# ---- R78-7: a .git whose toplevel names another folder fails instead of skipping -------------------------


def test_toplevel_of_another_folder_fails_when_root_has_git(repo, tmp_path, monkeypatch):
    other = tmp_path / "other"
    other.mkdir()
    real = check_repo._git_paths

    def fake(root, *args):
        return [str(other)] if args[:1] == ("rev-parse",) else real(root, *args)

    monkeypatch.setattr(check_repo, "_git_paths", fake)
    (error,) = check_repo.check_gasp_guard(repo)
    assert error.startswith("gasp: git") and "toplevel" in error
    monkeypatch.setattr(
        check_repo,
        "_git_paths",
        lambda root, *a: [str(tmp_path / "gone")] if a[0] == "rev-parse" else real(root, *a),
    )
    (error,) = check_repo.check_gasp_guard(repo)
    assert "toplevel" in error


def test_toplevel_spelled_another_way_for_the_same_folder_passes(repo, tmp_path, monkeypatch):
    """subst / junction / symlink spellings (R78-7): os.path.samefile, not a string compare."""
    link = tmp_path / "link"
    try:
        link.symlink_to(repo, target_is_directory=True)
    except OSError:
        pytest.skip("no symlink permission")
    real = check_repo._git_paths
    monkeypatch.setattr(
        check_repo,
        "_git_paths",
        lambda root, *a: [str(link) + "\n"] if a[0] == "rev-parse" else real(root, *a),
    )
    write(repo, "unreal/Golmok/Content/GASP/X.uasset")
    (repo / ".gitignore").write_text("", encoding="utf-8")
    (error,) = check_repo.check_gasp_guard(repo)  # checked, not skipped
    assert error.startswith("unreal/Golmok/Content/GASP/X.uasset: GASP 가드")
    assert check_repo.check_gasp_guard(link) == [error]


# ---- R78-9: the check_repo.py constants and golmok.gasp_pure move together -------------------------------


def test_guard_constants_match_gasp_pure():
    assert check_repo.GASP_TAGS_ALLOWED == gasp_pure.TAGS_ALLOWED
    assert (check_repo.GASP_TAGS_FILE,) == gasp_pure.LOCAL_ONLY_FILES
    assert check_repo.GASP_LOCAL_ONLY == gasp_pure.LOCAL_ONLY_PREFIXES
    assert check_repo.GASP_TAGS_DIR == gasp_pure.TAGS_DIR
    assert check_repo.GASP_CONTENT == gasp_pure.GUARD_CONTENT
    assert check_repo.GASP_TRACKED_CONTENT == gasp_pure.TRACKED_CONTENT
    assert check_repo.GASP_PACKAGE_CONTENT == gasp_pure.PACKAGE_CONTENT
    assert check_repo.GASP_LOCAL_FOLDERS == gasp_pure.LOCAL_FOLDER_NAMES
    # gasp_pure.is_local_only has no GASP_INI_COMMIT_ALLOWED switch: flipping it means editing both files
    # (and this test: with it False, DefaultGameplayTags.ini must stay local in both)
    assert check_repo.GASP_INI_COMMIT_ALLOWED is False
    assert gasp_pure.is_local_only("unreal/Golmok/Config/DefaultGameplayTags.ini")


# ---- R81-1: the toplevel compare is os.path.samefile, not resolve() -------------------------------------


def test_toplevel_compare_is_samefile_not_resolve(repo, tmp_path, monkeypatch):
    """R81-1: two spellings whose strings and resolve() both differ, that only samefile calls the same folder
    (a subst drive / junction on Windows). A symlink test cannot tell them apart: resolve() follows it too."""
    alias = tmp_path / "subst-drive" / "repo"  # never created: resolve() keeps it, unlike repo
    assert str(alias) != str(repo) and alias.resolve() != repo.resolve()
    real_samefile = check_repo.os.path.samefile
    calls = []

    def samefile(a, b):
        calls.append((str(a), str(b)))
        if {str(a), str(b)} == {str(alias), str(repo)}:
            return True
        return real_samefile(a, b)

    monkeypatch.setattr(check_repo.os.path, "samefile", samefile)
    real = check_repo._git_paths
    monkeypatch.setattr(
        check_repo,
        "_git_paths",
        lambda root, *a: [str(alias) + "\n"] if a[0] == "rev-parse" else real(root, *a),
    )
    write(repo, "unreal/Golmok/Content/GASP/X.uasset")
    (repo / ".gitignore").write_text("", encoding="utf-8")
    (error,) = check_repo.check_gasp_guard(repo)  # checked, neither skipped nor a toplevel error
    assert error.startswith("unreal/Golmok/Content/GASP/X.uasset: GASP 가드"), error
    assert calls == [(str(alias), str(repo))]


# ---- R81-2 / R81-3: add-gasp list forms, the matched name in the message ---------------------------------

CVAR_LIST_FAILS = (
    ('{"cvars":[{"name":"DDCvar.X","value":1}]}\n', "DDCvar.X"),
    ('{"name":"DDCvar.X","DefaultValueInt":1}\n', "DDCvar.X"),
    ('[{"name": "DDCvar.Y", "defaultValue": true}]\n', "DDCvar.Y"),
    # json.dumps(sort_keys=True) with braces in the help text: "default" before and "name" after the "{"
    (
        '{"cvars": [{"default": 1, "help": "0 = off {legacy}, 1 = on", "name": "DDCvar.Foot.Mode", '
        '"type": "int"}]}\n',
        "DDCvar.Foot.Mode",
    ),
    ('{"cvars": [{"default": 1, "help": "a \\"{\\" b", "name": "DDCvar.Q", "type": "int"}]}\n', "DDCvar.Q"),
    ('{"cvars": [\n  {\n    "help": "}",\n    "name": "DDCvar.Z",\n    "value": 2\n  }\n]}\n', "DDCvar.Z"),
)


@pytest.mark.parametrize(("text", "name"), CVAR_LIST_FAILS)
def test_add_gasp_list_forms_fail_and_name_the_cvar(repo, text, name):
    rel = "unreal/Golmok/Config/Golmok/copied.json"
    write(repo, rel, text)
    (error,) = check_repo.check_gasp_guard(repo)
    assert error.startswith(f"{rel}:") and "GASP 가드" in error, error
    assert f'"{name}"' in error and "({)" not in error, error  # R81-2: the name, not a lone "{"


def test_add_gasp_list_line_is_the_object_line(repo):
    rel = "unreal/Golmok/Config/Golmok/copied.json"
    write(repo, rel, '{\n "cvars": [\n  {"help": "{", "name": "DDCvar.X", "value": 1}\n ]\n}\n')
    (error,) = check_repo.check_gasp_guard(repo)
    assert error.startswith(f"{rel}:3: GASP 가드"), error


CVAR_OTHER_FORMS_FAIL = (
    ('{"cvars": [["DDCvar.X", 1], ["DDCvar.Y", 0.5]]}\n', "DDCvar.X"),  # pair list
    ('{"cvars": [["DDCvar.Y", -0.5]]}\n', "DDCvar.Y"),  # R87-6: a negative decimal alone (the -?\.? of pairs)
    ('[ [ "ddcvar.x" , true ] ]\n', "ddcvar.x"),
    ("DDCvar.FootPlacementMode 1\n", "DDCvar.FootPlacementMode"),  # console form (.txt)
    ("; tuning\n  ddcvar.x -0.5\n", "ddcvar.x"),
    ("DDCvar.X true\n", "DDCvar.X"),  # R87-6: console bool values
    ("\tDDCvar.Y False\n", "DDCvar.Y"),
    # R87-1: a key after a \n / \t escape inside a JSON string (main caught these)
    ('{"ini": "[ConsoleVariables]\\nDDCvar.X=1"}\n', "DDCvar.X"),
    ('{"ini": "\\tDDCvar.X=1"}\n', "DDCvar.X"),
    ('{"ini": "a\\rDDCvar.X=1"}\n', "DDCvar.X"),  # verify: \r pinned too
)


@pytest.mark.parametrize(("text", "name"), CVAR_OTHER_FORMS_FAIL)
def test_pair_list_and_console_forms_fail(repo, text, name):
    rel = "unreal/Golmok/Config/Golmok/cvars.txt"
    write(repo, rel, text)
    (error,) = check_repo.check_gasp_guard(repo)
    assert error.startswith(f"{rel}:") and "GASP 가드" in error and name in error, error


def test_pretty_pair_list_error_is_one_line(repo):
    """R87-6: a pair list spread over lines is shown on one line in the error."""
    rel = "unreal/Golmok/Config/Golmok/cvars.json"
    write(repo, rel, '{"cvars": [\n  [\n    "DDCvar.X",\n    1\n  ]\n]}\n')
    (error,) = check_repo.check_gasp_guard(repo)
    assert error == f'{rel}:2: GASP 가드 — GASP ini 형식 텍스트([ "DDCvar.X", 1)는 커밋하지 않는다', error


CVAR_NAME_TEXTS_PASS = (
    '{"cvars": ["DDCvar.X", "DDCvar.Y"], "note": "value: 1"}',  # a name list (D-021)
    '{"name": "DDCvar.X", "values": "see ABP"}',
    '{"name": "DDCvar.X"}, {"value": 1}',  # value in another object
    '{"rows": [{"name": "Walk", "value": 1}], "cvar": {"name": "DDCvar.X"}}',
    '{"help": "{\\"name\\": \\"DDCvar.X\\", \\"value\\": 1}"}',  # quoted inside a string
    "cvars: DDCvar.X, DDCvar.Y\nDDCvar.X is set in the ABP (1 = on)\n",
    "set DDCvar.X 1 in the console\n",  # console form only at the start of a line (verify F8)
    "DDCvar.X\n1\n",
    "DDCvar.X truthy flag, see the ABP\n",  # R87-6: a word that starts with true is not a value
)


@pytest.mark.parametrize("text", CVAR_NAME_TEXTS_PASS)
def test_cvar_names_without_values_pass(repo, text):
    write(repo, "unreal/Golmok/Config/Golmok/animation.json", text)
    assert check_repo.check_gasp_guard(repo) == []


def test_text_rule_is_linear_on_a_large_config(repo):
    """Verify round: no catastrophic backtracking on a large JSON with many unclosed objects and strings."""
    import time

    rel = "unreal/Golmok/Config/Golmok/big.json"
    chunk = '{"name": "DDCvar.X", "help": "' + "{" * 50 + '", "note": "\\"}" '
    # one object with many string keys and no value key: overlapping alternatives (a "help" string or any
    # character) would backtrack 2**20 ways per object, about 7 s for these three
    many = '{"name": "DDCvar.X", ' + '"help": "a", ' * 20 + "}"
    write(repo, rel, "[" + chunk * 4000 + many * 3 + "]")
    start = time.perf_counter()
    check_repo.GASP_TEXT_INI_FORMS.search((repo / rel).read_text(encoding="utf-8"))
    assert time.perf_counter() - start < 2.0


@pytest.mark.parametrize(
    "text",
    [
        '{\\"' * 20000,  # a "{" inside an escaped string: no string may start at the escaping backslash
        '{"help": "' + '{\\"name\\": \\"DDCvar.X\\", ' * 5000 + '"}',  # an escaped JSON blob in a string
        "ddcvar." * 20000,  # one long [\w.] run: each "ddcvar." inside it must not rescan the run
        "\\nddcvar." * 20000,  # R87-1: the escape lookbehind must not reopen the run either
        "ddcvar." * 150000,  # R87-1: about 1 MB
        "\\nddcvar." * 120000,
    ],
    ids=["escaped-braces", "escaped-json", "ddcvar-run", "escaped-run", "ddcvar-run-1mb", "escaped-run-1mb"],
)
def test_text_rule_is_linear_on_escapes_and_long_name_runs(text):
    """Verify round 2 (F1, F2): 60-140 KB inputs that took 14 s or more with a quadratic scan."""
    import time

    start = time.perf_counter()
    check_repo.GASP_TEXT_INI_FORMS.search(text)
    assert time.perf_counter() - start < 2.0


# ---- R87-2: the DDCvar branches only when "ddcvar." is in the text ----------------------------------------

SAME_VERDICT_TEXTS = (
    CVAR_NAME_TEXTS_PASS
    + tuple(t for t, _ in CVAR_LIST_FAILS + CVAR_OTHER_FORMS_FAIL)
    + (
        "",
        "[/Script/Engine.DataDrivenConsoleVariableSettings]\n",
        '{"x": 1}\n+CVarsArray=(Name="A")\n',
        'a\n+GameplayTagList=(Tag="A.B")\nDDCvar.X=1\n',  # a section before a key: the first one is shown
        '{"help": "DDCvar.X=1"}\n[ConsoleVariables]\n',
        '{"samples": [1, 2, 3]}\n',
        "DDCVAR.x=1\n",
        "ddcvar\n.x=1\n",
    )
)


@pytest.mark.parametrize("text", SAME_VERDICT_TEXTS)
def test_text_form_matches_the_full_rule(text):
    """_gasp_text_form gives the full rule's first match (same span and shown name) with or without DDCvar."""
    full = check_repo.GASP_TEXT_INI_FORMS.search(text)
    got = check_repo._gasp_text_form(text)
    if full is None:
        assert got is None
    else:
        assert got is not None
        name = got.group(1) if got.re.groups else None
        assert (got.span(), got.group(0), name) == (
            full.span(),
            full.group(0),
            full.group(1),
        )


def test_large_braceless_json_without_ddcvar_is_cheap(repo):
    """R87-2: 4 MB of numbers in one list took about 550 MB with the full rule (its list body is linear)."""
    import time
    import tracemalloc

    rel = "unreal/Golmok/Config/Golmok/samples.json"
    write(repo, rel, '{"samples": [' + "12345, " * 600000 + "0]}\n")
    text = (repo / rel).read_text(encoding="utf-8")
    tracemalloc.start()
    try:
        start = time.perf_counter()
        assert check_repo._gasp_text_form(text) is None
        elapsed = time.perf_counter() - start
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert peak < 64 << 20, peak  # the text is 4 MB; lower() copies it once
    assert elapsed < 2.0
    assert check_repo.check_gasp_guard(repo) == []
