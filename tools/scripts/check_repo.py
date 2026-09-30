"""Repository sanity checks (standard library only). Run from anywhere:

    python tools/scripts/check_repo.py [--root <repo>]

Checks:
    - unreal/Golmok/Golmok.uproject parses as JSON and EngineAssociation == "5.8"
    - unreal/Golmok/Config/*.ini parse (Unreal style: duplicate keys, +/-/./! prefixed keys)
    - unreal/Golmok/Config/Golmok/**/*.json and docs/**/*.json parse
    - relative links in docs/**/*.md, README.md, CLAUDE.md, tools/README.md point to existing files
    - .gitattributes puts *.uasset and *.umap in Git LFS
    - no merge conflict markers (<<<<<<< / >>>>>>>) left in text files

Every failure is printed; exit code 1 if there was any.
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ENGINE_ASSOCIATION = "5.8"
UPROJECT = Path("unreal/Golmok/Golmok.uproject")
CONFIG_DIR = Path("unreal/Golmok/Config")
LFS_PATTERNS = ("*.uasset", "*.umap")
DOC_GLOBS = ("docs/**/*.md", "README.md", "CLAUDE.md", "tools/README.md")

# [text](target) and ![alt](target); target may be <...> and may carry a "title"
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+[\"'(][^)]*)?\)")
# [label]: target
REF_LINK = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]*>|\S+)", re.MULTILINE)
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`+[^`]*`+")
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")

# A bare "=======" is also a markdown heading underline, so only the two outer markers count.
CONFLICT_MARKER = re.compile(r"^(<{7}|>{7})( |$)", re.MULTILINE)
TEXT_SUFFIXES = {
    ".md", ".py", ".toml", ".ini", ".cpp", ".h", ".cs", ".ps1", ".bat", ".yml", ".yaml",
    ".json", ".js", ".mjs", ".html", ".css", ".uproject", ".txt",
}  # fmt: skip
TEXT_NAMES = {".gitignore", ".gitattributes", ".editorconfig"}
# Generated/vendored folders, and .claude (local worktrees hold other copies of the repo).
SKIP_DIRS = {
    ".git", ".claude", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache",
    "Binaries", "Intermediate", "Saved", "DerivedDataCache",
}  # fmt: skip


def check_uproject(root: Path) -> list[str]:
    path = root / UPROJECT
    if not path.is_file():
        return [f"{UPROJECT}: 파일 없음"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return [f"{UPROJECT}: JSON 파싱 실패: {e}"]
    got = data.get("EngineAssociation") if isinstance(data, dict) else None
    if got != ENGINE_ASSOCIATION:
        return [f"{UPROJECT}: EngineAssociation {got!r} != {ENGINE_ASSOCIATION!r}"]
    return []


def parse_ue_ini(text: str) -> configparser.RawConfigParser:
    """Parse an Unreal config file. Raises configparser.Error on malformed input."""
    cp = configparser.RawConfigParser(
        strict=False,  # UE repeats keys (+Array=..., -Array=...) and may repeat sections
        interpolation=None,
        delimiters=("=",),
        comment_prefixes=(";", "#"),
        inline_comment_prefixes=None,
        allow_no_value=True,
        empty_lines_in_values=False,
    )
    cp.optionxform = str  # keep key case and the +/-/./! prefixes as-is
    cp.read_string(text)
    return cp


def check_ini(root: Path) -> list[str]:
    errors = []
    config_dir = root / CONFIG_DIR
    files = sorted(config_dir.glob("*.ini"))
    if not files:
        return [f"{CONFIG_DIR}: .ini 파일 없음"]
    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            parse_ue_ini(path.read_text(encoding="utf-8-sig"))
        except (configparser.Error, UnicodeDecodeError) as e:
            errors.append(f"{rel}: ini 파싱 실패: {e}")
    return errors


def check_json(root: Path) -> list[str]:
    errors = []
    paths = sorted(
        set((root / CONFIG_DIR / "Golmok").glob("**/*.json")) | set((root / "docs").glob("**/*.json"))
    )
    for path in paths:
        rel = path.relative_to(root).as_posix()
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            errors.append(f"{rel}: JSON 파싱 실패: {e}")
    return errors


def iter_links(text: str):
    """Yield (line_no, target) for markdown links outside fenced code blocks and inline code."""
    in_fence = False
    for no, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = INLINE_CODE.sub("", line)
        for m in INLINE_LINK.finditer(line):
            yield no, m.group(1)
        for m in REF_LINK.finditer(line):
            yield no, m.group(1)


def resolve_link(root: Path, doc: Path, target: str) -> Path | None:
    """Local file a link points to, or None for external URLs and same-page anchors.

    A leading "/" is repository-root relative (GitHub rendering).
    """
    target = target.strip("<>").strip()
    if not target or target.startswith("#") or SCHEME.match(target) or target.startswith("//"):
        return None
    target = unquote(target.split("#", 1)[0].split("?", 1)[0])
    if not target:
        return None
    return root / target.lstrip("/") if target.startswith("/") else doc.parent / target


def check_links(root: Path, globs: tuple[str, ...] = DOC_GLOBS) -> list[str]:
    errors = []
    docs = sorted({p for g in globs for p in root.glob(g) if p.is_file()})
    for doc in docs:
        rel = doc.relative_to(root).as_posix()
        for no, target in iter_links(doc.read_text(encoding="utf-8")):
            path = resolve_link(root, doc, target)
            if path is not None and not path.exists():
                errors.append(f"{rel}:{no}: 깨진 링크 {target}")
    return errors


def check_gitattributes(root: Path) -> list[str]:
    path = root / ".gitattributes"
    if not path.is_file():
        return [".gitattributes: 파일 없음"]
    lfs = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts and not parts[0].startswith("#") and "filter=lfs" in parts[1:]:
            lfs.add(parts[0])
    return [
        f".gitattributes: {p} 가 Git LFS(filter=lfs)로 지정돼 있지 않음" for p in LFS_PATTERNS if p not in lfs
    ]


def check_conflict_markers(root: Path) -> list[str]:
    errors = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.suffix.lower() not in TEXT_SUFFIXES and name not in TEXT_NAMES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            rel = path.relative_to(root).as_posix()
            for m in CONFLICT_MARKER.finditer(text):
                no = text.count("\n", 0, m.start()) + 1
                errors.append(f"{rel}:{no}: 병합 충돌 표시 {m.group(1)}")
    return errors


# [WP-19 hook] GASP repository guard (D-021, Fab EULA section 5(a); WP-19 design section 9; WP-19a-2 R76 T3).
# GASP_INI_COMMIT_ALLOWED (owner fact check R21-11-3) controls every GASP ini rule: DDCvar / gameplay-tag text
# in any committable Config/**/*.ini, Config/Tags/*.ini outside GASP_TAGS_ALLOWED, DefaultGameplayTags.ini.
# The add-gasp outputs (Config/Golmok/local/, Config/Tags/GASP*.ini) and GASP content stay local regardless.
# Path rules compare lower case; golmok.gasp_pure.is_local_only applies the same path rules to git status
# (tools/tests/test_check_repo_gasp.py runs both over one table).
GASP_INI_COMMIT_ALLOWED = False
GASP_CONTENT = "unreal/golmok/content/"
GASP_TRACKED_CONTENT = ("unreal/golmok/content/golmok/", "unreal/golmok/content/python/")
GASP_PACKAGE_CONTENT = "unreal/golmok/content/golmok/"  # the only place for a committed .uasset / .umap
GASP_LOCAL_FOLDERS = ("gasp", "golmoklocal")  # never committed, wherever they sit under Content
GASP_LOCAL_ONLY = ("unreal/golmok/config/golmok/local/",)
GASP_ADD_GASP_TAGS = re.compile(r"^unreal/golmok/config/tags/gasp[^/]*\.ini$")
GASP_TAGS_DIR = "unreal/golmok/config/tags/"
GASP_TAGS_ALLOWED: tuple[str, ...] = ()
GASP_TAGS_FILE = "unreal/golmok/config/defaultgameplaytags.ini"
GASP_CONFIG_INI = re.compile(r"^unreal/golmok/config/.+\.ini$")
GASP_INI_TEXT = re.compile(
    r"DataDrivenConsoleVariableSettings|CVarsArray|ddcvar\.|GameplayTagList", re.IGNORECASE
)


def _git_paths(root: Path, *args: str) -> list[str] | None:
    """`git -C root <args>` output split on NUL / newlines, or None when git is missing or fails."""
    import subprocess

    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    except OSError:
        return None
    if done.returncode != 0:
        return None
    text = done.stdout.decode("utf-8", "replace")
    return [p for p in (text.split("\0") if "\0" in text else text.splitlines()) if p]


def _gasp_path_rule(path: str) -> str | None:
    """Why a repository path must never be committed (lower-case path rules), else None."""
    low = path.lower()
    parts = low.split("/")
    if low.endswith((".uasset", ".umap")) and not low.startswith(GASP_PACKAGE_CONTENT):
        return ".uasset / .umap는 Content/Golmok/ 안에만 커밋한다"
    if low.startswith(GASP_CONTENT):
        if not low.startswith(GASP_TRACKED_CONTENT):
            return "Content/ 루트에는 Golmok/·Python/만 커밋한다"
        if any(part in GASP_LOCAL_FOLDERS for part in parts[3:-1]):
            return "GASP·GolmokLocal 폴더는 로컬 전용이다"
    if low.startswith(GASP_LOCAL_ONLY) or GASP_ADD_GASP_TAGS.match(low):
        return "로컬 전용 파일(add-gasp)이다"
    if not GASP_INI_COMMIT_ALLOWED:
        if low.startswith(GASP_TAGS_DIR) and low.endswith(".ini") and low not in GASP_TAGS_ALLOWED:
            return "Config/Tags/*.ini는 허용 목록 밖이면 커밋하지 않는다(R21-11-3)"
        if low == GASP_TAGS_FILE:
            return "DefaultGameplayTags.ini는 로컬 전용이다(R21-11-3)"
    return None


def check_gasp_guard(root: Path) -> list[str]:
    top = _git_paths(root, "rev-parse", "--show-toplevel")
    if top is None and (root / ".git").exists():
        return [
            "gasp: git 실행 실패(git rev-parse) — PATH·safe.directory를 확인한다(GASP 가드를 건너뛰지 않는다)"
        ]
    if not top or Path(top[0].strip()).resolve() != root.resolve():
        return []  # not the top of a git work tree (e.g. the synthetic repos of test_check_repo.py): skipped
    tracked = _git_paths(root, "ls-files", "-z")
    addable = _git_paths(root, "ls-files", "--others", "--exclude-standard", "-z")
    if tracked is None or addable is None:
        return [
            "gasp: git 실행 실패(git ls-files) — PATH·safe.directory를 확인한다(GASP 가드를 건너뛰지 않는다)"
        ]
    errors = []
    for state, paths in (("추적 중", tracked), ("추가 가능", addable)):
        for path in paths:
            rule = _gasp_path_rule(path)
            if rule:
                errors.append(f"{path}: GASP 가드 — {rule} ({state})")
            elif not GASP_INI_COMMIT_ALLOWED and GASP_CONFIG_INI.match(path.lower()):
                file = root / path
                text = file.read_text(encoding="utf-8-sig", errors="replace") if file.is_file() else ""
                m = GASP_INI_TEXT.search(text)
                if m:
                    no = text.count("\n", 0, m.start()) + 1
                    errors.append(
                        f"{path}:{no}: GASP 가드 — GASP DDCvar·태그 텍스트({m.group(0)})는 커밋하지 않는다"
                    )
    return errors


# [/WP-19 hook]


CHECKS = {
    "uproject": check_uproject,
    "ini": check_ini,
    "json": check_json,
    "links": check_links,
    "gitattributes": check_gitattributes,
    "conflicts": check_conflict_markers,
    "gasp": check_gasp_guard,  # [WP-19 hook]
}


def run(root: Path) -> list[str]:
    errors = []
    for check in CHECKS.values():
        errors.extend(check(root))
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2], help="저장소 루트")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    errors = run(root)
    for e in errors:
        print(f"FAIL {e}")
    if errors:
        print(f"\n{len(errors)}개 실패")
        return 1
    print(f"OK ({', '.join(CHECKS)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
