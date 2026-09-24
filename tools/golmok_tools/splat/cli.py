"""golmok-splat: 3DGS PLY inspect/crop/clean/transform and 3D Tiles (docs/runbooks/recon-postprocess.md).

golmok-splat inspect scene.ply
golmok-splat crop scene.ply --manifest zones/z_…/v1/manifest.json --margin-m 2 --out cropped.ply
golmok-splat clean cropped.ply --knn 16 --std 2.0 --min-opacity 0.02 --max-scale-m 1.0 --out clean.ply
golmok-splat transform clean.ply --matrix 1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1 --out moved.ply
golmok-splat tiles clean.ply --out tiles/ [--manifest …] [--max-splats 500000]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from . import ops, ply
from .tiles import write_tileset


def _floats(text: str, n: int, what: str) -> list[float]:
    try:
        vals = [float(x) for x in text.split(",")]
    except ValueError:
        raise argparse.ArgumentTypeError(f"{what}: 숫자 목록이 아니다: {text!r}") from None
    if len(vals) != n:
        raise argparse.ArgumentTypeError(f"{what}: 값 {n}개가 필요하다: {text!r}")
    return vals


def footprint_local(manifest: dict) -> np.ndarray:
    """Zone footprint (lon, lat) -> zone-local x, y through the manifest transform."""
    from golmok_tools.zone import manifest as zm
    from golmok_tools.zone import transform as zt

    poly = zm.footprint_polygon(manifest["footprint_wgs84"])
    h = manifest["origin"]["height_ellipsoidal"]
    m = zt.from_row_major(manifest["transform"])
    ecef = np.array([zt.geodetic_to_ecef(lat, lon, h) for lon, lat in poly.exterior.coords])
    return zt.ecef_to_enu(m, ecef)[:, :2]


def cmd_inspect(args) -> int:
    d = ply.read_ply(args.input)
    s = ops.stats(d)
    if args.json:
        print(json.dumps(s, indent=2))
        return 0
    print(f"splat {s['count']:,} · SH 차수 {s['sh_degree']}")
    if s["count"]:
        lo, hi = (np.round(b, 3).tolist() for b in s["bounds"])
        print(f"범위(m) {lo} ~ {hi}")
        print(f"opacity 백분위 {s['opacity_percentiles']}")
        print(f"최대 축 크기(m) 백분위 {s['max_scale_m_percentiles']}")
    extra = [n for n in s["properties"] if n not in ply.splat_dtype(s["sh_degree"], True).names]
    if extra:
        print(f"기타 속성: {extra}")
    return 0


def cmd_crop(args) -> int:
    d = ply.read_ply(args.input)
    if args.bbox:
        v = _floats(args.bbox, 6, "--bbox")
        out = ops.crop_bbox(d, v[:3], v[3:])
    elif args.manifest:
        from golmok_tools.zone import manifest as zm

        out = ops.crop_polygon(d, footprint_local(zm.load(args.manifest)), args.margin_m)
    else:
        print("ERROR --bbox 또는 --manifest가 필요하다")
        return 2
    ply.write_ply(out, args.out)
    print(f"{len(d):,} → {len(out):,} splat ({len(d) - len(out):,} 제거) → {args.out}")
    return 0


def cmd_clean(args) -> int:
    d = ply.read_ply(args.input)
    out, rep = ops.clean(
        d, knn=args.knn, std=args.std, min_opacity=args.min_opacity, max_scale_m=args.max_scale_m
    )
    ply.write_ply(out, args.out)
    print(json.dumps(rep, ensure_ascii=False))
    print(f"{rep['input']:,} → {rep['output']:,} splat → {args.out}")
    return 0


def cmd_transform(args) -> int:
    d = ply.read_ply(args.input)
    m = np.asarray(_floats(args.matrix, 16, "--matrix")).reshape(4, 4)  # row-major, like the zone manifest
    ply.write_ply(ops.transform(d, m), args.out)
    print(f"{len(d):,} splat 변환 → {args.out}")
    return 0


def cmd_tiles(args) -> int:
    d = ply.read_ply(args.input)
    root_transform = None
    if args.manifest:
        from golmok_tools.zone import manifest as zm
        from golmok_tools.zone import transform as zt

        root_transform = zt.from_row_major(zm.load(args.manifest)["transform"])
    rep = write_tileset(
        d,
        args.out,
        max_splats=args.max_splats,
        root_transform=root_transform,
        lod_scale_exp=args.lod_scale_exp,
        color_space=args.color_space,
    )
    print(f"splat {rep['splats']:,} → 타일 {rep['tiles']}개(깊이 {rep['depth']}) → {rep['tileset']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="golmok-splat", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("inspect", help="개수, 범위, opacity/scale 분포, SH 차수")
    p.add_argument("input", type=Path)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("crop", help="bbox 또는 zone footprint로 자르기")
    p.add_argument("input", type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--bbox", help="xmin,ymin,zmin,xmax,ymax,zmax (zone-local m)")
    p.add_argument("--manifest", type=Path, help="footprint_wgs84로 수평 자르기")
    p.add_argument("--margin-m", type=float, default=1.0, help="footprint 바깥 여유(m)")
    p.set_defaults(func=cmd_crop)

    p = sub.add_parser("clean", help="플로터·흐린·너무 큰 splat 제거")
    p.add_argument("input", type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--knn", type=int, default=16)
    p.add_argument("--std", type=float, default=2.0, help="평균 kNN 거리 > 평균 + std×표준편차면 제거 (0=끔)")
    p.add_argument("--min-opacity", type=float, help="예: 0.02")
    p.add_argument("--max-scale-m", type=float, help="가장 긴 축이 이보다 크면 제거(m)")
    p.set_defaults(func=cmd_clean)

    p = sub.add_parser("transform", help="4x4(행 우선) 적용: 위치·회전·크기·SH")
    p.add_argument("input", type=Path)
    p.add_argument("--matrix", required=True, help="16개, row-major (회전×균일 스케일 + 이동)")
    p.add_argument("--out", required=True, type=Path)
    p.set_defaults(func=cmd_transform)

    p = sub.add_parser("tiles", help="PLY → 3D Tiles 1.1 (glTF KHR_gaussian_splatting)")
    p.add_argument("input", type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--max-splats", type=int, default=500_000, help="타일당 최대 splat")
    p.add_argument("--manifest", type=Path, help="root.transform = zone transform(ECEF 배치)")
    p.add_argument("--lod-scale-exp", type=float, default=0.5, help="부모 타일 splat 확대 지수(0=끔)")
    p.add_argument(
        "--color-space", choices=["srgb_rec709_display", "lin_rec709_display"], default="srgb_rec709_display"
    )
    p.set_defaults(func=cmd_tiles)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (argparse.ArgumentTypeError, ValueError, FileNotFoundError) as e:
        print(f"ERROR {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
