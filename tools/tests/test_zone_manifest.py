import copy
import json
import shutil

import numpy as np
from zone_util import FIXTURE_ZONES, make_zone, rect_footprint

from golmok_tools.zone import manifest as zm
from golmok_tools.zone import transform as T

FIXTURE = FIXTURE_ZONES / "z_synthetic_001" / "v1" / "manifest.json"


def fixture():
    return copy.deepcopy(zm.load(FIXTURE))


def errors_of(d, path=None, **kw):
    return zm.check(d, path, **kw).errors


def test_fixture_transform_is_enu_at_origin():
    d = fixture()
    o = d["origin"]
    expected = T.zone_transform(o["lat"], o["lon"], o["height_ellipsoidal"])
    assert np.abs(np.array(d["transform"]) - expected.reshape(16)).max() < 1e-6
    assert (o["lat"], o["lon"], o["height_ellipsoidal"]) == (37.5620, 126.9250, 50.0)


def test_dataclass_roundtrip_is_lossless():
    d = fixture()
    m = zm.ZoneManifest.from_dict(d)
    assert m.layers.visual.chunks[1].id == "chunk_01"
    assert m.portals[0].pose_enu.yaw_deg == 90.0
    assert m.to_dict() == d
    assert json.loads(zm.dumps(m)) == d


def test_save_is_byte_stable(tmp_path):
    p = zm.save(fixture(), tmp_path / "m.json")
    # fixture was written by zm.save (LF); a Windows checkout may turn it into CRLF (text=auto)
    assert p.read_bytes() == FIXTURE.read_bytes().replace(b"\r\n", b"\n")
    assert b"\r\n" not in p.read_bytes()


def test_new_manifest_defaults_validate():
    fp = rect_footprint(37.5620, 126.9250, 30, 30)
    d = zm.new_manifest("z_test_001", "exterior", 37.5620, 126.9250, 50.0, fp, yaw_deg=15).to_dict()
    rep = zm.check(d)
    assert rep.ok, rep.errors
    assert any("chunks" in w for w in rep.warnings)
    assert d["consent"] == {"type": "public_street", "record_id": None}
    assert d["replaces"]["terrain_clip"] is True
    i = zm.new_manifest("z_test_001_in", "interior", 37.5620, 126.9250, 50.0, fp, parent_zone="z_test_001")
    irep = zm.check(i.to_dict())
    assert irep.ok, irep.errors
    assert any("record_id" in w for w in irep.warnings)


def test_non_rigid_transform_rejected():
    d = fixture()
    t = np.array(d["transform"]).reshape(4, 4)
    t[:3, :3] *= 1.01  # scale
    d["transform"] = t.reshape(16).tolist()
    assert any("rigid" in e for e in errors_of(d))
    d = fixture()
    t = np.array(d["transform"]).reshape(4, 4)
    t[:3, 0] *= -1  # mirror: orthogonal but det -1
    d["transform"] = t.reshape(16).tolist()
    assert any("rigid" in e for e in errors_of(d))


def test_origin_must_match_transform():
    d = fixture()
    d["origin_ecef"][0] += 0.01
    assert any("origin_ecef" in e for e in errors_of(d))
    d = fixture()
    d["origin"]["height_ellipsoidal"] += 0.5
    assert any("origin (lat/lon/h)" in e for e in errors_of(d))


def test_realigned_transform_with_small_tilt_warns_but_passes():
    d = fixture()
    t = np.array(d["transform"]).reshape(4, 4)
    c, s = np.cos(np.radians(1.0)), np.sin(np.radians(1.0))
    tilt = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    t[:3, :3] = t[:3, :3] @ tilt
    d["transform"] = t.reshape(16).tolist()
    rep = zm.check(d)
    assert rep.ok and any("기울어" in w for w in rep.warnings)


