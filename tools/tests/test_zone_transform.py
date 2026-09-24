"""Coordinate conventions: ENU (m, x=east, y=north, z=up) -> ECEF, area ENU, UE (cm, X=east, Y=south, Z=up).

The expected numbers are parsed from docs/spec/zone-manifest.md §4 so the spec table, this Python code
and pyproj cannot drift apart (WP-04 uses the same table for its C++ tests).
"""

import math
import re

import numpy as np
import pytest
from pyproj import Transformer
from zone_util import REPO

from golmok_tools.zone import transform as T

SPEC = REPO / "docs" / "spec" / "zone-manifest.md"
ORIGIN = (37.5620, 126.9250, 50.0)
AREA = (37.5600, 126.9230, 40.0)
TOL_M = 1e-4  # tables print 4 decimals (m)


def spec_table(name: str) -> list[list[str]]:
    text = SPEC.read_text(encoding="utf-8")
    m = re.search(rf"<!-- table:{name} -->\n(.*?)<!-- /table -->", text, re.S)
    assert m, f"table {name} missing from {SPEC}"
    rows = [r.strip().strip("|").split("|") for r in m.group(1).strip().splitlines()[2:]]
    return [[c.strip() for c in r] for r in rows]


def vec(cell: str) -> list[float]:
    return [float(v) for v in cell.split(",")]


def test_spec_table_a_geodetic_to_ecef_matches_closed_form_and_pyproj():
    to_ecef = Transformer.from_crs("EPSG:4979", "EPSG:4978", always_xy=True)
    rows = spec_table("ecef")
    assert len(rows) >= 5
    for lat, lon, h, x, y, z in ([float(c) for c in r] for r in rows):
        expected = np.array([x, y, z])
        closed = T.geodetic_to_ecef(lat, lon, h)
        proj = np.array(to_ecef.transform(lon, lat, h))
        assert np.abs(closed - expected).max() < TOL_M
        assert np.abs(proj - expected).max() < TOL_M
        assert np.abs(closed - proj).max() < 1e-6  # WGS84 constants agree with pyproj


def test_spec_table_b_zone_local_to_ecef():
    rows = spec_table("zone")
    assert len(rows) >= 6
    for yaw, local, x, y, z, ue in rows:
        m = T.zone_transform(*ORIGIN, yaw_deg=float(yaw))
        got = T.enu_to_ecef(m, vec(local))
        assert np.abs(got - [float(x), float(y), float(z)]).max() < TOL_M, (yaw, local)
        assert np.allclose(T.enu_to_ue(vec(local)), vec(ue))


def test_spec_table_c_zone_local_to_area_and_ue_level():
    rows = spec_table("area")
    assert len(rows) >= 5
    for yaw, local, e, n, u, ue in rows:
        m = T.zone_local_to_area_enu(T.zone_transform(*ORIGIN, yaw_deg=float(yaw)), AREA)
        area = T.apply(m, vec(local))
        assert np.abs(area - [float(e), float(n), float(u)]).max() < TOL_M, (yaw, local)
        assert np.abs(T.enu_to_ue(area) - vec(ue)).max() < 0.01  # cm, 2 decimals


def test_enu_axes_in_ecef_are_east_north_up():
    lat, lon, h = ORIGIN
    m = T.zone_transform(lat, lon, h)
    phi, lam = math.radians(lat), math.radians(lon)
    east = [-math.sin(lam), math.cos(lam), 0.0]
    north = [-math.sin(phi) * math.cos(lam), -math.sin(phi) * math.sin(lam), math.cos(phi)]
    up = [math.cos(phi) * math.cos(lam), math.cos(phi) * math.sin(lam), math.sin(phi)]
    assert np.allclose(m[:3, 0], east) and np.allclose(m[:3, 1], north) and np.allclose(m[:3, 2], up)
    # 10 m up raises the ellipsoidal height by 10 m; 10 m north raises the latitude
    lat_u, lon_u, h_u = T.ecef_to_geodetic(T.enu_to_ecef(m, [0, 0, 10]))
    assert abs(h_u - (h + 10)) < 1e-6 and abs(lat_u - lat) < 1e-9
    lat_n, _, _ = T.ecef_to_geodetic(T.enu_to_ecef(m, [0, 10, 0]))
    assert lat_n > lat
    _, lon_e, _ = T.ecef_to_geodetic(T.enu_to_ecef(m, [10, 0, 0]))
    assert lon_e > lon


