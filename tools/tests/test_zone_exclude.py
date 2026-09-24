import numpy as np
import pytest
from shapely.geometry import shape
from zone_util import make_zone

from golmok_tools.zone import manifest as zm
from golmok_tools.zone.exclude import buffered_footprint, build_exclude

LAT, LON = 37.5620, 126.9250


def local_area(geom: dict) -> float:
    return zm.footprint_enu(geom, (LAT, LON, 0.0)).area


def test_overlapping_zones_merge_and_interior_is_skipped(tmp_path):
    make_zone(tmp_path, "z_a_001", size=(40, 20))
    # 30 m east: overlaps z_a by 10 m
    make_zone(tmp_path, "z_b_001", lon=LON + 30 / (111320 * np.cos(np.radians(LAT))), size=(40, 20))
    # 500 m north: separate polygon
    make_zone(tmp_path, "z_c_001", lat=LAT + 500 / 110950)
    make_zone(tmp_path, "z_d_001_in", kind="interior", parent="z_a_001", size=(200, 200))
    fc, problems = build_exclude(tmp_path, buffer_m=0.0)
    assert problems == []
    assert fc["type"] == "FeatureCollection"
    ids = [f["properties"]["zone_ids"] for f in fc["features"]]
    assert sorted(ids) == [["z_a_001", "z_b_001"], ["z_c_001"]]
    merged = next(f for f in fc["features"] if len(f["properties"]["zone_ids"]) == 2)
    assert local_area(merged["geometry"]) == pytest.approx(70 * 20, rel=2e-3)  # east offset is approximate


@pytest.mark.parametrize("buffer_m", [0.5, 0.75, 1.0])
def test_buffer_grows_footprint_by_meters(tmp_path, buffer_m):
    _, d = make_zone(tmp_path, "z_a_001", size=(40, 20))
    grown = buffered_footprint(d, buffer_m)
    local = zm.footprint_enu(
        {"type": "Polygon", "coordinates": [list(grown.exterior.coords)]}, (LAT, LON, 50.0)
    )
    minx, miny, maxx, maxy = local.bounds
    # mitre join keeps a rectangle: each side moves out by buffer_m
    assert np.allclose(
        [minx, miny, maxx, maxy], [-20 - buffer_m, -10 - buffer_m, 20 + buffer_m, 10 + buffer_m], atol=2e-3
    )


def test_negative_buffer_rejected(tmp_path):
    with pytest.raises(ValueError):
        build_exclude(tmp_path, buffer_m=-1)


def test_output_feeds_golmok_basemap_exclude(tmp_path):
    """golmok-basemap build --exclude reads this file and drops buildings that intersect it."""
    from golmok_tools.basemap.build import _load_exclude
    from golmok_tools.basemap.geo import EnuFrame, Projector

    make_zone(tmp_path / "zones", "z_a_001", size=(40, 20))
    fc, _ = build_exclude(tmp_path / "zones", buffer_m=0.75)
    path = zm.write_json(fc, tmp_path / "exclude.geojson")
    projector = Projector("EPSG:4326", EnuFrame(lon=LON, lat=LAT, height=0.0))
    polys = _load_exclude(path, projector)
    assert len(polys) == 1
    assert polys[0].area == pytest.approx(41.5 * 21.5, rel=1e-3)
    assert shape(fc["features"][0]["geometry"]).is_valid
