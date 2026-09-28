"""WP-15a: cross-check Map/GolmokTravelMath.h and Map/GolmokMapMath.h (pure C++) in g++ CI.

The headers have no Unreal dependency, so fixtures/ue/travelmath_driver.cpp compiles them into a small
stdin/stdout driver. Checked against golmok_tools.zone.transform / .index and numpy:

- spawn position_enu (zone-local m) -> level UE cm = S * (zone-local -> area ENU) * p for the committed
  fixture zones and random zones (the S M S^-1 actor matrix the UE zone root carries), 1e-6 cm;
- spawn yaw_deg -> UE Yaw: the heading of the zone-local direction (cos, sin, 0) in area ENU, negated
  (UE Yaw = -yaw_deg, spec §1); identity zone: yaw_deg 90 (north) -> UE -90;
- spec §1 fallback probe (+3 m above zone-local (0,0,0), straight down), hit / no-hit feet, heading yaw_deg 0;
- standing location = feet + half height + 2 cm; save yaw ENU <-> UE sign and normalisation;
- travel refusal order, poll verdicts, restore rules ①②③ (full truth table), periodic autosave rule;
- map: bbox <-> pixel (linear and Web Mercator) round trips, z16 cell == index.lonlat_to_tile, cell bounds ==
  index.tile_bounds, cell pixel rectangles tile the texture, world pixels.
Skipped when no C++ compiler is on PATH.
"""

from __future__ import annotations

import itertools
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from zone_util import REPO

from golmok_tools.zone import index as zi
from golmok_tools.zone import transform as T

MAP_DIR = REPO / "unreal" / "Golmok" / "Source" / "Golmok" / "Map"
HEADERS = (MAP_DIR / "GolmokTravelMath.h", MAP_DIR / "GolmokMapMath.h")
DRIVER_SRC = Path(__file__).parent / "fixtures" / "ue" / "travelmath_driver.cpp"
ZONES = REPO / "unreal" / "Golmok" / "Content" / "Golmok" / "Zones"
AREA = (37.5600, 126.9230, 40.0)  # spec §4 area origin = L_ZoneTest level origin
S = np.diag([100.0, -100.0, 100.0])
ALLOWED_INCLUDES = {"array", "cmath", "cstddef"}

REFUSAL = {"none": 0, "busy": 1, "photo": 2, "portal": 3, "unknown": 4, "region": 5, "player": 6}
RESTORE = {"none": 0, "saved": 1, "zone_spawn": 2, "home": 3}


@pytest.fixture(scope="module")
def driver(tmp_path_factory) -> Path:
    compiler = next((p for name in ("g++", "clang++", "c++") if (p := shutil.which(name))), None)
    if not compiler:
        pytest.skip("no g++/clang++ on PATH")
    exe = tmp_path_factory.mktemp("travelmath") / ("driver.exe" if sys.platform == "win32" else "driver")
    cmd = [
        compiler,
        "-std=c++17",
        "-O1",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-pedantic",
        f"-I{MAP_DIR}",
        str(DRIVER_SRC),
        "-o",
        str(exe),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0 and not res.stderr.strip(), res.stdout + res.stderr
    return exe


def run(driver: Path, lines: list[str]) -> list[list[float]]:
    out = subprocess.run(
        [str(driver)],
        input="\n".join(lines) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    rows = [[float(v) for v in line.split()] for line in out.splitlines()]
    assert len(rows) == len(lines)
    return rows


def fmt(*values) -> str:
    return " ".join(repr(float(v)) for v in values)


def mat(m: np.ndarray) -> str:
    return fmt(*np.asarray(m, dtype=np.float64).reshape(16))


def actor_matrix(zone_t: np.ndarray, area=AREA) -> np.ndarray:
    return T.ue_actor_matrix(T.zone_local_to_area_enu(zone_t, area))


def expected_spawn(zone_t: np.ndarray, pos, yaw_deg: float, area=AREA) -> tuple[np.ndarray, float]:
    """Independent path: zone-local -> area ENU (transform.py), then S; turned heading, negated."""
    m = T.zone_local_to_area_enu(zone_t, area)
    enu = (m @ np.array([*pos, 1.0]))[:3]
    d = m[:3, :3] @ np.array([math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg)), 0.0])
    return S @ enu, -math.degrees(math.atan2(d[1], d[0]))


def yaw_diff(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def fixture_manifests() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(ZONES.glob("z_*/v*/manifest.json"))]


