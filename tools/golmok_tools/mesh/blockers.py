"""Blocker planes (docs/spec/zone-manifest.md §3.1) -> thin boxes for UE collision.

Rectangle axes: height axis = zone +z projected onto the plane (north if the plane is horizontal),
width axis = height axis × normal. Boxes are THICKNESS_M thick, centered on the plane.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

THICKNESS_M = 0.02
BLOCKERS_NAME = "blockers.json"


def plane_axes(normal) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(width axis, height axis, unit normal) for a blocker plane."""
    n = np.asarray(normal, dtype=np.float64)
    norm = np.linalg.norm(n)
    if norm < 1e-9:
        raise ValueError("normal_enu has zero length")
    n = n / norm
    up = np.array([0.0, 0.0, 1.0])
    h = up - (up @ n) * n
    if np.linalg.norm(h) < 1e-6:  # horizontal plane
        north = np.array([0.0, 1.0, 0.0])
        h = north - (north @ n) * n
    h /= np.linalg.norm(h)
    w = np.cross(h, n)
    return w, h, n


_BOX_FACES = np.array(
    [
        [0, 2, 1], [0, 3, 2],  # -n
        [4, 5, 6], [4, 6, 7],  # +n
        [0, 1, 5], [0, 5, 4],
        [1, 2, 6], [1, 6, 5],
        [2, 3, 7], [2, 7, 6],
        [3, 0, 4], [3, 4, 7],
    ]
)  # fmt: skip


def plane_box(center, normal, size, thickness: float = THICKNESS_M) -> tuple[np.ndarray, np.ndarray]:
    """8 vertices, 12 outward-facing triangles."""
    w, h, n = plane_axes(normal)
    c = np.asarray(center, dtype=np.float64)
    hw, hh, ht = size[0] / 2, size[1] / 2, thickness / 2
    corners = []
    for s in (-ht, ht):
        for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            corners.append(c + s * n + a * hw * w + b * hh * h)
    v = np.asarray(corners)
    f = _BOX_FACES.copy()
    # keep outward winding whatever the handedness of (w, h, n)
    if np.dot(np.cross(v[f[0, 1]] - v[f[0, 0]], v[f[0, 2]] - v[f[0, 0]]), -n) < 0:
        f = f[:, ::-1]
    return v, f


def load(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {"planes": []}
    return json.loads(p.read_text(encoding="utf-8"))


def save(doc: dict, path: str | Path) -> Path:
    from golmok_tools.zone.manifest import write_json

    return write_json(doc, path)


def add_plane(doc: dict, center, normal, size, kind: str, plane_id: str | None = None) -> dict:
    ids = {p["id"] for p in doc["planes"]}
    if plane_id is None:
        k = 1
        while f"{kind}_{k}" in ids:
            k += 1
        plane_id = f"{kind}_{k}"
    if plane_id in ids:
        raise ValueError(f"blocker id {plane_id!r} already exists")
    plane_axes(normal)  # validates
    doc["planes"].append(
        {
            "id": plane_id,
            "center_enu": [float(x) for x in center],
            "normal_enu": [float(x) for x in normal],
            "size_m": [float(x) for x in size],
            "kind": kind,
        }
    )
    return doc


def blockers_mesh(doc: dict, thickness: float = THICKNESS_M) -> tuple[np.ndarray, np.ndarray]:
    vs, fs, off = [], [], 0
    for p in doc["planes"]:
        v, f = plane_box(p["center_enu"], p["normal_enu"], p["size_m"], thickness)
        vs.append(v)
        fs.append(f + off)
        off += len(v)
    if not vs:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    return np.vstack(vs), np.vstack(fs)


def write_blockers_glb(doc: dict, path: str | Path, thickness: float = THICKNESS_M) -> Path:
    """One GLB node per plane (named by id, extras.kind) so UE can tell glass from no-entry."""
    from golmok_tools.basemap.gltf import MeshData, write_glb

    meshes = []
    for p in doc["planes"]:
        v, f = plane_box(p["center_enu"], p["normal_enu"], p["size_m"], thickness)
        meshes.append(
            MeshData(
                positions=v, indices=f.astype(np.uint32).reshape(-1), name=p["id"], extras={"kind": p["kind"]}
            )
        )
    write_glb(path, meshes, metadata={"generator": "golmok-mesh blockers", "thickness_m": thickness})
    return Path(path)