def test_footprint_checks():
    d = fixture()
    ring = d["footprint_wgs84"]["coordinates"][0]
    ring[1], ring[2] = ring[2], ring[1]  # bow-tie
    assert any("유효하지 않은" in e for e in errors_of(d))
    d = fixture()
    d["footprint_wgs84"]["coordinates"][0][-1] = [126.9251, 37.5621]
    assert any("닫혀" in e for e in errors_of(d))
    d = fixture()
    d["footprint_wgs84"] = rect_footprint(37.5620, 126.9250, 20, 20, dx=200)  # 190 m away from origin
    assert any("떨어져" in e for e in errors_of(d))
    d = fixture()
    d["footprint_wgs84"] = rect_footprint(37.5620, 126.9250, 20, 20, dx=30)  # 20 m outside: warning only
    rep = zm.check(d)
    assert rep.ok and any("footprint 밖" in w for w in rep.warnings)
    d = fixture()  # reversed winding is fine
    d["footprint_wgs84"]["coordinates"][0].reverse()
    assert errors_of(d) == []


def test_id_and_reference_checks():
    d = fixture()
    d["layers"]["visual"]["chunks"][2]["id"] = "chunk_00"
    assert any("id 중복" in e for e in errors_of(d))
    d = fixture()
    d["layers"]["visual"]["chunks"][0]["bbox_enu"] = [[1, 0, 0], [0, 1, 1]]
    assert any("min > max" in e for e in errors_of(d))
    d = fixture()
    d["portals"][0]["to_zone"] = d["zone_id"]
    assert any("자기 자신" in e for e in errors_of(d))


def test_layout_checks(tmp_path):
    path, d = make_zone(tmp_path, "z_layout_001", version=2)
    assert zm.check(d, path).ok
    d["version"] = 3
    assert any("폴더 v2" in e for e in errors_of(d, path))
    odd = zm.save(d, tmp_path / "loose" / "manifest.json")
    assert any("규약" in w for w in zm.check(d, odd).warnings)


def test_check_files(tmp_path):
    dst = tmp_path / "z_synthetic_001" / "v1"
    shutil.copytree(FIXTURE.parent, dst)
    path = dst / "manifest.json"
    d = zm.load(path)
    missing = errors_of(d, path, check_files=True)
    assert sorted(missing) == sorted(f"파일 없음: {u}" for u in zm.referenced_uris(d) if u != "blockers.json")
    for u in zm.referenced_uris(d):
        (dst / u).parent.mkdir(parents=True, exist_ok=True)
        if not (dst / u).exists():
            (dst / u).write_bytes(b"glTF")
    assert errors_of(d, path, check_files=True) == []
    (dst / "blockers.json").write_text('{"planes": [{"id": "g"}]}', encoding="utf-8")
    assert any("blockers.json" in e for e in errors_of(d, path, check_files=True))
    bad = {
        "planes": [
            {"id": "g", "center_enu": [0, 0, 0], "normal_enu": [0, 0, 0], "size_m": [1, 1], "kind": "glass"}
        ]
    }
    (dst / "blockers.json").write_text(json.dumps(bad), encoding="utf-8")
    assert any("normal_enu" in e for e in errors_of(d, path, check_files=True))


def test_read_footprint_file_variants(tmp_path):
    poly = rect_footprint(37.5620, 126.9250, 10, 10)
    for doc in (
        poly,
        {"type": "Feature", "properties": {}, "geometry": poly},
        {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": poly}]},
    ):
        p = tmp_path / "fp.geojson"
        p.write_text(json.dumps(doc), encoding="utf-8")
        assert zm.read_footprint_file(p) == poly
    p.write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    try:
        zm.read_footprint_file(p)
    except ValueError as e:
        assert "exactly 1" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_footprint_enu_is_in_meters():
    local = zm.footprint_enu(rect_footprint(37.5620, 126.9250, 40, 20), (37.5620, 126.9250, 0.0))
    assert abs(local.area - 800.0) < 0.01
    minx, miny, maxx, maxy = local.bounds
    assert np.allclose([minx, miny, maxx, maxy], [-20, -10, 20, 10], atol=1e-3)
