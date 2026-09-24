"""Building footprints (GIS건물통합정보 SHP or similar) -> LOD1 extruded meshes in the ENU frame.

Attribute column names are not hard-coded: run `golmok-basemap inspect` on the real file and pass
--height-field / --floors-field / --usage-field / --id-field. When the height is missing it is
estimated from the floor count, and failing that a 2-floor default is used (flagged `estimated`).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import mapbox_earcut as earcut
import numpy as np
import shapefile
from pyproj import CRS
from shapely.geometry import Polygon, MultiPolygon, shape, box
from shapely.geometry.polygon import orient
from shapely.validation import make_valid

from .geo import Projector
from .gltf import MeshData

DEFAULT_FLOOR_HEIGHT = 3.2
DEFAULT_HEIGHT = 2 * DEFAULT_FLOOR_HEIGHT
MIN_AREA_M2 = 4.0

# Usage category codes written to TEXCOORD_1.y (roofs add 100). Keyword match on the usage name.
USAGE_CATEGORIES = [
    (1, ("주택", "아파트", "주거", "다세대", "다가구", "연립", "기숙사")),
    (2, ("근린생활", "판매", "상가", "시장", "숙박", "위락")),
    (3, ("업무", "오피스", "방송")),
    (4, ("공장", "창고", "자동차", "위험물")),
    (5, ("교육", "학교", "종교", "문화", "의료", "노유자", "운동", "공공", "관광")),
]

PALETTE = np.array([
    [150, 72, 58],    # red brick
    [168, 96, 72],    # light brick
    [196, 184, 164],  # beige
    [176, 176, 172],  # concrete grey
    [214, 210, 200],  # off-white render
    [120, 110, 100],  # dark stone
], dtype=np.float64)


@dataclass
class Building:
    id: str
    footprint: Polygon  # ENU meters, exterior CCW
    height: float
    floors: int | None
    usage: str | None
    category: int
    estimated: bool = False
    base_z: float = 0.0
    top_z: float = 0.0
    attrs: dict = field(default_factory=dict)

    @property
    def floor_height(self) -> float:
        if self.floors and self.floors > 0:
            fh = self.height / self.floors
            if 2.4 <= fh <= 6.0:
                return fh
        return DEFAULT_FLOOR_HEIGHT


def usage_category(usage: str | None) -> int:
    if not usage:
        return 0
    for code, words in USAGE_CATEGORIES:
        if any(w in usage for w in words):
            return code
    return 0


def _to_float(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) else None


def inspect_fields(shp: Path, encoding: str = "cp949", samples: int = 5) -> str:
    with shapefile.Reader(str(shp), encoding=encoding) as r:
        names = [f[0] for f in r.fields[1:]]
        lines = [f"레코드 {len(r)}개, 도형 유형 {r.shapeTypeName}", f"필드 {len(names)}개:"]
        rows = [r.record(i) for i in range(min(samples, len(r)))]
        for i, (name, typ, size, dec) in enumerate(r.fields[1:]):
            vals = ", ".join(repr(row[i]) for row in rows)
            lines.append(f"  {name:<12} {typ}{size:>4}  예: {vals}")
    prj = shp.with_suffix(".prj")
    if prj.exists():
        try:
            crs = CRS.from_wkt(prj.read_text(encoding="utf-8", errors="ignore"))
            lines.append(f"좌표계(.prj): {crs.name} (EPSG:{crs.to_epsg()})")
        except Exception as e:
            lines.append(f"좌표계(.prj) 해석 실패: {e}")
    else:
        lines.append("좌표계: .prj 없음 → --src-crs 필요")
    return "\n".join(lines)


def shapefile_crs(shp: Path, override: str | None) -> CRS:
    if override:
        return CRS.from_user_input(override)
    prj = shp.with_suffix(".prj")
    if not prj.exists():
        raise ValueError(f"{prj} 없음: --src-crs로 좌표계를 지정해야 한다")
    return CRS.from_wkt(prj.read_text(encoding="utf-8", errors="ignore"))


def load_buildings(shp: Path, projector: Projector, area_enu: Polygon, *, encoding: str = "cp949",
                   height_field: str | None, floors_field: str | None = None,
                   usage_field: str | None = None, id_field: str | None = None,
                   exclude_enu: list[Polygon] | None = None) -> list[Building]:
    """Read footprints whose ENU footprint intersects `area_enu`."""
    # Coarse filter in the source CRS using the area's lon/lat bounds.
    ex, ey = area_enu.exterior.xy
    lon, lat = projector.enu_to_lonlat(np.array(ex), np.array(ey))
    sx, sy = projector.from_lonlat(lon, lat)
    src_bbox = box(float(np.min(sx)), float(np.min(sy)), float(np.max(sx)), float(np.max(sy)))

    out: list[Building] = []
    with shapefile.Reader(str(shp), encoding=encoding, encodingErrors="replace") as r:
        names = [f[0] for f in r.fields[1:]]
        for fld in (height_field, floors_field, usage_field, id_field):
            if fld and fld not in names:
                raise ValueError(f"필드 '{fld}' 없음. 사용 가능: {names}")
        for n, sr in enumerate(r.iterShapeRecords(bbox=list(src_bbox.bounds))):
            if not sr.shape.points:
                continue
            geom = shape(sr.shape.__geo_interface__)
            if not geom.intersects(src_bbox):
                continue
            rec = dict(zip(names, sr.record))
            for poly in _polygons(geom):
                enu_poly = _poly_to_enu(poly, projector)
                if enu_poly is None or enu_poly.area < MIN_AREA_M2 or not enu_poly.intersects(area_enu):
                    continue
                if exclude_enu and any(enu_poly.intersects(z) for z in exclude_enu):
                    continue
                out.append(_make_building(rec, enu_poly, n, height_field, floors_field, usage_field, id_field))
    return out


def _polygons(geom):
    geom = make_valid(geom)
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]


def _poly_to_enu(poly: Polygon, projector: Projector) -> Polygon | None:
    def ring(coords):
        c = np.asarray(coords, dtype=np.float64)
        enu = projector.to_enu(c[:, 0], c[:, 1], np.zeros(len(c)))
        return enu[:, :2]
    try:
        p = Polygon(ring(poly.exterior.coords), [ring(i.coords) for i in poly.interiors])
    except ValueError:
        return None
    p = make_valid(p)
    if not isinstance(p, Polygon):
        parts = _polygons(p)
        if not parts:
            return None
        p = max(parts, key=lambda g: g.area)
    return orient(p.simplify(0.05, preserve_topology=True), 1.0)


def _make_building(rec, poly, n, height_field, floors_field, usage_field, id_field) -> Building:
    height = _to_float(rec.get(height_field)) if height_field else None
    floors_f = _to_float(rec.get(floors_field)) if floors_field else None
    floors = int(floors_f) if floors_f and floors_f > 0 else None
    usage = str(rec.get(usage_field)).strip() if usage_field and rec.get(usage_field) else None
    bid = str(rec.get(id_field)).strip() if id_field and rec.get(id_field) not in (None, "") else f"row{n}"
    estimated = False
    if not height or height <= 0:
        height = floors * DEFAULT_FLOOR_HEIGHT if floors else DEFAULT_HEIGHT
        estimated = True
    height = float(np.clip(height, 2.5, 400.0))
    return Building(id=bid, footprint=poly, height=height, floors=floors, usage=usage,
                    category=usage_category(usage), estimated=estimated)


def set_elevations(buildings: list[Building], ground_at) -> None:
    """ground_at(e, n) -> orthometric ground heights, already shifted into ENU z by the caller."""
    for b in buildings:
        xs, ys = b.footprint.exterior.xy
        g = np.asarray(ground_at(np.array(xs), np.array(ys)))
        b.base_z = float(g.min()) - 0.3  # sink slightly so slopes never show a gap
        b.top_z = max(float(g.mean()) + b.height, float(g.max()) + 2.0)


def tint(building_id: str) -> np.ndarray:
    h = hashlib.blake2b(building_id.encode("utf-8"), digest_size=4).digest()
    base = PALETTE[h[0] % len(PALETTE)]
    jitter = (np.array([h[1], h[2], h[3]]) / 255.0 - 0.5) * 16
    return np.clip(base + jitter, 0, 255)


def buildings_mesh(buildings: list[Building], name: str = "buildings") -> MeshData:
    pos, nrm, uv0, uv1, col, fid, idx = [], [], [], [], [], [], []
    count = 0

    def add(p, nm, u0, u1, c, f, tri):
        nonlocal count
        pos.append(p); nrm.append(nm); uv0.append(u0); uv1.append(u1); col.append(c); fid.append(f)
        idx.append(tri + count)
        count += len(p)

    for fi, b in enumerate(buildings):
        rgba = np.append(tint(b.id), 255).astype(np.uint8)
        fh = b.floor_height
        rings = [np.asarray(b.footprint.exterior.coords)[:-1]] + [np.asarray(r.coords)[:-1] for r in b.footprint.interiors]
        # Walls: one quad per edge with flat normals. Exterior is CCW, holes CW -> (dy, -dx) points outward.
        for ring in rings:
            p0 = ring
            p1 = np.roll(ring, -1, axis=0)
            d = p1 - p0
            length = np.linalg.norm(d, axis=1)
            keep = length > 1e-3
            p0, p1, d, length = p0[keep], p1[keep], d[keep], length[keep]
            m = len(p0)
            if m == 0:
                continue
            normal = np.stack([d[:, 1], -d[:, 0], np.zeros(m)], axis=1) / length[:, None]
            u_start = np.concatenate([[0.0], np.cumsum(length)[:-1]])
            zb, zt = b.base_z, b.top_z
            v = np.empty((m, 4, 3))
            v[:, 0] = np.c_[p0, np.full(m, zb)]
            v[:, 1] = np.c_[p1, np.full(m, zb)]
            v[:, 2] = np.c_[p1, np.full(m, zt)]
            v[:, 3] = np.c_[p0, np.full(m, zt)]
            uv = np.empty((m, 4, 2))
            uv[:, 0] = np.c_[u_start, np.zeros(m)]
            uv[:, 1] = np.c_[u_start + length, np.zeros(m)]
            uv[:, 2] = np.c_[u_start + length, np.full(m, zt - zb)]
            uv[:, 3] = np.c_[u_start, np.full(m, zt - zb)]
            tris = (np.arange(m)[:, None] * 4 + np.array([0, 1, 2, 0, 2, 3])).ravel()
            add(v.reshape(-1, 3), np.repeat(normal, 4, axis=0), uv.reshape(-1, 2),
                np.tile([fh, b.category], (m * 4, 1)), np.tile(rgba, (m * 4, 1)), np.full(m * 4, fi), tris)

        # Roof: earcut with holes, flat at top_z, UV = ENU meters.
        flat = np.concatenate(rings)
        ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
        tri = np.asarray(earcut.triangulate_float64(flat, ends), dtype=np.int64).reshape(-1, 3)
        if len(tri):
            a, bb, c = flat[tri[:, 0]], flat[tri[:, 1]], flat[tri[:, 2]]
            cross = (bb[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (bb[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
            tri[cross < 0] = tri[cross < 0][:, [0, 2, 1]]  # make CCW from above (normal +z)
            k = len(flat)
            add(np.c_[flat, np.full(k, b.top_z)], np.tile([0.0, 0.0, 1.0], (k, 1)), flat.copy(),
                np.tile([fh, 100 + b.category], (k, 1)), np.tile(rgba, (k, 1)), np.full(k, fi), tri.ravel())

    if not pos:
        return MeshData(np.zeros((0, 3)), np.zeros(0, np.uint32), name=name)
    return MeshData(
        positions=np.concatenate(pos), indices=np.concatenate(idx).astype(np.uint32),
        normals=np.concatenate(nrm), uv0=np.concatenate(uv0), uv1=np.concatenate(uv1),
        colors=np.concatenate(col), feature_ids=np.concatenate(fid).astype(np.float32), name=name,
        extras={"features": [{"id": b.id, "height": round(b.height, 2), "floors": b.floors,
                              "usage": b.usage, "category": b.category, "estimated": b.estimated}
                             for b in buildings]},
    )
