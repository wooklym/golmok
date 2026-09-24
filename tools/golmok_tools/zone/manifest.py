"""Zone manifest model: dataclasses, load/save, defaults and semantic checks.

The JSON Schema (schema.py) checks shape and types; `check()` adds what a schema cannot express:
rigid transform, origin/transform agreement, footprint validity, unique ids, path layout.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from shapely.geometry import Point, Polygon, shape
from shapely.validation import explain_validity

from . import schema, transform

SCHEMA_VERSION = 1
MANIFEST_NAME = "manifest.json"
ZONE_ID_RE = re.compile(r"^z_[a-z0-9]+(_[a-z0-9]+)*$")
VERSION_DIR_RE = re.compile(r"^v([1-9][0-9]*)$")

RIGID_TOL = 1e-9  # |R^T R - I|, det - 1
ORIGIN_TOL_M = 1e-3  # origin / origin_ecef / transform translation agreement
ORIGIN_MAX_DIST_M = 50.0  # origin outside the footprint by more than this is an error
TILT_WARN_DEG = 0.5  # zone up vs local vertical


@dataclass
class Origin:
    lat: float
    lon: float
    height_ellipsoidal: float


@dataclass
class Chunk:
    id: str
    uri: str
    bbox_enu: list[list[float]]
    tris: int | None = None


@dataclass
class VisualLayer:
    format: str = "nanite_mesh"
    chunks: list[Chunk] = field(default_factory=list)
    textures: list[dict] | None = None


@dataclass
class CollisionLayer:
    format: str = "glb"
    uri: str = "collision.glb"
    chunks: list[Chunk] | None = None


@dataclass
class Layers:
    visual: VisualLayer = field(default_factory=VisualLayer)
    collision: CollisionLayer = field(default_factory=CollisionLayer)
    blockers: dict | None = None  # {"uri": ...}
    navmesh: dict | None = None  # {"format": "recast", "uri": ...}


@dataclass
class Pose:
    position: list[float]
    yaw_deg: float = 0.0


@dataclass
class Portal:
    id: str
    to_zone: str
    pose_enu: Pose
    radius_m: float = 1.5
    kind: str = "door"


@dataclass
class Replaces:
    building_ids: list[str] = field(default_factory=list)
    terrain_clip: bool = True


@dataclass
class Consent:
    type: str = "public_street"
    record_id: str | None = None


@dataclass
class ZoneManifest:
    zone_id: str
    version: int
    kind: str
    origin: Origin
    origin_ecef: list[float]
    transform: list[float]
    footprint_wgs84: dict
    parent_zone: str | None = None
    replaces: Replaces = field(default_factory=Replaces)
    layers: Layers = field(default_factory=Layers)
    portals: list[Portal] = field(default_factory=list)
    priority: int = 0
    quality: dict = field(default_factory=dict)
    consent: Consent = field(default_factory=Consent)
    attribution: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION

    # -- conversion -------------------------------------------------------------------------------
    @classmethod
    def from_dict(cls, d: dict) -> ZoneManifest:
        layers = d.get("layers", {})
        vis = layers.get("visual", {})
        col = layers.get("collision", {})
        return cls(
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            zone_id=d["zone_id"],
            version=d["version"],
            kind=d["kind"],
            parent_zone=d.get("parent_zone"),
            origin=Origin(**d["origin"]),
            origin_ecef=list(d["origin_ecef"]),
            transform=list(d["transform"]),
            footprint_wgs84=d["footprint_wgs84"],
            replaces=Replaces(**d.get("replaces", {})),
            layers=Layers(
                visual=VisualLayer(
                    format=vis.get("format", "nanite_mesh"),
                    chunks=[Chunk(**c) for c in vis.get("chunks", [])],
                    textures=vis.get("textures"),
                ),
                collision=CollisionLayer(
                    format=col.get("format", "glb"),
                    uri=col.get("uri", "collision.glb"),
                    chunks=[Chunk(**c) for c in col["chunks"]] if col.get("chunks") is not None else None,
                ),
                blockers=layers.get("blockers"),
                navmesh=layers.get("navmesh"),
            ),
            portals=[Portal(**{**p, "pose_enu": Pose(**p["pose_enu"])}) for p in d.get("portals", [])],
            priority=d.get("priority", 0),
            quality=dict(d.get("quality", {})),
            consent=Consent(**d.get("consent", {})),
            attribution=list(d.get("attribution", [])),
            sources=list(d.get("sources", [])),
        )

    def to_dict(self) -> dict:
        return _drop_none(asdict(self), keep=_NULLABLE)

    @property
    def matrix(self) -> np.ndarray:
        return transform.from_row_major(self.transform)

    def footprint(self) -> Polygon:
        return footprint_polygon(self.footprint_wgs84)


# Keys whose null is meaningful (written out); other None fields are optional and dropped.
_NULLABLE = {"parent_zone", "record_id", "icp_rmse_m", "footprint_iou", "reviewed_by", "reviewed_at"}

_KEY_ORDER = [
    "schema_version",
    "zone_id",
    "version",
    "kind",
    "parent_zone",
    "origin",
    "origin_ecef",
    "transform",
    "footprint_wgs84",
    "replaces",
    "layers",
    "portals",
    "priority",
    "quality",
    "consent",
    "attribution",
    "sources",
]


def _drop_none(obj, keep: set[str]):
    if isinstance(obj, dict):
        return {k: _drop_none(v, keep) for k, v in obj.items() if v is not None or k in keep}
    if isinstance(obj, list):
        return [_drop_none(v, keep) for v in obj]
    return obj


def new_manifest(
    zone_id: str,
    kind: str,
    lat: float,
    lon: float,
    h: float,
    footprint_wgs84: dict,
    yaw_deg: float = 0.0,
    version: int = 1,
    parent_zone: str | None = None,
    priority: int = 0,
) -> ZoneManifest:
    """A manifest with defaults: no chunks yet, collision.glb, consent by kind, unreviewed quality."""
    m = transform.zone_transform(lat, lon, h, yaw_deg)
    return ZoneManifest(
        zone_id=zone_id,
        version=version,
        kind=kind,
        parent_zone=parent_zone,
        origin=Origin(lat=lat, lon=lon, height_ellipsoidal=h),
        origin_ecef=[float(v) for v in m[:3, 3]],
        transform=transform.to_row_major(m),
        footprint_wgs84=footprint_wgs84,
        replaces=Replaces(building_ids=[], terrain_clip=kind == "exterior"),
        priority=priority,
        quality={"icp_rmse_m": None, "footprint_iou": None, "reviewed_by": None, "reviewed_at": None},
        consent=Consent(type="public_street" if kind == "exterior" else "owner_consent", record_id=None),
    )


# -- files ----------------------------------------------------------------------------------------


def load(path: str | Path) -> dict:
    """Manifest JSON as a dict (use ZoneManifest.from_dict for the typed model)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _flat(v) -> bool:
    return not isinstance(v, dict | list | tuple)


