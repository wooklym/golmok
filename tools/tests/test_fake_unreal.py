"""tools/tests/fake_unreal.py checked against the generated synthetic zone (design §5-0).

Every test installs the fake into the shared stub `unreal` for its own duration and drives it the way the
editor modules do (AssetImportTask -> AssetToolsHelpers, execute_console_command, slate ticks); the last two
tests run the real synthetic_zone / basemap_import / materials / viewpoints code on it.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import time
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("scipy")
pytest.importorskip("fast_simplification")

import fake_unreal  # noqa: E402
from fake_unreal import DEFAULT_LEVEL, ZONE_ROOT_CM  # noqa: E402
from golmok import _pure as pure  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "make_synthetic_zone.py"
ZONE = "z_synthetic_scan_001"
FOLDER = f"/Game/Golmok/Zones/{ZONE}/v1"
IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
MISSING = object()


@pytest.fixture(scope="module")
def zone(tmp_path_factory):
    """One generated synthetic zone (with the interior room) shared by the module."""
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        msz = importlib.import_module("make_synthetic_zone")
    finally:
        sys.path.remove(str(SCRIPT.parent))
    out = tmp_path_factory.mktemp("fake unreal zone")
    assert msz.main(["--out", str(out), "--interior", "--quiet"]) == 0
    return SimpleNamespace(
        version=out / "zones" / ZONE / "v1",
        tex=out / "recon" / ZONE / "tex",
        room_tex=out / "recon" / f"{ZONE}_room" / "tex",
    )


@pytest.fixture
def fake(monkeypatch, tmp_path):
    return fake_unreal.install(monkeypatch, tmp_path)


@pytest.fixture
def unreal(fake):
    return fake.module


def _import(unreal, path, dest, name=None, factory=None, options=None, replace=True):
    """AssetImportTask the way zone_import._import_task builds it; returns imported_object_paths."""
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(path))
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", replace)
    task.set_editor_property("save", False)
    if name:
        task.set_editor_property("destination_name", name)
    if factory is not None:
        task.set_editor_property("factory", factory)
    if options is not None:
        task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return task.get_editor_property("imported_object_paths")


def _box(mesh):
    box = mesh.get_bounding_box()
    return (box.min.x, box.min.y, box.min.z), (box.max.x, box.max.y, box.max.z)


def test_install_sets_names_and_restores_them(tmp_path):
    module = sys.modules.setdefault("unreal", types.ModuleType("unreal"))
    watched = ("StaticMesh", "GolmokZone", "log", "EditorLevelLibrary", "get_editor_subsystem")
    before = {n: getattr(module, n, MISSING) for n in watched}
    with pytest.MonkeyPatch.context() as mp:
        fake = fake_unreal.install(mp, tmp_path)
        assert (
            module.StaticMesh is fake_unreal.FakeStaticMesh and module.GolmokZone is fake_unreal.FakeZoneActor
        )
        assert module.get_editor_subsystem(module.LevelEditorSubsystem) is fake.level_editor
        assert module.get_editor_subsystem(module.EditorActorSubsystem) is fake.actor_subsystem
        assert module.get_editor_subsystem(module.StaticMeshEditorSubsystem) is fake.static_mesh_editor
        with pytest.raises(RuntimeError):
            module.get_editor_subsystem(object)
        assert not hasattr(module, "EditorLevelLibrary") and not hasattr(module, "CesiumGeoreference")
        assert module.Paths.project_saved_dir() == tmp_path.as_posix() + "/Saved/"
        assert (
            Path(fake.saved_dir).is_dir()
            and Path(fake.content_dir).is_dir()
            and Path(fake.config_dir).is_dir()
        )
        assert module.SystemLibrary.get_engine_version() == "5.8.3-fake"
        module.log("a")
        module.log_warning("b")
        module.log_error("c")
        assert fake.logs == [("log", "a"), ("warning", "b"), ("error", "c")] and fake.logged("error") == ["c"]
        assert fake.current_level == DEFAULT_LEVEL and module.EditorAssetLibrary.does_asset_exist(
            DEFAULT_LEVEL
        )
        assert module.get_default_object(module.LevelEditorPlaySettings) is fake.play_settings
        with pytest.raises(TypeError):
            fake_unreal.install(mp, tmp_path, no_such_knob=1)
        mp.delattr(module.SystemLibrary, "get_engine_version")  # hasattr branches remove static methods
        assert not hasattr(module.SystemLibrary, "get_engine_version")
        assert module.EditorAssetLibrary.load_asset("/Game/Nope") is None  # other methods keep working
    assert {n: getattr(module, n, MISSING) for n in watched} == before


def test_obj_import_maps_bounds_and_slots(fake, unreal, zone):
    obj = zone.version / "visual" / "c_e000_n000.obj"
    ui = unreal.FbxImportUI()
    ui.set_editor_property("is_obj_import", True)
    ui.set_editor_property("import_materials", False)
    ui.get_editor_property("static_mesh_import_data").set_editor_property("build_nanite", True)
    paths = _import(unreal, obj, FOLDER, "SM_c_e000_n000", factory=unreal.FbxFactory(), options=ui)
    assert paths[0] == f"{FOLDER}/SM_c_e000_n000.SM_c_e000_n000"
    assert fake.calls == [("import", "c_e000_n000.obj", FOLDER, "SM_c_e000_n000", "fbx")]
    mesh = unreal.EditorAssetLibrary.load_asset(paths[0])
    assert isinstance(mesh, unreal.StaticMesh) and mesh is unreal.EditorAssetLibrary.load_asset(
        f"{FOLDER}/SM_c_e000_n000"
    )
    # bbox_enu [[0, 0, 0], [15, 15, 6]] (expected.json) read as Y-up: 100 * M_OBJ = (x, z, -y) cm
    expected = json.loads((zone.version / "expected.json").read_text("utf-8"))["chunks"]["c_e000_n000"]
    assert expected["bbox_enu"] == [[0.0, 0.0, 0.0], [15.0, 15.0, 6.0]]
    assert _box(mesh) == ((0.0, 0.0, -1500.0), (1500.0, 600.0, 0.0))
    slots = [
        str(sm.get_editor_property("material_slot_name"))
        for sm in mesh.get_editor_property("static_materials")
    ]
    assert slots == ["ground", "facade"]  # usemtl order of the chunk OBJ
    assert mesh.get_material_index("facade") == 1 and mesh.get_material_index("nope") == -1
    # importer by-products: one Material per usemtl next to the mesh, also in imported_object_paths
    assert sorted(paths[1:]) == [f"{FOLDER}/facade.facade", f"{FOLDER}/ground.ground"]
    assert isinstance(unreal.EditorAssetLibrary.load_asset(f"{FOLDER}/facade"), unreal.Material)
    assert mesh.get_material(0).path == f"{FOLDER}/ground"
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mi = tools.create_asset("MI_facade", f"{FOLDER}/Materials", unreal.MaterialInstanceConstant, None)
    mesh.set_material(1, mi)
    assert fake.calls[-1] == ("set_material", f"{FOLDER}/SM_c_e000_n000", 1, f"{FOLDER}/Materials/MI_facade")
    assert mesh.get_material(1) is mi
    with pytest.raises(IndexError):
        mesh.set_material(2, mi)
    # knobs: generic slot names, no by-products, another mapping, a bounds offset
    fake.slot_names_from_usemtl = False
    fake.importer_makes_materials = False
    fake.obj_mapping = (1.0, IDENTITY)
    fake.bounds_offset["c_e000_n000.obj"] = (50.0, 0.0, 0.0)
    paths = _import(unreal, obj, FOLDER, "SM_c_e000_n000", factory=unreal.FbxFactory(), options=ui)
    mesh = unreal.EditorAssetLibrary.load_asset(paths[0])
    assert len(paths) == 1 and mesh.slots == ["Material_0", "Material_1"]
    assert _box(mesh) == ((50.0, 0.0, 0.0), (65.0, 15.0, 6.0))


def test_glb_import_uses_gltf_axes_and_mesh_name(fake, unreal, zone):
    glb = zone.version / "collision" / "c_e000_n000.glb"
    paths = _import(unreal, glb, FOLDER)
    assert paths == [f"{FOLDER}/collision_c_e000_n000.collision_c_e000_n000"]  # the glTF mesh name
    assert fake.calls == [("import", "c_e000_n000.glb", FOLDER, None, None)]
    mesh = unreal.EditorAssetLibrary.load_asset(paths[0])
    # glTF (E, U, -N) of bbox_enu [[0, 0, 0], [15, 15, 6]] -> M_GLB (x, -z, y) -> (E, N, U) * 100
    assert _box(mesh) == ((0.0, 0.0, 0.0), (1500.0, 1500.0, 600.0))
    assert mesh.slots == ["collision_c_e000_n000_mat"] and mesh.get_material(0) is None
    paths = _import(unreal, glb, FOLDER, "SM_collision")
    assert paths == [f"{FOLDER}/SM_collision.SM_collision"]
    fake.glb_mapping = (1.0, IDENTITY)
    paths = _import(unreal, glb, FOLDER, "SM_raw")
    assert _box(unreal.EditorAssetLibrary.load_asset(paths[0])) == ((0.0, 0.0, -15.0), (15.0, 6.0, 0.0))


def test_png_import_udim_merge_and_single(fake, unreal, zone):
    textures = f"{FOLDER}/Textures"
    paths = _import(unreal, zone.tex / "facade.1001.png", textures, "T_facade")
    tex = unreal.EditorAssetLibrary.load_asset(paths[0])
    assert paths == [f"{textures}/T_facade.T_facade"] and isinstance(tex, unreal.Texture2D)
    assert (tex.blueprint_get_size_x(), tex.blueprint_get_size_y()) == (512, 512)  # 2 x 2 blocks of 256
    assert tex.tiles == [1001, 1002, 1011]
    assert (
        tex.get_editor_property("virtual_texture_streaming") is True
        and tex.get_editor_property("srgb") is True
    )
    ground = unreal.EditorAssetLibrary.load_asset(_import(unreal, zone.tex / "ground.png", textures)[0])
    assert ground.path == f"{textures}/ground" and ground.size == (256, 256) and ground.tiles == []
    room = unreal.EditorAssetLibrary.load_asset(_import(unreal, zone.room_tex / "room.1001.png", textures)[0])
    assert room.path == f"{textures}/room" and room.size == (256, 256) and room.tiles == []
    fake.udim_merge = False
    single = unreal.EditorAssetLibrary.load_asset(_import(unreal, zone.tex / "facade.1001.png", textures)[0])
    assert single.path == f"{textures}/facade_1001" and single.size == (256, 256)
    fake.texture_vt_default = False
    plain = unreal.EditorAssetLibrary.load_asset(
        _import(unreal, zone.tex / "ground.png", textures, "T_ground")[0]
    )
    assert plain.get_editor_property("virtual_texture_streaming") is False
    plain.set_editor_property("virtual_texture_streaming", True)
    assert plain.get_editor_property("virtual_texture_streaming") is True
    fake.vt_settable = False
    plain.set_editor_property("virtual_texture_streaming", False)
    assert plain.get_editor_property("virtual_texture_streaming") is True  # the editor refused
    # UDIM fallback: tiles imported one by one, packed with block coordinates
    tiles = [
        unreal.EditorAssetLibrary.load_asset(
            _import(unreal, zone.tex / f"facade.{t}.png", f"{textures}/_tiles")[0]
        )
        for t in (1001, 1002, 1011)
    ]
    assert [t.path for t in tiles] == [f"{textures}/_tiles/facade_{n}" for n in (1001, 1002, 1011)]
    coords = [unreal.IntPoint(*pure.udim_block_coords(t)) for t in (1001, 1002, 1011)]
    packed = unreal.UDIMTextureFunctionLibrary.make_udim_virtual_texture_from_texture2_ds(
        f"{textures}/T_packed", tiles, coords, keep_existing_settings=False, check_out_and_save=True
    )
    assert packed is unreal.EditorAssetLibrary.load_asset(f"{textures}/T_packed")
    assert packed.size == (512, 512) and packed.tiles == [1001, 1002, 1011]
    assert packed.get_editor_property("virtual_texture_streaming") is True
    assert fake.calls[-1] == ("make_udim", f"{textures}/T_packed", [(0, 0), (1, 0), (0, 1)])


def test_obj_route_detection_and_ladder(fake, unreal, zone):
    obj = zone.version / "visual" / "c_w001_n000.obj"
    fake.importer_makes_materials = False

    def attempt(**kw):
        paths = _import(unreal, obj, FOLDER, "SM_c_w001_n000", **kw)
        return fake.calls[-1][4], len(paths)

    assert attempt(factory=unreal.FbxFactory(), options=unreal.FbxImportUI()) == ("fbx", 1)
    assert attempt(factory=unreal.FbxFactory()) == ("fbx", 1)  # FbxImportUI missing: the factory decides
    assert attempt(options=unreal.InterchangeGenericAssetsPipeline()) == ("interchange", 1)
    assert attempt(options=unreal.FbxImportUI()) == (
        "auto",
        0,
    )  # neither factory nor flag: not a ladder route
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "Interchange.FeatureFlags.Import.OBJ 0")
    assert fake.legacy_flag and ("console", "Interchange.FeatureFlags.Import.OBJ 0") in fake.calls
    assert attempt(options=unreal.FbxImportUI()) == ("legacy_flag", 1)
    assert attempt(factory=unreal.FbxFactory(), options=unreal.FbxImportUI()) == ("fbx", 1)
    fake.obj_routes_ok = {"interchange"}
    assert attempt(factory=unreal.FbxFactory(), options=unreal.FbxImportUI()) == ("fbx", 0)
    assert attempt(options=unreal.FbxImportUI()) == ("legacy_flag", 0)
    assert attempt(options=unreal.InterchangeGenericAssetsPipeline()) == ("interchange", 1)
    fake.fail_import = {"c_w001_n000.obj"}
    assert attempt(options=unreal.InterchangeGenericAssetsPipeline()) == ("interchange", 0)
    assert _import(unreal, obj.with_name("missing.obj"), FOLDER, factory=unreal.FbxFactory()) == []
    assert all(t.replace_existing and t.automated and not t.save for t in fake.tasks)
    # option objects carry the citations.md property names and nothing else
    pipeline = unreal.InterchangeGenericAssetsPipeline()
    pipeline.material_pipeline.texture_pipeline.import_udi_ms = True
    pipeline.material_pipeline.set_editor_property("import_materials", False)
    pipeline.mesh_pipeline.build_nanite = True
    pipeline.common_meshes_properties.force_all_mesh_as_type = (
        unreal.InterchangeForceMeshType.IFMT_STATIC_MESH
    )
    assert pipeline.material_pipeline.get_editor_property("texture_pipeline").import_udi_ms is True
    with pytest.raises(AttributeError):
        pipeline.material_pipeline.texture_pipeline.import_udims = True
    with pytest.raises(AttributeError):
        unreal.AssetImportTask().set_editor_property("destinationName", "x")
    with pytest.raises(AttributeError):
        unreal.FbxImportUI().get_editor_property("import_udi_ms")


def test_screenshot_files_appear_after_tick(fake, unreal, tmp_path):
    system = unreal.SystemLibrary
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    system.execute_console_command(editor.get_editor_world(), "golmok.screenshot a far_01")  # no PIE
    assert fake.logged("error") == ["golmok.screenshot: ERROR no game viewport (PIE is not running)"]
    assert not fake.pending_files
    level_editor.editor_request_begin_play()
    pie = editor.get_game_world()
    system.execute_console_command(pie, "golmok.tod clear_noon")
    system.execute_console_command(pie, "golmok.hud 0")
    assert fake.preset == "clear_noon" and fake.hud is False
    system.execute_console_command(pie, "golmok.screenshot a far_01")
    path = Path(pure.screenshot_path(fake.saved_dir, "a", "clear_noon", "far_01"))
    fake_unreal.tick(fake, 2)  # 0.2 s of fake time < screenshot_delay_s
    assert not path.exists()
    fake_unreal.tick(fake, 2)
    assert path.exists() and fake.clock == pytest.approx(0.4)
    assert pure.png_size(path.read_bytes()[:24]) == (2560, 1440)  # PIE window 1280 x 720 x multiplier 2
    settings = unreal.get_default_object(unreal.LevelEditorPlaySettings)
    settings.set_editor_property("new_window_width", 640)
    settings.set_editor_property("new_window_height", 360)
    settings.set_editor_property(
        "last_executed_play_mode_type", unreal.PlayModeType.PLAY_MODE_TYPE_PLAY_IN_EDITOR_FLOATING
    )
    assert fake.calls_of("play_settings") == [("play_settings", 640, 360)]  # one record for the pair
    fake.screenshot_fallback_name = True
    system.execute_console_command(pie, "golmok.screenshot b near_03")
    fake_unreal.tick(fake, 4)
    fallback = Path(
        pure.screenshot_fallback_path(pure.screenshot_path(fake.saved_dir, "b", "clear_noon", "near_03"))
    )
    assert fallback.name == "near_0300000.png" and fallback.exists()
    assert pure.png_size(fallback.read_bytes()[:24]) == (1280, 720)
    system.execute_console_command(pie, "golmok.screenshot a,b x")
    assert fake.logged("error")[-1].startswith("golmok.screenshot: ERROR usage")
    assert fake.calls_of("console") == [
        ("console", "golmok.screenshot a far_01"),
        ("console", "golmok.tod clear_noon"),
        ("console", "golmok.hud 0"),
        ("console", "golmok.screenshot a far_01"),
        ("console", "golmok.screenshot b near_03"),
        ("console", "golmok.screenshot a,b x"),
    ]
    # the attended editor path (viewpoints.py) goes through AutomationLibrary and needs no PIE
    level_editor.editor_request_end_play()
    shot = tmp_path / "editor" / "shot.png"
    unreal.AutomationLibrary.take_high_res_screenshot(2560, 1440, str(shot))
    assert fake.calls[-1] == ("high_res_screenshot", str(shot))
    fake_unreal.tick(fake, 4)
    assert pure.png_size(shot.read_bytes()[:24]) == (2560, 1440)


def test_path_play_and_csv(fake, unreal):
    system = unreal.SystemLibrary
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    system.execute_console_command(world, "golmok.path play vp_far_01")
    assert (
        fake.logged("error")[-1].startswith("golmok.path play: ERROR no path file") and fake.playing is None
    )
    paths_dir = Path(fake.saved_dir) / "Golmok" / "Paths"
    paths_dir.mkdir(parents=True)
    dwell = pure.dwell_path_json(
        "vp_far_01", "L_ZoneTest", (1.0, 2.0, 3.0), (0.0, -10.0, 90.0), created="2026-09-24"
    )
    (paths_dir / "vp_far_01.json").write_text(dwell, encoding="utf-8")
    system.execute_console_command(world, "golmok.path play vp_far_01")
    assert fake.playing == "vp_far_01" and not fake.pending_files
    system.execute_console_command(world, "golmok.path stopplay")
    assert fake.playing is None
    system.execute_console_command(world, "golmok.path stopplay")
    assert fake.logs[-1] == ("log", "golmok.path stopplay: ERROR not playing")
    walk = {
        "version": 1,
        "samples": [{"t": 0, "p": [0, 0, 0], "r": [0, 0, 0]}, {"t": 5, "p": [1, 0, 0], "r": [0, 0, 0]}],
    }
    (paths_dir / "walk_01.json").write_text(json.dumps(walk), encoding="utf-8")
    system.execute_console_command(world, "golmok.path play walk_01 --csv")
    csv = Path(fake.saved_dir) / "Profiling" / "CSV" / "Profile(1).csv"
    fake_unreal.tick(fake, 4)  # 0.4 s < csv_delay_s
    assert not csv.exists()
    fake_unreal.tick(fake, 1)
    assert csv.exists() and fake.logs[-1] == ("log", f"GolmokDebugSubsystem: csv: {csv}")
    sample = {"t": 1, "p": [0, 0, 0], "r": [0, 0, 0]}
    back = json.dumps({"version": 1, "samples": [sample, {**sample, "t": 0}]})
    for name, text, problem in (
        ("v2", json.dumps({"version": 2, "samples": [sample]}), "version must be 1"),
        ("back", back, "samples[].t must be monotonic"),
        ("empty", '{"version": 1, "samples": []}', "no samples"),
        ("junk", "{", "invalid JSON"),
    ):
        (paths_dir / f"{name}.json").write_text(text, encoding="utf-8")
        system.execute_console_command(world, f"golmok.path play {name} --csv")
        assert fake.logged("error")[-1].startswith(f"golmok.path play: ERROR {problem}")
    assert fake.csv_count == 1


def test_pie_begin_end_and_worlds(fake, unreal):
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    statics = unreal.GameplayStatics
    zone = fake.add_actor("GolmokZone", "Zone_z_x", zone_id="z_x")
    spike = fake.add_actor(unreal.Actor, "Spike_b_lcc")
    assert editor.get_game_world() is None and level_editor.is_in_play_in_editor() is False
    assert statics.get_player_controller(editor.get_editor_world(), 0) is None
    level_editor.editor_request_begin_play()
    assert fake.pie and level_editor.is_in_play_in_editor()
    pie = editor.get_game_world()
    assert pie.kind == "pie" and pie.get_name() == "L_ZoneTest"
    assert pie.get_path_name() == f"{DEFAULT_LEVEL}.L_ZoneTest" == editor.get_editor_world().get_path_name()
    assert statics.get_player_controller(pie, 0) is not None
    assert statics.get_all_actors_of_class(pie, unreal.GolmokZone) == [zone]
    assert statics.get_all_actors_of_class(pie, unreal.Actor) == [zone, spike]
    level_editor.editor_request_end_play()
    assert not fake.pie and editor.get_game_world() is None
    assert fake.calls == [("begin_play",), ("end_play",)]
    fake.begin_play_starts_pie = False
    level_editor.editor_request_begin_play()
    assert not fake.pie and fake.calls[-1] == ("begin_play",)


def test_registry_replace_rename_delete_list(fake, unreal, zone):
    library = unreal.EditorAssetLibrary
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    obj = zone.version / "visual" / "c_w001_n000.obj"
    fake.importer_makes_materials = False
    first = _import(unreal, obj, FOLDER, "SM_c_w001_n000", factory=unreal.FbxFactory())
    assert _import(unreal, obj, FOLDER, "SM_c_w001_n000", factory=unreal.FbxFactory()) == first
    assert set(fake.registry) == {DEFAULT_LEVEL, f"{FOLDER}/SM_c_w001_n000"}
    third = _import(unreal, obj, FOLDER, "SM_c_w001_n000", factory=unreal.FbxFactory(), replace=False)
    assert third == [f"{FOLDER}/SM_c_w001_n000_2.SM_c_w001_n000_2"]
    assert library.does_asset_exist(first[0]) and library.does_asset_exist(f"{FOLDER}/SM_c_w001_n000")
    assert library.rename_asset(f"{FOLDER}/SM_c_w001_n000_2", f"{FOLDER}/Textures/T_moved")
    assert fake.calls[-1] == ("rename", f"{FOLDER}/SM_c_w001_n000_2", f"{FOLDER}/Textures/T_moved")
    moved = library.load_asset(f"{FOLDER}/Textures/T_moved")
    assert moved.get_path_name() == f"{FOLDER}/Textures/T_moved.T_moved" and moved.get_name() == "T_moved"
    assert not library.does_asset_exist(f"{FOLDER}/SM_c_w001_n000_2")
    assert not library.rename_asset(f"{FOLDER}/nope", f"{FOLDER}/nope2")
    assert library.list_assets(FOLDER, recursive=True, include_folder=False) == [
        f"{FOLDER}/SM_c_w001_n000.SM_c_w001_n000",
        f"{FOLDER}/Textures/T_moved.T_moved",
    ]
    assert library.list_assets(FOLDER, recursive=False) == [f"{FOLDER}/SM_c_w001_n000.SM_c_w001_n000"]
    assert library.list_assets(FOLDER, recursive=False, include_folder=True)[-1] == f"{FOLDER}/Textures/"
    assert library.does_directory_exist(f"{FOLDER}/Textures") and not library.does_directory_exist(
        "/Game/Nope"
    )
    material = tools.create_asset(
        "M_ZoneScan", "/Game/Golmok/Materials", unreal.Material, unreal.MaterialFactoryNew()
    )
    assert (
        isinstance(material, unreal.Material)
        and library.load_asset("/Game/Golmok/Materials/M_ZoneScan") is material
    )
    assert fake.calls[-1] == ("create_asset", "M_ZoneScan", "/Game/Golmok/Materials", "Material")
    library.save_loaded_asset(material)
    assert fake.calls[-1] == ("save", "/Game/Golmok/Materials/M_ZoneScan")
    assert library.delete_asset(f"{FOLDER}/Textures/T_moved") and not library.delete_asset(
        f"{FOLDER}/Textures/T_moved"
    )
    assert fake.calls[-1] == ("delete_asset", f"{FOLDER}/Textures/T_moved")
    assert library.delete_directory(FOLDER) and fake.calls[-1] == ("delete_directory", FOLDER)
    assert set(fake.registry) == {DEFAULT_LEVEL, "/Game/Golmok/Materials/M_ZoneScan"}
    assert not library.does_directory_exist(FOLDER) and library.load_asset("/Game/Nope") is None


def test_actors_levels_and_slate(fake, unreal, monkeypatch):
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    zone = actors.spawn_actor_from_class(unreal.GolmokZone, unreal.Vector(0, 0, 0))
    assert isinstance(zone, unreal.GolmokZone) and isinstance(zone, unreal.Actor)
    assert fake.calls[-1][:2] == ("spawn", "GolmokZone")
    zone.set_actor_label("Zone_z_x")
    zone.set_editor_property("zone_id", "z_x")
    assert fake.calls[-1] == ("spawn", "GolmokZone", "Zone_z_x")  # the label lands in the spawn record
    assert zone.get_editor_property("zone_id") == "z_x" and zone.get_editor_property("auto_managed") is True
    with pytest.raises(TypeError):
        actors.spawn_actor_from_class(object, unreal.Vector(0, 0, 0))
    zone.rebuild_in_editor()
    t = zone.get_actor_transform()
    assert tuple(t.translation) == ZONE_ROOT_CM and t.rotation.rotator().yaw == 0.0
    assert tuple(t.transform_location(unreal.Vector(400.0, -340.0, 250.0))) == pytest.approx(
        (ZONE_ROOT_CM[0] + 400.0, ZONE_ROOT_CM[1] - 340.0, ZONE_ROOT_CM[2] + 250.0)
    )
    zone.set_visual_visible(False)
    zone.unload_in_editor()
    assert fake.calls[-3:] == [
        ("rebuild_in_editor", "z_x"),
        ("set_visual_visible", "z_x", False),
        ("unload_in_editor", "z_x"),
    ]
    light = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(1, 2, 3), unreal.Rotator(0, 0, 0))
    component = light.get_component_by_class(unreal.PointLightComponent)
    component.set_intensity(3000.0)
    component.set_editor_property("temperature", 3000.0)
    assert ("set_intensity", (3000.0,)) in component.calls and component.props["temperature"] == 3000.0
    light.set_editor_property("tags", [unreal.Name("GolmokInteriorSetup")])
    assert (
        unreal.Name("GolmokInteriorSetup") in light.get_editor_property("tags")
        and "GolmokInteriorSetup" in light.tags
    )
    light.set_actor_hidden_in_game(True)
    light.set_editor_property("hidden", False)
    light.set_is_temporarily_hidden_in_editor(True)
    assert fake.calls_of("hidden_in_game") == [
        ("hidden_in_game", light.label, True),
        ("hidden_in_game", light.label, False),
    ]
    assert fake.calls_of("hidden_in_editor") == [("hidden_in_editor", light.label, True)]
    assert actors.get_all_level_actors() == [zone, light]
    sublevel = "/Game/Golmok/Zones/z_x/v1/L_z_x"
    assert (
        level_editor.new_level(sublevel)
        and fake.current_level == sublevel
        and actors.get_all_level_actors() == []
    )
    assert fake.calls[-1] == ("new_level", sublevel) and isinstance(
        fake.registry[sublevel], fake_unreal.FakeLevel
    )
    prop = fake.add_actor(unreal.Actor, "Prop_chair")
    assert level_editor.save_current_level() and fake.calls[-1] == ("save_current_level",)
    assert level_editor.load_level(DEFAULT_LEVEL) and actors.get_all_level_actors() == [zone, light]
    assert not level_editor.load_level("/Game/Nope") and fake.current_level == DEFAULT_LEVEL
    assert actors.destroy_actor(light) and fake.calls[-1] == ("destroy", light.label)
    assert actors.get_all_level_actors() == [zone] and not actors.destroy_actor(light)
    assert fake.levels[sublevel] == [prop]
    duplicate = unreal.EditorAssetLibrary.duplicate_asset(DEFAULT_LEVEL, "/Game/Golmok/Maps/L_Spike_b")
    assert isinstance(duplicate, fake_unreal.FakeLevel) and fake.calls[-1] == (
        "duplicate_asset",
        DEFAULT_LEVEL,
        "/Game/Golmok/Maps/L_Spike_b",
    )
    copies = fake.levels["/Game/Golmok/Maps/L_Spike_b"]
    assert (
        [a.label for a in copies] == ["Zone_z_x"]
        and copies[0] is not zone
        and isinstance(copies[0], unreal.GolmokZone)
    )
    ticks = []
    handle = unreal.register_slate_post_tick_callback(ticks.append)
    spike_runner = types.ModuleType("golmok.spike_runner")  # tick() binds its _now to the fake clock
    spike_runner._now = time.monotonic
    monkeypatch.setitem(sys.modules, "golmok.spike_runner", spike_runner)
    fake_unreal.tick(fake, 3, 0.5)
    assert ticks == [0.5, 0.5, 0.5] and fake.now() == pytest.approx(1.5)
    assert spike_runner._now is fake.now and spike_runner._now() == pytest.approx(1.5)
    unreal.unregister_slate_post_tick_callback(handle)
    fake_unreal.tick(fake, 2)
    assert len(ticks) == 3 and fake.clock == pytest.approx(1.7)


def test_existing_editor_modules_run_on_the_fake(fake, unreal, zone, monkeypatch):
    sz = importlib.import_module("golmok.synthetic_zone")
    bm = importlib.import_module("golmok.basemap_import")
    materials = importlib.import_module("golmok.materials")
    first, again = sz.find_or_spawn_zone("z_x", 1), sz.find_or_spawn_zone("z_x", 1)
    assert first is again and fake.calls_of("spawn") == [("spawn", "GolmokZone", "Zone_z_x")]
    assert first.get_folder_path() == "Golmok/Zones" and first.get_editor_property("version") == 1
    geo = sz.find_or_spawn_geo_origin(37.56, 126.923, 40.0)
    assert isinstance(geo, unreal.GolmokGeoOrigin) and geo.get_editor_property("latitude") == 37.56
    assert sz.open_or_create_level(DEFAULT_LEVEL) is False and fake.calls[-1] == ("load_level", DEFAULT_LEVEL)
    assert sz._current_level_path() == DEFAULT_LEVEL
    mesh = bm._import_glb(str(zone.version / "collision" / "c_w001_n000.glb"), f"{FOLDER}/_probe")
    assert mesh.path == f"{FOLDER}/_probe/collision_c_w001_n000"
    # bbox_enu [[-15, 0, -0.3], [0, 15, 5]] through the default glTF mapping
    lo, hi = bm._mesh_bounds(mesh)  # float32 positions in the GLB: -0.3 m is not exactly -30 cm
    assert [*lo, *hi] == pytest.approx([-1500.0, 0.0, -30.0, 0.0, 1500.0, 500.0], abs=1e-3)
    err, scale, m = bm._measure_import_mapping([((lo, hi), ((-15.0, 0.0, -0.3), (0.0, 15.0, 5.0)))])
    # M_GLB acts on glTF axes; measured from ENU boxes the importer mapping is M_GLB * G = identity
    assert scale == pytest.approx(100.0, rel=1e-6) and m == IDENTITY and err == pytest.approx(0.0, abs=1e-3)
    bm._set_nanite(mesh, True)
    assert fake.calls[-1] == ("set_nanite", mesh.path, True) and mesh.nanite.enabled is True
    monkeypatch.delattr(unreal.StaticMeshEditorSubsystem, "set_nanite_settings")
    bm._set_nanite(mesh, False)  # property fallback path
    assert fake.calls[-1] == ("set_nanite", mesh.path, False) and mesh.nanite.enabled is False
    bm._complex_collision(mesh)
    assert mesh.body_setup.collision_trace_flag == unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
    material = materials.build_terrain_material()
    assert isinstance(material, unreal.Material) and material.props["used_with_nanite"] is True
    assert material.expressions[0].class_name == "MaterialExpressionTextureSampleParameter2D"
    assert material.expressions[0].props["parameter_name"] == "BaseColor"
    assert [c[0] for c in material.connections] == ["MP_BASE_COLOR", "MP_ROUGHNESS", "MP_SPECULAR"]
    assert ("recompile_material", (material,)) in fake.mel_calls
    texture = fake_unreal.FakeTexture2D(fake, f"{FOLDER}/Textures/T_x")
    fake.registry[texture.path] = texture
    instance = materials.terrain_instance(texture, material, f"{FOLDER}/Materials/MI_x")
    assert instance.parent is material and instance.texture_params["BaseColor"] is texture
    assert instance.get_editor_property("parent") is material and fake.calls[-1] == ("save", instance.path)
    assert instance is materials.terrain_instance(
        texture, material, f"{FOLDER}/Materials/MI_x"
    )  # updated, not recreated


def test_viewpoints_capture_runs_on_the_fake(fake, unreal):
    viewpoints = importlib.import_module("golmok.viewpoints")
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    editor.set_level_viewport_camera_info(unreal.Vector(1.0, 2.0, 3.0), unreal.Rotator(0.0, -10.0, 90.0))
    viewpoints.save("far_01")
    store = Path(fake.config_dir) / "Golmok" / "Viewpoints" / "L_ZoneTest.json"
    assert json.loads(store.read_text("utf-8")) == {
        "far_01": {"location": [1.0, 2.0, 3.0], "rotation": [0.0, -10.0, 90.0]}
    }
    capture = viewpoints.capture("a", names=["far_01"], presets=[None])
    assert capture is not None and len(fake.callbacks) == 1
    fake_unreal.tick(fake, 60)
    shot = Path(fake.saved_dir) / "Screenshots" / "Golmok" / "a" / "current" / "far_01.png"
    # os.path.join of the UE-style "/"-path gives mixed separators on Windows: compare normalized paths.
    assert [os.path.normpath(p) for p in capture.saved] == [os.path.normpath(shot)]
    assert capture.missing == [] and shot.exists()
    assert pure.png_size(shot.read_bytes()[:24]) == (viewpoints.RES_X, viewpoints.RES_Y)
    assert not fake.callbacks and fake.logs[-1] == (
        "log",
        f"Capture 'a' done: 1 saved, 0 missing -> {shot.parent.parent}",
    )
    shots = [(k, os.path.normpath(v)) for k, v in fake.calls_of("high_res_screenshot")]
    assert shots == [("high_res_screenshot", os.path.normpath(shot))]
