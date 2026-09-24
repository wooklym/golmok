"""Collision mesh from a reconstructed mesh (research/02 §3: separate visual and collision layers).

Steps: drop small connected components -> (optional) fill holes up to a perimeter -> snap near-ground
vertices onto RANSAC ground planes fitted per horizontal cell (alleys slope, so one global plane is not
enough) -> quadric decimation (fast-simplification, MIT) -> GLB (glTF Y-up, as golmok-basemap).

open3d is not used: its Linux wheel needs libEGL and pulls in a web stack; plane RANSAC is a few lines of
numpy. Everything here works on position indices only; UVs are irrelevant for collision.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .objio import Mesh

UP_COS = math.cos(math.radians(15))  # ground plane normal within 15° of +z
# A cell's ground inliers must spread at least this much across their minor axis (std, m): rejects a
# line of points (the foot of a wall at a cell edge) but keeps a 1 m strip of a narrow alley.
MIN_GROUND_SPREAD_M = 0.2
GROUND_COLUMN_M = 0.5  # ground candidates: near the lowest point of each column of this size


@dataclass
class CollisionReport:
    input_faces: int = 0
    removed_components: int = 0
    removed_faces: int = 0
    filled_faces: int = 0
    snapped_vertices: int = 0
    ground_planes: list[dict] = field(default_factory=list)
    output_faces: int = 0
    bounds_enu: list[list[float]] = field(default_factory=list)
    up_facing_ratio: float = 0.0


def weld(mesh: Mesh) -> tuple[np.ndarray, np.ndarray]:
    """(vertices, faces) with only the used positions; exact duplicates merged, degenerate faces dropped."""
    v, inv = np.unique(np.round(mesh.v, 6), axis=0, return_inverse=True)
    f = inv.reshape(-1)[mesh.f_v]
    keep = (f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])
    f = f[keep]
    used, finv = np.unique(f, return_inverse=True)
    return v[used], finv.reshape(f.shape)


def _areas(v, f):
    return 0.5 * np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1)


def component_labels(f: np.ndarray, n_vertices: int) -> np.ndarray:
    """Connected component id per face (faces sharing a vertex are connected)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    rows = np.concatenate([f[:, 0], f[:, 1], f[:, 2]])
    cols = np.concatenate([f[:, 1], f[:, 2], f[:, 0]])
    g = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n_vertices, n_vertices))
    _, labels = connected_components(g, directed=False)
    return labels[f[:, 0]]


def remove_small_components(v, f, min_area_m2: float) -> tuple[np.ndarray, np.ndarray, int]:
    if min_area_m2 <= 0 or not len(f):
        return v, f, 0
    lab = component_labels(f, len(v))
    area = np.bincount(lab, weights=_areas(v, f))
    small = area < min_area_m2
    keep = ~small[lab]
    n_removed = int(np.count_nonzero(small[np.unique(lab)]))
    f = f[keep]
    used, inv = np.unique(f, return_inverse=True)
    return v[used], inv.reshape(f.shape), n_removed


def fill_holes(v, f, max_hole_m: float = 20.0) -> tuple[np.ndarray, np.ndarray, int]:
    """Close boundary loops whose perimeter is ≤ max_hole_m with a fan around the loop's centroid.

    The mesh's outer boundary is longer and stays open. Only simple loops (each vertex on exactly one
    incoming and one outgoing boundary edge) are filled; new faces keep the neighbours' winding.
    numpy + scipy only (trimesh's fill_holes needs networkx and closes only 3- and 4-edge holes).
    """
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    if not len(f):
        return v, f, 0
    he = f[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)  # directed half-edges a -> b, face on the left
    _, inv, counts = np.unique(np.sort(he, axis=1), axis=0, return_inverse=True, return_counts=True)
    bnd = he[counts[inv.reshape(-1)] == 1]
    if not len(bnd):
        return v, f, 0
    nodes, bi = np.unique(bnd, return_inverse=True)
    bi = bi.reshape(-1, 2)
    n = len(nodes)
    g = coo_matrix((np.ones(len(bi)), (bi[:, 0], bi[:, 1])), shape=(n, n))
    n_comp, lab = connected_components(g, directed=False)
    out_deg = np.bincount(bi[:, 0], minlength=n)
    in_deg = np.bincount(bi[:, 1], minlength=n)
    simple = np.ones(n_comp, bool)
    simple[np.unique(lab[(out_deg != 1) | (in_deg != 1)])] = False
    length = np.linalg.norm(v[bnd[:, 1]] - v[bnd[:, 0]], axis=1)
    perimeter = np.bincount(lab[bi[:, 0]], weights=length, minlength=n_comp)
    nxt = np.full(n, -1)
    nxt[bi[:, 0]] = bi[:, 1]
    first = np.full(n_comp, -1)
    first[lab[::-1]] = np.arange(n)[::-1]
    new_v, new_f = [], []
    for c in np.nonzero(simple & (perimeter <= max_hole_m))[0]:
        loop = [first[c]]
        while nxt[loop[-1]] != loop[0]:
            loop.append(nxt[loop[-1]])
        ids = nodes[loop]
        center = len(v) + len(new_v)
        new_v.append(v[ids].mean(axis=0))
        # the boundary runs a -> b along the existing faces; the fill runs b -> a
        new_f += [[center, ids[(i + 1) % len(ids)], ids[i]] for i in range(len(ids))]
    if not new_f:
        return v, f, 0
    return np.vstack([v, new_v]), np.vstack([f, np.asarray(new_f, dtype=f.dtype)]), len(new_f)


