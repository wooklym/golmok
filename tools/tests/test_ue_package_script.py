"""tools/ue/package.ps1 output path (C-07), checkable without Unreal or PowerShell.

- The param line and its defaults are unchanged (-Config Development, -OutDir empty).
- $env:GOLMOK_PKG_DIR is read only inside the `if (-not $OutDir)` branch, so an explicit -OutDir always wins;
  a whitespace-only value counts as empty and falls back to <repo>\\build\\Windows.
- The chosen directory is printed and handed to BuildCookRun as -archivedirectory.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKAGE_PS1 = REPO / "tools" / "ue" / "package.ps1"


def _code() -> str:
    """package.ps1 without comment lines (the C-07 comment mentions GOLMOK_PKG_DIR too)."""
    text = PACKAGE_PS1.read_text(encoding="utf-8")
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def _outdir_block(code: str) -> str:
    match = re.search(r"^if \(-not \$OutDir\) \{\n(.*?)^\}", code, re.MULTILINE | re.DOTALL)
    assert match, "package.ps1 lost its `if (-not $OutDir) { ... }` block"
    return match.group(1)


def test_param_interface_unchanged() -> None:
    assert 'param([string]$Config = "Development", [string]$OutDir = "")' in _code()


def test_env_dir_only_when_outdir_empty() -> None:
    code = _code()
    block = _outdir_block(code)
    assert "[string]::IsNullOrWhiteSpace($env:GOLMOK_PKG_DIR)" in block
    assert "$OutDir = $env:GOLMOK_PKG_DIR" in block
    assert 'Join-Path $RepoRoot "build\\Windows"' in block
    # the env var is not read anywhere else, so an explicit -OutDir is never overridden
    assert code.count("GOLMOK_PKG_DIR") == block.count("GOLMOK_PKG_DIR")


def test_chosen_dir_printed_and_used() -> None:
    code = _code()
    assert 'Write-Host "Package output: $OutDir"' in code
    assert code.index('Write-Host "Package output: $OutDir"') > code.index("if (-not $OutDir)")
    assert '"-archivedirectory=$OutDir"' in code
