"""golmok-align: put a zone on the basemap (GPS prior -> ICP), record quality, re-check blur.

    golmok-align run --zone zones/z_.../v1 --basemap D:\\golmok_basemap\\yeonnam \\
        [--poses cameras.csv --gps gps_priors.csv] [--write]
    golmok-align check-blur Saved\\Screenshots\\Golmok\\spike_a --face-model ... --lp-model ...
    golmok-align compare --before v1/manifest.json --after v2/manifest.json

Pipeline (ARCHITECTURE §5 ⑦⑧):
    1. Zone collision mesh (zone-local) -> area ENU with the manifest transform (initial guess).
    2. Optional GPS prior: camera positions (RealityScan CSV, zone-local) vs GPS -> similarity; the
       rotation/translation replace the initial guess (scale is reported; --apply-scale rescales).
    3. ICP: wall samples against basemap building tiles, ground samples against terrain tiles.
    4. Metrics -> manifest.quality; new transform = correction (area ENU) composed with the old one.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from golmok_tools.zone import manifest as zm
from golmok_tools.zone import transform as zt

from . import icp as icp_mod
from . import meshio, metrics, poses, prior

MAX_POINTS_DEFAULT = 200_000


def _area_origin(basemap_manifest: dict) -> tuple[float, float, float]:
    o = basemap_manifest["origin"]
    return (
        float(o["lat"]),
        float(o["lon"]),
        float(o.get("height_ellipsoidal", o.get("height_orthometric", 0.0))),
    )


def split_wall_ground(
    samples: meshio.Samples, wall_max_nz: float = 0.5
) -> tuple[meshio.Samples, meshio.Samples]:
    """Points on near-vertical faces (walls) vs upward-facing faces (ground/roofs)."""
    nz = samples.normals[:, 2]
    wall = np.abs(nz) < wall_max_nz
    ground = nz >= 0.8
    return (
        meshio.Samples(samples.points[wall], samples.normals[wall]),
        meshio.Samples(samples.points[ground], samples.normals[ground]),
    )


def compose_new_transform(old_zone_t: np.ndarray, correction_area: np.ndarray, area_origin) -> np.ndarray:
    """zone-local -> ECEF after applying `correction_area` (4x4 in area ENU) on top of the old placement."""
    area = zt.enu_frame_matrix(*area_origin)
    return area @ correction_area @ zt.rigid_inverse(area) @ old_zone_t


def _polish_rigid(m: np.ndarray) -> np.ndarray:
    """Re-orthonormalise the rotation part (accumulated float error) so validate() passes."""
    u, _, vt = np.linalg.svd(m[:3, :3])
    r = u @ vt
    if np.linalg.det(r) < 0:
        u[:, -1] *= -1
        r = u @ vt
    out = np.eye(4)
    out[:3, :3] = r
    out[:3, 3] = m[:3, 3]
    return out


def run_align(args) -> tuple[dict, dict]:
    zone_dir = Path(args.zone)
    mpath = zone_dir / zm.MANIFEST_NAME if zone_dir.is_dir() else zone_dir
    zone_dir = mpath.parent
    d = zm.load(mpath)
    old_t = zt.from_row_major(d["transform"])

    bm_manifest, bm_buildings, bm_terrain = meshio.load_basemap(args.basemap, args.max_points)
    area_origin = _area_origin(bm_manifest)
    to_area_old = zt.zone_local_to_area_enu(old_t, area_origin)

    coll_uri = d["layers"]["collision"]["uri"]
    zone_mesh = meshio.load_mesh(zone_dir / coll_uri, axes=args.mesh_axes)
    zone_samples = meshio.sample_mesh(zone_mesh, args.max_points)
    report: dict = {
        "zone_id": d["zone_id"],
        "version": d["version"],
        "collision_mesh": coll_uri,
        "zone_points": len(zone_samples),
        "basemap": {
            "folder": str(args.basemap),
            "building_points": len(bm_buildings),
            "terrain_points": len(bm_terrain),
        },
        "area_origin": list(area_origin),
    }

    # -- step 2: GPS prior --------------------------------------------------------------------------
    correction = np.eye(4)  # in area ENU, applied on top of the old placement
    if args.poses and args.gps:
        cams = poses.read_realityscan_csv(args.poses)
        fixes = poses.read_gps_csv(args.gps)
        pairs = poses.join(cams, fixes)
        if len(pairs) < 3:
            raise SystemExit(f"GPS prior: 매칭된 카메라가 {len(pairs)}개 (3개 이상 필요)")
        cam_area = zt.apply(to_area_old, np.array([p.position for p, _ in pairs]))
        lat = np.array([f.lat for _, f in pairs])
        lon = np.array([f.lon for _, f in pairs])
        alt = np.array(
            [(f.alt if f.alt is not None else area_origin[2]) + args.gps_alt_offset for _, f in pairs]
        )
        gps_area = zt.lonlat_to_enu(lon, lat, alt, area_origin)
        sim = prior.fit_prior(
            cam_area, gps_area, with_scale=not args.already_georeferenced, inlier_m=args.gps_inlier_m
        )
        report["gps_prior"] = {
            "pairs": len(pairs),
            "inliers": int(sim.inliers.sum()),
            "rmse_m": sim.rmse,
            "scale": sim.scale,
            **icp_mod.decompose(sim.matrix()),
        }
        if args.apply_scale and abs(sim.scale - 1.0) > 1e-6:
            correction = sim.matrix()
        else:
            correction = np.eye(4)
            correction[:3, :3] = sim.rotation
            correction[:3, 3] = (
                sim.translation + (1 - sim.scale) * (sim.rotation @ cam_area.mean(axis=0)) * 0.0
            )
            # keep the prior's rotation and translation but not its scale (reported only)
            correction[:3, 3] = sim.translation
    elif args.poses or args.gps:
        raise SystemExit("--poses와 --gps는 함께 줘야 한다")

    # -- step 3: ICP ---------------------------------------------------------------------------------
    init = correction @ to_area_old
    zone_area = zt.apply(init, zone_samples.points)
    zone_n = zone_samples.normals @ init[:3, :3].T
    walls, ground = split_wall_ground(meshio.Samples(zone_area, zone_n))
    center = zone_area.mean(axis=0)
    radius = float(np.max(np.linalg.norm(zone_area[:, :2] - center[:2], axis=1))) + args.max_corr_m + 5.0
    b_near = meshio.crop(bm_buildings, center, radius)
    t_near = meshio.crop(bm_terrain, center, radius)

    icp_walls = None
    if len(walls) >= 10 and len(b_near) >= 10 and not args.no_walls:
        icp_walls = icp_mod.icp_point_to_plane(
            walls.points,
            b_near.points,
            b_near.normals,
            max_correspondence_m=args.max_corr_m,
            dof=args.dof,
            normal_agreement=0.5,
            src_normals=walls.normals,
        )
        report["icp_walls"] = {
            "rmse_m": icp_walls.rmse,
            "inlier_ratio": icp_walls.inlier_ratio,
            "iterations": icp_walls.iterations,
            "converged": icp_walls.converged,
            **icp_mod.decompose(icp_walls.transform),
        }
    icp_ground = None
    if args.ground and len(ground) >= 10 and len(t_near) >= 10:
        # After the wall ICP, only allow a vertical shift from the ground match (keeps walls aligned).
        base = np.eye(4) if icp_walls is None else icp_walls.transform
        g_pts = zt.apply(base, ground.points)
        icp_ground = icp_mod.icp_point_to_plane(
            g_pts,
            t_near.points,
            t_near.normals,
            max_correspondence_m=args.max_corr_m,
            dof=1,
        )
        report["icp_ground"] = {
            "rmse_m": icp_ground.rmse,
            "inlier_ratio": icp_ground.inlier_ratio,
            **icp_mod.decompose(icp_ground.transform),
        }

    total = np.eye(4)
    if icp_walls is not None:
        total = icp_walls.transform @ total
    if icp_ground is not None:
        g = np.eye(4)
        g[2, 3] = icp_ground.transform[2, 3]  # vertical only
        total = g @ total
    correction_total = total @ correction
    dec = icp_mod.decompose(correction_total)
    report["correction_area_enu"] = dec
    if dec["shift_norm_m"] > args.max_shift_m or abs(dec["yaw_deg"]) > args.max_yaw_deg:
        report["failed"] = (
            f"보정이 한계를 넘음: shift {dec['shift_norm_m']:.2f} m, yaw {dec['yaw_deg']:.2f}° "
            "(--max-shift-m/--max-yaw-deg)"
        )

    # -- step 4: metrics ----------------------------------------------------------------------------
    final_area = correction_total @ to_area_old
    pts_final = zt.apply(final_area, zone_samples.points)
    fp_enu = zm.footprint_enu(d["footprint_wgs84"], area_origin)
    walls_f, ground_f = split_wall_ground(
        meshio.Samples(pts_final, zone_samples.normals @ final_area[:3, :3].T)
    )
    quality = {
        "icp_rmse_m": None if icp_walls is None else round(icp_walls.rmse, 4),
        "icp_inlier_ratio": None if icp_walls is None else round(icp_walls.inlier_ratio, 4),
        "footprint_iou": round(metrics.footprint_iou(fp_enu, pts_final), 4),
        "tilt_deg": round(metrics.ground_tilt_deg(ground_f.points), 4) if len(ground_f) >= 3 else None,
        "wall_distance": metrics.surface_distance(walls_f.points, b_near.points, b_near.normals)
        if len(walls_f) and len(b_near)
        else None,
        "ground_distance": metrics.surface_distance(ground_f.points, t_near.points, t_near.normals)
        if len(ground_f) and len(t_near)
        else None,
        "aligned_by": "golmok-align",
        "aligned_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    if args.scale_check:
        a, b, meters = args.scale_check
        quality["scale_check"] = metrics.scale_check(a, b, meters)
    report["quality"] = quality
    report["warnings"] = metrics.verdict(quality)

    new_t = _polish_rigid(compose_new_transform(old_t, correction_total, area_origin))
    lat, lon, h = zt.ecef_to_geodetic(new_t[:3, 3])
    report["new_origin"] = {"lat": lat, "lon": lon, "height_ellipsoidal": h}
    report["old_origin"] = dict(d["origin"])

    if args.write and "failed" not in report:
        d["transform"] = zt.to_row_major(new_t)
        d["origin"] = {"lat": lat, "lon": lon, "height_ellipsoidal": h}
        d["origin_ecef"] = [float(v) for v in new_t[:3, 3]]
        q = d.setdefault("quality", {})
        q.update({k: v for k, v in quality.items() if k not in ("wall_distance", "ground_distance")})
        q["wall_distance_median_m"] = (
            None if not quality["wall_distance"] else quality["wall_distance"]["median_m"]
        )
        q["ground_distance_median_m"] = (
            None if not quality["ground_distance"] else quality["ground_distance"]["median_m"]
        )
        zm.save(d, mpath)
        report["written"] = str(mpath)
    write_report(zone_dir / "align_report.md", report)
    return d, report


def write_report(path: Path, r: dict) -> None:
    lines = [f"# 정합 리포트 — {r['zone_id']} v{r['version']}", ""]
    lines.append(f"- 충돌 메시: `{r['collision_mesh']}` ({r['zone_points']} 샘플)")
    b = r["basemap"]
    lines.append(
        f"- 베이스맵: `{b['folder']}` (건물 {b['building_points']}, 지형 {b['terrain_points']} 샘플)"
    )
    if "gps_prior" in r:
        g = r["gps_prior"]
        lines.append(
            f"- GPS prior: {g['inliers']}/{g['pairs']} 사용, RMSE {g['rmse_m']:.2f} m, scale {g['scale']:.4f}"
        )
    for key, label in (("icp_walls", "ICP 벽면"), ("icp_ground", "ICP 지면")):
        if key in r:
            i = r[key]
            lines.append(
                f"- {label}: RMSE {i['rmse_m']:.3f} m, inlier {i['inlier_ratio']:.2f}, "
                f"이동 {i['shift_norm_m']:.2f} m, yaw {i['yaw_deg']:.3f}°"
            )
    c = r["correction_area_enu"]
    lines.append(
        f"- 총 보정(area ENU): 이동 {c['shift_norm_m']:.3f} m {[round(v, 3) for v in c['shift_m']]}, "
        f"yaw {c['yaw_deg']:.3f}°, tilt {c['tilt_deg']:.3f}°"
    )
    q = r["quality"]
    lines += ["", "## 품질 지표", ""]
    lines.append("| ICP RMSE | inlier | footprint IoU | 기울기 | 벽 거리 중앙값 | 지면 거리 중앙값 |")
    lines.append("|---|---|---|---|---|---|")
    wd = q.get("wall_distance") or {}
    gd = q.get("ground_distance") or {}
    lines.append(
        f"| {q['icp_rmse_m']} | {q['icp_inlier_ratio']} | {q['footprint_iou']} | {q['tilt_deg']} | "
        f"{wd.get('median_m')} | {gd.get('median_m')} |"
    )
    if r["warnings"]:
        lines += ["", "**경고**"] + [f"- {w}" for w in r["warnings"]]
    if "failed" in r:
        lines += ["", f"**실패: {r['failed']}** — manifest를 고치지 않았다."]
    o, n = r["old_origin"], r["new_origin"]
    lines += ["", "## 원점", "", f"- 전: {o}", f"- 후: {n}"]
    if "written" in r:
        lines.append(f"- manifest 갱신: `{r['written']}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_run(args) -> int:
    _, report = run_align(args)
    print(json.dumps(report, ensure_ascii=False, indent=1, default=str))
    return 1 if "failed" in report else 0


def cmd_compare(args) -> int:
    a = zt.from_row_major(zm.load(args.before)["transform"])
    b = zt.from_row_major(zm.load(args.after)["transform"])
    # Express the 'after' placement in the 'before' zone frame: shift and yaw of the change.
    shift_zone = zt.rigid_inverse(a) @ np.append(b[:3, 3], 1.0)
    dec = icp_mod.decompose(zt.rigid_inverse(a) @ b)
    out = {"shift_in_before_frame_m": [float(v) for v in shift_zone[:3]], **dec}
    print(json.dumps(out, indent=1))
    return 0


def cmd_check_blur(args) -> int:
    from golmok_tools.imageio import is_supported, read_image, to_uint8
    from golmok_tools.privacy.detector import EgoBlurDetector, detect_scaled

    folder = Path(args.folder)
    files = sorted(p for p in folder.rglob("*") if p.is_file() and is_supported(p))
    if not files:
        print("이미지 없음")
        return 1
    try:
        dets = [
            EgoBlurDetector("face", args.face_model, args.threshold, 0.3, args.device),
            EgoBlurDetector("plate", args.lp_model, args.threshold, 0.3, args.device),
        ]
    except Exception as e:  # torch missing, model missing
        print(f"EgoBlur 모델을 열 수 없다: {e}\n모델 파일과 torch 설치를 확인한다(tools/README.md).")
        return 2
    hits = []
    for p in files:
        img = to_uint8(read_image(p))
        counts = {d.name: len(detect_scaled(d, img, args.detect_max_side)) for d in dets}
        if any(counts.values()):
            hits.append((p, counts))
        print(f"{p.name}: 얼굴 {counts['face']} 번호판 {counts['plate']}")
    print(f"\n{len(files)}장 중 검출 {len(hits)}장")
    for p, c in hits:
        print(f"  {p}: {c}")
    return 1 if hits else 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="golmok-align", description="Zone 정합(GPS prior → ICP)·품질 지표·블러 재검사"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Zone을 베이스맵에 정합하고 quality를 기록")
    r.add_argument("--zone", required=True, help="zones/<id>/v<n> 폴더 또는 manifest.json")
    r.add_argument("--basemap", required=True, help="golmok-basemap 출력 폴더")
    r.add_argument("--poses", help="RealityScan 카메라 CSV (#name,x,y,alt,...)")
    r.add_argument("--gps", help="golmok-blur의 gps_priors.csv")
    r.add_argument("--gps-alt-offset", type=float, default=0.0, help="GPS 고도(정표고)→타원체고 보정 m")
    r.add_argument("--gps-inlier-m", type=float, default=8.0)
    r.add_argument(
        "--already-georeferenced", action="store_true", help="RealityScan이 이미 지오레퍼런싱: 스케일 1 고정"
    )
    r.add_argument("--apply-scale", action="store_true", help="GPS prior의 스케일도 적용(기본: 리포트만)")
    r.add_argument("--mesh-axes", choices=meshio.AXES, default="gltf-yup", help="collision.glb 정점 축 규약")
    r.add_argument("--max-points", type=int, default=MAX_POINTS_DEFAULT)
    r.add_argument("--max-corr-m", type=float, default=2.0, help="ICP 대응 최대 거리")
    r.add_argument("--dof", type=int, choices=[4, 6], default=4, help="벽면 ICP 자유도(4=yaw+이동, 6=강체)")
    r.add_argument("--ground", action="store_true", help="지면 포인트를 지형 타일과 별도 ICP(수직 보정)")
    r.add_argument("--no-walls", action="store_true")
    r.add_argument("--max-shift-m", type=float, default=5.0)
    r.add_argument("--max-yaw-deg", type=float, default=5.0)
    r.add_argument(
        "--scale-check",
        nargs=3,
        metavar=("A", "B", "METERS"),
        type=_point_or_float,
        help="스케일 확인: zone-local 점 A 'x,y,z' 점 B 'x,y,z' 실측 m",
    )
    r.add_argument("--write", action="store_true", help="manifest transform/origin/quality 갱신")
    r.set_defaults(func=cmd_run)

    c = sub.add_parser("compare", help="두 manifest의 변환 차이")
    c.add_argument("--before", required=True)
    c.add_argument("--after", required=True)
    c.set_defaults(func=cmd_compare)

    b = sub.add_parser("check-blur", help="렌더 스크린샷에 EgoBlur 검출을 다시 돌려 누락 확인")
    b.add_argument("folder")
    b.add_argument("--face-model", required=True, type=Path)
    b.add_argument("--lp-model", required=True, type=Path)
    b.add_argument("--threshold", type=float, default=0.7, help="재검사는 낮은 임계값으로(기본 0.7)")
    b.add_argument("--detect-max-side", type=int, default=0)
    b.add_argument("--device", default="auto")
    b.set_defaults(func=cmd_check_blur)
    return ap


def _point_or_float(text: str):
    if "," in text:
        return [float(v) for v in text.split(",")]
    return float(text)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
