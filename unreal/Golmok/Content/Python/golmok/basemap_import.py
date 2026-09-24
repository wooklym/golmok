"""Import a golmok-basemap output folder into the current level.

    import golmok.basemap_import as b; b.run(r"D:\\golmok_basemap\\yeonnam")
    b.run(r"D:\\golmok_basemap\\yeonnam", level="/Game/Golmok/Maps/L_Basemap_Yeonnam")  # own level

- Imports tiles/*.glb as static meshes into /Game/Golmok/Basemap/<area>/ (Nanite on for buildings,
  off for terrain; complex-as-simple collision so nothing falls through at the play-zone edge).
- Assigns M_BasemapFacade to building meshes and M_BasemapTerrain instances (orthophoto) to
  terrain meshes (both built on first use, see materials.py).
- Places one actor per tile in the level folder "Basemap/<area>" so that Unreal X = east,
  Y = south, Z = up at the area origin (Cesium for Unreal's convention). The glTF importer's axis
  and unit conversion is measured from each tile's bounding box instead of being assumed.
- If Cesium for Unreal is enabled, sets the CesiumGeoreference origin to the area origin.
"""

import itertools
import json
import math
import os

import unreal

from . import materials

ROOT = "/Game/Golmok/Basemap"
# Target: UE = 100 * diag(1, -1, 1) * ENU  (cm; X east, Y south, Z up)
TARGET = ((100.0, 0.0, 0.0), (0.0, -100.0, 0.0), (0.0, 0.0, 100.0))


def _matmul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _apply(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def _transpose(m):
    return tuple(tuple(m[j][i] for j in range(3)) for i in range(3))


def _signed_permutations():
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1.0, -1.0), repeat=3):
            m = [[0.0] * 3 for _ in range(3)]
            for row, col in enumerate(perm):
                m[row][col] = signs[row]
            yield tuple(tuple(r) for r in m)


def _mesh_bounds(mesh):
    box = mesh.get_bounding_box()
    return (box.min.x, box.min.y, box.min.z), (box.max.x, box.max.y, box.max.z)


