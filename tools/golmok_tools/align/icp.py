"""Point-to-plane ICP (numpy + scipy KD-tree), rigid, with a 4-DoF (yaw + translation) option.

Linearised small-angle solve per iteration (Low 2004): minimise sum ((R p + t - q) . n)^2 over
(rx, ry, rz, tx, ty, tz), then re-orthonormalise. Small problem sizes (<= 200k points) keep this
in pure Python fast enough, and it avoids a native open3d dependency in CI.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import cKDTree


@dataclass
class IcpResult:
    transform: np.ndarray  # 4x4 applied to the source (ENU meters)
    rmse: float  # point-to-plane RMSE over inliers, meters
    inlier_ratio: float
    iterations: int
    converged: bool
    history: list[float] = field(default_factory=list)


def _rot_from_small(rx: float, ry: float, rz: float) -> np.ndarray:
    """Exact rotation from an axis-angle vector (small angles from the linear solve)."""
    v = np.array([rx, ry, rz])
    theta = np.linalg.norm(v)
    if theta < 1e-12:
        return np.eye(3)
    k = v / theta
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(theta) * kx + (1 - np.cos(theta)) * kx @ kx


def icp_point_to_plane(
    src: np.ndarray,
    dst: np.ndarray,
    dst_normals: np.ndarray,
    init: np.ndarray | None = None,
    max_correspondence_m: float = 2.0,
    max_iterations: int = 60,
    tolerance: float = 1e-5,
    dof: int = 6,
    normal_agreement: float = 0.0,
    src_normals: np.ndarray | None = None,
) -> IcpResult:
    """Align src points to the dst surface (points + normals).

    dof=4 keeps the source level (yaw + translation only): use it when the scan's up axis is trusted.
    dof=1 solves the vertical shift only (ground-to-terrain matching, where yaw/xy are unobservable).
    normal_agreement > 0 rejects pairs whose normals disagree (dot < value); needs src_normals.
    """
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)
    dst_normals = np.asarray(dst_normals, dtype=np.float64)
    if len(dst) < 10 or len(src) < 10:
        raise ValueError("need at least 10 points on both sides")
    tree = cKDTree(dst)
    t_total = np.eye(4) if init is None else np.array(init, dtype=np.float64)
    cur = src @ t_total[:3, :3].T + t_total[:3, 3]
    cur_n = None if src_normals is None else np.asarray(src_normals) @ t_total[:3, :3].T
    history: list[float] = []
    prev_err = np.inf
    converged = False
    it = 0
    for it in range(1, max_iterations + 1):  # noqa: B007 - reported as iterations
        dist, idx = tree.query(cur, distance_upper_bound=max_correspondence_m)
        ok = np.isfinite(dist)
        if normal_agreement > 0 and cur_n is not None:
            agree = (
                np.einsum("ij,ij->i", cur_n, dst_normals[np.minimum(idx, len(dst) - 1)]) >= normal_agreement
            )
            ok &= agree
        if ok.sum() < 6:
            break
        p, q, n = cur[ok], dst[idx[ok]], dst_normals[idx[ok]]
        r = np.einsum("ij,ij->i", q - p, n)  # signed point-to-plane residual
        err = float(np.sqrt(np.mean(r**2)))
        history.append(err)
        # Jacobian rows: [ (p x n), n ] for 6-DoF; [ (p x n)_z, n ] for yaw-only.
        pxn = np.cross(p, n)
        if dof == 6:
            a = np.hstack([pxn, n])
        elif dof == 4:
            a = np.hstack([pxn[:, 2:3], n])
        elif dof == 1:
            a = n[:, 2:3]
        else:
            raise ValueError("dof must be 1, 4 or 6")
        # rcond guards against unobservable directions (e.g. yaw against a single flat plane).
        x, *_ = np.linalg.lstsq(a, r, rcond=1e-6)
        if dof == 6:
            rot = _rot_from_small(x[0], x[1], x[2])
            trans = x[3:6]
        elif dof == 4:
            rot = _rot_from_small(0.0, 0.0, x[0])
            trans = x[1:4]
        else:
            rot = np.eye(3)
            trans = np.array([0.0, 0.0, x[0]])
        step = np.eye(4)
        step[:3, :3] = rot
        step[:3, 3] = trans
        t_total = step @ t_total
        cur = cur @ rot.T + trans
        if cur_n is not None:
            cur_n = cur_n @ rot.T
        if abs(prev_err - err) < tolerance:
            converged = True
            break
        prev_err = err

    dist, idx = tree.query(cur, distance_upper_bound=max_correspondence_m)
    ok = np.isfinite(dist)
    if ok.any():
        r = np.einsum("ij,ij->i", dst[idx[ok]] - cur[ok], dst_normals[idx[ok]])
        rmse = float(np.sqrt(np.mean(r**2)))
    else:
        rmse = float("nan")
    return IcpResult(
        transform=t_total,
        rmse=rmse,
        inlier_ratio=float(ok.mean()),
        iterations=it,
        converged=converged,
        history=history,
    )


def decompose(m: np.ndarray) -> dict:
    """Shift (m), yaw/pitch/roll-ish angles (deg) and scale of a 4x4 for reports."""
    r = m[:3, :3]
    scale = float(np.cbrt(abs(np.linalg.det(r))))
    rn = r / scale
    yaw = float(np.degrees(np.arctan2(rn[1, 0], rn[0, 0])))
    tilt = float(np.degrees(np.arccos(np.clip(rn[2, 2], -1.0, 1.0))))
    return {
        "shift_m": [float(v) for v in m[:3, 3]],
        "shift_norm_m": float(np.linalg.norm(m[:3, 3])),
        "yaw_deg": yaw,
        "tilt_deg": tilt,
        "scale": scale,
    }
