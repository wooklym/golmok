"""Pure helpers for the WP-06 editor automation (zone_import, interior_setup, spike_runner).

Nothing from the editor API, no array library and no tools package is imported here, so
tools/tests/test_ue_python_pure.py runs every function on plain Python. File-system access is injected
(exists, listdir, isfile, isdir, read_text) and path strings are joined with '/' (posixpath); the caller
normalizes with os.path.normpath where the platform matters.

What lives here (docs/plan/WP-06-ue-python-automation.md, "설계 (확정)" §3-1):
- asset path conventions (spec §5 = GolmokZoneManifest.cpp) and UDIM file names (BaseName.####.ext only)
- MTL / OBJ streaming helpers, the import plan dict (§4-1) with its problem and warning strings (§4-5)
- importer pre-transform of OBJ and GLB copies (D3): A = (s M)^-1 TARGET, normals by U = A / k, winding flip
- the log formats LOG (§4-6), import_result.json (§4-3), the importer mapping cache check
- interior portal round trip check and the sublevel light spec (D9, D10)
- spike helpers: dwell path JSON (§4-7), -game command line and PowerShell script (§4-8), contact sheet
  HTML (§4-9) and the research/08 report template (§4-10)
"""

from __future__ import annotations

import html
import itertools
import json
import math
import posixpath
import re
import struct
import time
from collections.abc import Callable, Iterable, Iterator

# ---- constants ----------------------------------------------------------------------------------------

ZONES_ROOT = "/Game/Golmok/Zones"
MATERIAL_DIR = "/Game/Golmok/Materials"  # == materials.MATERIAL_DIR
MASTER_MATERIAL = f"{MATERIAL_DIR}/M_ZoneScan"
MASTER_MATERIAL_NOVT = f"{MATERIAL_DIR}/M_ZoneScan_NoVT"
CONTENT_ZONES_REL = "Golmok/Zones"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_]*$")
ZONE_ID_RE = re.compile(r"^z_[a-z0-9]+(_[a-z0-9]+)*$")
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")  # console names (tags, viewpoints, paths): C++ IsValidPathName
VERSION_DIR_RE = re.compile(r"^v([1-9][0-9]*)$")
# Official UDIM convention BaseName.####.ext (1001..1999); other names the engine's UDIM detection matches
# (UTextureFactory::UdimRegexPattern default "(.+?)[._](\d{4})$", index >= 1001: "_1002", ".2048") are only a
# warning and are imported with UDIM detection off (design D5, runbook #38).
UDIM_RE = re.compile(r"^(?P<base>.+)\.(?P<tile>1\d{3})\.(?P<ext>[A-Za-z0-9]+)$")
UDIM_SUSPECT_RE = re.compile(r"^(?P<base>.+?)[._](?P<tile>\d{4})\.(?P<ext>[A-Za-z0-9]+)$")
UDIM_TOKEN_RE = re.compile(r"<udim>", re.IGNORECASE)
UDIM_MIN, UDIM_MAX = 1001, 1999
# ENU (m) -> UE (cm): X east, Y south, Z up (== basemap_import.TARGET)
TARGET = ((100.0, 0.0, 0.0), (0.0, -100.0, 0.0), (0.0, 0.0, 100.0))
# ENU -> glTF Y-up: (x, y, z) -> (x, z, -y); its inverse is the transpose
GLTF_G = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0))
PROBE_BOX = ((1.0, 2.0, 3.0), (5.0, 9.0, 15.0))  # ENU m; three different extents: no permutation ambiguity
INTERIOR_SETUP_TAG = "GolmokInteriorSetup"
FORBIDDEN_SUBLEVEL_CLASSES = ("GolmokZone", "PostProcessVolume", "DirectionalLight", "GolmokPortal")
_MAP_KEYS = ("map_", "bump", "disp", "decal", "norm", "refl")  # == objio._MAP_KEYS
# MTL texture options and how many arguments they take (-o/-s/-t take 1 to 3 numbers) == objio._MAP_OPTS
_MAP_OPTS = {
    "-blendu": 1, "-blendv": 1, "-bm": 1, "-boost": 1, "-cc": 1, "-clamp": 1, "-imfchan": 1,
    "-mm": 2, "-o": 3, "-s": 3, "-t": 3, "-texres": 1, "-type": 1,
}  # fmt: skip
_UP_TO_3 = ("-o", "-s", "-t")
VIEWPOINT_NAMES = (
    "far_01", "far_02", "far_03", "mid_01", "mid_02", "mid_03", "mid_04", "near_01", "near_02", "near_03",
)  # fmt: skip
# docs/research/08-spike-results.md "시각 품질" rows -> the viewpoints that score them (design D13)
QUALITY_ROWS = (
    ("원경", ("far_01", "far_02", "far_03")),
    ("중경", ("mid_01", "mid_02", "mid_03", "mid_04")),
    ("근경 0.5m", ("near_01", "near_02", "near_03")),
    ("얇은 구조물(전선·철망·난간)", ("mid_04",)),
    ("캐릭터 그림자가 바닥·벽에 떨어지는지", ("near_03",)),
    ("조명 프리셋 변경에 반응하는지", ("mid_01",)),
    ("이음새(청크·배경·메시↔splat)", ("mid_02",)),
)
COST_ROWS = ("처리 시간(재구성·학습·변환)", "수작업 시간", "라이선스·배포 조건")
TAGS = ("a", "b", "c", "ac")
TAG_COLUMNS = {
    "a": "(a) 메시 Nanite+Lumen",
    "b": "(b) Cesium splat",
    "c": "(c) XGRIDS LCC",
    "ac": "(a+c) 하이브리드",
}
COST_COLUMNS = {"a": "(a)", "b": "(b)", "c": "(c)", "ac": "(a+c)"}  # research/08 "제작 비용" header
DEFAULT_PRESETS = ("overcast_morning", "clear_noon", "golden_evening")  # lighting cycle minus night
# spike_runner.configure_pie_window only (attended "New Editor Window (PIE)"; x ScreenshotMultiplier 2 =
# 2560x1440): capture_all's PIE plays in the level viewport and asks HighResShot for RES_X x RES_Y explicitly.
PIE_WINDOW = (1280, 720)
SCREENSHOT_MULTIPLIER = 2  # DefaultGame.ini [GolmokDebugSubsystem] ScreenshotMultiplier
SCREENSHOT_FOLDER = "Screenshots/Golmok"  # DefaultGame.ini [GolmokDebugSubsystem] ScreenshotFolder
PATH_FOLDER = "Golmok/Paths"  # DefaultGame.ini [GolmokDebugSubsystem] PathFolder
DWELL_S = 600.0  # dwell path length: even background PIE at 8 fps never runs off the end
ENGINE_VERSION_KEY = "5.8"  # %LOCALAPPDATA%/UnrealEngine/<key>/Saved (Launcher build, -game runs)
AREA_ORIGIN = (37.56, 126.923, 40.0)  # docs/spec/zone-manifest.md §4 area origin (== synthetic_zone)
PERF_HEADER = (  # == perf_report.to_markdown header line
    "| 구성 | 프레임 | 평균 fps | 1% low fps | 프레임 p50 ms | p99 ms | Game ms | Render ms | GPU ms |"
)
PERF_SEPARATOR = "|---|---|---|---|---|---|---|---|---|"
INTERIOR_LIGHT_CD = 3000.0
INTERIOR_LIGHT_KELVIN = 3000.0
INTERIOR_LIGHT_MAX_Z_CM = 250.0

Vec3 = tuple[float, float, float]
Mat3 = tuple[Vec3, Vec3, Vec3]
Bounds = tuple[Vec3, Vec3]


def _posix(path: str) -> str:
    return str(path).replace("\\", "/")


def _is_abs(path: str) -> bool:
    return path.startswith("/") or re.match(r"^[A-Za-z]:/", path) is not None


# ---- asset path conventions (spec §5, GolmokZoneManifest.cpp) ------------------------------------------


def asset_folder(zone_id: str, version: int) -> str:
    return f"{ZONES_ROOT}/{zone_id}/v{int(version)}"


def chunk_asset(zone_id: str, version: int, chunk_id: str) -> str:
    return f"{asset_folder(zone_id, version)}/SM_{chunk_id}"


def collision_asset(zone_id: str, version: int, chunk_id: str | None = None) -> str:
    name = f"SM_{zone_id}_collision" if chunk_id is None else f"SM_{zone_id}_collision_{chunk_id}"
    return f"{asset_folder(zone_id, version)}/{name}"


def sublevel_package(zone_id: str, version: int) -> str:
    return f"{asset_folder(zone_id, version)}/L_{zone_id}"


def texture_asset(zone_id: str, version: int, base: str) -> str:
    return f"{asset_folder(zone_id, version)}/Textures/T_{asset_name_safe(base)}"


def material_instance_asset(zone_id: str, version: int, material: str) -> str:
    return f"{asset_folder(zone_id, version)}/Materials/MI_{asset_name_safe(material)}"


def content_manifest_rel(zone_id: str, version: int) -> str:
    """'Golmok/Zones/<id>/v<n>' relative to the project Content folder ('/' separated)."""
    return f"{CONTENT_ZONES_REL}/{zone_id}/v{int(version)}"


def asset_paths(zone_id: str, version: int, chunk_id: str | None = None) -> dict:
    """Every asset path of a zone version (spec deliverable 1 name). ValueError on an invalid id."""
    if not ZONE_ID_RE.match(zone_id):
        raise ValueError(f"zone_id invalid: {zone_id}")
    if chunk_id is not None and not ID_RE.match(chunk_id):
        raise ValueError(f"chunk id invalid: {chunk_id}")
    if int(version) < 1:
        raise ValueError(f"version must be >= 1, got {version}")
    folder = asset_folder(zone_id, version)
    out: dict[str, str] = {"folder": folder}
    if chunk_id is not None:
        out["chunk"] = chunk_asset(zone_id, version, chunk_id)
    out["collision"] = collision_asset(zone_id, version)
    if chunk_id is not None:
        out["collision_chunk"] = collision_asset(zone_id, version, chunk_id)
    out["sublevel"] = sublevel_package(zone_id, version)
    out["textures_folder"] = f"{folder}/Textures"
    out["materials_folder"] = f"{folder}/Materials"
    out["manifest_rel"] = f"{content_manifest_rel(zone_id, version)}/manifest.json"
    out["probe"] = f"{folder}/_probe"
    return out


