"""Pure parts of unreal/.../golmok/synthetic_zone.py (GLB writer, geometry, importer pre-transform) with a
stub `unreal` module, same pattern as test_unreal_basemap_mapping.py.

WP-05 (design §8-4): the default geometry is frozen (WP-04 runbook numbers), door_openings() cuts the door_1
hole into chunk_01 and the collision mesh only, interior_geometry() builds the room inside its bbox, and
sublevel_actor_specs() puts the light and the marker inside the room.
"""

import importlib
import inspect
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
INTERIOR_MANIFEST = MANIFEST.parents[2] / "z_synthetic_001_interior/v1/manifest.json"

# synthetic_geometry(manifest) as WP-04 shipped it (docs/runbooks/pc-verify-wp04.md numbers). Must not change.
WP04_CHUNK_00 = [
    ((-20.0, 9.8, 0.0), (-13.5, 10.0, 12.0)),
    ((-10.5, 9.8, 0.0), (-7.0, 10.0, 12.0)),
    ((-13.5, 9.8, 2.75), (-10.5, 10.0, 12.0)),
    ((-13.5, 9.8, 0.0), (-10.5, 10.0, 0.25)),
]
WP04_CHUNK_01 = [((-7.0, 9.8, 0.0), (7.0, 10.0, 12.0))]
WP04_CHUNK_02 = [((7.0, 9.8, 0.0), (20.0, 10.0, 12.0))]
WP04_FLOOR = ((-22.0, -12.0, -0.2), (22.0, 12.0, 0.0))
WP04_GEOMETRY = {
    "SM_chunk_00": WP04_CHUNK_00,
    "SM_chunk_01": WP04_CHUNK_01,
    "SM_chunk_02": WP04_CHUNK_02,
    "SM_z_synthetic_001_collision": [WP04_FLOOR] + WP04_CHUNK_00 + WP04_CHUNK_01 + WP04_CHUNK_02,
}
# With the door_1 hole (x 3.5..6.5, z 0..2.2): left, right, lintel; the sill has zero height and is dropped.
WP05_CHUNK_01 = [
    ((-7.0, 9.8, 0.0), (3.5, 10.0, 12.0)),
    ((6.5, 9.8, 0.0), (7.0, 10.0, 12.0)),
    ((3.5, 9.8, 2.2), (6.5, 10.0, 12.0)),
]


@pytest.fixture(scope="module")
def mod():
    sys.modules.setdefault("unreal", types.ModuleType("unreal"))
    sys.path.insert(0, str(PY_DIR))
    try:
        yield importlib.import_module("golmok.synthetic_zone")
    finally:
        sys.path.remove(str(PY_DIR))


def _manifest():
    return json.loads(MANIFEST.read_text("utf-8"))


def _interior_manifest():
    return json.loads(INTERIOR_MANIFEST.read_text("utf-8"))


def _solid_at(boxes, p):
    return any(all(lo[i] < p[i] < hi[i] for i in range(3)) for lo, hi in boxes)


def _inside(boxes, lo, hi, tol=1e-9):
    return all(lo[i] - tol <= blo[i] <= bhi[i] <= hi[i] + tol for blo, bhi in boxes for i in range(3))


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
    manifest = _manifest()
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


# ---- WP-05 (design §8-4) ----


def test_default_geometry_is_unchanged_from_wp04(mod):
    manifest = _manifest()
    assert mod.synthetic_geometry(manifest) == WP04_GEOMETRY
    assert mod.synthetic_geometry(manifest, openings=()) == WP04_GEOMETRY
    assert mod.chunk_boxes((-7.0, -10.0, 0.0), (7.0, 10.0, 12.0), False) == WP04_CHUNK_01
    assert mod.chunk_boxes((-20.0, -10.0, 0.0), (-7.0, 10.0, 12.0), True) == WP04_CHUNK_00  # order too
    assert mod.chunk_boxes((-20.0, -10.0, 0.0), (-7.0, 10.0, 12.0), True, openings=()) == WP04_CHUNK_00
    assert mod.FLOOR == WP04_FLOOR and mod.WALL_Y == (9.8, 10.0)
    assert mod.DOOR_HEIGHT_M == 2.2 and mod.ROOM_WALL_M == 0.2


