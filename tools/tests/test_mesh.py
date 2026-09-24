"""golmok-mesh: OBJ I/O, chunking (UV/material/UDIM preserved), collision, blockers."""

import json

import numpy as np
import pytest

pytest.importorskip("trimesh")
pytest.importorskip("fast_simplification")

from mesh_util import SLOPE, synthetic_alley, write_synthetic_obj  # noqa: E402

from golmok_tools.mesh import blockers as bl  # noqa: E402
from golmok_tools.mesh import chunk as ch  # noqa: E402
from golmok_tools.mesh import collision as col  # noqa: E402
from golmok_tools.mesh.cli import main  # noqa: E402
from golmok_tools.mesh.objio import Mesh, read_mesh, read_obj, stats, write_obj  # noqa: E402


def test_obj_roundtrip_keeps_uv_materials_and_udim(tmp_path):
    src = write_synthetic_obj(tmp_path)
    m = read_obj(src)
    ref = synthetic_alley()
    assert m.n_faces == ref.n_faces
    assert m.materials == ["ground", "facade"]
    assert m.udim_tiles() == [1001, 1002]
    order = np.argsort(ref.f_mat, kind="stable")  # write_obj groups faces by material
    assert np.allclose(m.v[m.f_v], ref.v[ref.f_v[order]], atol=1e-6)
    assert np.allclose(m.vt[m.f_vt], ref.vt[ref.f_vt[order]], atol=1e-7)
    assert m.mtllibs == [(tmp_path / "alley.mtl").resolve()]


def test_obj_reader_handles_polygons_negative_indices_and_normals(tmp_path):
    p = tmp_path / "q.obj"
    p.write_text(
        "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nvn 0 0 1\n"
        "f 1//1 2//1 3//1 4//1\n"  # quad, v//vn
        "usemtl b\nf -4//-1 -2//-1 -1//-1\n",
        encoding="utf-8",
    )
    m = read_obj(p)
    assert m.f_v.tolist() == [[0, 1, 2], [0, 2, 3], [0, 2, 3]]
    assert m.vt is None and m.f_vn.tolist() == [[0, 0, 0]] * 3
    assert m.materials == ["b", ""] and m.f_mat.tolist() == [1, 1, 0]
    back = read_obj(write_obj(m, tmp_path / "r.obj"))
    assert back.n_faces == 3 and back.vn is not None


def test_glb_input_is_converted_from_y_up(tmp_path):
    from golmok_tools.basemap.gltf import MeshData, write_glb

    v = np.array([[0, 0, 0], [2, 0, 0], [0, 3, 5]], float)  # ENU
    write_glb(tmp_path / "t.glb", [MeshData(positions=v, indices=np.array([0, 1, 2], np.uint32))])
    m = read_mesh(tmp_path / "t.glb")
    assert np.allclose(m.v, v, atol=1e-6)


def test_grid_chunks_cover_every_face_once(tmp_path):
    mesh = synthetic_alley()
    chunks = ch.grid_chunks(mesh, 15.0)
    faces = np.concatenate([c.faces for c in chunks])
    assert sorted(faces.tolist()) == list(range(mesh.n_faces))
    assert len({c.id for c in chunks}) == len(chunks)
    assert all(c.id.startswith("c_") for c in chunks)
    cent = mesh.face_centroids()
    for c in chunks:  # each chunk spans at most one 15 m cell horizontally
        span = np.ptp(cent[c.faces, :2], axis=0)
        assert (span <= 15.0 + 1e-9).all()


def test_polyline_chunks_follow_the_centerline():
    mesh = synthetic_alley()
    chunks = ch.polyline_chunks(mesh, np.array([[0.0, 0.0], [60.0, 0.0]]), 20.0)
    assert [c.id for c in chunks] == ["s_000", "s_001", "s_002", "s_003"]
    cent = mesh.face_centroids()
    for k, c in enumerate(chunks[:3]):
        x = cent[c.faces, 0]
        assert x.min() >= 20 * k - 1e-9 and x.max() < 20 * (k + 1)


def test_write_chunks_preserves_attributes_and_rewrites_mtl(tmp_path):
    mesh = read_obj(write_synthetic_obj(tmp_path / "src"))
    doc = ch.write_chunks(mesh, ch.grid_chunks(mesh, 15.0), tmp_path / "out")
    assert doc["total_tris"] == mesh.n_faces
    assert doc["mtl"] == ["alley.mtl"]
    mtl = (tmp_path / "out" / "alley.mtl").read_text(encoding="utf-8")
    assert "map_Kd ../src/tex/ground.<UDIM>.png" in mtl and "-bm 1 ../src/tex/facade.<UDIM>.png" in mtl
    tiles = set()
    for e in doc["chunks"]:
        sub = read_obj(tmp_path / "out" / e["file"])
        assert sub.n_faces == e["tris"]
        assert sub.mtllibs == [(tmp_path / "out" / "alley.mtl").resolve()]
        lo, hi = sub.bounds()
        assert np.allclose([lo, hi], e["bbox_enu"], atol=1e-4)
        assert sub.udim_tiles() == e["udim_tiles"]
        tiles |= set(e["udim_tiles"])
        assert set(e["materials"]) <= {"ground", "facade"}
    assert tiles == {1001, 1002}


