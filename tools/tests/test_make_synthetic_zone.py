"""tools/scripts/make_synthetic_zone.py (WP-06 design §5-2): the synthetic scan zone the runbook imports.

One subprocess run (--interior, non-ASCII output folder) is shared by the file-checking tests; the determinism
and --check tests call main() in-process. expected.json is checked against the generated files, the spec §4 C
level coordinates are recomputed with golmok_tools.zone.transform, and the door/window/room layout is verified
on the OBJ and collision GLB geometry.
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import types
import zlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("scipy")
pytest.importorskip("fast_simplification")

from golmok_tools.mesh.objio import read_obj  # noqa: E402
from golmok_tools.zone import manifest as zm  # noqa: E402
from golmok_tools.zone import transform as T  # noqa: E402
from golmok_tools.zone.cli import main as zone_main  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "scripts" / "make_synthetic_zone.py"
PY_DIR = REPO / "unreal" / "Golmok" / "Content" / "Python"
sys.path.insert(0, str(SCRIPT.parent))
import make_synthetic_zone as msz  # noqa: E402

ZONE = "z_synthetic_scan_001"
ROOM = f"{ZONE}_room"
AREA_ORIGIN = (37.5600, 126.9230, 40.0)
# design §3-7: exactly these files (case included), nothing else
EXPECTED_FILES = {
    f"recon/{ZONE}/scan.obj",
    f"recon/{ZONE}/scan.mtl",
    f"recon/{ZONE}/tex/ground.png",
    f"recon/{ZONE}/tex/facade.1001.png",
    f"recon/{ZONE}/tex/facade.1002.png",
    f"recon/{ZONE}/tex/facade.1011.png",
    f"zones/{ZONE}/v1/manifest.json",
    f"zones/{ZONE}/v1/expected.json",
    f"zones/{ZONE}/v1/blockers.json",
    f"zones/{ZONE}/v1/blockers.glb",
    f"zones/{ZONE}/v1/collision.glb",
    f"zones/{ZONE}/v1/collision/c_e000_n000.glb",
    f"zones/{ZONE}/v1/collision/c_w001_n000.glb",
    f"zones/{ZONE}/v1/visual/c_e000_n000.obj",
    f"zones/{ZONE}/v1/visual/c_w001_n000.obj",
    f"zones/{ZONE}/v1/visual/scan.mtl",
    f"zones/{ZONE}/v1/visual/chunk_manifest.json",
    f"recon/{ROOM}/room.obj",
    f"recon/{ROOM}/room.mtl",
    f"recon/{ROOM}/tex/room.1001.png",
    f"zones/{ROOM}/v1/manifest.json",
    f"zones/{ROOM}/v1/expected.json",
    f"zones/{ROOM}/v1/collision.glb",
    f"zones/{ROOM}/v1/collision/c_e000_n000.glb",
    f"zones/{ROOM}/v1/visual/c_e000_n000.obj",
    f"zones/{ROOM}/v1/visual/room.mtl",
    f"zones/{ROOM}/v1/visual/chunk_manifest.json",
}
DOOR_HOLE = ((4.0, 6.0), (7.0, 7.2), (0.0, 2.2))  # x, y, z ranges (exterior m)
WINDOW_HOLE = ((-9.5, -6.5), (5.0, 5.2), (0.25, 2.75))
ROOM_IN_EXTERIOR = ((1.0, 7.2, -0.2), (9.0, 14.0, 3.2))


# ---- helpers ----


def _tree(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _png(path: Path) -> tuple[int, int, bytes]:
    """(w, h, RGB pixels) decoded with zlib only: 8-bit RGB, filter 0 on every row."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(data):
        length, tag = struct.unpack(">I4s", data[pos : pos + 8])
        body = data[pos + 8 : pos + 8 + length]
        if tag == b"IHDR":
            w, h, depth, color = struct.unpack(">IIBB", body[:10])
            assert (depth, color) == (8, 2)
        elif tag == b"IDAT":
            idat += body
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = 3 * w + 1
    assert len(raw) == stride * h and all(raw[y * stride] == 0 for y in range(h))
    return w, h, b"".join(raw[y * stride + 1 : (y + 1) * stride] for y in range(h))


def _pixel(img, x: int, y: int) -> tuple[int, int, int]:
    w, _, px = img
    i = 3 * (y * w + x)
    return tuple(px[i : i + 3])


def _glb(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """(positions ENU m (N, 3), triangles (M, 3)) of every primitive, following the accessors."""
    data = path.read_bytes()
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF" and version == 2 and total == len(data)
    json_len = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20 : 20 + json_len])
    bin_len = struct.unpack_from("<I", data, 20 + json_len)[0]
    blob = data[28 + json_len : 28 + json_len + bin_len]
    dtypes = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}

    def read(acc_index: int) -> np.ndarray:
        acc = gltf["accessors"][acc_index]
        view = gltf["bufferViews"][acc["bufferView"]]
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[acc["type"]]
        start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        arr = np.frombuffer(blob, dtype=dtypes[acc["componentType"]], count=acc["count"] * n, offset=start)
        return arr.reshape(acc["count"], n)

    pos, tris, off = [], [], 0
    for mesh in gltf["meshes"]:
        for prim in mesh["primitives"]:
            p = read(prim["attributes"]["POSITION"]).astype(np.float64)
            pos.append(np.stack([p[:, 0], -p[:, 2], p[:, 1]], axis=1))  # glTF Y-up -> ENU
            tris.append(read(prim["indices"]).reshape(-1, 3).astype(np.int64) + off)
            off += len(p)
    return np.vstack(pos), np.vstack(tris)


