"""WP-15a: zone manifest schema_version 2 (optional `spawn`, `display_name`; docs/spec/zone-manifest.md §3.3).

Schema (v2 fields, v1 unchanged, v1 + v2 field = error), model round trip, validator (spawn outside the
footprint = warning), `golmok-zone init/validate/bump`, the synthetic generators / committed fixtures (v2 +
spawn on open ground) and the Zone Index (schema 1, no spawn/display_name).
"""

import copy
import importlib
import json
import sys
import types

import pytest
from zone_util import FIXTURE_ZONES, REPO, make_zone, rect_footprint

from golmok_tools.zone import index as zone_index
from golmok_tools.zone import manifest as zm
from golmok_tools.zone import schema
from golmok_tools.zone.cli import main

SCRIPTS = REPO / "tools" / "scripts"
PY_DIR = REPO / "unreal" / "Golmok" / "Content" / "Python"
CONTENT_ZONES = REPO / "unreal" / "Golmok" / "Content" / "Golmok" / "Zones"
FIXTURE = FIXTURE_ZONES / "z_synthetic_001" / "v1" / "manifest.json"
V2_KEYS = ("spawn", "display_name")
PLAYER_HEIGHT_M = 1.8  # clearance column above a spawn point
PLAYER_RADIUS_M = 0.4  # >= UE capsule radius (34 cm default)

# spawn / display_name per committed zone (the UE side and the runbook quote these)
COMMITTED = {
    "z_synthetic_001": ({"position_enu": [5.0, 4.0, 0.0], "yaw_deg": 90.0}, "합성 골목 1"),
    "z_synthetic_001_interior": ({"position_enu": [0.0, -1.5, 0.0], "yaw_deg": 90.0}, "합성 골목 1 실내"),
    "z_synthetic_002": ({"position_enu": [-8.0, 3.0, -0.16], "yaw_deg": 90.0}, "합성 골목 2"),
}


@pytest.fixture(scope="module")
def scripts():
    sys.path.insert(0, str(SCRIPTS))
    try:
        yield types.SimpleNamespace(
            msz=importlib.import_module("make_synthetic_zone"),
            mif=importlib.import_module("make_interior_fixture"),
            mxf=importlib.import_module("make_index_fixture"),
        )
    finally:
        sys.path.remove(str(SCRIPTS))


@pytest.fixture(scope="module")
def synth():
    sys.modules.setdefault("unreal", types.ModuleType("unreal"))
    sys.path.insert(0, str(PY_DIR))
    try:
        yield importlib.import_module("golmok.synthetic_zone")
    finally:
        sys.path.remove(str(PY_DIR))


def v2():
    return copy.deepcopy(zm.load(FIXTURE))


def as_v1(d):
    d = copy.deepcopy(d)
    d["schema_version"] = 1
    for k in V2_KEYS:
        d.pop(k, None)
    return d


# ---- schema ---------------------------------------------------------------------------------------


def test_committed_fixture_is_v2_and_valid():
    d = v2()
    assert d["schema_version"] == 2 and "spawn" in d and "display_name" in d
    assert schema.validate(d) == []


def test_v1_without_v2_keys_is_valid_and_round_trips_byte_for_byte():
    d = as_v1(v2())
    assert schema.validate(d) == []
    text = zm.dumps(d)
    assert zm.dumps(zm.ZoneManifest.from_dict(json.loads(text))) == text
    assert '"spawn"' not in text and '"display_name"' not in text
    assert zm.check(d, FIXTURE).errors == []


def test_v2_keys_are_optional():
    for keep in ((), ("spawn",), ("display_name",)):
        d = v2()
        for k in V2_KEYS:
            if k not in keep:
                d.pop(k)
        assert schema.validate(d) == [], keep


@pytest.mark.parametrize("key", V2_KEYS)
def test_v1_with_v2_key_is_schema_error(key):
    d = as_v1(v2())
    d[key] = v2()[key]
    errors = schema.validate(d)
    assert errors and any(key in e for e in errors), errors


@pytest.mark.parametrize("value", [0, 3, "2", 2.5, True, None])
def test_schema_version_is_exactly_1_or_2(value):
    d = v2()
    d["schema_version"] = value
    assert any("schema_version" in e for e in schema.validate(d))


