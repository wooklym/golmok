"""WP-11: the viewer's axis conversion (tools/viewer/zonemath.js) against golmok-mesh's own GLB code.

zonemath.js runs in Node (skipped when `node` is not on PATH). The reference is Python only:
golmok_tools/basemap/gltf.py `enu_to_gltf` (what collision.glb / blockers.glb hold), objio `gltf_to_enu`,
blockers `plane_axes` / `plane_box`, and the zone transform from golmok_tools.zone.transform.
"""

import json
import shutil
import struct
import subprocess
from pathlib import Path

import numpy as np
import pytest

from golmok_tools.basemap.gltf import enu_to_gltf
from golmok_tools.mesh import blockers as bl
from golmok_tools.mesh.objio import gltf_to_enu

ZONEMATH = Path(__file__).resolve().parents[1] / "viewer" / "zonemath.js"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "zones" / "z_synthetic_001" / "v1" / "manifest.json"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node not on PATH")


def zm(calls: list) -> list:
    """Evaluate [[fn, *args], ...] with zonemath.js in Node; returns the results in order."""
    script = (
        "const ZM = require(process.argv[1]);"
        "let s = '';process.stdin.on('data', d => s += d).on('end', () => {"
        "const out = JSON.parse(s).map(([fn, ...a]) => typeof ZM[fn] === 'function' ? ZM[fn](...a) : ZM[fn]);"
        "process.stdout.write(JSON.stringify(out)); });"
    )
    r = subprocess.run(
        [NODE, "-e", script, str(ZONEMATH)],
        input=json.dumps(calls),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(r.stdout)


def read_glb_positions(path: Path) -> list[np.ndarray]:
    """Raw glTF POSITION arrays (no axis conversion) of every mesh primitive in a GLB."""
    data = path.read_bytes()
    assert data[:4] == b"glTF"
    jlen = struct.unpack_from("<I", data, 12)[0]
    doc = json.loads(data[20 : 20 + jlen])
    blen = struct.unpack_from("<I", data, 20 + jlen)[0]
    binary = data[28 + jlen : 28 + jlen + blen]
    out = []
    for mesh in doc["meshes"]:
        for prim in mesh["primitives"]:
            acc = doc["accessors"][prim["attributes"]["POSITION"]]
            view = doc["bufferViews"][acc["bufferView"]]
            off = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
            pos = np.frombuffer(binary, np.float32, acc["count"] * 3, off)
            out.append(pos.reshape(-1, 3).astype(np.float64))
    return out


def test_gltf_to_zone_matches_python_writer_and_reader():
    rng = np.random.default_rng(11)
    enu = rng.uniform(-50, 50, size=(20, 3))
    gltf = enu_to_gltf(enu)
    got = np.array(zm([["gltfToZoneLocal", p] for p in gltf.tolist()]))
    np.testing.assert_allclose(got, enu, atol=1e-12)
    np.testing.assert_allclose(got, gltf_to_enu(gltf), atol=1e-12)
    (m,) = zm([["GLTF_TO_ZONE"]])
    r = np.array(m, dtype=np.float64).reshape(4, 4)[:3, :3]
    assert np.isclose(np.linalg.det(r), 1.0)


def test_model_matrix_places_glb_like_the_zone_transform():
    t = json.loads(FIXTURE.read_text(encoding="utf-8"))["transform"]
    tm = np.array(t, dtype=np.float64).reshape(4, 4)  # row-major, spec §3
    (mm,) = zm([["gltfModelMatrix", t]])
    mm = np.array(mm, dtype=np.float64).reshape(4, 4)
    enu = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0], [-8.0, 5.0, 1.5]])
    gltf = enu_to_gltf(enu)
    ecef_viewer = (mm @ np.c_[gltf, np.ones(len(gltf))].T).T[:, :3]
    ecef_zone = (tm @ np.c_[enu, np.ones(len(enu))].T).T[:, :3]
    np.testing.assert_allclose(ecef_viewer, ecef_zone, atol=1e-6)


