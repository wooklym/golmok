"""Synthetic RealityScan-like zone for WP-06: raw OBJ/MTL/UDIM PNGs -> real golmok-mesh pipeline -> zone.

    python tools/scripts/make_synthetic_zone.py --out <dir> [--zone-id z_synthetic_scan_001] [--interior]
                                                [--tile-px 256] [--force] [--check] [--quiet]

Writes (WP-06 design §3-7):
    <out>/recon/<zone_id>/     scan.obj, scan.mtl, tex/{ground.png, facade.1001.png, facade.1002.png,
                               facade.1011.png} -- the "export"; textures live outside the zone version folder
    <out>/zones/<zone_id>/v1/  manifest.json, visual/ (15 m grid chunks, rewritten MTL, chunk_manifest.json),
                               collision.glb, collision/<chunk>.glb, blockers.json/.glb, expected.json
    --interior                 <out>/recon/<zone_id>_room/ and <out>/zones/<zone_id>_room/v1/: the room behind
                               the door as an interior zone of its own (portals door_1 <-> door_out)

The zone folder comes out of golmok_tools.mesh.cli (chunk -> collision --per-chunk --no-snap-ground ->
blockers) and golmok_tools.zone.cli validate --check-files --strict, exactly like a real scan. expected.json
is the source of the numbers the runbook (docs/runbooks/pc-verify-wp06.md) and the tests quote; it is computed
from the generated files, UE level coordinates with golmok_tools.zone.transform (area origin 37.56/126.923/40,
spec §4 C).

Geometry (zone-local ENU m, Z-up; the exterior is the same with or without --interior, the door hole is
always cut):
    ground    x -15..15, y 0..15, 5 m cells, z = 0.02 x          material ground (single texture)    36 tris
    facade A  thin wall x 1..9, y 7.0..7.2, z 0..6, door x 4..6 z 0..2.2       facade tile 1001 red   36 tris
    facade B  thin wall x -11..-5, y 5.0..5.2, z 0..5, window x -9.5..-6.5 z 0.25..2.75  tile 1002    48 tris
    block C   solid box x 10..13, y 2..4, z 0..2                                tile 1011 blue         12 tris
    room      (--interior, room-local, origin = exterior (1, 7.2, 0)) floor, west/east/north walls and
              ceiling of an 8 x 6.8 x 3 m room, 0.2 m thick           material room tile 1001 yellow  60 tris

Textures are pure-Python PNGs (zlib + struct): solid colour, 2 px black border, white squares top-left (as
many as the tile's position in its UDIM set) and the tile number in a 5x7 bitmap font (ground.png, not UDIM,
has no number). UE flips UDIM tiles vertically on import and adjusts the mesh UVs, so the numbers must read
normally in the viewport. No timestamps, no randomness: two runs give identical files; --check regenerates
into a temp folder and compares. stdout carries only "wrote <relpath>" lines and the final "next: ..." line,
ASCII only.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import shutil
import struct
import sys
import tempfile
import zlib
from pathlib import Path

try:
    import numpy as np

    from golmok_tools.mesh.cli import main as mesh_main
    from golmok_tools.mesh.objio import Mesh, write_obj
    from golmok_tools.zone import manifest as zm
    from golmok_tools.zone import transform
    from golmok_tools.zone.cli import main as zone_main
except ImportError:  # no `pip install -e tools`: import from the checkout
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    try:
        import numpy as np

        from golmok_tools.mesh.cli import main as mesh_main
        from golmok_tools.mesh.objio import Mesh, write_obj
        from golmok_tools.zone import manifest as zm
        from golmok_tools.zone import transform
        from golmok_tools.zone.cli import main as zone_main
    except ImportError as e:
        sys.stderr.write(f'ERROR install tools with pip install -e ".[zone,mesh]" ({e})\n')
        raise SystemExit(2) from None

DEFAULT_ZONE_ID = "z_synthetic_scan_001"
DEFAULT_TILE_PX = 256
VERSION = 1
CHUNK_SIZE_M = 15.0
ZONE_ORIGIN = (37.5620, 126.9250, 50.0)  # lat, lon, ellipsoidal h (spec §4 B)
AREA_ORIGIN = (37.5600, 126.9230, 40.0)  # level (CesiumGeoreference) origin, spec §4 C
FOOTPRINT_M = (32.0, 17.0, 0.0, 7.5)  # w, h, dx, dy: x -16..16, y -1..16
ZONE_TEST_MAP = "/Game/Golmok/Maps/L_ZoneTest"
MASTER_MATERIAL = "/Game/Golmok/Materials/M_ZoneScan"
OBJ_HEADER = "make_synthetic_zone.py (WP-06 synthetic scan, not a real capture)"

# ---- geometry (ENU m) ----
GROUND_X = (-15.0, 15.0)
GROUND_Y = (0.0, 15.0)
GROUND_CELL_M = 5.0
GROUND_SLOPE = 0.02  # z = 0.02 x: -0.3 .. 0.3
DOOR_1 = (5.0, 7.0, 0.0)  # portal door_1 (exterior), yaw 90 = facing north into the room
DOOR_RADIUS_M = 1.0  # hole x = 5 +- 1.0 (door_openings rule: the portal radius)
DOOR_HEIGHT_M = 2.2
WALL_A = ((1.0, 7.0, 0.0), (9.0, 7.2, 6.0))
WALL_B = ((-11.0, 5.0, 0.0), (-5.0, 5.2, 5.0))
WINDOW = ((-9.5, -6.5), (0.25, 2.75))  # x range, z range of the glass hole in wall B
BLOCK_C = ((10.0, 2.0, 0.0), (13.0, 4.0, 2.0))
DOOR_OPENING = ((DOOR_1[0] - DOOR_RADIUS_M, DOOR_1[0] + DOOR_RADIUS_M), (0.0, DOOR_HEIGHT_M))
# (look, UDIM tile, wall box, opening) -- design §3-7 geometry table
WALLS = (
    ("red facade with door hole (1001)", 1001, WALL_A, DOOR_OPENING),
    ("green facade with glass window (1002)", 1002, WALL_B, WINDOW),
    ("blue block (1011)", 1011, BLOCK_C, None),
)
GROUND_LOOK = "grey ground"
ROOM_ORIGIN_IN_PARENT_M = (1.0, 7.2, 0.0)  # south-west floor corner of the room, right behind facade A
ROOM_SIZE_M = (8.0, 6.8, 3.0)  # inner x, y extent and wall height
ROOM_WALL_M = 0.2
ROOM_TILE = 1001
ROOM_LOOK = "yellow room (1001)"
# door_out = door_1 in room-local coordinates: (4, -0.2, 0), yaw -90 (facing south, out of the room)
DOOR_OUT = tuple(round(a - b, 6) for a, b in zip(DOOR_1, ROOM_ORIGIN_IN_PARENT_M, strict=True))
PLAYER_START_ENU = (0.0, 2.0, 1.5)
INTERIOR_LIGHT_Z_MAX_CM = 250.0
WALK = (
    "from PlayerStart (0,2) m: north-west to the green wall (x -11..-5, y 5) - the glass window at "
    "x -9.5..-6.5 blocks you although you see through it; east to the red facade (x 1..9, y 7) - the door "
    "hole at x 4..6 lets you through (door_1 portal with --interior); the blue block at x 10..13 is a 2 m "
    "obstacle"
)

# ---- textures ----
TILE_COLORS = {
    "facade": {1001: (200, 60, 60), 1002: (60, 200, 60), 1011: (60, 60, 200)},
    "ground": {None: (120, 120, 120)},  # not UDIM: ground.png
    "room": {1001: (200, 200, 60)},
}
BORDER_PX = 2
SQUARE_PX, SQUARE_GAP_PX = 12, 4  # at 256 px; scaled with --tile-px
GLYPH_SCALE, GLYPH_TOP_PX = 8, 100  # 5x7 font x8 = 40x56 px, 8 px apart, rows 100..156 at 256 px
FONT_5X7 = {
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
}

SCAN_MTL = (
    "newmtl ground\nKd 1 1 1\nmap_Kd tex/ground.png\n\n"
    "newmtl facade\nKd 1 1 1\nmap_Kd -bm 1 tex/facade.<UDIM>.png\n"
)
ROOM_MTL = "newmtl room\nKd 1 1 1\nmap_Kd tex/room.1001.png\n"


class GenerateError(Exception):
    """Pipeline or validation failure; str() is what goes to stderr."""


# ---- output helpers ----


def _ascii(text: str) -> str:
    return text.encode("ascii", "backslashreplace").decode("ascii")


def _say(line: str) -> None:
    sys.stdout.write(_ascii(line) + "\n")


def _path_literal(path: str) -> str:
    """Python literal for `path` that survives _ascii: r"..." when plain ASCII, else ascii() escapes."""
    if path.isascii() and not path.endswith("\\") and '"' not in path:
        return f'r"{path}"'
    return ascii(path)


def _err(line: str) -> None:
    sys.stderr.write(_ascii(line) + "\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _round(v, ndigits: int) -> float:
    return round(float(v), ndigits) + 0.0  # + 0.0 turns -0.0 into 0.0


# ---- PNG (pure Python) ----


def write_png_rgb(path: str | Path, w: int, h: int, rows: list[bytes]) -> Path:
    """8-bit RGB PNG: signature, IHDR, one IDAT (filter-0 rows, zlib level 6), IEND. CRC = zlib.crc32."""
    if len(rows) != h or any(len(r) != 3 * w for r in rows):
        raise ValueError("rows must be h rows of 3*w bytes")

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"".join(b"\x00" + row for row in rows), 6)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return path


def read_png_rgb(data: bytes) -> tuple[int, int, bytes]:
    """(w, h, pixels) of a PNG written by write_png_rgb (8-bit RGB, filter-0 rows)."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, w, h, idat = 8, 0, 0, b""
    while pos + 8 <= len(data):
        length, tag = struct.unpack(">I4s", data[pos : pos + 8])
        body = data[pos + 8 : pos + 8 + length]
        if tag == b"IHDR":
            w, h, depth, color = struct.unpack(">IIBB", body[:10])
            if (depth, color) != (8, 2):
                raise ValueError("only 8-bit RGB")
        elif tag == b"IDAT":
            idat += body
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = 3 * w + 1
    if len(raw) != stride * h:
        raise ValueError("bad IDAT length")
    rows = []
    for y in range(h):
        if raw[y * stride] != 0:
            raise ValueError("only filter 0")
        rows.append(raw[y * stride + 1 : (y + 1) * stride])
    return w, h, b"".join(rows)


