"""Load meshes (GLB/OBJ) as surface samples with normals, in a chosen axis convention.

Axis conventions (``axes`` argument):
    gltf-yup : glTF Y-up as written by golmok-basemap's gltf.py -> ENU = (x, -z, y)   [default]
    enu      : vertices already ENU (x=east, y=north, z=up), meters
    ue       : Unreal cm, X=east, Y=south, Z=up -> ENU = (x/100, -y/100, z/100)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh

AXES = ("gltf-yup", "enu", "ue")


@dataclass
class Samples:
    points: np.ndarray  # (N, 3) ENU meters
    normals: np.ndarray  # (N, 3) unit
    faces_total: int = 0
    bounds: np.ndarray | None = None  # (2, 3) ENU

    def __len__(self) -> int:
        return len(self.points)


def to_enu(v: np.ndarray, axes: str) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64)
    if axes == "gltf-yup":
        return np.stack([v[..., 0], -v[..., 2], v[..., 1]], axis=-1)
    if axes == "enu":
        return v
    if axes == "ue":
        return np.stack([v[..., 0], -v[..., 1], v[..., 2]], axis=-1) / 100.0
    raise ValueError(f"unknown axes {axes!r}; choose from {AXES}")


def load_mesh(path: str | Path, axes: str = "gltf-yup") -> trimesh.Trimesh:
    """One Trimesh in ENU meters (scenes are concatenated)."""
    mesh = trimesh.load(str(path), force="mesh", process=False)
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        raise ValueError(f"no triangles in {path}")
    return trimesh.Trimesh(vertices=to_enu(mesh.vertices, axes), faces=mesh.faces, process=False)


def sample_mesh(mesh: trimesh.Trimesh, n: int, seed: int = 0) -> Samples:
    """Area-weighted surface samples with face normals (exact for LOD1 boxes)."""
    n = int(max(1, min(n, 50_000_000)))
    pts, fidx = trimesh.sample.sample_surface(mesh, n, seed=seed)
    return Samples(
        points=np.asarray(pts, dtype=np.float64),
        normals=np.asarray(mesh.face_normals[fidx], dtype=np.float64),
        faces_total=int(len(mesh.faces)),
        bounds=np.asarray(mesh.bounds, dtype=np.float64),
    )


def merge(samples: list[Samples]) -> Samples:
    samples = [s for s in samples if len(s)]
    if not samples:
        return Samples(np.zeros((0, 3)), np.zeros((0, 3)))
    pts = np.concatenate([s.points for s in samples])
    return Samples(
        points=pts,
        normals=np.concatenate([s.normals for s in samples]),
        faces_total=sum(s.faces_total for s in samples),
        bounds=np.stack([pts.min(axis=0), pts.max(axis=0)]),
    )


def load_basemap(folder: str | Path, max_points: int = 200_000, seed: int = 0):
    """Basemap output folder -> (manifest dict, building Samples, terrain Samples), all in area ENU.

    Buildings and terrain are sampled separately so walls and ground can be matched to the right
    part of the zone (ARCHITECTURE §5 ⑦: --ground uses the terrain tiles).
    """
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    tiles = manifest.get("tiles", [])
    b_meshes = [load_mesh(folder / t["buildings"]) for t in tiles if t.get("buildings")]
    t_meshes = [load_mesh(folder / t["terrain"]) for t in tiles if t.get("terrain")]

    def sample_group(meshes):
        if not meshes:
            return Samples(np.zeros((0, 3)), np.zeros((0, 3)))
        areas = np.array([m.area for m in meshes])
        share = areas / max(areas.sum(), 1e-9)
        counts = [max(1, int(round(max_points * s))) for s in share]
        return merge([sample_mesh(m, n, seed) for m, n in zip(meshes, counts, strict=True)])

    return manifest, sample_group(b_meshes), sample_group(t_meshes)


def crop(samples: Samples, center: np.ndarray, radius: float) -> Samples:
    d = np.linalg.norm(samples.points[:, :2] - np.asarray(center)[:2], axis=1)
    keep = d <= radius
    pts = samples.points[keep]
    return Samples(
        pts,
        samples.normals[keep],
        samples.faces_total,
        None if not len(pts) else np.stack([pts.min(0), pts.max(0)]),
    )
