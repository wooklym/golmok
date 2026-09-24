"""Splat operations: crop, clean, rigid(+uniform scale) transform with SH rotation, stats."""

from __future__ import annotations

import math
from functools import cache

import numpy as np

from . import ply

# Real SH basis with Condon–Shortley phase, as used by 3DGS renderers and KHR_gaussian_splatting
# (Khronos README, "Calculating color from Spherical Harmonics"). Index 0 = degree 0.
C0 = 0.2820947917738781
C1 = 0.4886025119029199
C2 = (1.092548430592079, -1.092548430592079, 0.3153915652525200, -1.092548430592079, 0.5462742152960395)
C3 = (
    -0.5900435899266435,
    2.890611442640554,
    -0.4570457994644657,
    0.3731763325901154,
    -0.4570457994644657,
    1.445305721320277,
    -0.5900435899266435,
)


def sh_basis(dirs: np.ndarray, degree: int) -> np.ndarray:
    """(N, (degree+1)²) basis values for unit directions."""
    x, y, z = dirs[:, 0], dirs[:, 1], dirs[:, 2]
    cols = [np.full(len(dirs), C0)]
    if degree >= 1:
        cols += [-C1 * y, C1 * z, -C1 * x]
    if degree >= 2:
        xx, yy, zz = x * x, y * y, z * z
        cols += [
            C2[0] * x * y,
            C2[1] * y * z,
            C2[2] * (2 * zz - xx - yy),
            C2[3] * x * z,
            C2[4] * (xx - yy),
        ]
    if degree >= 3:
        cols += [
            C3[0] * y * (3 * xx - yy),
            C3[1] * x * y * z,
            C3[2] * y * (4 * zz - xx - yy),
            C3[3] * z * (2 * zz - 3 * xx - 3 * yy),
            C3[4] * x * (4 * zz - xx - yy),
            C3[5] * z * (xx - yy),
            C3[6] * x * (xx - 3 * yy),
        ]
    return np.stack(cols, axis=1)


@cache
def _sample_dirs(n: int = 256) -> np.ndarray:
    rng = np.random.default_rng(12345)
    d = rng.normal(size=(n, 3))
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def sh_rotation(rot: np.ndarray, degree: int) -> np.ndarray:
    """Block matrix M ((d+1)²-1 square, degrees ≥ 1) with rest' = M @ rest for a splat rotated by `rot`.

    Solved per band from the identity Σ c'_i Y_i(R d) = Σ c_i Y_i(d) over sample directions (exact for
    rotations because each band is closed under rotation).
    """
    dirs = _sample_dirs()
    k = ply.sh_rest_count(degree)
    m = np.zeros((k, k))
    a_all = sh_basis(dirs @ rot.T, degree)[:, 1:]
    b_all = sh_basis(dirs, degree)[:, 1:]
    start = 0
    for band in range(1, degree + 1):
        w = 2 * band + 1
        a, b = a_all[:, start : start + w], b_all[:, start : start + w]
        m[start : start + w, start : start + w] = np.linalg.lstsq(a, b, rcond=None)[0]
        start += w
    return m


