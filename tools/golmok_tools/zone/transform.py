"""Zone coordinate transforms.

Conventions (docs/spec/zone-manifest.md, "좌표 규약"):
    zone-local : ENU at the zone origin, x=east, y=north, z=up, meters (right-handed).
    transform  : zone-local -> ECEF (EPSG:4978, m), 4x4 double, stored row-major (16 numbers).
    area ENU   : ENU at the basemap area origin (= the level's CesiumGeoreference origin), m.
    UE         : X=east, Y=south, Z=up, centimeters (left-handed) -> (x, y, z)_m -> (100x, -100y, 100z)_cm.
    yaw_deg    : counter-clockwise from +x (east) about +z (up), seen from above. UE yaw = -yaw_deg.
"""

from __future__ import annotations

import math

import numpy as np
from pyproj import Transformer

from golmok_tools.basemap.geo import ECEF, WGS84_3D, EnuFrame

# WGS84 ellipsoid (NIMA TR8350.2). Cross-checked against pyproj in tests/test_zone_transform.py.
WGS84_A = 6378137.0
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)

# ENU (m) -> UE (cm): X=east, Y=south, Z=up.
ENU_TO_UE = np.diag([100.0, -100.0, 100.0])

_TO_GEODETIC = Transformer.from_crs(ECEF, WGS84_3D, always_xy=True)


def geodetic_to_ecef(lat: float, lon: float, h: float) -> np.ndarray:
    """Closed-form WGS84 geodetic (deg, deg, ellipsoidal m) -> ECEF (m). Same formula WP-04 uses in C++."""
    phi, lam = math.radians(lat), math.radians(lon)
    n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * math.sin(phi) ** 2)
    return np.array(
        [
            (n + h) * math.cos(phi) * math.cos(lam),
            (n + h) * math.cos(phi) * math.sin(lam),
            (n * (1.0 - WGS84_E2) + h) * math.sin(phi),
        ]
    )


def ecef_to_geodetic(xyz) -> tuple[float, float, float]:
    """ECEF (m) -> (lat, lon, ellipsoidal height)."""
    x, y, z = (float(v) for v in xyz)
    lon, lat, h = _TO_GEODETIC.transform(x, y, z)
    return float(lat), float(lon), float(h)


def rot_z(yaw_deg: float) -> np.ndarray:
    c, s = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def enu_frame_matrix(lat: float, lon: float, h: float) -> np.ndarray:
    """4x4: ENU at (lat, lon, h) -> ECEF. Columns of the rotation are east, north, up."""
    frame = EnuFrame(lon=lon, lat=lat, height=h)
    return np.array(frame.transform_matrix(), dtype=np.float64).reshape(4, 4).T  # column-major -> matrix


def zone_transform(lat: float, lon: float, h: float, yaw_deg: float = 0.0) -> np.ndarray:
    """4x4 zone-local -> ECEF for a zone whose axes are the ENU axes at (lat, lon, h) turned by yaw_deg.

    yaw_deg > 0 turns the zone's +x from east toward north.
    """
    m = enu_frame_matrix(lat, lon, h)
    m[:3, :3] = m[:3, :3] @ rot_z(yaw_deg)
    return m


def to_row_major(m: np.ndarray) -> list[float]:
    return [float(v) for v in np.asarray(m, dtype=np.float64).reshape(16)]


def from_row_major(values) -> np.ndarray:
    m = np.asarray(values, dtype=np.float64)
    if m.shape != (16,):
        raise ValueError(f"transform needs 16 numbers, got {m.size}")
    return m.reshape(4, 4)


def apply(m: np.ndarray, pts) -> np.ndarray:
    """Apply a 4x4 affine transform to one point (3,) or many (N, 3)."""
    p = np.asarray(pts, dtype=np.float64)
    return p @ m[:3, :3].T + m[:3, 3]


