"""Zone Index: index/zones.json (all zones, latest version) + index/cells/<z>_<x>_<y>.json per z16 tile.

Zones root layout: <zones_root>/<zone_id>/v<version>/manifest.json (immutable versions). Only the
highest version folder of each zone that passes `manifest.check` is published; broken ones are reported.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from shapely.geometry import box

from . import manifest as zm

CELL_ZOOM = 16
INDEX_SCHEMA_VERSION = 1
MAX_LAT = 85.0511287798066  # Web Mercator limit
INDEX_DIR_NAME = "index"  # <zones_root>/index is the index itself (spec §6), never a zone folder


def lonlat_to_tile(lon: float, lat: float, z: int = CELL_ZOOM) -> tuple[int, int]:
    """Web Mercator (XYZ / slippy map) tile containing the point. y grows southward."""
    n = 2**z
    lat = max(-MAX_LAT, min(MAX_LAT, lat))
    x = math.floor((lon + 180.0) / 360.0 * n)
    y = math.floor((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def tile_bounds(x: int, y: int, z: int = CELL_ZOOM) -> tuple[float, float, float, float]:
    """(west, south, east, north) degrees of an XYZ tile."""
    n = 2**z

    def lat(yy):
        return math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * yy / n))))

    return x / n * 360.0 - 180.0, lat(y + 1), (x + 1) / n * 360.0 - 180.0, lat(y)


def tiles_for_polygon(poly, z: int = CELL_ZOOM) -> list[tuple[int, int]]:
    """Tiles whose lon/lat rectangle intersects the polygon (not just its bbox)."""
    w, s, e, n = poly.bounds
    x0, y0 = lonlat_to_tile(w, n, z)
    x1, y1 = lonlat_to_tile(e, s, z)
    out = []
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if poly.intersects(box(*tile_bounds(x, y, z))):
                out.append((x, y))
    return out


@dataclass
class ZoneEntry:
    id: str
    version: int
    kind: str
    priority: int
    bbox_wgs84: list[float]
    manifest: str  # relative to zones root
    doc: dict


def scan_zones(zones_root: str | Path) -> tuple[list[ZoneEntry], list[str]]:
    """Latest valid version of every zone under zones_root, and problems found (as messages)."""
    root = Path(zones_root)
    entries, problems = [], []
    for zdir in sorted(p for p in root.iterdir() if p.is_dir()):
        if zdir.name == INDEX_DIR_NAME:
            continue  # the index built into the zones root (spec §6 layout); silently skipped (WP-09)
        if not zm.ZONE_ID_RE.match(zdir.name):
            problems.append(f"{zdir.name}: zone id 형식이 아니라 건너뜀")
            continue
        versions = sorted(
            (int(m.group(1)), v)
            for v in zdir.iterdir()
            if v.is_dir() and (m := zm.VERSION_DIR_RE.match(v.name))
        )
        chosen = None
        for num, vdir in reversed(versions):
            path = vdir / zm.MANIFEST_NAME
            if not path.is_file():
                problems.append(f"{zdir.name}/{vdir.name}: {zm.MANIFEST_NAME} 없음")
                continue
            try:
                doc = zm.load(path)
            except json.JSONDecodeError as e:
                problems.append(f"{zdir.name}/{vdir.name}: JSON 파싱 실패: {e}")
                continue
            rep = zm.check(doc, path)
            if not rep.ok:
                problems += [f"{zdir.name}/{vdir.name}: {e}" for e in rep.errors]
                continue
            chosen = (num, vdir, doc)
            break
        if chosen is None:
            if versions:
                problems.append(f"{zdir.name}: 유효한 버전이 없어 인덱스에서 뺌")
            continue
        num, vdir, doc = chosen
        poly = zm.footprint_polygon(doc["footprint_wgs84"])
        entries.append(
            ZoneEntry(
                id=doc["zone_id"],
                version=num,
                kind=doc["kind"],
                priority=doc["priority"],
                bbox_wgs84=[round(v, 9) for v in poly.bounds],
                manifest=f"{zdir.name}/{vdir.name}/{zm.MANIFEST_NAME}",
                doc=doc,
            )
        )
    return entries, problems


def _order(entries):
    # Winner first: priority desc, then newer version, then id (stable output)
    return sorted(entries, key=lambda e: (-e.priority, -e.version, e.id))


def build_index(
    zones_root: str | Path, problems: list[str] | None = None
) -> tuple[dict, dict[tuple[int, int, int], dict]]:
    """(zones.json dict, {(z, x, y): cell dict}). Skipped zones/versions are appended to `problems`."""
    entries, found = scan_zones(zones_root)
    if problems is not None:
        problems.extend(found)
    zones = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "cell_zoom": CELL_ZOOM,
        "zones": [
            {
                "id": e.id,
                "version": e.version,
                "kind": e.kind,
                "priority": e.priority,
                "bbox_wgs84": e.bbox_wgs84,
                "manifest": e.manifest,
            }
            for e in sorted(entries, key=lambda e: e.id)
        ],
    }
    by_cell: dict[tuple[int, int, int], list[ZoneEntry]] = {}
    for e in entries:
        for x, y in tiles_for_polygon(zm.footprint_polygon(e.doc["footprint_wgs84"])):
            by_cell.setdefault((CELL_ZOOM, x, y), []).append(e)
    cells = {
        key: {
            "schema_version": INDEX_SCHEMA_VERSION,
            "z": key[0],
            "x": key[1],
            "y": key[2],
            "zones": [{"id": e.id, "version": e.version} for e in _order(es)],
        }
        for key, es in sorted(by_cell.items())
    }
    return zones, cells


def cell_name(z: int, x: int, y: int) -> str:
    return f"{z}_{x}_{y}.json"


def write_index(zones: dict, cells: dict, out_dir: str | Path) -> list[Path]:
    """Write zones.json and cells/*.json; stale cell files from an earlier build are removed."""
    out = Path(out_dir)
    written = [out / "zones.json"]
    zm.write_json(zones, written[0])
    cell_dir = out / "cells"
    cell_dir.mkdir(parents=True, exist_ok=True)
    keep = {cell_name(*k) for k in cells}
    for old in cell_dir.glob("*.json"):
        if old.name not in keep:
            old.unlink()
    for key, doc in cells.items():
        p = cell_dir / cell_name(*key)
        zm.write_json(doc, p)
        written.append(p)
    return written
