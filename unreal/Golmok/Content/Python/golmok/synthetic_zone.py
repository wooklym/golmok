"""Build the synthetic zone z_synthetic_001 v1 in the editor so WP-04 can be verified without real captures.

Run inside the editor (Output Log, "Python" mode). By default everything is built in its own map,
/Game/Golmok/Maps/L_ZoneTest (created with the L_Dev lighting when missing, opened otherwise), so L_Dev stays
untouched and main's automation test Golmok.Player.Movement (tools/ue/test.ps1) keeps passing:

    import golmok.synthetic_zone as z; z.run()
    z.run(geo_origin="zone")            # put the zone at the level origin instead of the spec area origin
    z.run(move_player_start=False)      # leave the PlayerStart where it is
    z.run(level=None)                   # build in whatever level is open instead of L_ZoneTest

What it does (docs/runbooks/pc-verify-wp04.md):
1. Writes small GLB meshes into <Project>/Saved/Golmok/synthetic_zone/ and imports them as
   /Game/Golmok/Zones/z_synthetic_001/v1/SM_chunk_00..02 (a facade wall per chunk; chunk_00 has a door-sized
   opening where blockers.json puts the glass plane) and SM_z_synthetic_001_collision (floor slab + the facade
   wall minus the opening, complex-as-simple collision). Vertices end up in zone-local UE cm (X=east, Y=south,
   Z=up) exactly as the spec's UE mapping requires: the glTF importer's axis/unit mapping is measured on a
   probe mesh first (same method as basemap_import) and the geometry is pre-transformed to cancel it.
2. Finds or spawns AGolmokGeoOrigin ("FindOrSpawn" convention) at (0,0,0). geo_origin="area" (default) uses
   the spec §4 area origin (37.5600, 126.9230, 40) so the zone lands at UE (17670.59, -22198.00, 999.37) cm,
   table C; geo_origin="zone" uses the zone origin so the zone sits at the level origin.
3. Finds or spawns AGolmokZone (zone_id z_synthetic_001, version 1) and calls RebuildInEditor().
4. Spawns two cubes tagged GolmokBasemap: BM_dummy_inside (bounds center inside the footprint, must vanish in
   PIE once the zone loads) and BM_dummy_outside (stays).
5. Spawns a 400 x 400 m ground plane 20 cm below the slab top (the dev floor does not reach the zone) and moves
   the PlayerStart onto the zone's collision slab (5 m south of the zone origin); a missing PlayerStart is spawned.

The manifest is read by the C++ actor from Content/Golmok/Zones/z_synthetic_001/v1/manifest.json (committed).
"""

import itertools
import json
import os
import struct

import unreal

from . import basemap_import as bm

ZONE_ID = "z_synthetic_001"
VERSION = 1
ASSET_FOLDER = f"/Game/Golmok/Zones/{ZONE_ID}/v{VERSION}"
ZONE_TEST_MAP = "/Game/Golmok/Maps/L_ZoneTest"  # own map so L_Dev (movement automation test) stays untouched
AREA_ORIGIN = (37.5600, 126.9230, 40.0)  # docs/spec/zone-manifest.md §4 C
CUBE = "/Engine/BasicShapes/Cube.Cube"
PLANE = "/Engine/BasicShapes/Plane.Plane"
BASEMAP_TAG = "GolmokBasemap"

# Facade wall (visual): the north 20 cm of every chunk bbox, full chunk height. Door opening in chunk_00 where
# blockers.json puts glass_1 (center (-12, 10, 1.5), 3.0 x 2.5 m): x -13.5..-10.5, z 0.25..2.75.
WALL_Y = (9.8, 10.0)
OPENING_X = (-13.5, -10.5)
OPENING_Z = (0.25, 2.75)
FLOOR = ((-22.0, -12.0, -0.2), (22.0, 12.0, 0.0))


# ---- pure geometry (unit-tested in tools/tests/test_ue_python_synthetic_zone.py) ----


def chunk_boxes(bbox_min, bbox_max, with_opening):
    """Facade wall boxes (ENU m) inside a chunk bbox; with_opening cuts the door hole."""
    x0, _, z0 = bbox_min
    x1, _, z1 = bbox_max
    y0, y1 = WALL_Y
    if not with_opening:
        return [((x0, y0, z0), (x1, y1, z1))]
    ox0, ox1 = OPENING_X
    oz0, oz1 = OPENING_Z
    return [
        ((x0, y0, z0), (ox0, y1, z1)),  # left of the opening
        ((ox1, y0, z0), (x1, y1, z1)),  # right of the opening
        ((ox0, y0, oz1), (ox1, y1, z1)),  # lintel above
        ((ox0, y0, z0), (ox1, y1, oz0)),  # sill below
    ]


