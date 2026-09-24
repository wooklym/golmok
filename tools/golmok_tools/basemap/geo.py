"""Local East-North-Up frame around an origin, and conversions from any CRS into it.

All basemap geometry is written in one ENU frame per area (meters, origin = area center), so a
2-4 km area keeps millimeter float32 precision and every tile shares the same 3D Tiles transform.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pyproj import CRS, Transformer

WGS84_3D = CRS.from_epsg(4979)  # lon, lat, ellipsoidal height
ECEF = CRS.from_epsg(4978)


@dataclass(frozen=True)
class EnuFrame:
    lon: float
    lat: float
    height: float  # ellipsoidal meters

    def __post_init__(self):
        to_ecef = Transformer.from_crs(WGS84_3D, ECEF, always_xy=True)
        x, y, z = to_ecef.transform(self.lon, self.lat, self.height)
        object.__setattr__(self, "_origin_ecef", np.array([x, y, z]))
        lam, phi = np.radians(self.lon), np.radians(self.lat)
        # Rows: east, north, up unit vectors expressed in ECEF.
        rot = np.array([
            [-np.sin(lam), np.cos(lam), 0.0],
            [-np.sin(phi) * np.cos(lam), -np.sin(phi) * np.sin(lam), np.cos(phi)],
            [np.cos(phi) * np.cos(lam), np.cos(phi) * np.sin(lam), np.sin(phi)],
        ])
        object.__setattr__(self, "_ecef_to_enu", rot)

    @property
    def origin_ecef(self) -> np.ndarray:
        return self._origin_ecef

    def ecef_to_enu(self, xyz: np.ndarray) -> np.ndarray:
        return (np.asarray(xyz, dtype=np.float64) - self._origin_ecef) @ self._ecef_to_enu.T

    def enu_to_ecef(self, enu: np.ndarray) -> np.ndarray:
        return np.asarray(enu, dtype=np.float64) @ self._ecef_to_enu + self._origin_ecef

    def transform_matrix(self) -> list[float]:
        """ENU -> ECEF 4x4 matrix in column-major order (3D Tiles `transform`)."""
        m = np.eye(4)
        m[:3, :3] = self._ecef_to_enu.T  # columns = east, north, up
        m[:3, 3] = self._origin_ecef
        return m.T.flatten().tolist()


class Projector:
    """Converts coordinates in `src_crs` (x, y [, height]) into the ENU frame.

    Heights are taken as orthometric (above sea level, as in Korean DEMs) and converted to
    ellipsoidal by adding `geoid_offset` (constant; varies only centimeters over a few km).
    """

    def __init__(self, src_crs: CRS, frame: EnuFrame, geoid_offset: float = 0.0):
        self.src_crs = CRS.from_user_input(src_crs)
        self.frame = frame
        self.geoid_offset = geoid_offset
        self._to_lonlat = Transformer.from_crs(self.src_crs, CRS.from_epsg(4326), always_xy=True)
        self._from_lonlat = Transformer.from_crs(CRS.from_epsg(4326), self.src_crs, always_xy=True)
        self._to_ecef = Transformer.from_crs(WGS84_3D, ECEF, always_xy=True)

    def to_lonlat(self, x, y):
        return self._to_lonlat.transform(np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64))

    def from_lonlat(self, lon, lat):
        return self._from_lonlat.transform(np.asarray(lon, dtype=np.float64), np.asarray(lat, dtype=np.float64))

    def lonlat_to_enu(self, lon, lat, h_ortho) -> np.ndarray:
        lon = np.asarray(lon, dtype=np.float64)
        lat = np.asarray(lat, dtype=np.float64)
        h = np.asarray(h_ortho, dtype=np.float64) + self.geoid_offset
        x, y, z = self._to_ecef.transform(lon, lat, h)
        return self.frame.ecef_to_enu(np.stack([x, y, z], axis=-1))

    def to_enu(self, x, y, h_ortho) -> np.ndarray:
        lon, lat = self.to_lonlat(x, y)
        return self.lonlat_to_enu(lon, lat, h_ortho)

    def enu_to_lonlat(self, e, n):
        """Horizontal ENU (on the origin's tangent plane) -> lon, lat."""
        e = np.asarray(e, dtype=np.float64)
        n = np.asarray(n, dtype=np.float64)
        ecef = self.frame.enu_to_ecef(np.stack([e, n, np.zeros_like(e)], axis=-1))
        lon, lat, _ = self._to_ecef.transform(ecef[..., 0], ecef[..., 1], ecef[..., 2], direction="INVERSE")
        return lon, lat
