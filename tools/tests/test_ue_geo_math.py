"""Cross-check unreal/.../Geo/GolmokGeoMath.h (pure C++) against golmok_tools.zone.transform and the spec.

The header has no Unreal dependency, so it is compiled with g++ (fixtures/ue/geomath_driver.cpp) into a small
command-line driver. Every function the UE wrappers call is exercised: geodetic<->ECEF, ENU frame, zone
transform, zone-local -> area ENU, ENU<->UE, the actor matrix S M S^-1, rigidity error, point-in-polygon and
blocker axes. Tolerance 1e-6 m (the spec asks 1e-4). Skipped when no C++ compiler is on PATH.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from zone_util import REPO

from golmok_tools.zone import transform as T

HEADER = REPO / "unreal" / "Golmok" / "Source" / "Golmok" / "Geo" / "GolmokGeoMath.h"
SPEC = REPO / "docs" / "spec" / "zone-manifest.md"
ORIGIN = (37.5620, 126.9250, 50.0)
AREA = (37.5600, 126.9230, 40.0)
TOL = 1e-6

DRIVER_SRC = Path(__file__).parent / "fixtures" / "ue" / "geomath_driver.cpp"


def _compiler() -> list[str] | None:
    for name in ("g++", "clang++", "c++"):
        exe = shutil.which(name)
        if exe:
            return [exe, "-std=c++17", "-O1", "-Wall", "-Wextra", "-Werror", "-pedantic"]
    return None


@pytest.fixture(scope="module")
def driver(tmp_path_factory) -> Path:
    cxx = _compiler()
    if cxx is None:
        pytest.skip("no C++ compiler (g++/clang++) on PATH")
    build = tmp_path_factory.mktemp("geomath")
    src = DRIVER_SRC
    exe = build / ("driver.exe" if sys.platform == "win32" else "driver")
    cmd = [*cxx, f"-I{HEADER.parent}", str(src), "-o", str(exe)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"compile failed:\n{' '.join(cmd)}\n{res.stdout}\n{res.stderr}"
    return exe


def run(driver: Path, *args) -> list[float]:
    out = subprocess.run(
        [str(driver), *(str(a) for a in args)], capture_output=True, text=True, check=True
    ).stdout
    return [float(v) for v in out.split()]


def mat_args(m: np.ndarray) -> list[str]:
    return [repr(float(v)) for v in np.asarray(m, dtype=np.float64).reshape(16)]


def spec_table(name: str) -> list[list[str]]:
    text = SPEC.read_text(encoding="utf-8")
    m = re.search(rf"<!-- table:{name} -->\n(.*?)<!-- /table -->", text, re.S)
    assert m, f"table {name} missing from {SPEC}"
    rows = [r.strip().strip("|").split("|") for r in m.group(1).strip().splitlines()[2:]]
    return [[c.strip() for c in r] for r in rows]


def vec(cell: str) -> list[float]:
    return [float(v) for v in cell.split(",")]


def test_header_is_pure():
    text = HEADER.read_text(encoding="utf-8")
    assert re.findall(r'^#include\s+"', text, re.M) == []
    assert set(re.findall(r"^#include\s+<([^>]+)>", text, re.M)) <= {"cmath", "array", "cstddef"}


def test_geodetic_to_ecef_matches_python_and_spec_table_a(driver):
    for lat, lon, h, x, y, z in ([float(c) for c in r] for r in spec_table("ecef")):
        got = np.array(run(driver, "ecef", lat, lon, h))
        assert np.abs(got - T.geodetic_to_ecef(lat, lon, h)).max() < 1e-9
        assert np.abs(got - [x, y, z]).max() < 1e-4  # table prints 4 decimals
    rng = np.random.default_rng(4)
    for lat, lon, h in zip(
        rng.uniform(-89, 89, 20), rng.uniform(-180, 180, 20), rng.uniform(-100, 3000, 20), strict=True
    ):
        got = np.array(run(driver, "ecef", lat, lon, h))
        assert np.abs(got - T.geodetic_to_ecef(lat, lon, h)).max() < 1e-9


def test_ecef_to_geodetic_round_trip_and_pyproj(driver):
    cases = [ORIGIN, AREA, (0.0, 0.0, 0.0), (89.999, 10.0, 100.0), (-45.0, -170.0, -50.0), (90.0, 0.0, 0.0)]
    for lat, lon, h in cases:
        ecef = T.geodetic_to_ecef(lat, lon, h)
        la, lo, hh = run(driver, "geodetic", *ecef)
        ref_lat, ref_lon, ref_h = T.ecef_to_geodetic(ecef)
        assert abs(la - ref_lat) < 1e-9 and abs(hh - ref_h) < TOL, (lat, lon, h)
        if abs(lat) < 89.9999:
            assert abs(((lo - ref_lon) + 180) % 360 - 180) < 1e-9
        back = np.array(run(driver, "ecef", la, lo, hh))
        assert np.abs(back - ecef).max() < TOL


def test_enu_frame_columns_and_zone_transform_match_python(driver):
    for lat, lon, h in (ORIGIN, AREA):
        got = np.array(run(driver, "enuframe", lat, lon, h)).reshape(4, 4)
        assert np.abs(got - T.enu_frame_matrix(lat, lon, h)).max() < 1e-9
    for yaw in (0.0, 30.0, -90.0, 187.5):
        got = np.array(run(driver, "zone", *ORIGIN, yaw)).reshape(4, 4)
        ref = T.zone_transform(*ORIGIN, yaw_deg=yaw)
        assert np.abs(got - ref).max() < 1e-9, yaw


def test_spec_table_b_zone_local_to_ecef_and_ue(driver):
    rows = spec_table("zone")
    assert len(rows) >= 6
    for yaw, local, x, y, z, ue in rows:
        m = T.zone_transform(*ORIGIN, yaw_deg=float(yaw))
        got = np.array(run(driver, "apply", *mat_args(m), *vec(local)))
        assert np.abs(got - [float(x), float(y), float(z)]).max() < 1e-4, (yaw, local)
        assert np.abs(got - T.enu_to_ecef(m, vec(local))).max() < TOL
        assert np.allclose(run(driver, "enu2ue", *vec(local)), vec(ue))
        assert np.allclose(run(driver, "ue2enu", *vec(ue)), vec(local))


def test_spec_table_c_zone_local_to_area_enu_and_ue_level(driver):
    rows = spec_table("area")
    assert len(rows) >= 5
    for yaw, local, e, n, u, ue in rows:
        zone_t = T.zone_transform(*ORIGIN, yaw_deg=float(yaw))
        to_area = np.array(run(driver, "toarea", *mat_args(zone_t), *AREA)).reshape(4, 4)
        ref = T.zone_local_to_area_enu(zone_t, AREA)
        assert np.abs(to_area - ref).max() < 1e-9
        area = np.array(run(driver, "apply", *mat_args(to_area), *vec(local)))
        assert np.abs(area - [float(e), float(n), float(u)]).max() < 1e-4, (yaw, local)
        ue_cm = np.array(run(driver, "enu2ue", *area))
        assert np.abs(ue_cm - vec(ue)).max() < 0.01  # table prints 2 decimals (cm)
        # The actor matrix applied to the chunk vertex (already in UE cm) gives the same level position.
        actor = np.array(run(driver, "actor", *mat_args(to_area))).reshape(4, 4)
        assert np.abs(actor - T.ue_actor_matrix(to_area)).max() < 1e-7
        via_actor = np.array(run(driver, "apply", *mat_args(actor), *T.enu_to_ue(vec(local))))
        assert np.abs(via_actor - ue_cm).max() < 1e-6


def test_actor_matrix_rotation_is_proper_and_yaw_sign(driver):
    zone_t = T.zone_transform(*ORIGIN, yaw_deg=30.0)
    to_area = T.zone_local_to_area_enu(zone_t, AREA)
    actor = np.array(run(driver, "actor", *mat_args(to_area))).reshape(4, 4)
    err, det = run(driver, "rigid", *mat_args(actor))
    assert err < 1e-9 and abs(det - 1.0) < 1e-9  # D R D keeps det +1
    assert np.abs(actor[:3, 3] - T.enu_to_ue(to_area[:3, 3])).max() < 1e-6
    (yaw_ue,) = run(driver, "yaw", *mat_args(to_area))
    assert abs(yaw_ue - (-30.0)) < 0.01  # spec §4: UE Yaw ≈ −30° (curvature adds ~0.002°)


def test_rigid_inverse_and_rigidity_error(driver):
    zone_t = T.zone_transform(*ORIGIN, yaw_deg=12.0)
    inv = np.array(run(driver, "inverse", *mat_args(zone_t))).reshape(4, 4)
    assert (
        np.abs(inv @ zone_t - np.eye(4)).max() < 1e-6
    )  # translation ~3e6 m: 1e-6 absolute is ~1e-12 relative
    err, det = run(driver, "rigid", *mat_args(zone_t))
    assert err < 1e-12 and abs(det - 1.0) < 1e-12
    scaled = zone_t.copy()
    scaled[:3, :3] *= 1.001
    err2, _ = run(driver, "rigid", *mat_args(scaled))
    assert err2 > 1e-3


def test_point_in_polygon(driver):
    ring = [(-10.0, -5.0), (10.0, -5.0), (10.0, 5.0), (-10.0, 5.0)]
    flat = [v for p in ring for v in p]
    assert run(driver, "pip", 4, *flat, 0.0, 0.0) == [1]
    assert run(driver, "pip", 4, *flat, 11.0, 0.0) == [0]
    assert run(driver, "pip", 4, *flat, 9.9, -4.9) == [1]
    assert run(driver, "pip", 4, *flat, 0.0, 5.1) == [0]
    # closed ring (last == first) gives the same answers
    closed = flat + list(ring[0])
    assert run(driver, "pip", 5, *closed, 0.0, 0.0) == [1]
    assert run(driver, "pip", 5, *closed, 11.0, 0.0) == [0]
    # concave L shape: the notch is outside
    L = [0, 0, 4, 0, 4, 1, 1, 1, 1, 4, 0, 4]
    assert run(driver, "pip", 6, *L, 3.0, 3.0) == [0]
    assert run(driver, "pip", 6, *L, 0.5, 3.0) == [1]


def test_blocker_axes_follow_spec_3_1(driver):
    # vertical glass facing south (fixture): height = +z, width = height x normal = z x (-y) = +x
    w, h = np.array(run(driver, "blocker", 0, -1, 0)).reshape(2, 3)
    assert np.allclose(h, [0, 0, 1]) and np.allclose(w, [1, 0, 0])
    # facing east: height +z, width = z x x = +y
    w, h = np.array(run(driver, "blocker", 1, 0, 0)).reshape(2, 3)
    assert np.allclose(h, [0, 0, 1]) and np.allclose(w, [0, 1, 0])
    # horizontal plane: height axis = +y (north), width = y x z = +x
    w, h = np.array(run(driver, "blocker", 0, 0, 1)).reshape(2, 3)
    assert np.allclose(h, [0, 1, 0]) and np.allclose(w, [1, 0, 0])
    # tilted, unnormalized normal: axes orthonormal and orthogonal to the normal
    n = np.array([0.3, -2.0, 0.5])
    w, h = np.array(run(driver, "blocker", *n)).reshape(2, 3)
    for v in (w, h):
        assert abs(np.linalg.norm(v) - 1) < 1e-9 and abs(v @ n) < 1e-9
    assert abs(w @ h) < 1e-9 and h[2] > 0


def test_fixture_manifest_transform_reproduces_origin(driver):
    d = json.loads(
        (REPO / "unreal/Golmok/Content/Golmok/Zones/z_synthetic_001/v1/manifest.json").read_text("utf-8")
    )
    m = np.array(d["transform"]).reshape(4, 4)
    la, lo, h = run(driver, "geodetic", *m[:3, 3])
    o = d["origin"]
    assert abs(la - o["lat"]) < 1e-9 and abs(lo - o["lon"]) < 1e-9 and abs(h - o["height_ellipsoidal"]) < 1e-3
    err, det = run(driver, "rigid", *mat_args(m))
    assert err < 1e-9 and abs(det - 1) < 1e-9


def test_distance_to_polygon_matches_shapely(driver):
    shapely = pytest.importorskip("shapely")
    from shapely.geometry import Point, Polygon

    ring = [(-20.0, -10.0), (20.0, -10.0), (20.0, 10.0), (5.0, 10.0), (5.0, 3.0), (-20.0, 3.0)]  # notched box
    poly = Polygon(ring)
    flat = [v for p in ring for v in p]
    rng = np.random.default_rng(7)
    for x, y in zip(rng.uniform(-40, 40, 60), rng.uniform(-30, 30, 60), strict=True):
        (got,) = run(driver, "dist", len(ring), *flat, x, y)
        assert (
            abs(got - poly.exterior.distance(Point(x, y)) * (0 if poly.contains(Point(x, y)) else 1)) < 1e-9
        )
    assert shapely is not None


def test_polygons_overlap(driver):
    a = [0, 0, 10, 0, 10, 10, 0, 10]
    b = [5, 5, 15, 5, 15, 15, 5, 15]  # overlaps corner
    c = [20, 20, 30, 20, 30, 30, 20, 30]  # disjoint
    d = [2, 2, 3, 2, 3, 3, 2, 3]  # fully inside a
    e = [-5, 4, 15, 4, 15, 6, -5, 6]  # crosses a without a vertex inside
    ovl = lambda p, q: run(driver, "overlap", 4, *p, 4, *q) == [1]  # noqa: E731
    assert ovl(a, b) and ovl(b, a)
    assert not ovl(a, c) and not ovl(c, a)
    assert ovl(a, d) and ovl(d, a)
    assert ovl(a, e) and ovl(e, a)
