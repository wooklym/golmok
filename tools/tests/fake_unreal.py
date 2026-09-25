"""Scripted fake `unreal` module for the WP-06 editor Python tests (design §5-0). A helper, not a test.

install(monkeypatch, tmp_path, **cfg) overwrites names on the shared stub module sys.modules["unreal"] (the
other UE Python tests create it as an empty types.ModuleType) with monkeypatch.setattr(raising=False), so
every name is restored, or removed again, after the test. It returns a Fake the tests read and tune:

    calls      ordered records of the editor calls that matter (RECORDS); fake.calls_of("save") filters
    registry   "/Game/..." asset path -> FakeStaticMesh | FakeTexture2D | FakeMaterial |
               FakeMaterialInstanceConstant | FakeLevel (object paths "/Game/A/B.B" are accepted everywhere)
    levels     level package -> list of FakeActor; current_level; actors = the open level's list
    logs       ("log" | "warning" | "error", text) from unreal.log/log_warning/log_error plus the errors
               the C++ console commands would print (golmok.path play without a path file, ...)
    clock      fake seconds; tick() advances it and fake.now replaces golmok.spike_runner._now
    tasks      every AssetImportTask handed to import_asset_tasks; mel_calls: MaterialEditingLibrary calls
    saved_dir, content_dir, config_dir    <tmp_path>/Saved, Content, Config (unreal.Paths.project_*_dir)

Importer (AssetToolsHelpers.get_asset_tools().import_asset_tasks) parses the real files:
    .obj  bounds = scale * M * parse_obj_bounds (+ bounds_offset[basename]), (scale, M) = obj_mapping;
          slots from usemtl order (Material_0.. when slot_names_from_usemtl=False); route "fbx"
          (task.factory is FbxFactory), "interchange" (options is InterchangeGenericAssetsPipeline),
          "legacy_flag" (console flag "Interchange.FeatureFlags.Import.OBJ 0" seen and no factory) or
          "auto"; a route outside obj_routes_ok imports nothing; importer_makes_materials adds FakeMaterial
          <dest>/<usemtl> by-products.
    .glb  raw glTF POSITION min/max (glTF axes) mapped with glb_mapping; name = destination_name or the
          glTF mesh name; slots from the glTF materials; no material assets (design §5-0).
    .png  IHDR size; a BaseName.####.ext tile with sibling tiles becomes tile x canvas_blocks when
          udim_merge (asset BaseName), otherwise a single texture named after the file (facade_1001).
    Name clashes: replace_existing overwrites, otherwise "_2". fail_import (basenames) or a missing file:
    empty result. imported_object_paths and list_assets return object paths "/Game/A/B.B".

RECORDS (fake.calls, design §5-0; "spawn" gets its label when set_actor_label is called):
    ("import", basename, dest, dest_name, route)  route None for .glb/.png   ("delete_directory", path)
    ("delete_asset", path) ("rename", old, new) ("save", path) ("create_asset", name, folder, class_name)
    ("set_material", mesh_path, index, material_path) ("set_nanite", mesh_path, enabled)
    ("spawn", class_name, label) ("destroy", label) ("rebuild_in_editor", zone_id)
    ("unload_in_editor", zone_id) ("set_visual_visible", zone_id, visible) ("hidden_in_game", label, hidden)
    ("console", command) ("begin_play",) ("end_play",) ("load_level", path) ("new_level", path)
    ("save_current_level",) ("duplicate_asset", src, dst) ("play_settings", width, height)
    additive: ("hidden_in_editor", label, hidden) ("make_udim", output_path, [(u, v), ...])
    ("add_level_to_world", package) ("high_res_screenshot", path)

KNOBS (install(**cfg) keywords = Fake attributes): obj_mapping=(100.0, M_OBJ) glb_mapping=(100.0, M_GLB)
    obj_routes_ok={"fbx","interchange","legacy_flag"} udim_merge=True texture_vt_default=True
    vt_settable=True importer_makes_materials=True slot_names_from_usemtl=True fail_import=set()
    bounds_offset={} pie=False screenshot_delay_s=0.3 csv_delay_s=0.5 screenshot_fallback_name=False
    zone_transform=ZONE_ROOT_CM begin_play_starts_pie=True level=DEFAULT_LEVEL (registered as an existing
    FakeLevel and opened, so synthetic_zone.open_or_create_level takes the load_level path instead of
    building the L_Dev lighting)

Console (SystemLibrary.execute_console_command): "golmok.tod <preset>" picks the screenshot folder;
"golmok.screenshot <tag> [name]" writes <Saved>/Screenshots/Golmok/<tag>/<preset or current>/<name>.png
(PNG signature + IHDR of the PIE window size x 2; "<name>00000.png" with screenshot_fallback_name) after
screenshot_delay_s of fake time, only while PIE runs; "golmok.path play <name> [--csv]" needs
<Saved>/Golmok/Paths/<name>.json (version 1, monotonic samples, else an error log) and with --csv writes
<Saved>/Profiling/CSV/Profile(<n>).csv after csv_delay_s; "golmok.path stopplay"; "golmok.hud 0";
"Interchange.FeatureFlags.Import.OBJ 0" arms the legacy_flag route. tick(fake, n, dt) runs the registered
slate post-tick callbacks n times, advancing the clock by dt each time and creating the files that fell due.

Libraries (EditorAssetLibrary, SystemLibrary, Paths, ...) are classes of static methods bound to the Fake, so
monkeypatch.delattr(unreal.SystemLibrary, "get_engine_version") removes one for a hasattr test; subsystems
are classes too (delattr on unreal.StaticMeshEditorSubsystem); get_editor_subsystem returns Fake instances.
EditorLevelLibrary and CesiumGeoreference are absent by default (fallback tests add them). Where the fake
merely assumes real-API behaviour (UDIM canvas size, usemtl slot names, HighResShot fallback name) the
runbook rows are docs/runbooks/pc-verify-wp06.md §12 #4, #7 and #30.
"""

from __future__ import annotations

import copy
import itertools
import json
import math
import os
import struct
import sys
import types
import zlib
from pathlib import Path

PY_DIR = Path(__file__).resolve().parents[2] / "unreal" / "Golmok" / "Content" / "Python"
if str(PY_DIR) not in sys.path:
    sys.path.insert(0, str(PY_DIR))
sys.modules.setdefault("unreal", types.ModuleType("unreal"))

from golmok import _pure as pure  # noqa: E402

M_OBJ = (
    (1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, -1.0, 0.0),
)  # design §4-2 example: OBJ (x, y, z) -> UE (x, z, -y)
M_GLB = ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0))  # glTF (x, y, z) -> UE (x, -z, y)
ENGINE_VERSION = "5.8.3-fake"
DEFAULT_LEVEL = "/Game/Golmok/Maps/L_ZoneTest"
ZONE_ROOT_CM = (17670.59, -22198.0, 999.37)  # expected.json zone_root_ue_cm (spec §4 table C)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ABSENT_BY_DEFAULT = ("EditorLevelLibrary", "CesiumGeoreference")
KNOBS = {
    "obj_mapping": (100.0, M_OBJ), "glb_mapping": (100.0, M_GLB),
    "obj_routes_ok": frozenset({"fbx", "interchange", "legacy_flag"}), "udim_merge": True,
    "texture_vt_default": True, "vt_settable": True, "importer_makes_materials": True,
    "slot_names_from_usemtl": True, "fail_import": frozenset(), "bounds_offset": {}, "pie": False,
    "screenshot_delay_s": 0.3, "csv_delay_s": 0.5, "screenshot_fallback_name": False,
    "zone_transform": ZONE_ROOT_CM, "begin_play_starts_pie": True, "level": DEFAULT_LEVEL,
}  # fmt: skip


def _key(path) -> str:
    """Asset path: '/Game/A/B.B' or '/Game/A/B/' -> '/Game/A/B'."""
    text = str(path).replace("\\", "/").rstrip("/")
    head, _, tail = text.rpartition("/")
    return f"{head}/{tail.split('.')[0]}" if "." in tail else text


