"""golmok/interior_setup.py on the scripted fake `unreal` (WP-06 design §5-4), generated synthetic zone.

The exterior zone is imported first with zone_import.run (the `parent` fixture), so the parent's Content
manifest and its Zone_<parent> actor exist the way they do on the PC (runbook §2 before §4); the interior
room zone (--interior) is then set up with interior_setup.run. Tests that break manifests copy the whole
generated tree into their own tmp_path.
"""

from __future__ import annotations

import copy
import importlib
import inspect
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("scipy")
pytest.importorskip("fast_simplification")

import fake_unreal  # noqa: E402
from fake_unreal import DEFAULT_LEVEL  # noqa: E402
from golmok import _pure as pure  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "scripts" / "make_synthetic_zone.py"
WP05_INTERIOR_MANIFEST = REPO / "unreal/Golmok/Content/Golmok/Zones/z_synthetic_001_interior/v1/manifest.json"
ZONE = "z_synthetic_scan_001"
ROOM = f"{ZONE}_room"
FOLDER = f"/Game/Golmok/Zones/{ZONE}/v1"
ROOM_FOLDER = f"/Game/Golmok/Zones/{ROOM}/v1"
SUBLEVEL = f"{ROOM_FOLDER}/L_{ROOM}"
LIGHT = f"Interior_Light_{ROOM}"
TAG = "GolmokInteriorSetup"
MATERIALS = "/Game/Golmok/Materials"
M_ZONE_SCAN = f"{MATERIALS}/M_ZoneScan"
PORTAL_LINE = "interior_setup: portal door_out<->door_1 same point (err 0.000 m), opposite yaw (err 0.0 deg)"
SUBLEVEL_LINE = f"interior_setup: sublevel {SUBLEVEL} actors=['{LIGHT}'] (level coordinates)"
RERUN_LINE = f"interior_setup: removed 1 GolmokInteriorSetup actors from {SUBLEVEL}"
PARENT_HINT = "run zone_import.run on the parent zone first"


# ---- fixtures ------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    """One generated synthetic zone (with the interior room) shared by the module, in a non-ASCII folder."""
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        msz = importlib.import_module("make_synthetic_zone")
    finally:
        sys.path.remove(str(SCRIPT.parent))
    out = tmp_path_factory.mktemp("합성 zone")
    assert msz.main(["--out", str(out), "--interior", "--quiet"]) == 0
    return out


def _view(out: Path) -> SimpleNamespace:
    version = out / "zones" / ZONE / "v1"
    room_version = out / "zones" / ROOM / "v1"
    return SimpleNamespace(
        out=out,
        dir=out / "zones" / ZONE,
        version=version,
        room=out / "zones" / ROOM,
        room_version=room_version,
        expected=json.loads((version / "expected.json").read_text("utf-8")),
        room_expected=json.loads((room_version / "expected.json").read_text("utf-8")),
    )


@pytest.fixture
def zone(generated) -> SimpleNamespace:
    """Read-only view of the generated zone."""
    return _view(generated)


@pytest.fixture
def zone_copy(generated, tmp_path) -> SimpleNamespace:
    """A private copy of the whole generated tree for tests that break files."""
    out = tmp_path / "zone copy"
    shutil.copytree(generated, out)
    return _view(out)


@pytest.fixture
def fake(monkeypatch, tmp_path):
    return fake_unreal.install(monkeypatch, tmp_path)


@pytest.fixture
def unreal(fake):
    return fake.module


@pytest.fixture
def zi(fake):
    return importlib.import_module("golmok.zone_import")


@pytest.fixture
def it(fake):
    return importlib.import_module("golmok.interior_setup")


@pytest.fixture
def sz(fake):
    return importlib.import_module("golmok.synthetic_zone")


@pytest.fixture
def parent(fake, zone, zi) -> dict:
    """The exterior zone imported into L_ZoneTest (runbook §2): Content manifest, Zone_<parent> actor and
    importer mapping cache exist; the records and logs of that run are dropped."""
    result = zi.run(str(zone.dir), level=DEFAULT_LEVEL, geo_origin="area")
    fake.calls.clear()
    fake.logs.clear()
    return result


# ---- helpers -------------------------------------------------------------------------------------------