def tile_rows(px: int, color: tuple[int, int, int], squares: int, label: str | None) -> list[bytes]:
    """Pixel rows of one tile: background colour, black border, white squares top-left, `label` digits."""
    canvas = bytearray(bytes(color) * (px * px))

    def fill(x0: int, y0: int, x1: int, y1: int, rgb: tuple[int, int, int]) -> None:
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(px, x1), min(px, y1)
        for y in range(y0, y1):
            canvas[3 * (y * px + x0) : 3 * (y * px + x1)] = bytes(rgb) * (x1 - x0)

    white, black = (255, 255, 255), (0, 0, 0)
    s = px / DEFAULT_TILE_PX
    sq, gap = max(1, round(SQUARE_PX * s)), max(1, round(SQUARE_GAP_PX * s))
    for k in range(squares):
        fill(gap + k * (sq + gap), gap, gap + k * (sq + gap) + sq, gap + sq, white)
    if label:
        g = max(1, round(GLYPH_SCALE * s))
        width = len(label) * 5 * g + (len(label) - 1) * g
        x, y0 = (px - width) // 2, round(GLYPH_TOP_PX * s)
        for ch in label:
            for r, row in enumerate(FONT_5X7[ch]):
                for c, bit in enumerate(row):
                    if bit == "1":
                        fill(x + c * g, y0 + r * g, x + (c + 1) * g, y0 + (r + 1) * g, white)
            x += 6 * g
    fill(0, 0, px, BORDER_PX, black)
    fill(0, px - BORDER_PX, px, px, black)
    fill(0, 0, BORDER_PX, px, black)
    fill(px - BORDER_PX, 0, px, px, black)
    return [bytes(canvas[3 * y * px : 3 * (y + 1) * px]) for y in range(px)]


