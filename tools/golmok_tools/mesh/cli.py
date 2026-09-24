"""golmok-mesh: RealityScan mesh -> zone chunks, collision, blockers (docs/runbooks/recon-postprocess.md).

golmok-mesh inspect alley.obj
golmok-mesh chunk alley.obj --size 15 --out zones/z_…/v1/visual --manifest zones/z_…/v1/manifest.json
golmok-mesh collision alley.obj --out zones/z_…/v1/collision.glb --manifest zones/z_…/v1/manifest.json
golmok-mesh blockers add zones/z_…/v1/blockers.json --center 3,9.8,1.5 --normal 0,-1,0 \\
        --size 3,2.4 --kind glass
golmok-mesh blockers build zones/z_…/v1/blockers.json --manifest zones/z_…/v1/manifest.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

from . import blockers as bl
from . import chunk as ch
from . import collision as col
from .objio import read_mesh, stats


def _vec(text: str, n: int, what: str) -> list[float]:
    try:
        vals = [float(x) for x in text.split(",")]
    except ValueError:
        raise argparse.ArgumentTypeError(f"{what}: 숫자 목록이 아니다: {text!r}") from None
    if len(vals) != n:
        raise argparse.ArgumentTypeError(f"{what}: 값 {n}개가 필요하다: {text!r}")
    return vals


def _rel_uri(path: Path, manifest: Path) -> str:
    rel = os.path.relpath(Path(path).resolve(), manifest.parent.resolve()).replace(os.sep, "/")
    if rel.startswith(".."):
        raise ValueError(f"{path}는 zone 버전 폴더({manifest.parent}) 안에 있어야 한다")
    return rel


def _load_manifest(path: Path) -> dict:
    from golmok_tools.zone import manifest as zm

    return zm.load(path)


def _save_manifest(d: dict, path: Path) -> None:
    from golmok_tools.zone import manifest as zm

    zm.save(d, path)


def centerline_local(geojson_path: Path, manifest: dict) -> np.ndarray:
    """LineString (lon, lat) -> zone-local x, y via the manifest transform."""
    from golmok_tools.zone import transform as zt

    data = json.loads(Path(geojson_path).read_text(encoding="utf-8"))
    if data.get("type") == "FeatureCollection":
        data = data["features"][0]
    if data.get("type") == "Feature":
        data = data["geometry"]
    if data.get("type") != "LineString":
        raise ValueError(f"{geojson_path}: LineString이 필요하다, {data.get('type')}")
    h = manifest["origin"]["height_ellipsoidal"]
    m = zt.from_row_major(manifest["transform"])
    ecef = np.array([zt.geodetic_to_ecef(lat, lon, h) for lon, lat, *_ in data["coordinates"]])
    return zt.ecef_to_enu(m, ecef)[:, :2]


def cmd_inspect(args) -> int:
    mesh = read_mesh(args.input, up=args.up)
    s = stats(mesh)
    if args.json:
        print(json.dumps(s, indent=2, ensure_ascii=False))
        return 0
    lo, hi = s["bounds_enu"]
    print(f"면 {s['faces']:,} · 정점 {s['vertices']:,} · UV {s['uvs']:,} · 노멀 {s['normals']:,}")
    lo, hi, size = (np.round(x, 2).tolist() for x in (lo, hi, s["size_m"]))
    print(f"범위(m) {lo} ~ {hi}  크기 {size}")
    print(f"면적 {s['area_m2']:.1f} m², 위를 향한 면 {s['up_facing_ratio'] * 100:.1f}%")
    print(f"머티리얼 {len(s['materials'])}: {', '.join(s['materials'][:10])}")
    print(f"UDIM 타일: {s['udim_tiles'] or '없음'}")
    print(f"경계 에지 {s['boundary_edges']:,} · 비매니폴드 에지 {s['non_manifold_edges']:,}")
    return 0


def cmd_chunk(args) -> int:
    mesh = read_mesh(args.input, up=args.up)
    manifest_doc = _load_manifest(args.manifest) if args.manifest else None
    if args.along:
        if manifest_doc is None:
            print("ERROR --along은 경위도 중심선을 zone-local로 바꾸려고 --manifest가 필요하다")
            return 2
        chunks = ch.polyline_chunks(mesh, centerline_local(args.along, manifest_doc), args.size)
    else:
        chunks = ch.grid_chunks(mesh, args.size)
    doc = ch.write_chunks(mesh, chunks, args.out, source=str(args.input))
    path = ch.save_chunk_manifest(doc, args.out)
    for e in doc["chunks"]:
        print(f"{e['id']}: {e['tris']:,} tris, UDIM {e['udim_tiles'] or '-'}")
    print(f"청크 {len(doc['chunks'])}개, 총 {doc['total_tris']:,} tris → {args.out} ({path.name})")
    big = [e["id"] for e in doc["chunks"] if e["tris"] > args.warn_tris]
    if big:
        print(f"WARN  {args.warn_tris:,} tris 초과 청크: {big} (--size를 줄이는 것을 고려)")
    if args.manifest:
        ch.update_zone_manifest(args.manifest, doc, args.out)
        print(f"manifest 갱신: layers.visual.chunks ({args.manifest})")
    return 0


def _collision_one(mesh, args):
    return col.build_collision(
        mesh,
        min_component_m2=args.min_component_m2,
        fill=args.fill_holes,
        snap=args.snap_ground,
        snap_cell=args.snap_cell,
        snap_tol=args.snap_tol,
        target_tris=None if args.ratio else args.target_tris,
        ratio=args.ratio,
    )


def _print_report(rep: col.CollisionReport, label: str) -> None:
    print(
        f"{label}: {rep.input_faces:,} → {rep.output_faces:,} tris · 작은 조각 {rep.removed_components}개"
        f"({rep.removed_faces:,} 면) 제거 · 구멍 채움 {rep.filled_faces}"
        f" · 바닥 스냅 {rep.snapped_vertices:,} 정점"
        f"({len(rep.ground_planes)} 셀) · 위를 향한 면 {rep.up_facing_ratio * 100:.1f}%"
    )


def cmd_collision(args) -> int:
    out = Path(args.out)
    v, f, report = _collision_one(read_mesh(args.input, up=args.up), args)
    _print_report(report, "collision")
    out.parent.mkdir(parents=True, exist_ok=True)
    col.write_collision_glb(out, v, f)
    print(f"작성: {out} ({len(f):,} tris)")
    entries = []
    if args.per_chunk:
        # Split the finished collision mesh (not the chunks' meshes): cleaning/decimating whole keeps
        # objects that cross chunk borders intact and makes chunk seams match exactly.
        cdoc = json.loads((Path(args.per_chunk) / ch.CHUNK_MANIFEST).read_text(encoding="utf-8"))
        parts = col.split_by_bboxes(v, f, [e["bbox_enu"] for e in cdoc["chunks"]])
        for e, (cv, cf) in zip(cdoc["chunks"], parts, strict=True):
            if not len(cf):
                continue
            p = out.parent / "collision" / f"{e['id']}.glb"
            p.parent.mkdir(parents=True, exist_ok=True)
            col.write_collision_glb(p, cv, cf, name=f"collision_{e['id']}")
            lo, hi = cv.min(axis=0), cv.max(axis=0)
            entries.append(
                {"id": e["id"], "path": p, "bbox_enu": [lo.round(4).tolist(), hi.round(4).tolist()]}
            )
        print(f"청크별 충돌 {len(entries)}개 → {out.parent / 'collision'}")
    if args.report:
        Path(args.report).write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    if args.manifest:
        mpath = Path(args.manifest)
        d = _load_manifest(mpath)
        layer = {"format": "glb", "uri": _rel_uri(out, mpath)}
        if entries:
            layer["chunks"] = [
                {"id": e["id"], "uri": _rel_uri(e["path"], mpath), "bbox_enu": e["bbox_enu"]} for e in entries
            ]
        d["layers"]["collision"] = layer
        _save_manifest(d, mpath)
        print(f"manifest 갱신: layers.collision ({mpath})")
    return 0


def cmd_blockers_add(args) -> int:
    doc = bl.load(args.file)
    bl.add_plane(
        doc,
        _vec(args.center, 3, "--center"),
        _vec(args.normal, 3, "--normal"),
        _vec(args.size, 2, "--size"),
        args.kind,
        args.id,
    )
    bl.save(doc, args.file)
    print(f"추가: {doc['planes'][-1]['id']} → {args.file} (총 {len(doc['planes'])}개)")
    return 0


def cmd_blockers_build(args) -> int:
    from golmok_tools.zone import schema

    doc = bl.load(args.file)
    errors = schema.validate_blockers(doc)
    if errors:
        for e in errors:
            print(f"ERROR {e}")
        return 1
    out = Path(args.out) if args.out else Path(args.file).with_suffix(".glb")
    bl.write_blockers_glb(doc, out, thickness=args.thickness)
    print(f"blocker {len(doc['planes'])}개 → {out} (두께 {args.thickness * 100:.0f} cm)")
    if args.manifest:
        mpath = Path(args.manifest)
        d = _load_manifest(mpath)
        d["layers"]["blockers"] = {"uri": _rel_uri(Path(args.file), mpath)}
        _save_manifest(d, mpath)
        print(f"manifest 갱신: layers.blockers ({mpath})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="golmok-mesh", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    up_help = "입력 축: z(zone-local 그대로, OBJ 기본) 또는 y(glTF, GLB 기본)"

    p = sub.add_parser("inspect", help="메시 통계")
    p.add_argument("input", type=Path)
    p.add_argument("--up", choices=["y", "z"], help=up_help)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("chunk", help="청크 분할(OBJ+MTL, UV·머티리얼·UDIM 보존)")
    p.add_argument("input", type=Path)
    p.add_argument("--out", required=True, type=Path, help="청크 폴더(보통 zones/<id>/v<N>/visual)")
    p.add_argument("--size", type=float, default=15.0, help="격자 한 변 또는 중심선 구간 길이(m)")
    p.add_argument("--along", type=Path, help="골목 중심선 GeoJSON LineString(경위도) — 구간 분할")
    p.add_argument("--manifest", type=Path, help="zone manifest.json: layers.visual.chunks 갱신")
    p.add_argument("--warn-tris", type=int, default=15_000_000, help="청크당 tri 경고 기준")
    p.add_argument("--up", choices=["y", "z"], help=up_help)
    p.set_defaults(func=cmd_chunk)

    p = sub.add_parser("collision", help="충돌 메시 GLB")
    p.add_argument("input", type=Path)
    p.add_argument("--out", required=True, type=Path, help="collision.glb")
    p.add_argument(
        "--per-chunk",
        type=Path,
        help="chunk 결과 폴더: 완성된 충돌 메시를 청크 영역별 collision/<id>.glb로도 나눔",
    )
    p.add_argument("--min-component-m2", type=float, default=1.0, help="이보다 작은 연결요소 제거")
    p.add_argument("--fill-holes", action="store_true")
    p.add_argument("--snap-ground", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--snap-cell", type=float, default=10.0, help="바닥 평면을 맞추는 수평 셀 크기(m)")
    p.add_argument("--snap-tol", type=float, default=0.05, help="평면에서 이 거리 안의 정점만 투영(m)")
    p.add_argument("--target-tris", type=int, default=30000)
    p.add_argument("--ratio", type=float, help="목표 대신 비율(0~1)")
    p.add_argument("--manifest", type=Path, help="zone manifest.json: layers.collision 갱신")
    p.add_argument("--report", type=Path, help="처리 통계 JSON")
    p.add_argument("--up", choices=["y", "z"], help=up_help)
    p.set_defaults(func=cmd_collision)

    p = sub.add_parser("blockers", help="유리·접근 금지 평면")
    bsub = p.add_subparsers(dest="blockers_cmd", required=True)
    a = bsub.add_parser("add", help="평면 추가")
    a.add_argument("file", type=Path, help="blockers.json (없으면 만든다)")
    a.add_argument("--center", required=True, help="x,y,z (zone-local m)")
    a.add_argument("--normal", required=True, help="nx,ny,nz")
    a.add_argument("--size", required=True, help="폭,높이 (m)")
    a.add_argument("--kind", choices=["glass", "no_entry"], required=True)
    a.add_argument("--id")
    a.set_defaults(func=cmd_blockers_add)
    b = bsub.add_parser("build", help="blockers.json → 얇은 박스 GLB")
    b.add_argument("file", type=Path)
    b.add_argument("--out", type=Path, help="기본: blockers.glb")
    b.add_argument("--thickness", type=float, default=bl.THICKNESS_M)
    b.add_argument("--manifest", type=Path, help="zone manifest.json: layers.blockers 갱신")
    b.set_defaults(func=cmd_blockers_build)
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