def ransac_plane(
    pts: np.ndarray, tol: float, iters: int = 200, rng: np.random.Generator | None = None
) -> tuple[np.ndarray, float, np.ndarray] | None:
    """Best upward plane n·x + d = 0 (|n| = 1, n_z > 0) by inlier count; refit by least squares."""
    if len(pts) < 3:
        return None
    rng = rng or np.random.default_rng(0)
    best, best_count = None, 0
    idx = rng.integers(0, len(pts), size=(iters, 3))
    for a, b, c in idx:
        n = np.cross(pts[b] - pts[a], pts[c] - pts[a])
        norm = np.linalg.norm(n)
        if norm < 1e-9:
            continue
        n = n / norm
        if n[2] < 0:
            n = -n
        if n[2] < UP_COS:
            continue
        d = -n @ pts[a]
        count = int(np.count_nonzero(np.abs(pts @ n + d) < tol))
        if count > best_count:
            best, best_count = (n, d), count
    if best is None:
        return None
    n, d = best
    inl = np.abs(pts @ n + d) < tol
    # least-squares refit on inliers (smallest singular vector)
    q = pts[inl]
    c = q.mean(axis=0)
    _, _, vt = np.linalg.svd(q - c, full_matrices=False)
    n = vt[-1] / np.linalg.norm(vt[-1])
    if n[2] < 0:
        n = -n
    if n[2] < UP_COS:
        n, d = best
    else:
        d = -n @ c
    return n, float(d), np.abs(pts @ n + d) < tol


def snap_ground(v, cell: float, tol: float, seed: int = 0) -> tuple[np.ndarray, int, list[dict]]:
    """Per horizontal cell, fit the dominant upward plane and project vertices within ±tol onto it.

    Vertices are only moved along the plane normal and by at most `tol`, so cell seams step ≤ 2*tol.
    """
    v = v.copy()
    rng = np.random.default_rng(seed)
    ij = np.floor(v[:, :2] / cell).astype(np.int64)
    keys = ij[:, 0] * 1_000_003 + ij[:, 1]
    order = np.argsort(keys, kind="stable")
    uniq, start = np.unique(keys[order], return_index=True)
    bounds = np.append(start, len(order))
    planes, snapped = [], 0
    for k in range(len(uniq)):
        sel = order[bounds[k] : bounds[k + 1]]
        # candidates: points near the lowest point of their 0.5 m column (ground, not the walls above it).
        # A share of the cell (e.g. its lower half) would be mostly wall in a narrow alley with tall walls.
        pts = v[sel]
        col_id = np.unique(
            np.floor(pts[:, :2] / GROUND_COLUMN_M).astype(np.int64), axis=0, return_inverse=True
        )[1]
        col_id = col_id.reshape(-1)
        zmin = np.full(col_id.max() + 1, np.inf)
        np.minimum.at(zmin, col_id, pts[:, 2])
        low = pts[:, 2] <= zmin[col_id] + max(3 * tol, 0.1)
        fit = ransac_plane(pts[low], tol, rng=rng)
        if fit is None:
            continue
        n, d, inl = fit
        # skip degenerate fits: inliers must cover an area (not a line of points at the cell edge).
        # The floor is absolute, not a fraction of the cell: alleys can be 2 m wide whatever --snap-cell is.
        xy = pts[low][inl][:, :2]
        if len(xy) < 10 or np.sqrt(max(np.linalg.eigvalsh(np.cov(xy.T))[0], 0.0)) < MIN_GROUND_SPREAD_M:
            continue
        dist = pts @ n + d
        near = np.abs(dist) < tol
        if not near.any():
            continue
        v[sel[near]] = pts[near] - dist[near, None] * n
        snapped += int(near.sum())
        planes.append(
            {
                "cell": [int(ij[sel[0], 0]), int(ij[sel[0], 1])],
                "normal": np.round(n, 5).tolist(),
                "d": round(d, 4),
                "slope_deg": round(math.degrees(math.acos(min(1.0, n[2]))), 2),
                "snapped": int(near.sum()),
            }
        )
    return v, snapped, planes