def _measure_import_mapping(samples):
    """Find s, M with imported = s * M * ENU from (mesh bounds, ENU bbox) pairs of several tiles.

    samples: list of ((umin, umax), (emin, emax)). Using many tiles removes the ambiguity a single
    square, centered tile would have.
    """
    best = None
    for m in _signed_permutations():
        scales, pairs = [], []
        for (umin, umax), (emin, emax) in samples:
            e_center = [(a + b) / 2 for a, b in zip(emin, emax)]
            e_ext = [b - a for a, b in zip(emin, emax)]
            u_center = [(a + b) / 2 for a, b in zip(umin, umax)]
            u_ext = [b - a for a, b in zip(umin, umax)]
            ext_mapped = [abs(v) for v in _apply(m, e_ext)]
            scales.append(sum(u_ext) / max(sum(ext_mapped), 1e-6))
            pairs.append((_apply(m, e_center), u_center, ext_mapped, u_ext))
        scale = sorted(scales)[len(scales) // 2]
        err = 0.0
        for c, uc, em, ue in pairs:
            err += sum(abs(scale * ci - ui) for ci, ui in zip(c, uc))
            err += sum(abs(scale * ei - ui) for ei, ui in zip(em, ue))
        if best is None or err < best[0]:
            best = (err, scale, m)
    return best


def _actor_transform(scale, m):
    """Rotator + scale3d turning imported geometry (s*M*ENU) into TARGET."""
    inv = tuple(tuple(v / scale for v in row) for row in _transpose(m))  # (s*M)^-1 = M^T / s
    a = _matmul(TARGET, inv)
    k = abs(a[0][0]) + abs(a[0][1]) + abs(a[0][2])
    unit = tuple(tuple(v / k for v in row) for row in a)
    for roll, pitch, yaw in itertools.product((0, 90, 180, 270), repeat=3):
        rot = unreal.Rotator(roll, pitch, yaw)
        axes = [rot.get_forward_vector(), rot.get_right_vector(), rot.get_up_vector()]
        r = tuple(tuple(round(getattr(axes[col], "xyz"[row]), 6) for col in range(3)) for row in range(3))
        for signs in itertools.product((1.0, -1.0), repeat=3):
            rs = tuple(tuple(r[i][j] * signs[j] for j in range(3)) for i in range(3))
            if all(abs(rs[i][j] - unit[i][j]) < 1e-4 for i in range(3) for j in range(3)):
                return rot, unreal.Vector(k * signs[0], k * signs[1], k * signs[2])
    raise RuntimeError(f"no rotator found for matrix {a}")


def _import_glb(path, dest):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    meshes = []
    for obj_path in task.get_editor_property("imported_object_paths"):
        asset = unreal.EditorAssetLibrary.load_asset(obj_path)
        if isinstance(asset, unreal.StaticMesh):
            meshes.append(asset)
    if not meshes:
        raise RuntimeError(f"no static mesh imported from {path}")
    return meshes[0]


def _tile_texture(mesh):
    """The orthophoto texture the glTF importer put next to a terrain mesh (<tile>/Textures/)."""
    folder = mesh.get_path_name().rsplit("/", 2)[0] + "/Textures"
    for path in unreal.EditorAssetLibrary.list_assets(folder, recursive=False):
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if isinstance(asset, unreal.Texture2D):
            return asset
    return None


def _set_nanite(mesh, enabled):
    """Nanite on (buildings) or off (terrain).

    Complex collision of a Nanite mesh comes from its simplified fallback mesh. For terrain tiles that
    opened gaps along tile seams once the terrain had real relief (the 5 m contour DEM), so terrain
    stays a plain static mesh (small uniform grids gain nothing from Nanite), and buildings keep an
    unsimplified fallback so their collision matches what is drawn."""
    settings = mesh.get_editor_property("nanite_settings")
    settings.set_editor_property("enabled", enabled)
    if enabled:
        for prop, value in (("fallback_relative_error", 0.0), ("fallback_percent_triangles", 1.0)):
            try:
                settings.set_editor_property(prop, value)
            except Exception:  # property names differ between engine versions
                unreal.log_warning(f"Nanite setting {prop} not available")
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    if hasattr(sub, "set_nanite_settings"):
        sub.set_nanite_settings(mesh, settings, apply_changes=True)
    else:
        mesh.set_editor_property("nanite_settings", settings)


def _complex_collision(mesh):
    body = mesh.get_editor_property("body_setup")
    if body:
        body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)


def _set_georeference(origin):
    if not hasattr(unreal, "CesiumGeoreference"):
        unreal.log_warning("Cesium for Unreal not enabled; skipping georeference origin.")
        return
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    geo = next((a for a in actors.get_all_level_actors() if isinstance(a, unreal.CesiumGeoreference)), None)
    if geo is None:
        geo = actors.spawn_actor_from_class(unreal.CesiumGeoreference, unreal.Vector(0, 0, 0))
    geo.set_editor_property("origin_latitude", origin["lat"])
    geo.set_editor_property("origin_longitude", origin["lon"])
    geo.set_editor_property("origin_height", origin["height_ellipsoidal"])


def _open_level(level):
    """Load `level`, or create it with the dev-level lighting (sun, sky, fog, post process)."""
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(level):
        les.load_level(level)
        return
    if not les.new_level(level):
        raise RuntimeError(f"Could not create {level}")
    from . import setup_dev_level
    setup_dev_level._build_lighting()


