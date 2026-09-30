"""WP-19 (D-021) GASP setup plan, manifest and local config files; usable without Unreal (design section 8).

tools/ue/add-gasp.ps1 drives golmok.gasp_import (the thin `unreal` adapter) in three headless editor
sessions: migrate (in the GASP project), relocate + local files (in Golmok) and verify (in Golmok). Everything
that can be computed without the editor lives here (tools/tests/test_ue_python_gasp_import.py).

Nothing written here is committed: Content/GASP, Config/Golmok/local/ and Config/Tags/GASP*.ini are ignored
(.gitignore [WP-19 hook]) and tools/scripts/check_repo.py fails when one of them becomes committable (Fab EULA
section 5(a); GASP ini text stays local until the owner confirms it may be committed, R21-11-3).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[3]
CONTENT = PROJECT / "Content"
CONFIG = PROJECT / "Config"
ANIMATION_JSON = CONFIG / "Golmok" / "animation.json"
LOCAL_DIR = CONFIG / "Golmok" / "local"
MANIFEST = LOCAL_DIR / "gasp_manifest.json"
DDCVARS = LOCAL_DIR / "gasp_ddcvars.json"
TAGS_INI = CONFIG / "Tags" / "GASP.ini"

CONTENT_ROOTS = ("/Game/GASP", "/Game")
EXPECTED_DDCVARS = 27  # V-08: DataDrivenConsoleVariableSettings +CVarsArray lines of GASP 5.8
EXPECTED_TAGS = 39  # V-08: +GameplayTagList lines of GASP 5.8
PACKAGE_EXTENSIONS = (".uasset", ".umap")
DDCVAR_SECTION = "/Script/Engine.DataDrivenConsoleVariableSettings"
TAGS_SECTION = "/Script/GameplayTags.GameplayTagsSettings"
TAGS_LIST_SECTION = "/Script/GameplayTags.GameplayTagsList"
CVAR_TYPES = {"CVarInt": "int", "CVarFloat": "float", "CVarBool": "bool"}
# UE long package names: any character but "/" and INVALID_LONGPACKAGE_CHARACTERS (backslash : * ? " < > | '
# space , . & ! ~ newline CR tab @ #), so "/Game/Audio/Foley-Step_01" or non-ASCII names are packages too
# (review R76 T4).
INVALID_PACKAGE_CHARS = "\\:*?\"<>|' ,.&!~\n\r\t@#"
PACKAGE_RE = re.compile(r"/Game(/[^/" + re.escape(INVALID_PACKAGE_CHARS) + r"]+)+")
MIGRATE_ROOT = "/Game/GASP"
MANNEQUIN_PACK = "/Game/Characters/Mannequins/"  # tools/ue/add-mannequin.ps1
# Repository guard: the path rules of tools/scripts/check_repo.py check_gasp_guard, in lower case
# (tools/tests/test_check_repo_gasp.py runs both over one table). Only Content/Golmok and Content/Python are
# committable under Content; .uasset / .umap only inside Content/Golmok, never in a GASP / GolmokLocal folder.
GUARD_CONTENT = "unreal/golmok/content/"
TRACKED_CONTENT = ("unreal/golmok/content/golmok/", "unreal/golmok/content/python/")
PACKAGE_CONTENT = "unreal/golmok/content/golmok/"
LOCAL_FOLDER_NAMES = ("gasp", "golmoklocal")
LOCAL_ONLY_PREFIXES = ("unreal/golmok/config/golmok/local/",)
TAGS_DIR = "unreal/golmok/config/tags/"
TAGS_ALLOWED: tuple[str, ...] = ()  # committable Config/Tags/*.ini (none: GASP tags stay local, R21-11-3)
LOCAL_ONLY_FILES = ("unreal/golmok/config/defaultgameplaytags.ini",)


# ---- closure.json -----------------------------------------------------------------------------------------


def load_json(path):
    # utf-8-sig: Windows PowerShell 5.1 Set-Content -Encoding UTF8 writes a BOM.
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def parse_closure(data) -> list[str]:
    """tools/ue/gasp/closure.json: the migrate roots as original GASP package paths (/Game/...)."""
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != 1
        or type(data.get("schema_version")) is not int
    ):
        raise ValueError("closure.json: expected schema_version 1")
    roots = data.get("roots")
    if not isinstance(roots, list) or not roots:
        raise ValueError("closure.json: roots must be a nonempty list")
    paths = []
    for index, root in enumerate(roots):
        if not isinstance(root, dict) or set(root) != {"path", "status", "note"}:
            raise ValueError(f"closure.json: roots[{index}] must be {{path, status, note}}")
        path = root["path"]
        if not isinstance(path, str) or not PACKAGE_RE.fullmatch(path) or path.startswith("/Game/GASP/"):
            raise ValueError(
                f"closure.json: roots[{index}].path must be an original /Game package path: {path!r}"
            )
        if root["status"] not in ("confirmed", "estimated"):
            raise ValueError(f"closure.json: roots[{index}].status must be confirmed or estimated")
        if path in paths:
            raise ValueError(f"closure.json: duplicate root {path}")
        paths.append(path)
    return paths


def is_package_name(name: str) -> bool:
    """A /Game long package name UE can hold (INVALID_PACKAGE_CHARS)."""
    return PACKAGE_RE.fullmatch(name) is not None


def closure(roots, dependencies) -> tuple[list[str], list[str]]:
    """Breadth-first package closure over dependencies(package) -> package names, kept to /Game.

    Returns (packages, rejected): a "/Game/..." dependency that is not a valid package name is never dropped
    silently; migrate reports it and stops before copying (review R76 T4).
    """
    seen: set[str] = set()
    rejected: set[str] = set()
    queue = [r for r in roots if is_package_name(r)]
    while queue:
        package = queue.pop(0)
        if package in seen:
            continue
        seen.add(package)
        for dependency in dependencies(package) or ():
            name = str(dependency)
            if is_package_name(name):
                if name not in seen:
                    queue.append(name)
            elif name.startswith("/Game/"):
                rejected.add(name)
    return sorted(seen), sorted(rejected)


# ---- relocation -------------------------------------------------------------------------------------------


def map_to_root(package: str, content_root: str) -> str:
    """/Game/X/Y -> <content_root>/X/Y ("/Game/GASP" or "/Game")."""
    if content_root not in CONTENT_ROOTS:
        raise ValueError(f"content_root must be one of {CONTENT_ROOTS}: {content_root!r}")
    if not PACKAGE_RE.fullmatch(package):
        raise ValueError(f"not a /Game package: {package!r}")
    return package if content_root == "/Game" else content_root + package[len("/Game") :]


def relocation_plan(migrated, existing, content_root: str = "/Game/GASP") -> list[tuple[str, str, str]]:
    """Moves that put every migrated package under content_root without touching pre-existing ones.

    A folder that holds only migrated packages moves whole ("dir", src, dst) with rename_directory; a folder
    that also holds pre-existing packages (e.g. /Game/Characters with the mannequin pack) is split: its
    subfolders are planned the same way and its own migrated packages move one by one ("asset", src, dst).
    Nothing is planned for
    content_root "/Game" (the fallback keeps the Migrate paths).
    """
    migrated = sorted(set(migrated))
    existing = set(existing)  # only compared by prefix: whatever else is in Content is not validated (R76 T4)
    for package in migrated:
        if not is_package_name(package):
            raise ValueError(f"not a /Game package: {package!r}")
    if content_root == "/Game" or not migrated:
        return []
    if any(p == content_root or p.startswith(content_root + "/") for p in migrated):
        raise ValueError(f"migrated packages already under {content_root}")
    taken = sorted(map_to_root(p, content_root) for p in migrated if map_to_root(p, content_root) in existing)
    if taken:
        raise ValueError(
            f"{content_root} already holds {len(taken)} of the packages (e.g. {taken[0]}): "
            f"delete Content/{content_root[len('/Game/') :]} before add-gasp -Force"
        )
    return [(kind, path, map_to_root(path, content_root)) for kind, path in split_folders(migrated, existing)]


def split_folders(packages, others) -> list[tuple[str, str]]:
    """The fewest ("dir", folder) / ("asset", package) units that cover packages without covering others.

    A folder that holds only packages is one unit; a folder that also holds one of others (e.g.
    /Game/Characters with the mannequin pack) is split into its subfolders and its own packages.
    """
    packages = sorted(set(packages))
    others = set(others)
    out: list[tuple[str, str]] = []

    def visit(folder: str, inside_packages: list[str]):
        if folder != "/Game" and not any(p.startswith(folder + "/") for p in others):
            out.append(("dir", folder))
            return
        direct = [p for p in inside_packages if p.rpartition("/")[0] == folder]
        out.extend(("asset", p) for p in direct)
        children = sorted(
            {folder + "/" + p[len(folder) + 1 :].split("/", 1)[0] for p in inside_packages if p not in direct}
        )
        for child in children:
            visit(child, [p for p in inside_packages if p.startswith(child + "/")])

    visit("/Game", packages)
    return out


def migrate_preconditions(packages, existing, history=(), same_as_source=lambda package: False) -> dict:
    """What must be true before migrate copies anything into Golmok Content (review R76 T1).

    Stops when /Game/GASP already holds packages (an install: -Force never overwrites one) or when closure
    packages already sit at their Migrate paths as leftovers of an earlier add-gasp run: listed in the migrate
    history of this checkout, or byte-identical to the GASP file. Returns {problems, leftovers, delete} where
    delete are Content-relative folders / files that hold nothing but leftovers (never the mannequin pack).
    """
    existing = set(existing)
    installed = sorted(p for p in existing if p.startswith(MIGRATE_ROOT + "/"))
    history = set(history)
    conflicts = sorted(set(packages) & existing)
    # The byte rule never applies to the mannequin pack (add-mannequin copies Epic template files that could
    # be byte-identical to a GASP copy): only the history can call a package there a leftover.
    leftovers = sorted(
        {p for p in existing if p in history and not p.startswith(MIGRATE_ROOT + "/")}
        | {p for p in conflicts if not p.startswith(MANNEQUIN_PACK) and same_as_source(p)}
    )
    problems = []
    if installed:
        problems.append(
            f"{MIGRATE_ROOT} is already installed ({len(installed)} packages, e.g. {installed[0]}): add-gasp "
            f"never overwrites it; delete Content/{MIGRATE_ROOT[len('/Game/') :]} and Config/Golmok/local "
            "first (runbook A3 re-install)"
        )
    delete = []
    if leftovers:
        for kind, path in split_folders(leftovers, existing - set(leftovers)):
            rel = "Content/" + path[len("/Game/") :]
            delete.append(rel if kind == "dir" else rel + ".uasset")
        problems.append(
            f"{len(leftovers)} GASP packages of an earlier add-gasp run are still at their Migrate paths "
            f"(e.g. {leftovers[0]}): delete {', '.join(delete)} (unreal/Golmok/...; .umap for a level), then "
            "run add-gasp -Force (runbook A3 re-install)"
        )
    return {"problems": problems, "leftovers": leftovers, "delete": delete, "installed": len(installed)}


def load_history(path) -> set[str]:
    """Saved/Golmok/add-gasp/migrated-history.json: every package an add-gasp copy ever planned in this checkout."""
    if not path or not Path(path).is_file():
        return set()
    data = load_json(path)
    return {p for p in data.get("migrated", []) if isinstance(p, str)}


def record_history(path, packages) -> None:
    """Adds packages to the migrate history (kept across runs; a failed run never loses what it copied)."""
    if not path or not packages:
        return
    merged = sorted(load_history(path) | set(packages))
    write_json(path, {"schema_version": 1, "migrated": merged})


def installed_root(content_dir, migrated) -> str | None:
    """Where the migrated packages are now: "/Game/GASP", "/Game" (the Migrate paths) or None (neither)."""
    for root in CONTENT_ROOTS:
        if migrated and all(package_file(content_dir, map_to_root(p, root)) for p in migrated):
            return root
    return None


def packages_on_disk(content_dir) -> set[str]:
    """/Game package paths of the .uasset / .umap files under a Content folder."""
    root = Path(content_dir)
    out = set()
    if not root.is_dir():
        return out
    for path in root.rglob("*"):
        if path.suffix.lower() in PACKAGE_EXTENSIONS and path.is_file():
            rel = path.relative_to(root).with_suffix("").as_posix()
            out.add("/Game/" + rel)
    return out


def package_file(content_dir, package: str) -> Path | None:
    """The file of /Game/X/Y under content_dir (.uasset, else .umap), or None."""
    rel = PurePosixPath(package[len("/Game/") :])
    for ext in PACKAGE_EXTENSIONS:
        path = Path(content_dir) / (str(rel) + ext)
        if path.is_file():
            return path
    return None


# ---- manifest ---------------------------------------------------------------------------------------------


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def aggregate_digest(entries) -> str:
    """Order-independent digest of (path, size, sha256) entries; paths are relative to content_root."""
    lines = sorted(f"{e['path']}\t{e['size']}\t{e['sha256']}" for e in entries)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def relative_to_root(package: str, content_root: str) -> str:
    prefix = content_root + "/"
    if not package.startswith(prefix):
        raise ValueError(f"{package} is not under {content_root}")
    return package[len(prefix) :]


def source_entries(content_dir, packages) -> list[dict]:
    """The acquired GASP files (in the GASP project): (original /Game relative path, file, size, sha256)."""
    entries, missing = [], []
    for package in sorted(set(packages)):
        path = package_file(content_dir, package)
        if path is None:
            missing.append(package)
            continue
        entries.append(
            {
                "path": relative_to_root(package, "/Game"),
                "file": path.suffix,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    if missing:
        raise FileNotFoundError(
            f"{len(missing)} closure packages have no file in the GASP project: {missing[:3]}"
        )
    return entries


def build_manifest(
    content_dir, packages, content_root, gasp_project, engine_version, now=None, source=None
) -> dict:
    """gasp_manifest.json: every package with size and sha256 (paths relative to content_root) + digest.

    digest covers the relocated local files (integrity of this checkout; a rename resaves packages, so it
    differs between runs and PCs). source = {"source_digest", "source_package_count"} from the migrate report:
    the acquired GASP (original files in the GASP project), what tools/ue/gasp/expected.json pins (R76 T2).
    """
    if content_root not in CONTENT_ROOTS:
        raise ValueError(f"content_root must be one of {CONTENT_ROOTS}")
    entries, missing = [], []
    for package in sorted(set(packages)):
        path = package_file(content_dir, package)
        if path is None:
            missing.append(package)
            continue
        entries.append(
            {
                "path": relative_to_root(package, content_root),
                "file": path.suffix,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    if missing:
        raise FileNotFoundError(f"{len(missing)} migrated packages have no file, e.g. {missing[:3]}")
    stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": 1,
        "gasp_project": str(gasp_project),
        "engine_version": str(engine_version),
        "content_root": content_root,
        "package_count": len(entries),
        "digest": aggregate_digest(entries),
        "source_digest": (source or {}).get("source_digest"),
        "source_package_count": (source or {}).get("source_package_count"),
        "generated_utc": stamp,
        "packages": entries,
    }


def check_manifest(content_dir, manifest) -> list[str]:
    """Problems: a package missing on disk or with another size / hash; a digest that does not add up."""
    problems = []
    root = manifest.get("content_root")
    if root not in CONTENT_ROOTS:
        return [f"manifest content_root {root!r} is not one of {CONTENT_ROOTS}"]
    entries = manifest.get("packages") or []
    if manifest.get("package_count") != len(entries) or manifest.get("digest") != aggregate_digest(entries):
        problems.append("manifest package_count / digest do not match its package list (edited by hand?)")
    for entry in entries:
        package = f"{root}/{entry['path']}"
        path = package_file(content_dir, package)
        if path is None:
            problems.append(f"missing: {package}")
        elif path.stat().st_size != entry["size"] or sha256_file(path) != entry["sha256"]:
            problems.append(f"changed: {package}")
    return problems


EXPECTED_KEYS = ("engine_version", "package_count", "source_digest")


def compare_expected(manifest, expected) -> str | None:
    """tools/ue/gasp/expected.json (19b fills it from the first verified install): None when it matches.

    Compares the acquired GASP (source_digest / source_package_count of the migrate step, Fab section 7(a))
    and the engine version; the relocated local digest is not compared (it changes with every rename).
    """
    if any(expected.get(key) is None for key in EXPECTED_KEYS):
        return "expected.json not filled yet (19b records the first verified source_digest)"
    got = (
        manifest.get("engine_version"),
        manifest.get("source_package_count"),
        manifest.get("source_digest"),
    )
    want = tuple(expected[key] for key in EXPECTED_KEYS)
    if got != want:
        return (
            f"GASP 갱신 — V-08b/V-15 재확인: engine {got[0]} / {got[1]} packages / source_digest {got[2]}, "
            f"expected {want[0]} / {want[1]} / {want[2]}"
        )
    return None


# ---- GASP ini text -> local files -------------------------------------------------------------------------


def _sections(text: str):
    """(section, line) pairs of an ini text, section '' before the first header."""
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if line and not line.startswith((";", "#")):
            yield section, line


def _struct_fields(body: str) -> dict[str, str]:
    """Key=Value pairs of an Unreal struct text '(A=1,B="x, y",C=True)' (quoted values may hold commas)."""
    body = body.strip()
    if not (body.startswith("(") and body.endswith(")")):
        raise ValueError(f"not a struct value: {body!r}")
    fields: dict[str, str] = {}
    for match in re.finditer(
        r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*("(?:\\.|[^"\\])*"|[^,]*)\s*(?:,|$)', body[1:-1]
    ):
        value = match.group(2).strip()
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        fields[match.group(1)] = value
    return fields


def _array_value(line: str, key: str) -> str | None:
    """The value of '+Key=...' / 'Key=...' / '.Key=...' (Unreal array add forms), else None."""
    match = re.match(r"^[+.]?" + re.escape(key) + r"\s*=\s*(.*)$", line)
    return match.group(1) if match else None


def parse_cvars(text: str) -> list[dict]:
    """GASP DefaultEngine.ini [DataDrivenConsoleVariableSettings] +CVarsArray entries (Int / Float / Bool)."""
    out = []
    for section, line in _sections(text):
        if section != DDCVAR_SECTION:
            continue
        value = _array_value(line, "CVarsArray")
        if value is None:
            continue
        fields = _struct_fields(value)
        kind = CVAR_TYPES.get(fields.get("Type", ""))
        name = fields.get("Name", "")
        if kind is None or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]{0,127}", name):
            raise ValueError(f"unsupported CVarsArray entry: {line}")
        if kind == "bool":
            default = fields.get("DefaultValueBool", "False").lower() == "true"
        elif kind == "int":
            default = int(float(fields.get("DefaultValueInt", "0")))
        else:
            default = float(fields.get("DefaultValueFloat", "0"))
        if any(c["name"].lower() == name.lower() for c in out):
            raise ValueError(f"duplicate CVarsArray name: {name}")
        out.append({"name": name, "type": kind, "default": default, "help": fields.get("ToolTip", "")})
    return out


def ddcvars_json(cvars, source) -> dict:
    """Config/Golmok/local/gasp_ddcvars.json as GolmokAnimation::ParseDDCvars reads it."""
    return {"schema_version": 1, "source": str(source), "cvars": list(cvars)}


def parse_tags(text: str) -> list[tuple[str, str]]:
    """GASP DefaultGameplayTags.ini +GameplayTagList entries -> [(tag, dev_comment)]."""
    out = []
    for section, line in _sections(text):
        if section != TAGS_SECTION:
            continue
        value = _array_value(line, "GameplayTagList")
        if value is None:
            continue
        fields = _struct_fields(value)
        tag = fields.get("Tag", "")
        if not re.fullmatch(r"[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)*", tag):
            raise ValueError(f"unsupported GameplayTagList entry: {line}")
        if tag not in [t for t, _ in out]:
            out.append((tag, fields.get("DevComment", "")))
    return out


def tags_ini(tags, source) -> str:
    """Config/Tags/GASP.ini in the additional-tags format the engine reads from Config/Tags/*.ini."""
    lines = [
        f"; Generated by tools/ue/add-gasp.ps1 from {source} (local only, git-ignored).",
        f"[{TAGS_LIST_SECTION}]",
    ]
    for tag, comment in tags:
        escaped = comment.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'GameplayTagList=(Tag="{tag}",DevComment="{escaped}")')
    return "\n".join(lines) + "\n"


# ---- guards -----------------------------------------------------------------------------------------------


def is_local_only(path: str) -> bool:
    """A repo-relative path that must never be committed (check_repo.py GASP guard path rules, lower case)."""
    path = path.replace("\\", "/").strip().strip('"').lower()
    parts = path.split("/")
    if ".." in parts:
        return True  # never a clean repository path (git status prints none)
    if path.endswith((".uasset", ".umap")) and not path.startswith(PACKAGE_CONTENT):
        return True
    if path.startswith(GUARD_CONTENT):
        if not path.startswith(TRACKED_CONTENT):
            return True
        if any(part in LOCAL_FOLDER_NAMES for part in parts[3:-1]):
            return True
    if path.startswith(TAGS_DIR) and path.endswith(".ini") and path not in TAGS_ALLOWED:
        return True
    return path.startswith(LOCAL_ONLY_PREFIXES) or path in LOCAL_ONLY_FILES


def committable_local_paths(porcelain: str) -> list[str]:
    """Paths from `git status --porcelain --untracked-files=all` that the GASP guard forbids."""
    out = []
    for line in porcelain.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if is_local_only(path):
            out.append(path.strip().strip('"'))
    return out


def load_animation_config(path=ANIMATION_JSON) -> dict:
    """The fields add-gasp needs from animation.json (the C++ parser / pytest check the full schema)."""
    data = load_json(path)
    gasp = data["gasp"]
    return {
        "content_root": gasp["content_root"],
        "anim_class": gasp["anim_class"],
        "pawn_interface": gasp["pawn_interface"],
        "pawn_class": gasp["pawn_class"],
    }


def asset_path(content_root: str, relative: str) -> str:
    return relative if relative.startswith("/") else f"{content_root}/{relative}"


def write_text(path, text: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_json(path, data) -> Path:
    return write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