def rigid_inverse(m: np.ndarray) -> np.ndarray:
    r, t = m[:3, :3], m[:3, 3]
    inv = np.eye(4)
    inv[:3, :3] = r.T
    inv[:3, 3] = -r.T @ t
    return inv


def enu_to_ecef(zone_t: np.ndarray, enu) -> np.ndarray:
    return apply(zone_t, enu)


def ecef_to_enu(zone_t: np.ndarray, ecef) -> np.ndarray:
    return apply(rigid_inverse(zone_t), ecef)


def zone_local_to_area_enu(zone_t: np.ndarray, area_origin: tuple[float, float, float]) -> np.ndarray:
    """4x4: zone-local (m) -> area ENU (m) at area_origin = (lat, lon, h). = inv(area) @ zone_t."""
    lat, lon, h = area_origin
    return rigid_inverse(enu_frame_matrix(lat, lon, h)) @ zone_t


def enu_to_ue(enu) -> np.ndarray:
    """ENU point(s) in m -> UE cm (X=east, Y=south, Z=up)."""
    return np.asarray(enu, dtype=np.float64) @ ENU_TO_UE.T


def ue_to_enu(ue) -> np.ndarray:
    return np.asarray(ue, dtype=np.float64) @ np.linalg.inv(ENU_TO_UE).T


def ue_actor_matrix(zone_to_area: np.ndarray) -> np.ndarray:
    """4x4 in UE space for the zone's root actor, given zone-local -> area ENU.

    Chunk meshes are imported with vertices already in UE axes (S @ p, S = diag(100,-100,100)), so the
    actor transform is S @ M @ S^-1: rotation D R D (D = diag(1,-1,1), still det +1), location S t (cm).
    """
    s = np.eye(4)
    s[:3, :3] = ENU_TO_UE
    s_inv = np.eye(4)
    s_inv[:3, :3] = np.linalg.inv(ENU_TO_UE)
    return s @ zone_to_area @ s_inv


def rigidity_error(m: np.ndarray) -> tuple[float, float, float]:
    """(max |R^T R - I|, det(R), max |bottom row - [0,0,0,1]|)."""
    r = m[:3, :3]
    ortho = float(np.max(np.abs(r.T @ r - np.eye(3))))
    return ortho, float(np.linalg.det(r)), float(np.max(np.abs(m[3] - np.array([0.0, 0.0, 0.0, 1.0]))))


def tilt_deg(zone_t: np.ndarray) -> float:
    """Angle between the zone's +z and the ellipsoid normal at the zone origin."""
    lat, lon, _ = ecef_to_geodetic(zone_t[:3, 3])
    up = enu_frame_matrix(lat, lon, 0.0)[:3, 2]
    z = zone_t[:3, 2] / np.linalg.norm(zone_t[:3, 2])
    return math.degrees(math.acos(max(-1.0, min(1.0, float(z @ up)))))


_TO_ECEF = Transformer.from_crs(WGS84_3D, ECEF, always_xy=True)


def lonlat_to_enu(lon, lat, h, origin: tuple[float, float, float]) -> np.ndarray:
    """Geodetic arrays -> ENU (N, 3) m at origin = (lat, lon, h)."""
    x, y, z = _TO_ECEF.transform(
        np.asarray(lon, dtype=np.float64), np.asarray(lat, dtype=np.float64), np.asarray(h, dtype=np.float64)
    )
    frame = EnuFrame(lon=origin[1], lat=origin[0], height=origin[2])
    return frame.ecef_to_enu(np.stack([x, y, z], axis=-1))


def enu_to_lonlat(enu, origin: tuple[float, float, float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """ENU (N, 3) m at origin -> (lon, lat, h) arrays."""
    frame = EnuFrame(lon=origin[1], lat=origin[0], height=origin[2])
    ecef = frame.enu_to_ecef(np.asarray(enu, dtype=np.float64))
    return _TO_GEODETIC.transform(ecef[..., 0], ecef[..., 1], ecef[..., 2])
