"""Basemap builder on synthetic data: SHP footprints (EPSG:5186), sloped DEM, RGB orthophoto."""

import json
from argparse import Namespace
from pathlib import Path

import numpy as np
import pytest

shapefile = pytest.importorskip("shapefile")
rasterio = pytest.importorskip("rasterio")
pygltflib = pytest.importorskip("pygltflib")
from pyproj import Transformer  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402

from golmok_tools.basemap.build import build, main  # noqa: E402
from golmok_tools.basemap.geo import EnuFrame, Projector  # noqa: E402

LAT, LON = 37.5620, 126.9250  # Yeonnam-dong area
CRS = "EPSG:5186"
PRJ_5186 = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)


def center_xy():
    return PRJ_5186.transform(LON, LAT)


def write_shp(path: Path):
    cx, cy = center_xy()
    w = shapefile.Writer(str(path), shapeType=shapefile.POLYGON, encoding="cp949")
    w.field("A1", "C", 30)
    w.field("A9", "C", 40)
    w.field("A16", "N", 10, 2)
    w.field("FLOORS", "N", 5, 0)
    # 10x10 m house at the center, 12 m high, 4 floors (clockwise ring = shapefile outer ring)
    w.poly([[(cx - 5, cy - 5), (cx - 5, cy + 5), (cx + 5, cy + 5), (cx + 5, cy - 5), (cx - 5, cy - 5)]])
    w.record("B-CENTER", "단독주택", 12.0, 4)
    # 20x10 m shop 100 m east, missing height -> estimated from 3 floors
    w.poly([[(cx + 100, cy), (cx + 100, cy + 10), (cx + 120, cy + 10), (cx + 120, cy), (cx + 100, cy)]])
    w.record("B-SHOP", "제2종근린생활시설", 0, 3)
    # Courtyard building with a hole, 300 m north
    outer = [
        (cx - 15, cy + 300),
        (cx - 15, cy + 330),
        (cx + 15, cy + 330),
        (cx + 15, cy + 300),
        (cx - 15, cy + 300),
    ]
    hole = [
        (cx - 5, cy + 310),
        (cx + 5, cy + 310),
        (cx + 5, cy + 320),
        (cx - 5, cy + 320),
        (cx - 5, cy + 310),
    ]
    w.poly([outer, hole])
    w.record("B-COURT", "업무시설", 20.0, 5)
    # Far away building (outside radius) must be skipped
    w.poly([[(cx + 5000, cy), (cx + 5000, cy + 10), (cx + 5010, cy + 10), (cx + 5010, cy), (cx + 5000, cy)]])
    w.record("B-FAR", "창고", 8.0, 1)
    w.close()
    path.with_suffix(".prj").write_text(
        __import__("pyproj").CRS.from_user_input(CRS).to_wkt("WKT1_ESRI"), encoding="utf-8"
    )


def write_dem(path: Path):
    cx, cy = center_xy()
    res = 5.0
    size = 1000  # 5 km
    x0, y0 = cx - size * res / 2, cy + size * res / 2
    rows, cols = np.mgrid[0:size, 0:size]
    x = x0 + (cols + 0.5) * res
    # 30 m at the center, rising 1 m per 100 m eastwards
    z = 30.0 + (x - cx) / 100.0
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=1,
        dtype="float32",
        crs=CRS,
        transform=from_origin(x0, y0, res, res),
    ) as ds:
        ds.write(z.astype(np.float32), 1)


def write_ortho(path: Path):
    cx, cy = center_xy()
    res = 1.0
    size = 1200
    x0, y0 = cx - size * res / 2, cy + size * res / 2
    img = np.zeros((3, size, size), np.uint8)
    img[0] = 180
    img[1, :, : size // 2] = 90
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=3,
        dtype="uint8",
        crs=CRS,
        transform=from_origin(x0, y0, res, res),
    ) as ds:
        ds.write(img)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("basemap")
    write_shp(d / "bld.shp")
    write_dem(d / "dem.tif")
    write_ortho(d / "ortho.tif")
    args = Namespace(
        buildings=d / "bld.shp",
        dem=[str(d / "dem.tif")],
        ortho=[str(d / "ortho.tif")],
        center=f"{LAT},{LON}",
        radius=400.0,
        out=d / "out",
        height_field="A16",
        floors_field="FLOORS",
        usage_field="A9",
        id_field="A1",
        src_crs=None,
        encoding="cp949",
        tile_size=200.0,
        terrain_spacing=10.0,
        texture_size=512,
        geoid_offset=0.0,
        exclude=None,
        no_terrain=False,
    )
    manifest = build(args)
    return d / "out", manifest


def load_glb(path: Path):
    g = pygltflib.GLTF2().load(str(path))
    blob = g.binary_blob()

    def accessor(i, dtype, comps):
        acc = g.accessors[i]
        view = g.bufferViews[acc.bufferView]
        arr = np.frombuffer(
            blob, dtype=dtype, count=acc.count * comps, offset=view.byteOffset + (acc.byteOffset or 0)
        )
        return arr.reshape(acc.count, comps) if comps > 1 else arr

    prim = g.meshes[0].primitives[0]
    pos = accessor(prim.attributes.POSITION, np.float32, 3)
    idx = accessor(prim.indices, np.uint32, 1)
    nrm = accessor(prim.attributes.NORMAL, np.float32, 3)
    uv1 = (
        accessor(prim.attributes.TEXCOORD_1, np.float32, 2)
        if prim.attributes.TEXCOORD_1 is not None
        else None
    )
    fid_acc = getattr(prim.attributes, "_FEATURE_ID_0", None)
    load_glb.fid = accessor(fid_acc, np.float32, 1) if fid_acc is not None else None
    return g, pos, idx, nrm, uv1