def decimate(
    v, f, target_tris: int | None = None, ratio: float | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Quadric decimation to target_tris (or keep `ratio` of the faces)."""
    import fast_simplification

    n = len(f)
    if ratio is not None:
        target = max(4, int(n * ratio))
    elif target_tris is not None:
        target = target_tris
    else:
        return v, f
    if target >= n:
        return v, f
    reduction = 1.0 - target / n
    v2, f2 = fast_simplification.simplify(
        np.asarray(v, np.float32), np.asarray(f, np.int32), target_reduction=reduction
    )
    return np.asarray(v2, np.float64), np.asarray(f2, np.int64)


def build_collision(
    mesh: Mesh,
    min_component_m2: float = 1.0,
    fill: bool = False,
    max_hole_m: float = 20.0,
    snap: bool = True,
    snap_cell: float = 10.0,
    snap_tol: float = 0.05,
    target_tris: int | None = 30000,
    ratio: float | None = None,
) -> tuple[np.ndarray, np.ndarray, CollisionReport]:
    rep = CollisionReport(input_faces=mesh.n_faces)
    v, f = weld(mesh)
    v, f, rep.removed_components = remove_small_components(v, f, min_component_m2)
    rep.removed_faces = rep.input_faces - len(f)
    if fill:
        v, f, rep.filled_faces = fill_holes(v, f, max_hole_m)
    if snap:
        v, rep.snapped_vertices, rep.ground_planes = snap_ground(v, snap_cell, snap_tol)
    v, f = decimate(v, f, target_tris=target_tris, ratio=ratio)
    rep.output_faces = int(len(f))
    if len(f):
        used = v[np.unique(f)]
        rep.bounds_enu = [used.min(axis=0).round(4).tolist(), used.max(axis=0).round(4).tolist()]
        a = _areas(v, f)
        n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
        nz = n[:, 2] / np.maximum(np.linalg.norm(n, axis=1), 1e-12)
        rep.up_facing_ratio = float(a[nz > math.cos(math.radians(30))].sum() / max(a.sum(), 1e-12))
    return v, f, rep


def split_by_bboxes(v, f, bboxes) -> list[tuple[np.ndarray, np.ndarray]]:
    """Assign each face (by centroid, horizontally) to the chunk bbox containing it, else the nearest."""
    b = np.asarray(bboxes, dtype=np.float64)[:, :, :2]  # (C, 2, 2): min/max x, y
    c = v[f].mean(axis=1)[:, :2]
    below = np.maximum(b[None, :, 0, :] - c[:, None, :], 0)
    above = np.maximum(c[:, None, :] - b[None, :, 1, :], 0)
    dist = np.linalg.norm(below + above, axis=2)  # 0 inside
    owner = np.argmin(dist, axis=1)
    out = []
    for k in range(len(b)):
        sel = f[owner == k]
        used, inv = np.unique(sel, return_inverse=True)
        out.append((v[used], inv.reshape(sel.shape)))
    return out


def write_collision_glb(
    path, v: np.ndarray, f: np.ndarray, name: str = "collision", extras: dict | None = None
):
    from golmok_tools.basemap.gltf import MeshData, write_glb

    write_glb(
        path,
        [MeshData(positions=v, indices=np.asarray(f, np.uint32).reshape(-1), name=name)],
        metadata={"generator": "golmok-mesh collision", **(extras or {})},
    )
