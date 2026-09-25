import json

import pytest
from shapely.geometry import Polygon
from zone_util import make_zone, rect_footprint

from golmok_tools.zone import index as zi
from golmok_tools.zone import schema


def test_tile_math_known_values():
    assert zi.lonlat_to_tile(0.0, 0.0) == (32768, 32768)
    assert zi.lonlat_to_tile(-180.0, 85.06) == (0, 0)  # clamped to the Mercator limit
    assert zi.lonlat_to_tile(179.9999, -85.06) == (65535, 65535)
    # Seoul, Yeonnam-dong: x = floor(306.925 / 360 * 65536)
    x, y = zi.lonlat_to_tile(126.9250, 37.5620)
    assert x == 55873
    w, s, e, n = zi.tile_bounds(x, y)
    assert w <= 126.9250 < e and s <= 37.5620 < n
    assert (e - w) == pytest.approx(360 / 65536)


@pytest.mark.parametrize("lon, lat", [(126.9250, 37.5620), (-73.98, 40.75), (151.2, -33.86), (0.001, -0.001)])
def test_tile_bounds_contain_point(lon, lat):
    x, y = zi.lonlat_to_tile(lon, lat, 16)
    w, s, e, n = zi.tile_bounds(x, y, 16)
    assert w <= lon < e and s <= lat < n


def test_polygon_tiles_use_shape_not_bbox():
    x, y = zi.lonlat_to_tile(126.9250, 37.5620)
    w, s, e, n = zi.tile_bounds(x, y)
    tw, th = e - w, n - s

    def at(u, v):  # position in tile units from the SW corner of (x, y); +v is north
        return (w + u * tw, s + v * th)

    # triangle under the line v = u - 0.2: covers (x, y), (x+1, y), (x+1, y-1) but not (x, y-1),
    # although its bbox covers all four
    tri = Polygon([at(0.3, 0.1), at(1.9, 0.1), at(1.9, 1.7)])
    tiles = set(zi.tiles_for_polygon(tri))
    assert tiles == {(x, y), (x + 1, y), (x + 1, y - 1)}  # (x, y - 1) is in the bbox only
    for tx, ty in tiles:
        assert tri.intersects(Polygon.from_bounds(*zi.tile_bounds(tx, ty)))


def test_build_index_latest_valid_version_and_order(tmp_path):
    make_zone(tmp_path, "z_a_001", priority=5)
    make_zone(tmp_path, "z_b_001", version=1, priority=5)
    make_zone(tmp_path, "z_b_001", version=2, priority=5)
    make_zone(tmp_path, "z_c_001", priority=20, lat=37.5621)
    # z_d: v2 broken -> falls back to v1
    make_zone(tmp_path, "z_d_001", version=1)
    make_zone(tmp_path, "z_d_001", version=2, edit=lambda d: d.update(kind="bogus"))
    # interior far away in its own cell
    make_zone(tmp_path, "z_e_001_in", kind="interior", parent="z_a_001", lat=37.5700, lon=126.9400)
    (tmp_path / "not_a_zone").mkdir()

    problems = []
    zones, cells = zi.build_index(tmp_path, problems)
    by_id = {z["id"]: z for z in zones["zones"]}
    assert list(by_id) == sorted(by_id)
    assert by_id["z_b_001"]["version"] == 2
    assert by_id["z_b_001"]["manifest"] == "z_b_001/v2/manifest.json"
    assert by_id["z_d_001"]["version"] == 1
    assert by_id["z_e_001_in"]["kind"] == "interior"
    assert any("z_d_001/v2" in p for p in problems)
    assert any("not_a_zone" in p for p in problems)

    home = zi.lonlat_to_tile(126.9250, 37.5620)
    assert {z["id"] for z in cells[(16, *home)]["zones"]} == {"z_a_001", "z_b_001", "z_c_001", "z_d_001"}
    cell = next(c for c in cells.values() if any(z["id"] == "z_c_001" for z in c["zones"]))
    ids = [z["id"] for z in cell["zones"]]
    assert ids[0] == "z_c_001"  # priority 20 first
    assert ids.index("z_b_001") < ids.index("z_a_001")  # same priority: newer version first
    far = zi.lonlat_to_tile(126.9400, 37.5700)
    assert cells[(16, *far)]["zones"] == [{"id": "z_e_001_in", "version": 1}]

    assert schema.validate_index(zones) == []
    for c in cells.values():
        assert schema.validate_index(c) == []
        bbox = by_id[c["zones"][0]["id"]]["bbox_wgs84"]
        assert Polygon.from_bounds(*bbox).intersects(Polygon.from_bounds(*zi.tile_bounds(c["x"], c["y"])))


def test_bbox_matches_footprint(tmp_path):
    make_zone(tmp_path, "z_a_001")
    zones, _ = zi.build_index(tmp_path)
    fp = rect_footprint(37.5620, 126.9250, 40, 20)
    lons = [p[0] for p in fp["coordinates"][0]]
    lats = [p[1] for p in fp["coordinates"][0]]
    assert zones["zones"][0]["bbox_wgs84"] == pytest.approx([min(lons), min(lats), max(lons), max(lats)])


def test_write_index_removes_stale_cells(tmp_path):
    zroot = tmp_path / "zones"
    make_zone(zroot, "z_a_001")
    out = tmp_path / "index"
    (out / "cells").mkdir(parents=True)
    (out / "cells" / "16_1_1.json").write_text("{}", encoding="utf-8")
    zones, cells = zi.build_index(zroot)
    written = zi.write_index(zones, cells, out)
    assert not (out / "cells" / "16_1_1.json").exists()
    assert json.loads((out / "zones.json").read_text(encoding="utf-8")) == zones
    assert len(written) == 1 + len(cells)
    for (z, x, y), c in cells.items():
        assert json.loads((out / "cells" / f"{z}_{x}_{y}.json").read_text(encoding="utf-8")) == c


def test_scan_zones_skips_index_folder(tmp_path):
    """WP-09: the index lives inside the zones root (spec §6 layout); scan_zones must not report it."""
    from golmok_tools.zone.cli import main as zone_main

    make_zone(tmp_path, "z_a_001")
    (tmp_path / zi.INDEX_DIR_NAME / "cells").mkdir(parents=True)
    entries, problems = zi.scan_zones(tmp_path)
    assert [e.id for e in entries] == ["z_a_001"]
    assert problems == []
    out = tmp_path / zi.INDEX_DIR_NAME
    assert zone_main(["index", "build", "--zones-root", str(tmp_path), "--out", str(out), "--strict"]) == 0
    assert (out / "zones.json").is_file()
    # a second build over the same root (now holding zones.json + cells) is still clean
    assert zone_main(["index", "build", "--zones-root", str(tmp_path), "--out", str(out), "--strict"]) == 0
    zones = json.loads((out / "zones.json").read_text(encoding="utf-8"))
    assert [z["id"] for z in zones["zones"]] == ["z_a_001"]
