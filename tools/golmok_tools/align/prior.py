"""GPS prior: similarity transform (scale, R, t) from camera positions to GPS positions in area ENU.

Umeyama (1991) closed-form least squares, wrapped in RANSAC to drop bad GPS fixes (urban canyons).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Similarity:
    scale: float
    rotation: np.ndarray  # (3, 3)
    translation: np.ndarray  # (3,)
    inliers: np.ndarray  # bool mask over the input pairs
    rmse: float  # over inliers, meters

    def matrix(self) -> np.ndarray:
        m = np.eye(4)
        m[:3, :3] = self.scale * self.rotation
        m[:3, 3] = self.translation
        return m

    def apply(self, pts) -> np.ndarray:
        p = np.asarray(pts, dtype=np.float64)
        return self.scale * (p @ self.rotation.T) + self.translation


def umeyama(
    src: np.ndarray, dst: np.ndarray, with_scale: bool = True
) -> tuple[float, np.ndarray, np.ndarray]:
    """Least-squares similarity dst ~ s * R @ src + t. Needs >= 3 non-collinear points."""
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)
    if len(src) < 3 or len(src) != len(dst):
        raise ValueError("need at least 3 matching points")
    mu_s, mu_d = src.mean(axis=0), dst.mean(axis=0)
    xs, xd = src - mu_s, dst - mu_d
    cov = xd.T @ xs / len(src)
    u, d, vt = np.linalg.svd(cov)
    s_fix = np.eye(3)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        s_fix[2, 2] = -1.0
    rot = u @ s_fix @ vt
    var_s = (xs**2).sum() / len(src)
    scale = float(np.trace(np.diag(d) @ s_fix) / var_s) if with_scale and var_s > 0 else 1.0
    t = mu_d - scale * rot @ mu_s
    return scale, rot, t


def umeyama_level(
    src: np.ndarray, dst: np.ndarray, with_scale: bool = True
) -> tuple[float, np.ndarray, np.ndarray]:
    """Similarity restricted to yaw + scale + translation (the scan's up axis is trusted).

    Camera tracks of a street capture are nearly planar, so a free 3D rotation would tilt from GPS
    noise; here the rotation is solved in the horizontal plane and z is a mean offset.
    """
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)
    if len(src) < 2 or len(src) != len(dst):
        raise ValueError("need at least 2 matching points")
    mu_s, mu_d = src.mean(axis=0), dst.mean(axis=0)
    xs, xd = src[:, :2] - mu_s[:2], dst[:, :2] - mu_d[:2]
    cov = xd.T @ xs / len(src)
    u, d, vt = np.linalg.svd(cov)
    s_fix = np.eye(2)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        s_fix[1, 1] = -1.0
    r2 = u @ s_fix @ vt
    var_s = (xs**2).sum() / len(src)
    scale = float(np.trace(np.diag(d) @ s_fix) / var_s) if with_scale and var_s > 0 else 1.0
    rot = np.eye(3)
    rot[:2, :2] = r2
    t = mu_d - scale * rot @ mu_s
    return scale, rot, t


def fit_prior(
    src: np.ndarray,
    dst: np.ndarray,
    with_scale: bool = True,
    inlier_m: float = 8.0,
    iterations: int = 200,
    seed: int = 0,
    level: bool = True,
) -> Similarity:
    """RANSAC + Umeyama. inlier_m: max residual for a GPS fix to count (phone GPS in streets: 5-15 m).

    level=True (default) keeps the scan level (yaw/scale/translation only); level=False is full 3D.
    """
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)
    n = len(src)
    if n < 3:
        raise ValueError("need at least 3 camera/GPS pairs")
    solve = umeyama_level if level else umeyama
    rng = np.random.default_rng(seed)
    best_mask = np.ones(n, dtype=bool)
    best_count = -1
    if n > 3:
        for _ in range(iterations):
            idx = rng.choice(n, 3, replace=False)
            try:
                s, r, t = solve(src[idx], dst[idx], with_scale)
            except (ValueError, np.linalg.LinAlgError):
                continue
            if not with_scale:
                s = 1.0
            if not (0.5 <= s <= 2.0):  # a sane phone/scan scale; wildly off = degenerate sample
                continue
            res = np.linalg.norm(s * (src @ r.T) + t - dst, axis=1)
            mask = res <= inlier_m
            if mask.sum() > best_count:
                best_count, best_mask = int(mask.sum()), mask
        if best_count < 3:
            best_mask = np.ones(n, dtype=bool)
    s, r, t = solve(src[best_mask], dst[best_mask], with_scale)
    res = np.linalg.norm(s * (src[best_mask] @ r.T) + t - dst[best_mask], axis=1)
    return Similarity(
        scale=s, rotation=r, translation=t, inliers=best_mask, rmse=float(np.sqrt(np.mean(res**2)))
    )