def json_text(obj, indent: int = 2, _level: int = 0) -> str:
    """JSON with 2-space indent; short number lists stay on one line, a 16-number list is 4 rows.

    Keeps transforms, bboxes and coordinates readable. Floats use repr (round-trips exactly).
    """
    pad, inner = " " * (indent * _level), " " * (indent * (_level + 1))
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items = [
            f"{inner}{json.dumps(k, ensure_ascii=False)}: {json_text(v, indent, _level + 1)}"
            for k, v in obj.items()
        ]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(obj, list | tuple):
        if not obj:
            return "[]"
        if len(obj) == 16 and all(isinstance(v, int | float) for v in obj):  # 4x4 row-major
            rows = [", ".join(json.dumps(v) for v in obj[i : i + 4]) for i in range(0, 16, 4)]
            return "[\n" + ",\n".join(inner + r for r in rows) + "\n" + pad + "]"
        one_line = "[" + ", ".join(json_text(v, indent, _level + 1) for v in obj) + "]"
        simple = all(_flat(v) or (isinstance(v, list | tuple) and all(_flat(w) for w in v)) for v in obj)
        if simple and len(one_line) + len(inner) <= 100:
            return one_line
        return "[\n" + ",\n".join(inner + json_text(v, indent, _level + 1) for v in obj) + "\n" + pad + "]"
    return json.dumps(obj, ensure_ascii=False)