def synthetic_geometry(manifest):
    """{asset name: [box (lo, hi) in zone-local ENU m]} for the fixture manifest."""
    chunks = manifest["layers"]["visual"]["chunks"]
    out = {}
    walls = []
    for i, chunk in enumerate(chunks):
        lo, hi = chunk["bbox_enu"]
        boxes = chunk_boxes(lo, hi, with_opening=(i == 0))
        out[f"SM_{chunk['id']}"] = boxes
        walls.extend(boxes)
    out[f"SM_{manifest['zone_id']}_collision"] = [FLOOR] + walls
    return out


def boxes_glb(boxes, name):
    """Binary glTF 2.0 with one mesh made of axis-aligned boxes given as ENU (m) (lo, hi) pairs.

    Positions are written in glTF Y-up meters from ENU: (x, y, z)_enu -> (x, z, -y), like every GLB this
    project writes (golmok-basemap, golmok-mesh). Flat shading: 24 verts and 12 triangles per box, CCW out.
    """

    def g(x, y, z):
        return (x, z, -y)

    pos, nrm, idx = [], [], []
    for lo, hi in boxes:
        ex, ey, ez = lo
        fx, fy, fz = hi
        faces = [
            ((1, 0, 0), [(fx, ey, ez), (fx, fy, ez), (fx, fy, fz), (fx, ey, fz)]),
            ((-1, 0, 0), [(ex, fy, ez), (ex, ey, ez), (ex, ey, fz), (ex, fy, fz)]),
            ((0, 1, 0), [(fx, fy, ez), (ex, fy, ez), (ex, fy, fz), (fx, fy, fz)]),
            ((0, -1, 0), [(ex, ey, ez), (fx, ey, ez), (fx, ey, fz), (ex, ey, fz)]),
            ((0, 0, 1), [(ex, ey, fz), (fx, ey, fz), (fx, fy, fz), (ex, fy, fz)]),
            ((0, 0, -1), [(ex, fy, ez), (fx, fy, ez), (fx, ey, ez), (ex, ey, ez)]),
        ]
        for n, quad in faces:
            base = len(pos)
            pos.extend(g(*c) for c in quad)
            nrm.extend([g(*n)] * 4)
            idx.extend([base, base + 1, base + 2, base, base + 2, base + 3])
    pos_b = b"".join(struct.pack("<3f", *p) for p in pos)
    nrm_b = b"".join(struct.pack("<3f", *p) for p in nrm)
    idx_b = b"".join(struct.pack("<I", i) for i in idx)
    bin_chunk = pos_b + nrm_b + idx_b
    mins = [min(p[i] for p in pos) for i in range(3)]
    maxs = [max(p[i] for p in pos) for i in range(3)]
    gltf = {
        "asset": {"version": "2.0", "generator": "golmok synthetic_zone"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": name}],
        "meshes": [
            {
                "name": name,
                "primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1}, "indices": 2, "mode": 4}],
            }
        ],
        "buffers": [{"byteLength": len(bin_chunk)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_b), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_b), "byteLength": len(nrm_b), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_b) + len(nrm_b), "byteLength": len(idx_b), "target": 34963},
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": len(pos),
                "type": "VEC3",
                "min": mins,
                "max": maxs,
            },
            {"bufferView": 1, "componentType": 5126, "count": len(nrm), "type": "VEC3"},
            {"bufferView": 2, "componentType": 5125, "count": len(idx), "type": "SCALAR"},
        ],
    }
    json_b = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_b += b" " * (-len(json_b) % 4)
    total = 12 + 8 + len(json_b) + 8 + len(bin_chunk)
    return (
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<I4s", len(json_b), b"JSON")
        + json_b
        + struct.pack("<I4s", len(bin_chunk), b"BIN\0")
        + bin_chunk
    )


def pretransform_box(lo, hi, scale, m):
    """Box to *write* (in ENU-file space) so that after the importer mapping imported = scale*M*written the
    result equals TARGET*ENU = UE cm. written = (scale*M)^-1 * TARGET * enu; boxes stay axis-aligned."""
    inv = tuple(tuple(v / scale for v in row) for row in bm._transpose(m))  # (sM)^-1 = M^T / s
    a = bm._matmul(inv, bm.TARGET)
    corners = [bm._apply(a, c) for c in itertools.product(*zip(lo, hi, strict=True))]
    return tuple(min(c[i] for c in corners) for i in range(3)), tuple(
        max(c[i] for c in corners) for i in range(3)
    )