# ---- purity ----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("header", HEADERS, ids=lambda p: p.name)
def test_headers_are_pure(header: Path):
    text = header.read_text(encoding="utf-8")
    assert text.lstrip().startswith("#pragma once")
    assert re.findall(r'^#include\s+"', text, re.M) == []
    assert set(re.findall(r"^#include\s+<([^>]+)>", text, re.M)) <= ALLOWED_INCLUDES
    for banned in ("CoreMinimal", "UCLASS", "UE_LOG", "std::min", "std::max", "printf", "FVector"):
        assert banned not in text, banned
    assert re.search(r"^\s*(?:PI|check)\b", text, re.M) is None


# ---- spawn -----------------------------------------------------------------------------------------------


def test_fixture_spawns_match_transform_py(driver):
    manifests = [m for m in fixture_manifests() if "spawn" in m]
    assert {m["zone_id"] for m in manifests} >= {"z_synthetic_001", "z_synthetic_002"}
    lines, expected = [], []
    for m in manifests:
        zone_t = T.from_row_major(m["transform"])
        pos, yaw = m["spawn"]["position_enu"], m["spawn"]["yaw_deg"]
        lines.append(f"spawn {mat(actor_matrix(zone_t))} {fmt(*pos, yaw)}")
        expected.append(expected_spawn(zone_t, pos, yaw))
    for got, (ue, yaw_ue) in zip(run(driver, lines), expected, strict=True):
        assert np.abs(np.array(got[:3]) - ue).max() < 1e-6
        assert yaw_diff(got[3], yaw_ue) < 1e-9


def test_random_zone_spawns(driver):
    rng = np.random.default_rng(15)
    lines, expected = [], []
    for _ in range(60):
        zone_t = T.zone_transform(
            AREA[0] + rng.uniform(-0.02, 0.02),
            AREA[1] + rng.uniform(-0.02, 0.02),
            AREA[2] + rng.uniform(-20, 60),
            rng.uniform(-180, 180),
        )
        pos, yaw = rng.uniform(-40, 40, 3), rng.uniform(-360, 360)
        lines.append(f"spawn {mat(actor_matrix(zone_t))} {fmt(*pos, yaw)}")
        expected.append(expected_spawn(zone_t, pos, yaw))
    for got, (ue, yaw_ue) in zip(run(driver, lines), expected, strict=True):
        assert np.abs(np.array(got[:3]) - ue).max() < 1e-6
        assert yaw_diff(got[3], yaw_ue) < 1e-7
        assert -180.0 < got[3] <= 180.0


def test_yaw_sign_on_identity_zone(driver):
    ident = mat(np.eye(4))
    rows = run(driver, [f"spawn {ident} {fmt(1, 2, 3, y)}" for y in (0, 90, 180, -90, 45)])
    assert rows[0] == [100.0, -200.0, 300.0, 0.0]  # ENU (x, y, z) m -> UE (100x, -100y, 100z) cm
    assert [r[3] for r in rows] == pytest.approx(
        [0.0, -90.0, 180.0, 90.0, -45.0], abs=1e-12
    )  # UE Yaw = -yaw_deg


def test_fallback_probe_and_feet(driver):
    zone_t = T.zone_transform(37.5620, 126.9250, 50.0, 30.0)
    a = actor_matrix(zone_t)
    origin = (a @ np.array([0.0, 0.0, 0.0, 1.0]))[:3]
    hit = origin + np.array([0.0, 0.0, -12.5])
    miss, got_hit = run(driver, [f"fallback {mat(a)} 0 0 0 0", f"fallback {mat(a)} 1 {fmt(*hit)}"])
    assert np.abs(np.array(miss[0:3]) - (origin + [0, 0, 300.0])).max() < 1e-9  # +3 m
    assert miss[3:5] == pytest.approx(list(origin[:2]), abs=1e-9) and miss[5] == pytest.approx(
        origin[2] - 5000.0
    )
    assert np.abs(np.array(miss[6:9]) - origin).max() < 1e-9  # no hit: zone-local (0,0,0)
    assert np.abs(np.array(got_hit[6:9]) - hit).max() < 1e-9
    _, yaw0 = expected_spawn(zone_t, (0, 0, 0), 0.0)
    assert yaw_diff(miss[9], yaw0) < 1e-9  # heading yaw_deg 0 = the zone +x axis
    assert yaw_diff(miss[9], -30.0) < 0.05  # ~ -zone yaw (meridian convergence is tiny here)