def test_unknown_top_level_key_still_error_in_v2():
    d = v2()
    d["sounds"] = []  # WP-17 is not in v2 (v3 if adopted)
    assert any("sounds" in e for e in schema.validate(d))


@pytest.mark.parametrize(
    "spawn",
    [
        {"position_enu": [0, 0, 0]},
        {"yaw_deg": 0},
        {"position_enu": [0, 0], "yaw_deg": 0},
        {"position_enu": [0, 0, 0, 0], "yaw_deg": 0},
        {"position_enu": [0, "a", 0], "yaw_deg": 0},
        {"position_enu": [0, 0, 0], "yaw_deg": 360.5},
        {"position_enu": [0, 0, 0], "yaw_deg": -361},
        {"position_enu": [0, 0, 0], "yaw_deg": "90"},
        {"position_enu": [0, 0, 0], "yaw_deg": 0, "pitch_deg": 0},
        {"position": [0, 0, 0], "yaw_deg": 0},
        [0, 0, 0, 0],
    ],
)
def test_spawn_shape_errors(spawn):
    d = v2()
    d["spawn"] = spawn
    assert any(e.startswith("spawn") for e in schema.validate(d)), spawn


@pytest.mark.parametrize("yaw", [-360, -90.5, 0, 359.99, 360])
def test_spawn_yaw_range_matches_portal(yaw):
    d = v2()
    d["spawn"]["yaw_deg"] = yaw
    d["portals"][0]["pose_enu"]["yaw_deg"] = yaw
    assert schema.validate(d) == []


@pytest.mark.parametrize("name", ["", " ", "\t\n", "가" * 65, 5, None])
def test_display_name_errors(name):
    d = v2()
    d["display_name"] = name
    assert any("display_name" in e for e in schema.validate(d)), name


@pytest.mark.parametrize("name", ["a", "가" * 64, " 연남동 골목 ", "z_synthetic_001"])
def test_display_name_ok(name):
    d = v2()
    d["display_name"] = name
    assert schema.validate(d) == []


def test_schema_documents_v2_and_both_copies_carry_it():
    for path in (REPO / "docs/spec/zone-manifest.schema.json", REPO / "tools/golmok_tools/zone/schemas"):
        s = json.loads((path if path.suffix else path / schema.MANIFEST).read_text(encoding="utf-8"))
        assert s["properties"]["schema_version"]["enum"] == [1, 2]
        assert set(V2_KEYS) <= set(s["properties"])
        assert s["additionalProperties"] is False


# ---- model ----------------------------------------------------------------------------------------


def test_model_round_trips_v2_fields():
    d = v2()
    m = zm.ZoneManifest.from_dict(d)
    assert m.schema_version == 2 and m.display_name == "합성 골목 1"
    assert m.spawn == zm.Spawn(position_enu=[5.0, 4.0, 0.0], yaw_deg=90.0)
    assert zm.dumps(m) == FIXTURE.read_text(encoding="utf-8")


def test_new_manifest_writes_v2_and_omits_absent_keys():
    fp = rect_footprint(37.5620, 126.9250, 40, 20)
    d = zm.new_manifest("z_test_001", "exterior", 37.5620, 126.9250, 50.0, fp).to_dict()
    assert d["schema_version"] == zm.SCHEMA_VERSION == 2
    assert not set(V2_KEYS) & set(d)
    d = zm.new_manifest(
        "z_test_001", "exterior", 37.5620, 126.9250, 50.0, fp, display_name="테스트", spawn=(1, 2, 3, 45)
    ).to_dict()
    assert d["display_name"] == "테스트"
    assert d["spawn"] == {"position_enu": [1.0, 2.0, 3.0], "yaw_deg": 45.0}
    assert schema.validate(d) == []
    keys = list(json.loads(zm.dumps(d)))
    assert keys.index("display_name") == keys.index("parent_zone") + 1
    assert keys.index("spawn") == keys.index("portals") + 1


# ---- validator ------------------------------------------------------------------------------------