def _run(it, zone, **kw):
    kw.setdefault("level", DEFAULT_LEVEL)
    return it.run(str(zone.room), **kw)


def _usemtl(version_dir: Path, cid: str) -> list[str]:
    return pure.usemtl_order((version_dir / "visual" / f"{cid}.obj").read_text("utf-8").splitlines())


def _expected_assets(expected: dict) -> set[str]:
    folder = expected["asset_folder"]
    out = {c["asset"] for c in expected["chunks"].values()}
    out |= {c["asset"] for c in expected["collision"]["chunks"].values()}
    out |= {f"{folder}/Textures/{name}" for name in expected["textures"]}
    out |= {f"{folder}/Materials/{name}" for name in expected["materials"]}
    assert all(a.startswith("/Game/") for a in out)
    return out


def _rewrite(path: Path, mutate) -> None:
    data = json.loads(path.read_text("utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _zone_labels(fake, unreal) -> list[str]:
    return [a.get_actor_label() for a in fake.actors if isinstance(a, unreal.GolmokZone)]


def _labels(actors) -> list[str]:
    return [a.get_actor_label() for a in actors]


# ---- contract --------------------------------------------------------------------------------------------


def test_run_signature_and_error_class(it, zi, sz):
    params = inspect.signature(it.run).parameters
    assert list(params) == [
        "zone_dir", "version", "level", "save", "register", "remeasure", "reimport_textures",
    ]  # fmt: skip
    assert [p.default for p in list(params.values())[1:]] == [None, None, True, False, False, True]
    e = it.InteriorSetupError("portal", "x")
    assert isinstance(e, zi.ZoneImportError) and isinstance(e, RuntimeError)
    assert str(e) == "interior_setup: ERROR portal: x" == pure.fmt("is.error", step="portal", message="x")
    assert (e.step, e.message) == ("portal", "x")
    # the synthetic_zone helpers interior_setup relies on (design §3-6, D18)
    assert list(inspect.signature(sz._spawn_interior_sublevel).parameters) == [
        "int_manifest", "zone_transform", "return_level", "specs", "delete_tag", "on_removed",
    ]  # fmt: skip
    register = inspect.signature(sz.register_interior_sublevel).parameters
    assert list(register) == ["zone_id", "version"]
    assert register["zone_id"].default == sz.INTERIOR_ZONE_ID
    assert register["version"].default == sz.INTERIOR_VERSION
    assert list(inspect.signature(sz.run).parameters) == [
        "geo_origin", "move_player_start", "import_assets", "level", "interior",
    ]  # fmt: skip


# ---- steps 1-4: no editor call -------------------------------------------------------------------------


def test_requires_interior_kind_and_parent_manifest(fake, zone, zone_copy, it, zi):
    with pytest.raises(it.InteriorSetupError) as info:
        it.run(str(zone.dir), level=DEFAULT_LEVEL)  # an exterior folder
    e = info.value
    assert e.step == "manifest"
    assert e.message == "kind must be interior (use zone_import.run for exterior zones)"
    assert str(e) == f"interior_setup: ERROR manifest: {e.message}" and isinstance(e, zi.ZoneImportError)
    assert fake.calls == [] and set(fake.registry) == {DEFAULT_LEVEL} and fake.logs == []
    # zone_import.run was never run on the parent in this editor: no Content manifest to check against
    with pytest.raises(it.InteriorSetupError) as info:
        it.run(str(zone.room), level=DEFAULT_LEVEL)
    assert info.value.step == "parent"
    assert str(info.value) == f"interior_setup: ERROR parent: no Content manifest for {ZONE}: {PARENT_HINT}"
    assert fake.calls == [] and fake.logs == []
    manifest = zone_copy.room_version / "manifest.json"
    _rewrite(manifest, lambda m: m.pop("parent_zone"))
    with pytest.raises(it.InteriorSetupError) as info:
        it.run(str(zone_copy.room))
    assert (info.value.step, info.value.message) == ("manifest", "parent_zone missing")
    _rewrite(manifest, lambda m: m.update(parent_zone="../z_x"))
    with pytest.raises(it.InteriorSetupError) as info:
        it.run(str(zone_copy.room))
    assert info.value.step == "manifest" and "parent_zone invalid" in info.value.message
    # folder problems read like zone_import's plan stage
    with pytest.raises(it.InteriorSetupError) as info:
        it.run(str(zone.out))
    assert info.value.step == "plan" and "no v<n> folder with manifest.json" in str(info.value)
    with pytest.raises(it.InteriorSetupError) as info:
        it.run(str(zone.room), version=2)
    assert info.value.step == "plan" and "version 2 requested" in str(info.value)
    assert fake.calls == [] and fake.logs == []


def test_portal_mismatch_aborts_before_editor(fake, parent, zone_copy, it):
    manifest = zone_copy.room_version / "manifest.json"
    original = manifest.read_text("utf-8")
    content_manifest = Path(fake.content_dir) / "Golmok" / "Zones" / ZONE / "v1" / "manifest.json"
    parent_original = content_manifest.read_text("utf-8")

    def case(path: Path, mutate, message: str):
        _rewrite(path, mutate)
        with pytest.raises(it.InteriorSetupError) as info:
            it.run(str(zone_copy.room), level=DEFAULT_LEVEL)
        assert info.value.step == "portal"
        assert str(info.value) == f"interior_setup: ERROR portal: {message}"
        assert fake.calls == [] and fake.logs == []  # no editor call, not even the portal line
        manifest.write_text(original, encoding="utf-8")
        content_manifest.write_text(parent_original, encoding="utf-8")

    def yaw(m):
        m["portals"][0]["pose_enu"]["yaw_deg"] = -80.0

    def shifted(m):
        m["portals"][0]["pose_enu"]["position"][0] += 1.0

    def no_portals(m):
        m["portals"] = []

    def no_transform(m):
        del m["transform"]

    def doubled(m):
        m["portals"].append(copy.deepcopy(m["portals"][0]))

    fix = "(fix the manifests before importing)"
    case(manifest, yaw, f"door_out vs door_1: 0.000 m apart, yaw error 10.0 deg {fix}")
    case(manifest, shifted, f"door_out vs door_1: 1.000 m apart, yaw error 0.0 deg {fix}")
    case(manifest, no_portals, f"{ROOM}: 0 portals lead to {ZONE} (expected exactly 1)")
    case(manifest, no_transform, "manifest key 'transform' missing")
    # the parent side is checked too: its Content manifest, the file C++ reads
    case(content_manifest, doubled, f"{ZONE}: 2 portals lead to {ROOM} (expected exactly 1)")
    assert fake.calls == [] and not [k for k in fake.registry if ROOM in k]


def test_plan_problem_after_portal_check(fake, parent, zone_copy, it):
    (zone_copy.room_version / "visual" / "c_e000_n000.obj").unlink()
    with pytest.raises(it.InteriorSetupError) as info:
        it.run(str(zone_copy.room), level=DEFAULT_LEVEL)
    e = info.value
    assert e.step == "plan" and "chunk c_e000_n000: file missing" in e.message
    assert str(e).startswith("interior_setup: ERROR plan:")
    assert fake.calls == []
    assert set(fake.registry) == _expected_assets(zone_copy.expected) | {DEFAULT_LEVEL, M_ZONE_SCAN}
    # the portal check runs before the plan; the plan line is never reached
    assert fake.logged("log") == [PORTAL_LINE]


# ---- the run -------------------------------------------------------------------------------------------


def test_run_sequence(fake, unreal, parent, zone, it):
    root = tuple(zone.room_expected["zone_root_ue_cm"])
    fake.zone_transform = fake_unreal.Transform(fake_unreal.Vector(*root))  # what rebuild_in_editor yields
    result = _run(it, zone)
    usemtl = _usemtl(zone.room_version, "c_e000_n000")
    assert usemtl == ["room"]
    mesh, collision = f"{ROOM_FOLDER}/SM_c_e000_n000", f"{ROOM_FOLDER}/SM_{ROOM}_collision_c_e000_n000"
    calls = [
        ("load_level", DEFAULT_LEVEL),
        # import_assets (importer mapping cache hit: no probe; M_ZoneScan exists: loaded, not created)
        ("import", "room.1001.png", f"{ROOM_FOLDER}/Textures", "T_room", None),
        ("save", f"{ROOM_FOLDER}/Textures/T_room"),
        ("create_asset", "MI_room", f"{ROOM_FOLDER}/Materials", "MaterialInstanceConstant"),
        ("save", f"{ROOM_FOLDER}/Materials/MI_room"),
        ("import", "SM_c_e000_n000.obj", ROOM_FOLDER, "SM_c_e000_n000", "fbx"),
        *[("delete_asset", f"{ROOM_FOLDER}/{m}") for m in usemtl],  # importer by-products
        ("set_nanite", mesh, True),
        *[("set_material", mesh, i, f"{ROOM_FOLDER}/Materials/MI_{m}") for i, m in enumerate(usemtl)],
        ("save", mesh),
        ("import", f"SM_{ROOM}_collision_c_e000_n000.glb", ROOM_FOLDER, collision.rsplit("/", 1)[1], None),
        ("set_nanite", collision, False),
        ("save", collision),
        # the interior zone actor: rebuilt as an editor check, then unloaded
        ("spawn", "GolmokZone", f"Zone_{ROOM}"),
        ("rebuild_in_editor", ROOM),
        ("unload_in_editor", ROOM),
        # the sublevel (synthetic_zone._spawn_interior_sublevel), then the reopened persistent level
        ("save_current_level",),
        ("new_level", SUBLEVEL),
        ("spawn", "PointLight", LIGHT),
        ("save_current_level",),
        ("load_level", DEFAULT_LEVEL),
        ("rebuild_in_editor", ZONE),
        ("save_current_level",),
    ]
    assert fake.calls == calls
    # the light: spec location through the zone transform (level coordinates), tagged, warm
    lights = fake.levels[SUBLEVEL]
    assert _labels(lights) == [LIGHT] and isinstance(lights[0], unreal.PointLight)
    light = lights[0]
    local = zone.room_expected["light"]["interior_local_cm"]
    assert zone.room_expected["light"]["label"] == LIGHT and local == [400.0, -340.0, 250.0]
    assert tuple(light.location) == pytest.approx(tuple(r + v for r, v in zip(root, local, strict=True)))
    assert light.tags == [TAG] and light.folder == "Golmok/Interior"
    assert ("set_intensity", (3000.0,)) in light.component.calls
    assert ("set_mobility", (unreal.ComponentMobility.MOVABLE,)) in light.component.calls
    assert light.component.props["temperature"] == 3000.0
    assert light.component.props["use_temperature"] is True
    assert light.component.props["intensity_units"] == unreal.LightUnits.CANDELAS
    # the persistent level is open again with both zone actors; the room's is a real AGolmokZone
    assert fake.current_level == DEFAULT_LEVEL
    assert _zone_labels(fake, unreal) == [f"Zone_{ZONE}", f"Zone_{ROOM}"]
    room_zone = next(a for a in fake.actors if a.get_actor_label() == f"Zone_{ROOM}")
    assert (room_zone.get_editor_property("zone_id"), room_zone.get_editor_property("version")) == (ROOM, 1)
    assert room_zone.get_folder_path() == "Golmok/Zones"
    assert set(fake.registry) == _expected_assets(zone.expected) | _expected_assets(zone.room_expected) | {
        DEFAULT_LEVEL,
        M_ZONE_SCAN,
        SUBLEVEL,
    }
    assert zone.room_expected["sublevel"] == SUBLEVEL
    for c in zone.room_expected["chunks"].values():
        got = fake.registry[c["asset"]].bounds
        assert [*got[0], *got[1]] == pytest.approx([*c["ue_bounds_cm"][0], *c["ue_bounds_cm"][1]], abs=0.01)
    assert fake.registry[mesh].get_material(0) is fake.registry[f"{ROOM_FOLDER}/Materials/MI_room"]
    assert fake.registry[f"{ROOM_FOLDER}/Materials/MI_room"].parent is fake.registry[M_ZONE_SCAN]
    dest = Path(fake.content_dir) / "Golmok" / "Zones" / ROOM / "v1"
    assert sorted(p.name for p in dest.iterdir()) == ["manifest.json"]
    # the result: zone_import's part plus the interior block, written next to the OBJ copies
    assert [a["kind"] for a in result["assets"]] == ["texture", "material", "chunk", "collision", "file"]
    assert result["route"] == "fbx" and result["warnings"] == [] and result["zone_id"] == ROOM
    interior = result["interior"]
    assert list(interior) == ["sublevel", "round_trip", "parent", "parent_version", "actors"]
    assert (interior["sublevel"], interior["parent"], interior["parent_version"]) == (SUBLEVEL, ZONE, 1)
    assert interior["actors"] == [LIGHT]
    trip = interior["round_trip"]
    assert (trip["parent_portal"], trip["interior_portal"], trip["ok"]) == ("door_1", "door_out", True)
    assert trip["dist_m"] == pytest.approx(0.0, abs=0.005)
    assert trip["yaw_err_deg"] == pytest.approx(0.0, abs=0.01)
    path = Path(fake.saved_dir) / "Golmok" / "zone_import" / ROOM / "v1" / "import_result.json"
    assert json.loads(path.read_text("utf-8")) == result
    assert fake.logged("warning") == []


def test_logs_match_runbook_and_log_source(fake, parent, zone, it):
    _run(it, zone)
    logs = fake.logged("log")
    cache = Path(fake.saved_dir) / "Golmok" / "zone_import" / "importer_mapping.json"
    dest = Path(fake.content_dir) / "Golmok" / "Zones" / ROOM / "v1"
    result_path = Path(fake.saved_dir) / "Golmok" / "zone_import" / ROOM / "v1" / "import_result.json"
    collision = f"{ROOM_FOLDER}/SM_{ROOM}_collision_c_e000_n000"
    expected = [  # docs/runbooks/pc-verify-wp06.md §4 (the LogGolmok lines come from C++)
        PORTAL_LINE,
        f"zone_import: plan {ROOM} v1: chunks=1 collision=1 (chunks) textures=1 materials=1 blockers=0",
        f"zone_import: importer mapping cache hit -> {cache}",
        f"zone_import: texture {ROOM_FOLDER}/Textures/T_room tiles=[1001] size=256x256 vt=on "
        "(single texture)",
        f"zone_import: material {ROOM_FOLDER}/Materials/MI_room parent={M_ZONE_SCAN} texture=T_room",
        f"zone_import: chunk {ROOM_FOLDER}/SM_c_e000_n000 tris=60 bounds ok (error 0.00 cm) "
        "slots=room=MI_room",
        f"zone_import: collision {collision} bounds ok (error 0.00 cm) complex-as-simple nanite=off",
        f"zone_import: copied manifest.json -> {dest}",
        SUBLEVEL_LINE,
        f"interior_setup: exterior zone Zone_{ZONE} rebuilt",
        f"interior_setup: done {ROOM} v1 -> {result_path}",
    ]
    positions = []
    for line in expected:
        assert line in logs, line
        positions.append(logs.index(line))
    assert positions == sorted(positions)  # in the runbook's order
    assert not [t for t in logs if t.startswith("interior_setup: removed")]  # a new sublevel: no re-run line
    assert fake.logged("warning") == [] and fake.logged("error") == []
    # every log line comes from _pure.LOG (runbook drift test), is a summary line, or is synthetic_zone's own
    prefixes = tuple(pure.log_prefixes().values())
    for text in logs:
        assert text.startswith(prefixes) or text.startswith(("  - ", "Created ", "synthetic_zone: ")), text
    assert [t for t in logs if t.startswith("synthetic_zone: ")] == [
        t for t in logs if t.startswith(f"synthetic_zone: sublevel actor {LIGHT} at ")
    ]


def test_sublevel_contains_only_allowed_classes(fake, unreal, parent, zone, it):
    _run(it, zone)
    start = fake.calls.index(("new_level", SUBLEVEL))
    end = fake.calls.index(("load_level", DEFAULT_LEVEL), start)
    assert [c[1] for c in fake.calls[start:end] if c[0] == "spawn"] == ["PointLight"]
    actors = fake.levels[SUBLEVEL]
    classes = {a.class_name for a in actors}
    assert classes == {"PointLight"} and not classes & set(pure.FORBIDDEN_SUBLEVEL_CLASSES)
    assert all(a.tags == [TAG] for a in actors)  # no GolmokLighting tag: not a preset target (design D10)
    assert isinstance(fake.registry[SUBLEVEL], fake_unreal.FakeLevel)
    assert fake.calls_of("add_level_to_world") == []  # LevelInstance path: not in the Levels list
    # the zone actors (and the L_Dev lighting) stay in the persistent level
    assert _zone_labels(fake, unreal) == [f"Zone_{ZONE}", f"Zone_{ROOM}"]
    assert not [a for a in fake.actors if a.class_name == "PointLight"]


def test_rerun_deletes_only_tagged_actors(fake, unreal, parent, zone, it):
    fake.registry[SUBLEVEL] = fake_unreal.FakeLevel(fake, SUBLEVEL)
    fake.add_actor("PointLight", "Interior_Light_x", tags=[TAG], level=SUBLEVEL)
    fake.add_actor("StaticMeshActor", "Prop_chair", level=SUBLEVEL)
    fake.add_actor("StaticMeshActor", "ManualProp", tags=["Other"], level=SUBLEVEL)
    _run(it, zone)
    assert ("load_level", SUBLEVEL) in fake.calls and ("new_level", SUBLEVEL) not in fake.calls
    assert fake.calls_of("destroy") == [("destroy", "Interior_Light_x")]
    logs = fake.logged("log")
    assert logs.index(RERUN_LINE) < logs.index(SUBLEVEL_LINE)
    assert _labels(fake.levels[SUBLEVEL]) == ["Prop_chair", "ManualProp", LIGHT]
    # a real second run (runbook §6) replaces the light it made and nothing else; assets are overwritten
    fake.calls.clear()
    fake.logs.clear()
    count = len(fake.registry)
    _run(it, zone, level=None)  # the level is already open
    assert fake.calls[0][0] == "import"
    assert fake.calls_of("load_level") == [("load_level", SUBLEVEL), ("load_level", DEFAULT_LEVEL)]
    assert fake.calls_of("destroy") == [("destroy", LIGHT)] and RERUN_LINE in fake.logged("log")
    assert fake.calls_of("spawn") == [("spawn", "PointLight", LIGHT)]  # both zone actors found, not respawned
    assert _labels(fake.levels[SUBLEVEL]) == ["Prop_chair", "ManualProp", LIGHT]
    assert len(fake.registry) == count and not [k for k in fake.registry if k.endswith("_2")]
    assert _zone_labels(fake, unreal) == [f"Zone_{ZONE}", f"Zone_{ROOM}"]
    assert all(t.replace_existing for t in fake.tasks)


def test_parent_zone_actor_missing_errors(fake, unreal, parent, zone, it):
    fake.actors = [a for a in fake.actors if not isinstance(a, unreal.GolmokZone)]
    with pytest.raises(it.InteriorSetupError) as info:
        _run(it, zone)
    assert str(info.value) == f"interior_setup: ERROR parent: Zone_{ZONE} not in level: {PARENT_HINT}"
    assert fake.calls == [("load_level", DEFAULT_LEVEL)]  # the level was opened, nothing was imported
    assert not [k for k in fake.registry if ROOM in k]


def test_register_path_b(fake, unreal, parent, zone, it, monkeypatch):
    _run(it, zone, register=True)
    assert fake.calls_of("add_level_to_world") == [("add_level_to_world", SUBLEVEL)]
    i = fake.calls.index(("add_level_to_world", SUBLEVEL))
    assert fake.calls[i - 1] == ("load_level", DEFAULT_LEVEL)  # once the persistent level is open again
    # sz.register_interior_sublevel saves the persistent map by path (V-03 fix), not the current (sub)level
    assert fake.calls[i + 1 : i + 3] == [("save_map", DEFAULT_LEVEL), ("rebuild_in_editor", ZONE)]
    assert fake.calls_of("save_map") == [("save_map", DEFAULT_LEVEL)]
    registered = f"synthetic_zone: sublevel {SUBLEVEL} registered in Levels (initially unloaded, hidden)"
    assert registered in fake.logged("log") and fake.logged("warning") == []
    # without EditorLevelUtils the registration is skipped with a warning and the run still completes
    monkeypatch.delattr(unreal, "EditorLevelUtils")
    fake.calls.clear()
    fake.logs.clear()
    result = _run(it, zone, register=True)
    assert fake.calls_of("add_level_to_world") == [] and result["interior"]["sublevel"] == SUBLEVEL
    warnings = fake.logged("warning")
    assert len(warnings) == 1 and warnings[0].startswith("synthetic_zone: could not register the sublevel")


def test_editor_failures_are_wrapped(fake, parent, zone, it, zi, monkeypatch):
    # a failure of the asset part keeps zone_import's step and text; no interior zone actor is spawned
    fake.fail_import = {"SM_c_e000_n000.obj"}
    with pytest.raises(zi.ZoneImportError) as info:
        _run(it, zone)
    e = info.value
    assert e.step == "chunk c_e000_n000" and "no asset imported from" in e.message
    assert str(e).startswith("zone_import: ERROR chunk c_e000_n000:")
    assert not isinstance(e, it.InteriorSetupError)
    assert fake.calls_of("spawn") == [] and ("new_level", SUBLEVEL) not in fake.calls
    fake.fail_import = set()
    fake.calls.clear()
    # a failing editor call of an interior step becomes InteriorSetupError(step, message)
    with monkeypatch.context() as m:

        def boom(self):
            raise RuntimeError("boom")

        m.setattr(fake_unreal.FakeZoneActor, "unload_in_editor", boom)
        with pytest.raises(it.InteriorSetupError) as info:
            _run(it, zone)
    assert (info.value.step, info.value.message) == ("zone", "boom")
    assert str(info.value) == "interior_setup: ERROR zone: boom"
    assert fake.calls[-1] == ("rebuild_in_editor", ROOM) and ("new_level", SUBLEVEL) not in fake.calls
    result = Path(fake.saved_dir) / "Golmok" / "zone_import" / ROOM / "v1" / "import_result.json"
    assert not result.exists()


# ---- synthetic_zone generalisation (design §3-6) ---------------------------------------------------------


def test_sz_sublevel_helper_defaults_keep_wp05_behaviour(fake, unreal, sz):
    manifest = json.loads(WP05_INTERIOR_MANIFEST.read_text("utf-8"))
    package = sz.sublevel_path(manifest)
    assert package == "/Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior"
    fake.registry[package] = fake_unreal.FakeLevel(fake, package)
    fake.add_actor("PointLight", "Interior_Light", tags=[TAG], level=package)  # label match: replaced
    fake.add_actor("StaticMeshActor", "Interior_Marker", level=package)  # label match: replaced
    fake.add_actor("StaticMeshActor", "Prop_chair", tags=[TAG], level=package)  # tag only: kept
    removed = []
    transform = fake_unreal.Transform(fake_unreal.Vector(10.0, 20.0, 30.0))
    built = sz._spawn_interior_sublevel(manifest, transform, DEFAULT_LEVEL, on_removed=removed.append)
    assert built == package and removed == [2]
    assert fake.calls_of("destroy") == [("destroy", "Interior_Light"), ("destroy", "Interior_Marker")]
    actors = fake.levels[package]
    assert _labels(actors) == ["Prop_chair", "Interior_Light", "Interior_Marker"]
    assert actors[1].tags == [] and actors[2].tags == []  # sublevel_actor_specs carry no tags
    assert tuple(actors[1].location) == (10.0, 20.0, 280.0)
    assert tuple(actors[2].location) == (10.0, 20.0, 180.0)
    assert fake.current_level == DEFAULT_LEVEL and fake.calls[-1] == ("load_level", DEFAULT_LEVEL)
    # with delete_tag only the tagged actors go, whatever their label; on_removed is optional
    fake.calls.clear()
    specs = [{"label": "Interior_Light", "kind": "point_light", "location_cm": (0.0, 0.0, 100.0),
              "intensity_cd": 1.0, "kelvin": 4000.0, "tags": [TAG]}]  # fmt: skip
    sz._spawn_interior_sublevel(manifest, transform, DEFAULT_LEVEL, specs=specs, delete_tag=TAG)
    assert fake.calls_of("destroy") == [("destroy", "Prop_chair")]
    assert [(a.get_actor_label(), list(a.tags)) for a in fake.levels[package]] == [
        ("Interior_Light", []),
        ("Interior_Marker", []),
        ("Interior_Light", [TAG]),
    ]
    # a new sublevel never reports removals
    removed.clear()
    other = {**manifest, "zone_id": "z_other", "version": 1}
    sz._spawn_interior_sublevel(other, transform, DEFAULT_LEVEL, on_removed=removed.append)
    assert removed == [] and ("new_level", "/Game/Golmok/Zones/z_other/v1/L_z_other") in fake.calls