def asset_name_safe(text: str) -> str:
    """Asset-name safe token: [^A-Za-z0-9_] -> '_', a leading digit gets a '_' prefix; '' is an error."""
    if not text:
        raise ValueError("asset name must not be empty")
    safe = re.sub(r"[^A-Za-z0-9_]", "_", text)
    return "_" + safe if safe[0].isdigit() else safe


def object_path(asset_path: str) -> str:
    """'/Game/A/B' -> '/Game/A/B.B' (object path of a top-level asset)."""
    return f"{asset_path}.{asset_path.rsplit('/', 1)[-1]}"


# ---- UDIM ---------------------------------------------------------------------------------------------


def udim_split(filename: str) -> tuple[str, int, str] | None:
    """'T_alley.1002.png' -> ('T_alley', 1002, 'png'); None when the name is not BaseName.####.ext."""
    m = UDIM_RE.match(posixpath.basename(_posix(filename)))
    if not m:
        return None
    tile = int(m.group("tile"))
    if not UDIM_MIN <= tile <= UDIM_MAX:
        return None
    return m.group("base"), tile, m.group("ext")


def udim_tile_of(filename: str) -> int | None:
    split = udim_split(filename)
    return None if split is None else split[1]


def udim_suspect(filename: str) -> bool:
    """'a_1002.png', 'a.2048.png': the engine's UDIM name rule matches ([._]####, >= 1001) but the official
    convention BaseName.1001..1999.ext does not (warning; zone_import turns UDIM detection off for it)."""
    if udim_split(filename) is not None:
        return False
    m = UDIM_SUSPECT_RE.match(posixpath.basename(_posix(filename)))
    return bool(m) and int(m.group("tile")) >= UDIM_MIN


def udim_block_coords(tile: int) -> tuple[int, int]:
    """1001 -> (0, 0), 1002 -> (1, 0), 1011 -> (0, 1); u = (t-1001) % 10, v = (t-1001) // 10."""
    if not UDIM_MIN <= int(tile) <= UDIM_MAX:
        raise ValueError(f"UDIM tile must be in {UDIM_MIN}..{UDIM_MAX}, got {tile}")
    t = int(tile) - UDIM_MIN
    return t % 10, t // 10


def udim_canvas_blocks(tiles: Iterable[int]) -> tuple[int, int]:
    coords = [udim_block_coords(t) for t in tiles]
    if not coords:
        return 1, 1
    return max(u for u, _ in coords) + 1, max(v for _, v in coords) + 1


def _safe_listdir(listdir: Callable[[str], Iterable[str]], folder: str) -> list[str]:
    try:
        return sorted(listdir(folder))
    except OSError:
        return []


def _split_after(after: str) -> tuple[str, str]:
    """('.tiles', 'png') for '.tiles.png'; ('', 'png') for '.png' (a dotfile to posixpath.splitext)."""
    if after.startswith(".") and "." not in after[1:]:
        return "", after[1:]
    stem, dot_ext = posixpath.splitext(after)
    return stem, dot_ext[1:]


def _tile_pattern(before: str, after: str) -> re.Pattern:
    """Regex for sibling tiles: <before>####<after>, the extension of `after` case-insensitive."""
    stem, ext = _split_after(after)
    tail = re.escape(stem) + (r"\.(?i:" + re.escape(ext) + ")" if ext else "")
    return re.compile("^" + re.escape(before) + r"(?P<tile>1\d{3})" + tail + "$")


def _collect_tiles(names: Iterable[str], pattern: re.Pattern, folder: str) -> dict[int, str]:
    tiles: dict[int, str] = {}
    for name in names:
        m = pattern.match(name)
        if not m:
            continue
        tile = int(m.group("tile"))
        if not UDIM_MIN <= tile <= UDIM_MAX:
            continue
        if tile in tiles:
            raise ValueError(f"duplicate tile {tile}")
        tiles[tile] = posixpath.join(folder, name)
    return tiles


def _group(base: str, ext: str, folder: str, tiles: dict[int, str]) -> dict:
    ordered = sorted(tiles)
    return {
        "base": base,
        "ext": ext,
        "dir": folder,
        "tiles": ordered,
        "files": {str(t): tiles[t] for t in ordered},
        "anchor": tiles[ordered[0]] if ordered else None,
    }


def udim_group(map_path: str, listdir: Callable[[str], Iterable[str]]) -> dict:
    """The texture set behind one absolute map_Kd path.

    '<UDIM>' token: the folder is listed and every file with the same base and extension (extension case
    ignored) and a four-digit tile becomes part of the set. 'name.1001.png': that file's set including its
    sibling tiles. 'name.png': a single texture (tiles=[]). Two files with the same tile number (extension
    case) raise ValueError('duplicate tile <n>'); a token without files gives tiles=[], files={}, anchor=None.
    """
    path = _posix(map_path)
    folder, name = posixpath.dirname(path), posixpath.basename(path)
    if UDIM_TOKEN_RE.search(name):
        before, after = UDIM_TOKEN_RE.split(name, maxsplit=1)
        base = before[:-1] if before.endswith((".", "_")) else before
        ext = _split_after(after)[1]
        tiles = _collect_tiles(_safe_listdir(listdir, folder), _tile_pattern(before, after), folder)
        return _group(base, ext, folder, tiles)
    split = udim_split(name)
    if split is not None:
        base, _, ext = split
        tiles = _collect_tiles(_safe_listdir(listdir, folder), _tile_pattern(base + ".", "." + ext), folder)
        return _group(base, ext, folder, tiles)
    stem, dot_ext = posixpath.splitext(name)
    return {
        "base": stem,
        "ext": dot_ext[1:],
        "dir": folder,
        "tiles": [],
        "files": {"single": path},
        "anchor": path,
    }


def _udim_base_of(map_path: str) -> str:
    """Base name a map_Kd path would group under (for problem messages)."""
    name = posixpath.basename(_posix(map_path))
    if UDIM_TOKEN_RE.search(name):
        before = UDIM_TOKEN_RE.split(name, maxsplit=1)[0]
        return before[:-1] if before.endswith((".", "_")) else before
    split = udim_split(name)
    return split[0] if split else posixpath.splitext(name)[0]


# ---- MTL ----------------------------------------------------------------------------------------------


def _is_number(tok: str) -> bool:
    try:
        float(tok)
    except ValueError:
        return False
    return True


def split_map_line(line: str) -> tuple[str, str] | None:
    """'map_Kd -bm 1 tex/my file.png' -> ('map_Kd -bm 1', 'tex/my file.png'); None if not a texture line.

    Same rules as objio.split_map_line: known options and their arguments are skipped, everything after
    them is the file name, spaces included.
    """
    s = line.strip()
    if not s.lower().startswith(_MAP_KEYS):
        return None
    toks = s.split()
    i = 1
    while i < len(toks) - 1 and toks[i].lower() in _MAP_OPTS:
        opt = toks[i].lower()
        i += 1
        if opt in _UP_TO_3:
            k = 0
            while k < 3 and i < len(toks) - 1 and _is_number(toks[i]):
                i += 1
                k += 1
        else:
            i += _MAP_OPTS[opt]
    if i >= len(toks):
        return None
    parts = s.split(maxsplit=i)
    return " ".join(parts[:i]), parts[i]


def parse_mtl(text: str) -> dict[str, dict]:
    """{material: {'map_Kd': '<path as written, options stripped>' | None, 'Kd': [r, g, b] | None}}.

    Materials keep their newmtl order; a UTF-8 BOM is allowed.
    """
    out: dict[str, dict] = {}
    current: dict | None = None
    for raw in text.lstrip("\ufeff").splitlines():
        parts = raw.split(maxsplit=1)
        if not parts:
            continue
        key, rest = parts[0], (parts[1].strip() if len(parts) > 1 else "")
        if key == "newmtl":
            current = out.setdefault(rest, {"map_Kd": None, "Kd": None})
        elif current is None:
            continue
        elif key.lower() == "map_kd":
            split = split_map_line(raw)
            if split:
                current["map_Kd"] = split[1]
        elif key == "Kd":
            values = rest.split()
            if len(values) >= 3 and all(_is_number(v) for v in values[:3]):
                current["Kd"] = [float(v) for v in values[:3]]
    return out


def resolve_map_path(map_kd: str, mtl_dir: str) -> str:
    """Absolute texture path of a map_Kd entry: absolute as written, relative from the MTL's folder."""
    path = _posix(map_kd)
    if _is_abs(path):
        return path
    return posixpath.normpath(posixpath.join(_posix(mtl_dir), path))


def mtl_with_absolute_textures(text: str, mtl_dir: str) -> str:
    """The MTL text with every map_* path made absolute (option prefix kept); other lines untouched."""
    lines = []
    for line in text.splitlines():
        split = split_map_line(line)
        if split:
            prefix, name = split
            line = f"{prefix} {resolve_map_path(name, mtl_dir)}"
        lines.append(line)
    return "\n".join(lines) + "\n"


# ---- OBJ streaming ------------------------------------------------------------------------------------


def _obj_key(line: str) -> tuple[str, str]:
    parts = line.split(maxsplit=1)
    if not parts:
        return "", ""
    return parts[0], (parts[1] if len(parts) > 1 else "")


def obj_mtllibs(lines: Iterable[str]) -> list[str]:
    """'mtllib' names before the first face line; a name with spaces is the whole remainder."""
    out = []
    for line in lines:
        key, rest = _obj_key(line)
        if key == "f":
            break
        if key == "mtllib" and rest.strip():
            out.append(rest.strip())
    return out