def _with_spawn(tmp_path, pos, yaw_deg_zone=0.0):
    fp = rect_footprint(37.5620, 126.9250, 40, 20)  # x -20..20, y -10..10 (ENU at the origin)
    d = zm.new_manifest(
        "z_test_001", "exterior", 37.5620, 126.9250, 50.0, fp, yaw_deg=yaw_deg_zone, spawn=(*pos, 0.0)
    ).to_dict()
    d["sources"] = [{"capture_id": "synthetic"}]
    return d, zm.save(d, tmp_path / "z_test_001" / "v1" / zm.MANIFEST_NAME)


def _spawn_warnings(rep):
    return [w for w in rep.warnings if w.startswith("spawn")]


def test_spawn_inside_footprint_no_warning(tmp_path):
    for pos in ((0, 0, 0), (19.9, 9.9, 3.0), (-20.0, 0.0, 0.0)):  # the edge counts as inside
        d, path = _with_spawn(tmp_path, pos)
        rep = zm.check(d, path)
        assert rep.errors == [] and _spawn_warnings(rep) == [], pos
        assert zm.spawn_footprint_distance_m(d) == pytest.approx(0.0, abs=1e-6)


def test_spawn_outside_footprint_warns_and_strict_fails(tmp_path, capsys):
    d, path = _with_spawn(tmp_path, (0.0, 12.5, 0.0))
    rep = zm.check(d, path)
    assert rep.errors == []
    (w,) = _spawn_warnings(rep)
    assert "footprint 밖(2.50 m)" in w
    assert zm.spawn_footprint_distance_m(d) == pytest.approx(2.5, abs=1e-3)
    assert main(["validate", str(path)]) == 0
    assert main(["validate", "--strict", str(path)]) == 1
    assert "WARN  spawn" in capsys.readouterr().out


def test_spawn_check_uses_zone_transform(tmp_path):
    # zone yaw 90: zone-local +x points north, so (15, 0) is 15 m north of the origin -> outside (|y| <= 10)
    d, path = _with_spawn(tmp_path, (15.0, 0.0, 0.0), yaw_deg_zone=90.0)
    assert zm.spawn_footprint_distance_m(d) == pytest.approx(5.0, abs=1e-3)
    assert _spawn_warnings(zm.check(d, path))
    d, path = _with_spawn(tmp_path, (0.0, 15.0, 0.0), yaw_deg_zone=90.0)  # 15 m west -> inside
    assert _spawn_warnings(zm.check(d, path)) == []


def test_no_spawn_no_distance():
    assert zm.spawn_footprint_distance_m(as_v1(v2())) is None


# ---- CLI ------------------------------------------------------------------------------------------


def _fp_file(tmp_path):
    p = tmp_path / "fp.geojson"
    p.write_text(json.dumps(rect_footprint(37.5620, 126.9250, 40, 20)), encoding="utf-8")
    return p


def _init(tmp_path, *extra):
    out = tmp_path / "zones" / "z_test_001" / "v1"
    argv = ["init", "--id", "z_test_001", "--kind", "exterior", "--origin", "37.5620,126.9250,50"]
    rc = main([*argv, "--footprint", str(_fp_file(tmp_path)), "--out", str(out), *extra])
    return rc, out / zm.MANIFEST_NAME


def test_init_writes_v2_without_spawn_by_default(tmp_path):
    rc, path = _init(tmp_path)
    assert rc == 0
    d = zm.load(path)
    assert d["schema_version"] == 2 and not set(V2_KEYS) & set(d)


def test_init_display_name_and_spawn(tmp_path):
    rc, path = _init(tmp_path, "--display-name", "연남동 골목", "--spawn=-3,2.5,0.1,-45")
    assert rc == 0
    d = zm.load(path)
    assert d["display_name"] == "연남동 골목"
    assert d["spawn"] == {"position_enu": [-3.0, 2.5, 0.1], "yaw_deg": -45.0}
    assert main(["validate", str(path)]) == 0


@pytest.mark.parametrize("bad", ["1,2,3", "1,2,3,4,5", "a,b,c,d"])
def test_init_rejects_bad_spawn(tmp_path, bad):
    rc, path = _init(tmp_path, f"--spawn={bad}")
    assert rc == 2 and not path.exists()


