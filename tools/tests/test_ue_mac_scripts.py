"""WP-20 (D-022): tools/ue/*.sh, the Mac ports of tools/ue/*.ps1, checkable without Unreal.

- Text checks mirror test_ue_package_script.py and the add-gasp checks in test_ue_python_gasp_import.py /
  test_ue_wp19_fixture.py for the .ps1 files, plus bash 3.2 rules (macOS system bash) and LF line ends.
- Behaviour tests copy the scripts into a fake checkout and run them against a fake engine tree under a folder
  with spaces ("Epic Games"): stub Build.sh / RunUAT.sh / UnrealEditor-Cmd record their argv (and the add-gasp
  job file), the editor stub writes the automation report or the add-gasp step report. Skipped on Windows.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
UE_DIR = REPO / "tools" / "ue"
SCRIPTS = (
    "common.sh",
    "build.sh",
    "generate-project-files.sh",
    "open-editor.sh",
    "package.sh",
    "test.sh",
    "add-mannequin.sh",
    "add-gasp.sh",
)
posix_only = pytest.mark.skipif(
    sys.platform == "win32" or not shutil.which("bash"), reason="needs POSIX bash"
)


def _read(name: str) -> str:
    return (UE_DIR / name).read_text(encoding="utf-8")


def _code(name: str) -> str:
    """A script without its comment lines (comments mention GOLMOK_PKG_DIR and the old .ps1 names)."""
    return "\n".join(line for line in _read(name).splitlines() if not line.lstrip().startswith("#"))


# --- text checks ---


def test_every_ps1_has_a_bash_port():
    ports = {p.name for p in UE_DIR.glob("*.sh")}
    assert ports == set(SCRIPTS)
    assert {p.stem for p in UE_DIR.glob("*.ps1")} == {Path(n).stem for n in SCRIPTS}


@pytest.mark.parametrize("name", SCRIPTS)
def test_scripts_are_lf_bash32_and_source_common(name):
    raw = (UE_DIR / name).read_bytes()
    assert b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf"), name
    text = raw.decode("utf-8")
    # macOS ships bash 3.2: no associative arrays, mapfile/readarray, case conversion, ;& / |& or coproc.
    bash4 = (
        r"declare\s+-A",
        r"\bmapfile\b",
        r"\breadarray\b",
        r"\$\{[^}]*(,,|\^\^)",
        r";;&",
        r"\|&",
        r"coproc",
    )
    for pattern in bash4:
        assert not re.search(pattern, _code(name)), (name, pattern)
    if name == "common.sh":
        assert "set -euo pipefail" in text
        assert 'UE_ROOT="${UE_ROOT:-/Users/Shared/Epic Games/UE_5.8}"' in text
        assert 'UEEditorApp="$UERoot/Engine/Binaries/Mac/UnrealEditor.app"' in text
        assert 'UEEditor="$UEEditorApp/Contents/MacOS/UnrealEditor"' in text
        assert "DEVELOPER_DIR=" not in text  # honoured as the user set it, never overridden
    else:
        assert text.startswith("#!/bin/bash\n"), name
        assert 'source "$(dirname "${BASH_SOURCE[0]}")/common.sh"' in text, name
        if sys.platform != "win32":
            assert os.access(UE_DIR / name, os.X_OK), f"{name} is not executable"


def test_gitattributes_and_check_repo_cover_sh():
    attrs = (REPO / ".gitattributes").read_text(encoding="utf-8").splitlines()
    assert "*.sh text eol=lf" in attrs
    sys.path.insert(0, str(REPO / "tools" / "scripts"))
    try:
        import check_repo
    finally:
        sys.path.pop(0)
    assert ".sh" in check_repo.TEXT_SUFFIXES and ".ps1" in check_repo.TEXT_SUFFIXES


def test_uproject_targets_windows_and_mac():
    project = json.loads((REPO / "unreal" / "Golmok" / "Golmok.uproject").read_text(encoding="utf-8"))
    assert project["TargetPlatforms"] == ["Windows", "Mac"]


def test_package_env_dir_only_when_outdir_empty():
    code = _code("package.sh")
    match = re.search(r'^if \[ -z "\$OutDir" \]; then\n(.*?)^fi$', code, re.MULTILINE | re.DOTALL)
    assert match, 'package.sh lost its `if [ -z "$OutDir" ]; then ... fi` block'
    block = match.group(1)
    assert '"${GOLMOK_PKG_DIR:-}"' in block and "golmok_trim" in block
    assert 'OutDir="$RepoRoot/build/Mac"' in block
    assert code.count("GOLMOK_PKG_DIR") == block.count("GOLMOK_PKG_DIR")
    assert 'echo "Package output: $OutDir"' in code
    assert code.index('echo "Package output: $OutDir"') > code.index('if [ -z "$OutDir" ]')
    assert '"-archivedirectory=$OutDir"' in code and "-platform=Mac" in code
    assert "must never be distributed (D-021)" in code


def test_add_gasp_script_drives_gasp_import():
    text = _read("add-gasp.sh")
    assert "golmok/gasp_import.py" in text and "GOLMOK_GASP_JOB" in text
    assert "git add -A" in text  # the warning line ("Never `git add -A` ...")
    assert 'GaspProject="$HOME/UE/GASP_58"' in text
    for flag in ("--gasp-project)", "--verify)", "--force)", "--local-files)", "--manifest)"):
        assert flag in text, flag
    for step in ("migrate closure", "relocate migrate_report", "verify content_dir", "local_files local_dir",
                 "manifest migrate_report", "source_content ", "history ", "migrate-last-ok.json",
                 "--untracked-files=all", "ps -axo pid=,comm="):  # fmt: skip
        assert step in text, step
    force = text.index("add-gasp --force never overwrites an install")
    assert force < text.index("migrate closure") and '-e "$ManifestFile"' in text
    assert "*[[:space:]]*)" in text
    assert text.index("add-mannequin.sh first") < text.index("migrate closure")


# --- behaviour tests with a fake engine ---

STUB = """#!{python}
import json, os, shutil, sys
from pathlib import Path

