"""Basemap exclusion polygons from exterior zone footprints (input of `golmok-basemap build --exclude`).

golmok-basemap drops every basemap building whose footprint intersects an exclusion polygon (D-012).
`buffer_m` grows each footprint outward so buildings touching the zone's overlap band (ARCHITECTURE §4-4:
0.5~1 m) are dropped too; the zone's own geometry is expected to cover that band.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from shapely import union_all
from shapely.geometry import MultiPolygon, Polygon, mapping

from . import manifest as zm
from . import transform
from .index import scan_zones

DEFAULT_BUFFER_M = 0.75


def buffered_footprint(doc: dict, buffer_m: float) -> Polygon:
    """Footprint grown by buffer_m meters (in the zone's tangent plane), back in lon/lat."""
    if buffer_m == 0:
        return zm.footprint_polygon(doc["footprint_wgs84"])
    o = doc["origin"]
    origin = (o["lat"], o["lon"], o["height_ellipsoidal"])
    local = zm.footprint_enu(doc["footprint_wgs84"], origin).buffer(buffer_m, join_style="mitre")

    def ring(coords):
        xy = np.asarray(coords, dtype=np.float64)
        enu = np.column_stack([xy[:, 0], xy[:, 1], np.zeros(len(xy))])
        lon, lat, _ = transform.enu_to_lonlat(enu, origin)
        return np.round(np.column_stack([lon, lat]), 9)  # 1e-9 deg ≈ 0.1 mm

    return Polygon(ring(local.exterior.coords), [ring(r.coords) for r in local.interiors])


def build_exclude(zones_root: str | Path, buffer_m: float = DEFAULT_BUFFER_M) -> tuple[dict, list[str]]:
    """(GeoJSON FeatureCollection, problems). One feature per merged polygon; zone ids in properties."""
    if buffer_m < 0:
        raise ValueError("buffer_m must be >= 0")
    entries, problems = scan_zones(zones_root)
    parts = [(e.id, buffered_footprint(e.doc, buffer_m)) for e in entries if e.kind == "exterior"]
    features = []
    if parts:
        merged = union_all([p for _, p in parts])
        polys = list(merged.geoms) if isinstance(merged, MultiPolygon) else [merged]
        for poly in sorted(polys, key=lambda p: p.bounds):
            ids = sorted(zid for zid, p in parts if p.intersects(poly))
            features.append(
                {
                    "type": "Feature",
                    "properties": {"zone_ids": ids, "buffer_m": buffer_m},
                    "geometry": mapping(poly),
                }
            )
    return {"type": "FeatureCollection", "features": features}, problems
