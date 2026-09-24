"""Import a golmok-basemap output folder into the current level.

    import golmok.basemap_import as b; b.run(r"D:\\golmok_basemap\\yeonnam")

- Imports tiles/*.glb as static meshes into /Game/Golmok/Basemap/<area>/ (Nanite on for buildings,
  complex-as-simple collision so nothing falls through at the play-zone edge).
- Assigns M_BasemapFacade to building meshes (built on first use, see materials.py).
- Places one actor per tile in the level folder "Basemap/<area>" so that Unreal X = east,
  Y = south, Z = up at the area origin (Cesium for Unreal's convention). The glTF importer's axis
  and unit conversion is measured from each tile's bounding box instead of being assumed.
- If Cesium for Unreal is enabled, sets the CesiumGeoreference origin to the area origin.
"""

import itertools
import json
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


def _enable_nanite(mesh):
    settings = mesh.get_editor_property("nanite_settings")
    settings.set_editor_property("enabled", True)
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


def run(folder, area_name=None):
    folder = os.path.abspath(folder)
    manifest = json.load(open(os.path.join(folder, "manifest.json"), encoding="utf-8"))
    area = area_name or os.path.basename(folder.rstrip("\\/"))
    dest = f"{ROOT}/{area}"
    facade = materials.build_facade_material()
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
                    _enable_nanite(mesh)
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
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.log(f"Basemap {area}: {len(imported)} actors placed. Attribution: {' / '.join(manifest['attribution'])}")