def test_door_openings_cut_the_door_1_hole_in_chunk_01_and_collision_only(mod):
    manifest = _manifest()
    openings = mod.door_openings(manifest)
    assert openings == [((3.5, 6.5), (0.0, 2.2))]  # door_1: x 5 +- 1.5, z 0..DOOR_HEIGHT_M
    assert mod.door_openings({"portals": []}) == [] and mod.door_openings({}) == []
    geometry = mod.synthetic_geometry(manifest, openings=openings)
    assert set(geometry) == set(WP04_GEOMETRY)
    assert geometry["SM_chunk_00"] == WP04_CHUNK_00  # glass hole untouched
    assert geometry["SM_chunk_02"] == WP04_CHUNK_02  # the door is not in chunk_02
    assert geometry["SM_chunk_01"] == WP05_CHUNK_01
    collision = geometry["SM_z_synthetic_001_collision"]
    assert collision == [WP04_FLOOR] + WP04_CHUNK_00 + WP05_CHUNK_01 + WP04_CHUNK_02
    for name in ("SM_chunk_01", "SM_z_synthetic_001_collision"):
        boxes = geometry[name]
        # nothing solid in the door hole (x 3.5..6.5, z 0..2.2), at the wall's y
        for probe in ((5.0, 9.9, 1.0), (3.6, 9.9, 2.1), (6.4, 9.9, 0.1)):
            assert not _solid_at(boxes, probe), (name, probe)
        # the lintel above the door, the wall at x = 0 and the wall at x = +6.8 are still there
        for probe in ((5.0, 9.9, 2.3), (0.0, 9.9, 1.0), (6.8, 9.9, 1.0), (3.4, 9.9, 1.0)):
            assert _solid_at(boxes, probe), (name, probe)
    # the glass hole of chunk_00 is still open, its lintel/sill still solid (chunk_00 and the collision mesh)
    for name in ("SM_chunk_00", "SM_z_synthetic_001_collision"):
        boxes = geometry[name]
        assert not _solid_at(boxes, (-12.0, 9.9, 1.5)), name
        assert _solid_at(boxes, (-12.0, 9.9, 2.9)) and _solid_at(boxes, (-12.0, 9.9, 0.1)), name
    # wall boxes stay inside their chunk bbox; no degenerate boxes anywhere
    for chunk in manifest["layers"]["visual"]["chunks"]:
        lo, hi = chunk["bbox_enu"]
        assert _inside(geometry[f"SM_{chunk['id']}"], lo, hi)
    for boxes in geometry.values():
        for lo, hi in boxes:
            assert all(a < b for a, b in zip(lo, hi, strict=True)), (lo, hi)
    # holes outside a chunk are ignored, holes taller than the wall are clipped, two holes give five pieces
    assert mod.chunk_boxes((7.0, -10.0, 0.0), (20.0, 10.0, 12.0), False, openings=openings) == WP04_CHUNK_02
    tall = mod.chunk_boxes((-7.0, -10.0, 0.0), (7.0, 10.0, 12.0), False, openings=[((3.5, 6.5), (0.0, 50.0))])
    assert tall == WP05_CHUNK_01[:2]
    # two holes in one wall: left, middle, right, glass lintel + sill, door lintel (door sill is degenerate)
    two = mod.chunk_boxes((-20.0, -10.0, 0.0), (20.0, 10.0, 12.0), True, openings=openings)
    assert two == [
        ((-20.0, 9.8, 0.0), (-13.5, 10.0, 12.0)),
        ((-10.5, 9.8, 0.0), (3.5, 10.0, 12.0)),
        ((6.5, 9.8, 0.0), (20.0, 10.0, 12.0)),
        ((-13.5, 9.8, 2.75), (-10.5, 10.0, 12.0)),
        ((-13.5, 9.8, 0.0), (-10.5, 10.0, 0.25)),
        ((3.5, 9.8, 2.2), (6.5, 10.0, 12.0)),
    ]
    assert not _solid_at(two, (-12.0, 9.9, 1.5)) and not _solid_at(two, (5.0, 9.9, 1.0))
    for probe in ((0.0, 9.9, 1.0), (-19.0, 9.9, 1.0), (19.0, 9.9, 1.0)):
        assert _solid_at(two, probe), probe