def test_init_out_of_range_spawn_yaw_fails_validation(tmp_path):
    rc, _ = _init(tmp_path, "--spawn=0,0,0,400")
    assert rc == 1


def test_bump_keeps_v1_as_v1(tmp_path):
    src = tmp_path / "z_synthetic_001" / "v1"
    src.mkdir(parents=True)
    zm.save(as_v1(v2()), src / zm.MANIFEST_NAME)
    before = (src / zm.MANIFEST_NAME).read_bytes()
    assert main(["bump", str(src / zm.MANIFEST_NAME)]) == 0
    d = zm.load(tmp_path / "z_synthetic_001" / "v2" / zm.MANIFEST_NAME)
    assert d["schema_version"] == 1 and d["version"] == 2 and not set(V2_KEYS) & set(d)
    assert schema.validate(d) == []
    assert (src / zm.MANIFEST_NAME).read_bytes() == before


def test_bump_keeps_v2_and_its_fields(tmp_path):
    src = tmp_path / "z_synthetic_001" / "v1"
    src.mkdir(parents=True)
    zm.save(v2(), src / zm.MANIFEST_NAME)
    assert main(["bump", str(src / zm.MANIFEST_NAME)]) == 0
    d = zm.load(tmp_path / "z_synthetic_001" / "v2" / zm.MANIFEST_NAME)
    assert d["schema_version"] == 2 and d["version"] == 2
    assert d["spawn"] == v2()["spawn"] and d["display_name"] == v2()["display_name"]


# ---- generators and committed fixtures --------------------------------------------------------------


def _clear(boxes, x, y, z):
    """No solid box overlaps the player column (radius PLAYER_RADIUS_M, z .. z + PLAYER_HEIGHT_M)."""
    r = PLAYER_RADIUS_M
    for lo, hi in boxes:
        if (
            lo[0] - r < x < hi[0] + r
            and lo[1] - r < y < hi[1] + r
            and lo[2] < z + PLAYER_HEIGHT_M
            and hi[2] > z
        ):
            return False
    return True


@pytest.mark.parametrize("zone_id", sorted(COMMITTED))
def test_committed_zones_are_v2_with_spawn(zone_id):
    spawn, name = COMMITTED[zone_id]
    paths = [root / zone_id / "v1" / zm.MANIFEST_NAME for root in (CONTENT_ZONES, FIXTURE_ZONES)]
    assert paths[0].read_bytes() == paths[1].read_bytes()
    d = zm.load(paths[0])
    assert d["schema_version"] == 2 and d["spawn"] == spawn and d["display_name"] == name
    rep = zm.check(d, paths[0])
    assert rep.errors == [] and rep.warnings == []
    assert zm.spawn_footprint_distance_m(d) == 0.0


def test_z_synthetic_001_spawn_on_slab_clear_of_facade(synth):
    d = zm.load(CONTENT_ZONES / "z_synthetic_001" / "v1" / zm.MANIFEST_NAME)
    x, y, z = d["spawn"]["position_enu"]
    floor_lo, floor_hi = synth.FLOOR
    assert floor_lo[0] < x < floor_hi[0] and floor_lo[1] < y < floor_hi[1] and z == floor_hi[2]
    for openings in ((), synth.door_openings(d)):  # WP-04 and WP-05 (door hole) geometry
        geo = synth.synthetic_geometry(d, openings)
        walls = [b for k, v in geo.items() if not k.endswith("_collision") for b in v]
        assert _clear(walls, x, y, z)
    # faces the door it stands south of
    door = d["portals"][0]["pose_enu"]["position"]
    assert x == door[0] and y < door[1] and d["spawn"]["yaw_deg"] == 90.0