def _map_bounds(bounds, scale, m, offset=(0.0, 0.0, 0.0)):
    """Axis-aligned bounds after imported = scale * M * written, shifted by offset."""
    corners = [
        tuple(sum(m[i][k] * c[k] for k in range(3)) for i in range(3))
        for c in itertools.product(*zip(bounds[0], bounds[1], strict=True))
    ]
    lo = tuple(min(c[i] for c in corners) * scale + offset[i] for i in range(3))
    hi = tuple(max(c[i] for c in corners) * scale + offset[i] for i in range(3))
    return lo, hi


def _png_bytes(w: int, h: int) -> bytes:
    """Signature + IHDR + IEND: enough for _pure.png_size, not a viewable image."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    return PNG_SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IEND", b"")


def _path_file_problem(path: str) -> str | None:
    """Why the C++ golmok.path play would refuse this path JSON (GolmokStatsMath parser rules)."""
    if not os.path.isfile(path):
        return f"no path file {path} (record it first: golmok.path record <name>)"
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as e:
        return f"invalid JSON in {path}: {e}"
    if data.get("version") != 1:
        return "version must be 1"
    samples = data.get("samples")
    if not isinstance(samples, list) or not samples:
        return "no samples"
    last = -math.inf
    for s in samples:
        t, p, r = s.get("t"), s.get("p"), s.get("r")
        if not isinstance(t, int | float) or t < last:
            return "samples[].t must be monotonic"
        if not (isinstance(p, list) and len(p) == 3 and isinstance(r, list) and len(r) == 3):
            return "samples need p[3] and r[3]"
        last = t
    return None


# ---- value types -----------------------------------------------------------------------------------------


class _Fields:
    """Positional-field struct: unreal.Vector(x, y, z), Rotator(roll, pitch, yaw), IntPoint(x, y)."""

    _fields: tuple[str, ...] = ()
    _cast = float

    def __init__(self, *values):
        values = tuple(values) + (0,) * (len(self._fields) - len(values))
        for name, value in zip(self._fields, values, strict=True):
            setattr(self, name, type(self)._cast(value))

    def to_tuple(self):
        return tuple(getattr(self, f) for f in self._fields)

    def __iter__(self):
        return iter(self.to_tuple())

    def __eq__(self, other):
        return type(other) is type(self) and self.to_tuple() == other.to_tuple()

    def __hash__(self):
        return hash(self.to_tuple())

    def __repr__(self):
        return f"{type(self).__name__}{self.to_tuple()}"


class Vector(_Fields):
    _fields = ("x", "y", "z")

    def __add__(self, other):
        return Vector(*(a + b for a, b in zip(self, other, strict=True)))

    def __sub__(self, other):
        return Vector(*(a - b for a, b in zip(self, other, strict=True)))

    def __mul__(self, k):
        return Vector(*(a * k for a in self))


class Rotator(_Fields):
    _fields = ("roll", "pitch", "yaw")


class IntPoint(_Fields):
    _fields = ("x", "y")
    _cast = int


class Quat:
    def __init__(self, rotator: Rotator):
        self._rotator = rotator

    def rotator(self) -> Rotator:
        return self._rotator


class Transform:
    def __init__(self, translation=None, rotation=None, scale3d=None):
        self.translation = translation or Vector()
        self.rotation = rotation if isinstance(rotation, Quat) else Quat(rotation or Rotator())
        self.scale3d = scale3d or Vector(1.0, 1.0, 1.0)

    def transform_location(self, v: Vector) -> Vector:
        return self.translation + v  # translation only (design §5-0)


class Name(str):
    """FName stand-in: a str, so Name('x') == 'x' and `Name(tag) in actor.tags` work."""

    __slots__ = ()


class Box:
    def __init__(self, lo: Vector, hi: Vector):
        self.min, self.max = lo, hi


def _enum(name, *members):
    return type(name, (), {m: m for m in members})


def _marker(name):
    return type(name, (), {})


FBXImportType = _enum("FBXImportType", "FBXIT_STATIC_MESH", "FBXIT_SKELETAL_MESH", "FBXIT_ANIMATION")
InterchangeForceMeshType = _enum(
    "InterchangeForceMeshType", "IFMT_NONE", "IFMT_STATIC_MESH", "IFMT_SKELETAL_MESH"
)
InterchangeMaterialImportOption = _enum(
    "InterchangeMaterialImportOption", "IMPORT_AS_MATERIALS", "IMPORT_AS_MATERIAL_INSTANCES"
)
CollisionTraceFlag = _enum(
    "CollisionTraceFlag", "CTF_USE_DEFAULT", "CTF_USE_SIMPLE_AND_COMPLEX", "CTF_USE_SIMPLE_AS_COMPLEX",
    "CTF_USE_COMPLEX_AS_SIMPLE",
)  # fmt: skip
MaterialSamplerType = _enum(
    "MaterialSamplerType", "SAMPLERTYPE_COLOR", "SAMPLERTYPE_LINEAR_COLOR", "SAMPLERTYPE_NORMAL",
    "SAMPLERTYPE_VIRTUAL_COLOR", "SAMPLERTYPE_VIRTUAL_LINEAR_COLOR", "SAMPLERTYPE_VIRTUAL_NORMAL",
)  # fmt: skip
MaterialProperty = _enum(
    "MaterialProperty", "MP_BASE_COLOR", "MP_ROUGHNESS", "MP_SPECULAR", "MP_NORMAL", "MP_METALLIC",
    "MP_EMISSIVE_COLOR", "MP_OPACITY",
)  # fmt: skip
TextureCompressionSettings = _enum(
    "TextureCompressionSettings", "TC_DEFAULT", "TC_NORMALMAP", "TC_MASKS", "TC_GRAYSCALE", "TC_BC7"
)
ComponentMobility = _enum("ComponentMobility", "STATIC", "STATIONARY", "MOVABLE")
LightUnits = _enum("LightUnits", "UNITLESS", "CANDELAS", "LUMENS")
CollisionEnabled = _enum(
    "CollisionEnabled", "NO_COLLISION", "QUERY_ONLY", "PHYSICS_ONLY", "QUERY_AND_PHYSICS"
)
CustomMaterialOutputType = _enum("CustomMaterialOutputType", "CMOT_FLOAT1", "CMOT_FLOAT3", "CMOT_FLOAT4")
PlayModeType = _enum(
    "PlayModeType", "PLAY_MODE_TYPE_PLAY_IN_VIEWPORT", "PLAY_MODE_TYPE_PLAY_IN_EDITOR_FLOATING",
    "PLAY_MODE_TYPE_PLAY_IN_NEW_PROCESS", "PLAY_MODE_TYPE_SIMULATE",
)  # fmt: skip


# ---- editor structs / objects with a fixed property set (citations.md names; typos raise) ------------------


class FakeOptions:
    """UObject/struct stand-in: only the properties in _known exist; unknown names raise AttributeError."""

    _known: dict = {}
    _kind = "FakeOptions"

    def __init__(self, **values):
        for name, default in self._known.items():
            object.__setattr__(self, name, default() if isinstance(default, type) else copy.copy(default))
        for name, value in values.items():
            setattr(self, name, value)

    def __setattr__(self, name, value):
        if name not in self._known:
            raise AttributeError(f"{self._kind} has no property {name!r}")
        object.__setattr__(self, name, value)

    def set_editor_property(self, name, value):
        setattr(self, name, value)

    def get_editor_property(self, name):
        if name not in self._known:
            raise AttributeError(f"{self._kind} has no property {name!r}")
        return getattr(self, name)


def _options(kind, known):
    return type(kind, (FakeOptions,), {"_kind": kind, "_known": known})


FbxStaticMeshImportData = _options("FbxStaticMeshImportData", {
    "build_nanite": False, "combine_meshes": False, "auto_generate_collision": True,
    "generate_lightmap_u_vs": True, "convert_scene": True, "convert_scene_unit": False,
    "force_front_x_axis": False, "import_uniform_scale": 1.0, "import_rotation": None,
    "import_translation": None, "normal_import_method": None, "remove_degenerates": True,
    "vertex_color_import_option": None, "reorder_material_to_fbx_order": True,
    "transform_vertex_to_absolute": True, "bake_pivot_in_vertex": False,
})  # fmt: skip
FbxImportUI = _options("FbxImportUI", {
    "is_obj_import": False, "import_materials": True, "import_textures": True, "import_mesh": True,
    "import_as_skeletal": False, "mesh_type_to_import": "FBXIT_STATIC_MESH",
    "automated_import_should_detect_type": True, "override_full_name": True,
    "static_mesh_import_data": FbxStaticMeshImportData, "texture_import_data": None,
    "reset_to_fbx_on_material_conflict": False, "import_animations": False, "create_physics_asset": False,
})  # fmt: skip
InterchangeGenericTexturePipeline = _options("InterchangeGenericTexturePipeline", {
    "allow_non_power_of_two": False, "asset_name": "", "detect_long_lat_cubemap": False,
    "detect_normal_map_texture": True, "file_extensions_to_import_as_long_lat_cubemap": list,
    "flip_normal_map_green_channel": False, "import_textures": True, "import_udi_ms": True,
    "pipeline_display_name": "", "prefer_compressed_source_data": False,
})  # fmt: skip
InterchangeGenericMaterialPipeline = _options("InterchangeGenericMaterialPipeline", {
    "asset_name": "", "create_material_instance_for_parent": False, "create_new_materials": True,
    "identify_duplicate_materials": False, "import_materials": True, "material_import": "IMPORT_AS_MATERIALS",
    "override_displacement": False, "parent_material": None, "reuse_existing_materials": False,
    "search_location": None, "sparse_volume_texture_pipeline": None,
    "texture_pipeline": InterchangeGenericTexturePipeline,
})  # fmt: skip
InterchangeGenericMeshPipeline = _options("InterchangeGenericMeshPipeline", {
    "build_nanite": False, "nanite_triangle_threshold": 0, "collision": True,
    "import_collision_according_to_mesh_name": True, "force_collision_primitive_generation": False,
    "fallback_collision_type": None, "combine_static_meshes": False, "combine_static_meshes_behavior": None,
    "import_static_meshes": True, "import_skeletal_meshes": True, "generate_lightmap_u_vs": True,
    "build_scale3d": None, "lod_group": None, "import_vertex_attributes": False,
})  # fmt: skip
InterchangeGenericCommonMeshesProperties = _options("InterchangeGenericCommonMeshesProperties", {
    "auto_detect_mesh_type": True, "bake_meshes": True, "bake_pivot_meshes": False,
    "force_all_mesh_as_type": "IFMT_NONE", "import_lods": True, "keep_sections_separate": False,
    "recompute_normals": False, "recompute_tangents": False, "remove_degenerates": True,
    "use_full_precision_u_vs": False, "use_mikk_t_space": True, "vertex_color_import_option": None,
    "vertex_override_color": None,
})  # fmt: skip
InterchangeGenericAssetsPipeline = _options("InterchangeGenericAssetsPipeline", {
    "animation_pipeline": None, "asset_name": "", "asset_type_sub_folders": False,
    "common_meshes_properties": InterchangeGenericCommonMeshesProperties,
    "common_skeletal_meshes_and_animations_properties": None, "groom_pipeline": None,
    "import_offset_rotation": None, "import_offset_translation": None, "import_offset_uniform_scale": 1.0,
    "material_pipeline": InterchangeGenericMaterialPipeline, "mesh_pipeline": InterchangeGenericMeshPipeline,
    "pipeline_display_name": "", "reimport_strategy": None, "scene_name_sub_folder": False,
    "use_source_name_for_asset": False,
})  # fmt: skip
MeshNaniteSettings = _options("MeshNaniteSettings", {
    "enabled": False, "fallback_percent_triangles": 1.0, "fallback_relative_error": 0.0,
    "fallback_target": None, "generate_fallback": None, "keep_percent_triangles": 1.0,
    "trim_relative_error": 0.0, "position_precision": -1, "normal_precision": -1, "tangent_precision": -1,
    "target_minimum_residency_in_kb": 0, "max_edge_length_factor": 0.0, "shape_preservation": None,
    "explicit_tangents": False,
})  # fmt: skip
BodySetup = _options("BodySetup", {"collision_trace_flag": "CTF_USE_DEFAULT"})
StaticMaterial = _options("StaticMaterial", {"material_interface": None, "material_slot_name": ""})
CustomInput = _options("CustomInput", {"input_name": ""})
LevelStreamingDynamic = _options(
    "LevelStreamingDynamic", {"initially_loaded": True, "initially_visible": True, "world_asset": None}
)
AssetImportTask = _options("AssetImportTask", {
    "async_": False, "automated": False, "destination_name": "", "destination_path": "", "factory": None,
    "filename": "", "imported_object_paths": list, "options": None, "replace_existing": False,
    "replace_existing_settings": False, "result": list, "save": True,
})  # fmt: skip
AssetImportTask.get_objects = lambda self: list(self.result)


class FakePlaySettings(FakeOptions):
    """get_default_object(unreal.LevelEditorPlaySettings); setting the window size records it."""

    _kind = "LevelEditorPlaySettings"
    _known = {"new_window_width": 1280, "new_window_height": 720, "last_executed_play_mode_type": None}

    def __init__(self, fake):
        object.__setattr__(self, "_fake", fake)
        super().__init__()

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name in ("new_window_width", "new_window_height"):
            self._fake._record_play_settings()


# ---- assets --------------------------------------------------------------------------------------------


class FakeAsset:
    unreal_name = "Object"

    def __init__(self, fake, path):
        self._fake = fake
        self.path = _key(path)
        self.props: dict = {}

    def get_path_name(self):
        return pure.object_path(self.path)

    def get_name(self):
        return self.path.rsplit("/", 1)[-1]

    def set_editor_property(self, name, value):
        self.props[name] = value

    def get_editor_property(self, name):
        if name not in self.props:
            raise AttributeError(f"{self.unreal_name} {self.path} has no property {name!r}")
        return self.props[name]

    def __repr__(self):
        return f"<{type(self).__name__} {self.path}>"


class FakeStaticMesh(FakeAsset):
    unreal_name = "StaticMesh"

    def __init__(
        self, fake, path, bounds=((0.0,) * 3, (0.0,) * 3), slots=("Material_0",), materials=(), source=""
    ):
        super().__init__(fake, path)
        self.bounds = (tuple(bounds[0]), tuple(bounds[1]))
        self.slots = list(slots)
        self.materials = list(materials) + [None] * (len(self.slots) - len(materials))
        self.nanite = MeshNaniteSettings()
        self.body_setup = BodySetup()
        self.source = source
        self.props.update({"lod_group": None, "generate_mesh_distance_field": False})

    def get_bounding_box(self):
        return Box(Vector(*self.bounds[0]), Vector(*self.bounds[1]))

    def get_editor_property(self, name):
        if name == "static_materials":
            pairs = zip(self.slots, self.materials, strict=True)
            return [StaticMaterial(material_interface=m, material_slot_name=Name(s)) for s, m in pairs]
        if name == "nanite_settings":
            return self.nanite
        if name == "body_setup":
            return self.body_setup
        return super().get_editor_property(name)

    def set_editor_property(self, name, value):
        if name == "nanite_settings":  # bm._set_nanite fallback when the subsystem lacks set_nanite_settings
            self.nanite = value
            self._fake.calls.append(("set_nanite", self.path, bool(value.enabled)))
        elif name == "static_materials":
            self.slots = [str(sm.material_slot_name) for sm in value]
            self.materials = [sm.material_interface for sm in value]
        else:
            super().set_editor_property(name, value)

    def set_material(self, material_index, new_material):
        if not 0 <= material_index < len(self.slots):
            raise IndexError(f"{self.path}: material index {material_index} of {len(self.slots)} slots")
        self.materials[material_index] = new_material
        self._fake.calls.append(
            ("set_material", self.path, material_index, getattr(new_material, "path", None))
        )

    def get_material(self, material_index):
        return self.materials[material_index]

    def get_material_index(self, material_slot_name):
        name = str(material_slot_name)
        return self.slots.index(name) if name in self.slots else -1


class FakeTexture2D(FakeAsset):
    unreal_name = "Texture2D"

    def __init__(self, fake, path, size=(256, 256), vt=None, source=""):
        super().__init__(fake, path)
        self.size = (int(size[0]), int(size[1]))
        self.source = source
        self.tiles: list[int] = []
        vt = fake.texture_vt_default if vt is None else bool(vt)
        self.props.update(virtual_texture_streaming=vt, srgb=True, compression_settings="TC_DEFAULT",
                          lod_group="TEXTUREGROUP_WORLD", never_stream=False)  # fmt: skip

    def blueprint_get_size_x(self):
        return self.size[0]

    def blueprint_get_size_y(self):
        return self.size[1]

    def set_editor_property(self, name, value):
        if name == "virtual_texture_streaming" and not self._fake.vt_settable:
            return  # the editor keeps the old value (runbook #5)
        super().set_editor_property(name, value)


class FakeMaterial(FakeAsset):
    unreal_name = "Material"

    def __init__(self, fake, path):
        super().__init__(fake, path)
        self.expressions: list[FakeExpression] = []
        self.connections: list[tuple[str, FakeExpression, str]] = []
        self.props["used_with_nanite"] = False


class FakeMaterialInstanceConstant(FakeAsset):
    unreal_name = "MaterialInstanceConstant"

    def __init__(self, fake, path):
        super().__init__(fake, path)
        self.parent = None
        self.texture_params: dict[str, FakeAsset | None] = {}
        self.scalar_params: dict[str, float] = {}

    def get_editor_property(self, name):
        return self.parent if name == "parent" else super().get_editor_property(name)


class FakeLevel(FakeAsset):
    unreal_name = "World"


class FakeExpression:
    """MaterialEditingLibrary.create_material_expression result; properties are stored, never validated."""

    def __init__(self, material, class_name, pos):
        self.material, self.class_name, self.pos, self.props = material, class_name, pos, {}

    def set_editor_property(self, name, value):
        self.props[name] = value

    def get_editor_property(self, name):
        return self.props[name]

    def __repr__(self):
        return f"<{self.class_name} {self.props}>"


# ---- actors --------------------------------------------------------------------------------------------


class Recorder:
    """Component stand-in: every method call is recorded as (name, args); set_editor_property fills props."""

    def __init__(self, label):
        self.label, self.calls, self.props = label, [], {}

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def call(*args, **kwargs):
            self.calls.append((name, args + tuple(kwargs.values())))

        return call

    def set_editor_property(self, name, value):
        self.props[name] = value
        self.calls.append(("set_editor_property", (name, value)))

    def get_editor_property(self, name):
        return self.props.get(name)


class FakeActor:
    unreal_name = "Actor"
    _defaults: dict = {}
    _count = 0

    def __init__(self, fake, label="", location=None, rotation=None, tags=(), folder="", **props):
        FakeActor._count += 1
        self._fake = fake
        self.class_name = self.unreal_name
        self.label = label or f"{self.unreal_name}_{FakeActor._count}"
        self.location = location or Vector()
        self.rotation = rotation or Rotator()
        self.scale = Vector(1.0, 1.0, 1.0)
        self.tags = [Name(t) for t in tags]
        self.folder = folder
        self.hidden_in_game = self.hidden_in_editor = False
        self.props = {**self._defaults, **props}
        self.component: Recorder | None = None
        self.mesh = None
        self._spawn_record: int | None = None

    def _clone(self):
        other = copy.copy(self)
        other.tags, other.props, other._spawn_record = list(self.tags), dict(self.props), None
        return other

    def get_actor_label(self):
        return self.label

    def set_actor_label(self, label, mark_dirty=True):
        self.label = str(label)
        i = self._spawn_record
        if i is not None and i < len(self._fake.calls) and self._fake.calls[i][0] == "spawn":
            self._fake.calls[i] = ("spawn", self.unreal_name, self.label)

    def get_name(self):
        return self.label

    def get_folder_path(self):
        return Name(self.folder)

    def set_folder_path(self, path):
        self.folder = str(path)

    def get_actor_location(self):
        return copy.copy(self.location)

    def set_actor_location(self, location, sweep=False, teleport=False):
        self.location = location
        return True

    def set_actor_rotation(self, rotation, teleport_physics=False):
        self.rotation = rotation
        return True

    def set_actor_scale3d(self, scale):
        self.scale = scale

    def get_actor_transform(self):
        return Transform(copy.copy(self.location), copy.copy(self.rotation), copy.copy(self.scale))

    def set_actor_hidden_in_game(self, hidden):
        self.hidden_in_game = bool(hidden)
        self._fake.calls.append(("hidden_in_game", self.label, bool(hidden)))

    def set_is_temporarily_hidden_in_editor(self, hidden):
        self.hidden_in_editor = bool(hidden)
        self._fake.calls.append(("hidden_in_editor", self.label, bool(hidden)))

    def get_component_by_class(self, component_class):
        return self.component

    def set_editor_property(self, name, value):
        if name == "tags":
            self.tags = [Name(t) for t in value]
        elif name == "hidden":
            self.set_actor_hidden_in_game(value)
        else:
            self.props[name] = value

    def get_editor_property(self, name):
        if name == "tags":
            return self.tags
        if name == "hidden":
            return self.hidden_in_game
        if name not in self.props:
            raise AttributeError(f"{self.unreal_name} {self.label!r} has no property {name!r}")
        return self.props[name]

    def __repr__(self):
        return f"<{self.unreal_name} {self.label!r}>"


class FakeZoneActor(FakeActor):
    """AGolmokZone: zone_id / version / auto_managed, rebuild/unload/set_visual_visible recorded."""

    unreal_name = "GolmokZone"
    _defaults = {"zone_id": "", "version": 1, "auto_managed": True}

    def rebuild_in_editor(self):
        self._fake.calls.append(("rebuild_in_editor", self.props.get("zone_id")))
        t = self._fake.zone_transform
        self.location, self.rotation = copy.copy(t.translation), copy.copy(t.rotation.rotator())

    def unload_in_editor(self):
        self._fake.calls.append(("unload_in_editor", self.props.get("zone_id")))

    def set_visual_visible(self, visible):
        self._fake.calls.append(("set_visual_visible", self.props.get("zone_id"), bool(visible)))


class FakeGeoOrigin(FakeActor):
    unreal_name = "GolmokGeoOrigin"
    _defaults = {"latitude": 0.0, "longitude": 0.0, "height_ellipsoidal": 0.0}


class FakePointLight(FakeActor):
    unreal_name = "PointLight"

    def __init__(self, fake, label="", location=None, rotation=None, tags=(), folder="", **props):
        super().__init__(fake, label, location, rotation, tags, folder, **props)
        self.component = Recorder(f"{self.label}.PointLightComponent")


# Component returned by get_component_by_class() for the lighting actors setup_dev_level._build_lighting()
# spawns (sun_comp.set_mobility / set_intensity / set_editor_property are recorded like FakePointLight's).
_LIGHT_COMPONENTS = {
    "DirectionalLight": "DirectionalLightComponent",
    "SkyLight": "SkyLightComponent",
    "ExponentialHeightFog": "ExponentialHeightFogComponent",
}


def _actor_class(name):
    component_name = _LIGHT_COMPONENTS.get(name)

    def __init__(self, fake, label="", location=None, rotation=None, tags=(), folder="", **props):
        FakeActor.__init__(self, fake, label, location, rotation, tags, folder, **props)
        if component_name:
            self.component = Recorder(f"{self.label}.{component_name}")

    return type(name, (FakeActor,), {"unreal_name": name, "__init__": __init__})


StaticMeshActor = _actor_class("StaticMeshActor")
EXTRA_ACTORS = {n: _actor_class(n) for n in (
    "PlayerStart", "DirectionalLight", "SkyLight", "ExponentialHeightFog", "PostProcessVolume",
    "SkyAtmosphere",
)}  # fmt: skip
ACTOR_CLASSES = dict(EXTRA_ACTORS)
for _cls in (FakeActor, FakeZoneActor, FakeGeoOrigin, FakePointLight, StaticMeshActor):
    ACTOR_CLASSES[_cls.unreal_name] = _cls


class FakeWorld:
    def __init__(self, fake, kind):
        self._fake, self.kind = fake, kind

    def get_name(self):
        return self._fake.current_level.rsplit("/", 1)[-1]

    def get_path_name(self):
        return pure.object_path(self._fake.current_level)


class FakePlayerController:
    def get_name(self):
        return "PlayerController_0"


# ---- subsystems and libraries (instances bound to the Fake) -----------------------------------------------


class _Bound:
    def __init__(self, fake):
        self._fake = fake


class EditorActorSubsystem(_Bound):
    def get_all_level_actors(self):
        return list(self._fake.actors)

    def _add(self, actor):
        self._fake.actors.append(actor)
        actor._spawn_record = len(self._fake.calls)
        self._fake.calls.append(("spawn", actor.unreal_name, actor.label))
        return actor

    def spawn_actor_from_class(self, actor_class, location=None, rotation=None, transient=False):
        if not (isinstance(actor_class, type) and issubclass(actor_class, FakeActor)):
            raise TypeError(f"fake unreal: cannot spawn {actor_class!r} (not an actor class of the fake)")
        return self._add(actor_class(self._fake, location=location, rotation=rotation))

    def spawn_actor_from_object(self, object_to_use, location=None, rotation=None, transient=False):
        actor = StaticMeshActor(self._fake, location=location, rotation=rotation)
        actor.mesh = object_to_use
        return self._add(actor)

    def destroy_actor(self, actor):
        for actors in self._fake.levels.values():
            if actor in actors:
                actors.remove(actor)
                self._fake.calls.append(("destroy", actor.label))
                return True
        return False

    def destroy_actors(self, actors):
        return all([self.destroy_actor(a) for a in list(actors)])


class LevelEditorSubsystem(_Bound):
    def load_level(self, asset_path):
        key = _key(asset_path)
        if not isinstance(self._fake.registry.get(key), FakeLevel):
            return False
        self._fake.current_level = key
        self._fake.levels.setdefault(key, [])
        self._fake.calls.append(("load_level", key))
        return True

    def new_level(self, asset_path, is_partitioned_world=False):
        key = _key(asset_path)
        self._fake.registry[key] = FakeLevel(self._fake, key)
        self._fake.levels[key] = []
        self._fake.current_level = key
        self._fake.calls.append(("new_level", key))
        return True

    def save_current_level(self):
        self._fake.calls.append(("save_current_level",))
        return True

    def editor_request_begin_play(self):
        self._fake.calls.append(("begin_play",))
        if self._fake.begin_play_starts_pie:
            self._fake.pie = True

    def editor_request_end_play(self):
        self._fake.calls.append(("end_play",))
        self._fake.pie, self._fake.playing = False, None

    def is_in_play_in_editor(self):
        return self._fake.pie

    def editor_set_viewport_realtime(self, realtime):
        self._fake.viewport_realtime = bool(realtime)

    def editor_get_game_view(self, viewport_config_key="None"):
        return self._fake.game_view

    def editor_set_game_view(self, game_view, viewport_config_key="None"):
        self._fake.game_view = bool(game_view)

    def editor_invalidate_viewports(self):
        pass


class UnrealEditorSubsystem(_Bound):
    def get_editor_world(self):
        return self._fake.editor_world

    def get_game_world(self):
        return self._fake.pie_world if self._fake.pie else None

    def get_level_viewport_camera_info(self):
        return self._fake.camera

    def set_level_viewport_camera_info(self, location, rotation):
        self._fake.camera = (location, rotation)
        return True


class StaticMeshEditorSubsystem(_Bound):
    def set_nanite_settings(self, static_mesh, nanite_settings, apply_changes=True):
        static_mesh.nanite = nanite_settings
        self._fake.calls.append(("set_nanite", static_mesh.path, bool(nanite_settings.enabled)))

    def get_nanite_settings(self, static_mesh):
        return static_mesh.nanite


class FakeEditorAssetLibrary(_Bound):
    def does_asset_exist(self, asset_path):
        return _key(asset_path) in self._fake.registry

    def does_directory_exist(self, directory_path):
        prefix = _key(directory_path) + "/"
        return any(k.startswith(prefix) for k in self._fake.registry)

    def make_directory(self, directory_path):
        return True

    def load_asset(self, asset_path):
        return self._fake.registry.get(_key(asset_path))

    def save_loaded_asset(self, asset_to_save, only_if_is_dirty=True):
        self._fake.calls.append(("save", asset_to_save.path))
        return True

    def delete_asset(self, asset_path):
        key = _key(asset_path)
        self._fake.calls.append(("delete_asset", key))
        return self._fake.registry.pop(key, None) is not None

    def delete_directory(self, directory_path):
        key = _key(directory_path)
        self._fake.calls.append(("delete_directory", key))
        for k in [k for k in self._fake.registry if k.startswith(key + "/")]:
            del self._fake.registry[k]
        return True

    def rename_asset(self, source_asset_path, destination_asset_path):
        old, new = _key(source_asset_path), _key(destination_asset_path)
        self._fake.calls.append(("rename", old, new))
        asset = self._fake.registry.pop(old, None)
        if asset is None:
            return False
        asset.path = new
        self._fake.registry[new] = asset
        if isinstance(asset, FakeLevel) and old in self._fake.levels:
            self._fake.levels[new] = self._fake.levels.pop(old)
        return True

    def duplicate_asset(self, source_asset_path, destination_asset_path):
        src, dst = _key(source_asset_path), _key(destination_asset_path)
        self._fake.calls.append(("duplicate_asset", src, dst))
        asset = self._fake.registry.get(src)
        if asset is None:
            return None
        dup = copy.copy(asset)
        dup.path, dup.props = dst, dict(asset.props)
        self._fake.registry[dst] = dup
        if isinstance(asset, FakeLevel):
            self._fake.levels[dst] = [a._clone() for a in self._fake.levels.get(src, [])]
        return dup

    def list_assets(self, directory_path, recursive=True, include_folder=False):
        prefix = _key(directory_path) + "/"
        out, folders = [], set()
        for key in sorted(self._fake.registry):
            rest = key[len(prefix) :] if key.startswith(prefix) else None
            if rest is None:
                continue
            if "/" in rest:
                folders.add(prefix + rest.split("/", 1)[0] + "/")
                if not recursive:
                    continue
            out.append(pure.object_path(key))
        return out + (sorted(folders) if include_folder else [])


class FakeMaterialEditingLibrary(_Bound):
    """Stateful calls are explicit; the record-only ones (RECORD_ONLY_MEL) just append to fake.mel_calls."""

    def _rec(self, name, *args):
        self._fake.mel_calls.append((name, args))
        return True

    def create_material_expression(self, material, expression_class, node_pos_x=0, node_pos_y=0):
        self._fake.mel_calls.append(("create_material_expression", (material, expression_class)))
        expression = FakeExpression(material, expression_class.__name__, (node_pos_x, node_pos_y))
        material.expressions.append(expression)
        return expression

    def connect_material_property(self, from_expression, from_output_name, material_property):
        self._fake.mel_calls.append(
            ("connect_material_property", (from_expression, from_output_name, material_property))
        )
        from_expression.material.connections.append((material_property, from_expression, from_output_name))
        return True

    def set_material_instance_parent(self, instance, new_parent):
        self._fake.mel_calls.append(("set_material_instance_parent", (instance, new_parent)))
        instance.parent = new_parent
        return True

    def set_material_instance_texture_parameter_value(
        self, instance, parameter_name, value, association=None
    ):
        self._fake.mel_calls.append(
            ("set_material_instance_texture_parameter_value", (instance, parameter_name, value))
        )
        instance.texture_params[str(parameter_name)] = value
        return True

    def set_material_instance_scalar_parameter_value(self, instance, parameter_name, value, association=None):
        self._fake.mel_calls.append(
            ("set_material_instance_scalar_parameter_value", (instance, parameter_name, value))
        )
        instance.scalar_params[str(parameter_name)] = value
        return True


RECORD_ONLY_MEL = ("connect_material_expressions", "recompile_material", "update_material_instance",
                   "layout_material_expressions", "set_material_usage")  # fmt: skip
for _name in RECORD_ONLY_MEL:
    setattr(FakeMaterialEditingLibrary, _name, (lambda n: lambda self, *a, **k: self._rec(n, *a))(_name))


class FakeAssetTools(_Bound):
    def create_asset(self, asset_name, package_path, asset_class, factory, calling_context=None):
        if not (isinstance(asset_class, type) and issubclass(asset_class, FakeAsset)):
            raise TypeError(f"fake unreal: cannot create {asset_class!r}")
        folder = _key(package_path)
        asset = asset_class(self._fake, f"{folder}/{asset_name}")
        self._fake.registry[asset.path] = asset
        self._fake.calls.append(("create_asset", asset_name, folder, asset_class.unreal_name))
        return asset

    def import_asset_tasks(self, tasks):
        for task in tasks:
            self._fake.tasks.append(task)
            filename = str(task.filename)
            basename = os.path.basename(filename)
            ext = os.path.splitext(basename)[1].lower()
            dest, name = _key(task.destination_path), task.destination_name or None
            route = _obj_route(self._fake, task) if ext == ".obj" else None
            importer = {".obj": _import_obj, ".glb": _import_glb, ".png": _import_png}.get(ext)
            if importer is None:
                raise RuntimeError(f"fake unreal: no importer for {basename}")
            assets = []
            if basename not in self._fake.fail_import and os.path.isfile(filename):
                assets = importer(self._fake, task, filename, dest, name, route)
            self._fake.calls.append(("import", basename, dest, name, route))
            task.imported_object_paths = [a.get_path_name() for a in assets]
            task.result = list(assets)


class FakeAssetToolsHelpers:
    def __init__(self, fake):
        self._tools = FakeAssetTools(fake)

    def get_asset_tools(self):
        return self._tools


class FakeSystemLibrary(_Bound):
    def get_engine_version(self):
        return ENGINE_VERSION

    def execute_console_command(self, world_context_object, command, specific_player=None):
        fake = self._fake
        fake.calls.append(("console", command))
        parts = command.split()
        head, args = (parts[0], parts[1:]) if parts else ("", [])
        if head == "Interchange.FeatureFlags.Import.OBJ":
            fake.legacy_flag = bool(args) and args[0] == "0"
        elif head == "golmok.tod" and args:
            fake.preset = args[0]
        elif head == "golmok.hud":
            fake.hud = not (args and args[0] == "0")
        elif head == "golmok.screenshot":
            fake._screenshot(args)
        elif head == "golmok.path":
            fake._path_command(args)


class FakeGameplayStatics(_Bound):
    def get_all_actors_of_class(self, world_context_object, actor_class):
        return [a for a in self._fake.actors if isinstance(a, actor_class)]

    def get_player_controller(self, world_context_object, player_index=0):
        return self._fake.player_controller if self._fake.pie else None


class FakeUdimLibrary(_Bound):
    def make_udim_virtual_texture_from_texture2_ds(
        self,
        output_path_name,
        source_textures,
        block_coords,
        keep_existing_settings=False,
        check_out_and_save=False,
    ):
        coords = [(int(p.x), int(p.y)) for p in block_coords]
        if not coords or len(coords) != len(source_textures):
            raise ValueError("fake unreal: block_coords must match source_textures")
        tile_w, tile_h = (max(t.size[i] for t in source_textures) for i in (0, 1))
        size = ((max(u for u, _ in coords) + 1) * tile_w, (max(v for _, v in coords) + 1) * tile_h)
        tex = FakeTexture2D(self._fake, output_path_name, size, vt=True)
        tex.tiles = sorted(pure.UDIM_MIN + u + 10 * v for u, v in coords)
        self._fake.registry[tex.path] = tex
        self._fake.calls.append(("make_udim", tex.path, coords))
        return tex


class FakePaths(_Bound):
    """project_saved_dir() etc.: '<tmp_path>/Saved/' (forward slashes + trailing slash, like the editor)."""

    def get_project_file_path(self):
        return f"{self._fake.root.as_posix()}/Golmok.uproject"

    def project_dir(self):
        return self._fake.root.as_posix() + "/"


for _method, _folder in (("project_saved_dir", "Saved"), ("project_content_dir", "Content"),
                         ("project_config_dir", "Config"), ("engine_dir", "Engine")):  # fmt: skip
    setattr(
        FakePaths, _method, (lambda folder: lambda self: f"{self._fake.root.as_posix()}/{folder}/")(_folder)
    )


class FakeAutomationLibrary(_Bound):
    def take_high_res_screenshot(self, res_x, res_y, filename, *args, **kwargs):
        path = os.path.normpath(str(filename))
        self._fake.calls.append(("high_res_screenshot", path))
        self._fake.schedule_file(self._fake.screenshot_delay_s, path, _png_bytes(res_x, res_y))
        return True


class FakeEditorLevelUtils(_Bound):
    def add_level_to_world(self, world, level_package_name, level_streaming_class):
        key = _key(level_package_name)
        self._fake.calls.append(("add_level_to_world", key))
        return LevelStreamingDynamic(world_asset=key)


class ScopedSlowTask(Recorder):
    """`with unreal.ScopedSlowTask(n, label) as task:` no-op; should_cancel() returns None (falsy)."""

    def __init__(self, amount_of_work, default_message="", enabled=True):
        super().__init__("ScopedSlowTask")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


# ---- importer ------------------------------------------------------------------------------------------


def _obj_route(fake, task) -> str:
    if isinstance(task.factory, FbxFactory):
        return "fbx"
    if isinstance(task.options, InterchangeGenericAssetsPipeline):
        return "interchange"
    if fake.legacy_flag and task.factory is None:
        return "legacy_flag"
    return "auto"


def _register(fake, asset, replace_existing):
    if not replace_existing:
        while asset.path in fake.registry:
            asset.path += "_2"
    fake.registry[asset.path] = asset
    return asset


def _import_obj(fake, task, filename, dest, name, route):
    if route not in fake.obj_routes_ok:
        return []
    with open(filename, encoding="utf-8", errors="surrogateescape", newline="") as f:
        lines = f.readlines()
    scale, m = fake.obj_mapping
    basename = os.path.basename(filename)
    bounds = _map_bounds(
        pure.parse_obj_bounds(lines), scale, m, fake.bounds_offset.get(basename, (0.0, 0.0, 0.0))
    )
    usemtl = pure.usemtl_order(lines)
    slots = usemtl if fake.slot_names_from_usemtl else [f"Material_{i}" for i in range(len(usemtl))]
    materials = []
    if fake.importer_makes_materials:  # by-products of an importer that ignores import_materials=False
        materials = [
            _register(fake, FakeMaterial(fake, f"{dest}/{n}"), task.replace_existing) for n in usemtl
        ]
    stem = os.path.splitext(basename)[0]
    mesh = FakeStaticMesh(
        fake, f"{dest}/{name or stem}", bounds, slots or ["Material_0"], materials, filename
    )
    return [_register(fake, mesh, task.replace_existing), *materials]


def _import_glb(fake, task, filename, dest, name, route=None):
    with open(filename, "rb") as f:
        data = f.read()
    gltf = json.loads(data[20 : 20 + struct.unpack_from("<I", data, 12)[0]])
    (ex0, ey0, ez0), (ex1, ey1, ez1) = pure.glb_bounds_enu(data)  # ENU = (x, -z, y) of the glTF axes
    raw = ((ex0, ez0, -ey1), (ex1, ez1, -ey0))  # back to glTF (x, y, z): what a real importer reads
    scale, m = fake.glb_mapping
    basename = os.path.basename(filename)
    bounds = _map_bounds(raw, scale, m, fake.bounds_offset.get(basename, (0.0, 0.0, 0.0)))
    meshes, nodes = gltf.get("meshes") or [{}], gltf.get("nodes") or [{}]
    mesh_name = name or meshes[0].get("name") or nodes[0].get("name") or os.path.splitext(basename)[0]
    slots = [mat.get("name") or f"Material_{i}" for i, mat in enumerate(gltf.get("materials", []))]
    mesh = FakeStaticMesh(fake, f"{dest}/{mesh_name}", bounds, slots or ["Material_0"], (), filename)
    return [_register(fake, mesh, task.replace_existing)]


def _import_png(fake, task, filename, dest, name, route=None):
    with open(filename, "rb") as f:
        w, h = pure.png_size(f.read(24))
    basename = os.path.basename(filename)
    split = pure.udim_split(basename)
    merged = (
        split is not None and fake.udim_merge
    )  # runbook #4: BaseName.####.ext siblings become one texture
    tiles = pure.udim_group(filename, os.listdir)["tiles"] if merged else []
    if len(tiles) > 1:
        bu, bv = pure.udim_canvas_blocks(tiles)
        w, h = w * bu, h * bv
    default = split[0] if merged else pure.asset_name_safe(basename.rsplit(".", 1)[0])
    tex = FakeTexture2D(fake, f"{dest}/{name or default}", (w, h), None, filename)
    tex.tiles = tiles if len(tiles) > 1 else []
    return [_register(fake, tex, task.replace_existing)]


# ---- the Fake --------------------------------------------------------------------------------------------


def _as_transform(value) -> Transform:
    if isinstance(value, Transform):
        return value
    if len(value) == 2 and isinstance(value[0], tuple | list):
        return Transform(Vector(*value[0]), Rotator(0.0, 0.0, float(value[1])))
    return Transform(Vector(*value))


class Fake:
    """State and knobs of one installed fake unreal (see the module docstring)."""

    def __init__(self, monkeypatch, tmp_path, module, **cfg):
        if unknown := set(cfg) - set(KNOBS):
            raise TypeError(f"fake_unreal.install: unknown knobs {sorted(unknown)}")
        self._monkeypatch, self.module = monkeypatch, module
        self.root = Path(tmp_path)
        self.saved_dir, self.content_dir, self.config_dir = (
            str(self.root / d) for d in ("Saved", "Content", "Config")
        )
        for d in (self.saved_dir, self.content_dir, self.config_dir):
            os.makedirs(d, exist_ok=True)
        for knob, default in KNOBS.items():
            value = cfg.get(knob, default)
            if knob in ("obj_routes_ok", "fail_import"):
                value = set(value)
            elif knob == "bounds_offset":
                value = dict(value)
            elif knob == "zone_transform":
                value = _as_transform(value)
            elif knob == "level":
                continue
            setattr(self, knob, value)
        self.calls: list[tuple] = []
        self.registry: dict[str, FakeAsset] = {}
        self.levels: dict[str, list[FakeActor]] = {}
        self.logs: list[tuple[str, str]] = []
        self.tasks: list = []
        self.mel_calls: list[tuple] = []
        self.callbacks: dict[int, object] = {}
        self._next_handle = 1
        self.pending_files: list[tuple[float, str, bytes, str | None]] = []
        self.clock = 0.0
        self.now = self._clock_now  # one bound method object: bind_clock() and tests compare it by identity
        self.legacy_flag = False
        self.preset: str | None = None
        self.hud = True
        self.playing: str | None = None
        self.csv_count = 0
        self.game_view = self.viewport_realtime = False
        self.camera = (Vector(), Rotator())
        self.play_settings = FakePlaySettings(self)
        self.editor_world, self.pie_world = FakeWorld(self, "editor"), FakeWorld(self, "pie")
        self.player_controller = FakePlayerController()
        level = _key(cfg.get("level", DEFAULT_LEVEL))
        self.registry[level] = FakeLevel(self, level)
        self.levels[level] = []
        self.current_level = level
        self.actor_subsystem, self.level_editor = EditorActorSubsystem(self), LevelEditorSubsystem(self)
        self.editor_subsystem, self.static_mesh_editor = (
            UnrealEditorSubsystem(self),
            StaticMeshEditorSubsystem(self),
        )
        self.subsystems = {
            EditorActorSubsystem: self.actor_subsystem, LevelEditorSubsystem: self.level_editor,
            UnrealEditorSubsystem: self.editor_subsystem, StaticMeshEditorSubsystem: self.static_mesh_editor,
        }  # fmt: skip
        self.asset_library, self.asset_tools = FakeEditorAssetLibrary(self), FakeAssetToolsHelpers(self)

    # -- state helpers for tests --

    @property
    def actors(self) -> list[FakeActor]:
        return self.levels.setdefault(self.current_level, [])

    @actors.setter
    def actors(self, value):
        self.levels[self.current_level] = list(value)

    def _clock_now(self) -> float:
        return self.clock

    def calls_of(self, name) -> list[tuple]:
        return [c for c in self.calls if c[0] == name]

    def logged(self, kind=None) -> list[str]:
        return [text for k, text in self.logs if kind is None or k == kind]

    def add_actor(self, actor_class, label, tags=(), location=None, level=None, **props) -> FakeActor:
        """Seed an actor without a spawn record; actor_class is a fake class or an unreal class name."""
        cls = ACTOR_CLASSES[actor_class] if isinstance(actor_class, str) else actor_class
        actor = cls(self, label, location=location, tags=tags, **props)
        self.levels.setdefault(_key(level) if level else self.current_level, []).append(actor)
        return actor

    def bind_clock(self):
        """golmok.spike_runner._now -> fake clock (once the module is imported)."""
        sr = sys.modules.get("golmok.spike_runner")
        if sr is not None and getattr(sr, "_now", None) is not self.now:
            self._monkeypatch.setattr(sr, "_now", self.now, raising=False)

    # -- delayed files (screenshots, CSV) --

    def schedule_file(self, delay_s, path, content: bytes, message: str | None = None):
        self.pending_files.append((self.clock + delay_s, os.path.normpath(path), content, message))

    def flush_files(self):
        for entry in [e for e in self.pending_files if e[0] <= self.clock + 1e-9]:
            self.pending_files.remove(entry)
            _, path, content, message = entry
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(content)
            if message:
                self.logs.append(("log", message))

    # -- console command semantics --

    def _record_play_settings(self):
        record = ("play_settings", self.play_settings.new_window_width, self.play_settings.new_window_height)
        if self.calls and self.calls[-1][0] == "play_settings":
            self.calls[-1] = record
        else:
            self.calls.append(record)

    def _screenshot(self, args):
        tag, name = (args[0] if args else ""), (args[1] if len(args) > 1 else "shot")
        if not (pure.NAME_RE.match(tag) and pure.NAME_RE.match(name)):
            self.logs.append(
                ("error", f"golmok.screenshot: ERROR usage golmok.screenshot <tag> [name] ({args})")
            )
            return
        if not self.pie:
            self.logs.append(("error", "golmok.screenshot: ERROR no game viewport (PIE is not running)"))
            return
        path = os.path.normpath(pure.screenshot_path(self.saved_dir, tag, self.preset, name))
        if self.screenshot_fallback_name:  # runbook #30: HighResShot counter name
            path = pure.screenshot_fallback_path(path)
        w, h = self.play_settings.new_window_width, self.play_settings.new_window_height
        k = pure.SCREENSHOT_MULTIPLIER
        self.schedule_file(self.screenshot_delay_s, path, _png_bytes(w * k, h * k))

    def _path_command(self, args):
        sub = args[0] if args else ""
        if sub == "play":
            if len(args) < 2:
                self.logs.append(("error", "golmok.path play: ERROR usage: golmok.path play <name> [--csv]"))
                return
            name = args[1]
            problem = _path_file_problem(os.path.join(self.saved_dir, "Golmok", "Paths", f"{name}.json"))
            if problem:
                self.logs.append(("error", f"golmok.path play: ERROR {problem}"))
                return
            self.playing = name
            if "--csv" in args[2:]:
                self.csv_count += 1
                path = os.path.join(self.saved_dir, "Profiling", "CSV", f"Profile({self.csv_count}).csv")
                self.schedule_file(
                    self.csv_delay_s, path, b"FrameTime\n16.7\n", f"GolmokDebugSubsystem: csv: {path}"
                )
        elif sub == "stopplay":
            if self.playing is None:
                self.logs.append(("log", "golmok.path stopplay: ERROR not playing"))
            self.playing = None


# ---- install / tick --------------------------------------------------------------------------------------

MATERIAL_EXPRESSIONS = (
    "MaterialExpressionTextureSampleParameter2D", "MaterialExpressionConstant",
    "MaterialExpressionTextureCoordinate", "MaterialExpressionVertexColor", "MaterialExpressionCustom",
    "MaterialExpressionComponentMask", "MaterialExpressionScalarParameter",
    "MaterialExpressionVectorParameter", "MaterialExpressionMultiply",
)  # fmt: skip
COMPONENT_CLASSES = ("PointLightComponent", "StaticMeshComponent", "DirectionalLightComponent",
                     "SkyLightComponent", "ExponentialHeightFogComponent")  # fmt: skip
FbxFactory = _marker("FbxFactory")
MaterialFactoryNew = _marker("MaterialFactoryNew")
MaterialInstanceConstantFactoryNew = _marker("MaterialInstanceConstantFactoryNew")


def _static_library(name: str, instance) -> type:
    """A class like unreal.EditorAssetLibrary: static methods bound to this Fake, so a test can remove one
    with monkeypatch.delattr(unreal.SystemLibrary, "get_engine_version") for the hasattr branches."""
    methods = {n: staticmethod(getattr(instance, n)) for n in dir(type(instance)) if not n.startswith("_")}
    return type(name, (), methods)


def _names(fake: Fake) -> dict:
    """Everything install() puts on the `unreal` module."""

    def get_editor_subsystem(cls):
        for key, instance in fake.subsystems.items():
            if key is cls:
                return instance
        raise RuntimeError(f"fake unreal: no subsystem for {cls!r}")

    def get_default_object(cls):
        if cls is FakePlaySettings:
            return fake.play_settings
        raise RuntimeError(f"fake unreal: no default object for {cls!r}")

    def register_slate_post_tick_callback(callable_):
        handle, fake._next_handle = fake._next_handle, fake._next_handle + 1
        fake.callbacks[handle] = callable_
        return handle

    names = {
        "log": lambda text: fake.logs.append(("log", str(text))),
        "log_warning": lambda text: fake.logs.append(("warning", str(text))),
        "log_error": lambda text: fake.logs.append(("error", str(text))),
        "get_editor_subsystem": get_editor_subsystem, "get_default_object": get_default_object,
        "register_slate_post_tick_callback": register_slate_post_tick_callback,
        "unregister_slate_post_tick_callback": lambda handle: fake.callbacks.pop(handle, None),
        "Vector": Vector, "Rotator": Rotator, "Transform": Transform, "Quat": Quat, "Name": Name,
        "IntPoint": IntPoint, "Box": Box, "ScopedSlowTask": ScopedSlowTask,
        "Actor": FakeActor, "GolmokZone": FakeZoneActor, "GolmokGeoOrigin": FakeGeoOrigin,
        "PointLight": FakePointLight, "StaticMeshActor": StaticMeshActor, **EXTRA_ACTORS,
        "StaticMesh": FakeStaticMesh, "Texture2D": FakeTexture2D, "Texture": FakeTexture2D,
        "Material": FakeMaterial, "MaterialInstanceConstant": FakeMaterialInstanceConstant,
        "World": FakeLevel, "MaterialFactoryNew": MaterialFactoryNew, "FbxFactory": FbxFactory,
        "MaterialInstanceConstantFactoryNew": MaterialInstanceConstantFactoryNew,
        "AssetImportTask": AssetImportTask, "FbxImportUI": FbxImportUI, "FBXImportType": FBXImportType,
        "FbxStaticMeshImportData": FbxStaticMeshImportData,
        "InterchangeGenericAssetsPipeline": InterchangeGenericAssetsPipeline,
        "InterchangeGenericMaterialPipeline": InterchangeGenericMaterialPipeline,
        "InterchangeGenericTexturePipeline": InterchangeGenericTexturePipeline,
        "InterchangeGenericMeshPipeline": InterchangeGenericMeshPipeline,
        "InterchangeGenericCommonMeshesProperties": InterchangeGenericCommonMeshesProperties,
        "InterchangeForceMeshType": InterchangeForceMeshType,
        "InterchangeMaterialImportOption": InterchangeMaterialImportOption,
        "CollisionTraceFlag": CollisionTraceFlag, "MaterialSamplerType": MaterialSamplerType,
        "MaterialProperty": MaterialProperty, "TextureCompressionSettings": TextureCompressionSettings,
        "ComponentMobility": ComponentMobility, "LightUnits": LightUnits, "CustomInput": CustomInput,
        "CollisionEnabled": CollisionEnabled, "CustomMaterialOutputType": CustomMaterialOutputType,
        "MeshNaniteSettings": MeshNaniteSettings, "BodySetup": BodySetup, "StaticMaterial": StaticMaterial,
        "LevelEditorPlaySettings": FakePlaySettings, "PlayModeType": PlayModeType,
        "LevelStreamingDynamic": LevelStreamingDynamic,
        "EditorActorSubsystem": EditorActorSubsystem, "LevelEditorSubsystem": LevelEditorSubsystem,
        "UnrealEditorSubsystem": UnrealEditorSubsystem,
        "StaticMeshEditorSubsystem": StaticMeshEditorSubsystem,
    }  # fmt: skip
    libraries = {
        "EditorAssetLibrary": fake.asset_library, "AssetToolsHelpers": fake.asset_tools,
        "MaterialEditingLibrary": FakeMaterialEditingLibrary(fake), "SystemLibrary": FakeSystemLibrary(fake),
        "GameplayStatics": FakeGameplayStatics(fake), "UDIMTextureFunctionLibrary": FakeUdimLibrary(fake),
        "Paths": FakePaths(fake), "AutomationLibrary": FakeAutomationLibrary(fake),
        "EditorLevelUtils": FakeEditorLevelUtils(fake),
    }  # fmt: skip
    names.update({n: _static_library(n, instance) for n, instance in libraries.items()})
    names.update({n: _marker(n) for n in MATERIAL_EXPRESSIONS + COMPONENT_CLASSES})
    return names


def install(monkeypatch, tmp_path, **cfg) -> Fake:
    """Put the fake on sys.modules['unreal'] for one test (monkeypatch restores it) and return its Fake."""
    if str(PY_DIR) not in sys.path:
        sys.path.insert(0, str(PY_DIR))
    module = sys.modules.setdefault("unreal", types.ModuleType("unreal"))
    fake = Fake(monkeypatch, tmp_path, module, **cfg)
    for name, value in _names(fake).items():
        monkeypatch.setattr(module, name, value, raising=False)
    for name in ABSENT_BY_DEFAULT:
        monkeypatch.delattr(module, name, raising=False)
    fake.bind_clock()
    return fake


def tick(fake: Fake, n: int, dt: float = 0.1):
    """Run the registered slate post-tick callbacks n times; each tick advances the clock by dt and writes the
    delayed files (screenshots, CSV) that fell due. Also binds spike_runner._now to the fake clock."""
    fake.bind_clock()
    for _ in range(int(n)):
        for handle, callback in list(fake.callbacks.items()):
            if handle in fake.callbacks:
                callback(dt)
        fake.clock += dt
        fake.flush_files()