entry = {{"exe": sys.argv[0], "argv": sys.argv[1:]}}
job_path = os.environ.get("GOLMOK_GASP_JOB")
if job_path:
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    entry["job"] = job
    entry["job_bom"] = Path(job_path).read_bytes().startswith(b"\\xef\\xbb\\xbf")
    response = Path(os.environ["FAKE_GASP"]) / (job["step"] + ".json")
    if response.is_file():
        Path(job["result"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(response, job["result"])
for arg in sys.argv[1:]:
    if arg.startswith("-ReportExportPath=") and os.environ.get("FAKE_INDEX"):
        out = Path(arg.split("=", 1)[1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.json").write_bytes(b"\\xef\\xbb\\xbf" + os.environ["FAKE_INDEX"].encode("utf-8"))
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps(entry) + "\\n")
print("noise that the scripts must discard")
sys.exit(int(os.environ.get("FAKE_RC", "0")))
"""


def _stub(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class Env:
    def __init__(self, tmp_path: Path, repo_name: str):
        self.root = tmp_path
        self.repo = tmp_path / repo_name
        ue = self.repo / "tools" / "ue"
        ue.mkdir(parents=True)
        for name in SCRIPTS:
            shutil.copy2(UE_DIR / name, ue / name)
        shutil.copytree(UE_DIR / "gasp", ue / "gasp")
        project = self.repo / "unreal" / "Golmok"
        (project / "Content" / "Python" / "golmok").mkdir(parents=True)
        (project / "Golmok.uproject").write_text("{}", encoding="utf-8")
        self.content = project / "Content"
        self.engine = tmp_path / "Epic Games" / "UE_5.8"
        stub = STUB.format(python=sys.executable)
        mac = self.engine / "Engine" / "Binaries" / "Mac"
        for exe in (
            mac / "UnrealEditor.app" / "Contents" / "MacOS" / "UnrealEditor",
            mac / "UnrealEditor-Cmd",
            self.engine / "Engine" / "Build" / "BatchFiles" / "Mac" / "Build.sh",
            self.engine / "Engine" / "Build" / "BatchFiles" / "RunUAT.sh",
        ):
            _stub(exe, stub)
        self.bin = tmp_path / "bin"
        _stub(self.bin / "open", stub)
        _stub(self.bin / "git", '#!/bin/sh\necho "?? some/untracked.txt"\nexit "${FAKE_GIT_RC:-0}"\n')
        self.log = tmp_path / "log.jsonl"
        self.gasp = tmp_path / "gasp-responses"
        self.gasp.mkdir()
        self.env = {
            "PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}",
            "HOME": str(tmp_path / "home"),
            "UE_ROOT": str(self.engine),
            "GOLMOK_PYTHON": sys.executable,
            "FAKE_LOG": str(self.log),
            "FAKE_GASP": str(self.gasp),
        }

    def run(self, script: str, *args: str, **env: str) -> subprocess.CompletedProcess:
        full = dict(self.env)
        full.update(env)
        return subprocess.run(
            ["bash", str(self.repo / "tools" / "ue" / script), *args],
            env=full,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def run_relative(self, script: str, *args: str, **env: str) -> subprocess.CompletedProcess:
        """Run by a relative path from the repo root (CDPATH makes a bare `cd` print the directory)."""
        full = dict(self.env)
        full.update(env)
        return subprocess.run(
            ["bash", f"tools/ue/{script}", *args],
            env=full,
            cwd=self.repo,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def calls(self) -> list[dict]:
        if not self.log.is_file():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    @property
    def project(self) -> str:
        return str(self.repo / "unreal" / "Golmok" / "Golmok.uproject")

    def respond(self, step: str, **report) -> None:
        (self.gasp / f"{step}.json").write_text(json.dumps(report), encoding="utf-8")


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path, "my golmok")  # a space in the repo path too


@pytest.fixture
def gasp_env(tmp_path):
    e = Env(tmp_path, "golmok")  # add-gasp refuses a repo path with a space
    gasp = tmp_path / "home" / "UE" / "GASP_58"
    (gasp / "Content").mkdir(parents=True)
    (gasp / "GASP_58.uproject").write_text("{}", encoding="utf-8")
    (e.content / "Characters" / "Mannequins").mkdir(parents=True)
    e.gasp_project = gasp
    return e


@posix_only
@pytest.mark.parametrize("name", SCRIPTS)
def test_bash_syntax(name):
    result = subprocess.run(["bash", "-n", str(UE_DIR / name)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@posix_only
def test_missing_engine_fails(env):
    result = env.run("build.sh", UE_ROOT=str(env.root / "nowhere"))
    assert result.returncode == 1
    assert "Unreal Engine not found at" in result.stderr and "Set UE_ROOT" in result.stderr
    assert env.calls() == []


@posix_only
def test_build_passes_config_and_project(env):
    assert env.run("build.sh").returncode == 0
    assert env.run("build.sh", "DebugGame", UE_ROOT=str(env.engine) + "/").returncode == 0
    first, second = env.calls()
    assert first["exe"].endswith("Engine/Build/BatchFiles/Mac/Build.sh")
    assert first["argv"] == ["GolmokEditor", "Mac", "Development", f"-Project={env.project}", "-WaitMutex",
                             "-NoHotReloadFromIDE"]  # fmt: skip
    assert second["argv"][2] == "DebugGame"
    failed = env.run("build.sh", FAKE_RC="5")
    assert failed.returncode == 1 and "Build failed (5)" in failed.stderr
    extra = env.run("build.sh", "Development", "/x")
    assert extra.returncode == 1 and "build: unexpected argument /x" in extra.stderr


@posix_only
def test_relative_path_with_cdpath(env):
    result = env.run_relative("build.sh", CDPATH=f".:{env.root}")
    assert result.returncode == 0, result.stderr
    assert env.calls()[-1]["argv"][3] == f"-Project={env.project}"


@posix_only
def test_generate_project_files(env):
    assert env.run("generate-project-files.sh").returncode == 0
    assert env.calls()[0]["argv"] == ["-ProjectFiles", f"-Project={env.project}", "-Game", "-Progress"]
    failed = env.run("generate-project-files.sh", FAKE_RC="3")
    assert failed.returncode == 1 and "Project file generation failed (3)" in failed.stderr


@posix_only
def test_open_editor_uses_open_without_waiting(env):
    assert env.run("open-editor.sh").returncode == 0
    call = env.calls()[0]
    assert call["exe"] == str(env.bin / "open")
    app = env.engine / "Engine" / "Binaries" / "Mac" / "UnrealEditor.app"
    assert call["argv"] == ["-n", "-a", str(app), "--args", env.project]


def _package_dir(env: Env, *args: str, **extra: str) -> tuple[subprocess.CompletedProcess, str]:
    before = len(env.calls())
    result = env.run("package.sh", *args, **extra)
    argv = env.calls()[before]["argv"] if len(env.calls()) > before else []
    out = [a.split("=", 1)[1] for a in argv if a.startswith("-archivedirectory=")]
    return result, out[0] if out else ""


@posix_only
def test_package_output_dir_rules(env):
    result, out = _package_dir(env)
    assert result.returncode == 0 and out == str(env.repo / "build" / "Mac")
    assert f"Package output: {out}" in result.stdout
    # whitespace-only GOLMOK_PKG_DIR counts as empty
    assert _package_dir(env, GOLMOK_PKG_DIR="  \t ")[1] == str(env.repo / "build" / "Mac")
    # trimmed, trailing slashes removed, spaces inside kept as one argument
    result, out = _package_dir(env, GOLMOK_PKG_DIR="  /Users/me/Golmok Pkg//  ")
    assert out == "/Users/me/Golmok Pkg" and "Package output: /Users/me/Golmok Pkg\n" in result.stdout
    assert _package_dir(env, GOLMOK_PKG_DIR="/")[1] == "/"
    # an explicit --out-dir always wins over the env var, untouched
    assert _package_dir(env, "--out-dir", "/tmp/a b/", GOLMOK_PKG_DIR="/env")[1] == "/tmp/a b/"
    assert _package_dir(env, "Shipping", "--out-dir=/x", GOLMOK_PKG_DIR="/env")[1] == "/x"
    result, out = _package_dir(env, "Shipping", "/tmp/out")  # positional OutDir, as package.ps1 binds it
    assert result.returncode == 0 and out == "/tmp/out"
    assert any(a == "-clientconfig=Shipping" for a in env.calls()[-1]["argv"])
    assert env.run("package.sh", "Shipping", "/a", "/b").returncode == 1
    twice = env.run("package.sh", "Shipping", "--out-dir", "/a", "/b")
    assert twice.returncode == 1 and "output dir given twice" in twice.stderr


@posix_only
def test_package_argv_warning_and_failure(env):
    result, _ = _package_dir(env, "Shipping")
    call = env.calls()[-1]
    assert call["exe"].endswith("Engine/Build/BatchFiles/RunUAT.sh")
    assert call["argv"] == [
        "BuildCookRun", f"-project={env.project}", "-platform=Mac", "-clientconfig=Shipping", "-build",
        "-cook", "-stage", "-pak", "-package", "-archive", f"-archivedirectory={env.repo}/build/Mac",
        "-utf8output", "-ubtargs=-NoHotReloadFromIDE",
    ]  # fmt: skip
    assert "GASP" not in result.stderr
    (env.content / "GASP").mkdir()
    result, _ = _package_dir(env)
    assert "Content/GASP exists" in result.stderr and "(D-021)" in result.stderr
    failed = env.run("package.sh", FAKE_RC="7")
    assert failed.returncode == 1 and "Packaging failed (7)" in failed.stderr
    assert env.run("package.sh", "--bogus").returncode == 1


def _index(succeeded: int, failed: int, not_run: int = 0) -> str:
    return json.dumps({
        "succeeded": succeeded, "failed": failed, "notRun": not_run,
        "tests": [
            {"state": "Success", "fullTestPath": "Golmok.Geo.Wgs84", "entries": []},
            {"state": "Fail", "fullTestPath": "Golmok.Zone.Load",
             "entries": [{"event": {"type": "Error", "message": "골목 zone missing"}}]},
        ],
    })  # fmt: skip


@posix_only
def test_test_runs_headless_and_prints_report(env):
    stale = env.repo / "unreal/Golmok/Saved/Automation/Report/stale.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("old", encoding="utf-8")
    result = env.run("test.sh", FAKE_INDEX=_index(5, 0, 1))
    assert result.returncode == 0, result.stderr
    assert not stale.exists()
    call = env.calls()[0]
    assert call["exe"].endswith("Engine/Binaries/Mac/UnrealEditor-Cmd")
    report = env.repo / "unreal/Golmok/Saved/Automation/Report"
    assert call["argv"] == [
        env.project, "-ExecCmds=Automation RunTests Golmok.;Quit", f"-ReportExportPath={report}",
        "-unattended", "-nullrhi", "-nosplash", "-nopause", "-nosound",
    ]  # fmt: skip
    assert result.stdout.splitlines() == [
        "Success    Golmok.Geo.Wgs84",
        "Fail       Golmok.Zone.Load",
        "    [Error] 골목 zone missing",
        "Succeeded: 5  Failed: 0  Not run: 1",
    ]
    assert "noise" not in result.stdout


@posix_only
def test_test_flags(env):
    flags = ("--filter", "Golmok.Photo", "--setup-dev-level")
    assert env.run("test.sh", *flags, FAKE_INDEX=_index(1, 0)).returncode == 0
    assert env.calls()[-1]["argv"][1] == (
        "-ExecCmds=py import golmok.setup_dev_level as s; s.run(),Automation RunTests Golmok.Photo;Quit"
    )
    assert "-nullrhi" in env.calls()[-1]["argv"]
    assert env.run("test.sh", "--rhi", FAKE_INDEX=_index(1, 0)).returncode == 0
    assert "-nullrhi" not in env.calls()[-1]["argv"] and "" not in env.calls()[-1]["argv"]
    assert env.run("test.sh", FAKE_INDEX=_index(1, 0), GOLMOK_TEST_RHI="1").returncode == 0
    assert "-nullrhi" not in env.calls()[-1]["argv"]
    assert env.run("test.sh", FAKE_INDEX=_index(1, 0), GOLMOK_TEST_RHI="0").returncode == 0
    assert "-nullrhi" in env.calls()[-1]["argv"]
    assert env.run("test.sh", "--bogus").returncode == 1


@posix_only
def test_test_exit_rules(env):
    # the editor's own exit code is ignored; the report decides
    assert env.run("test.sh", FAKE_INDEX=_index(3, 0), FAKE_RC="9").returncode == 0
    failed = env.run("test.sh", FAKE_INDEX=_index(3, 1))
    assert failed.returncode == 1 and "Automation tests failed" in failed.stderr
    assert "Succeeded: 3  Failed: 1  Not run: 0" in failed.stdout
    assert env.run("test.sh", FAKE_INDEX=_index(0, 0)).returncode == 1
    missing = env.run("test.sh")
    assert missing.returncode == 1 and "No automation report at" in missing.stderr


@posix_only
def test_add_mannequin(env):
    source = env.engine / "Templates/TemplateResources/High/Characters/Content"
    missing = env.run("add-mannequin.sh")
    assert missing.returncode == 1 and "Mannequin pack not found" in missing.stderr
    (source / "Mannequins" / "Meshes").mkdir(parents=True)
    (source / "Mannequins" / "Meshes" / "SKM_Manny.uasset").write_text("x", encoding="utf-8")
    first = env.run("add-mannequin.sh")
    assert first.returncode == 0 and "Copied mannequin pack to" in first.stdout
    assert (env.content / "Characters/Mannequins/Meshes/SKM_Manny.uasset").is_file()
    again = env.run("add-mannequin.sh")
    assert again.returncode == 0 and "Already present:" in again.stdout


def _jobs(env: Env) -> list[dict]:
    return [c["job"] for c in env.calls() if "job" in c]


@posix_only
def test_add_gasp_refuses_repo_path_with_space(env):
    result = env.run("add-gasp.sh", "--verify")
    assert result.returncode == 1 and "the repository path has a space" in result.stderr
    assert env.calls() == []


@posix_only
def test_add_gasp_verify_only(gasp_env):
    e = gasp_env
    e.respond("verify", ok=True, messages=["27 DDCvars", "39 tags"], package_count=812, digest="abc",
              source_package_count=812, source_digest="def")  # fmt: skip
    result = e.run("add-gasp.sh", "--verify")
    assert result.returncode == 0, result.stderr
    work = e.repo / "unreal/Golmok/Saved/Golmok/add-gasp"
    (job,) = _jobs(e)
    assert job == {
        "step": "verify", "content_dir": str(e.content),
        "local_dir": str(e.repo / "unreal/Golmok/Config/Golmok/local"),
        "tags_ini": str(e.repo / "unreal/Golmok/Config/Tags/GASP.ini"),
        "expected": str(e.repo / "tools/ue/gasp/expected.json"), "git_status": str(work / "git-status.txt"),
        "result": str(work / "verify.json"),
    }  # fmt: skip
    assert not e.calls()[0]["job_bom"]
    argv = e.calls()[0]["argv"]
    assert argv[0] == e.project and argv[1] == "-ExecutePythonScript=" + str(
        e.content / "Python/golmok/gasp_import.py"
    )
    assert argv[2:] == ["-unattended", "-nullrhi", "-nosplash", "-nopause", "-nosound"]
    assert (work / "git-status.txt").read_text(encoding="utf-8") == "?? some/untracked.txt\n"
    assert "    27 DDCvars\n    39 tags\n" in result.stdout
    summary = "add-gasp verify: 812 packages, digest abc, source 812 packages, source_digest def"
    assert summary in result.stdout
    e.respond("verify", ok=False, messages=["leak"])
    failed = e.run("add-gasp.sh", "--verify")
    assert failed.returncode == 1 and "add-gasp: verify failed" in failed.stderr
    git_failed = e.run("add-gasp.sh", "--verify", FAKE_GIT_RC="128")
    assert git_failed.returncode == 1 and "git status failed (128" in git_failed.stderr
    e.respond("verify", ok=True, messages=[], package_count=1, digest="a", source_package_count=1,
              source_digest="b")  # fmt: skip
    relative = e.run_relative("add-gasp.sh", "--verify", CDPATH=f".:{e.root}")
    assert relative.returncode == 0, relative.stderr
    assert e.calls()[-1]["job"]["content_dir"] == str(e.content)
    (e.gasp / "verify.json").unlink()
    none = e.run("add-gasp.sh", "--verify")
    assert none.returncode == 1 and "verify wrote no result" in none.stderr


@posix_only
def test_add_gasp_install_flow(gasp_env):
    e = gasp_env
    e.respond("migrate", ok=True, messages=["migrated"], source_package_count=812, migrated=["a", "b", "c"],
              source_digest="s1")  # fmt: skip
    e.respond("relocate", ok=True, messages=[], exit=0)
    e.respond("verify", ok=True, messages=[], package_count=812, digest="d", source_package_count=812,
              source_digest="s1")  # fmt: skip
    result = e.run("add-gasp.sh")
    assert result.returncode == 0, result.stderr
    work = e.repo / "unreal/Golmok/Saved/Golmok/add-gasp"
    migrate, relocate, verify = _jobs(e)
    gasp = str(e.gasp_project)
    assert migrate == {
        "step": "migrate", "closure": str(e.repo / "tools/ue/gasp/closure.json"),
        "dest_content": str(e.content),
        "source_content": gasp + "/Content", "history": str(work / "migrated-history.json"),
        "result": str(work / "migrate.json"),
    }  # fmt: skip
    assert e.calls()[0]["argv"][0] == gasp + "/GASP_58.uproject"
    assert relocate["step"] == "relocate" and relocate["migrate_report"] == str(work / "migrate.json")
    assert relocate["gasp_project"] == gasp and set(relocate) == {
        "step", "migrate_report", "content_dir", "local_dir", "tags_ini", "gasp_project", "result"
    }  # fmt: skip
    assert verify["step"] == "verify" and e.calls()[1]["argv"][0] == e.project
    assert (work / "migrate-last-ok.json").is_file()
    assert "add-gasp migrate: 812 closure packages, 3 copied, source_digest s1" in result.stdout

    e.log.unlink()
    e.respond("relocate", ok=True, messages=["rename failed"], exit=2)
    two = e.run("add-gasp.sh", "--force")
    assert two.returncode == 2 and "GASP stays at the Migrate paths" in two.stderr
    assert [j["step"] for j in _jobs(e)] == ["migrate", "relocate"]


@posix_only
def test_add_gasp_install_guards(gasp_env):
    e = gasp_env
    e.respond("verify", ok=True, messages=[])
    local = e.repo / "unreal/Golmok/Config/Golmok/local"
    local.mkdir(parents=True)
    (local / "gasp_manifest.json").write_text("{}", encoding="utf-8")
    installed = e.run("add-gasp.sh")
    assert installed.returncode == 0 and "Already installed (" in installed.stdout
    assert [j["step"] for j in _jobs(e)] == ["verify"]
    (e.content / "GASP").mkdir()
    assert "Already installed: " in e.run("add-gasp.sh").stdout
    e.log.unlink()
    force = e.run("add-gasp.sh", "--force")
    assert force.returncode == 1 and "add-gasp --force never overwrites an install" in force.stderr
    assert e.calls() == []
    (e.content / "GASP").rmdir()
    shutil.rmtree(e.content / "Characters")
    mannequin = e.run("add-gasp.sh", "--force")
    assert mannequin.returncode == 1 and "add-mannequin.sh first" in mannequin.stderr
    assert e.calls() == []
    no_project = e.run("add-gasp.sh", "--gasp-project", str(e.root / "empty"))
    assert no_project.returncode == 1 and "No .uproject in" in no_project.stderr


@posix_only
def test_add_gasp_local_files_and_manifest(gasp_env):
    e = gasp_env
    e.respond("local_files", ok=True, messages=["tags written"])
    e.respond("manifest", ok=True, messages=[])
    e.respond("verify", ok=True, messages=[])
    assert e.run("add-gasp.sh", "--local-files").returncode == 0
    assert e.run("add-gasp.sh", "--manifest", "--gasp-project", str(e.gasp_project) + "/").returncode == 0
    local_files, _, manifest, _ = _jobs(e)
    assert set(local_files) == {"step", "local_dir", "tags_ini", "gasp_project", "result"}
    assert set(manifest) == {"step", "migrate_report", "content_dir", "local_dir", "gasp_project", "result"}
    assert manifest["migrate_report"].endswith("add-gasp/migrate-last-ok.json")
    assert manifest["gasp_project"] == str(e.gasp_project)
    e.respond("local_files", ok=False, messages=[])
    failed = e.run("add-gasp.sh", "--local-files")
    assert failed.returncode == 1 and "local_files failed" in failed.stderr


@posix_only
def test_add_gasp_refuses_while_an_editor_runs(gasp_env, tmp_path):
    e = gasp_env
    sleep = shutil.which("sleep")
    assert sleep
    fake = tmp_path / "Golmok.uproject.d" / "UnrealEditor"  # the command line then contains "Golmok.uproject"
    fake.parent.mkdir()
    # ps reports the symlink path as the executable (a copied macOS system binary may not run)
    fake.symlink_to(sleep)
    proc = subprocess.Popen([str(fake), "30"])
    try:
        time.sleep(0.3)
        if proc.poll() is not None:
            pytest.skip("the sleep symlink does not run here")
        result = e.run("add-gasp.sh", "--verify")
        assert result.returncode == 1
        assert f"close the Unreal Editor first (running: {proc.pid}" in result.stderr
        assert e.calls() == []
    finally:
        proc.kill()
        proc.wait()