def usemtl_order(lines: Iterable[str]) -> list[str]:
    """Material names in 'usemtl' order of appearance (duplicates removed); scans the whole file."""
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key, rest = _obj_key(line)
        if key == "usemtl":
            name = rest.strip()
            if name not in seen:
                seen.add(name)
                out.append(name)
    return out


def parse_obj_bounds(lines: Iterable[str]) -> Bounds:
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    for line in lines:
        key, rest = _obj_key(line)
        if key != "v":
            continue
        values = [float(v) for v in rest.split()[:3]]
        for i, v in enumerate(values):
            lo[i] = min(lo[i], v)
            hi[i] = max(hi[i], v)
    if lo[0] == math.inf:
        raise ValueError("OBJ has no 'v' lines")
    return tuple(lo), tuple(hi)


def _box_quads(lo: Vec3, hi: Vec3) -> list[tuple[Vec3, list[Vec3]]]:
    """(outward normal, CCW quad) per face of an axis-aligned box, like synthetic_zone.boxes_glb."""
    ex, ey, ez = lo
    fx, fy, fz = hi
    return [
        ((1, 0, 0), [(fx, ey, ez), (fx, fy, ez), (fx, fy, fz), (fx, ey, fz)]),
        ((-1, 0, 0), [(ex, fy, ez), (ex, ey, ez), (ex, ey, fz), (ex, fy, fz)]),
        ((0, 1, 0), [(fx, fy, ez), (ex, fy, ez), (ex, fy, fz), (fx, fy, fz)]),
        ((0, -1, 0), [(ex, ey, ez), (fx, ey, ez), (fx, ey, fz), (ex, ey, fz)]),
        ((0, 0, 1), [(ex, ey, fz), (fx, ey, fz), (fx, fy, fz), (ex, fy, fz)]),
        ((0, 0, -1), [(ex, fy, ez), (fx, fy, ez), (fx, ey, ez), (ex, ey, ez)]),
    ]


def probe_obj_text(box: Bounds = PROBE_BOX) -> str:
    """One axis-aligned box as OBJ text: 8 vertices, 12 triangles, no material, no vt/vn ('o probe')."""
    lo, hi = box
    corners = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    lines = ["# golmok zone_import probe (importer axis/unit measurement)", "o probe"]
    lines += ["v " + " ".join(f"{v:.6f}" for v in c) for c in corners]
    for _, quad in _box_quads(lo, hi):
        q = [corners.index(c) + 1 for c in quad]
        lines.append(f"f {q[0]} {q[1]} {q[2]}")
        lines.append(f"f {q[0]} {q[2]} {q[3]}")
    return "\n".join(lines) + "\n"


# ---- plan ---------------------------------------------------------------------------------------------


def resolve_zone_dir(
    zone_dir: str,
    version: int | None,
    listdir: Callable[[str], Iterable[str]],
    isdir: Callable[[str], bool],
    isfile: Callable[[str], bool],
) -> tuple[str, int]:
    """(version_dir, version) for '.../<zone_id>', '.../<zone_id>/v<n>' or '.../v<n>/manifest.json'.

    With version None the highest v<n> folder that has a manifest.json is chosen.
    """
    path = _posix(zone_dir).rstrip("/") or "/"
    if posixpath.basename(path) == "manifest.json":
        path = posixpath.dirname(path)
    m = VERSION_DIR_RE.match(posixpath.basename(path))
    if m:
        if not isfile(posixpath.join(path, "manifest.json")):
            raise ValueError(f"{path} is not a zone folder (expected .../<zone_id>/v<n>)")
        found = int(m.group(1))
        if version is not None and int(version) != found:
            raise ValueError(f"version {version} requested but {path} is v{found}")
        return path, found
    if not isdir(path):
        raise ValueError(f"{path} is not a zone folder (expected .../<zone_id>/v<n>)")
    if version is not None:
        vdir = posixpath.join(path, f"v{int(version)}")
        if not isfile(posixpath.join(vdir, "manifest.json")):
            raise ValueError(
                f"version {version} requested but {path}/v{int(version)}/manifest.json is missing"
            )
        return vdir, int(version)
    versions = []
    for name in listdir(path):
        vm = VERSION_DIR_RE.match(name)
        if vm and isfile(posixpath.join(path, name, "manifest.json")):
            versions.append(int(vm.group(1)))
    if not versions:
        raise ValueError(f"no v<n> folder with manifest.json under {path}")
    best = max(versions)
    return posixpath.join(path, f"v{best}"), best


def _bbox_list(bbox) -> list[list[float]] | None:
    if bbox is None:
        return None
    return [[float(v) for v in bbox[0]], [float(v) for v in bbox[1]]]


def _bbox_equal(a, b) -> bool:
    if a is None or b is None:
        return False
    flat_a, flat_b = list(a[0]) + list(a[1]), list(b[0]) + list(b[1])
    return all(round(float(x), 4) == round(float(y), 4) for x, y in zip(flat_a, flat_b, strict=True))


def _resolve_mtllibs(names: Iterable[str], folder: str, exists: Callable[[str], bool]) -> list[str]:
    """'mtllib a.mtl b.mtl' or 'mtllib my model.mtl': the whole remainder first, then space-separated."""
    out: list[str] = []
    for rest in names:
        whole = posixpath.join(folder, _posix(rest))
        parts = rest.split()
        if exists(whole) or len(parts) == 1:
            out.append(whole)
            continue
        candidates = [posixpath.join(folder, _posix(n)) for n in parts]
        out.extend(candidates if any(exists(c) for c in candidates) else [whole])
    return out