def _remove_area_actors(area):
    """Delete actors placed by a previous run for this area so re-running does not duplicate them."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    old = [a for a in eas.get_all_level_actors() if str(a.get_folder_path()) == f"Basemap/{area}"]
    if old:
        eas.destroy_actors(old)


def _ground_hit(world, x, y):
    hit = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x, y, 1.0e6), unreal.Vector(x, y, -1.0e6), unreal.TraceTypeQuery.ECC_VISIBILITY,
        False, [], unreal.DrawDebugTrace.NONE, True)
    if not hit:
        return None
    t = hit.to_tuple()  # (blocking, initial_overlap, time, distance, location, impact_point, ..., hit_actor, ...)
    return t[4], t[9]


def _place_player_start(area):
    """PlayerStart on open terrain (not a roof) nearest the area origin."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for r in range(0, 30000, 250):
        steps = max(1, int(2 * math.pi * r / 500))
        for k in range(steps):
            a = 2 * math.pi * k / steps
            hit = _ground_hit(world, r * math.cos(a), r * math.sin(a))
            if hit and hit[1] and hit[1].get_actor_label().startswith("BM_terrain"):
                loc = hit[0]
                start = eas.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(loc.x, loc.y, loc.z + 120.0))
                start.set_actor_label(f"PlayerStart_{area}")
                start.set_folder_path(f"Basemap/{area}")
                unreal.log(f"PlayerStart on terrain at ({loc.x / 100:.1f}, {loc.y / 100:.1f}, {loc.z / 100:.1f}) m")
                return start
    unreal.log_warning("No open terrain found near the origin for a PlayerStart.")
    return None


def run(folder, area_name=None, level=None):
    """Import into the current level, or into `level` (e.g. "/Game/Golmok/Maps/L_Basemap_Yeonnam"),
    which is created with lighting and gets a PlayerStart on the terrain near the area origin."""
    folder = os.path.abspath(folder)
    manifest = json.load(open(os.path.join(folder, "manifest.json"), encoding="utf-8"))
    area = area_name or os.path.basename(folder.rstrip("\\/"))
    dest = f"{ROOT}/{area}"
    if level:
        _open_level(level)
    _remove_area_actors(area)
    facade = materials.build_facade_material()
    terrain_mat = materials.build_terrain_material()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    imported = []  # (tile, kind, mesh)
    with unreal.ScopedSlowTask(len(manifest["tiles"]), f"Importing basemap {area}") as task:
        task.make_dialog(True)
        for tile in manifest["tiles"]:
            if task.should_cancel():
                break
            task.enter_progress_frame(1, tile["id"])
            for kind in ("terrain", "buildings"):
                uri = tile.get(kind)
                if not uri:
                    continue
                mesh = _import_glb(os.path.join(folder, uri), f"{dest}/{kind}")
                if kind == "buildings":
                    mesh.set_material(0, facade)
                    _set_nanite(mesh, True)
                else:
                    _set_nanite(mesh, False)  # the glTF importer turns Nanite on by default
                    if tex := _tile_texture(mesh):
                        # Our material, not the glTF default (its plugin parent lacks the Nanite flag).
                        tile_dir = mesh.get_path_name().rsplit("/", 2)[0]
                        mesh.set_material(0, materials.terrain_instance(
                            tex, terrain_mat, f"{tile_dir}/Materials/MI_{mesh.get_name()}"))
                _complex_collision(mesh)
                unreal.EditorAssetLibrary.save_loaded_asset(mesh)
                imported.append((tile, kind, mesh))
    if not imported:
        unreal.log_warning("Nothing imported.")
        return

    samples = [(_mesh_bounds(mesh), tile[f"{kind}_bbox_enu"]) for tile, kind, mesh in imported]
    err, scale, m = _measure_import_mapping(samples)
    unreal.log(f"glTF import mapping: scale={scale:.3f} M={m} (fit error {err:.1f} over {len(samples)} meshes)")
    rot, scale3d = _actor_transform(scale, m)

    for tile, kind, mesh in imported:
        actor = actors.spawn_actor_from_object(mesh, unreal.Vector(0, 0, 0), rot)
        actor.set_actor_scale3d(scale3d)
        actor.set_actor_label(f"BM_{kind}_{tile['id']}")
        actor.set_folder_path(f"Basemap/{area}")

    _set_georeference(manifest["origin"])
    if level:
        _place_player_start(area)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.log(f"Basemap {area}: {len(imported)} actors placed. Attribution: {' / '.join(manifest['attribution'])}")
