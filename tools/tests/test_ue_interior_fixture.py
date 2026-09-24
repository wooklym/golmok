"""WP-05 §8-5: the synthetic interior fixture z_synthetic_001_interior v1 (design §9-1).

- tools/scripts/make_interior_fixture.py build() regenerates exactly the committed manifest, in both copies
  (Content/Golmok/Zones for AGolmokZone, tests/fixtures/zones for the tools), and the folder holds no binary
  assets (synthetic_zone.run(interior=True) imports the meshes in the editor).
- Schema and semantic checks are clean (no warnings either).
- Portal round trip: exterior door_1 (5, 9.5, 0) yaw 90 and interior door_out (0, -3.5, 0) yaw -90 are the
  same point facing opposite ways; the interior origin is exterior zone-local (5, 13, 0); the 8 x 6 m room
  sits at exterior y 10..16 and door_1 is inside chunk_01's bbox (the door hole must be cut in chunk_01).
"""

from __future__ import annotations

import json
import sys

import numpy as np
from zone_util import FIXTURE_ZONES, REPO

from golmok_tools.zone import manifest as zm
from golmok_tools.zone import schema
from golmok_tools.zone import transform as T

sys.path.insert(0, str(REPO / "tools" / "scripts"))
import make_interior_fixture as mif  # noqa: E402

CONTENT_ZONES = REPO / "unreal" / "Golmok" / "Content" / "Golmok" / "Zones"
INTERIOR = CONTENT_ZONES / "z_synthetic_001_interior" / "v1" / "manifest.json"
INTERIOR_FIXTURE = FIXTURE_ZONES / "z_synthetic_001_interior" / "v1" / "manifest.json"
EXTERIOR = CONTENT_ZONES / "z_synthetic_001" / "v1" / "manifest.json"

# Two ENU frames 14 m apart differ by ~2.2 µrad, so a true local frame (transform.zone_transform) round-trips
# a point 3.5 m from the origin within ~1e-5 m, not 1e-6. 1e-4 m still catches any axis/sign/unit mistake.
TOL_M = 1e-4