def gltf_to_enu(p):
    return np.stack([p[:, 0], -p[:, 2], p[:, 1]], axis=1)


def test_manifest_counts_and_origin(built):
    out, m = built
    assert m["buildings"]["count"] == 3  # far building skipped
    assert m["buildings"]["height_estimated"] == 1
    assert m["origin"]["height_orthometric"] == pytest.approx(30.0, abs=0.2)
    assert (out / "tileset.json").exists()
    assert len(m["tiles"]) == 16  # 800 m square / 200 m tiles


def test_center_building_geometry(built):
    out, m = built
    tile = next(
        t
        for t in m["tiles"]
        if t["buildings"]
        and t["n_buildings"]
        and abs(t["center_enu"][0]) <= 100
        and abs(t["center_enu"][1]) <= 100
    )
    g, pos, idx, nrm, uv1 = load_glb(out / tile["buildings"])
    feats = g.meshes[0].extras["features"]
    fi = next(i for i, f in enumerate(feats) if f["id"] == "B-CENTER")
    assert feats[fi]["category"] == 1
    sel = load_glb.fid == fi
    assert sel.sum() > 8
    enu = gltf_to_enu(pos)[sel]
    uv1 = uv1[sel]
    # footprint ~10 m, top ~ ground(0 at origin) + 12 m
    assert enu[:, 0].max() - enu[:, 0].min() == pytest.approx(10.0, abs=0.2)
    assert enu[:, 2].max() == pytest.approx(12.0, abs=0.3)
    assert enu[:, 2].min() == pytest.approx(-0.3 - 0.05, abs=0.2)
    # floor height = 12 / 4
    assert np.allclose(uv1[:, 0], 3.0)
    assert idx.max() < len(pos)


def test_wall_normals_point_outward_and_winding_matches(built):
    out, m = built
    for t in m["tiles"]:
        if not t["buildings"]:
            continue
        g, pos, idx, nrm, uv1 = load_glb(out / t["buildings"])
        enu, n_enu = gltf_to_enu(pos), gltf_to_enu(nrm)
        tri = idx.reshape(-1, 3)
        a, b, c = enu[tri[:, 0]], enu[tri[:, 1]], enu[tri[:, 2]]
        face_n = np.cross(b - a, c - a)
        # geometric winding agrees with stored normals (counter-clockwise from outside)
        assert (np.einsum("ij,ij->i", face_n, n_enu[tri[:, 0]]) > 0).all()


def test_courtyard_hole_and_estimated_shop(built):
    out, m = built
    all_feats = []
    for t in m["tiles"]:
        if t["buildings"]:
            g = pygltflib.GLTF2().load(str(out / t["buildings"]))
            all_feats += g.meshes[0].extras["features"]
    by_id = {f["id"]: f for f in all_feats}
    assert by_id["B-SHOP"]["estimated"] and by_id["B-SHOP"]["height"] == pytest.approx(9.6)
    assert by_id["B-SHOP"]["category"] == 2
    assert by_id["B-COURT"]["category"] == 3


def test_terrain_follows_dem_slope_and_has_texture(built):
    out, m = built
    east = max(m["tiles"], key=lambda t: t["center_enu"][0])
    g, pos, idx, nrm, uv1 = load_glb(out / east["terrain"])
    enu = gltf_to_enu(pos)
    # DEM rises 1 m / 100 m eastwards
    slope = np.polyfit(enu[:, 0], enu[:, 2], 1)[0]
    assert slope == pytest.approx(0.01, abs=0.002)
    assert g.images and g.images[0].mimeType == "image/jpeg"
    assert (gltf_to_enu(nrm)[:, 2] > 0.99).all()


def test_tileset_transform_places_origin_at_center(built):
    out, m = built
    ts = json.loads((out / "tileset.json").read_text())
    mat = np.array(ts["root"]["transform"]).reshape(4, 4).T
    ecef = mat @ np.array([0, 0, 0, 1.0])
    to_ll = Transformer.from_crs(4978, 4979, always_xy=True)
    lon, lat, h = to_ll.transform(*ecef[:3])
    assert lon == pytest.approx(LON, abs=1e-7) and lat == pytest.approx(LAT, abs=1e-7)
    assert h == pytest.approx(30.0, abs=0.2)
    assert all("contents" in c for c in ts["root"]["children"])


def test_enu_roundtrip():
    frame = EnuFrame(LON, LAT, 30.0)
    proj = Projector("EPSG:4326", frame)
    lon, lat = proj.enu_to_lonlat(np.array([123.0]), np.array([-456.0]))
    enu = proj.lonlat_to_enu(lon, lat, np.array([30.0]))
    assert enu[0, 0] == pytest.approx(123.0, abs=0.01) and enu[0, 1] == pytest.approx(-456.0, abs=0.01)


def test_inspect_cli(tmp_path, capsys):
    write_shp(tmp_path / "b.shp")
    assert main(["inspect", "--buildings", str(tmp_path / "b.shp")]) == 0
    out = capsys.readouterr().out
    assert "A16" in out and "EPSG:5186" in out and "단독주택" in out