def write_tiles(tex_dir: Path, base: str, px: int) -> list[Path]:
    """<base>.<tile>.png per UDIM tile (or <base>.png for the single texture), numbered in set order."""
    out = []
    for k, (tile, color) in enumerate(sorted(TILE_COLORS[base].items(), key=lambda kv: kv[0] or 0), start=1):
        name = f"{base}.png" if tile is None else f"{base}.{tile}.png"
        rows = tile_rows(px, color, k, None if tile is None else f"{tile:04d}")
        out.append(write_png_rgb(tex_dir / name, px, px, rows))
    return out


# ---- geometry ----


def box(lo, hi, udim_tile: int = 1001):
    """8 vertices, 12 triangles, UVs as tests/mesh_util.box: tile offset + 0.1..0.9, u along x, v along z."""
    v = np.array([[x, y, z] for z in (lo[2], hi[2]) for y in (lo[1], hi[1]) for x in (lo[0], hi[0])], float)
    f = np.array(
        [[0, 2, 1], [1, 2, 3], [4, 5, 6], [5, 7, 6], [0, 1, 4], [1, 5, 4],
         [2, 6, 3], [3, 6, 7], [0, 4, 2], [2, 4, 6], [1, 3, 5], [3, 7, 5]]
    )  # fmt: skip
    t = udim_tile - 1001
    u0, v0 = t % 10, t // 10
    uv = np.column_stack([u0 + 0.1 + 0.8 * (v[:, 0] - v[:, 0].min()) / (np.ptp(v[:, 0]) or 1),
                          v0 + 0.1 + 0.8 * (v[:, 2] - v[:, 2].min()) / (np.ptp(v[:, 2]) or 1)])  # fmt: skip
    return v, f, uv


def ground_grid():
    """Sloped ground z = GROUND_SLOPE x on GROUND_CELL_M cells; u = (x - x0)/(x1 - x0), v likewise in y."""
    (x0, x1), (y0, y1) = GROUND_X, GROUND_Y
    xs = np.linspace(x0, x1, int(round((x1 - x0) / GROUND_CELL_M)) + 1)
    ys = np.linspace(y0, y1, int(round((y1 - y0) / GROUND_CELL_M)) + 1)
    gx, gy = np.meshgrid(xs, ys, indexing="ij")
    v = np.stack([gx, gy, GROUND_SLOPE * gx], axis=-1).reshape(-1, 3)
    nx, ny = len(xs), len(ys)
    f = []
    for i in range(nx - 1):
        for j in range(ny - 1):
            a, b, c, d = i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1
            f += [[a, b, c], [a, c, d]]
    uv = np.stack([(gx - x0) / (x1 - x0), (gy - y0) / (y1 - y0)], axis=-1).reshape(-1, 2)
    return v, np.asarray(f), uv


def wall_pieces(lo, hi, opening) -> list[tuple[tuple, tuple]]:
    """A thin wall minus a rectangular hole: left, right, lintel, sill (pieces of zero size are dropped)."""
    if opening is None:
        return [(tuple(lo), tuple(hi))]
    (ox0, ox1), (oz0, oz1) = opening
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    pieces = [
        ((x0, y0, z0), (ox0, y1, z1)),
        ((ox1, y0, z0), (x1, y1, z1)),
        ((ox0, y0, oz1), (ox1, y1, z1)),
        ((ox0, y0, z0), (ox1, y1, oz0)),
    ]
    return [(a, b) for a, b in pieces if all(b[i] > a[i] for i in range(3))]


def exterior_boxes() -> list[tuple[str, int, tuple, tuple]]:
    """(look, tile, lo, hi) of every solid exterior box (facade pieces and the block)."""
    return [
        (look, tile, lo, hi) for look, tile, (wlo, whi), op in WALLS for lo, hi in wall_pieces(wlo, whi, op)
    ]


