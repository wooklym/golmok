"""golmok-zone: create, check, index and version zone manifests (docs/spec/zone-manifest.md).

    golmok-zone init --id z_yeonnam_alley_001 --kind exterior --origin 37.5620,126.9250,50 \\
        --footprint fp.geojson --out zones/z_yeonnam_alley_001/v1
    golmok-zone validate zones/z_yeonnam_alley_001/v1/manifest.json [--check-files]
    golmok-zone index build --zones-root zones --out index
    golmok-zone exclude --zones-root zones --out exclude.geojson [--buffer-m 0.75]
    golmok-zone transform zones/.../manifest.json --enu 10,0,0 [--area-origin 37.56,126.92,40]
    golmok-zone bump zones/z_yeonnam_alley_001/v1/manifest.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np

from . import manifest as zm
from . import transform
from .exclude import DEFAULT_BUFFER_M, build_exclude
from .index import build_index, write_index


def _floats(text: str, n_min: int, n_max: int, what: str) -> list[float]:
    try:
        vals = [float(v) for v in text.split(",")]
    except ValueError:
        raise argparse.ArgumentTypeError(f"{what}: 숫자 목록이 아니다: {text!r}") from None
    if not n_min <= len(vals) <= n_max:
        raise argparse.ArgumentTypeError(f"{what}: 값 {n_min}~{n_max}개가 필요하다: {text!r}")
    return vals


def _print_report(rep: zm.Report, label: str) -> None:
    for e in rep.errors:
        print(f"ERROR {e}")
    for w in rep.warnings:
        print(f"WARN  {w}")
    print(f"{label}: {'OK' if rep.ok else 'FAIL'} (오류 {len(rep.errors)}, 경고 {len(rep.warnings)})")


def cmd_init(args) -> int:
    lat, lon, *rest = _floats(args.origin, 2, 3, "--origin")
    h = rest[0] if rest else 0.0
    if not rest:
        print("WARN  --origin에 높이가 없어 타원체고 0 m로 둔다(서울 지오이드고 약 +23 m, 정합 후 갱신)")
    if not zm.ZONE_ID_RE.match(args.id):
        print(f"ERROR --id {args.id!r}: 형식 z_<소문자·숫자>[_...]")
        return 2
    if args.kind == "interior" and not args.parent:
        print("ERROR interior zone은 --parent <exterior zone id>가 필요하다")
        return 2
    out = Path(args.out)
    if out.name.startswith("v") and zm.VERSION_DIR_RE.match(out.name) and out.name != "v1":
        print(f"ERROR init은 v1을 만든다. 새 버전은 bump를 쓴다: {out}")
        return 2
    path = out / zm.MANIFEST_NAME
    if path.exists() and not args.force:
        print(f"ERROR 이미 있다: {path} (--force로 덮어쓰기)")
        return 2
    footprint = zm.read_footprint_file(args.footprint)
    m = zm.new_manifest(
        args.id,
        args.kind,
        lat,
        lon,
        h,
        footprint,
        yaw_deg=args.yaw,
        parent_zone=args.parent if args.kind == "interior" else None,
        priority=args.priority,
    )
    d = m.to_dict()
    if args.capture:
        d["sources"] = [{"capture_id": c} for c in args.capture]
    zm.save(d, path)
    print(f"작성: {path}")
    rep = zm.check(d, path)
    _print_report(rep, "validate")
    return 0 if rep.ok else 1


def cmd_validate(args) -> int:
    worst = 0
    for p in args.manifest:
        try:
            d = zm.load(p)
        except (OSError, json.JSONDecodeError) as e:
            print(f"ERROR {p}: {e}")
            worst = 1
            continue
        rep = zm.check(d, p, check_files=args.check_files)
        _print_report(rep, str(p))
        if not rep.ok or (args.strict and rep.warnings):
            worst = 1
    return worst


def cmd_index_build(args) -> int:
    problems: list[str] = []
    zones, cells = build_index(args.zones_root, problems)
    for p in problems:
        print(f"WARN  {p}")
    written = write_index(zones, cells, args.out)
    print(f"zone {len(zones['zones'])}개, 셀 {len(cells)}개 → {args.out} ({len(written)} 파일)")
    return 1 if (args.strict and problems) else 0


def cmd_exclude(args) -> int:
    fc, problems = build_exclude(args.zones_root, args.buffer_m)
    for p in problems:
        print(f"WARN  {p}")
    out = zm.write_json(fc, args.out)
    n = sum(len(f["properties"]["zone_ids"]) for f in fc["features"])
    print(f"exterior zone {n}개 → 폴리곤 {len(fc['features'])}개 (buffer {args.buffer_m} m) → {out}")
    return 1 if (args.strict and problems) else 0


def transform_report(d: dict, enu: list[float], area_origin: list[float] | None = None) -> dict:
    m = transform.from_row_major(d["transform"])
    ecef = transform.enu_to_ecef(m, enu)
    lat, lon, h = transform.ecef_to_geodetic(ecef)
    out = {
        "enu_m": list(enu),
        "ecef_m": ecef.tolist(),
        "lat": lat,
        "lon": lon,
        "height_ellipsoidal": h,
        "ue_zone_local_cm": transform.enu_to_ue(enu).tolist(),
    }
    if area_origin is not None:
        to_area = transform.zone_local_to_area_enu(m, tuple(area_origin))
        area_enu = transform.apply(to_area, enu)
        out["area_origin"] = list(area_origin)
        out["area_enu_m"] = area_enu.tolist()
        out["ue_area_cm"] = transform.enu_to_ue(area_enu).tolist()
        out["ue_actor_matrix"] = transform.ue_actor_matrix(to_area).tolist()
    return out


def cmd_transform(args) -> int:
    d = zm.load(args.manifest)
    enu = _floats(args.enu, 3, 3, "--enu")
    area = _floats(args.area_origin, 3, 3, "--area-origin") if args.area_origin else None
    rep = transform_report(d, enu, area)
    if args.json:
        print(json.dumps(rep, indent=2))
        return 0
    np.set_printoptions(precision=6, suppress=True)
    print(f"zone-local ENU (m)   : {rep['enu_m']}")
    print(f"ECEF (m)             : {[round(v, 4) for v in rep['ecef_m']]}")
    print(f"lat, lon, h          : {rep['lat']:.9f}, {rep['lon']:.9f}, {rep['height_ellipsoidal']:.4f}")
    print(f"UE zone-local (cm)   : {[round(v, 2) for v in rep['ue_zone_local_cm']]}  (X=east, Y=south, Z=up)")
    if area:
        print(f"area ENU (m)         : {[round(v, 4) for v in rep['area_enu_m']]}  (origin {area})")
        print(f"UE level (cm)        : {[round(v, 2) for v in rep['ue_area_cm']]}")
    return 0


def cmd_bump(args) -> int:
    src = Path(args.manifest)
    d = zm.load(src)
    vdir = src.parent
    m = zm.VERSION_DIR_RE.match(vdir.name)
    if not m or int(m.group(1)) != d["version"] or vdir.parent.name != d["zone_id"]:
        print(f"ERROR 경로가 <zone_id>/v<version>/manifest.json 규약과 다르다: {src}")
        return 2
    versions = [
        int(mm.group(1))
        for p in vdir.parent.iterdir()
        if p.is_dir() and (mm := zm.VERSION_DIR_RE.match(p.name))
    ]
    new = max(versions) + 1
    if new != d["version"] + 1:
        print(f"WARN  v{d['version']}보다 새 버전(v{max(versions)})이 있다. v{new}로 만든다")
    dst = vdir.parent / f"v{new}"
    shutil.copytree(vdir, dst)  # fails if dst exists: versions are immutable
    d["version"] = new
    q = d.setdefault("quality", {})
    q["reviewed_by"] = None  # a new version needs its own review
    q["reviewed_at"] = None
    zm.save(d, dst / zm.MANIFEST_NAME)
    print(f"{vdir.name} → {dst.name}: {dst / zm.MANIFEST_NAME}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="golmok-zone", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="새 zone v1 manifest 작성")
    p.add_argument("--id", required=True, help="z_<지역>_<이름>_<번호>, 예: z_yeonnam_alley_001")
    p.add_argument("--kind", choices=["exterior", "interior"], required=True)
    p.add_argument("--origin", required=True, help="lat,lon[,타원체고 m] — zone-local (0,0,0)")
    p.add_argument("--footprint", required=True, type=Path, help="GeoJSON Polygon(경위도)")
    p.add_argument("--yaw", type=float, default=0.0, help="zone +x의 방향, 동쪽에서 반시계(도)")
    p.add_argument("--parent", help="interior일 때 exterior zone id")
    p.add_argument("--priority", type=int, default=0)
    p.add_argument("--capture", action="append", help="촬영 ID(captures/INDEX.md), 여러 번 가능")
    p.add_argument("--out", required=True, type=Path, help="zones/<id>/v1 폴더")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("validate", help="스키마 + 의미 검사")
    p.add_argument("manifest", nargs="+", type=Path)
    p.add_argument("--check-files", action="store_true", help="참조 파일 존재·blockers 스키마까지 검사")
    p.add_argument("--strict", action="store_true", help="경고도 실패로")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("index", help="Zone Index")
    isub = p.add_subparsers(dest="index_cmd", required=True)
    b = isub.add_parser("build", help="zones.json + cells/<z>_<x>_<y>.json")
    b.add_argument("--zones-root", required=True, type=Path)
    b.add_argument("--out", required=True, type=Path)
    b.add_argument("--strict", action="store_true", help="건너뛴 zone이 있으면 실패")
    b.set_defaults(func=cmd_index_build)

    p = sub.add_parser("exclude", help="golmok-basemap --exclude용 GeoJSON")
    p.add_argument("--zones-root", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--buffer-m", type=float, default=DEFAULT_BUFFER_M, help="footprint 바깥 확장(m, ≥0)")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=cmd_exclude)

    p = sub.add_parser("transform", help="zone-local ENU 점 → ECEF, 경위도, UE cm")
    p.add_argument("manifest", type=Path)
    p.add_argument("--enu", required=True, help="x,y,z (m, zone-local)")
    p.add_argument("--area-origin", help="lat,lon,h — 레벨(CesiumGeoreference) 원점 기준 좌표도 출력")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_transform)

    p = sub.add_parser("bump", help="새 version 폴더로 복사(불변 버전)")
    p.add_argument("manifest", type=Path)
    p.set_defaults(func=cmd_bump)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (argparse.ArgumentTypeError, ValueError, FileNotFoundError, FileExistsError) as e:
        print(f"ERROR {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