def import_plan(
    manifest: dict,
    chunk_manifest: dict | None,
    version_dir: str,
    *,
    exists: Callable[[str], bool],
    listdir: Callable[[str], Iterable[str]],
    read_text: Callable[[str], str],
) -> dict:
    """The import plan (design §4-1) for a zone version folder. Never raises: every issue lands in
    plan['problems'] (fatal, strings of §4-5) or plan['warnings'].

    `read_text(path)` is used for the OBJ headers (only the lines before the first face are needed, so a
    reader that returns the first few hundred lines is fine), the MTL files and blockers.json.
    """
    problems: list[str] = []
    warnings: list[str] = []
    version_dir = _posix(version_dir).rstrip("/")
    zone_id = str(manifest.get("zone_id", ""))
    version = manifest.get("version")
    kind = manifest.get("kind")
    parent_zone = manifest.get("parent_zone")
    if not ZONE_ID_RE.match(zone_id):
        problems.append(f"zone_id invalid: {zone_id}")
    folder_zone = posixpath.basename(posixpath.dirname(version_dir))
    folder_version = posixpath.basename(version_dir)
    if folder_zone != zone_id:
        problems.append(f"manifest: folder {folder_zone} != zone_id {zone_id}")
    if folder_version != f"v{version}":
        problems.append(f"manifest: folder {folder_version} != version {version}")
    layers = manifest.get("layers") or {}
    visual = layers.get("visual") or {}
    visual_format = visual.get("format")
    if visual_format != "nanite_mesh":
        problems.append(
            f"visual.format {visual_format} is not nanite_mesh (D-010: only nanite_mesh is importable)"
        )
    cm_chunks: dict[str, dict] = {}
    if chunk_manifest is None:
        problems.append("chunk_manifest.json missing (run golmok-mesh chunk)")
    else:
        cm_chunks = {str(c.get("id")): c for c in chunk_manifest.get("chunks", [])}
        missing = chunk_manifest.get("missing") or {}
        if missing.get("mtl") or missing.get("textures"):
            problems.append(
                f"chunk_manifest.missing: mtl={list(missing.get('mtl', []))} "
                f"textures={list(missing.get('textures', []))}"
            )

    mtl_cache: dict[str, dict] = {}
    tex_sets: dict[tuple, dict] = {}  # (dir, base, ext.lower()) -> texture entry
    tex_names: dict[str, tuple] = {}  # T_<name>.lower() -> set key (UE package names are case-insensitive)
    mi_names: dict[str, str] = {}  # MI_<name>.lower() -> MTL material name
    materials: dict[str, dict] = {}  # MTL material name -> plan entry (resolved)
    failed: set[str] = set()  # material names already reported
    chunk_entries: list[dict] = []

    def resolve_material(mat: str, cid: str, mtl_docs: list[tuple[str, dict]]) -> None:
        found = next(((path, doc[mat]) for path, doc in mtl_docs if mat in doc), None)
        if found is None:
            problems.append(f"material {mat}: not in {', '.join(p for p, _ in mtl_docs)} (chunk {cid})")
            failed.add(mat)
            return
        mtl_path, props = found
        mi_name = "MI_" + asset_name_safe(mat)
        other = mi_names.get(mi_name.lower())
        if other is not None and other != mat:
            problems.append(f"material {mat}: asset name collision {mi_name} (with material {other})")
            failed.add(mat)
            return
        mi_names[mi_name.lower()] = mat
        map_kd = props.get("map_Kd")
        if not map_kd:
            problems.append(f"material {mat}: no map_Kd (chunk {cid})")
            failed.add(mat)
            return
        map_path = resolve_map_path(map_kd, posixpath.dirname(mtl_path))
        try:
            group = udim_group(map_path, listdir)
        except ValueError as e:
            problems.append(f"texture {_udim_base_of(map_path)}: {e}")
            failed.add(mat)
            return
        anchor = group["anchor"]
        if anchor is None or not exists(anchor):
            problems.append(f"material {mat}: texture missing {anchor or map_path}")
            failed.add(mat)
            return
        key = (group["dir"], group["base"], group["ext"].lower())
        if key not in tex_sets:
            try:
                name = "T_" + asset_name_safe(group["base"])
            except ValueError as e:
                problems.append(f"material {mat}: {e} ({map_path})")
                failed.add(mat)
                return
            if name.lower() in tex_names:
                problems.append(f"texture {group['base']}: asset name collision {name}")
                failed.add(mat)
                return
            tex_names[name.lower()] = key
            tiles = list(group["tiles"])
            tex_sets[key] = {
                "name": name,
                "asset": f"{asset_folder(zone_id, version)}/Textures/{name}",
                "base": group["base"],
                "ext": group["ext"],
                "dir": group["dir"],
                "tiles": tiles,
                "files": dict(group["files"]),
                "anchor": anchor,
                "block_coords": [list(udim_block_coords(t)) for t in tiles],
                "canvas_blocks": list(udim_canvas_blocks(tiles)),
                "used_by": [],
            }
            if not tiles and udim_suspect(anchor):
                file = posixpath.basename(_posix(anchor))
                warnings.append(
                    f"texture {name}: '{file}' matches the engine UDIM name rule ([._]####, >= 1001) but "
                    "not BaseName.1001..1999.ext; imported as a single texture with UDIM detection off "
                    "(runbook #38)"
                )
            if tiles and group["ext"].lower() != "png":
                warnings.append(
                    f"texture {name}: UDIM tiles are .{group['ext']}; the merge check reads PNG headers only "
                    "(runbook #4) - export PNG"
                )
            if tiles and UDIM_MIN not in tiles:
                warnings.append(f"texture {group['base']}: tile 1001 missing; anchor is tile {tiles[0]}")
        tex_sets[key]["used_by"].append(mat)
        materials[mat] = {
            "name": "MI_" + asset_name_safe(mat),
            "asset": material_instance_asset(zone_id, version, mat),
            "mtl_material": mat,
            "mtl": mtl_path,
            "texture": tex_sets[key]["name"],
        }

    for chunk in sorted(visual.get("chunks", []), key=lambda c: str(c.get("id", ""))):
        cid = str(chunk.get("id", ""))
        if not ID_RE.match(cid):
            problems.append(f"chunk {cid}: invalid id")
            continue
        uri = _posix(str(chunk.get("uri", "")))
        if not uri.lower().endswith(".obj"):
            problems.append(
                f"chunk {cid}: uri {uri} is not .obj (WP-04/05 GLB fixtures: use synthetic_zone.run())"
            )
            continue
        obj = posixpath.join(version_dir, uri)
        if not exists(obj):
            problems.append(f"chunk {cid}: file missing {obj}")
            continue
        entry = cm_chunks.get(cid)
        if entry is None:
            if chunk_manifest is not None:
                problems.append(f"chunk {cid}: not in chunk_manifest.json")
            continue
        bbox = entry.get("bbox_enu")
        if not _bbox_equal(bbox, chunk.get("bbox_enu")):
            problems.append(f"chunk {cid}: bbox mismatch manifest vs chunk_manifest")
            if bbox is None:
                continue
        obj_dir = posixpath.dirname(obj)
        mtllibs = _resolve_mtllibs(obj_mtllibs(read_text(obj).splitlines()), obj_dir, exists)
        mtl_docs: list[tuple[str, dict]] = []
        for mtl in mtllibs:
            if not exists(mtl):
                problems.append(f"chunk {cid}: mtl missing {mtl}")
                continue
            if mtl not in mtl_cache:
                mtl_cache[mtl] = parse_mtl(read_text(mtl))
            mtl_docs.append((mtl, mtl_cache[mtl]))
        chunk_mats = sorted(str(m) for m in entry.get("materials", []))
        for mat in chunk_mats:
            if mat in materials or mat in failed or not mtl_docs:
                continue
            resolve_material(mat, cid, mtl_docs)
        # tile coverage is only meaningful once every material of the chunk resolved to a texture set
        resolved_all = all(m in materials for m in chunk_mats)
        chunk_tex = (
            [tex_sets[tex_names[materials[m]["texture"].lower()]] for m in chunk_mats] if resolved_all else []
        )
        udim_tiles = [int(t) for t in entry.get("udim_tiles", [])]
        for tile in udim_tiles:
            covered = any(tile in t["tiles"] or (not t["tiles"] and tile == UDIM_MIN) for t in chunk_tex)
            if chunk_tex and not covered:
                ref = next((t for t in chunk_tex if t["tiles"]), chunk_tex[0])
                warnings.append(
                    f"chunk {cid}: udim tile {tile} not in texture {ref['base']} tiles {ref['tiles']}"
                )
        lo, hi = expected_ue_bounds(bbox)
        chunk_entries.append(
            {
                "id": cid,
                "name": f"SM_{cid}",
                "asset": chunk_asset(zone_id, version, cid),
                "obj": obj,
                "mtllib": [posixpath.basename(m) for m in mtllibs],
                "bbox_enu": _bbox_list(bbox),
                "expected_ue_bounds_cm": [list(lo), list(hi)],
                "tris": int(entry.get("tris", 0)),
                "materials": chunk_mats,
                "slots": {m: "MI_" + asset_name_safe(m) for m in chunk_mats},
                "udim_tiles": udim_tiles,
            }
        )

    collision = layers.get("collision") or {}
    col_chunks = collision.get("chunks") or []
    collision_entries: list[dict] = []
    if col_chunks:
        collision_mode = "chunks"
        for c in sorted(col_chunks, key=lambda c: str(c.get("id", ""))):
            cid = str(c.get("id", ""))
            glb = posixpath.join(version_dir, _posix(str(c.get("uri", ""))))
            if not exists(glb):
                problems.append(f"collision chunk {cid}: file missing {glb}")
            collision_entries.append(
                {
                    "id": cid,
                    "name": f"SM_{zone_id}_collision_{cid}",
                    "asset": collision_asset(zone_id, version, cid),
                    "glb": glb,
                    "bbox_enu": _bbox_list(c.get("bbox_enu")),
                }
            )
    else:
        collision_mode = "single"
        glb = posixpath.join(version_dir, _posix(str(collision.get("uri") or "collision.glb")))
        if not exists(glb):
            problems.append(f"collision: file missing {glb}")
        collision_entries.append(
            {
                "id": None,
                "name": f"SM_{zone_id}_collision",
                "asset": collision_asset(zone_id, version),
                "glb": glb,
                "bbox_enu": None,
            }
        )

    copy_files = ["manifest.json"]
    blockers_layer = layers.get("blockers") or {}
    blockers = {"json": None, "planes": 0}
    if blockers_layer.get("uri"):
        uri = _posix(str(blockers_layer["uri"]))
        copy_files.append(uri)
        path = posixpath.join(version_dir, uri)
        blockers["json"] = path
        if not exists(path):
            problems.append(f"blockers: file missing {path}")
        else:
            try:
                blockers["planes"] = len(json.loads(read_text(path)).get("planes", []))
            except (ValueError, AttributeError) as e:
                problems.append(f"blockers: invalid JSON {path} ({e})")

    if kind == "interior" and not parent_zone:
        problems.append("interior: parent_zone missing")

    for tex in tex_sets.values():
        tex["used_by"] = sorted(set(tex["used_by"]))
    return {
        "schema": 1,
        "zone_id": zone_id,
        "version": version,
        "kind": kind,
        "parent_zone": parent_zone,
        "zone_dir": version_dir,
        "asset_folder": asset_folder(zone_id, version),
        "content_rel": content_manifest_rel(zone_id, version),
        "copy_files": sorted(copy_files),
        "textures": sorted(tex_sets.values(), key=lambda t: t["name"]),
        "materials": sorted(materials.values(), key=lambda m: m["name"]),
        "chunks": chunk_entries,
        "collision_mode": collision_mode,
        "collision": collision_entries,
        "blockers": blockers,
        "sublevel": sublevel_package(zone_id, version) if kind == "interior" else None,
        "problems": problems,
        "warnings": warnings,
    }


def plan_problems(plan: dict) -> list[str]:
    return list(plan.get("problems", []))


def slot_assignment(
    slot_names: list[str], wanted: dict[str, str], usemtl: list[str] | None
) -> tuple[list[tuple[int, str]], list[str]]:
    """[(slot_index, mi_name)] and the slot names left unmatched.

    Stages for every slot still unmatched: exact name -> case-insensitive name -> OBJ usemtl order
    (slot i <-> usemtl[i], only when that material is in `wanted`).
    """
    names = [str(n) for n in slot_names]
    pairs: dict[int, str] = {}
    for i, name in enumerate(names):
        if name in wanted:
            pairs[i] = wanted[name]
    lower = {}
    for key, value in wanted.items():
        lower.setdefault(key.lower(), value)
    for i, name in enumerate(names):
        if i not in pairs and name.lower() in lower:
            pairs[i] = lower[name.lower()]
    if usemtl:
        for i, _ in enumerate(names):
            if i not in pairs and i < len(usemtl) and usemtl[i] in wanted:
                pairs[i] = wanted[usemtl[i]]
    unmatched = [name for i, name in enumerate(names) if i not in pairs]
    return sorted(pairs.items()), unmatched


# ---- bbox and coordinates -----------------------------------------------------------------------------


def _matmul(a: Mat3, b: Mat3) -> Mat3:
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _apply(m: Mat3, v) -> Vec3:
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def _transpose(m: Mat3) -> Mat3:
    return tuple(tuple(m[j][i] for j in range(3)) for i in range(3))


def _signed_permutations() -> Iterator[Mat3]:
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1.0, -1.0), repeat=3):
            m = [[0.0] * 3 for _ in range(3)]
            for row, col in enumerate(perm):
                m[row][col] = signs[row]
            yield tuple(tuple(r) for r in m)


def expected_ue_bounds(bbox_enu) -> Bounds:
    """UE (cm) bounds of an ENU bbox [lo, hi]: TARGET applied to the 8 corners, min/max re-sorted."""
    lo, hi = bbox_enu
    corners = [_apply(TARGET, c) for c in itertools.product(*zip(lo, hi, strict=True))]
    return (
        tuple(min(c[i] for c in corners) for i in range(3)),
        tuple(max(c[i] for c in corners) for i in range(3)),
    )


def bounds_error_cm(got, want) -> float:
    """Largest absolute difference over the six bounds components."""
    pairs = [(a, b) for g, w in zip(got, want, strict=True) for a, b in zip(g, w, strict=True)]
    return max(abs(float(a) - float(b)) for a, b in pairs)