def room_boxes() -> list[tuple[tuple, tuple]]:
    """Floor, west wall, east wall, north wall, ceiling of the room in room-local ENU m (south side open)."""
    w, d, h = ROOM_SIZE_M
    t = ROOM_WALL_M
    return [
        ((0.0, 0.0, -t), (w, d, 0.0)),
        ((0.0, 0.0, 0.0), (t, d, h)),
        ((w - t, 0.0, 0.0), (w, d, h)),
        ((0.0, d - t, 0.0), (w, d, h)),
        ((0.0, 0.0, h), (w, d, h + t)),
    ]


def _assemble(parts, materials: list[str]) -> Mesh:
    vs, fs, uvs, mats, off = [], [], [], [], 0
    for (v, f, uv), mat in parts:
        vs.append(v)
        uvs.append(uv)
        fs.append(f + off)
        mats.append(np.full(len(f), mat))
        off += len(v)
    f = np.vstack(fs)
    return Mesh(v=np.vstack(vs), f_v=f, vt=np.vstack(uvs), f_vt=f.copy(), f_mat=np.concatenate(mats),
                materials=list(materials))  # fmt: skip


def exterior_mesh() -> Mesh:
    parts = [(ground_grid(), 0)] + [(box(lo, hi, tile), 1) for _, tile, lo, hi in exterior_boxes()]
    return _assemble(parts, ["ground", "facade"])


def room_mesh() -> Mesh:
    return _assemble([(box(lo, hi, ROOM_TILE), 0) for lo, hi in room_boxes()], ["room"])


def chunk_id_at(x: float, y: float, size: float = CHUNK_SIZE_M) -> str:
    """golmok_tools.mesh.chunk.grid_chunks id of the cell containing (x, y): c_<e|w><col>_<n|s><row>."""

    def signed(i: int, pos: str, neg: str) -> str:
        return f"{pos}{i:03d}" if i >= 0 else f"{neg}{-i:03d}"

    i, j = math.floor(x / size), math.floor(y / size)
    return f"c_{signed(i, 'e', 'w')}_{signed(j, 'n', 's')}"


def rect_footprint(lat: float, lon: float, w: float, h: float, dx: float = 0.0, dy: float = 0.0) -> dict:
    """GeoJSON Polygon: w x h m rectangle centered (dx, dy) m from (lat, lon) on its tangent plane."""
    xy = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2], [-w / 2, -h / 2]])
    xy += [dx, dy]
    lon_, lat_, _ = transform.enu_to_lonlat(np.column_stack([xy, np.zeros(5)]), (lat, lon, 0.0))
    ring = [[round(float(a), 9), round(float(b), 9)] for a, b in zip(lon_, lat_, strict=True)]
    ring[-1] = ring[0]
    return {"type": "Polygon", "coordinates": [ring]}


# ---- files ----


def output_files(zone_id: str, interior: bool) -> list[str]:
    """Exactly the files one run writes, relative to <out> with '/' (design §3-7)."""
    room = f"{zone_id}_room"
    files = [
        f"recon/{zone_id}/scan.obj",
        f"recon/{zone_id}/scan.mtl",
        f"recon/{zone_id}/tex/ground.png",
        f"recon/{zone_id}/tex/facade.1001.png",
        f"recon/{zone_id}/tex/facade.1002.png",
        f"recon/{zone_id}/tex/facade.1011.png",
        f"zones/{zone_id}/v1/manifest.json",
        f"zones/{zone_id}/v1/expected.json",
        f"zones/{zone_id}/v1/blockers.json",
        f"zones/{zone_id}/v1/blockers.glb",
        f"zones/{zone_id}/v1/collision.glb",
        f"zones/{zone_id}/v1/collision/c_e000_n000.glb",
        f"zones/{zone_id}/v1/collision/c_w001_n000.glb",
        f"zones/{zone_id}/v1/visual/c_e000_n000.obj",
        f"zones/{zone_id}/v1/visual/c_w001_n000.obj",
        f"zones/{zone_id}/v1/visual/scan.mtl",
        f"zones/{zone_id}/v1/visual/chunk_manifest.json",
    ]
    if interior:
        files += [
            f"recon/{room}/room.obj",
            f"recon/{room}/room.mtl",
            f"recon/{room}/tex/room.1001.png",
            f"zones/{room}/v1/manifest.json",
            f"zones/{room}/v1/expected.json",
            f"zones/{room}/v1/collision.glb",
            f"zones/{room}/v1/collision/c_e000_n000.glb",
            f"zones/{room}/v1/visual/c_e000_n000.obj",
            f"zones/{room}/v1/visual/room.mtl",
            f"zones/{room}/v1/visual/chunk_manifest.json",
        ]
    return files


def _zone_roots(out: Path, zone_id: str) -> list[Path]:
    return [out / kind / zid for kind in ("recon", "zones") for zid in (zone_id, f"{zone_id}_room")]


def tree_files(out: Path, zone_id: str) -> list[str]:
    """Every file under the recon/zones folders of the zone and its room, relative to <out> with '/'."""
    roots = [r for r in _zone_roots(out, zone_id) if r.is_dir()]
    return sorted(p.relative_to(out).as_posix() for r in roots for p in r.rglob("*") if p.is_file())


