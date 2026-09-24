"""contour-dem on a synthetic hill: circular 5 m contours + spot heights -> DEM close to the truth."""

from pathlib import Path

import numpy as np
import pytest

shapefile = pytest.importorskip("shapefile")
rasterio = pytest.importorskip("rasterio")
pytest.importorskip("scipy")
from pyproj import CRS, Transformer  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402

from golmok_tools.basemap.build import main  # noqa: E402
from golmok_tools.basemap.contour_dem import contour_dem  # noqa: E402

LAT, LON = 37.5620, 126.9250
EPSG = "EPSG:5186"
CX, CY = Transformer.from_crs("EPSG:4326", EPSG, always_xy=True).transform(LON, LAT)


def hill(x, y):
    """20 m plain with a 60 m cone (peak 80 m) whose slope is 1:10, centred 100 m east."""
    r = np.hypot(x - (CX + 100), y - CY)
    return 20 + np.maximum(0, 60 - r / 10)


def write_prj(path: Path):
    path.with_suffix(".prj").write_text(CRS.from_user_input(EPSG).to_wkt("WKT1_ESRI"), encoding="utf-8")


def write_contours(path: Path, field="등고수치"):
    w = shapefile.Writer(str(path), shapeType=shapefile.POLYLINE, encoding="cp949")
    w.field(field, "N", 8, 2)
    for h in range(25, 80, 5):
        r = (80 - h) * 10
        a = np.linspace(0, 2 * np.pi, 90)
        ring = np.c_[CX + 100 + r * np.cos(a), CY + r * np.sin(a)]
        w.line([ring.tolist()])
        w.record(h)
    w.line([[(CX - 50, CY), (CX - 40, CY)]])  # a contour without a height is skipped
    w.record(None)
    w.close()
    write_prj(path)


def write_spots(path: Path, n=400, field="표고수치"):
    rng = np.random.default_rng(2)
    w = shapefile.Writer(str(path), shapeType=shapefile.POINT, encoding="cp949")
    w.field(field, "N", 8, 2)
    xs = CX + rng.uniform(-1200, 1200, n)
    ys = CY + rng.uniform(-1200, 1200, n)
    for x, y in zip(xs, ys, strict=True):
        w.point(x, y)
        w.record(round(float(hill(x, y)), 2))
    w.close()
    write_prj(path)


def write_fill_dem(path: Path):
    res, size = 90.0, 60
    x0, y1 = CX - size * res / 2, CY + size * res / 2
    cols, rows = np.meshgrid(np.arange(size), np.arange(size))
    z = hill(x0 + (cols + 0.5) * res, y1 - (rows + 0.5) * res)
    with rasterio.open(path, "w", driver="GTiff", width=size, height=size, count=1, dtype="float32",
                       crs=EPSG, transform=from_origin(x0, y1, res, res)) as ds:  # fmt: skip
        ds.write(z.astype(np.float32), 1)


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    d = tmp_path_factory.mktemp("contour")
    write_contours(d / "contour.shp")
    write_spots(d / "spots.shp")
    write_fill_dem(d / "fill.tif")
    return d


def test_dem_matches_surface(data, tmp_path):
    out = tmp_path / "dem.tif"
    st = contour_dem([data / "contour.shp"], [data / "spots.shp"], LAT, LON, 1000.0, out,
                     res=5.0, smooth=1.0, fill_dem=[data / "fill.tif"])  # fmt: skip
    assert st["skipped_features"] == 1
    assert st["spot_heights"] == 400
    assert st["holdout_rmse"] < 1.5
    with rasterio.open(out) as ds:
        assert ds.crs.to_epsg() == 5186 and ds.res == (5.0, 5.0) and ds.width == 400
        z = ds.read(1)
        cols, rows = np.meshgrid(np.arange(ds.width), np.arange(ds.height))
        x = ds.transform.c + (cols + 0.5) * ds.transform.a
        y = ds.transform.f + (rows + 0.5) * ds.transform.e
    assert np.isfinite(z).all()
    err = z - hill(x, y)
    assert np.sqrt(np.mean(err**2)) < 1.0
    # the cone's slope between the 25 m and 75 m contours is followed closely; above the top contour
    # only spot heights constrain the summit (the known limit of contour interpolation)
    r = np.hypot(x - (CX + 100), y - CY)
    assert np.abs(err[(r > 60) & (r < 540)]).max() < 1.5


def test_needs_fill_dem_when_points_do_not_cover(data, tmp_path):
    with pytest.raises(ValueError, match="fill-dem"):
        contour_dem([data / "contour.shp"], [], LAT, LON, 1000.0, tmp_path / "dem.tif")


def test_cli(data, tmp_path, capsys):
    out = tmp_path / "dem_cli.tif"
    rc = main(["contour-dem", "--contours", str(data / "contour.shp"), "--spots", str(data / "spots.shp"),
               "--center", f"{LAT},{LON}", "--half-size", "600", "--fill-dem", str(data / "fill.tif"),
               "--out", str(out)])  # fmt: skip
    assert rc == 0 and out.exists()
    assert "RMSE" in capsys.readouterr().out
