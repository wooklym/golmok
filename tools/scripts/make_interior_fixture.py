"""Generate the synthetic interior zone fixture z_synthetic_001_interior v1 (WP-05 design §9-1).

Run from anywhere:

    python tools/scripts/make_interior_fixture.py            # (re)write both copies
    python tools/scripts/make_interior_fixture.py --check    # exit 1 if a committed copy differs

The same manifest is written to

    unreal/Golmok/Content/Golmok/Zones/z_synthetic_001_interior/v1/manifest.json  (read by AGolmokZone)
    tools/tests/fixtures/zones/z_synthetic_001_interior/v1/manifest.json           (tests; byte-identical)

The interior is a real zone with its own origin: exterior zone-local (5, 13, 0) m of z_synthetic_001, i.e. the
middle of an 8 x 6 m room behind the facade (exterior y 10..16). Its portal `door_out` (0, -3.5, 0) yaw -90 is
the same point as the exterior `door_1` (5, 9.5, 0) yaw 90, facing the other way. No binary assets are
committed: synthetic_zone.run(interior=True) imports SM_room / SM_<zone_id>_collision in the editor.
tests/test_ue_interior_fixture.py regenerates the dict with build() and compares it with the committed files.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

try:
    from golmok_tools.zone import manifest as zm
    from golmok_tools.zone import schema, transform
except ImportError:  # no `pip install -e tools`: import from the checkout
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from golmok_tools.zone import manifest as zm
    from golmok_tools.zone import schema, transform

REPO = Path(__file__).resolve().parents[2]

ZONE_ID = "z_synthetic_001_interior"
VERSION = 1
PARENT_ZONE = "z_synthetic_001"
PRIORITY = 20
ORIGIN_IN_PARENT_M = (5.0, 13.0, 0.0)  # interior origin in exterior zone-local ENU m
ROOM_SIZE_M = (8.0, 6.0)  # footprint w (east-west) x h (north-south), centered on the origin
ROOM_BBOX_ENU = [[-4.0, -3.0, 0.0], [4.0, 3.0, 3.2]]
ROOM_TRIS = 60  # 5 boxes x 12 triangles (synthetic_zone.interior_geometry)
DOOR_OUT = {
    "id": "door_out",
    "to_zone": PARENT_ZONE,
    "pose_enu": {"position": [0.0, -3.5, 0.0], "yaw_deg": -90.0},
    "radius_m": 1.5,
    "kind": "door",
}

EXTERIOR_MANIFEST = REPO / "unreal/Golmok/Content/Golmok/Zones" / PARENT_ZONE / "v1" / zm.MANIFEST_NAME
CONTENT_PATH = REPO / "unreal/Golmok/Content/Golmok/Zones" / ZONE_ID / f"v{VERSION}" / zm.MANIFEST_NAME
FIXTURE_PATH = REPO / "tools/tests/fixtures/zones" / ZONE_ID / f"v{VERSION}" / zm.MANIFEST_NAME
OUTPUTS = (CONTENT_PATH, FIXTURE_PATH)


def rect_footprint(lat: float, lon: float, w: float, h: float) -> dict:
    """GeoJSON Polygon: w x h m rectangle centered on (lat, lon) on its tangent plane (as tests/zone_util)."""
    xy = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2], [-w / 2, -h / 2]])
    lon_, lat_, _ = transform.enu_to_lonlat(np.column_stack([xy, np.zeros(5)]), (lat, lon, 0.0))
    ring = [[round(float(a), 9), round(float(b), 9)] for a, b in zip(lon_, lat_, strict=True)]
    ring[-1] = ring[0]
    return {"type": "Polygon", "coordinates": [ring]}


def interior_origin(exterior: dict) -> tuple[float, float, float]:
    """(lat, lon, h) of ORIGIN_IN_PARENT_M seen from the exterior zone; h = the exterior height (§9-1)."""
    o = exterior["origin"]
    ext_origin = (o["lat"], o["lon"], o["height_ellipsoidal"])
    lon, lat, _ = transform.enu_to_lonlat(np.array([ORIGIN_IN_PARENT_M]), ext_origin)
    return float(lat[0]), float(lon[0]), float(ext_origin[2])


def build(exterior: dict | None = None) -> dict:
    """The interior manifest dict (design §9-1), derived from the exterior fixture's origin."""
    ext = zm.load(EXTERIOR_MANIFEST) if exterior is None else exterior
    if ext["zone_id"] != PARENT_ZONE:
        raise ValueError(f"exterior manifest is {ext['zone_id']}, expected {PARENT_ZONE}")
    lat, lon, h = interior_origin(ext)
    d = zm.new_manifest(
        ZONE_ID,
        "interior",
        lat,
        lon,
        h,
        rect_footprint(lat, lon, *ROOM_SIZE_M),
        version=VERSION,
        parent_zone=PARENT_ZONE,
        priority=PRIORITY,
    ).to_dict()
    d["layers"]["visual"] = {
        "format": "nanite_mesh",
        "chunks": [{"id": "room", "uri": "visual/room.glb", "bbox_enu": ROOM_BBOX_ENU, "tris": ROOM_TRIS}],
    }
    d["layers"]["collision"] = {"format": "glb", "uri": "collision.glb"}
    d["portals"] = [DOOR_OUT]
    d["replaces"] = {"building_ids": [], "terrain_clip": False}
    d["consent"] = {"type": "owner_consent", "record_id": "synthetic-consent-001"}
    d["attribution"] = ["합성 테스트 데이터 (WP-05)"]
    d["sources"] = [{"capture_id": "synthetic", "note": "실내 테스트 픽스처, 실촬영 아님"}]
    return d


def validate(d: dict, path: Path = CONTENT_PATH) -> list[str]:
    """Schema errors + semantic errors + warnings (the fixture must be clean); [] when good."""
    problems = schema.validate(d)
    if problems:
        return problems
    rep = zm.check(d, path)
    return rep.errors + [f"warning: {w}" for w in rep.warnings]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="compare the committed files instead of writing")
    args = ap.parse_args(argv)
    d = build()
    problems = validate(d)
    if problems:
        for p in problems:
            print(f"ERROR {p}", file=sys.stderr)
        return 1
    text = zm.dumps(d)
    if args.check:
        want = text.encode("utf-8")
        bad = [p for p in OUTPUTS if not p.is_file() or p.read_bytes().replace(b"\r\n", b"\n") != want]
        for p in bad:
            print(f"DIFFERS {p.relative_to(REPO)}", file=sys.stderr)
        return 1 if bad else 0
    for p in OUTPUTS:
        zm.save(d, p)
        print(f"wrote {p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