def bounds_tolerance_cm(want) -> float:
    """max(5 cm, 0.5 % of the longest extent)."""
    lo, hi = want
    return max(5.0, 0.005 * max(float(b) - float(a) for a, b in zip(lo, hi, strict=True)))


def measure_mapping(samples) -> tuple[float, float, Mat3]:
    """Find s, M with imported = s * M * ENU from (mesh bounds, ENU bbox) pairs: (err, scale, M).

    Pure copy of basemap_import._measure_import_mapping (identical results, tested).
    """
    best = None
    for m in _signed_permutations():
        scales, pairs = [], []
        for (umin, umax), (emin, emax) in samples:
            e_center = [(a + b) / 2 for a, b in zip(emin, emax, strict=True)]
            e_ext = [b - a for a, b in zip(emin, emax, strict=True)]
            u_center = [(a + b) / 2 for a, b in zip(umin, umax, strict=True)]
            u_ext = [b - a for a, b in zip(umin, umax, strict=True)]
            ext_mapped = [abs(v) for v in _apply(m, e_ext)]
            scales.append(sum(u_ext) / max(sum(ext_mapped), 1e-6))
            pairs.append((_apply(m, e_center), u_center, ext_mapped, u_ext))
        scale = sorted(scales)[len(scales) // 2]
        err = 0.0
        for c, uc, em, ue in pairs:
            err += sum(abs(scale * ci - ui) for ci, ui in zip(c, uc, strict=True))
            err += sum(abs(scale * ei - ui) for ei, ui in zip(em, ue, strict=True))
        if best is None or err < best[0]:
            best = (err, scale, m)
    return best


def _origin_of(manifest: dict) -> Vec3:
    o = manifest["origin"]
    return float(o["lat"]), float(o["lon"]), float(o["height_ellipsoidal"])


def resolve_geo_origin(arg, existing: tuple | None, manifest: dict, read_json: Callable[[str], dict]):
    """((lat, lon, h), how) for zone_import.run(geo_origin=...).

    None: keep the level's GeoOrigin, else the zone origin (zone at the level origin). 'area': the spec
    area origin. 'zone': the zone origin. (lat, lon, h): as given. A folder path: that basemap manifest's
    origin.
    """
    if arg is None:
        if existing is not None:
            return tuple(float(v) for v in existing), "kept"
        return _origin_of(manifest), "spawned from zone origin (zone at level origin)"
    if arg == "area":
        return AREA_ORIGIN, "spec area origin"
    if arg == "zone":
        return _origin_of(manifest), "zone origin"
    if isinstance(arg, list | tuple) and len(arg) == 3:
        return tuple(float(v) for v in arg), "given"
    if isinstance(arg, str):
        path = _posix(arg).rstrip("/")
        if posixpath.basename(path) != "manifest.json":
            path = posixpath.join(path, "manifest.json")
        return _origin_of(read_json(path)), f"basemap {arg}"
    raise ValueError(
        f"geo_origin must be None, 'area', 'zone', (lat, lon, h) or a basemap folder, got {arg!r}"
    )


# ---- importer pre-transform ---------------------------------------------------------------------------


def inverse_mapping_matrix(scale: float, m: Mat3) -> Mat3:
    """A = (s M)^-1 TARGET = M^T TARGET / s: vertices to write so that the importer yields TARGET * ENU."""
    inv = tuple(tuple(v / scale for v in row) for row in _transpose(m))
    return _matmul(inv, TARGET)


def det3(a: Mat3) -> float:
    return (
        a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
        - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
        + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0])
    )


def normal_matrix(a: Mat3) -> Mat3:
    """U = A / k with k = |first row of A| (A is a signed permutation times a scalar): normals map by U."""
    k = abs(a[0][0]) + abs(a[0][1]) + abs(a[0][2])
    return tuple(tuple(v / k for v in row) for row in a)


def gltf_conjugate(a: Mat3) -> Mat3:
    """G A G^-1: the ENU matrix A expressed in glTF Y-up coordinates."""
    return _matmul(_matmul(GLTF_G, a), _transpose(GLTF_G))


def _fmt6(values) -> str:
    return " ".join(f"{v:.6f}" for v in values)


def _split_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    return line, ""


def _pretransform_line(line: str, a: Mat3, u: Mat3, flip: bool) -> str:
    key, rest = _obj_key(line)
    if key == "v":
        body, ending = _split_ending(line)
        toks = body.split()[1:]
        xyz = _apply(a, [float(t) for t in toks[:3]])
        extra = (" " + " ".join(toks[3:])) if len(toks) > 3 else ""
        return f"v {_fmt6(xyz)}{extra}{ending}"
    if key == "vn":
        body, ending = _split_ending(line)
        toks = body.split()[1:]
        return f"vn {_fmt6(_apply(u, [float(t) for t in toks[:3]]))}{ending}"
    if key == "f" and flip:
        body, ending = _split_ending(line)
        toks = body.split()[1:]
        return "f " + " ".join(reversed(toks)) + ending
    return line


def pretransform_obj_lines(lines: Iterable[str], a: Mat3) -> Iterator[str]:
    """'v x y z [w | r g b]' -> A applied ('%.6f', trailing values kept); 'vn x y z' -> U applied; when
    det(A) < 0 the vertex order of every 'f' line is reversed (v/vt/vn triples stay together). Every other
    line (mtllib, usemtl, vt, o, g, s, comments, blank) is yielded byte for byte; line endings survive."""
    u = normal_matrix(a)
    flip = det3(a) < 0
    for line in lines:
        yield _pretransform_line(line, a, u, flip)


def pretransform_obj_file(src: str, dst: str, a: Mat3, mtllib: str | None = None) -> int:
    """Stream src -> dst through pretransform_obj_lines (constant memory). With `mtllib` every 'mtllib'
    line becomes 'mtllib <mtllib>'. Returns the number of 'v' lines."""
    u = normal_matrix(a)
    flip = det3(a) < 0
    count = 0
    with (
        open(src, encoding="utf-8", errors="surrogateescape", newline="") as fin,
        open(dst, "w", encoding="utf-8", errors="surrogateescape", newline="") as fout,
    ):
        first = True
        for line in fin:
            if first:
                first = False
                line = line.removeprefix("\ufeff")
            key = _obj_key(line)[0]
            if key == "v":
                count += 1
            if mtllib is not None and key == "mtllib":
                fout.write(f"mtllib {mtllib}{_split_ending(line)[1] or chr(10)}")
                continue
            fout.write(_pretransform_line(line, a, u, flip))
    return count


_COMPONENT_FORMAT = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
_TYPE_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}


def _glb_parts(data: bytes) -> tuple[dict, bytearray]:
    if len(data) < 20:
        raise ValueError("not a GLB (too short)")
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2:
        raise ValueError(f"not a GLB 2.0 (magic {magic!r}, version {version})")
    if total != len(data):
        raise ValueError(f"GLB length {total} != {len(data)} bytes")
    offset = 12
    gltf = None
    blob = bytearray()
    while offset + 8 <= len(data):
        length, ctype = struct.unpack_from("<I4s", data, offset)
        offset += 8
        chunk = data[offset : offset + length]
        offset += length
        if ctype == b"JSON":
            gltf = json.loads(chunk.decode("utf-8"))
        elif ctype == b"BIN\0" and not blob:
            blob = bytearray(chunk)
    if gltf is None:
        raise ValueError("GLB has no JSON chunk")
    return gltf, blob


def _accessor_layout(gltf: dict, index: int) -> tuple[int, int, str, int]:
    """(byte offset into the BIN chunk, count, struct format char, components) of accessor `index`."""
    acc = gltf["accessors"][index]
    if "sparse" in acc or "bufferView" not in acc:
        raise ValueError(f"accessor {index}: sparse or bufferless accessors are not supported")
    view = gltf["bufferViews"][acc["bufferView"]]
    if view.get("buffer", 0) != 0 or "uri" in gltf["buffers"][0]:
        raise ValueError(f"accessor {index}: data must live in the GLB BIN chunk")
    if view.get("byteStride"):
        raise ValueError(f"accessor {index}: interleaved bufferView (byteStride) is not supported")
    fmt_char = _COMPONENT_FORMAT.get(acc["componentType"])
    width = _TYPE_WIDTH.get(acc["type"])
    if fmt_char is None or width is None:
        raise ValueError(
            f"accessor {index}: unsupported componentType/type {acc['componentType']}/{acc['type']}"
        )
    offset = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    size = struct.calcsize("<" + fmt_char) * width * acc["count"]
    if acc.get("byteOffset", 0) + size > view["byteLength"]:
        raise ValueError(f"accessor {index}: data exceeds its bufferView")
    return offset, acc["count"], fmt_char, width


def _read_vec3(gltf: dict, blob: bytes, index: int) -> list[Vec3]:
    offset, count, fmt_char, width = _accessor_layout(gltf, index)
    if fmt_char != "f" or width != 3:
        raise ValueError(f"accessor {index}: expected float32 VEC3")
    flat = struct.unpack_from(f"<{3 * count}f", blob, offset)
    return [tuple(flat[3 * i : 3 * i + 3]) for i in range(count)]


def _write_vec3(gltf: dict, blob: bytearray, index: int, values: list[Vec3]) -> None:
    offset, count, _, _ = _accessor_layout(gltf, index)
    flat = [c for v in values for c in v]
    struct.pack_into(f"<{3 * count}f", blob, offset, *flat)


def _primitives(gltf: dict) -> Iterator[dict]:
    for mesh in gltf.get("meshes", []):
        yield from mesh.get("primitives", [])


def glb_bounds_enu(data: bytes) -> Bounds:
    """ENU (m) bounds of every primitive's POSITION accessor: glTF (x, y, z) -> ENU (x, -z, y)."""
    gltf, blob = _glb_parts(data)
    points = []
    seen: set[int] = set()
    for prim in _primitives(gltf):
        idx = prim.get("attributes", {}).get("POSITION")
        if idx is None or idx in seen:
            continue
        seen.add(idx)
        points.extend((x, -z, y) for x, y, z in _read_vec3(gltf, blob, idx))
    if not points:
        raise ValueError("GLB has no POSITION data")
    return (
        tuple(min(p[i] for p in points) for i in range(3)),
        tuple(max(p[i] for p in points) for i in range(3)),
    )