def _obj_bounds(path: Path) -> tuple[list[float], list[float]]:
    v = np.array(
        [[float(t) for t in line.split()[1:4]] for line in path.read_text(encoding="utf-8").splitlines()
         if line.startswith("v ")]
    )  # fmt: skip
    return v.min(axis=0).tolist(), v.max(axis=0).tolist()


def _level_ue(manifest: dict, enu) -> np.ndarray:
    to_area = T.zone_local_to_area_enu(T.from_row_major(manifest["transform"]), AREA_ORIGIN)
    return T.enu_to_ue(T.apply(to_area, enu))


def _inside(p, box) -> bool:
    (x0, x1), (y0, y1), (z0, z1) = box
    return x0 < p[0] < x1 and y0 < p[1] < y1 and z0 < p[2] < z1


def _normalized(path: Path, root: Path) -> bytes:
    """Text files with the output folder replaced (raw and JSON-escaped), PNGs as pixels, others as bytes."""
    data = path.read_bytes()
    if path.suffix == ".png":
        w, h, px = _png(path)
        return struct.pack(">II", w, h) + px
    if path.suffix in (".obj", ".mtl", ".json"):
        data = data.replace(b"\r\n", b"\n")
        for form in (json.dumps(str(root), ensure_ascii=False)[1:-1], str(root)):
            data = data.replace(form.encode("utf-8"), b"<OUT>")
    return data


# ---- fixtures ----


@pytest.fixture(scope="module")
def run(tmp_path_factory) -> SimpleNamespace:
    """One subprocess run with --interior into a non-ASCII folder (Windows CI: cp1252 console, argv)."""
    out = (tmp_path_factory.mktemp("synthetic") / "합성 zone").resolve()
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out), "--interior"],
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    ext = out / "zones" / ZONE / "v1"
    room = out / "zones" / ROOM / "v1"
    return SimpleNamespace(
        out=out,
        proc=proc,
        ext=ext,
        room=room,
        recon=out / "recon" / ZONE,
        recon_room=out / "recon" / ROOM,
        expected=_json(ext / "expected.json") if proc.returncode == 0 else None,
    )


@pytest.fixture(scope="module")
def sz():
    """golmok.synthetic_zone with an empty `unreal` stub (expected_ue_bounds == _pure.expected_ue_bounds)."""
    sys.modules.setdefault("unreal", types.ModuleType("unreal"))
    sys.path.insert(0, str(PY_DIR))
    try:
        yield importlib.import_module("golmok.synthetic_zone")
    finally:
        sys.path.remove(str(PY_DIR))


# ---- tests ----


def test_script_runs_in_subprocess_with_unicode_path(run):
    proc = run.proc
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.isascii() and proc.stderr == ""
    lines = proc.stdout.splitlines()
    wrote = [ln[len("wrote ") :] for ln in lines if ln.startswith("wrote ")]
    assert set(wrote) == EXPECTED_FILES and len(wrote) == len(EXPECTED_FILES)
    prefix = "next: import golmok.zone_import as zi; zi.run("
    assert lines[-1].startswith(prefix)
    arg = lines[-1][len(prefix) : lines[-1].index(", level=")]
    got = os.path.normpath(ast.literal_eval(arg))
    assert got == os.path.normpath(str(run.out / "zones" / ZONE))  # pasteable for a non-ASCII folder
    assert lines[-1].endswith('level="/Game/Golmok/Maps/L_ZoneTest06", geo_origin="area")')
    assert len(lines) == len(EXPECTED_FILES) + 1
    assert _tree(run.out) == EXPECTED_FILES  # exact set, case included, no extras


@pytest.mark.parametrize(
    "path",
    ["D:\\golmok_synth\\zones\\z", "/tmp/a b/z", "D:\\합성\\z", "D:\\x\\", 'D:\\"q"', "/tmp/\U0001f600/z"],
)
def test_path_literal_round_trips(path):
    lit = msz._path_literal(path)
    assert lit.isascii() and msz._ascii(lit) == lit
    assert ast.literal_eval(lit) == path
    if path in ("D:\\golmok_synth\\zones\\z", "/tmp/a b/z"):
        assert lit == f'r"{path}"'  # runbook §1 example form stays valid for ASCII folders


def test_output_validates_strict(run):
    assert zone_main(["validate", "--check-files", "--strict", str(run.ext / "manifest.json")]) == 0
    assert zone_main(["validate", "--check-files", "--strict", str(run.room / "manifest.json")]) == 0
    for vdir in (run.ext, run.room):
        rep = zm.check(zm.load(vdir / "manifest.json"), vdir / "manifest.json", check_files=True)
        assert rep.errors == [] and rep.warnings == []


