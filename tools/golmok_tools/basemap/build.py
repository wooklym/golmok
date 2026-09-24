"""golmok-basemap: build background LOD1 buildings + terrain tiles for one area.

    golmok-basemap inspect --buildings AL_D010_11_….shp
    golmok-basemap build --buildings AL_D010_11_….shp --height-field A16 \\
        --dem dem\\*.tif --ortho ortho\\*.tif --center 37.5620,126.9250 --radius 1000 --out D:\\golmok_basemap\\yeonnam

Output (--out):
    manifest.json   origin, tiles, sources/attribution (read by the Unreal import script)
    tileset.json    3D Tiles 1.1 (review viewer / Cesium), same GLB files
    tiles/b_<ix>_<iy>.glb  buildings (TEXCOORD_0 wall/roof meters, TEXCOORD_1 = floor height, category)
    tiles/t_<ix>_<iy>.glb  terrain (orthophoto texture when --ortho is given)
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, box, shape

from .buildings import buildings_mesh, inspect_fields, load_buildings, set_elevations, shapefile_crs
from .geo import EnuFrame, Projector
from .gltf import write_glb
from .raster import DemSampler, OrthoSource
from .terrain import terrain_mesh

ATTRIBUTION = [
    "건물: 국토교통부 GIS건물통합정보 (공공누리 제1유형: 출처표시)",
    "지형·정사영상: 국토지리정보원",
]


def _expand(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in patterns or []:
        hits = sorted(glob.glob(p))
        out.extend(Path(h) for h in (hits or [p]))
    return out


def _bbox(p: np.ndarray) -> list[list[float]]:
    return [np.round(p.min(axis=0), 3).tolist(), np.round(p.max(axis=0), 3).tolist()]


def _parse_center(text: str) -> tuple[float, float]:
    lat, lon = (float(v) for v in text.split(","))
    return lat, lon


def _load_exclude(path: Path | None, projector: Projector) -> list[Polygon]:
    if not path:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    feats = data["features"] if data.get("type") == "FeatureCollection" else [data]
    polys = []
    for f in feats:
        g = shape(f.get("geometry", f))
        for p in getattr(g, "geoms", [g]):
            ll = np.asarray(p.exterior.coords)
            enu = projector.lonlat_to_enu(ll[:, 0], ll[:, 1], np.zeros(len(ll)))
            polys.append(Polygon(enu[:, :2]))
    return polys


def build(args) -> dict:
    lat, lon = _parse_center(args.center)
    dem_paths = _expand(args.dem)
    ortho_paths = _expand(args.ortho)
    out = Path(args.out)
    (out / "tiles").mkdir(parents=True, exist_ok=True)

    # Origin height = DEM at the center (orthometric) + geoid offset -> ellipsoidal.
    r = args.radius
    probe = EnuFrame(lon, lat, 0.0)
    probe_proj = Projector("EPSG:4326", probe)
    corner_lon, corner_lat = probe_proj.enu_to_lonlat(np.array([-r, r, r, -r]), np.array([-r, -r, r, r]))
    dem = DemSampler(
        dem_paths,
        corner_lon,
        corner_lat,
        margin=args.tile_size,
        crs_override=getattr(args, "raster_crs", None),
    )
    h0 = float(dem.sample_lonlat(np.array([lon]), np.array([lat]))[0])
    frame = EnuFrame(lon, lat, h0 + args.geoid_offset)

    src_crs = shapefile_crs(Path(args.buildings), args.src_crs)
    projector = Projector(src_crs, frame, args.geoid_offset)
    ll_proj = Projector("EPSG:4326", frame, args.geoid_offset)

    def ground_z(e, n):
        lo, la = ll_proj.enu_to_lonlat(e, n)
        return ll_proj.lonlat_to_enu(lo, la, dem.sample_lonlat(lo, la))[..., 2]

    area = box(-r, -r, r, r)
    exclude = _load_exclude(args.exclude, ll_proj)
    buildings = load_buildings(
        Path(args.buildings),
        projector,
        area,
        encoding=args.encoding,
        height_field=args.height_field,
        floors_field=args.floors_field,
        usage_field=args.usage_field,
        id_field=args.id_field,
        exclude_enu=exclude,
    )
    set_elevations(buildings, ground_z)
    ortho = OrthoSource(ortho_paths, getattr(args, "raster_crs", None)) if ortho_paths else None

    t = args.tile_size
    n_tiles = int(np.ceil(2 * r / t))
    x_min = -n_tiles * t / 2
    by_tile: dict[tuple[int, int], list] = {}
    for b in buildings:
        c = b.footprint.centroid
        key = (int((c.x - x_min) // t), int((c.y - x_min) // t))
        by_tile.setdefault(key, []).append(b)

    tiles, children = [], []
    for ix in range(n_tiles):
        for iy in range(n_tiles):
            x0, y0 = x_min + ix * t, x_min + iy * t
            tb = by_tile.get((ix, iy), [])
            contents, entry = (
                [],
                {
                    "id": f"{ix}_{iy}",
                    "ix": ix,
                    "iy": iy,
                    "center_enu": [x0 + t / 2, y0 + t / 2],
                    "buildings": None,
                    "terrain": None,
                    "n_buildings": len(tb),
                },
            )
            z_vals = []
            if not args.no_terrain:
                tm = terrain_mesh(
                    ll_proj,
                    dem,
                    x0,
                    y0,
                    t,
                    args.terrain_spacing,
                    ortho,
                    args.texture_size,
                    name=f"terrain_{ix}_{iy}",
                )
                uri = f"tiles/t_{ix}_{iy}.glb"
                write_glb(out / uri, [tm], {"golmok": {"kind": "terrain", "tile": entry["id"]}})
                entry["terrain"] = uri
                entry["terrain_bbox_enu"] = _bbox(tm.positions)
                contents.append({"uri": uri})
                z_vals += [tm.positions[:, 2].min(), tm.positions[:, 2].max()]
            if tb:
                bm = buildings_mesh(tb, name=f"buildings_{ix}_{iy}")
                uri = f"tiles/b_{ix}_{iy}.glb"
                write_glb(out / uri, [bm], {"golmok": {"kind": "buildings", "tile": entry["id"]}})
                entry["buildings"] = uri
                entry["buildings_bbox_enu"] = _bbox(bm.positions)
                contents.append({"uri": uri})
                z_vals += [bm.positions[:, 2].min(), bm.positions[:, 2].max()]
            if not contents:
                continue
            zmin, zmax = float(min(z_vals)), float(max(z_vals))
            children.append(
                {
                    "boundingVolume": {
                        "box": [
                            x0 + t / 2,
                            y0 + t / 2,
                            (zmin + zmax) / 2,
                            t / 2,
                            0,
                            0,
                            0,
                            t / 2,
                            0,
                            0,
                            0,
                            max((zmax - zmin) / 2, 1.0),
                        ]
                    },
                    "geometricError": 0.0,
                    "contents": contents,
                }
            )
            tiles.append(entry)

    if children:
        zs = [c["boundingVolume"]["box"][2] for c in children]
        hz = [c["boundingVolume"]["box"][11] for c in children]
        zmin = min(z - h for z, h in zip(zs, hz))
        zmax = max(z + h for z, h in zip(zs, hz))
    else:
        zmin, zmax = -1.0, 1.0
    half = n_tiles * t / 2
    tileset = {
        "asset": {"version": "1.1", "generator": "golmok-basemap"},
        "geometricError": 2 * half,
        "root": {
            "transform": frame.transform_matrix(),
            "boundingVolume": {
                "box": [0, 0, (zmin + zmax) / 2, half, 0, 0, 0, half, 0, 0, 0, max((zmax - zmin) / 2, 1.0)]
            },
            "geometricError": half,
            "refine": "ADD",
            "children": children,
        },
    }
    (out / "tileset.json").write_text(json.dumps(tileset, indent=1), encoding="utf-8")

    n_est = sum(1 for b in buildings if b.estimated)
    manifest = {
        "format": "golmok-basemap/1",
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "origin": {
            "lat": lat,
            "lon": lon,
            "height_orthometric": h0,
            "geoid_offset": args.geoid_offset,
            "height_ellipsoidal": h0 + args.geoid_offset,
        },
        "frame": "ENU meters (x=east, y=north, z=up); GLB stores (east, up, -north)",
        "radius_m": r,
        "tile_size_m": t,
        "terrain_spacing_m": args.terrain_spacing,
        "buildings": {
            "count": len(buildings),
            "height_estimated": n_est,
            "fields": {
                "height": args.height_field,
                "floors": args.floors_field,
                "usage": args.usage_field,
                "id": args.id_field,
            },
            "source_crs": src_crs.to_string(),
        },
        "sources": {
            "buildings": str(args.buildings),
            "dem": [str(p) for p in dem_paths],
            "ortho": [str(p) for p in ortho_paths],
        },
        "attribution": ATTRIBUTION,
        "tiles": tiles,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="golmok-basemap", description="배경 베이스맵(LOD1 건물 + 지형) 타일 빌더"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    ins = sub.add_parser("inspect", help="SHP 필드·좌표계 확인")
    ins.add_argument("--buildings", type=Path, required=True)
    ins.add_argument("--encoding", default="cp949")

    b = sub.add_parser("build", help="타일 생성")
    b.add_argument("--buildings", type=Path, required=True, help="건물 SHP (GIS건물통합정보)")
    b.add_argument("--dem", nargs="+", required=True, help="DEM GeoTIFF/IMG (여러 도엽·glob 가능)")
    b.add_argument("--ortho", nargs="*", default=[], help="정사영상 GeoTIFF (선택)")
    b.add_argument("--center", required=True, help="중심 위도,경도 (예: 37.5620,126.9250)")
    b.add_argument("--radius", type=float, default=1000.0, help="중심에서 반경(m), 정사각형 영역")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--height-field", required=True, help="높이(m) 필드명 — inspect로 확인")
    b.add_argument("--floors-field", help="지상층수 필드명")
    b.add_argument("--usage-field", help="용도명 필드명")
    b.add_argument("--id-field", help="건물 고유 ID 필드명")
    b.add_argument("--src-crs", help=".prj가 없을 때 좌표계 (예: EPSG:5174)")
    b.add_argument("--raster-crs", help="DEM/정사영상에 좌표계 정보가 없을 때 (예: EPSG:5186)")
    b.add_argument("--encoding", default="cp949")
    b.add_argument("--tile-size", type=float, default=250.0)
    b.add_argument("--terrain-spacing", type=float, default=5.0)
    b.add_argument("--texture-size", type=int, default=4096)
    b.add_argument(
        "--geoid-offset",
        type=float,
        default=0.0,
        help="지오이드고(m): 정표고→타원체고. UE 정적 임포트에는 영향 없음, Cesium 정렬 시 필요",
    )
    b.add_argument("--exclude", type=Path, help="제외할 플레이 구역 GeoJSON(경위도)")
    b.add_argument("--no-terrain", action="store_true")

    args = ap.parse_args(argv)
    if args.cmd == "inspect":
        print(inspect_fields(args.buildings, args.encoding))
        return 0
    manifest = build(args)
    bl = manifest["buildings"]
    print(
        f"건물 {bl['count']}동 (높이 추정 {bl['height_estimated']}동), 타일 {len(manifest['tiles'])}개 → {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
