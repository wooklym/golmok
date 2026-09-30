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
    assert error.startswith("unreal/Golmok/Config/DefaultEngine.ini:4: GASP 가드")
    monkeypatch.setattr(check_repo, "GASP_INI_COMMIT_ALLOWED", True)
    assert check_repo.check_gasp_guard(repo) == []


def test_guard_is_registered_and_the_real_repo_passes(capsys):
    assert check_repo.CHECKS["gasp"] is check_repo.check_gasp_guard
    assert check_repo.check_gasp_guard(REPO) == []
    assert check_repo.GASP_INI_COMMIT_ALLOWED is False
