"""Quality metrics recorded into manifest.quality after alignment (ARCHITECTURE §5 ⑧)."""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import MultiPoint, Polygon

# Proposed thresholds (조정 예정): review by eye when exceeded.
THRESHOLDS = {"icp_rmse_m": 0.5, "tilt_deg": 1.0, "footprint_iou_min": 0.5, "inlier_ratio_min": 0.5}


def footprint_iou(zone_footprint_enu: Polygon, points_enu: np.ndarray) -> float:
    """IoU between the manifest footprint and the convex hull of the aligned zone points (top view)."""
    if len(points_enu) < 3 or zone_footprint_enu.is_empty:
        return 0.0
    hull = MultiPoint(np.asarray(points_enu)[:, :2]).convex_hull
    if hull.is_empty or hull.area <= 0:
        return 0.0
    inter = zone_footprint_enu.intersection(hull).area
    union = zone_footprint_enu.union(hull).area
    return float(inter / union) if union > 0 else 0.0


def ground_tilt_deg(ground_points_enu: np.ndarray) -> float:
    """Angle between the best-fit plane normal of the ground points and +z (0 = level)."""
    p = np.asarray(ground_points_enu, dtype=np.float64)
    if len(p) < 3:
        return float("nan")
    c = p - p.mean(axis=0)
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    n = vt[-1]
    n = n if n[2] >= 0 else -n
    return float(np.degrees(np.arccos(np.clip(n[2], -1.0, 1.0))))


def scale_check(points_a: np.ndarray, points_b: np.ndarray, measured_m: float) -> dict:
    """Compare a tape-measured distance (notes.md) with the model distance between two picked points."""
    d = float(np.linalg.norm(np.asarray(points_a, dtype=np.float64) - np.asarray(points_b, dtype=np.float64)))
    return {
        "model_m": d,
        "measured_m": float(measured_m),
        "ratio": d / measured_m if measured_m else float("nan"),
    }


def surface_distance(
    points: np.ndarray,
    target_points: np.ndarray,
    target_normals: np.ndarray | None = None,
    max_m: float = 2.0,
) -> dict:
    """Distance stats from aligned zone points to the basemap surface.

    With target normals the distance is point-to-plane (|(p - q) . n| at the nearest sample), which
    stays meaningful when the target is sampled sparsely; otherwise plain nearest-neighbour distance.
    """
    tp = np.asarray(target_points)
    p = np.asarray(points)
    if len(tp) == 0 or len(p) == 0:
        return {"median_m": float("nan"), "p90_m": float("nan"), "within_ratio": 0.0}
    tree = cKDTree(tp)
    d, idx = tree.query(p, distance_upper_bound=max_m)
    ok = np.isfinite(d)
    if not ok.any():
        return {"median_m": float("nan"), "p90_m": float("nan"), "within_ratio": 0.0}
    if target_normals is not None:
        n = np.asarray(target_normals)[idx[ok]]
        d_ok = np.abs(np.einsum("ij,ij->i", p[ok] - tp[idx[ok]], n))
    else:
        d_ok = d[ok]
    return {
        "median_m": float(np.median(d_ok)),
        "p90_m": float(np.percentile(d_ok, 90)),
        "within_ratio": float(ok.mean()),
    }


def verdict(q: dict) -> list[str]:
    """Human-readable warnings for values over the proposed thresholds."""
    out = []
    if q.get("icp_rmse_m") is not None and q["icp_rmse_m"] > THRESHOLDS["icp_rmse_m"]:
        out.append(f"ICP RMSE {q['icp_rmse_m']:.2f} m > {THRESHOLDS['icp_rmse_m']} m")
    if (
        q.get("tilt_deg") is not None
        and not np.isnan(q["tilt_deg"])
        and q["tilt_deg"] > THRESHOLDS["tilt_deg"]
    ):
        out.append(f"기울기 {q['tilt_deg']:.2f}° > {THRESHOLDS['tilt_deg']}°")
    if q.get("footprint_iou") is not None and q["footprint_iou"] < THRESHOLDS["footprint_iou_min"]:
        out.append(f"footprint IoU {q['footprint_iou']:.2f} < {THRESHOLDS['footprint_iou_min']}")
    if q.get("icp_inlier_ratio") is not None and q["icp_inlier_ratio"] < THRESHOLDS["inlier_ratio_min"]:
        out.append(f"ICP inlier {q['icp_inlier_ratio']:.2f} < {THRESHOLDS['inlier_ratio_min']}")
    return out