def test_yaw_is_counter_clockwise_from_east():
    m = T.zone_transform(*ORIGIN, yaw_deg=90.0)
    ref = T.zone_transform(*ORIGIN)
    # zone +x with yaw 90 points north
    assert np.allclose(T.ecef_to_enu(ref, T.enu_to_ecef(m, [1, 0, 0])), [0, 1, 0], atol=1e-9)


def test_roundtrip_below_micrometer():
    rng = np.random.default_rng(7)
    for yaw in (0.0, 17.5, -130.0):
        m = T.zone_transform(*ORIGIN, yaw_deg=yaw)
        pts = rng.uniform(-500, 500, size=(200, 3))
        back = T.ecef_to_enu(m, T.enu_to_ecef(m, pts))
        assert np.abs(back - pts).max() < 1e-6
        area = T.zone_local_to_area_enu(m, AREA)
        back2 = T.apply(T.rigid_inverse(area), T.apply(area, pts))
        assert np.abs(back2 - pts).max() < 1e-6


def test_row_major_roundtrip_and_rigidity():
    m = T.zone_transform(*ORIGIN, yaw_deg=33.0)
    flat = T.to_row_major(m)
    assert flat[3] == m[0, 3] and flat[12:] == [0.0, 0.0, 0.0, 1.0]  # row-major: tx at index 3
    assert np.array_equal(T.from_row_major(flat), m)
    ortho, det, bottom = T.rigidity_error(m)
    assert ortho < 1e-12 and abs(det - 1) < 1e-12 and bottom == 0
    with pytest.raises(ValueError):
        T.from_row_major(flat[:15])


def test_enu_to_ue_axes():
    # ENU (m) -> UE (cm): X=east, Y=south, Z=up
    assert np.allclose(T.enu_to_ue([1, 0, 0]), [100, 0, 0])
    assert np.allclose(T.enu_to_ue([0, 1, 0]), [0, -100, 0])
    assert np.allclose(T.enu_to_ue([0, 0, 1]), [0, 0, 100])
    assert np.allclose(T.ue_to_enu(T.enu_to_ue([[3, -4, 5]])), [[3, -4, 5]])


def test_ue_actor_matrix_places_imported_vertices():
    m = T.zone_local_to_area_enu(T.zone_transform(*ORIGIN, yaw_deg=30.0), AREA)
    actor = T.ue_actor_matrix(m)
    assert abs(np.linalg.det(actor[:3, :3]) - 1.0) < 1e-9  # still a proper rotation in UE
    p = np.array([[2.0, 5.0, 1.0], [-7.0, 3.0, 0.0]])
    vertices_ue = T.enu_to_ue(p)  # what the importer produces for zone-local vertices
    placed = T.apply(actor, vertices_ue)
    assert np.allclose(placed, T.enu_to_ue(T.apply(m, p)), atol=1e-6)
    # UE yaw = -yaw_deg (UE X axis turned toward -Y, i.e. north)
    x_axis = actor[:3, 0]
    assert abs(math.degrees(math.atan2(x_axis[1], x_axis[0])) - (-30.0)) < 0.01


def test_tilt_zero_for_enu_and_detects_tilt():
    m = T.zone_transform(*ORIGIN)
    assert T.tilt_deg(m) < 1e-6
    tilt = np.eye(4)
    c, s = math.cos(math.radians(2)), math.sin(math.radians(2))
    tilt[1:3, 1:3] = [[c, -s], [s, c]]
    assert abs(T.tilt_deg(m @ tilt) - 2.0) < 1e-6


def test_lonlat_enu_roundtrip():
    lon, lat, h = T.enu_to_lonlat(np.array([[30.0, -12.0, 0.0]]), ORIGIN)
    back = T.lonlat_to_enu(lon, lat, h, ORIGIN)
    assert np.abs(back - [[30.0, -12.0, 0.0]]).max() < 1e-6