def test_expected_json_matches_files(run):
    exp = run.expected
    assert exp["schema"] == 1 and exp["zone_id"] == ZONE and exp["version"] == 1
    assert exp["asset_folder"] == f"/Game/Golmok/Zones/{ZONE}/v1"
    assert exp["content_manifest"] == f"Golmok/Zones/{ZONE}/v1/manifest.json"
    for vdir, recon, doc in ((run.ext, run.recon, exp), (run.room, run.recon_room, exp["interior"])):
        cm = _json(vdir / "visual" / "chunk_manifest.json")
        by_id = {c["id"]: c for c in cm["chunks"]}
        assert set(doc["chunks"]) == set(by_id)
        for cid, chunk in doc["chunks"].items():
            obj = vdir / "visual" / f"{cid}.obj"
            faces = sum(1 for ln in obj.read_text(encoding="utf-8").splitlines() if ln.startswith("f "))
            assert faces == chunk["tris"] == by_id[cid]["tris"]
            assert np.allclose(_obj_bounds(obj), chunk["bbox_enu"], atol=1e-6)
            assert chunk["bbox_enu"] == by_id[cid]["bbox_enu"]
            assert chunk["udim_tiles"] == by_id[cid]["udim_tiles"]
            assert chunk["materials"] == by_id[cid]["materials"]
            assert chunk["asset"] == f"{doc['asset_folder']}/SM_{cid}"
        col = doc["collision"]
        assert col["mode"] == "chunks"
        assert len(_glb(vdir / "collision.glb")[1]) == col["total_tris"]
        assert sum(c["tris"] for c in col["chunks"].values()) == col["total_tris"]
        for cid, c in col["chunks"].items():
            pos, tris = _glb(vdir / "collision" / f"{cid}.glb")
            assert len(tris) == c["tris"]
            assert c["asset"] == f"{doc['asset_folder']}/SM_{doc['zone_id']}_collision_{cid}"
            assert np.allclose(pos.min(axis=0), doc["chunks"][cid]["bbox_enu"][0], atol=1e-5)
            assert np.allclose(pos.max(axis=0), doc["chunks"][cid]["bbox_enu"][1], atol=1e-5)
        for name, tex in doc["textures"].items():
            base = name[len("T_") :]
            files = {str(t): recon / "tex" / f"{base}.{t}.png" for t in tex["tiles"]} or {
                "single": recon / "tex" / f"{base}.png"
            }
            assert set(files) == set(tex["colors"])
            u = [(t - 1001) % 10 for t in tex["tiles"]] or [0]
            v = [(t - 1001) // 10 for t in tex["tiles"]] or [0]
            assert tex["canvas_blocks"] == [max(u) + 1, max(v) + 1]
            assert tex["canvas_px"] == [
                tex["tile_px"] * tex["canvas_blocks"][0],
                tex["tile_px"] * tex["canvas_blocks"][1],
            ]
            for key, path in files.items():
                img = _png(path)
                assert (img[0], img[1]) == (tex["tile_px"], tex["tile_px"])
                assert _pixel(img, img[0] // 2, img[1] // 2) == tuple(tex["colors"][key])
        assert doc["materials"] == sorted({f"MI_{m}" for c in cm["chunks"] for m in c["materials"]})
    blockers = _json(run.ext / "blockers.json")
    assert {p["id"] for p in blockers["planes"]} == set(exp["blockers"])
    for p in blockers["planes"]:
        b = exp["blockers"][p["id"]]
        assert (b["center_enu"], b["normal_enu"], b["size_m"]) == (
            p["center_enu"],
            p["normal_enu"],
            p["size_m"],
        )
        assert b["ue_rel_center_cm"] == [
            100 * p["center_enu"][0],
            -100 * p["center_enu"][1],
            100 * p["center_enu"][2],
        ]
        assert b["ue_extent_cm"] == [5.0, 50 * p["size_m"][0], 50 * p["size_m"][1]]
    assert exp["master_material"] == "/Game/Golmok/Materials/M_ZoneScan"
    assert exp["area_origin"] == list(AREA_ORIGIN)
    manifest = zm.load(run.ext / "manifest.json")
    o = manifest["origin"]
    assert exp["zone_origin"] == [o["lat"], o["lon"], o["height_ellipsoidal"]] == [37.562, 126.925, 50.0]
    # the room zone's own expected.json is the "interior" block
    assert _json(run.room / "expected.json") == {"schema": 1, **exp["interior"]}
    inn = exp["interior"]
    assert inn["sublevel"] == f"/Game/Golmok/Zones/{ROOM}/v1/L_{ROOM}"
    assert inn["light"] == {"label": f"Interior_Light_{ROOM}", "interior_local_cm": [400.0, -340.0, 250.0]}
    ro = zm.load(run.room / "manifest.json")["origin"]
    assert inn["origin"] == [ro["lat"], ro["lon"], ro["height_ellipsoidal"]]


def test_geometry_numbers(run):
    exp = run.expected
    assert set(exp["chunks"]) == {"c_w001_n000", "c_e000_n000"}
    assert [exp["chunks"][c]["tris"] for c in ("c_w001_n000", "c_e000_n000")] == [66, 66]
    assert exp["chunks"]["c_w001_n000"]["bbox_enu"] == [[-15.0, 0.0, -0.3], [0.0, 15.0, 5.0]]
    assert exp["chunks"]["c_e000_n000"]["bbox_enu"] == [[0.0, 0.0, 0.0], [15.0, 15.0, 6.0]]
    assert exp["chunks"]["c_w001_n000"]["udim_tiles"] == [1001, 1002]
    assert exp["chunks"]["c_e000_n000"]["udim_tiles"] == [1001, 1011]
    assert all(exp["chunks"][c]["materials"] == ["facade", "ground"] for c in exp["chunks"])
    assert exp["collision"] == {
        "mode": "chunks",
        "total_tris": 132,
        "chunks": {
            "c_e000_n000": {
                "asset": f"/Game/Golmok/Zones/{ZONE}/v1/SM_{ZONE}_collision_c_e000_n000",
                "tris": 66,
                "ue_bounds_cm": [[0.0, -1500.0, 0.0], [1500.0, 0.0, 600.0]],
            },
            "c_w001_n000": {
                "asset": f"/Game/Golmok/Zones/{ZONE}/v1/SM_{ZONE}_collision_c_w001_n000",
                "tris": 66,
                "ue_bounds_cm": [[-1500.0, -1500.0, -30.0], [0.0, 0.0, 500.0]],
            },
        },
    }
    assert exp["textures"]["T_facade"]["tiles"] == [1001, 1002, 1011]
    assert exp["textures"]["T_facade"]["canvas_blocks"] == [2, 2]
    assert exp["textures"]["T_facade"]["canvas_px"] == [512, 512]
    assert exp["textures"]["T_ground"] == {
        "tiles": [],
        "tile_px": 256,
        "canvas_blocks": [1, 1],
        "canvas_px": [256, 256],
        "colors": {"single": [120, 120, 120]},
    }
    assert exp["materials"] == ["MI_facade", "MI_ground"]
    assert exp["blockers"]["glass_1"]["ue_rel_center_cm"] == [-800.0, -500.0, 150.0]
    assert exp["blockers"]["glass_1"]["ue_extent_cm"] == [5.0, 150.0, 125.0]
    inn = exp["interior"]
    assert list(inn["chunks"]) == ["c_e000_n000"] and inn["chunks"]["c_e000_n000"]["tris"] == 60
    assert inn["chunks"]["c_e000_n000"]["bbox_enu"] == [[0.0, 0.0, -0.2], [8.0, 6.8, 3.2]]
    assert inn["chunks"]["c_e000_n000"]["udim_tiles"] == [1001]
    assert inn["collision"]["total_tris"] == 60 and inn["materials"] == ["MI_room"]
    assert inn["origin_in_parent_m"] == [1.0, 7.2, 0.0]
    # WP-03 output as the importer will see it
    cm = _json(run.ext / "visual" / "chunk_manifest.json")
    assert (
        cm["missing"] == {"mtl": [], "textures": []} and cm["mtl"] == ["scan.mtl"] and cm["total_tris"] == 132
    )
    mtl = (run.ext / "visual" / "scan.mtl").read_text(encoding="utf-8")
    assert f"map_Kd -bm 1 ../../../../recon/{ZONE}/tex/facade.<UDIM>.png\n" in mtl
    assert f"map_Kd ../../../../recon/{ZONE}/tex/ground.png\n" in mtl
    assert str(run.recon / "tex" / "ground.png") in cm["textures"]
    assert any(t.endswith("facade.<UDIM>.png") for t in cm["textures"])
    manifest = zm.load(run.ext / "manifest.json")
    assert [c["id"] for c in manifest["layers"]["visual"]["chunks"]] == ["c_w001_n000", "c_e000_n000"]
    assert manifest["layers"]["visual"]["format"] == "nanite_mesh"
    assert manifest["layers"]["collision"]["uri"] == "collision.glb"
    assert [c["uri"] for c in manifest["layers"]["collision"]["chunks"]] == [
        "collision/c_w001_n000.glb",
        "collision/c_e000_n000.glb",
    ]
    assert manifest["layers"]["blockers"] == {"uri": "blockers.json"}
    assert manifest["priority"] == 10 and manifest["attribution"] == ["합성 테스트 데이터 (WP-06)"]
    assert manifest["sources"] == [{"capture_id": "synthetic", "note": "make_synthetic_zone.py"}]
    # the raw scan: v/vt/f v/vt, ground before facade
    scan = (run.recon / "scan.obj").read_text(encoding="utf-8").splitlines()
    assert "mtllib scan.mtl" in scan
    assert [ln for ln in scan if ln.startswith("usemtl")] == ["usemtl ground", "usemtl facade"]
    assert sum(1 for ln in scan if ln.startswith("f ")) == 132
    assert all(re.fullmatch(r"f \d+/\d+ \d+/\d+ \d+/\d+", ln) for ln in scan if ln.startswith("f "))
    assert (run.recon / "scan.mtl").read_text(encoding="utf-8") == (
        "newmtl ground\nKd 1 1 1\nmap_Kd tex/ground.png\n\n"
        "newmtl facade\nKd 1 1 1\nmap_Kd -bm 1 tex/facade.<UDIM>.png\n"
    )
    assert (run.recon_room / "room.mtl").read_text(encoding="utf-8") == (
        "newmtl room\nKd 1 1 1\nmap_Kd tex/room.1001.png\n"
    )


def test_ue_bounds_in_expected_are_target_of_bbox(run, sz):
    """ue_bounds_cm = TARGET diag(100, -100, 100) on the ENU bbox (== _pure.expected_ue_bounds == sz's)."""
    exp = run.expected
    docs = [exp, exp["interior"]]
    for doc in docs:
        for chunk in doc["chunks"].values():
            lo, hi = chunk["bbox_enu"]
            want = sz.expected_ue_bounds([(tuple(lo), tuple(hi))])
            assert np.allclose(chunk["ue_bounds_cm"], want, atol=1e-6), chunk
            assert (
                chunk["ue_bounds_cm"][0][1] == -100.0 * hi[1]
                and chunk["ue_bounds_cm"][1][1] == -100.0 * lo[1]
            )
        for cid, col in doc["collision"]["chunks"].items():
            assert col["ue_bounds_cm"] == doc["chunks"][cid]["ue_bounds_cm"]
    assert exp["chunks"]["c_w001_n000"]["ue_bounds_cm"] == [[-1500.0, -1500.0, -30.0], [0.0, 0.0, 500.0]]
    assert exp["interior"]["chunks"]["c_e000_n000"]["ue_bounds_cm"] == [
        [0.0, -680.0, -20.0],
        [800.0, 0.0, 320.0],
    ]


def test_level_coordinates_match_spec_table_c(run):
    exp = run.expected
    manifest = zm.load(run.ext / "manifest.json")
    room = zm.load(run.room / "manifest.json")
    # docs/spec/zone-manifest.md §4 C, first row: zone-local (0,0,0) -> UE (17670.59, -22198.00, 999.37)
    assert exp["zone_root_ue_cm"] == [17670.59, -22198.0, 999.37]
    assert np.allclose(_level_ue(manifest, (0.0, 0.0, 0.0)), exp["zone_root_ue_cm"], atol=0.01)
    assert exp["zone_root_yaw_deg"] == 0.0
    assert np.allclose(_level_ue(manifest, (0.0, 2.0, 1.5)), exp["player_start_ue_cm"], atol=0.01)
    assert exp["player_start_ue_cm"] == [17670.59, -22398.0, 1149.36]
    glass = exp["blockers"]["glass_1"]
    assert np.allclose(_level_ue(manifest, glass["center_enu"]), glass["level_ue_cm"], atol=0.01)
    assert glass["level_ue_cm"] == [16870.59, -22697.99, 1149.37]
    inn = exp["interior"]
    assert np.allclose(_level_ue(room, (0.0, 0.0, 0.0)), inn["zone_root_ue_cm"], atol=0.01)
    assert inn["zone_root_ue_cm"] == [17770.58, -22918.0, 999.34]
    pair = inn["portal_pair"]
    assert np.allclose(_level_ue(manifest, pair["parent_enu"]), pair["level_ue_cm"], atol=0.01)
    assert np.allclose(_level_ue(room, pair["interior_enu"]), pair["level_ue_cm"], atol=0.01)
    assert pair["level_ue_cm"] == [18170.58, -22898.01, 999.33]
    # the UE actor rotation is D R D with R ~ identity (two ENU frames ~290 m apart): yaw within 0.01 deg
    m = T.ue_actor_matrix(T.zone_local_to_area_enu(T.from_row_major(manifest["transform"]), AREA_ORIGIN))
    assert abs(np.degrees(np.arctan2(m[1, 0], m[0, 0]))) < 0.01


def test_door_hole_and_room_do_not_overlap(run):
    mesh = read_obj(run.recon / "scan.obj")
    assert mesh.n_faces == 132 and mesh.materials == ["ground", "facade"]
    for c in mesh.face_centroids():
        assert not _inside(c, DOOR_HOLE) and not _inside(c, WINDOW_HOLE), c
    pos, tris = _glb(run.ext / "collision.glb")
    assert len(tris) == 132
    for c in pos[tris].mean(axis=1):
        assert not _inside(c, DOOR_HOLE) and not _inside(c, WINDOW_HOLE), c
    # the wall pieces around the holes are there (left/right/lintel of the door, sill + lintel of the window)
    solid = [(lo, hi) for _, _, lo, hi in msz.exterior_boxes()]
    assert len(solid) == 3 + 4 + 1

    def solid_at(p):
        return any(all(lo[i] < p[i] < hi[i] for i in range(3)) for lo, hi in solid)

    for p in ((5.0, 7.1, 1.0), (4.5, 7.1, 2.1), (-8.0, 5.1, 1.5), (-9.4, 5.1, 0.3)):
        assert not solid_at(p), p
    for p in (
        (3.5, 7.1, 1.0),
        (6.5, 7.1, 1.0),
        (5.0, 7.1, 2.3),
        (-8.0, 5.1, 0.1),
        (-8.0, 5.1, 2.9),
        (11.5, 3.0, 1.0),
    ):
        assert solid_at(p), p
    # the room (exterior coordinates x 1..9, y 7.2..14, z -0.2..3.2) meets no exterior box (open intervals)
    (rx0, ry0, rz0), (rx1, ry1, rz1) = ROOM_IN_EXTERIOR
    for lo, hi in solid:
        overlap = lo[0] < rx1 and rx0 < hi[0] and lo[1] < ry1 and ry0 < hi[1] and lo[2] < rz1 and rz0 < hi[2]
        assert not overlap, (lo, hi)
    room = zm.load(run.room / "manifest.json")
    ext = zm.load(run.ext / "manifest.json")
    e_m, r_m = T.from_row_major(ext["transform"]), T.from_row_major(room["transform"])
    (lo, hi) = room["layers"]["visual"]["chunks"][0]["bbox_enu"]
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    in_ext = T.ecef_to_enu(e_m, T.enu_to_ecef(r_m, corners))
    assert np.allclose(in_ext.min(axis=0), ROOM_IN_EXTERIOR[0], atol=1e-3)
    assert np.allclose(in_ext.max(axis=0), ROOM_IN_EXTERIOR[1], atol=1e-3)
    # door_1 sits in the middle of the door hole, on the wall's south face
    door_1 = next(p for p in ext["portals"] if p["id"] == "door_1")
    (x0, x1), (y0, _), _ = DOOR_HOLE
    assert door_1["pose_enu"]["position"] == [(x0 + x1) / 2, y0, 0.0] and door_1["radius_m"] == (x1 - x0) / 2


def test_interior_portal_round_trip(run):
    ext, inn = zm.load(run.ext / "manifest.json"), zm.load(run.room / "manifest.json")
    assert inn["kind"] == "interior" and inn["parent_zone"] == ZONE and inn["priority"] == 20
    assert inn["consent"] == {"type": "owner_consent", "record_id": "synthetic-consent-002"}
    e_m, i_m = T.from_row_major(ext["transform"]), T.from_row_major(inn["transform"])
    door_1 = next(p for p in ext["portals"] if p["to_zone"] == ROOM)
    door_out = next(p for p in inn["portals"] if p["to_zone"] == ZONE)
    assert (door_1["id"], door_out["id"]) == ("door_1", "door_out")
    assert door_1["pose_enu"] == {"position": [5.0, 7.0, 0.0], "yaw_deg": 90.0}
    assert door_out["pose_enu"] == {"position": [4.0, -0.2, 0.0], "yaw_deg": -90.0}
    # same point (< 5 mm) seen from both zones
    p_ecef = T.enu_to_ecef(e_m, door_1["pose_enu"]["position"])
    q_ecef = T.enu_to_ecef(i_m, door_out["pose_enu"]["position"])
    assert np.linalg.norm(p_ecef - q_ecef) < 0.005
    assert np.abs(T.ecef_to_enu(i_m, p_ecef) - door_out["pose_enu"]["position"]).max() < 0.005
    # opposite headings (yaw error < 1 deg): angle between the ECEF forward vectors is 180 deg
    f1 = e_m[:3, :3] @ (T.rot_z(door_1["pose_enu"]["yaw_deg"]) @ [1.0, 0.0, 0.0])
    f2 = i_m[:3, :3] @ (T.rot_z(door_out["pose_enu"]["yaw_deg"]) @ [1.0, 0.0, 0.0])
    angle = np.degrees(np.arccos(np.clip(f1 @ f2, -1.0, 1.0)))
    assert abs(180.0 - angle) < 1.0
    assert door_1["radius_m"] == door_out["radius_m"] == 1.0
    # the interior origin is exterior zone-local (1, 7.2, 0) within 1 mm
    assert np.abs(T.ecef_to_enu(e_m, i_m[:3, 3]) - [1.0, 7.2, 0.0]).max() < 0.001
    assert run.expected["interior"]["portal_pair"]["yaw_deg"] == [90.0, -90.0]


def test_png_tiles_named_colored_numbered(run):
    tiles = {
        run.recon / "tex" / "facade.1001.png": ((200, 60, 60), 1, True),
        run.recon / "tex" / "facade.1002.png": ((60, 200, 60), 2, True),
        run.recon / "tex" / "facade.1011.png": ((60, 60, 200), 3, True),
        run.recon / "tex" / "ground.png": ((120, 120, 120), 1, False),
        run.recon_room / "tex" / "room.1001.png": ((200, 200, 60), 1, True),
    }
    white, black = (255, 255, 255), (0, 0, 0)
    for path, (color, squares, numbered) in tiles.items():
        assert path.is_file(), path
        img = _png(path)
        w, h, _ = img
        assert (w, h) == (256, 256)
        assert _pixel(img, w - 8, h - 8) == color and _pixel(img, 8, h // 2) == color
        # 2 px black border all around
        for k in (0, 1):
            assert all(_pixel(img, x, k) == black and _pixel(img, x, h - 1 - k) == black for x in range(w))
            assert all(_pixel(img, k, y) == black and _pixel(img, w - 1 - k, y) == black for y in range(h))
        assert _pixel(img, 2, 2) != black
        # white squares top-left: runs of white on the row through their middle (y = 4 + 6)
        row = [_pixel(img, x, 10) == white for x in range(w)]
        runs = sum(1 for x in range(1, w) if row[x] and not row[x - 1])
        assert runs == squares, path
        assert all(_pixel(img, x, 10) == white for x in range(4, 16))  # first square is 12 px at x 4..15
        # digits: 5x7 font x8 = 40x56 px per glyph, 4 glyphs 8 px apart, centered, rows 100..156
        band = [_pixel(img, x, y) == white for y in range(100, 156) for x in range(36, 220)]
        assert any(band) is numbered, path
        assert not any(_pixel(img, x, y) == white for y in range(20, 100) for x in range(0, w, 4))
        assert not any(_pixel(img, x, y) == white for y in range(156, h) for x in range(0, w, 4))


def test_deterministic_and_check_mode(tmp_path):
    a, b = (tmp_path / "a").resolve(), (tmp_path / "b").resolve()
    assert msz.main(["--out", str(a), "--interior", "--quiet"]) == 0
    assert msz.main(["--out", str(b), "--interior", "--quiet"]) == 0
    assert _tree(a) == _tree(b) == EXPECTED_FILES
    for rel in sorted(EXPECTED_FILES):
        assert _normalized(a / rel, a) == _normalized(b / rel, b), rel
    assert msz.main(["--out", str(a), "--interior", "--check"]) == 0
    manifest = a / "zones" / ZONE / "v1" / "manifest.json"
    manifest.write_bytes(manifest.read_bytes().replace(b'"priority": 10', b'"priority": 11'))
    assert msz.main(["--out", str(a), "--interior", "--check"]) == 1
    assert msz.main(["--out", str(a), "--interior"]) == 2  # exists; use --force
    assert msz.main(["--out", str(a), "--interior", "--force", "--quiet"]) == 0
    assert msz.main(["--out", str(a), "--interior", "--check"]) == 0
    assert msz.main(["--out", str(a), "--check"]) == 1  # room files are extra without --interior
    assert msz.main(["--out", str(tmp_path / "none"), "--check"]) == 1


def test_round_trip_plan(run):
    """_pure.import_plan on the generated folder: no problems, chunks mode, asset set == expected.json."""
    import os

    sys.modules.setdefault("unreal", types.ModuleType("unreal"))
    sys.path.insert(0, str(PY_DIR))
    try:
        pure = importlib.import_module("golmok._pure")
    finally:
        sys.path.remove(str(PY_DIR))
    exp = run.expected
    for vdir, doc in ((run.ext, exp), (run.room, exp["interior"])):
        version_dir, version = pure.resolve_zone_dir(
            str(vdir), None, os.listdir, os.path.isdir, os.path.isfile
        )
        manifest = _json(Path(version_dir) / "manifest.json")
        chunk_manifest = _json(Path(version_dir) / "visual" / "chunk_manifest.json")
        plan = pure.import_plan(
            manifest,
            chunk_manifest,
            version_dir,
            exists=os.path.exists,
            listdir=os.listdir,
            read_text=lambda p: Path(p).read_text(encoding="utf-8"),
        )
        assert plan["problems"] == [] and plan["warnings"] == []
        assert plan["collision_mode"] == "chunks" and version == 1
        assert {c["asset"] for c in plan["chunks"]} == {c["asset"] for c in doc["chunks"].values()}
        assert {c["asset"] for c in plan["collision"]} == {
            c["asset"] for c in doc["collision"]["chunks"].values()
        }
        assert {t["asset"] for t in plan["textures"]} == {
            f"{doc['asset_folder']}/Textures/{name}" for name in doc["textures"]
        }
        assert {m["name"] for m in plan["materials"]} == set(doc["materials"])
        for t in plan["textures"]:
            assert list(t["canvas_blocks"]) == doc["textures"][t["name"]]["canvas_blocks"]
        for c in plan["chunks"]:
            assert c["expected_ue_bounds_cm"] == doc["chunks"][c["id"]]["ue_bounds_cm"]
            assert pure.expected_ue_bounds(c["bbox_enu"]) == tuple(
                tuple(v) for v in doc["chunks"][c["id"]]["ue_bounds_cm"]
            )
    # design §4-1 literals for the exterior plan (dict shape the runbook quotes)
    plan = _exterior_plan(pure, run)
    assert list(plan) == [
        "schema", "zone_id", "version", "kind", "parent_zone", "zone_dir", "asset_folder", "content_rel",
        "copy_files", "textures", "materials", "chunks", "collision_mode", "collision", "blockers",
        "sublevel", "problems", "warnings",
    ]  # fmt: skip
    assert (plan["schema"], plan["kind"], plan["parent_zone"]) == (1, "exterior", None)
    assert plan["sublevel"] is None
    assert plan["copy_files"] == ["blockers.json", "manifest.json"]
    assert plan["blockers"] == {"json": str(run.ext / "blockers.json").replace("\\", "/"), "planes": 1}
    assert [t["name"] for t in plan["textures"]] == ["T_facade", "T_ground"]
    assert [m["name"] for m in plan["materials"]] == ["MI_facade", "MI_ground"]
    assert [c["name"] for c in plan["chunks"]] == ["SM_c_e000_n000", "SM_c_w001_n000"]
    assert [c["name"] for c in plan["collision"]] == [
        f"SM_{ZONE}_collision_c_e000_n000",
        f"SM_{ZONE}_collision_c_w001_n000",
    ]
    facade, ground = plan["textures"]
    assert facade["tiles"] == [1001, 1002, 1011] and facade["block_coords"] == [[0, 0], [1, 0], [0, 1]]
    assert sorted(facade["files"]) == ["1001", "1002", "1011"] and facade["used_by"] == ["facade"]
    assert ground["tiles"] == [] and list(ground["files"]) == ["single"] and ground["used_by"] == ["ground"]
    assert all(c["mtllib"] == ["scan.mtl"] for c in plan["chunks"])
    assert all(c["slots"] == {"facade": "MI_facade", "ground": "MI_ground"} for c in plan["chunks"])
    assert {m["texture"] for m in plan["materials"]} == {"T_facade", "T_ground"}
    # the two manifests pass _pure.portal_round_trip_check (design §5-2)
    ext_manifest, room_manifest = zm.load(run.ext / "manifest.json"), zm.load(run.room / "manifest.json")
    check = pure.portal_round_trip_check(ext_manifest, room_manifest)
    assert check["ok"] and check["dist_m"] < 0.005
    assert (check["parent_portal"], check["interior_portal"]) == ("door_1", "door_out")


def _exterior_plan(pure, run) -> dict:
    import os

    manifest = _json(run.ext / "manifest.json")
    chunk_manifest = _json(run.ext / "visual" / "chunk_manifest.json")
    return pure.import_plan(
        manifest,
        chunk_manifest,
        str(run.ext),
        exists=os.path.exists,
        listdir=os.listdir,
        read_text=lambda p: Path(p).read_text(encoding="utf-8"),
    )


def test_no_dev_only_imports():
    source = SCRIPT.read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(PIL|trimesh|fast_simplification|pygltflib)\b", source, re.M)
    assert re.search(r"^\s*import numpy as np$", source, re.M)
    assert set(msz.FONT_5X7) == set("0123456789")
    for glyph in msz.FONT_5X7.values():
        assert len(glyph) == 7 and all(len(row) == 5 and set(row) <= {"0", "1"} for row in glyph)
    assert msz.DEFAULT_TILE_PX == 256 and msz.DEFAULT_ZONE_ID == ZONE
    assert set(msz.output_files(ZONE, interior=True)) == EXPECTED_FILES
    assert len(msz.output_files(ZONE, interior=False)) == 17


GITIGNORED_GENERATED = (
    "unreal/Golmok/Content/Golmok/Zones/z_synthetic_scan_001/v1/manifest.json",
    "unreal/Golmok/Content/Golmok/Zones/z_synthetic_scan_001/v1/blockers.json",
    "unreal/Golmok/Content/Golmok/Zones/z_synthetic_scan_001/v1/SM_c_0_0.uasset",
    "unreal/Golmok/Content/Golmok/Zones/z_synthetic_scan_001/v1/Textures/T_c_0_0_1001.uasset",
    "unreal/Golmok/Content/Golmok/Zones/z_synthetic_scan_001_room/v1/L_z_synthetic_scan_001_room.umap",
    "unreal/Golmok/Content/Golmok/Maps/L_Spike_b.umap",
    "unreal/Golmok/Content/Golmok/Maps/L_Spike_ac_BuiltData.uasset",
)


def test_gitignore_covers_generated_zone_assets():
    """pc-findings #6: what zone_import / interior_setup (from this script's output) and spike_runner
    regenerate is never committed; the product material (M_ZoneScan) and the tracked V-03 manifests stay."""
    lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "unreal/Golmok/Content/Golmok/Zones/z_synthetic_scan_001*/" in lines
    assert "unreal/Golmok/Content/Golmok/Maps/L_Spike_*" in lines
    git = shutil.which("git")
    if git is None or not (REPO / ".git").exists():
        return
    for rel in GITIGNORED_GENERATED:
        assert subprocess.run([git, "check-ignore", "-q", rel], cwd=REPO).returncode == 0, rel
    for rel in (
        "unreal/Golmok/Content/Golmok/Materials/M_ZoneScan.uasset",
        "unreal/Golmok/Content/Golmok/Zones/z_synthetic_001/v1/manifest.json",
    ):
        assert subprocess.run([git, "check-ignore", "-q", rel], cwd=REPO).returncode == 1, rel
