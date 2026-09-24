"""Terrain tile: regular grid over a square in ENU, heights from the DEM, optional orthophoto texture."""

from __future__ import annotations

import numpy as np

from .geo import Projector
from .gltf import MeshData
from .raster import DemSampler, OrthoSource


def terrain_mesh(projector: Projector, dem: DemSampler, x0: float, y0: float, size: float,
                 spacing: float, ortho: OrthoSource | None = None, texture_size: int = 4096,
                 name: str = "terrain") -> MeshData:
    n = max(1, int(round(size / spacing)))
    xs = np.linspace(x0, x0 + size, n + 1)
    ys = np.linspace(y0, y0 + size, n + 1)
    gx, gy = np.meshgrid(xs, ys)  # row = y (north), col = x (east)
    lon, lat = projector.enu_to_lonlat(gx.ravel(), gy.ravel())
    h = dem.sample_lonlat(lon, lat)
    pos = projector.lonlat_to_enu(lon, lat, h)

    # Two CCW (seen from above) triangles per cell.
    i = np.arange(n)
    r, c = np.meshgrid(i, i, indexing="ij")
    a = (r * (n + 1) + c).ravel()
    b = a + 1
    d = a + (n + 1)
    e = d + 1
    indices = np.stack([a, b, e, a, e, d], axis=1).ravel().astype(np.uint32)

    normals = _grid_normals(pos.reshape(n + 1, n + 1, 3)).reshape(-1, 3)

    texture, uv = None, None
    if ortho is not None:
        texture, uv = ortho.crop(lon, lat, max_size=texture_size)
    if uv is None:
        uv = np.stack([(gx.ravel() - x0) / size, 1.0 - (gy.ravel() - y0) / size], axis=1)
    # Terrain uses category 200 so the shared material can tell it apart from walls/roofs.
    uv1 = np.tile([0.0, 200.0], (len(pos), 1))
    return MeshData(positions=pos, indices=indices, normals=normals, uv0=uv, uv1=uv1,
                    texture_jpeg=texture, name=name)


def _grid_normals(p: np.ndarray) -> np.ndarray:
    dx = np.gradient(p, axis=1)
    dy = np.gradient(p, axis=0)
    nrm = np.cross(dx, dy)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True) + 1e-12
    return nrm
