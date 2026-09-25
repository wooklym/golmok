"""unreal/.../golmok/_pure.py with an empty stub `unreal` module (WP-06 design §5-1).

The module must import and run without the editor, an array library or the tools package; the tests inject a
dict-backed file system, compare parity functions with their originals (objio.split_map_line,
basemap_import._measure_import_mapping, synthetic_zone.expected_ue_bounds / boxes_glb) and parse the
documents the strings must match (docs/research/08-spike-results.md, GolmokZoneManifest.cpp,
GolmokStatsMath.h, DefaultGame.ini).
"""

from __future__ import annotations

import importlib
import inspect
import itertools
import json
import re
import struct
import sys
import types
import zlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
PY_DIR = REPO / "unreal" / "Golmok" / "Content" / "Python"
GOLMOK_DIR = PY_DIR / "golmok"
FIXTURES = Path(__file__).parent / "fixtures"
CHUNK_MANIFEST_MIN = FIXTURES / "ue" / "chunk_manifest_min.json"
ZONE_FIXTURES = FIXTURES / "zones"
RESEARCH_08 = REPO / "docs" / "research" / "08-spike-results.md"
ZONE_MANIFEST_CPP = REPO / "unreal" / "Golmok" / "Source" / "Golmok" / "Zones" / "GolmokZoneManifest.cpp"
STATS_MATH_H = REPO / "unreal" / "Golmok" / "Source" / "Golmok" / "Debug" / "GolmokStatsMath.h"
DEFAULT_GAME_INI = REPO / "unreal" / "Golmok" / "Config" / "DefaultGame.ini"
RUNBOOKS = (REPO / "docs" / "runbooks" / "pc-verify-wp06.md", REPO / "docs" / "runbooks" / "pc-spike.md")

ROOT = "/synthetic"
ZONE = "z_synthetic_scan_001"
TEX_DIR = f"{ROOT}/recon/{ZONE}/tex"
FACADE_REL = "../../../../recon/z_synthetic_scan_001/tex/facade.<UDIM>.png"
GROUND_REL = "../../../../recon/z_synthetic_scan_001/tex/ground.png"
MTL_TEXT = (
    f"newmtl ground\nKd 1 1 1\nmap_Kd {GROUND_REL}\n\nnewmtl facade\nKd 1 1 1\nmap_Kd -bm 1 {FACADE_REL}\n"
)
OBJ_HEADER = (
    "# golmok-mesh chunk {cid}\nmtllib scan.mtl\nv 0.000000 0.000000 0.000000\nv 1 0 0\nv 0 1 0\nvt 0 0\n"
    "usemtl ground\nf 1/1 2/1 3/1\nusemtl facade\nf 1/1 3/1 2/1\n"
)
PLANE = {
    "id": "glass_1",
    "center_enu": [-8.0, 5.0, 1.5],
    "normal_enu": [0.0, -1.0, 0.0],
    "size_m": [3.0, 2.5],
    "kind": "glass",
}
IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
FLIP_Y = ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0))


@pytest.fixture(scope="module")
def mods():
    """_pure plus the existing modules it must agree with, all on the shared empty stub `unreal`."""
    sys.modules.setdefault("unreal", types.ModuleType("unreal"))
    sys.path.insert(0, str(PY_DIR))
    try:
        yield SimpleNamespace(
            pure=importlib.import_module("golmok._pure"),
            sz=importlib.import_module("golmok.synthetic_zone"),
            bm=importlib.import_module("golmok.basemap_import"),
            materials=importlib.import_module("golmok.materials"),
            lp=importlib.import_module("golmok.lighting_presets"),
        )
    finally:
        sys.path.remove(str(PY_DIR))


# ---- helpers -------------------------------------------------------------------------------------------


class FakeFS:
    """Dict-backed file system for the injected exists/listdir/isdir/isfile/read_text callables."""

    def __init__(self):
        self.files: dict[str, str] = {}

    def add(self, path, content=""):
        self.files[path] = content

    def remove(self, path):
        del self.files[path]

    def isfile(self, path):
        return path in self.files

    def isdir(self, path):
        prefix = path.rstrip("/") + "/"
        return any(k.startswith(prefix) for k in self.files)

    def exists(self, path):
        return self.isfile(path) or self.isdir(path)

    def listdir(self, folder):
        prefix = folder.rstrip("/") + "/"
        names = {k[len(prefix) :].split("/", 1)[0] for k in self.files if k.startswith(prefix)}
        if not names:
            raise FileNotFoundError(folder)
        return sorted(names)

    def read_text(self, path):
        return self.files[path]


def signed_permutations():
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1.0, -1.0), repeat=3):
            m = [[0.0] * 3 for _ in range(3)]
            for row, col in enumerate(perm):
                m[row][col] = signs[row]
            yield tuple(tuple(r) for r in m)