def glb_triangle_count(data: bytes) -> int:
    gltf, _ = _glb_parts(data)
    total = 0
    for prim in _primitives(gltf):
        if "indices" in prim:
            total += gltf["accessors"][prim["indices"]]["count"] // 3
        elif "POSITION" in prim.get("attributes", {}):
            total += gltf["accessors"][prim["attributes"]["POSITION"]]["count"] // 3
    return total


def pretransform_glb(data: bytes, a_enu: Mat3, rename: str | None = None) -> bytes:
    """Rewrite every primitive's POSITION with G A G^-1 and NORMAL with G U G^-1 (A given in ENU),
    refresh accessor min/max where present, reverse the triangles' index order when det(A) < 0, and
    rename every mesh and node to `rename`. Accessors sharing a bufferView, byteStride and non-triangle
    modes raise ValueError."""
    gltf, blob = _glb_parts(data)
    ag = gltf_conjugate(a_enu)
    ug = gltf_conjugate(normal_matrix(a_enu))
    flip = det3(a_enu) < 0
    view_users: dict[int, int] = {}
    for acc in gltf.get("accessors", []):
        if "bufferView" in acc:
            view_users[acc["bufferView"]] = view_users.get(acc["bufferView"], 0) + 1
    done: set[int] = set()

    def rewrite(index: int, matrix: Mat3, minmax: bool) -> None:
        if index in done:
            return
        done.add(index)
        acc = gltf["accessors"][index]
        if view_users.get(acc.get("bufferView"), 0) > 1:
            raise ValueError(f"accessor {index}: bufferView shared with another accessor")
        values = [_apply(matrix, v) for v in _read_vec3(gltf, blob, index)]
        _write_vec3(gltf, blob, index, values)
        if minmax:
            written = _read_vec3(gltf, blob, index)  # float32-rounded values
            if "min" in acc:
                acc["min"] = [min(v[i] for v in written) for i in range(3)]
            if "max" in acc:
                acc["max"] = [max(v[i] for v in written) for i in range(3)]

    for prim in _primitives(gltf):
        if prim.get("mode", 4) != 4:
            raise ValueError(f"primitive mode {prim.get('mode')} is not TRIANGLES")
        attributes = prim.get("attributes", {})
        if "POSITION" in attributes:
            rewrite(attributes["POSITION"], ag, minmax=True)
        if "NORMAL" in attributes:
            rewrite(attributes["NORMAL"], ug, minmax=False)
        if flip and "indices" not in prim:
            raise ValueError("non-indexed primitive with a mirroring mapping (winding cannot be flipped)")
        if flip and "indices" in prim and prim["indices"] not in done:
            index = prim["indices"]
            done.add(index)
            offset, count, fmt_char, width = _accessor_layout(gltf, index)
            if fmt_char not in ("H", "I") or width != 1:
                raise ValueError(f"accessor {index}: indices must be uint16 or uint32 scalars")
            if view_users.get(gltf["accessors"][index]["bufferView"], 0) > 1:
                raise ValueError(f"accessor {index}: bufferView shared with another accessor")
            flat = list(struct.unpack_from(f"<{count}{fmt_char}", blob, offset))
            for t in range(0, count - count % 3, 3):
                flat[t + 1], flat[t + 2] = flat[t + 2], flat[t + 1]
            struct.pack_into(f"<{count}{fmt_char}", blob, offset, *flat)
    if rename is not None:
        for mesh in gltf.get("meshes", []):
            mesh["name"] = rename
        for node in gltf.get("nodes", []):
            node["name"] = rename
    json_b = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_b += b" " * (-len(json_b) % 4)
    bin_b = bytes(blob) + b"\0" * (-len(blob) % 4)
    total = 12 + 8 + len(json_b) + 8 + len(bin_b)
    return (
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<I4s", len(json_b), b"JSON")
        + json_b
        + struct.pack("<I4s", len(bin_b), b"BIN\0")
        + bin_b
    )


def png_size(head: bytes) -> tuple[int, int]:
    """(width, height) from the first 24 bytes of a PNG (signature + IHDR); ValueError otherwise."""
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        raise ValueError("not a PNG header (signature + IHDR expected)")
    width, height = struct.unpack(">II", head[16:24])
    return width, height


# ---- logs (design §4-6: the single source of every log line; runbooks quote these) --------------------

LOG = {
    "zi.plan": (
        "zone_import: plan {zone_id} v{version}: chunks={chunks} collision={collision} ({collision_mode}) "
        "textures={textures} materials={materials} blockers={blockers}"
    ),
    "zi.cache": "zone_import: importer mapping cache {state} -> {path}",
    "zi.route": "zone_import: obj importer route={route} ({how})",
    "zi.mapping": "zone_import: {kind} importer mapping scale={scale:.3f} M={m} (fit error {err:.2f} cm)",
    "zi.texture": "zone_import: texture {asset} tiles={tiles} size={w}x{h} vt={vt} ({how})",
    "zi.material": "zone_import: material {asset} parent={parent} texture={texture}",
    "zi.chunk": "zone_import: chunk {asset} tris={tris} bounds ok (error {err:.2f} cm) slots={slots}",
    "zi.collision": (
        "zone_import: collision {asset} bounds ok (error {err:.2f} cm) complex-as-simple nanite=off"
    ),
    "zi.cleanup": "zone_import: deleted importer-created asset {asset}",
    "zi.moved": "zone_import: moved {src} -> {dst} (importer placement; runbook #37)",
    "zi.copied": "zone_import: copied {files} -> {dest}",
    "zi.geo": "zone_import: geo origin lat={lat:.6f} lon={lon:.6f} h={h:.3f} ({how})",
    "zi.zone": "zone_import: zone Zone_{zone_id} rebuilt",
    "zi.done": "zone_import: done {zone_id} v{version}: {assets} assets, {warnings} warnings -> {result}",
    "zi.warn": "zone_import: WARNING {message}",
    "zi.error": "zone_import: ERROR {step}: {message}",
    "is.portal": (
        "interior_setup: portal {interior_portal}<->{parent_portal} same point (err {dist_m:.3f} m), "
        "opposite yaw (err {yaw_err:.1f} deg)"
    ),
    "is.rerun": "interior_setup: removed {n} GolmokInteriorSetup actors from {package}",
    "is.sublevel": "interior_setup: sublevel {package} actors={actors} (level coordinates)",
    "is.exterior": "interior_setup: exterior zone Zone_{zone_id} rebuilt",
    "is.done": "interior_setup: done {zone_id} v{version} -> {result}",
    "is.error": "interior_setup: ERROR {step}: {message}",
    "sr.prepare": "spike_runner: viewpoints {level}: {saved} saved, missing={missing}",
    "sr.window": "spike_runner: PIE window {w}x{h} x{multiplier} ({how})",
    "sr.layers": (
        "spike_runner: layers tag={tag} zone_visual={zone_visual} Spike_b={spike_b} Spike_c={spike_c} "
        "(actors {n}, {where})"
    ),
    "sr.level": "spike_runner: layer level {package} saved (tag {tag})",
    "sr.pie": "spike_runner: PIE {state} tag={tag}",
    "sr.cmd": "spike_runner: > {command}",
    "sr.captured": "spike_runner: captured {path} ({w}x{h})",
    "sr.missing": "spike_runner: missing {path} ({why})",
    "sr.csv": 'spike_runner: csv {path} -> golmok-perf "{path}" --label {label} --markdown',
    "sr.done": "spike_runner: done {what}: {saved} saved, {missing} missing -> {root}",
    "sr.sheet": "spike_runner: contact sheet -> {path}",
    "sr.script": "spike_runner: -game script -> {path} ({runs} runs)",
    "sr.quit": "spike_runner: {what} finished; quitting the editor (quit_editor=True)",
    "sr.warn": "spike_runner: WARNING {message}",
    "bm.geo": (
        "basemap_import: GeoOrigin lat={lat:.6f} lon={lon:.6f} h={h:.3f} "
        "(basemap origin; ellipsoidal = DEM orthometric + --geoid-offset)"
    ),
}


def fmt(key: str, **kw) -> str:
    """LOG[key].format(**kw); an unknown key raises KeyError."""
    return LOG[key].format(**kw)


def log_prefixes() -> dict[str, str]:
    """key -> the fixed text before the first '{' placeholder (what the runbook drift test looks for)."""
    return {key: text.split("{", 1)[0] for key, text in LOG.items()}


# ---- results ------------------------------------------------------------------------------------------


def _mapping_json(mapping) -> dict | None:
    if mapping is None:
        return None
    if isinstance(mapping, dict):
        scale, m, err = mapping["scale"], mapping["m"], mapping.get("err", 0.0)
    else:
        scale, m, err = mapping
    return {"scale": float(scale), "m": [[float(v) for v in row] for row in m], "err": float(err)}


def result_json(plan: dict, mappings: dict, assets: list[dict], warnings: list[str], route: str) -> dict:
    """import_result.json (design §4-3). mappings: {'obj': (scale, m, err) | {...}, 'glb': ...}."""
    return {
        "schema": 1,
        "zone_id": plan["zone_id"],
        "version": plan["version"],
        "asset_folder": plan["asset_folder"],
        "route": route,
        "obj_mapping": _mapping_json(mappings.get("obj")),
        "glb_mapping": _mapping_json(mappings.get("glb")),
        "assets": list(assets),
        "warnings": list(warnings),
        "interior": None,
    }


def importer_cache_valid(cache: dict | None, engine_version: str) -> bool:
    return bool(cache) and cache.get("engine") == engine_version and "obj" in cache and "glb" in cache


_SUMMARY_ORDER = {"chunk": 0, "collision": 1, "texture": 2, "material": 3, "file": 4}


