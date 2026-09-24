"""Create the movement test level /Game/Golmok/Maps/L_Dev.

Run inside the editor (Output Log, "Python" mode):
    import golmok.setup_dev_level as s; s.run()
    import golmok.setup_dev_level as s; s.run(overwrite=True)   # rebuild

The level contains lighting (sun, sky, fog, Lumen-friendly), a 200 m floor and a test course sized
like a Seoul alley: two walls 5 m apart, a 15 cm curb, a flight of stairs (17 cm risers), a ramp and
a low wall to jump on. Units are centimeters.
"""

import unreal

MAP_PATH = "/Game/Golmok/Maps/L_Dev"
CUBE = "/Engine/BasicShapes/Cube.Cube"  # 100 cm cube, pivot at center
PLANE = "/Engine/BasicShapes/Plane.Plane"  # 100x100 cm plane
GRID_MATERIAL = "/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial"


def _actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def _spawn_mesh(mesh_path, label, location, scale, rotation=None, folder="Course"):
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    actor = _actors().spawn_actor_from_object(mesh, location, rotation or unreal.Rotator(0, 0, 0))
    actor.set_actor_scale3d(scale)
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    material = unreal.EditorAssetLibrary.load_asset(GRID_MATERIAL)
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if material and component:
        component.set_material(0, material)
    return actor


def _box(label, center_cm, size_cm, yaw=0.0, folder="Course"):
    """Cube actor with the given center and size (x, y, z) in cm."""
    return _spawn_mesh(
        CUBE,
        label,
        unreal.Vector(*center_cm),
        unreal.Vector(size_cm[0] / 100.0, size_cm[1] / 100.0, size_cm[2] / 100.0),
        unreal.Rotator(0, 0, yaw),
        folder,
    )


def _spawn(cls, label, location=unreal.Vector(0, 0, 0), rotation=unreal.Rotator(0, 0, 0), folder="Lighting"):
    actor = _actors().spawn_actor_from_class(cls, location, rotation)
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    return actor


def _build_lighting():
    # Rotator(roll, pitch, yaw): late-morning sun, 40 degrees above the horizon.
    sun = _spawn(unreal.DirectionalLight, "Sun", unreal.Vector(0, 0, 1000), unreal.Rotator(0, -40, 35))
    sun_comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sun_comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun_comp.set_editor_property("atmosphere_sun_light", True)
    sun_comp.set_intensity(10.0)
    # Tag GolmokLighting: lighting.py / AGolmokTimeOfDay drive the tagged actors first (WP-05).
    sun.set_editor_property("tags", [unreal.Name("GolmokLighting")])

    _spawn(unreal.SkyAtmosphere, "SkyAtmosphere")

    sky = _spawn(unreal.SkyLight, "SkyLight", unreal.Vector(0, 0, 500))
    sky_comp = sky.get_component_by_class(unreal.SkyLightComponent)
    sky_comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky_comp.set_editor_property("real_time_capture", True)
    sky.set_editor_property("tags", [unreal.Name("GolmokLighting")])

    fog = _spawn(unreal.ExponentialHeightFog, "HeightFog")
    fog.set_editor_property("tags", [unreal.Name("GolmokLighting")])

    ppv = _spawn(unreal.PostProcessVolume, "PostProcess")
    ppv.set_editor_property("unbound", True)
    ppv.set_editor_property("tags", [unreal.Name("GolmokLighting")])


def _build_course():
    _spawn_mesh(PLANE, "Floor", unreal.Vector(0, 0, 0), unreal.Vector(200, 200, 1))

    # Alley: 5 m wide, 40 m long, walls 8 m high, running along +X.
    _box("AlleyWall_L", (2000, -300, 400), (4000, 100, 800))
    _box("AlleyWall_R", (2000, 300, 400), (4000, 100, 800))
    _box("Curb", (2000, -200, 7.5), (4000, 60, 15))

    # Stairs: 10 steps, 17 cm risers, 30 cm treads, 2 m wide, going up along +X at y = -1500.
    for i in range(10):
        height = 17.0 * (i + 1)
        _box(f"Stair_{i:02d}", (500 + 30 * i + 15, -1500, height / 2), (30, 200, height), folder="Course/Stairs")
    _box("StairLanding", (500 + 300 + 150, -1500, 85), (300, 200, 170), folder="Course/Stairs")

    # Ramp: 12 degrees, 6 m long, at y = -2200.
    ramp = _box("Ramp", (800, -2200, 62), (600, 200, 20))
    ramp.set_actor_rotation(unreal.Rotator(0, 12, 0), False)

    # Low wall (60 cm) to test jumping, and a 1 m box that should block.
    _box("LowWall_60cm", (0, 800, 30), (40, 300, 60))
    _box("Block_100cm", (0, 1300, 50), (100, 100, 100))

    _spawn(unreal.PlayerStart, "PlayerStart", unreal.Vector(-500, 0, 120), folder="")


def run(overwrite=False):
    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        if not overwrite:
            unreal.log_warning(f"{MAP_PATH} already exists; loading it. Use run(overwrite=True) to rebuild.")
            level_editor.load_level(MAP_PATH)
            return
        unreal.EditorAssetLibrary.delete_asset(MAP_PATH)

    if not level_editor.new_level(MAP_PATH):
        unreal.log_error(f"Could not create {MAP_PATH}")
        return

    _build_lighting()
    _build_course()
    level_editor.save_current_level()
    unreal.log(f"Created {MAP_PATH}. Press Play (Alt+P) to walk: WASD, mouse, Space, hold Shift to run.")
