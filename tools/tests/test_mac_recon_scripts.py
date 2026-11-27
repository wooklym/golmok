"""WP-21 (D-022): tools/mac/install-recon-tools.sh and tools/mac/recon-smoke.sh, checkable without the tools.

- Text checks: LF, bash 3.2 (macOS system bash), pinned official downloads with sha256, the GPL-free
  conda-forge variants (COLMAP cpu_lgpl, ffmpeg/libheif lgpl), no sudo/Homebrew/Gatekeeper changes, none of
  the D-002 banned tools, and the COLMAP → undistort → Brush order (Brush ignores lens distortion).
- Behaviour: `bash -n`, and the guards that stop before anything is downloaded or written (usage, folders
  inside the repo, missing tools, non-Mac host). Skipped on Windows.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
MAC_DIR = REPO / "tools" / "mac"
INSTALL = MAC_DIR / "install-recon-tools.sh"
SMOKE = MAC_DIR / "recon-smoke.sh"
SCRIPTS = (INSTALL, SMOKE)
posix_only = pytest.mark.skipif(
    sys.platform == "win32" or not shutil.which("bash"), reason="needs POSIX bash"
)
BASH = "/bin/bash" if Path("/bin/bash").exists() else "bash"


def _code(path: Path) -> str:
    """The script without comment lines."""
    return "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#")
    )


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_scripts_are_lf_bash32_strict(path):
    raw = path.read_bytes()
    assert b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf"), path.name
    text = raw.decode("utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text
    assert "WP-21" in text and "D-022" in text
    code = _code(path)
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
        assert not re.search(pattern, code), (path.name, pattern)
    # bash 3.2 cannot parse a case statement inside $( … ); keep case blocks out of command substitutions.
    for block in re.findall(r"\$\(\n(.*?)\n\s*\)\"", code, flags=re.S):
        assert not re.search(r"\bcase\b", block), path.name


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_no_sudo_brew_gatekeeper_or_banned_tools(path):
    code = _code(path)
    for word in ("sudo", "brew ", "spctl --master-disable", "xattr -d", "xattr -c"):
        assert word not in code, (path.name, word)
    lowered = path.read_text(encoding="utf-8").lower()
    for banned in ("opensplat", "gsplat-mps", "openmvs", "ultralytics", "mast3r", "dust3r"):
        assert banned not in lowered, (path.name, banned)


def test_install_pins_official_sources_and_lgpl_variants():
    code = _code(INSTALL)
    assert 'PREFIX="${1:-${GOLMOK_TOOLS_PREFIX:-$HOME/golmok-tools}}"' in code
    assert re.search(r'MICROMAMBA_SHA256="[0-9a-f]{64}"', code)
    assert re.search(r'BRUSH_SHA256="[0-9a-f]{64}"', code)
    assert (
        "https://github.com/mamba-org/micromamba-releases/releases/download/$MICROMAMBA_VERSION/micromamba-osx-arm64"
        in code
    )
    assert "https://github.com/ArthurBrussee/brush/releases/download/$BRUSH_VERSION/$BRUSH_ASSET" in code
    assert 'BRUSH_ASSET="brush-app-aarch64-apple-darwin.tar.xz"' in code
    urls = re.findall(r"https?://[^\s\"']+", code)
    assert urls and all(u.startswith("https://github.com/") for u in urls), urls
    specs = re.search(r'RECON_SPECS="([^"]+)"', code).group(1).split()
    assert "colmap=4.2.1=cpu_lgpl*" in specs
    assert any(s.startswith("ffmpeg=") and s.endswith("=lgpl*") for s in specs)
    assert "libheif=*=lgpl*" in specs
    assert "-c conda-forge --override-channels" in code
    assert 'die "GPL-only packages' in code
    assert "recon-explicit.txt" in code and "--explicit" in code
    # Downloads are verified every run, and the prefix can never be inside the checkout.
    assert 'die "sha256 mismatch' in code
    assert 'die "PREFIX must be outside the repo' in code


def test_smoke_runs_cpu_colmap_then_undistort_then_brush_then_repo_postprocess():
    code = _code(SMOKE)
    order = [
        "feature_extractor",
        "_matcher",
        " mapper ",
        "global_mapper",
        "image_undistorter",
        '"$BRUSH" "$WORK/undistorted"',
        '"$SPLAT_CLI" inspect',
        '"$SPLAT_CLI" clean',
        '"$SPLAT_CLI" tiles',
    ]
    positions = [code.index(token) for token in order]
    assert positions == sorted(positions), dict(zip(order, positions, strict=True))
    assert "--FeatureExtraction.use_gpu 0" in code
    assert "--FeatureMatching.use_gpu 0" in code
    assert "--GlobalMapper.gp_use_gpu 0" in code
    assert "--output_type COLMAP" in code
    assert "patch_match_stereo" not in code  # dense MVS needs CUDA; not part of the Mac smoke
    assert '"$BRUSH" "$WORK/undistorted"' in code
    assert "--total-steps" in code and "--export-path" in code
    assert "/usr/bin/time -l" in code
    assert 'die "work folder must be outside the repo' in code
    assert "$HOME/golmok_data/recon-smoke/sfm-splat/" in code


@posix_only
@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_bash_syntax(path):
    result = subprocess.run([BASH, "-n", str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def _run(args: list[str], env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("GOLMOK_TOOLS_PREFIX", None)
    env.update(env_extra or {})
    return subprocess.run([BASH, *args], capture_output=True, text=True, env=env, timeout=60)


@posix_only
def test_smoke_usage_and_guards(tmp_path):
    result = _run([str(SMOKE)])
    assert result.returncode != 0 and "usage: recon-smoke.sh" in result.stderr

    result = _run([str(SMOKE), str(tmp_path / "missing")])
    assert result.returncode != 0 and "no such folder" in result.stderr

    images = tmp_path / "images"
    images.mkdir()
    inside = REPO / "tools" / "mac" / "should-not-exist"
    result = _run([str(SMOKE), str(images), str(inside)])
    assert result.returncode != 0 and "outside the repo" in result.stderr
    assert not inside.exists()

    work = tmp_path / "work"
    result = _run([str(SMOKE), str(images), str(work)], {"GOLMOK_TOOLS_PREFIX": str(tmp_path / "no-tools")})
    assert result.returncode != 0 and "install-recon-tools.sh" in result.stderr
    assert not work.exists()


@posix_only
def test_install_refuses_repo_prefix_or_non_mac(tmp_path):
    inside = REPO / "tools" / "mac" / "should-not-exist"
    result = _run([str(INSTALL), str(inside)])
    assert result.returncode != 0
    if sys.platform == "darwin" and os.uname().machine == "arm64":
        assert "outside the repo" in result.stderr
    elif sys.platform != "darwin":
        assert "macOS only" in result.stderr
    assert not inside.exists()


def _fake_repo(tmp_path: Path) -> Path:
    """A copy of the repo layout (tools/mac/*.sh) so the guards can be hit with relative paths safely."""
    fake = tmp_path / "fake repo"
    (fake / "tools" / "mac").mkdir(parents=True)
    for path in SCRIPTS:
        shutil.copy2(path, fake / "tools" / "mac" / path.name)
    return fake


def _run_in(
    cwd: Path, args: list[str], env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("GOLMOK_TOOLS_PREFIX", None)
    env.update(env_extra or {})
    return subprocess.run([BASH, *args], capture_output=True, text=True, env=env, cwd=cwd, timeout=60)


def _tree(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*")}


@posix_only
def test_smoke_refuses_relative_dotdot_case_and_symlink_work_paths(tmp_path):
    fake = _fake_repo(tmp_path)
    images = tmp_path / "images"
    images.mkdir()
    (tmp_path / "link").symlink_to(fake)
    before = _tree(fake)
    smoke = "tools/mac/recon-smoke.sh"
    cases = [
        (fake, "out rel"),
        (fake / "tools", "../out2"),
        (fake / "tools", f"../../{fake.name}/out3"),
        (tmp_path, str(tmp_path / "link" / "out4")),
        (tmp_path, str(fake).upper() + "/out5" if sys.platform == "darwin" else str(fake / "out5")),
    ]
    for cwd, work in cases:
        script = str(fake / smoke)
        result = _run_in(
            cwd, [script, str(images), work], {"GOLMOK_TOOLS_PREFIX": str(tmp_path / "no-tools")}
        )
        assert result.returncode != 0 and "outside the repo" in result.stderr, (work, result.stderr)
    # a tail that does not exist yet may not use . or .. (it could not be resolved exactly)
    result = _run_in(fake, [str(fake / smoke), str(images), "new/../x"])
    assert result.returncode != 0 and "without . or .." in result.stderr
    assert _tree(fake) == before


@posix_only
@pytest.mark.skipif(
    not (sys.platform == "darwin" and os.uname().machine == "arm64"), reason="Apple Silicon guard"
)
def test_install_refuses_relative_or_dotdot_prefix_inside_repo(tmp_path):
    fake = _fake_repo(tmp_path)
    before = _tree(fake)
    install = str(fake / "tools" / "mac" / "install-recon-tools.sh")
    for cwd, prefix in [
        (fake, "golmok-tools-rel"),
        (fake / "tools", f"../../{fake.name}/x2"),
        (fake, "./x3"),
    ]:
        result = _run_in(cwd, [install, prefix])
        assert result.returncode != 0 and "outside the repo" in result.stderr, (prefix, result.stderr)
    assert _tree(fake) == before
