"""Shared helpers for the zone tests (synthetic manifests)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

FIXTURE_ZONES = Path(__file__).parent / "fixtures" / "zones"
REPO = Path(__file__).resolve().parents[2]


def rect_footprint(lat: float, lon: float, w: float, h: float, dx: float = 0.0, dy: float = 0.0) -> dict:
    """GeoJSON Polygon: w x h m rectangle centered (dx, dy) m from (lat, lon), on its tangent plane."""
    from golmok_tools.zone import transform

    xy = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2], [-w / 2, -h / 2]])
    xy += [dx, dy]
    lon_, lat_, _ = transform.enu_to_lonlat(np.column_stack([xy, np.zeros(5)]), (lat, lon, 0.0))
    ring = [[round(float(a), 9), round(float(b), 9)] for a, b in zip(lon_, lat_, strict=True)]
    ring[-1] = ring[0]
    return {"type": "Polygon", "coordinates": [ring]}


def make_zone(
    root: Path,
    zone_id: str,
    lat: float = 37.5620,
    lon: float = 126.9250,
    h: float = 50.0,
    version: int = 1,
    kind: str = "exterior",
    priority: int = 0,
    size=(40.0, 20.0),
    parent: str | None = None,
    edit=None,
):
    """Write <root>/<zone_id>/v<version>/manifest.json; returns (path, dict)."""
    from golmok_tools.zone import manifest as zm

    fp = rect_footprint(lat, lon, *size)
    d = zm.new_manifest(
        zone_id, kind, lat, lon, h, fp, version=version, parent_zone=parent, priority=priority
    ).to_dict()
    d["sources"] = [{"capture_id": "synthetic"}]
    if edit:
        edit(d)
    path = zm.save(d, Path(root) / zone_id / f"v{version}" / zm.MANIFEST_NAME)
    return path, d