def expected_ue_bounds(boxes):
    """UE (cm) bounds of ENU boxes: TARGET applied to every corner."""
    corners = [
        bm._apply(bm.TARGET, c) for lo, hi in boxes for c in itertools.product(*zip(lo, hi, strict=True))
    ]
    return tuple(min(c[i] for c in corners) for i in range(3)), tuple(
        max(c[i] for c in corners) for i in range(3)
    )


# ---- editor side ----


def _content_dir():
    return unreal.Paths.project_content_dir()


def _saved_dir():
    path = os.path.join(unreal.Paths.project_saved_dir(), "Golmok", "synthetic_zone")
    os.makedirs(path, exist_ok=True)
    return path


def _actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def _load_manifest():
    path = os.path.join(_content_dir(), "Golmok", "Zones", ZONE_ID, f"v{VERSION}", "manifest.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _measure_mapping(work_dir):
    """Import an asymmetric probe box and measure the importer's ENU -> UE mapping (scale, permutation)."""
    probe = ((1.0, 2.0, 3.0), (5.0, 9.0, 15.0))
    path = os.path.join(work_dir, "SM_probe.glb")
    with open(path, "wb") as f:
        f.write(boxes_glb([probe], "probe"))
    mesh = bm._import_glb(path, f"{ASSET_FOLDER}/_probe")
    err, scale, m = bm._measure_import_mapping([(bm._mesh_bounds(mesh), probe)])
    unreal.log(f"synthetic_zone: importer mapping scale={scale:.3f} M={m} (fit error {err:.2f})")
    unreal.EditorAssetLibrary.delete_directory(f"{ASSET_FOLDER}/_probe")
    return scale, m


def _import_assets(manifest, work_dir):
    scale, m = _measure_mapping(work_dir)
    geometry = synthetic_geometry(manifest)
    for name, boxes in geometry.items():
        written = [pretransform_box(lo, hi, scale, m) for lo, hi in boxes]
        path = os.path.join(work_dir, f"{name}.glb")
        with open(path, "wb") as f:
            f.write(boxes_glb(written, name))
        mesh = bm._import_glb(path, ASSET_FOLDER)
        expected_path = f"{ASSET_FOLDER}/{name}"
        if mesh.get_path_name().split(".")[0] != expected_path:
            raise RuntimeError(f"{name}: imported as {mesh.get_path_name()}, but AGolmokZone loads {expected_path}")
        got = bm._mesh_bounds(mesh)
        want = expected_ue_bounds(boxes)
        err = max(abs(a - b) for g_, w_ in zip(got, want, strict=True) for a, b in zip(g_, w_, strict=True))
        if err > 1.0:
            raise RuntimeError(
                f"{name}: imported bounds {got} != expected UE bounds {want} (error {err:.1f} cm)"
            )
        if name.endswith("_collision"):
            bm._complex_collision(mesh)
            # Complex collision of a Nanite mesh comes from its simplified fallback (see basemap_import._set_nanite).
            if hasattr(bm, "_set_nanite"):
                bm._set_nanite(mesh, False)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        unreal.log(f"synthetic_zone: {mesh.get_path_name()} bounds ok (error {err:.2f} cm)")


def find_or_spawn_geo_origin(lat, lon, h):
    """FindOrSpawn convention (WP-06 too): one AGolmokGeoOrigin per level at (0,0,0), label GeoOrigin."""
    actors = _actors()
    geo = next((a for a in actors.get_all_level_actors() if isinstance(a, unreal.GolmokGeoOrigin)), None)
    if geo is None:
        geo = actors.spawn_actor_from_class(unreal.GolmokGeoOrigin, unreal.Vector(0, 0, 0))
        geo.set_actor_label("GeoOrigin")
        geo.set_folder_path("Golmok")
    geo.set_editor_property("latitude", lat)
    geo.set_editor_property("longitude", lon)
    geo.set_editor_property("height_ellipsoidal", h)
    return geo


def find_or_spawn_zone(zone_id, version):
    actors = _actors()
    zone = next(
        (
            a
            for a in actors.get_all_level_actors()
            if isinstance(a, unreal.GolmokZone) and a.get_editor_property("zone_id") == zone_id
        ),
        None,
    )
    if zone is None:
        zone = actors.spawn_actor_from_class(unreal.GolmokZone, unreal.Vector(0, 0, 0))
        zone.set_actor_label(f"Zone_{zone_id}")
        zone.set_folder_path("Golmok/Zones")
    zone.set_editor_property("zone_id", zone_id)
    zone.set_editor_property("version", version)
    return zone


def _spawn_tagged_cube(label, world_location, size_cm=400.0):
    actors = _actors()
    for a in actors.get_all_level_actors():
        if a.get_actor_label() == label:
            actors.destroy_actor(a)
    mesh = unreal.EditorAssetLibrary.load_asset(CUBE)
    actor = actors.spawn_actor_from_object(mesh, world_location, unreal.Rotator(0, 0, 0))
    actor.set_actor_scale3d(unreal.Vector(size_cm / 100.0, size_cm / 100.0, size_cm / 100.0))
    actor.set_actor_label(label)
    actor.set_folder_path("Golmok/BasemapDummy")
    actor.set_editor_property("tags", [unreal.Name(BASEMAP_TAG)])
    return actor


def _spawn_ground(zone):
    """400 x 400 m walkable plane 20 cm below the collision slab top: L_Dev's floor does not reach the zone (it is
    176 m east / 222 m south of the level origin and 10 m up), and the load/unload test walks 50 m away and back."""
    actors = _actors()
    for a in actors.get_all_level_actors():
        if a.get_actor_label() == "Zone_Ground":
            actors.destroy_actor(a)
    plane = unreal.EditorAssetLibrary.load_asset(PLANE)
    location = zone.get_actor_transform().transform_location(unreal.Vector(0.0, 0.0, -20.0))
    actor = actors.spawn_actor_from_object(plane, location, unreal.Rotator(0, 0, 0))
    actor.set_actor_scale3d(unreal.Vector(400.0, 400.0, 1.0))
    actor.set_actor_label("Zone_Ground")
    actor.set_folder_path("Golmok")
    return actor


def _move_player_start(zone):
    actors = _actors()
    starts = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.PlayerStart)]
    # zone-local (0, -5, 0) m -> UE (0, +500, 0) cm, 120 cm up so the capsule stands on the collision slab.
    target = zone.get_actor_transform().transform_location(unreal.Vector(0.0, 500.0, 120.0))
    if not starts:
        start = actors.spawn_actor_from_class(unreal.PlayerStart, target, unreal.Rotator(0.0, 0.0, 0.0))
        start.set_actor_label("PlayerStart")
        unreal.log(f"synthetic_zone: PlayerStart spawned at {target}")
        return
    starts[0].set_actor_location(target, False, False)
    for extra in starts[1:]:
        unreal.log_warning(f"synthetic_zone: extra PlayerStart '{extra.get_actor_label()}' left in place")
    unreal.log(f"synthetic_zone: PlayerStart moved to {target}")