def test_standing_location_and_save_yaw(driver):
    rows = run(driver, ["stand 10 20 30 88", "yaw 190", "yaw -180", "yaw 37.5", "yaw 540"])
    assert rows[0] == [10.0, 20.0, 30.0 + 88.0 + 2.0]
    assert rows[1] == pytest.approx([-170.0, 170.0, 170.0])
    assert rows[2][0] == 180.0  # (-180, 180]
    assert rows[3] == pytest.approx([37.5, -37.5, -37.5])
    assert rows[4][0] == 180.0


# ---- decisions -------------------------------------------------------------------------------------------


def test_travel_refusal_order(driver):
    cases = []
    for traveling, photo, portal, known, player in itertools.product((0, 1), repeat=5):
        for km in (0.0, 31.0):
            cases.append((traveling, photo, portal, known, player, km, 30.0))
    cases.append((0, 0, 0, 1, 1, 1e6, 0.0))  # 0 = no region limit
    rows = run(driver, [f"check {' '.join(str(c) for c in case)}" for case in cases])
    for (traveling, photo, portal, known, player, km, max_km), (got,) in zip(cases, rows, strict=True):
        if traveling:
            want = "busy"
        elif photo:
            want = "photo"
        elif portal:
            want = "portal"
        elif not known:
            want = "unknown"
        elif max_km > 0 and km > max_km:
            want = "region"
        elif not player:
            want = "player"
        else:
            want = "none"
        assert got == REFUSAL[want], (traveling, photo, portal, known, player, km)


def test_poll_verdicts(driver):
    cases = [
        ((1, 0, 0.1, 0.35, 20), 0),  # loaded but the fade is still running
        ((1, 0, 0.35, 0.35, 20), 1),
        ((0, 0, 5.0, 0.35, 20), 0),
        ((0, 0, 20.0, 0.35, 20), 2),  # timeout
        ((1, 0, 25.0, 0.35, 20), 1),  # loaded wins over a late poll
        ((0, 1, 0.1, 0.35, 20), 3),  # load failed
        ((1, 1, 1.0, 0.35, 20), 3),
    ]
    rows = run(driver, [f"poll {' '.join(str(v) for v in args)}" for args, _ in cases])
    assert [r[0] for r in rows] == [want for _, want in cases]


def test_restore_truth_table(driver):
    cases, want = [], []
    for has_save, has_pos, zone_empty, home in itertools.product((0, 1), repeat=4):
        for saved_v, index_v in ((1, 1), (1, 2), (2, 1), (1, 0)):
            cases.append((has_save, has_pos, zone_empty, saved_v, index_v, home))
            if not has_save:
                w = "none"
            elif zone_empty:
                w = "saved" if has_pos else ("home" if home else "none")
            elif index_v > 0 and index_v == saved_v and has_pos:
                w = "saved"  # ① same zone and version
            elif index_v > 0:
                w = "zone_spawn"  # ② the zone exists with another version (or no position)
            else:
                w = "home" if home else "none"  # ② zone gone -> HomeZoneId, ③ otherwise nothing
            want.append(RESTORE[w])
    rows = run(driver, [f"restore {' '.join(str(v) for v in c)}" for c in cases])
    assert [r[0] for r in rows] == want


def test_autosave_rule(driver):
    cases = [
        ((100, 50, 60, 0, 5.0, 0.0), 0),  # interval not reached
        ((120, 50, 60, 0, 0.5, 5.0), 0),  # nothing changed
        ((120, 50, 60, 1, 0.0, 0.0), 1),  # pending event
        ((120, 50, 60, 0, 1.5, 0.0), 1),  # moved > 1 m
        ((120, 50, 60, 0, 0.0, 350.0), 0),  # -10 deg after normalisation: not more than 10
        ((120, 50, 60, 0, 0.0, 15.0), 1),
        ((120, 50, 0, 1, 9.0, 90.0), 0),  # interval 0 = off
    ]
    rows = run(driver, [f"autosave {' '.join(str(v) for v in args)}" for args, _ in cases])
    assert [r[0] for r in rows] == [want for _, want in cases]


# ---- map math --------------------------------------------------------------------------------------------