def _lf(path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")  # a Windows checkout may turn LF into CRLF (text=auto)


def test_generator_reproduces_both_committed_copies():
    d = mif.build()
    assert mif.OUTPUTS == (INTERIOR, INTERIOR_FIXTURE)
    for path in (INTERIOR, INTERIOR_FIXTURE):
        assert path.is_file(), f"run python tools/scripts/make_interior_fixture.py ({path})"
        assert json.loads(path.read_text(encoding="utf-8")) == d, path
        assert _lf(path) == zm.dumps(d).encode("utf-8"), f"{path}: not written by zm.save (byte-stable)"
    assert _lf(INTERIOR) == _lf(INTERIOR_FIXTURE)
    assert mif.main(["--check"]) == 0
    # the interior folder is manifest-only: no .glb/.uasset committed for the synthetic room
    assert sorted(p.name for p in INTERIOR.parent.iterdir()) == ["manifest.json"]
    assert sorted(p.name for p in INTERIOR_FIXTURE.parent.iterdir()) == ["manifest.json"]


def test_build_derives_from_the_exterior_fixture_and_rejects_another():
    ext = zm.load(EXTERIOR)
    assert mif.build(ext) == mif.build()
    other = dict(ext, zone_id="z_other_001")
    try:
        mif.build(other)
    except ValueError as e:
        assert "z_other_001" in str(e)
    else:
        raise AssertionError("build() must refuse an exterior manifest that is not z_synthetic_001")


def test_schema_and_semantics_are_clean():
    for path in (INTERIOR, INTERIOR_FIXTURE):
        d = zm.load(path)
        assert schema.validate(d) == []
        rep = zm.check(d, path)  # includes the <zone_id>/v<version>/manifest.json layout check
        assert rep.errors == [] and rep.warnings == [], (path, rep)
        assert mif.validate(d, path) == []


def test_identity_fields():
    d = zm.load(INTERIOR)
    assert d["zone_id"] == "z_synthetic_001_interior" and d["version"] == 1
    assert d["kind"] == "interior" and d["parent_zone"] == "z_synthetic_001"
    assert d["priority"] == 20
    assert d["replaces"] == {"building_ids": [], "terrain_clip": False}
    assert d["consent"] == {"type": "owner_consent", "record_id": "synthetic-consent-001"}
    assert all(v is None for v in d["quality"].values()) and len(d["quality"]) == 4
    assert d["attribution"] == ["합성 테스트 데이터 (WP-05)"]
    assert d["sources"] == [{"capture_id": "synthetic", "note": "실내 테스트 픽스처, 실촬영 아님"}]
    chunks = d["layers"]["visual"]["chunks"]
    assert d["layers"]["visual"]["format"] == "nanite_mesh"
    assert len(chunks) == 1 and chunks[0]["id"] == "room" and chunks[0]["uri"] == "visual/room.glb"
    assert chunks[0]["bbox_enu"] == [[-4.0, -3.0, 0.0], [4.0, 3.0, 3.2]]
    assert d["layers"]["collision"] == {"format": "glb", "uri": "collision.glb"}
    assert "blockers" not in d["layers"] and "navmesh" not in d["layers"]
    assert len(d["portals"]) == 1
    portal = d["portals"][0]
    assert portal["id"] == "door_out" and portal["to_zone"] == "z_synthetic_001"
    assert portal["pose_enu"] == {"position": [0.0, -3.5, 0.0], "yaw_deg": -90.0}
    assert portal["radius_m"] == 1.5 and portal["kind"] == "door"
    assert d["origin"]["height_ellipsoidal"] == 50.0  # same as the exterior (§9-1)


def test_interior_origin_is_exterior_local_5_13_0():
    ext, inn = zm.load(EXTERIOR), zm.load(INTERIOR)
    e, i = T.from_row_major(ext["transform"]), T.from_row_major(inn["transform"])
    origin_in_exterior = T.ecef_to_enu(e, i[:3, 3])
    assert np.abs(origin_in_exterior - [5.0, 13.0, 0.0]).max() < TOL_M, origin_in_exterior
    # the transform is the plain ENU frame at the interior origin (yaw 0), like every zone the pipeline writes
    o = inn["origin"]
    expected = T.zone_transform(o["lat"], o["lon"], o["height_ellipsoidal"])
    assert np.abs(i - expected).max() < 1e-9
    assert np.allclose(inn["origin_ecef"], i[:3, 3])


def test_portal_round_trip_door_1_is_door_out_facing_back():
    ext, inn = zm.load(EXTERIOR), zm.load(INTERIOR)
    e, i = T.from_row_major(ext["transform"]), T.from_row_major(inn["transform"])
    door_1 = next(p for p in ext["portals"] if p["id"] == "door_1")
    door_out = inn["portals"][0]
    assert door_1["to_zone"] == inn["zone_id"] and door_out["to_zone"] == ext["zone_id"]
    assert door_1["pose_enu"]["position"] == [5.0, 9.5, 0.0] and door_1["pose_enu"]["yaw_deg"] == 90.0
    # exterior door_1 -> ECEF -> interior-local == door_out position
    in_interior = T.ecef_to_enu(i, T.enu_to_ecef(e, door_1["pose_enu"]["position"]))
    assert np.abs(in_interior - door_out["pose_enu"]["position"]).max() < TOL_M, in_interior
    # and back: interior door_out -> ECEF -> exterior-local == door_1 position
    in_exterior = T.ecef_to_enu(e, T.enu_to_ecef(i, door_out["pose_enu"]["position"]))
    assert np.abs(in_exterior - door_1["pose_enu"]["position"]).max() < TOL_M, in_exterior
    # opposite facing: yaw 90 (into the interior, north) vs -90 (out, south); both frames have yaw 0
    assert door_out["pose_enu"]["yaw_deg"] == -90.0
    assert (door_1["pose_enu"]["yaw_deg"] - door_out["pose_enu"]["yaw_deg"]) % 360.0 == 180.0
    fwd_1 = T.rot_z(door_1["pose_enu"]["yaw_deg"]) @ [1.0, 0.0, 0.0]
    fwd_out = T.rot_z(door_out["pose_enu"]["yaw_deg"]) @ [1.0, 0.0, 0.0]
    assert np.allclose(e[:3, :3] @ fwd_1, -(i[:3, :3] @ fwd_out), atol=1e-5)
    assert door_1["radius_m"] == door_out["radius_m"]


def test_room_footprint_sits_behind_the_facade_and_door_1_is_in_chunk_01():
    ext, inn = zm.load(EXTERIOR), zm.load(INTERIOR)
    o = ext["origin"]
    ext_origin = (o["lat"], o["lon"], o["height_ellipsoidal"])
    # interior footprint seen from the exterior origin: x 1..9, y 10..16 (8 x 6 m centered on (5, 13))
    local = zm.footprint_enu(inn["footprint_wgs84"], ext_origin)
    assert np.allclose(local.bounds, [1.0, 10.0, 9.0, 16.0], atol=1e-3), local.bounds
    assert abs(local.area - 48.0) < 0.01
    # in its own frame the room is centered on the origin
    io = inn["origin"]
    own = zm.footprint_enu(inn["footprint_wgs84"], (io["lat"], io["lon"], io["height_ellipsoidal"]))
    assert np.allclose(own.bounds, [-4.0, -3.0, 4.0, 3.0], atol=1e-3), own.bounds
    # the room bbox (visual chunk) matches the footprint
    lo, hi = inn["layers"]["visual"]["chunks"][0]["bbox_enu"]
    assert (lo[0], lo[1], hi[0], hi[1]) == (-4.0, -3.0, 4.0, 3.0)
    # the facade wall is the north 20 cm of the exterior chunks (y 9.8..10): the room starts right behind it
    ext_chunks = ext["layers"]["visual"]["chunks"]
    assert all(c["bbox_enu"][1][1] == 10.0 for c in ext_chunks)
    # door_1 lies inside chunk_01's x range (-7..7): synthetic_zone cuts the door hole in chunk_01
    door_1 = next(p for p in ext["portals"] if p["id"] == "door_1")
    px, py, _ = door_1["pose_enu"]["position"]
    chunk_01 = next(c for c in ext_chunks if c["id"] == "chunk_01")
    (x0, y0, _), (x1, y1, _) = chunk_01["bbox_enu"]
    r = door_1["radius_m"]
    assert x0 < px - r and px + r < x1, "door hole must fit inside chunk_01"
    assert y0 < py < y1
    assert [c["id"] for c in ext_chunks if c["bbox_enu"][0][0] <= px <= c["bbox_enu"][1][0]] == ["chunk_01"]