def _run(func, argv: list[str], log: list[str]) -> None:
    """In-process CLI call with its (Korean) stdout captured; a non-zero return is a GenerateError."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = func(argv)
    log.append(buf.getvalue())
    if rc != 0:
        raise GenerateError(f"{argv[0]} failed (rc {rc}):\n{buf.getvalue()}")


def _glb(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total != len(data):
        raise ValueError(f"{path}: not a GLB")
    json_len = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20 : 20 + json_len])
    bin_len = struct.unpack_from("<I", data, 20 + json_len)[0]
    return gltf, data[28 + json_len : 28 + json_len + bin_len]


def glb_triangles(path: Path) -> int:
    gltf, _ = _glb(path)
    acc = gltf["accessors"]
    prims = [p for m in gltf["meshes"] for p in m["primitives"] if "indices" in p]
    return sum(acc[p["indices"]]["count"] // 3 for p in prims)


def ue_bounds_cm(bbox_enu) -> list[list[float]]:
    """ENU (m) box -> UE cm box: TARGET = diag(100, -100, 100) on the 8 corners, min/max re-sorted."""
    (x0, y0, z0), (x1, y1, z1) = bbox_enu
    lo, hi = (100.0 * x0, -100.0 * y1, 100.0 * z0), (100.0 * x1, -100.0 * y0, 100.0 * z1)
    return [[_round(v, 6) for v in lo], [_round(v, 6) for v in hi]]


def _to_area(manifest: dict) -> np.ndarray:
    return transform.zone_local_to_area_enu(transform.from_row_major(manifest["transform"]), AREA_ORIGIN)


def level_ue_cm(manifest: dict, enu) -> list[float]:
    """Zone-local ENU m -> UE level cm with the area origin (spec §4 C), 2 decimals."""
    return [_round(v, 2) for v in transform.enu_to_ue(transform.apply(_to_area(manifest), enu))]


def zone_yaw_deg(manifest: dict) -> float:
    m = transform.ue_actor_matrix(_to_area(manifest))
    return _round(math.degrees(math.atan2(m[1, 0], m[0, 0])), 2)


def udim_blocks(tiles: list[int]) -> tuple[list[list[int]], list[int]]:
    """([u, v] per tile, canvas blocks (max u + 1, max v + 1)); [] -> (1, 1)."""
    coords = [[(t - 1001) % 10, (t - 1001) // 10] for t in tiles]
    if not coords:
        return [], [1, 1]
    return coords, [max(c[0] for c in coords) + 1, max(c[1] for c in coords) + 1]


def _texture_sets(recon: Path, tile_px: int) -> dict:
    """{T_<base>: {...}} from the PNG files in <recon>/tex (UDIM sets by BaseName.####.png)."""
    sets: dict[str, list[int | None]] = {}
    for p in sorted((recon / "tex").glob("*.png")):
        parts = p.name.split(".")
        if len(parts) == 3 and len(parts[1]) == 4 and parts[1].isdigit() and 1001 <= int(parts[1]) <= 1999:
            sets.setdefault(parts[0], []).append(int(parts[1]))
        else:
            sets.setdefault(p.name[: -len(p.suffix)], []).append(None)
    out = {}
    for base, found in sorted(sets.items()):
        tiles = sorted(t for t in found if t is not None)
        _, blocks = udim_blocks(tiles)
        colors = {"single" if t is None else str(t): list(TILE_COLORS[base][t]) for t in tiles or [None]}
        out[f"T_{base}"] = {
            "tiles": tiles,
            "tile_px": tile_px,
            "canvas_blocks": blocks,
            "canvas_px": [tile_px * blocks[0], tile_px * blocks[1]],
            "colors": colors,
        }
    return out


def _chunks_expected(zone_id: str, chunk_manifest: dict, looks: dict[str, list[str]]) -> dict:
    out = {}
    for e in sorted(chunk_manifest["chunks"], key=lambda c: c["id"]):
        out[e["id"]] = {
            "asset": f"/Game/Golmok/Zones/{zone_id}/v{VERSION}/SM_{e['id']}",
            "tris": e["tris"],
            "bbox_enu": e["bbox_enu"],
            "ue_bounds_cm": ue_bounds_cm(e["bbox_enu"]),
            "materials": e["materials"],
            "udim_tiles": e["udim_tiles"],
            "look": ", ".join(looks.get(e["id"], [])),
        }
    return out


def _collision_expected(zone_id: str, vdir: Path, manifest: dict) -> dict:
    col = manifest["layers"]["collision"]
    chunks = col.get("chunks") or []
    mode = "chunks" if chunks else "single"
    out = {"mode": mode, "total_tris": glb_triangles(vdir / col["uri"]), "chunks": {}}
    for c in sorted(chunks, key=lambda c: c["id"]):
        out["chunks"][c["id"]] = {
            "asset": f"/Game/Golmok/Zones/{zone_id}/v{VERSION}/SM_{zone_id}_collision_{c['id']}",
            "tris": glb_triangles(vdir / c["uri"]),
            "ue_bounds_cm": ue_bounds_cm(c["bbox_enu"]),
        }
    return out


def _materials_expected(chunk_manifest: dict) -> list[str]:
    return sorted({f"MI_{m}" for c in chunk_manifest["chunks"] for m in c["materials"]})


def exterior_looks(chunk_manifest: dict) -> dict[str, list[str]]:
    """chunk id -> looks of the elements whose faces fall into that 15 m cell (ground last)."""
    looks: dict[str, list[str]] = {}
    for look, _, lo, hi in exterior_boxes():
        cid = chunk_id_at((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2)
        if look not in looks.setdefault(cid, []):
            looks[cid].append(look)
    (x0, x1), (y0, y1) = GROUND_X, GROUND_Y
    for x in np.arange(x0 + GROUND_CELL_M / 2, x1, GROUND_CELL_M):
        for y in np.arange(y0 + GROUND_CELL_M / 2, y1, GROUND_CELL_M):
            cid = chunk_id_at(float(x), float(y))
            if GROUND_LOOK not in looks.setdefault(cid, []):
                looks[cid].append(GROUND_LOOK)
    ids = {c["id"] for c in chunk_manifest["chunks"]}
    if set(looks) != ids:
        raise GenerateError(f"chunk ids {sorted(ids)} differ from the geometry table cells {sorted(looks)}")
    return looks


def interior_expected(zone_id: str, out: Path, tile_px: int, parent: dict, room: dict) -> dict:
    """The "interior" block of expected.json (design §4-4), computed from the room zone's files."""
    room_id = room["zone_id"]
    vdir = out / "zones" / room_id / f"v{VERSION}"
    cm = json.loads((vdir / "visual" / "chunk_manifest.json").read_text(encoding="utf-8"))
    vis = room["layers"]["visual"]["chunks"]
    cx = (min(c["bbox_enu"][0][0] for c in vis) + max(c["bbox_enu"][1][0] for c in vis)) / 2.0
    cy = (min(c["bbox_enu"][0][1] for c in vis) + max(c["bbox_enu"][1][1] for c in vis)) / 2.0
    zmax = max(c["bbox_enu"][1][2] for c in vis)
    parent_m = transform.from_row_major(parent["transform"])
    origin_in_parent = transform.ecef_to_enu(parent_m, transform.from_row_major(room["transform"])[:3, 3])
    door_1 = next(p for p in parent["portals"] if p["to_zone"] == room_id)
    door_out = next(p for p in room["portals"] if p["to_zone"] == zone_id)
    o = room["origin"]
    light_z = min(INTERIOR_LIGHT_Z_MAX_CM, 100.0 * (zmax - 0.5))
    return {
        "zone_id": room_id,
        "version": VERSION,
        "asset_folder": f"/Game/Golmok/Zones/{room_id}/v{VERSION}",
        "origin_in_parent_m": [_round(v, 4) for v in origin_in_parent],
        "origin": [o["lat"], o["lon"], o["height_ellipsoidal"]],
        "chunks": _chunks_expected(room_id, cm, {c["id"]: [ROOM_LOOK] for c in cm["chunks"]}),
        "collision": _collision_expected(room_id, vdir, room),
        "textures": _texture_sets(out / "recon" / room_id, tile_px),
        "materials": _materials_expected(cm),
        "sublevel": f"/Game/Golmok/Zones/{room_id}/v{VERSION}/L_{room_id}",
        "light": {
            "label": f"Interior_Light_{room_id}",
            "interior_local_cm": [_round(100.0 * cx, 6), _round(-100.0 * cy, 6), _round(light_z, 6)],
        },
        "zone_root_ue_cm": level_ue_cm(room, (0.0, 0.0, 0.0)),
        "portal_pair": {
            "parent_portal": door_1["id"],
            "interior_portal": door_out["id"],
            "parent_enu": door_1["pose_enu"]["position"],
            "interior_enu": door_out["pose_enu"]["position"],
            "yaw_deg": [door_1["pose_enu"]["yaw_deg"], door_out["pose_enu"]["yaw_deg"]],
            "level_ue_cm": level_ue_cm(parent, door_1["pose_enu"]["position"]),
        },
    }


def exterior_expected(zone_id: str, out: Path, tile_px: int, interior: dict | None) -> dict:
    """expected.json of the exterior zone (design §4-4), computed from the generated files."""
    vdir = out / "zones" / zone_id / f"v{VERSION}"
    manifest = zm.load(vdir / zm.MANIFEST_NAME)
    cm = json.loads((vdir / "visual" / "chunk_manifest.json").read_text(encoding="utf-8"))
    blockers = json.loads((vdir / manifest["layers"]["blockers"]["uri"]).read_text(encoding="utf-8"))
    planes = {}
    for p in blockers["planes"]:
        c, n, (w, h) = p["center_enu"], p["normal_enu"], p["size_m"]
        planes[p["id"]] = {
            "center_enu": c,
            "normal_enu": n,
            "size_m": [w, h],
            "ue_rel_center_cm": [_round(100.0 * c[0], 6), _round(-100.0 * c[1], 6), _round(100.0 * c[2], 6)],
            "ue_extent_cm": [5.0, _round(50.0 * w, 6), _round(50.0 * h, 6)],  # AGolmokZone: 10 cm thick / 2
            "level_ue_cm": level_ue_cm(manifest, c),
        }
    o = manifest["origin"]
    return {
        "schema": 1,
        "zone_id": zone_id,
        "version": VERSION,
        "asset_folder": f"/Game/Golmok/Zones/{zone_id}/v{VERSION}",
        "content_manifest": f"Golmok/Zones/{zone_id}/v{VERSION}/{zm.MANIFEST_NAME}",
        "chunks": _chunks_expected(zone_id, cm, exterior_looks(cm)),
        "collision": _collision_expected(zone_id, vdir, manifest),
        "textures": _texture_sets(out / "recon" / zone_id, tile_px),
        "materials": _materials_expected(cm),
        "master_material": MASTER_MATERIAL,
        "blockers": planes,
        "area_origin": list(AREA_ORIGIN),
        "zone_origin": [o["lat"], o["lon"], o["height_ellipsoidal"]],
        "zone_root_ue_cm": level_ue_cm(manifest, (0.0, 0.0, 0.0)),
        "zone_root_yaw_deg": zone_yaw_deg(manifest),
        "player_start_ue_cm": level_ue_cm(manifest, PLAYER_START_ENU),
        "walk": WALK,
        "interior": interior,
    }


# ---- generation ----


def _mesh_pipeline(scan: Path, vdir: Path, manifest: Path, blockers: bool, log: list[str]) -> None:
    """golmok-mesh chunk -> collision --per-chunk --no-snap-ground -> (exterior) blockers add + build."""
    chunk = ["chunk", str(scan), "--size", f"{CHUNK_SIZE_M:g}", "--out", str(vdir / "visual")]
    _run(mesh_main, chunk + ["--manifest", str(manifest)], log)
    collision = ["collision", str(scan), "--out", str(vdir / "collision.glb"), "--target-tris", "1000"]
    collision += ["--min-component-m2", "0.1", "--no-snap-ground", "--per-chunk", str(vdir / "visual")]
    _run(mesh_main, collision + ["--manifest", str(manifest)], log)
    if blockers:
        (wx0, wx1), (wz0, wz1) = WINDOW
        center = (0.5 * (wx0 + wx1), WALL_B[0][1], 0.5 * (wz0 + wz1))  # glass on the south face of wall B
        path = vdir / "blockers.json"
        # --center=-8,... : argparse takes a bare "-8,5,1.5" for an option name (not a plain negative number)
        add = [
            "blockers",
            "add",
            str(path),
            "--center=" + ",".join(f"{v:g}" for v in center),
            "--normal",
            "0,-1,0",
        ]
        add += ["--size", f"{wx1 - wx0:g},{wz1 - wz0:g}", "--kind", "glass", "--id", "glass_1"]
        _run(mesh_main, add, log)
        _run(mesh_main, ["blockers", "build", str(path), "--manifest", str(manifest)], log)


def _exterior_manifest(zone_id: str, interior: bool) -> dict:
    lat, lon, h = ZONE_ORIGIN
    fp = rect_footprint(lat, lon, *FOOTPRINT_M)
    d = zm.new_manifest(zone_id, "exterior", lat, lon, h, fp, priority=10).to_dict()
    d["sources"] = [{"capture_id": "synthetic", "note": "make_synthetic_zone.py"}]
    d["attribution"] = ["합성 테스트 데이터 (WP-06)"]
    if interior:
        pose = {"position": list(DOOR_1), "yaw_deg": 90.0}
        room = f"{zone_id}_room"
        d["portals"] = [
            {"id": "door_1", "to_zone": room, "pose_enu": pose, "radius_m": DOOR_RADIUS_M, "kind": "door"}
        ]
    return d


def _interior_manifest(zone_id: str) -> dict:
    lon, lat, _ = transform.enu_to_lonlat(np.array([ROOM_ORIGIN_IN_PARENT_M]), ZONE_ORIGIN)
    lat, lon, h = float(lat[0]), float(lon[0]), ZONE_ORIGIN[2]
    w, dep, _ = ROOM_SIZE_M
    fp = rect_footprint(lat, lon, w, dep, dx=w / 2, dy=dep / 2)
    room = f"{zone_id}_room"
    d = zm.new_manifest(room, "interior", lat, lon, h, fp, parent_zone=zone_id, priority=20).to_dict()
    pose = {"position": list(DOOR_OUT), "yaw_deg": -90.0}
    d["portals"] = [
        {"id": "door_out", "to_zone": zone_id, "pose_enu": pose, "radius_m": DOOR_RADIUS_M, "kind": "door"}
    ]
    d["consent"] = {"type": "owner_consent", "record_id": "synthetic-consent-002"}
    d["sources"] = [{"capture_id": "synthetic", "note": "make_synthetic_zone.py"}]
    d["attribution"] = ["합성 테스트 데이터 (WP-06)"]
    return d


def generate(out: Path, zone_id: str, interior: bool, tile_px: int) -> list[str]:
    """Write everything under <out>; returns output_files(). Raises GenerateError (message for stderr)."""
    log: list[str] = []
    room_id = f"{zone_id}_room"
    recon, vdir = out / "recon" / zone_id, out / "zones" / zone_id / f"v{VERSION}"
    write_obj(exterior_mesh(), recon / "scan.obj", mtllib="scan.mtl", header=OBJ_HEADER)
    _write_text(recon / "scan.mtl", SCAN_MTL)
    write_tiles(recon / "tex", "ground", tile_px)
    write_tiles(recon / "tex", "facade", tile_px)
    manifest = zm.save(_exterior_manifest(zone_id, interior), vdir / zm.MANIFEST_NAME)
    _mesh_pipeline(recon / "scan.obj", vdir, manifest, blockers=True, log=log)
    manifests = [manifest]
    if interior:
        recon_room, vdir_room = out / "recon" / room_id, out / "zones" / room_id / f"v{VERSION}"
        write_obj(room_mesh(), recon_room / "room.obj", mtllib="room.mtl", header=OBJ_HEADER)
        _write_text(recon_room / "room.mtl", ROOM_MTL)
        write_tiles(recon_room / "tex", "room", tile_px)
        room_manifest = zm.save(_interior_manifest(zone_id), vdir_room / zm.MANIFEST_NAME)
        _mesh_pipeline(recon_room / "room.obj", vdir_room, room_manifest, blockers=False, log=log)
        manifests.append(room_manifest)
    _run(zone_main, ["validate", "--check-files", "--strict", *map(str, manifests)], log)
    interior_doc = None
    if interior:
        interior_doc = interior_expected(zone_id, out, tile_px, zm.load(manifests[0]), zm.load(manifests[1]))
        zm.write_json(
            {"schema": 1, **interior_doc}, out / "zones" / room_id / f"v{VERSION}" / "expected.json"
        )
    zm.write_json(exterior_expected(zone_id, out, tile_px, interior_doc), vdir / "expected.json")
    want, got = output_files(zone_id, interior), tree_files(out, zone_id)
    if sorted(want) != got:
        extra, missing = sorted(set(got) - set(want)), sorted(set(want) - set(got))
        raise GenerateError(f"output file set differs: extra {extra} missing {missing}")
    return want


# ---- --check ----


def _normalized(path: Path, roots: list[Path]) -> bytes:
    """Comparable content: PNG -> decoded pixels; .obj/.mtl/.json -> LF, <out> prefix -> <OUT>; else bytes."""
    data = path.read_bytes()
    if path.suffix == ".png":
        w, h, pixels = read_png_rgb(data)
        return struct.pack(">II", w, h) + pixels
    if path.suffix in (".obj", ".mtl", ".json"):
        data = data.replace(b"\r\n", b"\n")
        for root in roots:
            raw = str(root)
            for form in (json.dumps(raw, ensure_ascii=False)[1:-1], raw):  # JSON-escaped (backslashes) first
                data = data.replace(form.encode("utf-8"), b"<OUT>")
    return data


def check(out: Path, zone_id: str, interior: bool, tile_px: int) -> list[str]:
    """Regenerate into a temp folder and compare with <out>; returns the differences ([] = identical)."""
    tmp = Path(tempfile.mkdtemp(prefix="golmok_synth_check_")).resolve()
    try:
        want = generate(tmp, zone_id, interior, tile_px)
        diffs = []
        for rel in want:
            if not (out / rel).is_file():
                diffs.append(f"missing {rel}")
            elif _normalized(out / rel, [out]) != _normalized(tmp / rel, [tmp]):
                diffs.append(f"differs {rel}")
        diffs += [f"extra {rel}" for rel in tree_files(out, zone_id) if rel not in want]
        return diffs
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- CLI ----


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="make_synthetic_zone.py", description=__doc__.splitlines()[0])
    ap.add_argument(
        "--out", required=True, type=Path, help="output root: <out>/recon/<id>, <out>/zones/<id>/v1"
    )
    ap.add_argument("--zone-id", default=DEFAULT_ZONE_ID, help=f"z_... (default {DEFAULT_ZONE_ID})")
    ap.add_argument("--interior", action="store_true", help="also the room zone <zone_id>_room behind door_1")
    ap.add_argument("--tile-px", type=int, default=DEFAULT_TILE_PX, help="UDIM tile size in px (default 256)")
    ap.add_argument("--force", action="store_true", help="replace an existing <out>/zones/<zone_id>")
    ap.add_argument(
        "--check", action="store_true", help="compare with a fresh generation; exit 1 if different"
    )
    ap.add_argument("--quiet", action="store_true", help="no 'wrote' lines")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not zm.ZONE_ID_RE.match(args.zone_id):
        _err(f"ERROR --zone-id {args.zone_id!r}: expected z_<lowercase>[_...]")
        return 2
    if args.tile_px < 32:
        _err("ERROR --tile-px must be >= 32")
        return 2
    out = args.out.resolve()
    try:
        if args.check:
            if not (out / "zones" / args.zone_id).is_dir():
                _err(f"ERROR nothing to check: {out / 'zones' / args.zone_id} does not exist")
                return 1
            diffs = check(out, args.zone_id, args.interior, args.tile_px)
            for d in diffs:
                _say(d)
            _say(f"check: {'OK' if not diffs else f'FAIL ({len(diffs)} files)'}")
            return 1 if diffs else 0
        existing = [p for p in _zone_roots(out, args.zone_id) if p.parent.name == "zones" and p.exists()]
        if existing and not args.force:
            _err(f"ERROR {existing[0]} exists; use --force")
            return 2
        for p in _zone_roots(out, args.zone_id):
            if p.exists():
                shutil.rmtree(p)
        files = generate(out, args.zone_id, args.interior, args.tile_px)
    except ImportError as e:
        _err(f'ERROR install tools with pip install -e ".[zone,mesh]" ({e})')
        return 2
    except GenerateError as e:
        _err(f"ERROR {e}")
        return 1
    if not args.quiet:
        for rel in files:
            _say(f"wrote {rel}")
    zone_dir = _path_literal(str(out / "zones" / args.zone_id))
    call = f'zi.run({zone_dir}, level="{ZONE_TEST_MAP}", geo_origin="area")'
    _say(f"next: import golmok.zone_import as zi; {call}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
