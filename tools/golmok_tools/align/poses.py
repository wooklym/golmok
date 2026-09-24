"""Camera poses (RealityScan CSV export) joined with per-photo GPS (golmok-blur gps_priors.csv).

RealityScan "Internal/External camera parameters" CSV header [2차: community importers]:
    #name,x,y,alt,yaw,pitch,roll,f,px,py,k1,k2,k3,k4,t1,t2
Only name and x, y, alt (position in the project's coordinate system) are used here; the rotation
columns are not needed for the position prior. Georeferenced projects export grid coordinates.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class CameraPose:
    name: str
    position: np.ndarray  # (3,) in the scan's coordinate system (zone-local when not georeferenced)


@dataclass
class GpsFix:
    name: str
    lat: float
    lon: float
    alt: float | None  # EXIF GPSAltitude (usually above sea level)


def _stem(name: str) -> str:
    return Path(name).stem.lower()


def _num(row: dict, *keys: str) -> float | None:
    for k in keys:
        for cand in (k, k.upper(), k.capitalize()):
            if cand in row and row[cand] not in (None, ""):
                try:
                    return float(row[cand])
                except ValueError:
                    return None
    return None


def read_realityscan_csv(path: str | Path) -> list[CameraPose]:
    """Parse the RealityScan camera CSV. The header may start with '#'; extra columns are ignored."""
    text = Path(path).read_text(encoding="utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0].lstrip("#").strip()
    reader = csv.DictReader([header] + lines[1:])
    poses = []
    for row in reader:
        row = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
        name = row.get("name") or row.get("Name") or row.get("#name")
        x, y = _num(row, "x"), _num(row, "y")
        z = _num(row, "alt", "z")
        if name is None or x is None or y is None or z is None:
            continue
        poses.append(CameraPose(name=name, position=np.array([x, y, z], dtype=np.float64)))
    return poses


def read_gps_csv(path: str | Path) -> list[GpsFix]:
    """golmok-blur gps_priors.csv (name, lat, lon, alt) or any CSV with those columns."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    fixes = []
    for row in rows:
        lat, lon = _num(row, "lat", "latitude"), _num(row, "lon", "longitude")
        if lat is None or lon is None:
            continue
        fixes.append(GpsFix(name=row.get("name", ""), lat=lat, lon=lon, alt=_num(row, "alt", "altitude")))
    return fixes


def join(poses: list[CameraPose], fixes: list[GpsFix]) -> list[tuple[CameraPose, GpsFix]]:
    """Match by file stem (case-insensitive; extension differences such as DNG vs TIF are ignored)."""
    by_stem = {_stem(f.name): f for f in fixes}
    return [(p, by_stem[_stem(p.name)]) for p in poses if _stem(p.name) in by_stem]