def summary_lines(result: dict) -> list[str]:
    """One line per asset in runbook check order (chunk, collision, texture, material, file)."""
    assets = sorted(
        result.get("assets", []), key=lambda a: (_SUMMARY_ORDER.get(a.get("kind"), 9), str(a.get("asset")))
    )
    lines = []
    for a in assets:
        detail = a.get("detail") or {}
        parts = ", ".join(f"{k}={v}" for k, v in detail.items())
        state = "ok" if a.get("ok") else "FAILED"
        lines.append(f"  - {a.get('kind')} {a.get('asset')}: {state}" + (f" ({parts})" if parts else ""))
    return lines


# ---- interior -----------------------------------------------------------------------------------------


def portal_pair(parent: dict, interior: dict) -> tuple[dict, dict]:
    """The one parent portal leading to the interior and the one interior portal leading back."""
    pid, iid = parent["zone_id"], interior["zone_id"]
    to_interior = [p for p in parent.get("portals", []) if p.get("to_zone") == iid]
    to_parent = [p for p in interior.get("portals", []) if p.get("to_zone") == pid]
    if len(to_interior) != 1:
        raise ValueError(f"{pid}: {len(to_interior)} portals lead to {iid} (expected exactly 1)")
    if len(to_parent) != 1:
        raise ValueError(f"{iid}: {len(to_parent)} portals lead to {pid} (expected exactly 1)")
    return to_interior[0], to_parent[0]


def enu_to_ecef(transform16: list[float], p) -> Vec3:
    """4x4 row-major zone transform applied to a zone-local ENU point (m) -> ECEF (m)."""
    t = [float(v) for v in transform16]
    if len(t) != 16:
        raise ValueError(f"transform needs 16 numbers, got {len(t)}")
    x, y, z = (float(v) for v in p)
    return tuple(t[4 * i] * x + t[4 * i + 1] * y + t[4 * i + 2] * z + t[4 * i + 3] for i in range(3))


def heading_ecef(transform16: list[float], yaw_deg: float) -> Vec3:
    """Unit ECEF direction of a zone-local heading: R * (cos yaw, sin yaw, 0)."""
    t = [float(v) for v in transform16]
    c, s = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    d = [t[4 * i] * c + t[4 * i + 1] * s for i in range(3)]
    n = math.sqrt(sum(v * v for v in d)) or 1.0
    return tuple(v / n for v in d)


def portal_round_trip_check(parent: dict, interior: dict, max_dist_m=0.05, max_yaw_err_deg=1.0) -> dict:
    """Do the parent's door and the interior's return door meet at the same point facing opposite ways?"""
    pp, ip = portal_pair(parent, interior)
    a = enu_to_ecef(parent["transform"], pp["pose_enu"]["position"])
    b = enu_to_ecef(interior["transform"], ip["pose_enu"]["position"])
    dist = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))
    ha = heading_ecef(parent["transform"], pp["pose_enu"]["yaw_deg"])
    hb = heading_ecef(interior["transform"], ip["pose_enu"]["yaw_deg"])
    dot = max(-1.0, min(1.0, sum(x * y for x, y in zip(ha, hb, strict=True))))
    yaw_err = abs(180.0 - math.degrees(math.acos(dot)))
    return {
        "parent_portal": pp["id"],
        "interior_portal": ip["id"],
        "dist_m": dist,
        "yaw_err_deg": yaw_err,
        "ok": dist <= max_dist_m and yaw_err <= max_yaw_err_deg,
    }


