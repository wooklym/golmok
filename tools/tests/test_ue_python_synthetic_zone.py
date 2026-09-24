"""Pure parts of unreal/.../golmok/synthetic_zone.py (GLB writer, geometry, importer pre-transform) with a
stub `unreal` module, same pattern as test_unreal_basemap_mapping.py."""

import importlib
import itertools
import json
import struct
import sys
import types
from pathlib import Path

import numpy as np
import pytest

PY_DIR = Path(__file__).resolve().parents[2] / "unreal" / "Golmok" / "Content" / "Python"
MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "unreal/Golmok/Content/Golmok/Zones/z_synthetic_001/v1/manifest.json"
)
BLOCKERS = MANIFEST.parent / "blockers.json"


@pytest.fixture(scope="module")
def mod():
    sys.modules.setdefault("unreal", types.ModuleType("unreal"))
    sys.path.insert(0, str(PY_DIR))
    try:
        yield importlib.import_module("golmok.synthetic_zone")
    finally:
        sys.path.remove(str(PY_DIR))


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


def test_boxes_glb_is_valid_and_y_up(mod):
    pygltflib = pytest.importorskip("pygltflib")
    boxes = [((-20.0, -10.0, 0.0), (-7.0, 10.0, 12.0)), ((1.0, 2.0, 3.0), (2.0, 3.0, 4.0))]
    data = mod.boxes_glb(boxes, "chunk_00")
    gltf, pos, nrm, idx = read_glb(data)
    assert gltf["meshes"][0]["name"] == "chunk_00" and len(gltf["meshes"]) == 1
    assert len(pos) == 48 and len(idx) == 24
    # ENU (x, y, z) -> glTF (x, z, -y): east stays x, up becomes +y, north becomes -z
    acc = gltf["accessors"][0]
    assert acc["min"] == [-20.0, 0.0, -10.0] and acc["max"] == [2.0, 12.0, 10.0]
    # outward CCW winding: geometric normal agrees with the stored normal
    for tri in idx:
        a, b, c = pos[tri]
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n)
        assert n @ nrm[tri[0]] > 0.99
    # a real glTF parser accepts it
    g = pygltflib.GLTF2.load_from_bytes(data)
    assert g.accessors[2].count == 72


def test_synthetic_geometry_matches_fixture_and_blockers(mod):
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    blockers = json.loads(BLOCKERS.read_text("utf-8"))
    geometry = mod.synthetic_geometry(manifest)
    names = {f"SM_{c['id']}" for c in manifest["layers"]["visual"]["chunks"]} | {
        f"SM_{manifest['zone_id']}_collision"
    }
    assert set(geometry) == names
    # every wall box stays inside its chunk bbox
    for chunk in manifest["layers"]["visual"]["chunks"]:
        lo, hi = chunk["bbox_enu"]
        for blo, bhi in geometry[f"SM_{chunk['id']}"]:
            assert all(lo[i] - 1e-9 <= blo[i] <= bhi[i] <= hi[i] + 1e-9 for i in range(3))
    # the door opening is exactly where the glass blocker sits (center +- size/2), so the blocker box fills it
    plane = blockers["planes"][0]
    cx, cy, cz = plane["center_enu"]
    w, h = plane["size_m"]
    assert mod.OPENING_X == (cx - w / 2, cx + w / 2) and mod.OPENING_Z == (cz - h / 2, cz + h / 2)
    assert mod.WALL_Y[1] == cy  # wall face at the plane
    # nothing solid inside the opening in chunk_00 or in the collision mesh
    probe = (cx, cy - 0.1, cz)
    for name in ("SM_chunk_00", f"SM_{manifest['zone_id']}_collision"):
        for lo, hi in geometry[name]:
            assert not all(lo[i] < probe[i] < hi[i] for i in range(3)), (name, lo, hi)
    # the floor slab covers the footprint (+-22.6 m E-W, +-10 m N-S) at z <= 0
    floor = geometry[f"SM_{manifest['zone_id']}_collision"][0]
    assert floor[0][0] <= -20 and floor[1][0] >= 20 and floor[0][1] <= -10 and floor[1][1] >= 10
    assert floor[1][2] == 0.0


def test_pretransform_cancels_measured_importer_mapping(mod):
    """For every signed permutation and scale, pretransform then 'import' yields TARGET * ENU."""
    lo, hi = (-20.0, -10.0, 0.0), (-7.0, 10.0, 12.0)
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1.0, -1.0), repeat=3):
            m = [[0.0] * 3 for _ in range(3)]
            for row, col in enumerate(perm):
                m[row][col] = signs[row]
            m = tuple(tuple(r) for r in m)
            for scale in (1.0, 100.0):
                wlo, whi = mod.pretransform_box(lo, hi, scale, m)
                imported = [
                    tuple(scale * v for v in mod.bm._apply(m, c))
                    for c in itertools.product(*zip(wlo, whi, strict=True))
                ]
                got = (
                    tuple(min(c[i] for c in imported) for i in range(3)),
                    tuple(max(c[i] for c in imported) for i in range(3)),
                )
                want = mod.expected_ue_bounds([(lo, hi)])
                assert np.allclose(got, want), (perm, signs, scale)
    assert mod.expected_ue_bounds([(lo, hi)]) == ((-2000.0, -1000.0, 0.0), (-700.0, 1000.0, 1200.0))