@pytest.mark.parametrize("yaw_deg", [0.0, 30.0, -135.0])
def test_model_matrix_matches_zone_transform_module(yaw_deg):
    from golmok_tools.zone import transform

    zt = transform.zone_transform(37.5620, 126.9250, 50.0, yaw_deg)
    (mm,) = zm([["gltfModelMatrix", transform.to_row_major(zt)]])
    mm = np.array(mm, dtype=np.float64).reshape(4, 4)
    enu = np.array([[0.0, 0.0, 0.0], [15.0, 0.0, 0.0], [0.0, 15.0, 0.0], [0.0, 0.0, 6.0], [-15.0, 7.5, -0.3]])
    gltf = enu_to_gltf(enu)
    got = (mm @ np.c_[gltf, np.ones(len(gltf))].T).T[:, :3]
    np.testing.assert_allclose(got, transform.enu_to_ecef(zt, enu), atol=1e-6)
    # zone up points away from the Earth's centre
    o = mm[:3, 3]
    up = (mm @ np.r_[enu_to_gltf(np.array([[0.0, 0.0, 1.0]]))[0], 1.0])[:3] - o
    assert up @ (o / np.linalg.norm(o)) > 0.99


@pytest.mark.parametrize(
    "normal",
    [[0, -1, 0], [1, 0, 0], [0.6, 0.8, 0], [0, 0, 1], [0, 0, -1], [0.3, -0.2, 0.9], [1, 1, -1]],
)
def test_blocker_axes_match_golmok_mesh(normal):
    w, h, n = bl.plane_axes(normal)
    plane = {"center_enu": [-8.0, 5.0, 1.5], "normal_enu": normal, "size_m": [3.0, 2.5]}
    ax, corners = zm([["blockerAxes", normal], ["blockerCorners", plane]])
    np.testing.assert_allclose(ax["width"], w, atol=1e-12)
    np.testing.assert_allclose(ax["height"], h, atol=1e-12)
    np.testing.assert_allclose(ax["normal"], n, atol=1e-12)
    v, _ = bl.plane_box(plane["center_enu"], normal, plane["size_m"], thickness=0.0)
    np.testing.assert_allclose(np.array(corners), v[:4], atol=1e-12)


def test_blockers_glb_vertices_land_on_the_json_planes(tmp_path: Path):
    """End to end: golmok-mesh blockers.glb raw glTF positions, through the viewer conversion, are the
    plane boxes in zone-local ENU (blockers.json)."""
    doc = {"planes": []}
    bl.add_plane(doc, [-8, 5, 1.5], [0, -1, 0], [3.0, 2.5], "glass")
    bl.add_plane(doc, [4, 9, 0.0], [0, 0, 1], [2.0, 1.0], "no_entry")
    path = bl.write_blockers_glb(doc, tmp_path / "blockers.glb")
    raw = read_glb_positions(path)
    assert len(raw) == 2
    for plane, pos in zip(doc["planes"], raw, strict=True):
        got = np.array(zm([["gltfToZoneLocal", p] for p in pos.tolist()]))
        want, _ = bl.plane_box(plane["center_enu"], plane["normal_enu"], plane["size_m"])
        np.testing.assert_allclose(got, want, atol=1e-5)  # float32 in the GLB


def test_uri_rules_match_spec():
    m = "/zones/z_a/v1/manifest.json"
    ok, *bad = zm(
        [
            ["resolveZoneUri", m, "collision/c_e000_n000.glb"],
            ["resolveZoneUri", m, "../x.glb"],
            ["resolveZoneUri", m, "/x.glb"],
            ["resolveZoneUri", m, "file:///x.glb"],
        ]
    )
    assert ok == "/zones/z_a/v1/collision/c_e000_n000.glb"
    assert bad == [None, None, None]
