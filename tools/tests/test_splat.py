"""golmok-splat: PLY I/O, SH rotation, crop/clean/transform, 3D Tiles (KHR_gaussian_splatting)."""

import json
import os
import shutil
import struct
import subprocess

import numpy as np
import pytest

pytest.importorskip("scipy")

from zone_util import FIXTURE_ZONES, REPO  # noqa: E402

from golmok_tools.splat import ops, ply  # noqa: E402
from golmok_tools.splat.cli import footprint_local, main  # noqa: E402
from golmok_tools.splat.tiles import EXT, write_tileset  # noqa: E402

FIXTURE = FIXTURE_ZONES / "z_synthetic_001" / "v1" / "manifest.json"


def rot(axis, deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    i, j = [(1, 2), (2, 0), (0, 1)][axis]
    r = np.eye(3)
    r[i, i], r[i, j], r[j, i], r[j, j] = c, -s, s, c
    return r


def color(d, dirs):
    y = ops.sh_basis(dirs, ply.sh_degree(d))
    return ply.sh_dc(d)[:, None, :] * ops.C0 + np.einsum("dk,nkc->ndc", y[:, 1:], ply.sh_rest(d))


def cov(d):
    r = ops.quat_to_matrix(ply.quats_wxyz(d))
    c = r * ply.scales(d)[:, None, :]
    return c @ c.transpose(0, 2, 1)


@pytest.mark.parametrize("degree", [0, 1, 2, 3])
def test_ply_roundtrip_and_sh_degree(tmp_path, degree):
    d = ply.random_splats(500, degree)
    p = ply.write_ply(d, tmp_path / "a.ply")
    back = ply.read_ply(p)
    assert np.array_equal(back, d)
    assert ply.sh_degree(back) == degree
    assert ply.sh_rest(back).shape == (500, ply.sh_rest_count(degree), 3)


def test_f_rest_layout_is_channel_major():
    d = ply.random_splats(3, 1)
    k = 3
    rest = ply.sh_rest(d)
    # f_rest_0..2 = red coefficients 1..3, f_rest_3..5 = green ...
    assert rest[0, 1, 0] == pytest.approx(d["f_rest_1"][0])
    assert rest[0, 0, 1] == pytest.approx(d[f"f_rest_{k}"][0])
    ply.set_sh_rest(d, rest * 2)
    assert np.allclose(ply.sh_rest(d), rest * 2)


def test_read_ply_rejects_ascii(tmp_path):
    p = tmp_path / "a.ply"
    p.write_bytes(b"ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nend_header\n0\n")
    with pytest.raises(ValueError, match="binary_little_endian"):
        ply.read_ply(p)


def test_transform_rotates_positions_covariance_and_sh():
    d = ply.random_splats(200, 3)
    r = rot(2, 70) @ rot(0, 20) @ rot(1, -35)
    m = np.eye(4)
    m[:3, :3] = 1.5 * r
    m[:3, 3] = [1, 2, 3]
    out = ops.transform(d, m)
    a = 1.5 * r
    assert np.abs(ply.positions(out) - (ply.positions(d) @ a.T + [1, 2, 3])).max() < 1e-5
    assert np.abs(cov(out) - a @ cov(d) @ a.T).max() < 1e-6
    dirs = ops._sample_dirs()[:32]
    # the rotated splat seen from the rotated direction has the same color
    assert np.abs(color(out, dirs @ r.T) - color(d, dirs)).max() < 1e-5


def test_transform_rejects_shear_and_mirror():
    d = ply.random_splats(5, 0)
    with pytest.raises(ValueError):
        ops.transform(d, np.diag([1.0, 2.0, 1.0, 1.0]))
    with pytest.raises(ValueError):
        ops.transform(d, np.diag([1.0, -1.0, 1.0, 1.0]))


def test_crop_and_clean():
    d = ply.random_splats(2000, 0, extent=(10, 10, 2))
    assert len(ops.crop_bbox(d, [0, 0, 0], [5, 10, 2])) == pytest.approx(1000, rel=0.1)
    tri = [(0, 0), (10, 0), (0, 10)]
    assert len(ops.crop_polygon(d, tri)) == pytest.approx(1000, rel=0.1)
    assert len(ops.crop_polygon(d, tri, margin_m=20)) == 2000
    # 20 far floaters
    far = ply.random_splats(20, 0, extent=(40, 40, 10), seed=3)  # sparse, far above
    far["z"] += 50
    both = np.concatenate([d, far])
    out, rep = ops.clean(both, knn=8, std=2.0)
    assert rep["floaters"] >= 20 and (ply.positions(out)[:, 2] < 10).all()
    out, rep = ops.clean(both, knn=0, std=0, min_opacity=0.5, max_scale_m=0.05)
    assert (ply.opacities(out) >= 0.5).all() and (ply.scales(out).max(axis=1) <= 0.05).all()
    assert rep["removed"] == len(both) - len(out)


def test_crop_with_zone_footprint(tmp_path):
    d = ply.random_splats(4000, 0, extent=(60, 30, 5))
    d["x"] -= 30
    d["y"] -= 15
    poly = footprint_local(json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert np.allclose(poly.min(axis=0), [-20, -10], atol=0.01) and np.allclose(
        poly.max(axis=0), [20, 10], atol=0.01
    )
    src = ply.write_ply(d, tmp_path / "a.ply")
    assert (
        main(
            [
                "crop",
                str(src),
                "--manifest",
                str(FIXTURE),
                "--margin-m",
                "0",
                "--out",
                str(tmp_path / "b.ply"),
            ]
        )
        == 0
    )
    p = ply.positions(ply.read_ply(tmp_path / "b.ply"))
    assert (np.abs(p[:, 0]) <= 20.01).all() and (np.abs(p[:, 1]) <= 10.01).all()


def read_glb_json(path):
    raw = path.read_bytes()
    n = struct.unpack("<I", raw[12:16])[0]
    return json.loads(raw[20 : 20 + n])


def tile_iter(tile):
    yield tile
    for c in tile.get("children", []):
        yield from tile_iter(c)


def test_tiles_structure(tmp_path):
    d = ply.random_splats(6000, 2, extent=(20, 10, 4))
    t = np.eye(4)
    t[:3, 3] = [100, 200, 300]
    rep = write_tileset(d, tmp_path / "t", max_splats=1000, root_transform=t)
    ts = json.loads((tmp_path / "t" / "tileset.json").read_text(encoding="utf-8"))
    assert ts["asset"]["version"] == "1.1"
    root = ts["root"]
    assert root["transform"][12:15] == [100, 200, 300]  # column-major: translation last
    tiles = list(tile_iter(root))
    assert len(tiles) == rep["tiles"] > 1
    leaves = [x for x in tiles if not x.get("children")]
    total_leaf = 0
    for x in tiles:
        assert x["refine"] == "REPLACE"
        g = read_glb_json(tmp_path / "t" / x["content"]["uri"])
        prim = g["meshes"][0]["primitives"][0]
        assert prim["mode"] == 0 and prim["extensions"][EXT]["kernel"] == "ellipse"
        assert EXT in g["extensionsUsed"]
        attrs = prim["attributes"]
        names = {f"{EXT}:{a}" for a in ("ROTATION", "SCALE", "OPACITY", "SH_DEGREE_0_COEF_0")}
        names |= {f"{EXT}:SH_DEGREE_1_COEF_{n}" for n in range(3)} | {
            f"{EXT}:SH_DEGREE_2_COEF_{n}" for n in range(5)
        }
        assert names <= set(attrs) and f"{EXT}:SH_DEGREE_3_COEF_0" not in attrs
        count = g["accessors"][attrs["POSITION"]]["count"]
        assert count <= 1000
        if x in leaves:
            total_leaf += count
            assert x["geometricError"] == 0
        else:
            assert all(c["geometricError"] < x["geometricError"] for c in x["children"])
        # content (Y-up) must sit inside the Z-up bounding box
        acc = g["accessors"][attrs["POSITION"]]
        c, h = np.array(x["boundingVolume"]["box"][:3]), np.array(x["boundingVolume"]["box"][3::4])
        lo_enu = np.array([acc["min"][0], -acc["max"][2], acc["min"][1]])
        hi_enu = np.array([acc["max"][0], -acc["min"][2], acc["max"][1]])
        assert (lo_enu >= c - h - 1e-4).all() and (hi_enu <= c + h + 1e-4).all()
    assert total_leaf == len(d)
    assert ts["geometricError"] >= root["geometricError"] > 0


def test_tiles_attribute_values_follow_the_extension(tmp_path):
    """Values are activated (linear scale, sigmoid opacity, xyzw unit quaternion) and axis-converted."""
    d = ply.random_splats(50, 1)
    write_tileset(d, tmp_path / "t", max_splats=100)
    path = tmp_path / "t" / "tiles" / "r.glb"
    g = read_glb_json(path)
    raw = path.read_bytes()
    n = struct.unpack("<I", raw[12:16])[0]
    binary = raw[20 + n + 8 :]
    attrs = g["meshes"][0]["primitives"][0]["attributes"]

    def read(name, width):
        acc = g["accessors"][attrs[name]]
        view = g["bufferViews"][acc["bufferView"]]
        start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        return np.frombuffer(binary, np.float32, acc["count"] * width, start).reshape(acc["count"], width)

    pos = read("POSITION", 3)
    assert np.allclose(pos, ply.positions(d)[:, [0, 2, 1]] * [1, 1, -1], atol=1e-5)
    assert np.allclose(read(f"{EXT}:OPACITY", 1)[:, 0], ply.opacities(d), atol=1e-6)
    assert np.allclose(np.sort(read(f"{EXT}:SCALE", 3), 1), np.sort(ply.scales(d), 1), atol=1e-6)
    q = read(f"{EXT}:ROTATION", 4)
    assert np.allclose(np.linalg.norm(q, axis=1), 1, atol=1e-6)
    # covariance in glTF space equals the ENU covariance rotated into Y-up
    r = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
    qm = ops.quat_to_matrix(q[:, [3, 0, 1, 2]].astype(np.float64))
    c = qm * read(f"{EXT}:SCALE", 3)[:, None, :]
    assert np.abs(c @ c.transpose(0, 2, 1) - r @ cov(d) @ r.T).max() < 1e-6
    assert np.allclose(read(f"{EXT}:SH_DEGREE_0_COEF_0", 3), ply.sh_dc(d), atol=1e-6)


def test_cli_chain(tmp_path, capsys):
    src = ply.write_ply(ply.random_splats(3000, 3), tmp_path / "a.ply")
    assert main(["inspect", str(src), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["sh_degree"] == 3
    assert main(["clean", str(src), "--out", str(tmp_path / "b.ply"), "--min-opacity", "0.1"]) == 0
    eye = ",".join(str(v) for v in np.eye(4).reshape(16))
    assert (
        main(["transform", str(tmp_path / "b.ply"), "--matrix", eye, "--out", str(tmp_path / "c.ply")]) == 0
    )
    assert np.array_equal(ply.read_ply(tmp_path / "b.ply"), ply.read_ply(tmp_path / "c.ply"))
    assert main(["crop", str(src), "--bbox", "0,0,0,10,10,5", "--out", str(tmp_path / "d.ply")]) == 0
    assert (
        main(
            [
                "tiles",
                str(tmp_path / "b.ply"),
                "--out",
                str(tmp_path / "t"),
                "--max-splats",
                "800",
                "--manifest",
                str(FIXTURE),
            ]
        )
        == 0
    )
    root = json.loads((tmp_path / "t" / "tileset.json").read_text(encoding="utf-8"))["root"]
    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))["transform"]
    assert np.allclose(np.array(root["transform"]).reshape(4, 4).T.reshape(16), fx)


ALLOWED_VALIDATOR_ERRORS = ("Invalid attribute name.",)  # validator 0.6.1 predates KHR_gaussian_splatting


@pytest.mark.skipif(
    not (shutil.which("npx") and os.environ.get("GOLMOK_TILES_VALIDATOR")),
    reason="set GOLMOK_TILES_VALIDATOR=1 with Node (npx) to run 3d-tiles-validator",
)
def test_3d_tiles_validator(tmp_path):
    write_tileset(ply.random_splats(3000, 3), tmp_path / "t", max_splats=1000)
    r = subprocess.run(
        ["npx", "--yes", "3d-tiles-validator@0.6.1", "--tilesetFile", str(tmp_path / "t" / "tileset.json")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO,
        shell=os.name == "nt",
    )
    report = json.loads(r.stdout[r.stdout.index("{") : r.stdout.rindex("}") + 1])
    unexpected = []

    def walk(o):
        if isinstance(o, dict):
            leaf = "message" in o and not o.get("causes")
            if leaf and o.get("severity") == "ERROR" and o["message"] not in ALLOWED_VALIDATOR_ERRORS:
                unexpected.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(report)
    assert unexpected == [], unexpected
