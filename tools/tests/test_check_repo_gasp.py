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