def test_interior_fixture_spawn_inside_room(scripts, synth):
    d = scripts.mif.build()
    assert d["schema_version"] == 2
    assert d["spawn"] == {"position_enu": list(map(float, scripts.mif.SPAWN[:3])), "yaw_deg": 90.0}
    assert d["display_name"] == scripts.mif.DISPLAY_NAME
    x, y, z = d["spawn"]["position_enu"]
    floor, *rest = next(v for k, v in synth.interior_geometry(d).items() if k == "SM_room")
    assert z == floor[1][2] and floor[0][0] < x < floor[1][0] and floor[0][1] < y < floor[1][1]
    assert _clear(rest, x, y, z)
    marker = synth.sublevel_actor_specs(d)[1]
    mx, my = marker["location_cm"][0] / 100.0, -marker["location_cm"][1] / 100.0
    half = marker["size_cm"] / 200.0
    assert _clear([((mx - half, my - half, 0.0), (mx + half, my + half, 3.0))], x, y, z)
    assert scripts.mif.main(["--check"]) == 0


def test_make_synthetic_zone_manifests_v2_spawn_on_open_ground(scripts):
    msz = scripts.msz
    ext = msz._exterior_manifest("z_synthetic_scan_001", True)
    room = msz._interior_manifest("z_synthetic_scan_001")
    for d in (ext, room):
        assert d["schema_version"] == 2 and schema.validate(d) == []
        assert zm.spawn_footprint_distance_m(d) == 0.0
    assert ext["display_name"] == msz.DEFAULT_DISPLAY_NAME
    assert room["display_name"] == msz.DEFAULT_DISPLAY_NAME + " 실내"
    x, y, z = ext["spawn"]["position_enu"]
    assert msz.GROUND_X[0] < x < msz.GROUND_X[1] and msz.GROUND_Y[0] < y < msz.GROUND_Y[1]
    assert z == pytest.approx(msz.GROUND_SLOPE * x, abs=1e-9)
    assert _clear([(lo, hi) for _, _, lo, hi in msz.exterior_boxes()], x, y, z)
    (wx0, wx1), _ = msz.WINDOW
    assert wx0 < x < wx1 and y < msz.WALL_B[0][1] and ext["spawn"]["yaw_deg"] == 90.0  # facing the window
    assert 200.0 + x < 195.0  # z_synthetic_002 (200 m east of 001) stays on L_ZoneTest's +-200 m Zone_Ground
    x, y, z = room["spawn"]["position_enu"]
    floor, *walls = msz.room_boxes()
    assert z == floor[1][2] and floor[0][0] < x < floor[1][0] and floor[0][1] < y < floor[1][1]
    assert _clear(walls, x, y, z)
    named = msz._exterior_manifest("z_synthetic_002", False, display_name="합성 골목 2")
    assert named["display_name"] == "합성 골목 2" and named["spawn"] == ext["spawn"]


def test_make_synthetic_zone_rejects_blank_display_name(scripts, tmp_path):
    assert scripts.msz.main(["--out", str(tmp_path), "--display-name", "  ", "--quiet"]) == 2


def test_index_fixture_zone_002_uses_display_name(scripts):
    assert scripts.mxf.DISPLAY_NAME == COMMITTED["z_synthetic_002"][1]


# ---- Zone Index stays schema 1 ----------------------------------------------------------------------


def test_committed_index_has_no_v2_fields():
    for root in (CONTENT_ZONES / "index", FIXTURE_ZONES / "index"):
        files = [root / "zones.json", *sorted((root / "cells").glob("*.json"))]
        for f in files:
            doc = json.loads(f.read_text(encoding="utf-8"))
            assert doc["schema_version"] == 1
            assert schema.validate_index(doc) == []
            text = f.read_text(encoding="utf-8")
            assert '"spawn"' not in text and '"display_name"' not in text


def test_index_build_over_v2_zones_unchanged_entry_shape(tmp_path):
    make_zone(tmp_path, "z_a_001")  # new_manifest: v2 without spawn
    make_zone(
        tmp_path, "z_b_001", edit=lambda d: d.update(display_name="비", spawn=v2()["spawn"]), size=(40, 20)
    )
    zones, cells = zone_index.build_index(tmp_path, [])
    assert zones["schema_version"] == 1
    for z in zones["zones"]:
        assert set(z) == {"id", "version", "kind", "priority", "bbox_wgs84", "manifest"}
    assert schema.validate_index(zones) == []
    for c in cells.values():
        assert schema.validate_index(c) == []