def apply(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def fake_import(bbox, scale, m):
    corners = [apply(m, c) for c in itertools.product(*zip(*bbox, strict=True))]
    lo = tuple(min(c[i] for c in corners) * scale for i in range(3))
    hi = tuple(max(c[i] for c in corners) * scale for i in range(3))
    return lo, hi


def read_glb(data: bytes):
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF" and version == 2 and total == len(data)
    json_len, json_type = struct.unpack_from("<I4s", data, 12)
    assert json_type == b"JSON"
    gltf = json.loads(data[20 : 20 + json_len])
    bin_len, bin_type = struct.unpack_from("<I4s", data, 20 + json_len)
    assert bin_type == b"BIN\0"
    blob = data[28 + json_len : 28 + json_len + bin_len]
    views = gltf["bufferViews"]

    def view(i, dtype):
        v = views[i]
        return np.frombuffer(blob[v["byteOffset"] : v["byteOffset"] + v["byteLength"]], dtype=dtype)

    pos = view(0, np.float32).reshape(-1, 3)
    nrm = view(1, np.float32).reshape(-1, 3)
    idx = view(2, np.uint32).reshape(-1, 3)
    return gltf, pos, nrm, idx


def write_png_rgb(w: int, h: int, rows: list[bytes]) -> bytes:
    def chunk(tag, body):
        return (
            struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + r for r in rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


def zone_fixture(name):
    return json.loads((ZONE_FIXTURES / name / "v1" / "manifest.json").read_text("utf-8"))


def table_after(text: str, heading_prefix: str):
    """(header cells, [first cell of each row]) of the first markdown table after a heading."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(heading_prefix))
    rows = []
    for line in lines[start + 1 :]:
        if line.startswith("|"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
        elif rows:
            break
    header, body = rows[0], rows[2:]  # rows[1] is the |---| separator
    return header, [r[0] for r in body]


def build_scenario(
    zone_id=ZONE,
    version=1,
    folder_zone=None,
    folder_version=None,
    kind="exterior",
    parent_zone=None,
    per_chunk=True,
    blockers=True,
):
    """The synthetic zone as import_plan sees it: manifest dict, WP-03 chunk manifest, folder, fake FS."""
    vdir = f"{ROOT}/zones/{folder_zone or zone_id}/v{folder_version or version}"
    fs = FakeFS()
    for cid in ("c_e000_n000", "c_w001_n000"):
        fs.add(f"{vdir}/visual/{cid}.obj", OBJ_HEADER.format(cid=cid))
        fs.add(f"{vdir}/collision/{cid}.glb", "glb")
    fs.add(f"{vdir}/visual/scan.mtl", MTL_TEXT)
    fs.add(f"{vdir}/collision.glb", "glb")
    fs.add(f"{vdir}/manifest.json", "{}")
    if blockers:
        fs.add(f"{vdir}/blockers.json", json.dumps({"planes": [PLANE]}))
    for name in ("facade.1001.png", "facade.1002.png", "facade.1011.png", "ground.png"):
        fs.add(f"{TEX_DIR}/{name}", "png")
    chunk_manifest = json.loads(CHUNK_MANIFEST_MIN.read_text("utf-8"))
    cm = {c["id"]: c for c in chunk_manifest["chunks"]}
    order = ("c_w001_n000", "c_e000_n000")  # grid order of golmok-mesh chunk (west cell first)
    collision = {"format": "glb", "uri": "collision.glb"}
    if per_chunk:
        collision["chunks"] = [
            {"id": cid, "uri": f"collision/{cid}.glb", "bbox_enu": cm[cid]["bbox_enu"]} for cid in order
        ]
    layers = {
        "visual": {
            "format": "nanite_mesh",
            "chunks": [
                {
                    "id": cid,
                    "uri": f"visual/{cid}.obj",
                    "bbox_enu": cm[cid]["bbox_enu"],
                    "tris": cm[cid]["tris"],
                }
                for cid in order
            ],
        },
        "collision": collision,
    }
    if blockers:
        layers["blockers"] = {"uri": "blockers.json"}
    manifest = {
        "schema_version": 1,
        "zone_id": zone_id,
        "version": version,
        "kind": kind,
        "parent_zone": parent_zone,
        "origin": {"lat": 37.562, "lon": 126.925, "height_ellipsoidal": 50.0},
        "layers": layers,
        "portals": [],
    }
    return SimpleNamespace(manifest=manifest, chunk_manifest=chunk_manifest, vdir=vdir, fs=fs)


def run_plan(pure, scn):
    return pure.import_plan(
        scn.manifest,
        scn.chunk_manifest,
        scn.vdir,
        exists=scn.fs.exists,
        listdir=scn.fs.listdir,
        read_text=scn.fs.read_text,
    )


def manifest_chunk(scn, cid):
    return next(c for c in scn.manifest["layers"]["visual"]["chunks"] if c["id"] == cid)


def expected_plan(vdir: str, collision_mode: str) -> dict:
    """Design §4-1 literal for the synthetic zone (paths under the fake FS root)."""
    folder = f"/Game/Golmok/Zones/{ZONE}/v1"
    mtl = f"{vdir}/visual/scan.mtl"
    chunks = {
        "c_e000_n000": (
            [[0.0, 0.0, 0.0], [15.0, 15.0, 6.0]],
            [[0.0, -1500.0, 0.0], [1500.0, 0.0, 600.0]],
            [1001, 1011],
        ),
        "c_w001_n000": (
            [[-15.0, 0.0, -0.3], [0.0, 15.0, 5.0]],
            [[-1500.0, -1500.0, -30.0], [0.0, 0.0, 500.0]],
            [1001, 1002],
        ),
    }
    if collision_mode == "chunks":
        collision = [
            {
                "id": cid,
                "name": f"SM_{ZONE}_collision_{cid}",
                "asset": f"{folder}/SM_{ZONE}_collision_{cid}",
                "glb": f"{vdir}/collision/{cid}.glb",
                "bbox_enu": bbox,
            }
            for cid, (bbox, _, _) in chunks.items()
        ]
    else:
        collision = [
            {
                "id": None,
                "name": f"SM_{ZONE}_collision",
                "asset": f"{folder}/SM_{ZONE}_collision",
                "glb": f"{vdir}/collision.glb",
                "bbox_enu": None,
            }
        ]
    return {
        "schema": 1,
        "zone_id": ZONE,
        "version": 1,
        "kind": "exterior",
        "parent_zone": None,
        "zone_dir": vdir,
        "asset_folder": folder,
        "content_rel": f"Golmok/Zones/{ZONE}/v1",
        "copy_files": ["blockers.json", "manifest.json"],
        "textures": [
            {
                "name": "T_facade",
                "asset": f"{folder}/Textures/T_facade",
                "base": "facade",
                "ext": "png",
                "dir": TEX_DIR,
                "tiles": [1001, 1002, 1011],
                "files": {
                    "1001": f"{TEX_DIR}/facade.1001.png",
                    "1002": f"{TEX_DIR}/facade.1002.png",
                    "1011": f"{TEX_DIR}/facade.1011.png",
                },
                "anchor": f"{TEX_DIR}/facade.1001.png",
                "block_coords": [[0, 0], [1, 0], [0, 1]],
                "canvas_blocks": [2, 2],
                "used_by": ["facade"],
            },
            {
                "name": "T_ground",
                "asset": f"{folder}/Textures/T_ground",
                "base": "ground",
                "ext": "png",
                "dir": TEX_DIR,
                "tiles": [],
                "files": {"single": f"{TEX_DIR}/ground.png"},
                "anchor": f"{TEX_DIR}/ground.png",
                "block_coords": [],
                "canvas_blocks": [1, 1],
                "used_by": ["ground"],
            },
        ],
        "materials": [
            {
                "name": "MI_facade",
                "asset": f"{folder}/Materials/MI_facade",
                "mtl_material": "facade",
                "mtl": mtl,
                "texture": "T_facade",
            },
            {
                "name": "MI_ground",
                "asset": f"{folder}/Materials/MI_ground",
                "mtl_material": "ground",
                "mtl": mtl,
                "texture": "T_ground",
            },
        ],
        "chunks": [
            {
                "id": cid,
                "name": f"SM_{cid}",
                "asset": f"{folder}/SM_{cid}",
                "obj": f"{vdir}/visual/{cid}.obj",
                "mtllib": ["scan.mtl"],
                "bbox_enu": bbox,
                "expected_ue_bounds_cm": ue,
                "tris": 66,
                "materials": ["facade", "ground"],
                "slots": {"facade": "MI_facade", "ground": "MI_ground"},
                "udim_tiles": tiles,
            }
            for cid, (bbox, ue, tiles) in chunks.items()
        ],
        "collision_mode": collision_mode,
        "collision": collision,
        "blockers": {"json": f"{vdir}/blockers.json", "planes": 1},
        "sublevel": None,
        "problems": [],
        "warnings": [],
    }


# ---- module, paths, names ------------------------------------------------------------------------------


def test_modules_import_with_empty_stub(mods):
    src = (GOLMOK_DIR / "_pure.py").read_text("utf-8")
    for forbidden in ("unreal", "numpy", "golmok_tools"):
        assert forbidden not in src, f"_pure.py must not mention {forbidden}"
    assert callable(mods.pure.import_plan) and isinstance(mods.pure.LOG, dict)
    # WP-06 modules import on the same empty stub (no unreal.X at import time); signatures per design §3
    sys.path.insert(0, str(PY_DIR))
    try:
        zi = importlib.import_module("golmok.zone_import")
        it = importlib.import_module("golmok.interior_setup")
        sr = importlib.import_module("golmok.spike_runner")
        vp = importlib.import_module("golmok.viewpoints")
    finally:
        sys.path.remove(str(PY_DIR))
    assert list(inspect.signature(zi.run).parameters) == [
        "zone_dir", "version", "level", "geo_origin", "save", "remeasure", "reimport_textures",
    ]  # fmt: skip
    assert list(inspect.signature(it.run).parameters) == [
        "zone_dir", "version", "level", "save", "register", "remeasure", "reimport_textures",
    ]  # fmt: skip
    assert issubclass(it.InteriorSetupError, zi.ZoneImportError)
    assert list(inspect.signature(sr.capture_all).parameters) == [
        "tags", "presets", "names", "mode", "quit_editor",
    ]  # fmt: skip
    assert list(inspect.signature(sr.perf_all).parameters) == ["paths", "tags", "presets", "quit_editor"]
    assert list(inspect.signature(sr.game_scripts).parameters) == [
        "paths", "tags", "presets", "res", "base_level", "timeout_s", "label_suffix",
    ]  # fmt: skip
    assert list(inspect.signature(vp.capture).parameters) == [
        "tag", "names", "presets", "game_view", "on_done",
    ]  # fmt: skip
    # synthetic_zone.run keeps its signature (design D18):
    params = inspect.signature(mods.sz.run).parameters
    assert list(params) == ["geo_origin", "move_player_start", "import_assets", "level", "interior"]


def test_asset_paths_match_cpp_manifest_and_synthetic_zone(mods):
    pure, sz = mods.pure, mods.sz
    manifest, interior = zone_fixture("z_synthetic_001"), zone_fixture("z_synthetic_001_interior")
    assert (
        pure.asset_folder("z_synthetic_001", 1)
        == sz.asset_folder(manifest)
        == "/Game/Golmok/Zones/z_synthetic_001/v1"
    )
    assert pure.asset_folder(interior["zone_id"], 1) == sz.asset_folder(interior)
    assert pure.sublevel_package(interior["zone_id"], 1) == sz.sublevel_path(interior)
    assert (
        pure.chunk_asset("z_synthetic_001", 1, "chunk_00")
        == "/Game/Golmok/Zones/z_synthetic_001/v1/SM_chunk_00"
    )
    assert (
        pure.collision_asset("z_synthetic_001", 1)
        == "/Game/Golmok/Zones/z_synthetic_001/v1/SM_z_synthetic_001_collision"
    )
    assert pure.collision_asset("z_synthetic_001", 1, "c_e000_n000").endswith(
        "/SM_z_synthetic_001_collision_c_e000_n000"
    )
    assert pure.texture_asset("z_a", 2, "my tex") == "/Game/Golmok/Zones/z_a/v2/Textures/T_my_tex"
    assert pure.material_instance_asset("z_a", 2, "facade") == "/Game/Golmok/Zones/z_a/v2/Materials/MI_facade"
    assert pure.content_manifest_rel("z_a", 2) == "Golmok/Zones/z_a/v2"
    cpp = ZONE_MANIFEST_CPP.read_text("utf-8")
    for needle in ('"/Game/Golmok/Zones/%s/v%d"', 'SM_%s_collision"', 'SM_%s_collision_%s"', '"%s/L_%s"'):
        assert needle in cpp, needle
    assert pure.MATERIAL_DIR == mods.materials.MATERIAL_DIR
    assert pure.MASTER_MATERIAL == f"{pure.MATERIAL_DIR}/M_ZoneScan"
    paths = pure.asset_paths("z_synthetic_001", 1, "chunk_00")
    assert set(paths) == {
        "folder", "chunk", "collision", "collision_chunk", "sublevel", "textures_folder", "materials_folder",
        "manifest_rel", "probe",
    }  # fmt: skip
    folder = "/Game/Golmok/Zones/z_synthetic_001/v1"
    assert paths["folder"] == folder and paths["chunk"] == f"{folder}/SM_chunk_00"
    assert paths["collision"] == f"{folder}/SM_z_synthetic_001_collision"
    assert paths["collision_chunk"] == f"{folder}/SM_z_synthetic_001_collision_chunk_00"
    assert paths["sublevel"] == f"{folder}/L_z_synthetic_001" and paths["probe"] == f"{folder}/_probe"
    assert (
        paths["textures_folder"] == f"{folder}/Textures"
        and paths["materials_folder"] == f"{folder}/Materials"
    )
    assert paths["manifest_rel"] == "Golmok/Zones/z_synthetic_001/v1/manifest.json"
    assert set(pure.asset_paths("z_synthetic_001", 1)) == set(paths) - {"chunk", "collision_chunk"}
    with pytest.raises(ValueError):
        pure.asset_paths("Zone_1", 1)
    with pytest.raises(ValueError):
        pure.asset_paths("z_a", 1, "bad-id")


def test_asset_name_safe_and_object_path(mods):
    pure = mods.pure
    assert pure.asset_name_safe("my tex.v2") == "my_tex_v2"
    assert pure.asset_name_safe("1001x") == "_1001x"
    assert pure.asset_name_safe("facade") == "facade"
    with pytest.raises(ValueError):
        pure.asset_name_safe("")
    assert pure.object_path("/Game/A/B") == "/Game/A/B.B"
    assert pure.object_path("/Game/Golmok/Zones/z_a/v1/SM_x") == "/Game/Golmok/Zones/z_a/v1/SM_x.SM_x"


# ---- UDIM ----------------------------------------------------------------------------------------------


def test_udim_tile_of_official_rule_only(mods):
    pure = mods.pure
    assert pure.udim_tile_of("T_alley.1002.png") == 1002
    assert pure.udim_tile_of("x.png") is None
    assert pure.udim_tile_of("a.1000.png") is None
    assert pure.udim_tile_of("a.2001.png") is None
    assert pure.udim_tile_of("a.1001.PNG") == 1001
    assert pure.udim_split("a.b.1001.png") == ("a.b", 1001, "png")
    assert pure.udim_tile_of("a_1002.png") is None and pure.udim_suspect("a_1002.png")
    assert (
        not pure.udim_suspect("a.1002.png")
        and not pure.udim_suspect("a_1000.png")
        and not pure.udim_suspect("a_0999.png")
        and not pure.udim_suspect("a.png")
    )
    # the engine's UDIM rule ([._]####, >= 1001; UTextureFactory::UdimRegexPattern) is wider (runbook #38)
    assert all(pure.udim_suspect(n) for n in ("a.2048.png", "a_2048.png", "a_4096.jpg", "a.b_1001.PNG"))
    assert pure.udim_tile_of("D:\\tex\\wall.1003.jpg") == 1003


def test_udim_block_coords_and_canvas(mods):
    pure = mods.pure
    for tile, uv in (
        (1001, (0, 0)),
        (1002, (1, 0)),
        (1010, (9, 0)),
        (1011, (0, 1)),
        (1020, (9, 1)),
        (1999, (8, 99)),
    ):
        assert pure.udim_block_coords(tile) == uv, tile
    assert pure.udim_canvas_blocks([1001, 1002, 1011]) == (2, 2)
    assert pure.udim_canvas_blocks([]) == (1, 1)
    assert pure.udim_canvas_blocks([1001]) == (1, 1)
    for bad in (1000, 2000):
        with pytest.raises(ValueError):
            pure.udim_block_coords(bad)


def test_udim_group_token_explicit_plain(mods):
    pure = mods.pure
    tree = {"/tex": ["facade.1001.png", "facade.1002.PNG", "facade.1011.png", "ground.png", "room.1001.png"]}
    token = pure.udim_group("/tex/facade.<UDIM>.png", tree.__getitem__)
    assert token == {
        "base": "facade",
        "ext": "png",
        "dir": "/tex",
        "tiles": [1001, 1002, 1011],
        "files": {
            "1001": "/tex/facade.1001.png",
            "1002": "/tex/facade.1002.PNG",
            "1011": "/tex/facade.1011.png",
        },
        "anchor": "/tex/facade.1001.png",
    }
    assert pure.udim_group("/tex/facade.<udim>.png", tree.__getitem__)["tiles"] == [1001, 1002, 1011]
    explicit = pure.udim_group("/tex/room.1001.png", tree.__getitem__)
    assert explicit["tiles"] == [1001] and explicit["files"] == {"1001": "/tex/room.1001.png"}
    assert explicit["anchor"] == "/tex/room.1001.png" and explicit["base"] == "room"
    plain = pure.udim_group(
        "/tex/ground.png", lambda folder: pytest.fail("plain names never list the folder")
    )
    assert plain == {
        "base": "ground",
        "ext": "png",
        "dir": "/tex",
        "tiles": [],
        "files": {"single": "/tex/ground.png"},
        "anchor": "/tex/ground.png",
    }
    with pytest.raises(ValueError, match="duplicate tile 1001"):
        pure.udim_group("/tex/facade.<UDIM>.png", lambda _: tree["/tex"] + ["facade.1001.PNG"])
    empty = pure.udim_group("/tex/nothing.<UDIM>.png", tree.__getitem__)
    assert empty["tiles"] == [] and empty["files"] == {} and empty["anchor"] is None
    # a folder that does not exist behaves like an empty one
    missing = pure.udim_group("/nope/x.<UDIM>.png", lambda _: (_ for _ in ()).throw(FileNotFoundError()))
    assert missing["anchor"] is None


# ---- MTL / OBJ -------------------------------------------------------------------------------------------


def test_split_map_line_matches_objio(mods):
    objio = pytest.importorskip("golmok_tools.mesh.objio")
    lines = [
        "map_Kd -bm 1 tex/my file.png",
        "map_Kd -o 1 2 tex/a.png",
        "map_Kd tex/space name.png",
        "map_Kd D:\\tex\\abs.png",
        "map_Ka tex/ka.png",
        "Kd 1 1 1",
        "newmtl x",
        "  map_Kd  -s 1 2 3 tex/b.png",
        "bump -bm 0.5 tex/n.png",
        "map_Kd",
    ]
    for line in lines:
        assert mods.pure.split_map_line(line) == objio.split_map_line(line), line
    assert mods.pure.split_map_line(lines[0]) == ("map_Kd -bm 1", "tex/my file.png")
    assert mods.pure._MAP_OPTS == objio._MAP_OPTS and mods.pure._MAP_KEYS == objio._MAP_KEYS


def test_parse_mtl_and_resolve(mods):
    pure = mods.pure
    text = (
        "\ufeff# comment\nnewmtl ground\nKd 0.5 0.5 0.5\nmap_Kd tex/ground.png\n\n"
        "newmtl facade\nKd 1 1 1\nmap_Kd -bm 1 tex/facade.<UDIM>.png\n\nnewmtl bare\nKd 1 0 0\n"
    )
    mtl = pure.parse_mtl(text)
    assert list(mtl) == ["ground", "facade", "bare"]
    assert mtl["ground"] == {"map_Kd": "tex/ground.png", "Kd": [0.5, 0.5, 0.5]}
    assert mtl["facade"]["map_Kd"] == "tex/facade.<UDIM>.png"
    assert mtl["bare"] == {"map_Kd": None, "Kd": [1.0, 0.0, 0.0]}
    assert pure.parse_mtl("") == {}
    assert pure.resolve_map_path("tex/a.png", "/z/v1/visual") == "/z/v1/visual/tex/a.png"
    assert (
        pure.resolve_map_path("../../../../recon/x/tex/a.png", "/s/zones/z/v1/visual")
        == "/s/recon/x/tex/a.png"
    )
    assert pure.resolve_map_path("/abs/a.png", "/z") == "/abs/a.png"
    assert pure.resolve_map_path("D:\\tex\\abs.png", "/z") == "D:/tex/abs.png"
    assert pure.resolve_map_path("tex\\a.png", "D:\\z\\visual") == "D:/z/visual/tex/a.png"


def test_mtl_with_absolute_textures(mods):
    pure = mods.pure
    text = (
        "newmtl facade\nKd 1 1 1\nmap_Kd -bm 1 tex/facade.<UDIM>.png\nmap_Ka tex/ka.png\n# keep\n\n"
        "newmtl g\nmap_Kd D:\\abs\\g.png\n"
    )
    out = pure.mtl_with_absolute_textures(text, "/s/zones/z/v1/visual")
    lines = out.split("\n")
    assert "map_Kd -bm 1 /s/zones/z/v1/visual/tex/facade.<UDIM>.png" in lines
    assert "map_Ka /s/zones/z/v1/visual/tex/ka.png" in lines
    assert "map_Kd D:/abs/g.png" in lines
    keep = [line for line in text.splitlines() if not pure.split_map_line(line)]
    assert [line for line in out.splitlines() if not pure.split_map_line(line)] == keep
    assert len(out.splitlines()) == len(text.splitlines())
    assert out.endswith("\n") and not out.endswith("\n\n")


def test_obj_streaming_helpers(mods):
    pure = mods.pure
    lines = [
        "# c\n",
        "mtllib my model.mtl\n",
        "mtllib a.mtl\n",
        "v 0 0 0\n",
        "f 1 2 3\n",
        "mtllib late.mtl\n",
    ]
    assert pure.obj_mtllibs(lines) == ["my model.mtl", "a.mtl"]
    obj = [
        "usemtl ground\n",
        "f 1 2 3\n",
        "usemtl facade\n",
        "f 1 2 3\n",
        "usemtl ground\n",
        "usemtl glass\n",
    ]
    assert pure.usemtl_order(obj) == ["ground", "facade", "glass"]
    assert pure.parse_obj_bounds(["v 1 -2 3\n", "vt 0 0\n", "v -1 5 0.5 1.0\n", "f 1 2 2\n"]) == (
        (-1.0, -2.0, 0.5),
        (1.0, 5.0, 3.0),
    )
    with pytest.raises(ValueError):
        pure.parse_obj_bounds(["vt 0 0\n"])
    probe = pure.probe_obj_text()
    plines = probe.splitlines()
    assert sum(1 for line in plines if line.startswith("v ")) == 8
    assert sum(1 for line in plines if line.startswith("f ")) == 12
    assert "o probe" in plines and probe.endswith("\n")
    assert not any(line.startswith(("vn", "vt", "usemtl", "mtllib")) for line in plines)
    assert pure.parse_obj_bounds(plines) == pure.PROBE_BOX


# ---- plan --------------------------------------------------------------------------------------------------


def test_resolve_zone_dir(mods):
    pure = mods.pure
    fs = FakeFS()
    fs.add("/zones/z_a/v1/manifest.json", "{}")
    fs.add("/zones/z_a/v2/manifest.json", "{}")
    fs.add("/zones/z_a/v3/notes.txt", "")  # a v3 folder without a manifest is skipped
    fs.add("/zones/z_b/readme.txt", "")
    fs.add("C:/zones/z_a/v1/manifest.json", "{}")

    def resolve(path, version=None):
        return pure.resolve_zone_dir(path, version, fs.listdir, fs.isdir, fs.isfile)

    assert resolve("/zones/z_a/v2") == ("/zones/z_a/v2", 2)
    assert resolve("/zones/z_a/v2/", 2) == ("/zones/z_a/v2", 2)
    assert resolve("/zones/z_a") == ("/zones/z_a/v2", 2)
    assert resolve("/zones/z_a", 1) == ("/zones/z_a/v1", 1)
    assert resolve("/zones/z_a/v1/manifest.json") == ("/zones/z_a/v1", 1)
    assert resolve("C:\\zones\\z_a\\v1") == ("C:/zones/z_a/v1", 1)
    with pytest.raises(ValueError, match=r"version 3 requested but /zones/z_a/v3/manifest.json is missing"):
        resolve("/zones/z_a", 3)
    with pytest.raises(ValueError, match=r"no v<n> folder with manifest.json under /zones/z_b"):
        resolve("/zones/z_b")
    with pytest.raises(ValueError, match=r"/zones/nope is not a zone folder \(expected .../<zone_id>/v<n>\)"):
        resolve("/zones/nope")
    with pytest.raises(ValueError, match=r"/zones/z_a/v3 is not a zone folder"):
        resolve("/zones/z_a/v3")
    with pytest.raises(ValueError, match=r"version 1 requested but /zones/z_a/v2 is v2"):
        resolve("/zones/z_a/v2", 1)


@pytest.mark.parametrize("collision_mode", ["chunks", "single"])
def test_import_plan_shape_from_fixture(mods, collision_mode):
    scn = build_scenario(per_chunk=collision_mode == "chunks")
    plan = run_plan(mods.pure, scn)
    want = expected_plan(scn.vdir, collision_mode)
    assert plan == want
    assert list(plan) == list(want)  # key order of §4-1
    assert mods.pure.plan_problems(plan) == []
    # Windows-style input is normalized to '/' and a trailing separator is dropped
    scn.vdir = scn.vdir.replace("/", "\\") + "\\"
    assert run_plan(mods.pure, scn)["zone_dir"] == want["zone_dir"]


def _case_zone_id_invalid():
    return build_scenario(zone_id="Z-bad"), "zone_id invalid: Z-bad"


def _case_folder_zone():
    return build_scenario(folder_zone="z_other"), f"manifest: folder z_other != zone_id {ZONE}"


def _case_folder_version():
    return build_scenario(folder_version=2), "manifest: folder v2 != version 1"


def _case_visual_format():
    scn = build_scenario()
    scn.manifest["layers"]["visual"]["format"] = "splat_ply"
    return scn, "visual.format splat_ply is not nanite_mesh (D-010: only nanite_mesh is importable)"


def _case_chunk_manifest_missing():
    scn = build_scenario()
    scn.chunk_manifest = None
    return scn, "chunk_manifest.json missing (run golmok-mesh chunk)"


def _case_chunk_invalid_id():
    scn = build_scenario()
    manifest_chunk(scn, "c_e000_n000")["id"] = "bad-id"
    return scn, "chunk bad-id: invalid id"


def _case_chunk_uri_not_obj():
    scn = build_scenario()
    manifest_chunk(scn, "c_e000_n000")["uri"] = "visual/c_e000_n000.glb"
    return scn, (
        "chunk c_e000_n000: uri visual/c_e000_n000.glb is not .obj "
        "(WP-04/05 GLB fixtures: use synthetic_zone.run())"
    )


def _case_chunk_file_missing():
    scn = build_scenario()
    scn.fs.remove(f"{scn.vdir}/visual/c_e000_n000.obj")
    return scn, f"chunk c_e000_n000: file missing {scn.vdir}/visual/c_e000_n000.obj"


def _case_chunk_not_in_chunk_manifest():
    scn = build_scenario()
    scn.chunk_manifest["chunks"] = [c for c in scn.chunk_manifest["chunks"] if c["id"] != "c_e000_n000"]
    return scn, "chunk c_e000_n000: not in chunk_manifest.json"


def _case_bbox_mismatch():
    scn = build_scenario()
    manifest_chunk(scn, "c_e000_n000")["bbox_enu"] = [[0.0, 0.0, 0.0], [15.0, 15.0, 6.001]]
    return scn, "chunk c_e000_n000: bbox mismatch manifest vs chunk_manifest"


def _case_mtl_missing():
    scn = build_scenario()
    obj = f"{scn.vdir}/visual/c_e000_n000.obj"
    scn.fs.add(obj, scn.fs.read_text(obj).replace("mtllib scan.mtl", "mtllib other.mtl"))
    return scn, f"chunk c_e000_n000: mtl missing {scn.vdir}/visual/other.mtl"


def _case_material_not_in_mtl():
    scn = build_scenario()
    scn.fs.add(f"{scn.vdir}/visual/scan.mtl", MTL_TEXT.replace("newmtl facade", "newmtl facade_x"))
    return scn, f"material facade: not in {scn.vdir}/visual/scan.mtl (chunk c_e000_n000)"


def _case_no_map_kd():
    scn = build_scenario()
    scn.fs.add(f"{scn.vdir}/visual/scan.mtl", MTL_TEXT.replace(f"map_Kd -bm 1 {FACADE_REL}\n", ""))
    return scn, "material facade: no map_Kd (chunk c_e000_n000)"


def _case_texture_missing():
    scn = build_scenario()
    scn.fs.remove(f"{TEX_DIR}/ground.png")
    return scn, f"material ground: texture missing {TEX_DIR}/ground.png"


def _case_duplicate_tile():
    scn = build_scenario()
    scn.fs.add(f"{TEX_DIR}/facade.1001.PNG", "png")
    return scn, "texture facade: duplicate tile 1001"


def _case_asset_name_collision():
    scn = build_scenario()
    scn.fs.add(f"{ROOT}/recon/{ZONE}/tex2/ground.png", "png")
    other = FACADE_REL.replace("tex/facade.<UDIM>.png", "tex2/ground.png")
    scn.fs.add(f"{scn.vdir}/visual/scan.mtl", MTL_TEXT.replace(FACADE_REL, other))
    return scn, "texture ground: asset name collision T_ground"


def _case_collision_file_missing():
    scn = build_scenario(per_chunk=False)
    scn.fs.remove(f"{scn.vdir}/collision.glb")
    return scn, f"collision: file missing {scn.vdir}/collision.glb"


def _case_collision_chunk_file_missing():
    scn = build_scenario()
    scn.fs.remove(f"{scn.vdir}/collision/c_e000_n000.glb")
    return scn, f"collision chunk c_e000_n000: file missing {scn.vdir}/collision/c_e000_n000.glb"


def _case_blockers_file_missing():
    scn = build_scenario()
    scn.fs.remove(f"{scn.vdir}/blockers.json")
    return scn, f"blockers: file missing {scn.vdir}/blockers.json"


def _case_chunk_manifest_missing_entries():
    scn = build_scenario()
    scn.chunk_manifest["missing"] = {"mtl": ["/x/a.mtl"], "textures": []}
    return scn, "chunk_manifest.missing: mtl=['/x/a.mtl'] textures=[]"


def _case_interior_parent_missing():
    return build_scenario(kind="interior", parent_zone=None), "interior: parent_zone missing"


PROBLEM_CASES = [
    _case_zone_id_invalid,
    _case_folder_zone,
    _case_folder_version,
    _case_visual_format,
    _case_chunk_manifest_missing,
    _case_chunk_invalid_id,
    _case_chunk_uri_not_obj,
    _case_chunk_file_missing,
    _case_chunk_not_in_chunk_manifest,
    _case_bbox_mismatch,
    _case_mtl_missing,
    _case_material_not_in_mtl,
    _case_no_map_kd,
    _case_texture_missing,
    _case_duplicate_tile,
    _case_asset_name_collision,
    _case_collision_file_missing,
    _case_collision_chunk_file_missing,
    _case_blockers_file_missing,
    _case_chunk_manifest_missing_entries,
    _case_interior_parent_missing,
]


@pytest.mark.parametrize("case", PROBLEM_CASES, ids=lambda f: f.__name__[len("_case_") :])
def test_plan_problems_each_case(mods, case):
    scn, expected = case()
    plan = run_plan(mods.pure, scn)
    assert plan["problems"] == [expected]
    assert mods.pure.plan_problems(plan) == [expected]
    assert plan["warnings"] == []


def test_plan_warnings(mods):
    scn = build_scenario()
    scn.fs.add(f"{TEX_DIR}/ground_1002.png", "png")
    scn.fs.add(f"{scn.vdir}/visual/scan.mtl", MTL_TEXT.replace("tex/ground.png", "tex/ground_1002.png"))
    next(c for c in scn.chunk_manifest["chunks"] if c["id"] == "c_e000_n000")["udim_tiles"] = [1001, 1003]
    scn.fs.remove(f"{TEX_DIR}/facade.1001.png")
    plan = run_plan(mods.pure, scn)
    assert plan["problems"] == []
    assert plan["warnings"] == [
        "texture facade: tile 1001 missing; anchor is tile 1002",
        "texture T_ground_1002: 'ground_1002.png' matches the engine UDIM name rule ([._]####, >= 1001) but "
        "not BaseName.1001..1999.ext; imported as a single texture with UDIM detection off (runbook #38)",
        "chunk c_e000_n000: udim tile 1003 not in texture facade tiles [1002, 1011]",
    ]
    facade = next(t for t in plan["textures"] if t["name"] == "T_facade")
    assert facade["tiles"] == [1002, 1011] and facade["anchor"] == f"{TEX_DIR}/facade.1002.png"
    ground = next(t for t in plan["textures"] if t["name"] == "T_ground_1002")
    assert ground["tiles"] == [] and ground["files"] == {"single": f"{TEX_DIR}/ground_1002.png"}


def test_slot_assignment_three_stages(mods):
    pure = mods.pure
    wanted = {"facade": "MI_facade", "ground": "MI_ground", "glass": "MI_glass"}
    slots = ["facade", "Ground", "Material_2", "stray"]
    pairs, unmatched = pure.slot_assignment(slots, wanted, None)
    assert pairs == [(0, "MI_facade"), (1, "MI_ground")] and unmatched == ["Material_2", "stray"]
    pairs, unmatched = pure.slot_assignment(slots, wanted, ["facade", "ground", "glass", "other"])
    assert pairs == [(0, "MI_facade"), (1, "MI_ground"), (2, "MI_glass")] and unmatched == ["stray"]
    # usemtl only fills slots that are still unmatched and only with wanted materials
    pairs, unmatched = pure.slot_assignment(["Material_0", "Material_1"], wanted, ["ground", "nothing"])
    assert pairs == [(0, "MI_ground")] and unmatched == ["Material_1"]
    assert pure.slot_assignment([], wanted, None) == ([], [])


# ---- bbox, mapping, geo ----------------------------------------------------------------------------------


def test_expected_ue_bounds_matches_spec_and_synthetic_zone(mods):
    pure, sz, bm = mods.pure, mods.sz, mods.bm
    box = ((0.0, 10.0, 0.0), (10.0, 20.0, 1.0))
    assert pure.expected_ue_bounds(box) == ((0.0, -2000.0, 0.0), (1000.0, -1000.0, 100.0))
    assert pure.expected_ue_bounds(box) == sz.expected_ue_bounds([box])
    assert pure.expected_ue_bounds([[-15.0, 0.0, -0.3], [0.0, 15.0, 5.0]]) == (
        (-1500.0, -1500.0, -30.0),
        (0.0, 0.0, 500.0),
    )
    assert pure.TARGET == bm.TARGET
    want = ((0.0, -2000.0, 0.0), (1000.0, -1000.0, 100.0))
    assert pure.bounds_tolerance_cm(want) == 5.0
    assert pure.bounds_tolerance_cm(((0.0, 0.0, 0.0), (4000.0, 100.0, 100.0))) == 20.0
    assert pure.bounds_error_cm(((0.0, -2000.0, 0.5), (1000.0, -1001.0, 100.0)), want) == 1.0
    assert pure.bounds_error_cm(want, want) == 0.0


def test_measure_mapping_matches_basemap_import(mods):
    pure, bm = mods.pure, mods.bm
    tiles = [
        ((-400.0, -400.0, -2.0), (-200.0, -200.0, 1.0)),
        ((100.0, -30.0, -0.4), (120.0, -20.0, 9.6)),
        ((-15.0, 300.0, 1.5), (15.0, 330.0, 23.0)),
        ((200.0, 0.0, -1.0), (400.0, 200.0, 3.0)),
    ]
    count = 0
    for m in signed_permutations():
        for scale in (1.0, 100.0):
            samples = [(fake_import(b, scale, m), b) for b in tiles]
            got = pure.measure_mapping(samples)
            assert got == bm._measure_import_mapping(samples)
            err, s, mm = got
            assert mm == m and s == pytest.approx(scale, rel=1e-9) and err == pytest.approx(0.0, abs=1e-6)
            count += 1
    assert count == 96
    # the probe box alone is enough (three different extents)
    err, s, mm = pure.measure_mapping([(fake_import(pure.PROBE_BOX, 100.0, FLIP_Y), pure.PROBE_BOX)])
    assert mm == FLIP_Y and s == pytest.approx(100.0)


def test_resolve_geo_origin(mods):
    pure = mods.pure
    manifest = {"origin": {"lat": 37.562, "lon": 126.925, "height_ellipsoidal": 50.0}}
    assert pure.resolve_geo_origin(None, (1.0, 2.0, 3.0), manifest, None) == ((1.0, 2.0, 3.0), "kept")
    assert pure.resolve_geo_origin(None, None, manifest, None) == (
        (37.562, 126.925, 50.0),
        "spawned from zone origin (zone at level origin)",
    )
    assert pure.resolve_geo_origin("area", None, manifest, None) == (
        (37.56, 126.923, 40.0),
        "spec area origin",
    )
    assert pure.resolve_geo_origin("zone", (1.0, 2.0, 3.0), manifest, None) == (
        (37.562, 126.925, 50.0),
        "zone origin",
    )
    assert pure.resolve_geo_origin((1, 2, 3), None, manifest, None) == ((1.0, 2.0, 3.0), "given")
    seen = []

    def read_json(path):
        seen.append(path)
        return {"origin": {"lat": 37.55, "lon": 126.92, "height_ellipsoidal": 41.5}}

    assert pure.resolve_geo_origin("D:\\golmok_basemap\\yeonnam", None, manifest, read_json) == (
        (37.55, 126.92, 41.5),
        "basemap D:\\golmok_basemap\\yeonnam",
    )
    assert seen == ["D:/golmok_basemap/yeonnam/manifest.json"]
    with pytest.raises(ValueError):
        pure.resolve_geo_origin(42, None, manifest, None)


# ---- pre-transform ----------------------------------------------------------------------------------

OBJ_LINES = [
    "# 한글 주석\n",
    "mtllib scan.mtl\n",
    "o chunk\n",
    "v 1.5 -2.25 0.125\n",
    "v 3 4 5 0.5 0.25 0.75\n",
    "v -7 8 -9\r\n",
    "vt 0.1 0.2\n",
    "vn 0 0 1\n",
    "usemtl facade\n",
    "f 1/1/1 2/1/1 3/1/1\n",
    "\n",
]


def test_pretransform_obj_roundtrip_48_mappings(mods):
    pure = mods.pure
    for m in signed_permutations():
        for scale in (1.0, 100.0):
            a = pure.inverse_mapping_matrix(scale, m)
            flip = pure.det3(a) < 0
            out = list(pure.pretransform_obj_lines(OBJ_LINES, a))
            assert len(out) == len(OBJ_LINES)
            for src, dst in zip(OBJ_LINES, out, strict=True):
                key = src.split()[0] if src.split() else ""
                if key == "v":
                    toks, src_toks = dst.split(), src.split()
                    written = [float(t) for t in toks[1:4]]
                    imported = [scale * c for c in apply(m, written)]
                    want = apply(pure.TARGET, [float(t) for t in src_toks[1:4]])
                    assert np.allclose(imported, want, atol=1e-4), (m, scale, src)
                    assert toks[4:] == src_toks[4:]  # vertex colors / w survive
                    assert dst.endswith("\r\n") == src.endswith("\r\n")
                elif key == "vn":
                    assert dst.startswith("vn ") and len(dst.split()) == 4
                elif key == "f":
                    assert dst == ("f 3/1/1 2/1/1 1/1/1\n" if flip else src)
                else:
                    assert dst == src


def test_pretransform_obj_normals_and_winding(mods, tmp_path):
    pure = mods.pure
    a_flip = pure.inverse_mapping_matrix(100.0, IDENTITY)  # diag(1, -1, 1): det < 0
    assert pure.det3(a_flip) == -1.0 and pure.normal_matrix(a_flip) == FLIP_Y
    out = list(pure.pretransform_obj_lines(["vn 0 1 0\n", "vn 0.6 0 0.8\n", "f 1/1/1 2/2/2 3/3/3\n"], a_flip))
    assert out == [
        "vn 0.000000 -1.000000 0.000000\n",
        "vn 0.600000 0.000000 0.800000\n",
        "f 3/3/3 2/2/2 1/1/1\n",
    ]
    a_keep = pure.inverse_mapping_matrix(100.0, FLIP_Y)  # identity: det > 0
    assert a_keep == IDENTITY
    out = list(
        pure.pretransform_obj_lines(
            ["vn 0 1 0\n", "f 1/1/1 2/2/2 3/3/3\n", "f 4//4 5//5 6//6 7//7\n"], a_keep
        )
    )
    assert out == ["vn 0.000000 1.000000 0.000000\n", "f 1/1/1 2/2/2 3/3/3\n", "f 4//4 5//5 6//6 7//7\n"]
    # a scale-1 importer needs metre -> centimetre vertices; the normal matrix stays a unit permutation
    a_scaled = pure.inverse_mapping_matrix(1.0, IDENTITY)
    assert a_scaled == ((100.0, 0.0, 0.0), (0.0, -100.0, 0.0), (0.0, 0.0, 100.0))
    assert pure.normal_matrix(a_scaled) == FLIP_Y
    # streaming file copy: BOM dropped, CRLF kept, mtllib replaced, v lines counted
    src, dst = tmp_path / "in.obj", tmp_path / "out.obj"
    src.write_bytes(("\ufeff" + "".join(OBJ_LINES)).replace("\n", "\r\n").encode("utf-8"))
    assert pure.pretransform_obj_file(str(src), str(dst), a_flip, mtllib="SM_x.mtl") == 3
    text = dst.read_bytes().decode("utf-8")
    assert not text.startswith("\ufeff") and "\n" not in text.replace("\r\n", "")
    lines = text.split("\r\n")
    assert (
        lines[0] == "# 한글 주석"
        and lines[1] == "mtllib SM_x.mtl"
        and lines[3] == "v 1.500000 2.250000 0.125000"
    )
    assert lines[9] == "f 3/1/1 2/1/1 1/1/1"


def test_pretransform_glb_positions_normals_indices(mods):
    pure, sz = mods.pure, mods.sz
    boxes = [((0.0, 0.0, 0.0), (1.0, 2.0, 3.0)), ((5.0, 5.0, 5.0), (6.0, 7.0, 9.0))]
    data = sz.boxes_glb(boxes, "boxes")
    gltf0, pos0, nrm0, idx0 = read_glb(data)
    for m in (IDENTITY, FLIP_Y):
        a = pure.inverse_mapping_matrix(100.0, m)
        flip = pure.det3(a) < 0
        out = pure.pretransform_glb(data, a, rename="SM_test")
        assert len(out) % 4 == 0
        gltf, pos, nrm, idx = read_glb(out)
        ag, ug = pure.gltf_conjugate(a), pure.gltf_conjugate(pure.normal_matrix(a))
        assert np.allclose(pos, [apply(ag, p) for p in pos0], atol=1e-5)
        assert np.allclose(nrm, [apply(ug, n) for n in nrm0], atol=1e-6)
        assert np.array_equal(idx, idx0[:, [0, 2, 1]] if flip else idx0)
        acc = gltf["accessors"][0]
        assert np.allclose(acc["min"], pos.min(axis=0)) and np.allclose(acc["max"], pos.max(axis=0))
        assert gltf["meshes"][0]["name"] == "SM_test" and gltf["nodes"][0]["name"] == "SM_test"
        assert gltf["accessors"][1:] == gltf0["accessors"][1:] and gltf["bufferViews"] == gltf0["bufferViews"]
        assert gltf["buffers"] == gltf0["buffers"]
        # geometric and stored normals still agree (outward CCW winding survives the flip)
        for tri in idx:
            p0, p1, p2 = pos[tri]
            n = np.cross(p1 - p0, p2 - p0)
            assert n @ nrm[tri[0]] > 0
        assert flip == (m == IDENTITY)
        # the rewritten file yields the wanted UE bounds once the importer applies s*M
        lo, hi = pure.glb_bounds_enu(out)
        imported = [
            tuple(100.0 * c for c in apply(m, corner))
            for corner in itertools.product(*zip(lo, hi, strict=True))
        ]
        got = (
            tuple(min(c[i] for c in imported) for i in range(3)),
            tuple(max(c[i] for c in imported) for i in range(3)),
        )
        assert np.allclose(got, sz.expected_ue_bounds(boxes), atol=1e-3)
    # the identity matrix leaves geometry, winding and accessor bounds untouched (only names may change)
    _, pos_id, nrm_id, idx_id = read_glb(pure.pretransform_glb(data, IDENTITY))
    assert np.array_equal(pos_id, pos0) and np.array_equal(nrm_id, nrm0) and np.array_equal(idx_id, idx0)
    with pytest.raises(ValueError):
        pure.pretransform_glb(b"not a glb", IDENTITY)


def test_glb_bounds_and_triangle_count(mods):
    pure, sz = mods.pure, mods.sz
    box = ((1.0, 2.0, 3.0), (5.0, 9.0, 15.0))
    data = sz.boxes_glb([box], "SM_probe_glb")
    assert pure.glb_bounds_enu(data) == box
    assert pure.glb_triangle_count(data) == 12
    two = sz.boxes_glb([box, ((-1.0, -1.0, -1.0), (0.0, 0.0, 0.0))], "two")
    assert pure.glb_bounds_enu(two) == ((-1.0, -1.0, -1.0), (5.0, 9.0, 15.0))
    assert pure.glb_triangle_count(two) == 24


def test_gltf_conjugate(mods):
    pure = mods.pure
    g = pure.GLTF_G
    assert apply(g, (1.0, 2.0, 3.0)) == (1.0, 3.0, -2.0)  # ENU -> glTF (x, z, -y)
    points = [(1.0, 2.0, 3.0), (-4.5, 0.25, 7.0), (0.0, -1.0, 0.5)]
    for m in signed_permutations():
        a = pure.inverse_mapping_matrix(100.0, m)
        conj = pure.gltf_conjugate(a)
        for p in points:
            assert np.allclose(apply(conj, apply(g, p)), apply(g, apply(a, p)))
    assert pure.gltf_conjugate(IDENTITY) == IDENTITY


def test_png_size(mods):
    pure = mods.pure
    rows = [bytes([200, 60, 60] * 3) for _ in range(2)]
    data = write_png_rgb(3, 2, rows)
    assert pure.png_size(data[:24]) == (3, 2)
    assert pure.png_size(data) == (3, 2)
    assert (
        zlib.decompress(data[8 + 25 + 8 : -12 - 4]) == b"\x00" + rows[0] + b"\x00" + rows[1]
    )  # IDAT is zlib
    for bad in (b"", data[:20], b"\x89PNG\r\n\x1a\n" + b"\0" * 16, b"GIF89a" + b"\0" * 18):
        with pytest.raises(ValueError):
            pure.png_size(bad)


# ---- logs, results ----------------------------------------------------------------------------------


def test_log_formats_are_quoted_in_runbook(mods):
    pure = mods.pure
    text = "\n".join(p.read_text("utf-8") for p in RUNBOOKS)
    prefixes = pure.log_prefixes()
    for key, prefix in prefixes.items():
        assert prefix in text, f"{key}: {prefix!r} is not quoted in the runbooks"
    # full texts the PC session searches the Output Log for (zone_import._import_texture UDIM branches)
    for message in (
        "zone_import: WARNING texture T_facade: UDIM tiles not merged; using tile 1001 only (runbook #4)",
        "zone_import: WARNING texture T_facade: UDIM merge could not be verified by size (runbook #4)",
        "(merged by importer (size unknown))",
    ):
        assert message in text, message
    known = sorted(prefixes.values(), key=len, reverse=True)
    head = re.compile(r"^\s*(zone_import|interior_setup|spike_runner|basemap_import):")
    for path in RUNBOOKS:
        in_block = False
        for no, line in enumerate(path.read_text("utf-8").splitlines(), 1):
            if line.strip().startswith("```"):
                in_block = not in_block
                continue
            if in_block and head.match(line):
                assert any(line.strip().startswith(p) for p in known), f"{path.name}:{no}: {line.strip()}"


def test_result_json_and_cache_shape(mods):
    pure = mods.pure
    plan = {"zone_id": ZONE, "version": 1, "asset_folder": f"/Game/Golmok/Zones/{ZONE}/v1"}
    mappings = {"obj": (100.0, IDENTITY, 0.0), "glb": {"scale": 100.0, "m": FLIP_Y, "err": 0.5}}
    assets = [{"kind": "chunk", "asset": "/Game/x/SM_a", "ok": True, "detail": {"tris": 66}}]
    result = pure.result_json(plan, mappings, assets, ["w1"], "fbx")
    assert list(result) == [
        "schema", "zone_id", "version", "asset_folder", "route", "obj_mapping", "glb_mapping",
        "assets", "warnings", "interior",
    ]  # fmt: skip
    assert result["schema"] == 1 and result["route"] == "fbx" and result["interior"] is None
    assert result["obj_mapping"] == {
        "scale": 100.0,
        "m": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        "err": 0.0,
    }
    assert result["glb_mapping"]["m"][1] == [0.0, -1.0, 0.0] and result["glb_mapping"]["err"] == 0.5
    assert result["assets"] == assets and result["warnings"] == ["w1"]
    assert json.loads(json.dumps(result)) == result
    assert pure.importer_cache_valid(None, "5.8.3") is False
    assert pure.importer_cache_valid({"engine": "5.8.3", "obj": {}, "glb": {}}, "5.8.3") is True
    assert pure.importer_cache_valid({"engine": "5.8.3", "obj": {}}, "5.8.3") is False
    assert pure.importer_cache_valid({"engine": "5.8.2", "obj": {}, "glb": {}}, "5.8.3") is False
    assert (
        pure.fmt("zi.cache", state="hit", path="C:/x.json")
        == "zone_import: importer mapping cache hit -> C:/x.json"
    )
    with pytest.raises(KeyError):
        pure.fmt("zi.nope")
    assert pure.log_prefixes()["zi.warn"] == "zone_import: WARNING "
    assert pure.log_prefixes()["sr.cmd"] == "spike_runner: > "
    assert all(
        v.startswith(("zone_import: ", "interior_setup: ", "spike_runner: ", "basemap_import: "))
        for v in pure.log_prefixes().values()
    )
    line = pure.fmt(
        "zi.texture", asset="/Game/T", tiles=[1001, 1002], w=512, h=512, vt="on", how="merged by importer"
    )
    assert line == "zone_import: texture /Game/T tiles=[1001, 1002] size=512x512 vt=on (merged by importer)"


def test_summary_lines_mention_every_asset(mods):
    pure = mods.pure
    assets = [
        {"kind": "file", "asset": "Golmok/Zones/z/v1/manifest.json", "ok": True, "detail": {"bytes": 10}},
        {
            "kind": "texture",
            "asset": "/Game/z/Textures/T_facade",
            "ok": True,
            "detail": {"tiles": [1001], "vt": True},
        },
        {
            "kind": "material",
            "asset": "/Game/z/Materials/MI_facade",
            "ok": True,
            "detail": {"parent": "/Game/M"},
        },
        {"kind": "collision", "asset": "/Game/z/SM_z_collision", "ok": False, "detail": {}},
        {
            "kind": "chunk",
            "asset": "/Game/z/SM_c",
            "ok": True,
            "detail": {"tris": 66, "bounds_error_cm": 0.0},
        },
    ]
    lines = pure.summary_lines({"assets": assets})
    assert len(lines) == len(assets)
    for a in assets:
        assert sum(1 for line in lines if a["asset"] in line) == 1, a["asset"]
    assert [line.split()[1] for line in lines] == ["chunk", "collision", "texture", "material", "file"]
    assert "FAILED" in lines[1] and "ok" in lines[0]
    assert not any(line.startswith(("zone_import:", "interior_setup:", "spike_runner:")) for line in lines)


# ---- interior ---------------------------------------------------------------------------------------


def test_portal_pair_and_round_trip_on_fixtures(mods):
    pure = mods.pure
    parent, interior = zone_fixture("z_synthetic_001"), zone_fixture("z_synthetic_001_interior")
    pp, ip = pure.portal_pair(parent, interior)
    assert pp["id"] == "door_1" and ip["id"] == "door_out"
    check = pure.portal_round_trip_check(parent, interior)
    assert check["ok"] and check["dist_m"] < 0.01 and check["yaw_err_deg"] < 0.01
    assert check["parent_portal"] == "door_1" and check["interior_portal"] == "door_out"
    bad = json.loads(json.dumps(interior))
    bad["portals"][0]["pose_enu"]["yaw_deg"] = -80.0
    off = pure.portal_round_trip_check(parent, bad)
    assert not off["ok"] and off["yaw_err_deg"] == pytest.approx(10.0, abs=0.01)
    moved = json.loads(json.dumps(interior))
    moved["portals"][0]["pose_enu"]["position"] = [0.1, -3.5, 0.0]
    assert not pure.portal_round_trip_check(parent, moved)["ok"]
    assert pure.portal_round_trip_check(parent, moved, max_dist_m=0.2)["ok"]
    none = dict(interior, portals=[])
    with pytest.raises(ValueError):
        pure.portal_pair(parent, none)
    two = dict(interior, portals=[interior["portals"][0], interior["portals"][0]])
    with pytest.raises(ValueError):
        pure.portal_pair(parent, two)
    # ECEF helpers agree with the manifest's own origin_ecef and with numpy
    t = parent["transform"]
    assert np.allclose(pure.enu_to_ecef(t, (0.0, 0.0, 0.0)), parent["origin_ecef"])
    r = np.array(t).reshape(4, 4)
    assert np.allclose(pure.enu_to_ecef(t, (5.0, 9.5, 0.0)), r[:3, :3] @ [5.0, 9.5, 0.0] + r[:3, 3])
    assert np.allclose(pure.heading_ecef(t, 90.0), r[:3, 1])  # yaw 90 = north column


def test_interior_sublevel_specs(mods):
    pure = mods.pure
    interior = zone_fixture("z_synthetic_001_interior")
    specs = pure.interior_sublevel_specs(interior)
    assert len(specs) == 1
    (light,) = specs
    assert light["label"] == "Interior_Light_z_synthetic_001_interior" and light["kind"] == "point_light"
    assert light["location_cm"] == (0.0, 0.0, 250.0)
    assert light["intensity_cd"] == 3000.0 and light["kelvin"] == 3000.0
    assert light["tags"] == ["GolmokInteriorSetup"] == [pure.INTERIOR_SETUP_TAG]
    room = {"zone_id": "z_synthetic_scan_001_room", "layers": {"visual": {"chunks": [
        {"id": "c_e000_n000", "bbox_enu": [[0.0, 0.0, -0.2], [8.0, 6.8, 3.2]]}]}}}  # fmt: skip
    assert pure.interior_sublevel_specs(room)[0]["location_cm"] == (400.0, -340.0, 250.0)
    low = {
        "zone_id": "z_low",
        "layers": {"visual": {"chunks": [{"id": "c", "bbox_enu": [[0, 0, 0], [4, 4, 2.4]]}]}},
    }
    assert pure.interior_sublevel_specs(low)[0]["location_cm"] == (200.0, -200.0, 190.0)
    assert (
        "PostProcessVolume" in pure.FORBIDDEN_SUBLEVEL_CLASSES
        and "GolmokPortal" in pure.FORBIDDEN_SUBLEVEL_CLASSES
    )


# ---- spike ------------------------------------------------------------------------------------------


def test_viewpoints_presets_match_research_08(mods):
    pure, lp = mods.pure, mods.lp
    doc = RESEARCH_08.read_text("utf-8")
    names = pure.VIEWPOINT_NAMES
    assert len(names) == 10 and len(set(names)) == 10
    counts = {k: sum(1 for n in names if n.startswith(k + "_")) for k in ("far", "mid", "near")}
    m = re.search(r"원경 (\d+), 중경 (\d+), 근경\(0\.5m\) (\d+)", doc)
    assert m and (counts["far"], counts["mid"], counts["near"]) == tuple(int(v) for v in m.groups())
    assert all(pure.validate_name(n) == n for n in names)
    header, rows = table_after(doc, "### 시각 품질")
    assert rows == [row for row, _ in pure.QUALITY_ROWS]
    assert header[1:] == [pure.TAG_COLUMNS[t] for t in pure.TAGS]
    assert all(set(vps) <= set(names) for _, vps in pure.QUALITY_ROWS)
    cost_header, cost_rows = table_after(doc, "### 제작 비용")
    assert cost_rows == list(pure.COST_ROWS)
    assert cost_header[1:] == [pure.COST_COLUMNS[t] for t in pure.TAGS]
    cycle, presets = lp.load_presets()
    assert pure.DEFAULT_PRESETS == tuple(cycle)[:3] and "night" not in pure.DEFAULT_PRESETS
    condition = next(line for line in doc.splitlines() if "조명 프리셋" in line)
    assert all(p in condition for p in pure.DEFAULT_PRESETS)
    assert all(p in presets for p in pure.DEFAULT_PRESETS)


def test_layer_state_actor_group_jobs(mods):
    pure = mods.pure
    assert pure.layer_state("a") == {"zone_visual": True, "spike_b": False, "spike_c": False}
    assert pure.layer_state("b") == {"zone_visual": False, "spike_b": True, "spike_c": False}
    assert pure.layer_state("c") == {"zone_visual": False, "spike_b": False, "spike_c": True}
    assert pure.layer_state("ac") == {"zone_visual": True, "spike_b": False, "spike_c": True}
    with pytest.raises(ValueError):
        pure.layer_state("d")
    assert pure.spike_actor_group("Spike_b_lcc") == "spike_b"
    assert pure.spike_actor_group("Spike_c_tiles") == "spike_c"
    assert pure.spike_actor_group("Spike_x") is None and pure.spike_actor_group("Zone_x") is None
    assert pure.spike_actor_group("Spike_b") is None
    jobs = pure.capture_jobs(("a", "b"), ("p1", "p2"), ("n1", "n2"))
    assert jobs == [
        ("a", "p1", "n1"), ("a", "p1", "n2"), ("a", "p2", "n1"), ("a", "p2", "n2"),
        ("b", "p1", "n1"), ("b", "p1", "n2"), ("b", "p2", "n1"), ("b", "p2", "n2"),
    ]  # fmt: skip
    assert pure.missing_viewpoints({"mid_01": {}, "far_03": {}}) == [
        n for n in sorted(pure.VIEWPOINT_NAMES) if n not in ("mid_01", "far_03")
    ]
    assert pure.missing_viewpoints(dict.fromkeys(pure.VIEWPOINT_NAMES)) == []
    assert pure.perf_label("a", "clear_noon", "walk_01") == "a_clear_noon_walk_01"


def test_dwell_path_json_matches_cpp_layout(mods):
    pure = mods.pure
    text = pure.dwell_path_json(
        "vp_far_01",
        "L_ZoneTest",
        (17670.59, -22398.0, 1149.364),
        [0.0, -10.0, 90.0],
        created="2026-09-24T00:00:00Z",
    )
    layout = re.compile(
        r'^\{"version": 1, "name": "vp_far_01", "level": "L_ZoneTest", "hz": 10, '
        r'"created": "2026-09-24T00:00:00Z", "samples": \[\n'
        r'\{"t": 0\.000, "p": \[[^\]]*\], "r": \[[^\]]*\]\},\n'
        r'\{"t": 600\.000, "p": \[[^\]]*\], "r": \[[^\]]*\]\}\n\]\}\n$'
    )
    assert layout.match(text), text
    doc = json.loads(text)
    assert doc["samples"][0]["p"] == [17670.59, -22398.0, 1149.36]
    assert doc["samples"][0]["r"] == [
        -10.0,
        90.0,
        0.0,
    ]  # [pitch, yaw, roll] from viewpoints' [roll, pitch, yaw]
    assert doc["samples"][1]["t"] == 600.0 and doc["samples"][0]["t"] == 0.0
    assert (
        text.splitlines()[1]
        == '{"t": 0.000, "p": [17670.59, -22398.00, 1149.36], "r": [-10.000, 90.000, 0.000]},'
    )
    cpp = STATS_MATH_H.read_text("utf-8")
    for needle in ('"version"', '"samples"', '"t"', '"p"', '"r"'):
        assert needle in cpp, needle
    short = pure.dwell_path_json("vp_x", "L", (0, 0, 0), (0, 0, 0), dwell_s=30, hz=5)
    assert '"hz": 5' in short and '{"t": 30.000' in short and json.loads(short)["created"]
    with pytest.raises(ValueError):
        pure.dwell_path_json("bad name", "L", (0, 0, 0), (0, 0, 0))


def test_validate_name_exec_cmds_game_command_line(mods):
    pure = mods.pure
    assert pure.validate_name("far_01") == "far_01" and pure.validate_name("walk-01") == "walk-01"
    for bad in ("walk 01", "a,b", "", "x" * 65, 'q"'):
        with pytest.raises(ValueError):
            pure.validate_name(bad)
    assert (
        pure.exec_cmds(["golmok.hud 0", "golmok.tod clear_noon"])
        == '-ExecCmds="golmok.hud 0, golmok.tod clear_noon"'
    )
    with pytest.raises(ValueError):
        pure.exec_cmds(["golmok.tod a,b"])
    with pytest.raises(ValueError):
        pure.exec_cmds(['say "x"'])
    argv = pure.game_command_line(
        "C:/UE/UnrealEditor.exe", "D:/golmok/Golmok.uproject", "/Game/Golmok/Maps/L_ZoneTest",
        walk="walk_01", preset="clear_noon", log_path="D:/golmok/Saved/Golmok/spike/game_a.log",
    )  # fmt: skip
    assert argv == [
        "C:/UE/UnrealEditor.exe", "D:/golmok/Golmok.uproject", "/Game/Golmok/Maps/L_ZoneTest", "-game",
        "-RenderOffscreen", "-ResX=1920", "-ResY=1080", "-ForceRes", "-ExitAfterCsvProfiling", "-unattended",
        "-nosplash",
        '-ExecCmds="golmok.hud 0, golmok.tod clear_noon, golmok.path play walk_01 --csv"',
        "-abslog=D:/golmok/Saved/Golmok/spike/game_a.log",
    ]  # fmt: skip
    assert not any("csvCaptureFrames" in a for a in argv)
    assert "-ResX=2560" in pure.game_command_line(
        "e", "u", "m", walk="w", preset="p", res=(2560, 1440), log_path="l"
    )
    with pytest.raises(ValueError):
        pure.game_command_line("e", "u", "m", walk="walk 01", preset="p", log_path="l")


def test_saved_dir_candidates_newest_file(mods):
    pure = mods.pure
    both = pure.saved_dir_candidates("D:/P/Saved/", "C:/Users/x/AppData/Local")
    assert both == ["D:/P/Saved", "C:/Users/x/AppData/Local/UnrealEngine/5.8/Saved"]
    assert pure.saved_dir_candidates("D:\\P\\Saved", None) == ["D:/P/Saved"]
    assert pure.csv_dirs(both) == [
        "D:/P/Saved/Profiling/CSV",
        "C:/Users/x/AppData/Local/UnrealEngine/5.8/Saved/Profiling/CSV",
    ]
    assert pure.path_dirs(both) == [
        "D:/P/Saved/Golmok/Paths",
        "C:/Users/x/AppData/Local/UnrealEngine/5.8/Saved/Golmok/Paths",
    ]
    files = {
        "D:/P/Saved/Profiling/CSV/Profile(1).csv": 10.0,
        "D:/P/Saved/Profiling/CSV/Profile(2).csv": 50.0,
        "C:/Users/x/AppData/Local/UnrealEngine/5.8/Saved/Profiling/CSV/Profile(3).csv": 70.0,
        "C:/Users/x/AppData/Local/UnrealEngine/5.8/Saved/Profiling/CSV/old.csv": 90.0,
    }

    def glob(pattern):
        folder, name = pattern.rsplit("/", 1)
        prefix = name.split("*", 1)[0]
        return sorted(
            f for f in files if f.rsplit("/", 1)[0] == folder and f.rsplit("/", 1)[1].startswith(prefix)
        )

    newest = pure.newest_file(
        pure.csv_dirs(both), "Profile*.csv", 20.0, files.__contains__, files.__getitem__, glob
    )
    assert newest == "C:/Users/x/AppData/Local/UnrealEngine/5.8/Saved/Profiling/CSV/Profile(3).csv"
    assert (
        pure.newest_file(
            pure.csv_dirs(both), "Profile*.csv", 80.0, files.__contains__, files.__getitem__, glob
        )
        is None
    )
    only_project = pure.newest_file(
        pure.csv_dirs(both[:1]), "Profile*.csv", 0.0, files.__contains__, files.__getitem__, glob
    )
    assert only_project == "D:/P/Saved/Profiling/CSV/Profile(2).csv"


def test_powershell_script_quoting_and_layout(mods):
    pure = mods.pure
    assert pure.ps_quote("D:\\my dir\\Golmok.uproject") == "'\"D:\\my dir\\Golmok.uproject\"'"
    assert pure.ps_quote("D:\\it's\\x") == "'D:\\it''s\\x'"  # no spaces: only the PowerShell quoting
    assert pure.ps_quote("D:\\it's here\\my x") == "'\"D:\\it''s here\\my x\"'"
    assert pure.ps_quote('-ExecCmds="a, b"') == "'-ExecCmds=\"a, b\"'"
    assert pure.ps_quote("-abslog=D:\\my dir\\x.log") == "'-abslog=\"D:\\my dir\\x.log\"'"
    assert pure.ps_quote("-game") == "'-game'"
    saved = "D:/my project/Saved"
    candidates = pure.saved_dir_candidates(saved, "C:/Users/me/AppData/Local")
    runs = []
    for tag in ("a", "b"):
        label = pure.perf_label(tag, "clear_noon", "walk_01")
        argv = pure.game_command_line(
            "C:/UE/UnrealEditor.exe", "D:/my project/Golmok.uproject", f"/Game/Golmok/Maps/L_Spike_{tag}",
            walk="walk_01", preset="clear_noon", log_path=f"{saved}/Golmok/spike/game_{label}.log",
        )  # fmt: skip
        runs.append({"label": label, "argv": argv})
    script = pure.powershell_script(
        runs, [f"{saved}/Golmok/Paths/walk_01.json"], candidates, f"{saved}/Golmok/spike/csv", 900
    )
    lines = script.splitlines()
    assert lines[0] == "# generated by golmok.spike_runner.game_scripts - do not edit"
    assert lines[1] == "$ErrorActionPreference = 'Continue'"
    assert (
        lines[2] == "$pathDirs = @('D:\\my project\\Saved\\Golmok\\Paths', "
        "'C:\\Users\\me\\AppData\\Local\\UnrealEngine\\5.8\\Saved\\Golmok\\Paths')"
    )
    assert (
        lines[3] == "$csvDirs = @('D:\\my project\\Saved\\Profiling\\CSV', "
        "'C:\\Users\\me\\AppData\\Local\\UnrealEngine\\5.8\\Saved\\Profiling\\CSV')"
    )
    assert (
        lines[4].startswith("foreach ($d in $pathDirs) {")
        and lines[4].count("Copy-Item -Force 'D:\\my project\\Saved\\Golmok\\Paths\\walk_01.json' $d") == 1
    )
    assert (
        lines[5]
        == "New-Item -ItemType Directory -Force -Path 'D:\\my project\\Saved\\Golmok\\spike\\csv' | Out-Null"
    )
    assert lines[6] == "function Invoke-GolmokRun($label, $exe, $argv, $timeoutSec, $log) {"
    body = lines[7 : lines.index("}")]
    assert any("Start-Process -FilePath $exe -ArgumentList $argv -PassThru -NoNewWindow" in b for b in body)
    assert any("$p.WaitForExit($timeoutSec * 1000)" in b and "$p.Kill()" in b for b in body)
    assert any("-Filter 'Profile*.csv'" in b and "$_.LastWriteTime -ge $t0" in b for b in body)
    assert any("'GolmokDebugSubsystem: csv:'" in b and "runbook #17" in b for b in body)
    run_lines = [line for line in lines if line.startswith("Invoke-GolmokRun ")]
    assert len(run_lines) == 2
    assert run_lines[0].startswith(
        "Invoke-GolmokRun 'a_clear_noon_walk_01' 'C:/UE/UnrealEditor.exe' "
        "@('\"D:/my project/Golmok.uproject\"', '/Game/Golmok/Maps/L_Spike_a', '-game',"
    )
    assert (
        "'-ExecCmds=\"golmok.hud 0, golmok.tod clear_noon, golmok.path play walk_01 --csv\"'" in run_lines[0]
    )
    assert run_lines[0].count("-ExecCmds") == 1
    assert run_lines[0].endswith(") 900 'D:/my project/Saved/Golmok/spike/game_a_clear_noon_walk_01.log'")
    assert "'-abslog=\"D:/my project/Saved/Golmok/spike/game_a_clear_noon_walk_01.log\"'" in run_lines[0]
    assert lines[-1] == (
        'Write-Output \'golmok-perf "D:\\my project\\Saved\\Golmok\\spike\\csv\\a_clear_noon_walk_01.csv" '
        '"D:\\my project\\Saved\\Golmok\\spike\\csv\\b_clear_noon_walk_01.csv" '
        "--label a_clear_noon_walk_01 --label b_clear_noon_walk_01 --markdown'"
    )
    assert script.endswith("\n") and "\r" not in script


def test_screenshot_paths(mods):
    pure = mods.pure
    ini = DEFAULT_GAME_INI.read_text("utf-8")
    folder = re.search(r"^ScreenshotFolder=(.+)$", ini, re.MULTILINE).group(1).strip()
    assert pure.SCREENSHOT_FOLDER == folder
    multiplier = int(re.search(r"^ScreenshotMultiplier=(\d+)$", ini, re.MULTILINE).group(1))
    assert pure.SCREENSHOT_MULTIPLIER == multiplier
    pfolder = re.search(r"^PathFolder=(.+)$", ini, re.MULTILINE).group(1).strip()
    assert pure.PATH_FOLDER == pfolder
    assert pure.path_dirs(["D:/P/Saved"]) == [f"D:/P/Saved/{pfolder}"]
    assert (
        pure.screenshot_path("D:/P/Saved", "a", "clear_noon", "far_01")
        == f"D:/P/Saved/{folder}/a/clear_noon/far_01.png"
    )
    assert (
        pure.screenshot_path("D:\\P\\Saved\\", "b", None, "mid_02")
        == f"D:/P/Saved/{folder}/b/current/mid_02.png"
    )
    assert pure.screenshot_fallback_path("D:/x/far_01.png") == "D:/x/far_0100000.png"
    assert pure.screenshot_fallback_path("D:/x/far_01.PNG") == "D:/x/far_0100000.png"
    assert pure.PIE_WINDOW[0] * multiplier == 2560 and pure.PIE_WINDOW[1] * multiplier == 1440


def test_contact_sheet_html(mods):
    pure = mods.pure
    presets, names = ("clear_noon", "night"), ("far_01", "far_02", "far_03")

    def image_rel(tag, preset, name):
        return None if tag == "c" else f"{tag}\\{preset}\\{name}.png"

    html_text = pure.contact_sheet_html(pure.TAGS, presets, names, image_rel, title="Golmok <spike> & co")
    assert html_text.startswith("<!doctype html>") and '<meta charset="utf-8">' in html_text
    assert html_text.count("<table>") == 2 and html_text.count("</table>") == 2
    assert html_text.count("<img ") == 2 * 3 * 3
    assert html_text.count('<td class="missing">missing</td>') == 2 * 1 * 3
    assert '<h2 id="clear_noon">clear_noon</h2>' in html_text and '<h2 id="night">night</h2>' in html_text
    assert 'href="a/clear_noon/far_01.png"' in html_text and 'alt="a/clear_noon/far_01"' in html_text
    assert "\\" not in html_text and 'loading="lazy"' in html_text
    assert "<h1>Golmok &lt;spike&gt; &amp; co</h1>" in html_text
    for column in pure.TAG_COLUMNS.values():
        assert f"<th>{column}</th>" in html_text
    assert "<th>photo</th>" not in html_text and "http" not in html_text
    with_photos = pure.contact_sheet_html(
        ("a",), presets, names, image_rel, photo_rel=lambda n: pure.file_uri(f"D:/photos/{n} shot.jpg")
    )
    assert "<th>photo</th>" in with_photos and 'href="file:///D:/photos/far_01%20shot.jpg"' in with_photos
    assert (
        pure.file_uri("/x/y.jpg") == "file:///x/y.jpg"
        and pure.file_uri("D:\\x\\y#1.jpg") == "file:///D:/x/y%231.jpg"
    )
    assert pure.contact_sheet_html(pure.TAGS, presets, names, image_rel) == pure.contact_sheet_html(
        pure.TAGS, presets, names, image_rel
    )


def test_report_template_matches_research_08(mods):
    pure = mods.pure
    perf_report = pytest.importorskip("golmok_tools.perf_report")
    doc = RESEARCH_08.read_text("utf-8")
    text = pure.report_template()
    header, rows = table_after(text, "### 시각 품질")
    doc_header, doc_rows = table_after(doc, "### 시각 품질")
    assert header == doc_header and rows == doc_rows
    cost_header, cost_rows = table_after(text, "### 제작 비용")
    doc_cost_header, doc_cost_rows = table_after(doc, "### 제작 비용")
    assert cost_header == doc_cost_header and cost_rows == doc_cost_rows
    perf_lines = perf_report.to_markdown([]).splitlines()
    assert perf_lines[0] == pure.PERF_HEADER and perf_lines[1] == pure.PERF_SEPARATOR
    perf_header, _ = table_after(text, "### 성능")
    assert "| " + " | ".join(perf_header) + " |" == perf_lines[0]
    assert "### 시점↔행 매핑" in text and "| 얇은 구조물(전선·철망·난간) | mid_04 |" in text
    assert "2560×1440" in text and all(p in text for p in pure.DEFAULT_PRESETS) and "far_01" in text
    assert "contact_sheet.html#clear_noon" in text
    assert "golmok-perf" in text and "--markdown" in text
    markdown = perf_report.to_markdown(
        [perf_report.Summary("a_clear_noon_walk_01", 9000, 150.0, 120.0, 6.5, 8.0, 2.0, 6.0, 5.5)]
    )
    filled = pure.report_template(perf_markdown=markdown, csv_labels=["a_clear_noon_walk_01"])
    assert filled.count(pure.PERF_HEADER) == 1 and "| a_clear_noon_walk_01 | 9000 | 150.0 |" in filled
    assert "golmok-perf" not in filled
    labelled = pure.report_template(csv_labels=["a_clear_noon_walk_01", "b_clear_noon_walk_01"])
    assert (
        '"Saved/Golmok/spike/csv/a_clear_noon_walk_01.csv"' in labelled
        and "--label b_clear_noon_walk_01" in labelled
    )


def test_no_unreal_api_outside_touchpoint_list(mods):
    api = re.compile(r"unreal\.([A-Za-z_]\w*)")
    known = {"log", "log_warning", "log_error"}
    for name in ("basemap_import", "synthetic_zone", "viewpoints", "lighting", "setup_dev_level"):
        known |= set(api.findall((GOLMOK_DIR / f"{name}.py").read_text("utf-8")))
    materials_src = (GOLMOK_DIR / "materials.py").read_text("utf-8")
    marker = "def build_zone_scan_material"
    old_materials, new_materials = (
        materials_src.split(marker, 1) if marker in materials_src else (materials_src, "")
    )
    known |= set(api.findall(old_materials))
    runbook = RUNBOOKS[0].read_text("utf-8")
    table = runbook[runbook.index("불확실 API") :]
    known |= set(api.findall(table))
    violations = []
    for name in ("zone_import", "interior_setup", "spike_runner"):
        for no, line in enumerate((GOLMOK_DIR / f"{name}.py").read_text("utf-8").splitlines(), 1):
            violations += [f"{name}.py:{no}: unreal.{n}" for n in api.findall(line) if n not in known]
    for no, line in enumerate(new_materials.splitlines(), 1):
        violations += [
            f"materials.py (new functions) line {no}: unreal.{n}" for n in api.findall(line) if n not in known
        ]
    assert violations == []