def test_collision_removes_junk_snaps_ground_and_decimates():
    mesh = synthetic_alley(noise=0.01)
    v, f, rep = col.build_collision(
        mesh, min_component_m2=1.0, snap_cell=10.0, snap_tol=0.05, target_tris=600
    )
    assert rep.removed_components == 1 and rep.removed_faces == 12  # the 0.3 m floating box
    assert rep.snapped_vertices > 0 and rep.ground_planes
    for p in rep.ground_planes:  # every cell found the 3 % slope (1.72°)
        assert abs(p["slope_deg"] - np.degrees(np.arctan(SLOPE))) < 0.3
    assert 500 <= rep.output_faces <= 600
    assert rep.bounds_enu[1][2] < 11  # junk at z=12 is gone
    assert 0.2 < rep.up_facing_ratio < 0.6


def test_ground_snap_flattens_noise_within_tolerance():
    rng = np.random.default_rng(1)
    xy = rng.uniform(0, 10, (2000, 2))
    z = SLOPE * xy[:, 0] + rng.normal(0, 0.01, 2000)
    v = np.column_stack([xy, z])
    v2, n, planes = col.snap_ground(v, cell=10.0, tol=0.05)
    assert n > 1900 and len(planes) == 1
    nrm, d = np.array(planes[0]["normal"]), planes[0]["d"]
    assert np.abs(v2 @ nrm + d).max() < 1e-3  # on the plane (plane printed to 5 decimals)
    assert np.abs(v2 - v).max() <= 0.05 + 1e-9  # never moved farther than tol


def test_split_by_bboxes_partitions_faces():
    mesh = synthetic_alley()
    v, f, _ = col.build_collision(mesh, snap=False, target_tris=None)
    boxes = [[[0, -10, -1], [30, 10, 20]], [[30, -10, -1], [70, 10, 20]]]
    parts = col.split_by_bboxes(v, f, boxes)
    assert sum(len(pf) for _, pf in parts) == len(f)
    assert parts[0][0][:, 0].min() >= -1e-9


def test_blocker_box_geometry():
    w, h, n = bl.plane_axes([0, -1, 0])
    assert np.allclose(h, [0, 0, 1]) and np.allclose(n, [0, -1, 0]) and np.allclose(w, [1, 0, 0])
    w, h, n = bl.plane_axes([0, 0, 1])  # horizontal plane: height axis = north
    assert np.allclose(h, [0, 1, 0])
    v, f = bl.plane_box([3, 4.9, 1.5], [0, -1, 0], [3, 2])
    assert np.allclose(v.min(axis=0), [1.5, 4.89, 0.5]) and np.allclose(v.max(axis=0), [4.5, 4.91, 2.5])
    import trimesh

    tm = trimesh.Trimesh(v, f, process=False)
    assert tm.is_watertight and tm.volume > 0  # closed, outward-facing
    assert abs(tm.volume - 3 * 2 * 0.02) < 1e-9
    with pytest.raises(ValueError):
        bl.plane_axes([0, 0, 0])


def test_blockers_add_and_build(tmp_path):
    f = tmp_path / "blockers.json"
    assert (
        main(
            [
                "blockers",
                "add",
                str(f),
                "--center",
                "3,4.9,1.5",
                "--normal",
                "0,-1,0",
                "--size",
                "3,2",
                "--kind",
                "glass",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "blockers",
                "add",
                str(f),
                "--center",
                "0,0,1",
                "--normal",
                "1,0,0",
                "--size",
                "2,2",
                "--kind",
                "no_entry",
            ]
        )
        == 0
    )
    doc = json.loads(f.read_text(encoding="utf-8"))
    assert [p["id"] for p in doc["planes"]] == ["glass_1", "no_entry_1"]
    assert main(["blockers", "build", str(f)]) == 0
    import trimesh

    scene = trimesh.load(tmp_path / "blockers.glb")
    assert len(scene.geometry) == 2
    # glTF is Y-up: ENU (x, y, z) is stored as (x, z, -y)
    b = scene.geometry["glass_1"].bounds
    assert np.allclose(b, [[1.5, 0.5, -4.91], [4.5, 2.5, -4.89]], atol=1e-6)


def test_inspect_cli(tmp_path, capsys):
    src = write_synthetic_obj(tmp_path)
    assert main(["inspect", str(src), "--json"]) == 0
    s = json.loads(capsys.readouterr().out)
    assert s["udim_tiles"] == [1001, 1002] and s["materials"] == ["ground", "facade"]
    assert s["faces"] == synthetic_alley().n_faces
    assert stats(Mesh(v=np.zeros((0, 3)), f_v=np.zeros((0, 3), np.int64)))["faces"] == 0