def quat_from_matrix(r: np.ndarray) -> np.ndarray:
    """Rotation matrix -> unit quaternion (w, x, y, z)."""
    t = np.trace(r)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        q = [0.25 * s, (r[2, 1] - r[1, 2]) / s, (r[0, 2] - r[2, 0]) / s, (r[1, 0] - r[0, 1]) / s]
    else:
        i = int(np.argmax(np.diag(r)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = math.sqrt(1.0 + r[i, i] - r[j, j] - r[k, k]) * 2
        q = [0.0, 0.0, 0.0, 0.0]
        q[0] = (r[k, j] - r[j, k]) / s
        q[1 + i] = 0.25 * s
        q[1 + j] = (r[j, i] + r[i, j]) / s
        q[1 + k] = (r[k, i] + r[i, k]) / s
    q = np.asarray(q)
    return q / np.linalg.norm(q)


def quat_mul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Hamilton product, (w, x, y, z); a (4,) or (N, 4), b (N, 4)."""
    aw, ax, ay, az = np.moveaxis(np.broadcast_to(a, b.shape), -1, 0)
    bw, bx, by, bz = np.moveaxis(b, -1, 0)
    return np.stack(
        [
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        ],
        axis=-1,
    )


def quat_to_matrix(q: np.ndarray) -> np.ndarray:
    """(N, 4) wxyz -> (N, 3, 3)."""
    w, x, y, z = q.T
    return np.stack(
        [
            np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)], -1),
            np.stack([2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)], -1),
            np.stack([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], -1),
        ],
        axis=1,
    )


def decompose(m: np.ndarray) -> tuple[np.ndarray, float, np.ndarray]:
    """4x4 -> (rotation, uniform scale, translation). Rejects shear, non-uniform scale and mirroring."""
    m = np.asarray(m, dtype=np.float64)
    if m.shape != (4, 4) or not np.allclose(m[3], [0.0, 0.0, 0.0, 1.0]):
        raise ValueError(
            "4x4 matrix last row must be 0 0 0 1 (row-major, translation in the last column; "
            f"a column-major paste puts it in the last row): {m[3] if m.shape == (4, 4) else m.shape}"
        )
    a = m[:3, :3]
    s = np.linalg.norm(a, axis=0)
    if not np.allclose(s, s[0], rtol=1e-6):
        raise ValueError(f"only uniform scale is supported (column norms {s})")
    r = a / s[0]
    if not np.allclose(r.T @ r, np.eye(3), atol=1e-6) or np.linalg.det(r) < 0:
        raise ValueError("matrix must be rotation * uniform scale (no shear or mirror)")
    return r, float(s[0]), m[:3, 3]


def transform(d: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Apply a 4x4 similarity to positions, normals, rotations, scales and SH coefficients."""
    r, s, t = decompose(m)
    out = d.copy()
    p = ply.positions(d) @ (s * r).T + t
    out["x"], out["y"], out["z"] = p.T
    if "nx" in d.dtype.names:
        n = np.stack([d["nx"], d["ny"], d["nz"]], axis=1) @ r.T
        out["nx"], out["ny"], out["nz"] = n.T
    raw = np.stack([d[f"rot_{i}"] for i in range(4)], axis=1).astype(np.float64)
    q = quat_mul(quat_from_matrix(r), raw)  # unit q_R keeps the stored (unnormalized) magnitude
    for i in range(4):
        out[f"rot_{i}"] = q[:, i]
    if s != 1.0:
        for i in range(3):
            out[f"scale_{i}"] = d[f"scale_{i}"] + math.log(s)
    deg = ply.sh_degree(d)
    if deg > 0 and not np.allclose(r, np.eye(3)):
        rest = ply.sh_rest(d)
        ply.set_sh_rest(out, np.einsum("ij,njc->nic", sh_rotation(r, deg), rest))
    return out


def crop_bbox(d: np.ndarray, lo, hi) -> np.ndarray:
    p = ply.positions(d)
    keep = np.all((p >= np.asarray(lo)) & (p <= np.asarray(hi)), axis=1)
    return d[keep]


def crop_polygon(d: np.ndarray, polygon_xy, margin_m: float = 0.0) -> np.ndarray:
    """Keep splats whose (x, y) is inside the polygon grown by margin_m (zone-local m)."""
    import shapely
    from shapely.geometry import Polygon

    poly = polygon_xy if hasattr(polygon_xy, "exterior") else Polygon(polygon_xy)
    if margin_m:
        poly = poly.buffer(margin_m)
    p = ply.positions(d)
    return d[shapely.contains_xy(poly, p[:, 0], p[:, 1])]


def clean(
    d: np.ndarray,
    knn: int = 16,
    std: float = 2.0,
    min_opacity: float | None = None,
    max_scale_m: float | None = None,
) -> tuple[np.ndarray, dict]:
    """Remove floaters (statistical outliers on mean kNN distance), faint and oversized splats."""
    report = {"input": int(len(d))}
    keep = np.ones(len(d), bool)
    if min_opacity is not None:
        low = ply.opacities(d) < min_opacity
        report["low_opacity"] = int(low.sum())
        keep &= ~low
    if max_scale_m is not None:
        big = ply.scales(d).max(axis=1) > max_scale_m
        report["too_large"] = int((big & keep).sum())
        keep &= ~big
    if knn and std and keep.sum() > knn + 1:
        from scipy.spatial import cKDTree

        idx = np.nonzero(keep)[0]
        p = ply.positions(d)[idx]
        dist, _ = cKDTree(p).query(p, k=knn + 1, workers=-1)
        mean = dist[:, 1:].mean(axis=1)
        thr = mean.mean() + std * mean.std()
        out = mean > thr
        report["floaters"] = int(out.sum())
        report["knn_threshold_m"] = float(thr)
        keep[idx[out]] = False
    report["removed"] = int((~keep).sum())
    report["output"] = int(keep.sum())
    return d[keep], report


def stats(d: np.ndarray) -> dict:
    p = ply.positions(d)
    op = ply.opacities(d)
    sc = ply.scales(d).max(axis=1)
    q = [1, 5, 50, 95, 99]
    return {
        "count": int(len(d)),
        "sh_degree": ply.sh_degree(d),
        "bounds": [p.min(axis=0).tolist(), p.max(axis=0).tolist()] if len(d) else [],
        "opacity_percentiles": dict(zip(map(str, q), np.percentile(op, q).round(4).tolist(), strict=True))
        if len(d)
        else {},
        "max_scale_m_percentiles": dict(zip(map(str, q), np.percentile(sc, q).round(5).tolist(), strict=True))
        if len(d)
        else {},
        "properties": list(d.dtype.names),
    }