def write_json(obj, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n": identical bytes on Windows (UE and git see the same file)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json_text(obj) + "\n")
    return path


def dumps(d: dict | ZoneManifest) -> str:
    if isinstance(d, ZoneManifest):
        d = d.to_dict()
    ordered = {k: d[k] for k in _KEY_ORDER if k in d} | {k: v for k, v in d.items() if k not in _KEY_ORDER}
    return json_text(ordered) + "\n"


def save(d: dict | ZoneManifest, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dumps(d))
    return path


# -- geometry helpers -----------------------------------------------------------------------------


def footprint_polygon(geojson: dict) -> Polygon:
    g = shape(geojson)
    if not isinstance(g, Polygon):
        raise ValueError(f"footprint must be a Polygon, got {g.geom_type}")
    return g


def footprint_enu(geojson: dict, origin: tuple[float, float, float]) -> Polygon:
    """Footprint on the horizontal plane of the ENU frame at origin (lat, lon, h), in meters."""
    poly = footprint_polygon(geojson)

    def ring(coords):
        ll = np.asarray(coords, dtype=np.float64)[:, :2]
        enu = transform.lonlat_to_enu(ll[:, 0], ll[:, 1], np.full(len(ll), origin[2]), origin)
        return enu[:, :2]

    return Polygon(ring(poly.exterior.coords), [ring(r.coords) for r in poly.interiors])


def read_footprint_file(path: str | Path) -> dict:
    """GeoJSON file with one Polygon (bare geometry, Feature, or single-feature FeatureCollection)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("type") == "FeatureCollection":
        feats = data.get("features", [])
        if len(feats) != 1:
            raise ValueError(f"{path}: FeatureCollection must hold exactly 1 feature, has {len(feats)}")
        data = feats[0]
    if data.get("type") == "Feature":
        data = data["geometry"]
    if data.get("type") != "Polygon":
        raise ValueError(f"{path}: need a GeoJSON Polygon, got {data.get('type')}")
    return {"type": "Polygon", "coordinates": data["coordinates"]}


# -- checks ---------------------------------------------------------------------------------------


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def check(d: dict, path: str | Path | None = None, check_files: bool = False) -> Report:
    """Schema + semantic checks. `path` (manifest.json) enables layout checks; check_files needs it."""
    rep = Report(errors=schema.validate(d))
    if rep.errors:
        return rep
    _check_transform(d, rep)
    _check_footprint(d, rep)
    _check_ids(d, rep)
    _check_misc(d, rep)
    if path is not None:
        _check_layout(d, Path(path), rep)
        if check_files:
            _check_files(d, Path(path).parent, rep)
    return rep


def _check_transform(d: dict, rep: Report) -> None:
    m = transform.from_row_major(d["transform"])
    ortho, det, bottom = transform.rigidity_error(m)
    if ortho > RIGID_TOL or abs(det - 1.0) > RIGID_TOL or bottom > 0:
        rep.errors.append(
            f"transform: rigid 아님 (|RᵀR-I|={ortho:.3g}, det={det:.12f}, 마지막 행 오차={bottom:.3g}). "
            "회전은 직교·det=+1, 마지막 행은 [0,0,0,1]이어야 한다"
        )
        return
    t = m[:3, 3]
    if np.linalg.norm(np.asarray(d["origin_ecef"]) - t) > ORIGIN_TOL_M:
        rep.errors.append(f"origin_ecef {d['origin_ecef']} != transform 이동 성분 {t.tolist()}")
    o = d["origin"]
    geo = transform.geodetic_to_ecef(o["lat"], o["lon"], o["height_ellipsoidal"])
    if np.linalg.norm(geo - t) > ORIGIN_TOL_M:
        rep.errors.append(
            f"origin (lat/lon/h)이 transform 원점과 {np.linalg.norm(geo - t):.3f} m 다르다 "
            "(origin은 zone-local (0,0,0)의 측지 좌표)"
        )
    tilt = transform.tilt_deg(m)
    if tilt > TILT_WARN_DEG:
        rep.warnings.append(f"transform: zone +z가 연직에서 {tilt:.2f}° 기울어 있다(정합 결과인지 확인)")


def _check_footprint(d: dict, rep: Report) -> None:
    poly = footprint_polygon(d["footprint_wgs84"])
    # shapely closes rings silently; GeoJSON (RFC 7946 §3.1.6) requires first == last
    for i, ring in enumerate(d["footprint_wgs84"]["coordinates"]):
        if list(ring[0][:2]) != list(ring[-1][:2]):
            rep.errors.append(f"footprint_wgs84: ring {i}가 닫혀 있지 않다(첫 점 != 끝 점)")
    if not poly.is_valid:
        rep.errors.append(f"footprint_wgs84: 유효하지 않은 폴리곤 ({explain_validity(poly)})")
        return
    o = d["origin"]
    origin = (o["lat"], o["lon"], o["height_ellipsoidal"])
    local = footprint_enu(d["footprint_wgs84"], origin)
    if local.area < 1.0:
        rep.errors.append(f"footprint_wgs84: 면적 {local.area:.3f} m² — 너무 작다")
    dist = local.distance(Point(0.0, 0.0))
    if dist > ORIGIN_MAX_DIST_M:
        rep.errors.append(f"origin이 footprint에서 {dist:.1f} m 떨어져 있다(허용 {ORIGIN_MAX_DIST_M:.0f} m)")
    elif dist > 0:
        rep.warnings.append(f"origin이 footprint 밖({dist:.1f} m)이다")


def _dupes(items) -> list[str]:
    seen, dup = set(), []
    for x in items:
        if x in seen and x not in dup:
            dup.append(x)
        seen.add(x)
    return dup


def _check_ids(d: dict, rep: Report) -> None:
    layers = d["layers"]
    vis = layers["visual"]["chunks"]
    col = layers["collision"].get("chunks") or []
    for name, ids in (
        ("layers.visual.chunks", [c["id"] for c in vis]),
        ("layers.collision.chunks", [c["id"] for c in col]),
        ("portals", [p["id"] for p in d["portals"]]),
    ):
        if dup := _dupes(ids):
            rep.errors.append(f"{name}: id 중복 {dup}")
    for name, chunks in (("layers.visual.chunks", vis), ("layers.collision.chunks", col)):
        for c in chunks:
            lo, hi = c["bbox_enu"]
            if any(a > b for a, b in zip(lo, hi, strict=True)):
                rep.errors.append(f"{name}[{c['id']}]: bbox_enu min > max ({lo} / {hi})")
    for p in d["portals"]:
        if p["to_zone"] == d["zone_id"]:
            rep.errors.append(f"portals[{p['id']}]: to_zone이 자기 자신({d['zone_id']})이다")
    if d["parent_zone"] == d["zone_id"]:
        rep.errors.append("parent_zone이 자기 자신이다")


def _check_misc(d: dict, rep: Report) -> None:
    if not d["layers"]["visual"]["chunks"]:
        rep.warnings.append("layers.visual.chunks가 비어 있다(init 직후라면 정상)")
    if d["layers"]["visual"]["format"] != "nanite_mesh":
        rep.warnings.append(
            f"layers.visual.format={d['layers']['visual']['format']}: "
            "로더는 nanite_mesh를 먼저 지원한다(D-010 전)"
        )
    c = d["consent"]
    if c["type"] == "owner_consent" and not c["record_id"]:
        rep.warnings.append("consent: owner_consent인데 record_id가 없다(게시 전 필수)")
    if d["kind"] == "interior" and d["replaces"]["terrain_clip"]:
        rep.warnings.append("interior zone에 replaces.terrain_clip=true — 의도한 것인지 확인")
    if not d["sources"]:
        rep.warnings.append("sources가 비어 있다(captures/INDEX.md의 촬영 ID)")


def _check_layout(d: dict, path: Path, rep: Report) -> None:
    vdir, zdir = path.parent.name, path.parent.parent.name
    m = VERSION_DIR_RE.match(vdir)
    if path.name != MANIFEST_NAME or not m or zdir != d["zone_id"]:
        rep.warnings.append(
            f"경로가 규약 <zone_id>/v<version>/{MANIFEST_NAME}와 다르다: .../{zdir}/{vdir}/{path.name}"
        )
    elif int(m.group(1)) != d["version"]:
        rep.errors.append(f"폴더 {vdir}와 version {d['version']}이 다르다")


def referenced_uris(d: dict) -> list[str]:
    layers = d["layers"]
    uris = [c["uri"] for c in layers["visual"]["chunks"]]
    uris += [t["uri"] for t in layers["visual"].get("textures") or []]
    uris.append(layers["collision"]["uri"])
    uris += [c["uri"] for c in layers["collision"].get("chunks") or []]
    for k in ("blockers", "navmesh"):
        if layers.get(k):
            uris.append(layers[k]["uri"])
    return uris


def _check_files(d: dict, root: Path, rep: Report) -> None:
    for uri in referenced_uris(d):
        if not (root / uri).is_file():
            rep.errors.append(f"파일 없음: {uri}")
    b = d["layers"].get("blockers")
    if b and (root / b["uri"]).is_file():
        try:
            doc = json.loads((root / b["uri"]).read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            rep.errors.append(f"{b['uri']}: JSON 파싱 실패: {e}")
            return
        rep.errors += [f"{b['uri']}: {e}" for e in schema.validate_blockers(doc)]
        if not rep.errors:
            if dup := _dupes(p["id"] for p in doc["planes"]):
                rep.errors.append(f"{b['uri']}: plane id 중복 {dup}")
            for p in doc["planes"]:
                if np.linalg.norm(p["normal_enu"]) < 1e-6:
                    rep.errors.append(f"{b['uri']}[{p['id']}]: normal_enu 길이가 0")