def open_or_create_level(level_path):
    """Open the map at level_path, or create it with the L_Dev lighting (sun, sky, fog, post-process) when missing."""
    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(level_path):
        if not level_editor.load_level(level_path):
            raise RuntimeError(f"synthetic_zone: could not open {level_path}")
        return False
    if not level_editor.new_level(level_path):
        raise RuntimeError(f"synthetic_zone: could not create {level_path}")
    from . import setup_dev_level as dev  # imported here: its defaults touch unreal.Vector at import time

    dev._build_lighting()
    unreal.log(f"synthetic_zone: created {level_path} with the L_Dev lighting")
    return True


def run(geo_origin="area", move_player_start=True, import_assets=True, level=ZONE_TEST_MAP):
    """Build everything in `level` (default L_ZoneTest; None = the level that is open).

    geo_origin: "area" (spec §4 area origin) or "zone".
    """
    if level:
        open_or_create_level(level)
    manifest = _load_manifest()
    if import_assets:
        _import_assets(manifest, _saved_dir())
    if geo_origin == "area":
        lat, lon, h = AREA_ORIGIN
    elif geo_origin == "zone":
        o = manifest["origin"]
        lat, lon, h = o["lat"], o["lon"], o["height_ellipsoidal"]
    else:
        raise ValueError("geo_origin must be 'area' or 'zone'")
    find_or_spawn_geo_origin(lat, lon, h)
    zone = find_or_spawn_zone(manifest["zone_id"], manifest["version"])
    zone.rebuild_in_editor()
    t = zone.get_actor_transform()
    unreal.log(f"synthetic_zone: zone root at {t.translation} yaw {t.rotation.rotator().yaw:.4f}")
    if geo_origin == "area":
        unreal.log("synthetic_zone: expected root (spec table C): X=17670.59 Y=-22198.00 Z=999.37 cm, yaw ~0")
    _spawn_ground(zone)
    _spawn_tagged_cube("BM_dummy_inside", t.transform_location(unreal.Vector(0.0, 0.0, 500.0)))
    _spawn_tagged_cube("BM_dummy_outside", t.transform_location(unreal.Vector(6000.0, 0.0, 500.0)))
    if move_player_start:
        _move_player_start(zone)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.log(
        "synthetic_zone: done. PIE checklist: docs/runbooks/pc-verify-wp04.md "
        "(golmok.zone.list, golmok.geo.selftest, walk north into the glass opening at x=-12 m)"
    )
