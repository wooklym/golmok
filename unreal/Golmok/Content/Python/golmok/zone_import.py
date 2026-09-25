"""Import a golmok-mesh zone folder (docs/spec/zone-manifest.md §2) into the editor; rebuild its AGolmokZone.

    import golmok.zone_import as zi; r = zi.run(r"D:\\golmok\\zones\\z_yeonnam_alley_001")      # highest v*
    zi.run(r"D:\\golmok\\zones\\z_yeonnam_alley_001\\v2", level="/Game/Golmok/Maps/L_Basemap_Yeonnam")
    zi.run(r"D:\\golmok_synth\\zones\\z_synthetic_scan_001", level="/Game/Golmok/Maps/L_ZoneTest",
           geo_origin="area")                                 # docs/runbooks/pc-verify-wp06.md §2
    zi.run(..., geo_origin=r"D:\\golmok_basemap\\yeonnam")   # GeoOrigin from the basemap manifest origin
    zi.run(..., reimport_textures=False)                      # re-run: keep T_* assets that already exist
    zi.run(..., remeasure=True)                               # ignore the importer_mapping.json cache

What it does (docs/runbooks/pc-verify-wp06.md §2; WP-06 design §3-2):
1. Plan, without touching the editor: resolve the version folder, read manifest.json and
   visual/chunk_manifest.json, build the import plan (_pure.import_plan). Any problem raises
   ZoneImportError("plan", ...) before the first editor call.
2. Importer mapping: one probe OBJ (importer ladder fbx -> interchange -> legacy_flag) and one probe GLB
   measure the importer's axis/unit mapping (scale, M). The result is cached per engine version in
   <Saved>/Golmok/zone_import/importer_mapping.json (remeasure=True ignores the cache).
3. Textures: the UDIM anchor tile (BaseName.1001.ext) or the single file is imported as Textures/T_<base>,
   sRGB and virtual texture streaming are forced on, and tiles the importer did not merge are packed with
   UDIMTextureFunctionLibrary (last resort: tile 1001 only + WARNING).
4. Materials: /Game/Golmok/Materials/M_ZoneScan (VT sampler; default texture = its own T_ZoneScanDefault,
   repaired in place on an existing master) and M_ZoneScan_NoVT (T_ZoneScanDefault_NoVT) when a texture
   could not be made VT; one MI_<material> per MTL material.
5. Chunks: every visual/<chunk>.obj is rewritten into <Saved>/Golmok/zone_import/<id>/v<n>/visual/ with the
   inverse importer mapping baked into positions, normals and winding, imported as SM_<chunk_id>, its
   bounds checked against bbox_enu in UE cm, Nanite on, MI_* assigned by slot name.
6. Collision: collision/<chunk>.glb (or collision.glb) pre-transformed the same way, imported as
   SM_<zone_id>_collision[_<chunk_id>], complex-as-simple, Nanite off.
7. Exactly manifest.json and blockers.json are copied to <Content>/Golmok/Zones/<id>/v<n>/ (what the C++
   AGolmokZone reads); nothing else of the zone folder goes into Content.
8. GeoOrigin (find or spawn), AGolmokZone (find or spawn) + rebuild_in_editor(), save, import_result.json.

Every import goes to a scratch <folder>/_import and is moved to its convention path (V-03: Interchange puts
glTF at <dest>/<source>/StaticMeshes/<name>; runbook #37). Re-running is the normal workflow (the previous
asset at the path is replaced); the OBJ copies stay in Saved and are overwritten. interior_setup reuses
import_assets() for the asset part.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import struct
import zlib

import unreal

from . import _pure, materials
from . import basemap_import as bm
from . import synthetic_zone as sz

ROUTES = ("fbx", "interchange", "legacy_flag")
LEGACY_FLAG_COMMAND = "Interchange.FeatureFlags.Import.OBJ 0"
PROBE_FIT_MAX_CM = 1.0
CACHE_NAME = "importer_mapping.json"
RESULT_NAME = "import_result.json"
OBJ_HEADER_LINES = 4096  # import_plan only needs the lines before the first face (mtllib is at the top)
_BYPRODUCT_CLASSES = ("Material", "MaterialInstanceConstant", "Texture2D")  # importer by-products
SCRATCH = "_import"  # V-03: every import goes to <folder>/_import and is moved to its convention path
MASTER_DEFAULT_NAME = "T_ZoneScanDefault"  # the masters' own default texture (never a zone texture)
MASTER_DEFAULT_PX = 256  # >= the virtual texture tile size

_warnings: list[str] = []  # messages of the zi.warn lines of the current import_assets() call


class ZoneImportError(RuntimeError):
    """One failed step; str() is the `zone_import: ERROR <step>: <message>` line (LOG key `log_key`, which
    interior_setup.InteriorSetupError overrides)."""

    log_key = "zi.error"

    def __init__(self, step: str, message: str):
        super().__init__(_pure.fmt(self.log_key, step=step, message=message))
        self.step = step
        self.message = message


# ---- small helpers -----------------------------------------------------------------------------------


def _log(key: str, **kw) -> None:
    unreal.log(_pure.fmt(key, **kw))


def _warn(message: str) -> None:
    unreal.log_warning(_pure.fmt("zi.warn", message=message))
    _warnings.append(message)


@contextlib.contextmanager
def _step(name: str):
    """Wrap any unexpected exception of a step into ZoneImportError(name, ...)."""
    try:
        yield
    except ZoneImportError:
        raise
    except Exception as e:
        raise ZoneImportError(name, str(e) or type(e).__name__) from e


def _asset_key(path) -> str:
    """'/Game/A/B.B' -> '/Game/A/B' (runbook #6: both formats are accepted everywhere)."""
    text = str(path).replace("\\", "/")
    head, sep, tail = text.rpartition("/")
    return head + sep + tail.split(".")[0]


def _read_json(path: str) -> dict:
    with open(os.path.normpath(path), encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _read_text_head(path: str) -> str:
    """read_text for _pure.import_plan: whole MTL/JSON files, only the header of (possibly huge) OBJ files."""
    with open(os.path.normpath(path), encoding="utf-8", errors="surrogateescape") as f:
        if not path.lower().endswith(".obj"):
            return f.read()
        lines: list[str] = []
        for line in f:
            if line.startswith(("f ", "f\t")) or len(lines) >= OBJ_HEADER_LINES:
                break
            lines.append(line)
        return "".join(lines)


def _saved_dir() -> str:
    return os.path.normpath(unreal.Paths.project_saved_dir())


def _content_dir() -> str:
    return os.path.normpath(unreal.Paths.project_content_dir())


def _zone_import_dir() -> str:
    return os.path.join(_saved_dir(), "Golmok", "zone_import")


def work_dir(plan: dict) -> str:
    """<Saved>/Golmok/zone_import/<zone_id>/v<n>/ with visual/ and collision/ (created)."""
    path = os.path.join(_zone_import_dir(), plan["zone_id"], f"v{plan['version']}")
    for sub in ("visual", "collision"):
        os.makedirs(os.path.join(path, sub), exist_ok=True)
    return path


def _mapping_triple(mapping) -> tuple[float, tuple, float]:
    """(scale, m, err) from a cache dict or a (scale, m, err) tuple, m as a tuple of tuples of floats."""
    if isinstance(mapping, dict):
        scale, m, err = mapping["scale"], mapping["m"], mapping.get("err", 0.0)
    else:
        scale, m, err = mapping
    return float(scale), tuple(tuple(float(v) for v in row) for row in m), float(err)


def _mapping_dict(mapping) -> dict:
    """importer_mapping.json entry (design §4-2) of a (scale, m, err) tuple."""
    scale, m, err = _mapping_triple(mapping)
    return {"scale": scale, "m": [list(row) for row in m], "err": err}


# ---- plan (no editor call) -----------------------------------------------------------------------------


def make_plan(zone_dir, version=None) -> tuple[dict, dict]:
    """(plan, manifest) for a zone folder; ZoneImportError("plan", ...) on any problem. No editor call."""
    try:
        version_dir, version = _pure.resolve_zone_dir(
            str(zone_dir), version, os.listdir, os.path.isdir, os.path.isfile
        )
    except ValueError as e:
        raise ZoneImportError("plan", str(e)) from e
    try:
        manifest = _read_json(f"{version_dir}/manifest.json")
    except (OSError, ValueError) as e:
        raise ZoneImportError("plan", f"manifest.json: {e}") from e
    chunk_manifest = None
    chunk_manifest_path = f"{version_dir}/visual/chunk_manifest.json"
    if os.path.isfile(os.path.normpath(chunk_manifest_path)):
        try:
            chunk_manifest = _read_json(chunk_manifest_path)
        except (OSError, ValueError) as e:
            raise ZoneImportError("plan", f"chunk_manifest.json: {e}") from e
    plan = _pure.import_plan(
        manifest,
        chunk_manifest,
        version_dir,
        exists=os.path.exists,
        listdir=os.listdir,
        read_text=_read_text_head,
    )
    problems = _pure.plan_problems(plan)
    if problems:
        raise ZoneImportError("plan", "\n".join(problems))
    return plan, manifest


def log_plan(plan: dict) -> None:
    """The plan warnings (zi.warn) followed by the zi.plan line: step 1 of run() and interior_setup.run()."""
    for message in plan.get("warnings", []):
        _warn(message)
    _log(
        "zi.plan",
        zone_id=plan["zone_id"],
        version=plan["version"],
        chunks=len(plan["chunks"]),
        collision=len(plan["collision"]),
        collision_mode=plan["collision_mode"],
        textures=len(plan["textures"]),
        materials=len(plan["materials"]),
        blockers=plan["blockers"]["planes"],
    )


# ---- editor adapters (every uncertain call behind hasattr; runbook rows in the warnings) ----------------


def _import_task(filename, destination_path, destination_name=None, options=None, factory=None) -> list[str]:
    """One automated AssetImportTask; returns the imported object paths (never empty)."""
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", os.path.normpath(str(filename)))
    task.set_editor_property("destination_path", destination_path)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    if hasattr(task, "async_"):  # runbook #22
        task.set_editor_property("async_", False)
    if destination_name:
        task.set_editor_property("destination_name", destination_name)
    if options is not None:
        task.set_editor_property("options", options)
    if factory is not None:
        task.set_editor_property("factory", factory)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
    if not paths:
        raise RuntimeError(f"no asset imported from {os.path.normpath(str(filename))}")
    return paths


def _try_set(obj, prop: str, value, row: int) -> bool:
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception as e:
        _warn(f"{type(obj).__name__}.{prop} not settable ({e}); importer default kept (runbook #{row})")
        return False


def _try_get(obj, prop: str, row: int):
    try:
        return obj.get_editor_property(prop)
    except Exception as e:
        _warn(f"{type(obj).__name__}.{prop} not readable ({e}); importer default kept (runbook #{row})")
        return None


def _obj_factory(route: str):
    """FbxFactory for the fbx route (runbook #1); the other routes let the engine choose."""
    if route == "fbx" and hasattr(unreal, "FbxFactory"):
        return unreal.FbxFactory()
    return None


def _obj_options(route: str):
    """Import options of an OBJ route: mesh only (no materials, no textures), Nanite, one combined mesh."""
    if route in ("fbx", "legacy_flag"):
        if not hasattr(unreal, "FbxImportUI"):
            _warn("FbxImportUI unavailable: OBJ imported with default options (runbook #1)")
            return None
        ui = unreal.FbxImportUI()
        for prop, value in (
            ("is_obj_import", True),
            ("import_mesh", True),
            ("import_materials", False),
            ("import_textures", False),
            ("import_as_skeletal", False),
            ("automated_import_should_detect_type", False),
        ):
            _try_set(ui, prop, value, 1)
        if hasattr(unreal, "FBXImportType"):
            _try_set(ui, "mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH, 1)
        data = _try_get(ui, "static_mesh_import_data", 1)
        if data is not None:
            for prop, value in (
                ("build_nanite", True),
                ("combine_meshes", True),
                ("auto_generate_collision", False),
                ("generate_lightmap_u_vs", False),
            ):
                _try_set(data, prop, value, 1)
        return ui
    if route == "interchange":
        if not hasattr(unreal, "InterchangeGenericAssetsPipeline"):
            _warn(
                "InterchangeGenericAssetsPipeline unavailable: OBJ imported with default options (runbook #3)"
            )
            return None
        pipeline = unreal.InterchangeGenericAssetsPipeline()
        common = _try_get(pipeline, "common_meshes_properties", 3)
        if common is not None and hasattr(unreal, "InterchangeForceMeshType"):
            _try_set(common, "force_all_mesh_as_type", unreal.InterchangeForceMeshType.IFMT_STATIC_MESH, 3)
        mesh = _try_get(pipeline, "mesh_pipeline", 3)
        if mesh is not None:
            _try_set(mesh, "import_static_meshes", True, 3)
            _try_set(mesh, "build_nanite", True, 3)
        material = _try_get(pipeline, "material_pipeline", 3)
        if material is not None:
            _try_set(material, "import_materials", False, 3)
            texture = _try_get(material, "texture_pipeline", 3)
            if texture is not None:
                _try_set(texture, "import_textures", False, 3)
        return pipeline
    raise ValueError(f"unknown OBJ route {route!r}")


def _texture_options(udim: bool = True):
    """Interchange texture import: no materials; UDIM detection only for plan UDIM sets (udim=True). Single
    textures turn it off, because the engine rule [._]#### (>= 1001) would take 'wall_1002.png' or
    'photo.2048.png' for a UDIM tile (runbook #3, #38). None without the class."""
    if not hasattr(unreal, "InterchangeGenericAssetsPipeline"):
        return None
    pipeline = unreal.InterchangeGenericAssetsPipeline()
    material = _try_get(pipeline, "material_pipeline", 3)
    if material is not None:
        _try_set(material, "import_materials", False, 3)
        texture = _try_get(material, "texture_pipeline", 3)
        if texture is not None:
            _try_set(texture, "import_udi_ms", bool(udim), 3)
    return pipeline


def _console(cmd: str) -> None:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, cmd)


def _engine_version() -> str:
    if hasattr(unreal, "SystemLibrary") and hasattr(unreal.SystemLibrary, "get_engine_version"):
        return str(unreal.SystemLibrary.get_engine_version())
    _warn("SystemLibrary.get_engine_version unavailable: importer mapping cache disabled (runbook #26)")
    return "unknown"


def _pick(paths: list[str], cls):
    """The first imported asset of class `cls`."""
    for path in paths:
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if isinstance(asset, cls):
            return asset
    raise RuntimeError(f"no {cls.__name__} among the imported assets {list(paths)}")


def _byproduct_classes() -> tuple:
    return tuple(getattr(unreal, name) for name in _BYPRODUCT_CLASSES if hasattr(unreal, name))


def _delete_assets(paths: list[str], keep: set[str]) -> list[str]:
    """Delete the Material / MaterialInstanceConstant / Texture2D assets an import created besides `keep`."""
    lib = unreal.EditorAssetLibrary
    classes = _byproduct_classes()
    deleted = []
    for path in paths:
        key = _asset_key(path)
        if key in keep:
            continue
        asset = lib.load_asset(key)
        if asset is None:
            continue
        if isinstance(asset, classes):
            lib.delete_asset(key)
            _log("zi.cleanup", asset=key)
            deleted.append(key)
        else:
            _warn(f"unexpected asset {key} left in place")
    return deleted


def _ensure_path(asset, target: str, row: int, scratch: str | None = None):
    """The imported asset at exactly `target` (runbook #8): an existing asset there (the previous import) is
    replaced, like synthetic_zone._move_asset. A move out of `scratch` that keeps the name is the expected
    importer placement (zi.moved, runbook #37); any other rename is a warning (importer naming, row `row`)."""
    lib = unreal.EditorAssetLibrary
    current = _asset_key(asset.get_path_name())
    if current == target:
        return asset
    if lib.does_asset_exist(target) and not lib.delete_asset(target):
        raise RuntimeError(f"{target} exists and could not be deleted (referenced?)")
    if not lib.rename_asset(current, target):
        if lib.duplicate_asset(current, target) is None:
            raise RuntimeError(f"could not rename {current} to {target}")
        lib.delete_asset(current)
    same_name = current.rsplit("/", 1)[-1] == target.rsplit("/", 1)[-1]
    if scratch is not None and current.startswith(scratch + "/") and same_name:
        _log("zi.moved", src=current, dst=target)
    else:
        _warn(f"{current} renamed to {target} (importer naming; runbook #{row})")
    moved = lib.load_asset(target)
    if moved is None:
        raise RuntimeError(f"{target} missing after renaming {current}")
    return moved


def _import_moved(filename, folder: str, name: str, target: str, cls, row: int, options=None, factory=None):
    """V-03 pattern (pc-findings #1, synthetic_zone._import_geometry): import into <folder>/_import, move the
    `cls` asset to `target`, delete the by-products it listed, then drop the scratch folder with whatever the
    importer left there unlisted (Interchange glTF: <source>/StaticMeshes/<name> + sibling Materials/)."""
    lib = unreal.EditorAssetLibrary
    scratch = f"{folder}/{SCRATCH}"
    try:
        paths = _import_task(filename, scratch, destination_name=name, options=options, factory=factory)
        picked = _pick(paths, cls)
        src = _asset_key(picked.get_path_name())
        asset = _ensure_path(picked, target, row, scratch)
        _delete_assets(paths, keep={target, src})
    finally:
        if lib.does_directory_exist(scratch):
            for path in lib.list_assets(scratch, recursive=True, include_folder=False):
                _log("zi.cleanup", asset=_asset_key(path))
            lib.delete_directory(scratch)
    if _asset_key(asset.get_path_name()) != target:
        raise RuntimeError(f"imported as {asset.get_path_name()}, but the convention path is {target}")
    return asset


def _find_geo_origin() -> tuple | None:
    """(lat, lon, h) of the level's first AGolmokGeoOrigin, or None."""
    if not hasattr(unreal, "GolmokGeoOrigin"):
        return None
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    geo = next((a for a in actors if isinstance(a, unreal.GolmokGeoOrigin)), None)
    if geo is None:
        return None
    return tuple(float(geo.get_editor_property(p)) for p in ("latitude", "longitude", "height_ellipsoidal"))


# ---- importer mapping (probe) ------------------------------------------------------------------------


def _measure_obj_mapping(work: str, asset_folder: str) -> tuple[str, tuple[float, tuple, float]]:
    """(route, (scale, m, err)): the first importer route of the ladder that imports the probe OBJ."""
    probe = os.path.join(work, "_probe.obj")
    with open(probe, "w", encoding="utf-8", newline="\n") as f:
        f.write(_pure.probe_obj_text())
    probe_folder = f"{asset_folder}/_probe"
    failures = []
    try:
        for route in ROUTES:
            try:
                if route == "legacy_flag":
                    _console(LEGACY_FLAG_COMMAND)
                paths = _import_task(
                    probe,
                    probe_folder,
                    destination_name="SM_probe",
                    options=_obj_options(route),
                    factory=_obj_factory(route),
                )
                mesh = _pick(paths, unreal.StaticMesh)
            except Exception as e:
                failures.append(f"{route}: {e}")
                continue
            err, scale, m = _pure.measure_mapping([(bm._mesh_bounds(mesh), _pure.PROBE_BOX)])
            if err > PROBE_FIT_MAX_CM:
                raise ZoneImportError("probe", f"obj importer mapping fit failed (error {err:.2f} cm)")
            return route, (scale, m, err)
    finally:
        unreal.EditorAssetLibrary.delete_directory(probe_folder)
    raise ZoneImportError("probe", f"OBJ import failed on routes {', '.join(ROUTES)}: {'; '.join(failures)}")


def _measure_glb_mapping(work: str, asset_folder: str) -> tuple[float, tuple, float]:
    """(scale, m, err) of the glTF importer, measured on a probe box GLB (same method as basemap_import)."""
    probe = os.path.join(work, "_probe.glb")
    with open(probe, "wb") as f:
        f.write(sz.boxes_glb([_pure.PROBE_BOX], "SM_probe_glb"))
    probe_folder = f"{asset_folder}/_probe"
    try:
        paths = _import_task(probe, probe_folder, destination_name="SM_probe_glb")
        mesh = _pick(paths, unreal.StaticMesh)
        err, scale, m = _pure.measure_mapping([(bm._mesh_bounds(mesh), _pure.PROBE_BOX)])
    finally:
        unreal.EditorAssetLibrary.delete_directory(probe_folder)
    if err > PROBE_FIT_MAX_CM:
        raise ZoneImportError("probe", f"glb importer mapping fit failed (error {err:.2f} cm)")
    return scale, m, err


def _importer_mappings(work: str, asset_folder: str, remeasure: bool):
    """(route, obj_mapping, glb_mapping) from the cache (same engine version) or from fresh probes."""
    cache_path = os.path.join(_zone_import_dir(), CACHE_NAME)
    engine = _engine_version()
    cache = None
    if os.path.isfile(cache_path):
        try:
            cache = _read_json(cache_path)
        except (OSError, ValueError):
            cache = None
    if not remeasure and engine != "unknown" and _pure.importer_cache_valid(cache, engine):
        _log("zi.cache", state="hit", path=cache_path)
        return str(cache["obj"]["route"]), _mapping_triple(cache["obj"]), _mapping_triple(cache["glb"])
    _log("zi.cache", state="miss", path=cache_path)
    route, obj_mapping = _measure_obj_mapping(work, asset_folder)
    glb_mapping = _measure_glb_mapping(work, asset_folder)
    _log("zi.route", route=route, how="probe imported 1 static mesh")
    for kind, (scale, m, err) in (("obj", obj_mapping), ("glb", glb_mapping)):
        _log("zi.mapping", kind=kind, scale=scale, m=m, err=err)
    _write_json(
        cache_path,
        {
            "schema": 1,
            "engine": engine,
            "obj": {"route": route, **_mapping_dict(obj_mapping)},
            "glb": _mapping_dict(glb_mapping),
        },
    )
    return route, obj_mapping, glb_mapping


# ---- textures --------------------------------------------------------------------------------------------


def _texture_size(texture) -> tuple[int, int] | None:
    if hasattr(texture, "blueprint_get_size_x") and hasattr(texture, "blueprint_get_size_y"):
        return int(texture.blueprint_get_size_x()), int(texture.blueprint_get_size_y())
    return None


def _png_tile_size(path: str) -> tuple[int, int] | None:
    try:
        with open(os.path.normpath(path), "rb") as f:
            return _pure.png_size(f.read(24))
    except (OSError, ValueError):
        return None


def _force_texture_settings(texture) -> tuple[bool, bool]:
    """sRGB on, virtual texture streaming on: (vt now, vt was switched on here). Runbook #5."""
    _try_set(texture, "srgb", True, 5)
    vt = bool(_try_get(texture, "virtual_texture_streaming", 5))
    if vt:
        return True, False
    _try_set(texture, "virtual_texture_streaming", True, 5)
    vt = bool(_try_get(texture, "virtual_texture_streaming", 5))
    return vt, vt


def _pack_udim_tiles(tex: dict, asset_folder: str, single):
    """UDIM tiles the importer left unmerged: import every tile into Textures/_tiles and pack them with
    UDIMTextureFunctionLibrary; without the library keep the anchor tile only (runbook #4)."""
    name, tiles = tex["name"], tex["tiles"]
    if not hasattr(unreal, "UDIMTextureFunctionLibrary"):
        _warn(f"texture {name}: UDIM tiles not merged; using tile {tiles[0]} only (runbook #4)")
        return single, f"tile {tiles[0]} only (WARNING)"
    lib = unreal.EditorAssetLibrary
    tiles_folder = f"{asset_folder}/Textures/_tiles"
    tile_textures = []
    for tile in tiles:
        options = _texture_options(False)  # one plain tile each
        paths = _import_task(
            tex["files"][str(tile)], tiles_folder, destination_name=f"{name}_{tile}", options=options
        )
        texture = _pick(paths, unreal.Texture2D)
        _delete_assets(paths, keep={_asset_key(texture.get_path_name())})
        tile_textures.append(texture)
    coords = [unreal.IntPoint(int(u), int(v)) for u, v in tex["block_coords"]]
    # Packed onto the unmerged anchor at T_<base> in place (keep_existing_settings: "if a texture with the
    # same path name exists"): no force delete, so what references T_<base> keeps a texture (runbook #4, #10).
    packed = unreal.UDIMTextureFunctionLibrary.make_udim_virtual_texture_from_texture2_ds(
        tex["asset"], tile_textures, coords, keep_existing_settings=False, check_out_and_save=True
    )
    if packed is None:
        raise RuntimeError(f"make_udim_virtual_texture_from_texture2_ds({tex['asset']}) returned None")
    lib.delete_directory(tiles_folder)
    return packed, f"packed from {len(tile_textures)} tiles"


def _import_texture(tex: dict, asset_folder: str, reimport: bool) -> tuple[object, dict]:
    """Textures/T_<base> from the UDIM anchor tile or the single file: (texture, result detail)."""
    lib = unreal.EditorAssetLibrary
    tiles = list(tex["tiles"])
    if not reimport and lib.does_asset_exist(tex["asset"]):
        texture = lib.load_asset(tex["asset"])
        vt = bool(_try_get(texture, "virtual_texture_streaming", 5))
        how = "skipped: exists"
    else:
        texture = _import_moved(
            tex["anchor"],
            f"{asset_folder}/Textures",
            tex["name"],
            tex["asset"],
            unreal.Texture2D,
            4,
            options=_texture_options(udim=bool(tiles)),
        )
        how = "single texture"
        if not tiles:
            size, file_size = _texture_size(texture), _png_tile_size(tex["anchor"])
            if size is not None and file_size is not None and size != file_size:
                how = "imported as UDIM by the engine (WARNING)"
                file = os.path.basename(os.path.normpath(tex["anchor"]))
                _warn(
                    f"texture {tex['name']}: engine imported {file} "
                    f"as a UDIM ({size[0]}x{size[1]} != file {file_size[0]}x{file_size[1]}; name matches "
                    "[._]####); rename the file (runbook #38)"
                )
        elif len(tiles) > 1:
            size, tile = _texture_size(texture), _png_tile_size(tex["anchor"])
            if size is None or tile is None:
                how = "merged by importer (size unknown)"
                _warn(f"texture {tex['name']}: UDIM merge could not be verified by size (runbook #4)")
            elif size == tile:
                texture, how = _pack_udim_tiles(tex, asset_folder, texture)
            else:
                how = "merged by importer"
        vt, enabled = _force_texture_settings(texture)
        if enabled:
            how += ", vt enabled after import"
        lib.save_loaded_asset(texture)
    size = _texture_size(texture)
    w, h = size if size is not None else ("?", "?")
    _log("zi.texture", asset=tex["asset"], tiles=tiles, w=w, h=h, vt="on" if vt else "off", how=how)
    detail = {"tiles": tiles, "size": list(size) if size is not None else None, "vt": vt, "how": how}
    return texture, detail


def _grey_png(px: int, value: int = 128) -> bytes:
    """px x px 8-bit RGB mid-grey PNG (signature, IHDR, one IDAT of filter-0 rows, IEND)."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    rows = (b"\x00" + bytes([value]) * (3 * px)) * px
    ihdr = struct.pack(">IIBBBBB", px, px, 8, 2, 0, 0, 0)
    idat = zlib.compress(rows, 9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _master_default(vt: bool):
    """/Game/Golmok/Materials/T_ZoneScanDefault (VT on) or T_ZoneScanDefault_NoVT (VT off): a mid-grey texture
    owned by the master, created once from a generated PNG. A zone texture as the master's default would be
    nulled by the next re-import of that zone (delete_asset is a force delete) and would tie the committed
    master to one zone's assets (runbook #10). None when the VT setting cannot be made to match."""
    lib = unreal.EditorAssetLibrary
    name = MASTER_DEFAULT_NAME + ("" if vt else "_NoVT")
    path = f"{materials.MATERIAL_DIR}/{name}"
    changed = False
    if lib.does_asset_exist(path):
        texture = lib.load_asset(path)
    else:
        png = os.path.join(_zone_import_dir(), f"{MASTER_DEFAULT_NAME}.png")
        os.makedirs(os.path.dirname(png), exist_ok=True)
        with open(png, "wb") as f:
            f.write(_grey_png(MASTER_DEFAULT_PX))
        options = _texture_options(udim=False)
        texture = _import_moved(
            png, materials.MATERIAL_DIR, name, path, unreal.Texture2D, 10, options=options
        )
        _try_set(texture, "srgb", True, 5)
        changed = True
    is_vt = bool(_try_get(texture, "virtual_texture_streaming", 5))
    if is_vt != vt:
        _try_set(texture, "virtual_texture_streaming", vt, 5)
        is_vt, changed = bool(_try_get(texture, "virtual_texture_streaming", 5)), True
    if changed:
        lib.save_loaded_asset(texture)
    return texture if is_vt == vt else None


def _repair_master_default(master, name: str, default) -> None:
    """An existing master (e.g. built before T_ZoneScanDefault existed) gets `default` back as its BaseColor
    sampler texture, in place: other zones' MI_* keep their parent (runbook #10)."""
    mel = unreal.MaterialEditingLibrary
    want = _asset_key(default.get_path_name())
    if not hasattr(mel, "get_material_property_input_node"):
        _warn(
            f"MaterialEditingLibrary.get_material_property_input_node unavailable: check that {name}'s "
            f"BaseColor default is {want} by hand (runbook #10)"
        )
        return
    node = mel.get_material_property_input_node(master, unreal.MaterialProperty.MP_BASE_COLOR)
    current = _try_get(node, "texture", 10) if node is not None else None
    was = _asset_key(current.get_path_name()) if current is not None else "None"
    if was == want:
        return
    if node is None or not _try_set(node, "texture", default, 10):
        _warn(f"{name} BaseColor default is {was}, not {want}: set it by hand (runbook #10)")
        return
    mel.recompile_material(master)
    unreal.EditorAssetLibrary.save_loaded_asset(master)
    _warn(f"{name} BaseColor default was {was}; set to {want} (runbook #10)")


def _build_master(vt: bool, fallback):
    """M_ZoneScan (vt) / M_ZoneScan_NoVT whose default is its own T_ZoneScanDefault[_NoVT]; `fallback` (a
    zone texture) only when that texture cannot get the right VT setting."""
    name = materials.ZONE_SCAN_NAME if vt else materials.ZONE_SCAN_NOVT_NAME
    default = _master_default(vt)
    if default is None:
        default = fallback
        _warn(
            f"{MASTER_DEFAULT_NAME}{'' if vt else '_NoVT'}: virtual texture streaming could not be set to "
            f"{'on' if vt else 'off'}; {name} default is {_asset_key(fallback.get_path_name())} (runbook #10)"
        )
    existed = unreal.EditorAssetLibrary.does_asset_exist(f"{materials.MATERIAL_DIR}/{name}")
    master = materials.build_zone_scan_material(default, vt=vt)
    if existed:
        _repair_master_default(master, name, default)
    return master


def _build_masters(textures: dict) -> dict:
    """{"vt": M_ZoneScan | None, "novt": M_ZoneScan_NoVT | None} from the imported textures (design D6)."""
    first_vt = next((t for t, vt in textures.values() if vt), None)
    first_novt = next((t for t, vt in textures.values() if not vt), None)
    masters = {"vt": None, "novt": None}
    if first_vt is not None:
        masters["vt"] = _build_master(True, first_vt)
    if first_novt is not None:
        masters["novt"] = _build_master(False, first_novt)
    return masters


# ---- chunks, collision, files ----------------------------------------------------------------------------


def _assign_slots(mesh, chunk: dict, instances: dict) -> tuple[dict[str, str], list[str]]:
    """MI_* per material slot: exact name -> case-insensitive -> OBJ usemtl order (runbook #7).
    Returns ({slot name: MI name}, unmatched slot names)."""
    names = [
        str(sm.get_editor_property("material_slot_name"))
        for sm in mesh.get_editor_property("static_materials")
    ]
    pairs, unmatched = _pure.slot_assignment(names, chunk["slots"], None)
    if unmatched:
        with open(os.path.normpath(chunk["obj"]), encoding="utf-8", errors="surrogateescape") as f:
            usemtl = _pure.usemtl_order(f)
        pairs, unmatched = _pure.slot_assignment(names, chunk["slots"], usemtl)
    for name in unmatched:
        _warn(f"chunk {chunk['id']}: slot '{name}' left with the importer default (runbook #7)")
    slots: dict[str, str] = {}
    for index, mi_name in pairs:
        if mi_name not in instances:
            _warn(f"chunk {chunk['id']}: slot '{names[index]}' wants {mi_name}, which was not created")
            continue
        mesh.set_material(index, instances[mi_name])
        slots[names[index]] = mi_name
    return slots, unmatched


def _check_bounds(step: str, mesh, want) -> float:
    got = bm._mesh_bounds(mesh)
    err = _pure.bounds_error_cm(got, want)
    if err > _pure.bounds_tolerance_cm(want):
        raise ZoneImportError(
            step,
            f"imported bounds {got} != expected {want} (error {err:.2f} cm); "
            "importer mapping may have changed: run with remeasure=True (runbook #2)",
        )
    return err


def _import_chunk(chunk: dict, plan: dict, work: str, a_obj, instances: dict, factory, options) -> dict:
    """SM_<chunk_id>: pre-transformed OBJ copy -> import -> bounds check -> Nanite -> slots -> save."""
    copy = os.path.join(work, "visual", f"{chunk['name']}.obj")
    obj = os.path.normpath(chunk["obj"])
    _pure.pretransform_obj_file(obj, copy, a_obj, mtllib=" ".join(chunk["mtllib"]))
    obj_dir = os.path.dirname(obj)
    for name in chunk["mtllib"]:
        src = os.path.join(obj_dir, name)
        if not os.path.isfile(src):
            continue  # the plan already reported missing MTLs
        with open(src, encoding="utf-8", errors="surrogateescape", newline="") as f:
            text = f.read()
        with open(
            os.path.join(work, "visual", name), "w", encoding="utf-8", errors="surrogateescape", newline=""
        ) as f:
            f.write(_pure.mtl_with_absolute_textures(text, obj_dir.replace("\\", "/")))
    mesh = _import_moved(
        copy, plan["asset_folder"], chunk["name"], chunk["asset"], unreal.StaticMesh, 8, options, factory
    )
    err = _check_bounds(f"chunk {chunk['id']}", mesh, chunk["expected_ue_bounds_cm"])
    bm._set_nanite(mesh, True)
    slots, unmatched = _assign_slots(mesh, chunk, instances)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    _log(
        "zi.chunk",
        asset=chunk["asset"],
        tris=chunk["tris"],
        err=err,
        slots=",".join(f"{k}={v}" for k, v in sorted(slots.items())),
    )
    detail = {"tris": chunk["tris"], "bounds_error_cm": round(err, 3), "slots": slots, "unmatched": unmatched}
    return {"kind": "chunk", "asset": chunk["asset"], "ok": True, "detail": detail}


def _cleanup_folder(plan: dict) -> None:
    """Delete importer by-products (materials, textures) left in the zone folder; warn about anything else."""
    lib = unreal.EditorAssetLibrary
    expected = {c["asset"] for c in plan["chunks"]}
    expected |= {c["asset"] for c in plan["collision"]}
    expected |= {t["asset"] for t in plan["textures"]}
    expected |= {m["asset"] for m in plan["materials"]}
    expected.add(_pure.sublevel_package(plan["zone_id"], plan["version"]))
    classes = _byproduct_classes()
    for path in list(lib.list_assets(plan["asset_folder"], recursive=True, include_folder=False)):
        key = _asset_key(path)
        if key in expected:
            continue
        asset = lib.load_asset(key)
        if asset is not None and isinstance(asset, classes):
            lib.delete_asset(key)
            _log("zi.cleanup", asset=key)
        else:
            _warn(f"unexpected asset {key} left in place")


def _import_collision(col: dict, asset_folder: str, work: str, a_glb) -> dict:
    """SM_<zone_id>_collision[_<chunk_id>]: pre-transformed GLB -> import -> bounds -> complex-as-simple."""
    with open(os.path.normpath(col["glb"]), "rb") as f:
        data = f.read()
    want = _pure.expected_ue_bounds(_pure.glb_bounds_enu(data))
    copy = os.path.join(work, "collision", f"{col['name']}.glb")
    with open(copy, "wb") as f:
        f.write(_pure.pretransform_glb(data, a_glb, rename=col["name"]))
    mesh = _import_moved(copy, asset_folder, col["name"], col["asset"], unreal.StaticMesh, 29)
    err = _check_bounds(f"collision {col['id'] or 'single'}", mesh, want)
    bm._complex_collision(mesh)
    bm._set_nanite(mesh, False)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    _log("zi.collision", asset=col["asset"], err=err)
    return {
        "kind": "collision",
        "asset": col["asset"],
        "ok": True,
        "detail": {"bounds_error_cm": round(err, 3)},
    }


def _copy_files(plan: dict) -> list[dict]:
    """manifest.json (+ blockers.json) -> <Content>/Golmok/Zones/<id>/v<n>/, parsed first (design D8)."""
    dest = os.path.join(_content_dir(), *plan["content_rel"].split("/"))
    os.makedirs(dest, exist_ok=True)
    out = []
    for name in plan["copy_files"]:
        src = os.path.normpath(os.path.join(plan["zone_dir"], name))
        with open(src, "rb") as f:
            data = f.read()
        json.loads(data.decode("utf-8-sig"))  # a broken file would break AGolmokZone at load time
        target = os.path.join(dest, *name.split("/"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(src, target)
        asset = f"{plan['content_rel']}/{name}"
        out.append({"kind": "file", "asset": asset, "ok": True, "detail": {"bytes": len(data)}})
    _log("zi.copied", files=", ".join(sorted(plan["copy_files"])), dest=dest)
    return out


# ---- public entry points ---------------------------------------------------------------------------------


def import_assets(plan: dict, work_dir: str, remeasure=False, reimport_textures=True) -> tuple:
    """The asset part of run() (reused by interior_setup): (mappings, assets, warnings, route).

    mappings = {"obj": (scale, m, err), "glb": (scale, m, err)}; assets = result_json entries (textures,
    materials, chunks, collision, copied files); warnings = plan["warnings"] (already logged by log_plan)
    plus the zi.warn messages of this call. Levels, GeoOrigin and zone actors are not touched.
    """
    del _warnings[:]
    work = os.path.normpath(str(work_dir))
    for sub in ("visual", "collision"):
        os.makedirs(os.path.join(work, sub), exist_ok=True)
    asset_folder = plan["asset_folder"]
    assets: list[dict] = []
    with _step("probe"):
        route, obj_mapping, glb_mapping = _importer_mappings(work, asset_folder, remeasure)
    a_obj = _pure.inverse_mapping_matrix(obj_mapping[0], obj_mapping[1])
    a_glb = _pure.inverse_mapping_matrix(glb_mapping[0], glb_mapping[1])
    textures: dict[str, tuple] = {}  # T_ name -> (texture, vt)
    for tex in plan["textures"]:
        with _step(f"texture {tex['name']}"):
            texture, detail = _import_texture(tex, asset_folder, reimport_textures)
        textures[tex["name"]] = (texture, detail["vt"])
        assets.append({"kind": "texture", "asset": tex["asset"], "ok": True, "detail": detail})
    instances: dict[str, object] = {}
    with _step("material"):
        masters = _build_masters(textures)
        for mi in plan["materials"]:
            texture, vt = textures[mi["texture"]]
            parent = masters["vt"] if vt else masters["novt"]
            instances[mi["name"]] = materials.zone_scan_instance(texture, parent, mi["asset"])
            parent_path = _asset_key(parent.get_path_name())
            _log("zi.material", asset=mi["asset"], parent=parent_path, texture=mi["texture"])
            detail = {"parent": parent_path, "texture": mi["texture"]}
            assets.append({"kind": "material", "asset": mi["asset"], "ok": True, "detail": detail})
    factory, options = _obj_factory(route), _obj_options(route)
    with unreal.ScopedSlowTask(len(plan["chunks"]), f"Importing zone {plan['zone_id']} chunks") as task:
        task.make_dialog(False)
        for chunk in plan["chunks"]:
            task.enter_progress_frame(1, chunk["name"])
            with _step(f"chunk {chunk['id']}"):
                assets.append(_import_chunk(chunk, plan, work, a_obj, instances, factory, options))
    for col in plan["collision"]:
        with _step(f"collision {col['id'] or 'single'}"):
            assets.append(_import_collision(col, asset_folder, work, a_glb))
    with _step("cleanup"):  # after the last import, so collision by-products are swept too
        _cleanup_folder(plan)
    with _step("copy"):
        assets.extend(_copy_files(plan))
    mappings = {"obj": obj_mapping, "glb": glb_mapping}
    return mappings, assets, list(plan.get("warnings", [])) + list(_warnings), route


def write_result(work: str, result: dict) -> str:
    """<work>/import_result.json (utf-8, ensure_ascii=False, indent 2); returns its path."""
    path = os.path.join(os.path.normpath(str(work)), RESULT_NAME)
    _write_json(path, result)
    return path


def run(
    zone_dir, version=None, level=None, geo_origin=None, save=True, remeasure=False, reimport_textures=True
):
    """Import a zone folder ('.../<zone_id>', '.../<zone_id>/v<n>' or a manifest.json path) and rebuild its
    AGolmokZone in the open level (or in `level`, opened or created first). Returns the import_result dict.

    geo_origin: None keeps the level's GeoOrigin (spawned at the zone origin when there is none), "area" the
    spec area origin, "zone" the zone origin, (lat, lon, h) as given, or a basemap folder whose manifest
    origin is used. Raises ZoneImportError(step, message).
    """
    plan, manifest = make_plan(zone_dir, version)
    log_plan(plan)
    if level:
        with _step("level"):
            sz.open_or_create_level(level)
    work = work_dir(plan)
    mappings, assets, warnings, route = import_assets(plan, work, remeasure, reimport_textures)
    with _step("geo"):
        existing = _find_geo_origin()
        (lat, lon, h), how = _pure.resolve_geo_origin(geo_origin, existing, manifest, _read_json)
        sz.find_or_spawn_geo_origin(lat, lon, h)
    _log("zi.geo", lat=lat, lon=lon, h=h, how=how)
    with _step("zone"):
        zone = sz.find_or_spawn_zone(plan["zone_id"], plan["version"])
        zone.rebuild_in_editor()
    _log("zi.zone", zone_id=plan["zone_id"])
    if save:
        with _step("save"):
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    result = _pure.result_json(plan, mappings, assets, warnings, route)
    with _step("result"):
        result_path = write_result(work, result)
    _log(
        "zi.done",
        zone_id=plan["zone_id"],
        version=plan["version"],
        assets=sum(1 for a in assets if a["kind"] != "file"),
        warnings=len(warnings),
        result=result_path,
    )
    for line in _pure.summary_lines(result):
        unreal.log(line)
    return result