def test_interior_geometry_is_the_room_inside_its_bbox(mod):
    int_manifest = _interior_manifest()
    geometry = mod.interior_geometry(int_manifest)
    assert set(geometry) == {"SM_room", "SM_z_synthetic_001_interior_collision"}
    room = geometry["SM_room"]
    expected = [
        ((-4.0, -3.0, -0.2), (4.0, 3.0, 0.0)),  # floor
        ((-4.0, -3.0, 0.0), (-3.8, 3.0, 3.0)),  # west wall
        ((3.8, -3.0, 0.0), (4.0, 3.0, 3.0)),  # east wall
        ((-4.0, 2.8, 0.0), (4.0, 3.0, 3.0)),  # north wall
        ((-4.0, -3.0, 3.0), (4.0, 3.0, 3.2)),  # ceiling
    ]
    assert np.allclose(np.array(room), np.array(expected), atol=1e-12)
    assert geometry["SM_z_synthetic_001_interior_collision"] == room
    # every box inside the room bbox, allowing the floor thickness below it
    chunk = int_manifest["layers"]["visual"]["chunks"][0]
    lo, hi = chunk["bbox_enu"]
    assert _inside(room, (lo[0], lo[1], lo[2] - mod.ROOM_WALL_M), hi)
    assert chunk["tris"] == 12 * len(room)  # the manifest's tris count is the box count x 12
    # the interior is hollow and walkable: nothing solid along the room center from the floor to the ceiling
    for z in (0.05, 1.0, 2.95):
        assert not _solid_at(room, (0.0, 0.0, z))
    # the south side (towards the facade / door_out at y -3.5) is open: no box at y just inside the bbox
    assert not _solid_at(room, (0.0, -2.9, 1.0)) and not _solid_at(room, (3.0, -2.95, 2.5))
    # walls/ceiling/floor are solid where expected
    for probe in ((-3.9, 0.0, 1.0), (3.9, 0.0, 1.0), (0.0, 2.9, 1.0), (0.0, 0.0, 3.1), (0.0, 0.0, -0.1)):
        assert _solid_at(room, probe), probe
    # the GLB writer takes the boxes as they are
    gltf, pos, _, idx = read_glb(mod.boxes_glb(room, "room"))
    assert len(idx) == chunk["tris"] and len(pos) == 24 * len(room)
    with pytest.raises(ValueError):
        mod.interior_geometry({"zone_id": "z_x", "layers": {"visual": {"chunks": []}}})


def test_sublevel_actor_specs_are_inside_the_room(mod):
    int_manifest = _interior_manifest()
    specs = mod.sublevel_actor_specs(int_manifest)
    by_label = {s["label"]: s for s in specs}
    assert list(by_label) == ["Interior_Light", "Interior_Marker"]
    light, marker = by_label["Interior_Light"], by_label["Interior_Marker"]
    assert light["kind"] == "point_light" and light["location_cm"] == (0.0, 0.0, 250.0)
    assert light["intensity_cd"] == 3000.0 and light["kelvin"] == 3000.0
    assert marker["kind"] == "cube" and marker["size_cm"] == 50.0
    assert marker["location_cm"] == (0.0, 0.0, 150.0)
    room = mod.interior_geometry(int_manifest)["SM_room"]
    lo, hi = int_manifest["layers"]["visual"]["chunks"][0]["bbox_enu"]
    t = mod.ROOM_WALL_M
    for spec in specs:
        x, y, z = spec["location_cm"]
        enu = (x / 100.0, -y / 100.0, z / 100.0)  # UE cm (X=east, Y=south, Z=up) -> ENU m
        assert lo[0] + t < enu[0] < hi[0] - t and lo[1] < enu[1] < hi[1] - t and 0.0 < enu[2] < hi[2] - t
        assert not _solid_at(room, enu), spec
    half = marker["size_cm"] / 200.0
    mx, my, mz = (v / 100.0 for v in marker["location_cm"])
    for dx, dy, dz in itertools.product((-half, half), repeat=3):
        assert not _solid_at(room, (mx + dx, -my + dy, mz + dz))  # the whole cube floats inside the room


def test_asset_paths_and_run_signature_match_the_cpp_loader(mod):
    manifest, int_manifest = _manifest(), _interior_manifest()
    assert mod.asset_folder(manifest) == mod.ASSET_FOLDER == "/Game/Golmok/Zones/z_synthetic_001/v1"
    assert mod.asset_folder(int_manifest) == "/Game/Golmok/Zones/z_synthetic_001_interior/v1"
    # docs/spec/zone-manifest.md §5 / GolmokZoneManifest::SublevelPackagePath: .../L_<zone_id>
    assert (
        mod.sublevel_path(int_manifest)
        == "/Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior"
    )
    assert (mod.INTERIOR_ZONE_ID, mod.INTERIOR_VERSION) == (int_manifest["zone_id"], int_manifest["version"])
    assert manifest["portals"][0]["to_zone"] == mod.INTERIOR_ZONE_ID  # door_1 leads to the interior fixture
    params = inspect.signature(mod.run).parameters
    assert list(params) == ["geo_origin", "move_player_start", "import_assets", "level", "interior"]
    assert params["interior"].default is False and params["level"].default == mod.ZONE_TEST_MAP
    assert inspect.signature(mod._import_assets).parameters["openings"].default == ()
    assert callable(mod.register_interior_sublevel) and callable(mod._import_interior_assets)