def merc_y(lat: float) -> float:
    return (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0


def test_bbox_pixel_round_trip(driver):
    bbox = (126.9150, 37.5550, 126.9350, 37.5700)
    w, h = 2048, 1536
    rng = np.random.default_rng(3)
    pts = list(zip(rng.uniform(bbox[0], bbox[2], 40), rng.uniform(bbox[1], bbox[3], 40), strict=True))
    for merc in (0, 1):
        rows = run(driver, [f"l2p {fmt(*bbox)} {w} {h} {merc} {fmt(lon, lat)}" for lon, lat in pts])
        for (lon, lat), (px, py, inside) in zip(pts, rows, strict=True):
            assert inside == 1.0
            assert px == pytest.approx((lon - bbox[0]) / (bbox[2] - bbox[0]) * w, abs=1e-6)
            if merc:
                v = (merc_y(lat) - merc_y(bbox[3])) / (merc_y(bbox[1]) - merc_y(bbox[3]))
            else:
                v = (bbox[3] - lat) / (bbox[3] - bbox[1])
            assert py == pytest.approx(v * h, abs=1e-6)
        back = run(driver, [f"p2l {fmt(*bbox)} {w} {h} {merc} {fmt(r[0], r[1])}" for r in rows])
        for (lon, lat), (blon, blat, ok) in zip(pts, back, strict=True):
            assert ok == 1.0 and abs(blon - lon) < 1e-11 and abs(blat - lat) < 1e-11
    corners = run(
        driver,
        [
            f"l2p {fmt(*bbox)} {w} {h} 1 {fmt(bbox[0], bbox[3])}",
            f"l2p {fmt(*bbox)} {w} {h} 1 {fmt(bbox[2], bbox[1])}",
            f"l2p {fmt(*bbox)} {w} {h} 0 {fmt(bbox[2] + 0.001, bbox[1])}",
            f"l2p {fmt(bbox[0], bbox[1], bbox[0], bbox[3])} {w} {h} 0 {fmt(bbox[0], bbox[1])}",
        ],
    )
    assert corners[0] == pytest.approx([0.0, 0.0, 1.0], abs=1e-9)  # north-west = pixel (0, 0)
    assert corners[1] == pytest.approx([w, h, 1.0], abs=1e-6)
    assert corners[2][2] == 0.0  # outside
    assert corners[3] == [0.0, 0.0, 0.0]  # degenerate bbox


def test_cells_match_index_py(driver):
    rng = np.random.default_rng(16)
    pts = [(126.9250, 37.5620), (126.9230, 37.5600), (126.9272636, 37.5620), (0.0, 0.0), (-180.0, 85.06)]
    pts += list(zip(rng.uniform(126.8, 127.1, 30), rng.uniform(37.4, 37.7, 30), strict=True))
    rows = run(driver, [f"cell {fmt(lon, lat)} 16" for lon, lat in pts])
    for (lon, lat), (x, y) in zip(pts, rows, strict=True):
        assert (int(x), int(y)) == zi.lonlat_to_tile(lon, lat, 16)
    tiles = [(55873, 25379), (55874, 25380), (0, 0), (65535, 65535)]
    for (x, y), got in zip(tiles, run(driver, [f"bounds {x} {y} 16" for x, y in tiles]), strict=True):
        assert np.abs(np.array(got) - np.array(zi.tile_bounds(x, y, 16))).max() < 1e-12


def test_cell_rects_tile_a_mercator_texture(driver):
    # A texture that is exactly the 3x3 cells around the fixture origin: each cell is a 256 px square.
    x0, y0 = 55872, 25378
    west, _, _, north = zi.tile_bounds(x0, y0, 16)
    _, south, east, _ = zi.tile_bounds(x0 + 2, y0 + 2, 16)
    bbox = (west, south, east, north)
    lines = [f"rect {x0 + i} {y0 + j} 16 {fmt(*bbox)} 768 768 1" for j in range(3) for i in range(3)]
    for k, rect in enumerate(run(driver, lines)):
        i, j = k % 3, k // 3
        assert rect == pytest.approx([256 * i, 256 * j, 256 * (i + 1), 256 * (j + 1)], abs=1e-6)
    picks = run(
        driver,
        [f"p2c {fmt(*bbox)} 768 768 1 {px} {py} 16" for px, py in ((0, 0), (300, 700), (767, 767), (768, 0))],
    )
    assert picks[0] == [1.0, x0, y0]
    assert picks[1] == [1.0, x0 + 1, y0 + 2]
    assert picks[2] == [1.0, x0 + 2, y0 + 2]
    assert picks[3][0] == 0.0  # off the texture


def test_world_pixel(driver):
    rows = run(
        driver, ["world 0 0 0 256", "world -180 85.0511287798066 1 256", "world 126.925 37.562 16 256"]
    )
    assert rows[0] == pytest.approx([128.0, 128.0])
    assert rows[1] == pytest.approx([0.0, 0.0], abs=1e-6)
    x, y = zi.lonlat_to_tile(126.925, 37.562, 16)
    assert int(rows[2][0] // 256) == x and int(rows[2][1] // 256) == y