def interior_sublevel_specs(interior_manifest: dict) -> list[dict]:
    """The one PointLight of the interior sublevel (design D10), in interior-local UE cm: above the
    center of the visual chunks' bbox union, 2.5 m up or 0.5 m under a lower ceiling."""
    chunks = interior_manifest["layers"]["visual"]["chunks"]
    if not chunks:
        raise ValueError("interior manifest has no visual chunks")
    lo = [min(float(c["bbox_enu"][0][i]) for c in chunks) for i in range(3)]
    hi = [max(float(c["bbox_enu"][1][i]) for c in chunks) for i in range(3)]
    cx, cy = (lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0
    return [
        {
            "label": f"Interior_Light_{interior_manifest['zone_id']}",
            "kind": "point_light",
            "location_cm": (100.0 * cx, -100.0 * cy, min(INTERIOR_LIGHT_MAX_Z_CM, 100.0 * (hi[2] - 0.5))),
            "intensity_cd": INTERIOR_LIGHT_CD,
            "kelvin": INTERIOR_LIGHT_KELVIN,
            "tags": [INTERIOR_SETUP_TAG],
        }
    ]


# ---- spike --------------------------------------------------------------------------------------------


def missing_viewpoints(saved: dict, names: Iterable[str] = VIEWPOINT_NAMES) -> list[str]:
    return sorted(n for n in names if n not in saved)


def layer_state(tag: str) -> dict:
    if tag not in TAGS:
        raise ValueError(f"unknown spike tag {tag!r} (expected one of {', '.join(TAGS)})")
    return {"zone_visual": tag in ("a", "ac"), "spike_b": tag == "b", "spike_c": tag in ("c", "ac")}


def spike_actor_group(label: str) -> str | None:
    """'Spike_b_xgrids' -> 'spike_b', 'Spike_c_tiles' -> 'spike_c', anything else -> None."""
    for group in ("spike_b", "spike_c"):
        if label.startswith(f"Spike_{group[-1]}_"):
            return group
    return None


def capture_jobs(
    tags: Iterable[str], presets: Iterable[str], names: Iterable[str]
) -> list[tuple[str, str, str]]:
    """Tag-major job list: every preset of a tag, every viewpoint of a preset (one PIE session per tag)."""
    presets, names = list(presets), list(names)
    return [(tag, preset, name) for tag in tags for preset in presets for name in names]


def screenshot_path(saved_dir: str, tag: str, preset: str | None, name: str) -> str:
    """<Saved>/Screenshots/Golmok/<tag>/<preset or 'current'>/<name>.png (C++ golmok.screenshot)."""
    return f"{_posix(saved_dir).rstrip('/')}/{SCREENSHOT_FOLDER}/{tag}/{preset or 'current'}/{name}.png"


def screenshot_fallback_path(path: str) -> str:
    """'.../far_01.png' -> '.../far_0100000.png' (the HighResShot counter name the C++ fallback writes)."""
    return f"{path[:-4]}00000.png" if path.lower().endswith(".png") else f"{path}00000"


def validate_name(name: str) -> str:
    """Console-safe name (tag, viewpoint, path): commas and spaces would break -ExecCmds."""
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise ValueError(f"name {name!r} must match {NAME_RE.pattern}")
    return name


def dwell_path_json(
    name: str,
    level: str,
    location_cm,
    rotation_rpy_deg,
    dwell_s: float = DWELL_S,
    hz: int = 10,
    created: str = "",
) -> str:
    """Two-sample camera path standing still for dwell_s seconds, in GolmokStatsMath::FormatPathJson's
    layout (design §4-7). rotation_rpy_deg is viewpoints.py's [roll, pitch, yaw]; r = [pitch, yaw, roll]."""
    validate_name(name)
    if not created:
        created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    roll, pitch, yaw = (float(v) for v in rotation_rpy_deg)
    p = "[" + ", ".join(f"{float(v):.2f}" for v in location_cm) + "]"
    r = "[" + ", ".join(f"{v:.3f}" for v in (pitch, yaw, roll)) + "]"
    head = (
        f'{{"version": 1, "name": {json.dumps(name)}, "level": {json.dumps(level)}, "hz": {int(hz)}, '
        f'"created": {json.dumps(created)}, "samples": [\n'
    )
    first = f'{{"t": 0.000, "p": {p}, "r": {r}}},\n'
    last = f'{{"t": {float(dwell_s):.3f}, "p": {p}, "r": {r}}}\n'
    return head + first + last + "]}\n"


def exec_cmds(commands: list[str]) -> str:
    """'-ExecCmds="a, b, c"'; a command containing ',' or '"' cannot be passed and raises ValueError."""
    for command in commands:
        if "," in command or '"' in command:
            raise ValueError(f"console command {command!r} must not contain ',' or '\"'")
    return '-ExecCmds="' + ", ".join(commands) + '"'


def game_command_line(
    exe: str,
    uproject: str,
    map_path: str,
    *,
    walk: str,
    preset: str,
    res: tuple[int, int] = (1920, 1080),
    log_path: str,
) -> list[str]:
    """argv of one unattended -game CSV run (design §4-8): the path playback starts and stops CsvProfile."""
    validate_name(walk)
    validate_name(preset)
    return [
        exe,
        uproject,
        map_path,
        "-game",
        "-RenderOffscreen",
        f"-ResX={int(res[0])}",
        f"-ResY={int(res[1])}",
        "-ForceRes",
        "-ExitAfterCsvProfiling",
        "-unattended",
        "-nosplash",
        exec_cmds(["golmok.hud 0", f"golmok.tod {preset}", f"golmok.path play {walk} --csv"]),
        "-abslog=" + log_path,
    ]


def saved_dir_candidates(
    project_saved_dir: str, local_app_data: str | None, engine_version: str = ENGINE_VERSION_KEY
) -> list[str]:
    """Where a Launcher-build -game run may write Saved files: the project and %LOCALAPPDATA%."""
    out = [_posix(project_saved_dir).rstrip("/")]
    if local_app_data:
        out.append(f"{_posix(local_app_data).rstrip('/')}/UnrealEngine/{engine_version}/Saved")
    return out


def csv_dirs(candidates: list[str]) -> list[str]:
    return [f"{c}/Profiling/CSV" for c in candidates]


def path_dirs(candidates: list[str]) -> list[str]:
    return [f"{c}/{PATH_FOLDER}" for c in candidates]


def newest_file(
    candidates: list[str],
    pattern: str,
    not_before: float,
    isfile: Callable[[str], bool],
    mtime: Callable[[str], float],
    glob: Callable[[str], Iterable[str]],
) -> str | None:
    """Newest file matching <candidate>/<pattern> modified at or after not_before, or None."""
    best: tuple[float, str] | None = None
    for folder in candidates:
        for path in glob(f"{folder}/{pattern}"):
            if not isfile(path):
                continue
            t = mtime(path)
            if t >= not_before and (best is None or t > best[0]):
                best = (t, path)
    return None if best is None else best[1]


def _ps_str(text: str) -> str:
    """PowerShell single-quoted literal."""
    return "'" + text.replace("'", "''") + "'"


def ps_quote(arg: str) -> str:
    """One Start-Process -ArgumentList element. An argument with spaces and no '"' is wrapped in double
    quotes (a -key=value gets them around the value only, the way the engine parses -abslog=), then the
    whole thing becomes a PowerShell single-quoted literal (inner ' doubled)."""
    if '"' not in arg and " " in arg:
        if arg.startswith("-") and "=" in arg:
            key, value = arg.split("=", 1)
            arg = f'{key}="{value}"'
        else:
            arg = f'"{arg}"'
    return _ps_str(arg)


def _win(path: str) -> str:
    return str(path).replace("/", "\\")


def perf_label(tag: str, preset: str, walk: str) -> str:
    return f"{tag}_{preset}_{walk}"


def powershell_script(
    runs: list[dict], path_files: list[str], candidates: list[str], out_dir: str, timeout_s: int
) -> str:
    """run_game_perf.ps1 (design §4-8): copies the path JSONs into every Saved candidate, runs each
    {'label', 'argv'} with a timeout, collects the newest CSV into out_dir/<label>.csv and checks the log."""
    out_dir_w = _win(out_dir)
    lines = [
        "# generated by golmok.spike_runner.game_scripts - do not edit",
        "$ErrorActionPreference = 'Continue'",
        "$pathDirs = @(" + ", ".join(_ps_str(_win(d)) for d in path_dirs(candidates)) + ")",
        "$csvDirs = @(" + ", ".join(_ps_str(_win(d)) for d in csv_dirs(candidates)) + ")",
        "foreach ($d in $pathDirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null; "
        + "; ".join(f"Copy-Item -Force {_ps_str(_win(p))} $d" for p in path_files)
        + " }",
        f"New-Item -ItemType Directory -Force -Path {_ps_str(out_dir_w)} | Out-Null",
        "function Invoke-GolmokRun($label, $exe, $argv, $timeoutSec, $log) {",
        "  $t0 = Get-Date",
        "  $p = Start-Process -FilePath $exe -ArgumentList $argv -PassThru -NoNewWindow",
        "  if (-not $p.WaitForExit($timeoutSec * 1000)) { $p.Kill(); "
        'Write-Warning "$label timeout after $timeoutSec s" }',
        "  $csv = Get-ChildItem -Path $csvDirs -Filter 'Profile*.csv' -ErrorAction SilentlyContinue | "
        "Where-Object { $_.LastWriteTime -ge $t0 } | Sort-Object LastWriteTime -Descending | "
        "Select-Object -First 1",
        f'  if ($csv) {{ Copy-Item $csv.FullName (Join-Path {_ps_str(out_dir_w)} "$label.csv"); '
        'Write-Output "csv $label -> $($csv.FullName)" } '
        'else { Write-Warning "$label no CSV newer than $t0 (see $log)" }',
        "  if (-not (Select-String -Path $log -Pattern 'GolmokDebugSubsystem: csv:' -Quiet)) { "
        "Write-Warning \"$label log has no 'GolmokDebugSubsystem: csv:' line "
        '(ExecCmds timing? runbook #17)" }',
        "}",
    ]
    labels = []
    for run in runs:
        argv = list(run["argv"])
        label = run["label"]
        labels.append(label)
        log = run.get("log") or next((a[len("-abslog=") :] for a in argv if a.startswith("-abslog=")), "")
        lines.append(
            f"Invoke-GolmokRun {_ps_str(label)} {_ps_str(argv[0])} @("
            + ", ".join(ps_quote(a) for a in argv[1:])
            + f") {int(timeout_s)} {_ps_str(log)}"
        )
    perf = "golmok-perf " + " ".join(f'"{out_dir_w}\\{label}.csv"' for label in labels)
    perf += "".join(f" --label {label}" for label in labels) + " --markdown"
    lines.append(f"Write-Output {_ps_str(perf)}")
    return "\n".join(lines) + "\n"


_URI_SAFE = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~/:")


def file_uri(path: str) -> str:
    """'D:\\x\\y.jpg' -> 'file:///D:/x/y.jpg', '/x/y.jpg' -> 'file:///x/y.jpg' (percent-encoded)."""
    text = _posix(path)
    encoded = "".join(c if c in _URI_SAFE else "".join(f"%{b:02X}" for b in c.encode("utf-8")) for c in text)
    return "file://" + encoded if encoded.startswith("/") else "file:///" + encoded


_CONTACT_CSS = (
    "body{background:#111;color:#ddd;font-family:sans-serif;margin:16px}"
    "table{border-collapse:collapse;margin-bottom:24px}"
    "th,td{border:1px solid #444;padding:4px;vertical-align:top;text-align:center}"
    "th{background:#222}img{max-width:320px;display:block}"
    "td.missing{color:#f66;background:#221}a{color:#9cf}"
)


def _img_cell(rel: str, alt: str) -> str:
    rel = html.escape(_posix(rel))
    return f'<td><a href="{rel}"><img src="{rel}" loading="lazy" alt="{html.escape(alt)}"></a></td>'


def contact_sheet_html(
    tags: Iterable[str],
    presets: Iterable[str],
    names: Iterable[str],
    image_rel: Callable[[str, str, str], str | None],
    photo_rel: Callable[[str], str | None] | None = None,
    title: str = "Golmok spike 1.1",
) -> str:
    """One table per preset: viewpoint rows, a photo column (optional) and one column per tag; missing
    images become <td class="missing">missing</td>. Deterministic (no timestamp), no external resources."""
    tags, names = list(tags), list(names)
    esc = html.escape
    out = [
        "<!doctype html>",
        '<html lang="ko">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>{esc(title)}</title>",
        f"<style>{_CONTACT_CSS}</style>",
        "</head>",
        "<body>",
        f"<h1>{esc(title)}</h1>",
    ]
    header = ["viewpoint"] + (["photo"] if photo_rel else []) + [TAG_COLUMNS.get(t, t) for t in tags]
    for preset in presets:
        out.append(f'<h2 id="{esc(preset)}">{esc(preset)}</h2>')
        out.append("<table>")
        out.append("<tr>" + "".join(f"<th>{esc(h)}</th>" for h in header) + "</tr>")
        for name in names:
            cells = [f"<td>{esc(name)}</td>"]
            if photo_rel:
                rel = photo_rel(name)
                cells.append(_img_cell(rel, f"photo/{name}") if rel else '<td class="missing">missing</td>')
            for tag in tags:
                rel = image_rel(tag, preset, name)
                cells.append(
                    _img_cell(rel, f"{tag}/{preset}/{name}") if rel else '<td class="missing">missing</td>'
                )
            out.append("<tr>" + "".join(cells) + "</tr>")
        out.append("</table>")
    out += ["</body>", "</html>"]
    return "\n".join(out) + "\n"


def _table_header(cells: Iterable[str]) -> list[str]:
    cells = list(cells)
    return ["| " + " | ".join(cells) + " |", "|" + "---|" * len(cells)]


def report_template(
    tags: Iterable[str] = TAGS,
    presets: Iterable[str] = DEFAULT_PRESETS,
    perf_markdown: str = "",
    csv_labels: Iterable[str] = (),
) -> str:
    """Markdown skeleton of docs/research/08-spike-results.md's result tables (design §4-10). The headers
    and row names are the document's; the performance table takes golmok-perf --markdown output."""
    tags, presets, csv_labels = list(tags), list(presets), list(csv_labels)
    w, h = PIE_WINDOW
    m = SCREENSHOT_MULTIPLIER
    quality_cols = [TAG_COLUMNS.get(t, t) for t in tags]
    cost_cols = [COST_COLUMNS.get(t, f"({t})") for t in tags]
    walks = (
        ", ".join(csv_labels) or "walk_01 (golmok.path record walk_01, then golmok.path play walk_01 --csv)"
    )
    lines = [
        "## 조건",
        f"- 해상도: {w * m}×{h * m} (PIE `HighResShot {w * m}x{h * m}`; -game -ResX/-ResY 1920×1080)",
        f"- 조명 프리셋: {', '.join(presets)}",
        f"- 시점 {len(VIEWPOINT_NAMES)}곳: {', '.join(VIEWPOINT_NAMES)}",
        f"- 경로: {walks}",
        "",
        "### 시각 품질",
        *_table_header(["항목", *quality_cols]),
        *[f"| {row} |" + " |" * len(quality_cols) for row, _ in QUALITY_ROWS],
        "",
        "### 시점↔행 매핑",
        *_table_header(["항목", "시점"]),
        *[f"| {row} | {', '.join(names)} |" for row, names in QUALITY_ROWS],
        "",
        "### 성능",
        PERF_HEADER,
        PERF_SEPARATOR,
    ]
    rows = [line for line in perf_markdown.splitlines() if line.strip()]
    if rows and rows[0].strip() == PERF_HEADER:
        rows = rows[1:]
        if rows and rows[0].strip().startswith("|---"):
            rows = rows[1:]
    if rows:
        lines += rows
    else:
        labels = csv_labels or ["<label>"]
        csvs = [f'"Saved/Golmok/spike/csv/{label}.csv"' for label in csv_labels] or ['"<csv>"']
        command = "golmok-perf " + " ".join(csvs) + "".join(f" --label {label}" for label in labels)
        lines += ["", f"`{command} --markdown`"]
    lines += [
        "",
        "### 제작 비용",
        *_table_header(["항목", *cost_cols]),
        *[f"| {row} |" + " |" * len(cost_cols) for row in COST_ROWS],
        "",
        "### 컨택트 시트",
        *[f"- {preset}: Saved/Screenshots/Golmok/contact_sheet.html#{preset}" for preset in presets],
    ]
    return "\n".join(lines) + "\n"
