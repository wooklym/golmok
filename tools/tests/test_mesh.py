"""golmok-mesh: OBJ I/O, chunking (UV/material/UDIM preserved), collision, blockers."""

import json
import re

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
    chunks = {c.id: c for c in ch.grid_chunks(mesh, 15.0)}
    doc = ch.write_chunks(mesh, list(chunks.values()), tmp_path / "out")
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
        # per-face positions, UVs and materials equal the source faces (write_obj groups by material)
        faces = chunks[e["id"]].faces
        faces = faces[np.argsort(mesh.f_mat[faces], kind="stable")]
        assert np.allclose(sub.v[sub.f_v], mesh.v[mesh.f_v[faces]], atol=1e-6)
        assert np.allclose(sub.vt[sub.f_vt], mesh.vt[mesh.f_vt[faces]], atol=1e-7)
        assert [sub.materials[k] for k in sub.f_mat] == [mesh.materials[k] for k in mesh.f_mat[faces]]
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
    assert all(len(pf) for _, pf in parts)
    cx0 = parts[0][0][parts[0][1]].mean(axis=1)[:, 0]  # face centroids x
    cx1 = parts[1][0][parts[1][1]].mean(axis=1)[:, 0]
    assert cx0.max() <= 30 and cx1.min() >= 30


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


def test_reproject_from_projected_crs_to_zone_local(tmp_path):
    from pyproj import Transformer
    from zone_util import make_zone

    from golmok_tools.zone import transform as zt

    manifest, d = make_zone(tmp_path / "zones", "z_a_001", h=50.0)
    local = np.array([[0.0, 0.0, 0.0], [10.0, 5.0, 2.0], [-20.0, 8.0, 1.5]])
    ecef = zt.enu_to_ecef(zt.from_row_major(d["transform"]), local)
    lon, lat, h = Transformer.from_crs(4978, 4979, always_xy=True).transform(*ecef.T)
    e, n = Transformer.from_crs(4326, 5186, always_xy=True).transform(lon, lat)
    src = np.column_stack([e, n, h - 23.0])  # "orthometric" heights, geoid offset 23 m
    mesh = Mesh(v=src, f_v=np.array([[0, 1, 2]]), vt=np.array([[0.1, 0.1], [1.5, 0.2], [0.2, 0.9]]))
    mesh.f_vt = mesh.f_v.copy()
    write_obj(mesh, tmp_path / "in.obj")
    args = ["reproject", str(tmp_path / "in.obj"), "--src-crs", "EPSG:5186", "--manifest", str(manifest)]
    assert main([*args, "--height-offset", "23", "--out", str(tmp_path / "out.obj")]) == 0
    out = read_obj(tmp_path / "out.obj")
    assert np.abs(out.v - local).max() < 1e-5  # OBJ keeps 1e-6 m
    assert np.allclose(out.vt, mesh.vt, atol=1e-7)


# -- review fixes (2026-09-24) ---------------------------------------------------------------------


def _parts(tmp_path, split_x):
    """synthetic_alley split by face centroid x into west.obj / east.obj (two RealityScan export parts)."""
    full = synthetic_alley()
    x = full.face_centroids()[:, 0]
    out = []
    for name, sel in (("west", x < split_x), ("east", x >= split_x)):
        out.append(write_obj(full.submesh(np.nonzero(sel)[0]), tmp_path / "recon" / f"{name}.obj"))
    return full, out


def test_grid_chunk_ids_are_absolute_cells_from_the_zone_origin():
    full = synthetic_alley()
    east = full.submesh(np.nonzero(full.face_centroids()[:, 0] >= 37)[0])
    cells_full = {
        c.id: {tuple(p) for p in np.round(full.face_centroids()[c.faces], 6)}
        for c in ch.grid_chunks(full, 15)
    }
    for c in ch.grid_chunks(east, 15):  # the same world cell gets the same id whatever the input part
        assert {tuple(p) for p in np.round(east.face_centroids()[c.faces], 6)} <= cells_full[c.id]
    shifted = Mesh(v=full.v - [20.0, 12.0, 0.0], f_v=full.f_v)  # cells west/south of the origin
    ids = [c.id for c in ch.grid_chunks(shifted, 15)]
    assert len(set(ids)) == len(ids)
    assert all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_]*", i) for i in ids)  # spec §2 id pattern


def test_chunk_several_parts_into_one_zone(tmp_path):
    from zone_util import make_zone

    from golmok_tools.zone import manifest as zm

    full, (west, east) = _parts(tmp_path, 37.0)  # 37 m is inside a 15 m cell: that cell gets two chunks
    manifest, _ = make_zone(tmp_path / "zones", "z_synth_alley_001", size=(70, 30))
    vis = manifest.parent / "visual"
    args = ["--size", "15", "--out", str(vis), "--manifest", str(manifest)]
    assert main(["chunk", str(west), str(east), *args]) == 0
    chunks = zm.load(manifest)["layers"]["visual"]["chunks"]
    assert sum(c["tris"] for c in chunks) == full.n_faces
    assert len({c["id"] for c in chunks}) == len(chunks)
    assert sum(read_obj(vis / c["uri"].split("/")[-1]).n_faces for c in chunks) == full.n_faces
    # a folder that already has chunks is not silently overwritten
    assert main(["chunk", str(west), *args]) == 2
    assert zm.load(manifest)["layers"]["visual"]["chunks"] == chunks
    # --overwrite redoes the folder; --append adds another part
    assert main(["chunk", str(west), *args, "--overwrite"]) == 0
    assert main(["chunk", str(east), *args, "--append"]) == 0
    chunks2 = zm.load(manifest)["layers"]["visual"]["chunks"]
    assert sum(c["tris"] for c in chunks2) == full.n_faces
    cm = json.loads((vis / ch.CHUNK_MANIFEST).read_text(encoding="utf-8"))
    assert {c["id"] for c in cm["chunks"]} == {c["id"] for c in chunks2}
    assert sorted(p.name for p in vis.glob("*.obj")) == sorted(c["file"] for c in cm["chunks"])


def test_collision_accepts_several_parts(tmp_path):
    full, parts = _parts(tmp_path, 30.0)
    whole = write_obj(full, tmp_path / "recon" / "full.obj")
    for name, inputs in (("a", [whole]), ("b", parts)):
        rep = tmp_path / f"{name}.json"
        cmd = ["collision", *map(str, inputs), "--out", str(tmp_path / f"{name}.glb"), "--no-snap-ground"]
        assert main([*cmd, "--target-tris", "100000", "--report", str(rep)]) == 0
    a, b = (json.loads((tmp_path / f"{n}.json").read_text(encoding="utf-8")) for n in "ab")
    assert a["input_faces"] == b["input_faces"] == full.n_faces
    assert a["output_faces"] == b["output_faces"]


@pytest.mark.parametrize("width", [2.0, 3.0, 4.0])
def test_ground_snap_works_in_narrow_alleys(width):
    rng = np.random.default_rng(2)
    xs, ys = np.arange(0, 40.001, 0.25), np.arange(-width / 2, width / 2 + 1e-9, 0.25)
    gx, gy = (a.reshape(-1) for a in np.meshgrid(xs, ys, indexing="ij"))
    ground = np.column_stack([gx, gy, SLOPE * gx + rng.normal(0, 0.01, gx.size)])
    walls = []
    for side in (-1, 1):  # 8 m walls on both sides
        wx, wz = (a.reshape(-1) for a in np.meshgrid(xs, np.arange(0.25, 8.001, 0.25), indexing="ij"))
        walls.append(np.column_stack([wx, np.full(wx.size, side * (width / 2 + 0.05)), wz]))
    v = np.vstack([ground, *walls])
    v2, n, planes = col.snap_ground(v, cell=10.0, tol=0.05)
    assert len(planes) >= 4 and n > 0.9 * len(ground)
    fit = v2[: len(ground)]
    resid = fit[:, 2] - SLOPE * fit[:, 0]
    assert resid.std() < 0.5 * (ground[:, 2] - SLOPE * ground[:, 0]).std()


def _boundary_edges(f):
    e = np.sort(f[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    _, counts = np.unique(e, axis=0, return_counts=True)
    return int((counts == 1).sum())


def test_fill_holes_closes_multi_edge_holes_but_not_the_outer_boundary():
    n = 11  # 10 x 10 m grid of 1 m quads
    gx, gy = np.meshgrid(np.arange(n, dtype=float), np.arange(n, dtype=float), indexing="ij")
    v = np.column_stack([gx.reshape(-1), gy.reshape(-1), np.zeros(n * n)])
    f = []
    for i in range(n - 1):
        for j in range(n - 1):
            if 2 <= i <= 4 and 2 <= j <= 4:  # 3 x 3 m hole (12 boundary edges)
                continue
            if i == 7 and j == 7:  # single-quad hole
                continue
            a, b, c, d = i * n + j, (i + 1) * n + j, (i + 1) * n + j + 1, i * n + j + 1
            f += [[a, b, c], [a, c, d]]
    f = np.asarray(f)
    v2, f2, filled = col.fill_holes(v, f)
    assert filled > 0
    assert _boundary_edges(f2) == 40  # only the 10 x 10 m outline is left open
    area = 0.5 * np.linalg.norm(np.cross(v2[f2[:, 1]] - v2[f2[:, 0]], v2[f2[:, 2]] - v2[f2[:, 0]]), axis=1)
    assert area.sum() == pytest.approx(100.0)
    normals = np.cross(v2[f2[:, 1]] - v2[f2[:, 0]], v2[f2[:, 2]] - v2[f2[:, 0]])[:, 2]
    assert (normals > 0).all()  # filled faces keep the surrounding winding
    _, _, rep = col.build_collision(Mesh(v=v, f_v=f), fill=True, snap=False, target_tris=None)
    assert rep.filled_faces == filled


def test_read_obj_peak_memory_is_bounded(tmp_path, monkeypatch):
    import tracemalloc

    from golmok_tools.mesh import objio

    monkeypatch.setattr(objio, "_BATCH", 20_000, raising=False)
    k = 160  # (k-1)^2 * 2 ≈ 50k triangles with v/vt/vn like RealityScan
    gx, gy = np.meshgrid(np.arange(k, dtype=float), np.arange(k, dtype=float), indexing="ij")
    v = np.column_stack([gx.reshape(-1), gy.reshape(-1), np.zeros(k * k)])
    f = []
    for i in range(k - 1):
        for j in range(k - 1):
            a, b, c, d = i * k + j, (i + 1) * k + j, (i + 1) * k + j + 1, i * k + j + 1
            f += [[a, b, c], [a, c, d]]
    f = np.asarray(f)
    mesh = Mesh(
        v=v, f_v=f, vt=v[:, :2] / k, f_vt=f.copy(), vn=np.tile([0.0, 0, 1], (k * k, 1)), f_vn=f.copy()
    )
    p = write_obj(mesh, tmp_path / "g.obj")
    tracemalloc.start()
    try:
        m = read_obj(p)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert m.n_faces == len(f)
    assert peak / len(f) < 450, f"{peak / len(f):.0f} bytes per triangle"


def _spaced_model(folder, mtl=True, tex=True):
    folder.mkdir(parents=True, exist_ok=True)
    mesh = synthetic_alley()
    if mtl:
        (folder / "my model.mtl").write_text(
            "newmtl ground\nmap_Kd -s 1 1 1 tex/my model.<UDIM>.png\n\n"
            "newmtl facade\nmap_Kd -bm 1 tex/my model.<UDIM>.png\n",
            encoding="utf-8",
        )
    if tex:
        (folder / "tex").mkdir(exist_ok=True)
        for t in ("1001", "1002"):
            (folder / "tex" / f"my model.{t}.png").write_bytes(b"\x89PNG fake")
    return write_obj(mesh, folder / "my model.obj", mtllib="my model.mtl")


def test_mtllib_and_texture_paths_with_spaces(tmp_path):
    from golmok_tools.mesh.objio import mtl_textures

    src = _spaced_model(tmp_path / "src")
    assert read_obj(src).mtllibs == [(tmp_path / "src" / "my model.mtl").resolve()]
    assert mtl_textures(tmp_path / "src" / "my model.mtl") == ["tex/my model.<UDIM>.png"] * 2
    out = tmp_path / "out"
    doc = ch.write_chunks(read_obj(src), ch.grid_chunks(read_obj(src), 20.0), out)
    assert len(doc["mtl"]) == 1 and doc["missing"] == {"mtl": [], "textures": []}
    assert doc["textures"] == [str((tmp_path / "src" / "tex" / "my model.<UDIM>.png").resolve())]
    mtl_text = (out / doc["mtl"][0]).read_text(encoding="utf-8")
    assert "map_Kd -s 1 1 1 ../src/tex/my model.<UDIM>.png" in mtl_text
    assert "map_Kd -bm 1 ../src/tex/my model.<UDIM>.png" in mtl_text
    sub = read_obj(out / doc["chunks"][0]["file"])
    assert sub.mtllibs == [(out / doc["mtl"][0]).resolve()]


def test_missing_mtl_and_textures_are_reported(tmp_path, capsys):
    src = _spaced_model(tmp_path / "a", mtl=False)
    assert main(["chunk", str(src), "--size", "20", "--out", str(tmp_path / "oa")]) == 0
    assert "WARN" in capsys.readouterr().out
    cm = json.loads((tmp_path / "oa" / ch.CHUNK_MANIFEST).read_text(encoding="utf-8"))
    assert cm["missing"]["mtl"] == [str((tmp_path / "a" / "my model.mtl").resolve())]
    src = _spaced_model(tmp_path / "b", tex=False)
    assert main(["chunk", str(src), "--size", "20", "--out", str(tmp_path / "ob")]) == 0
    assert "WARN" in capsys.readouterr().out
    cm = json.loads((tmp_path / "ob" / ch.CHUNK_MANIFEST).read_text(encoding="utf-8"))
    assert cm["missing"]["textures"] == [str((tmp_path / "b" / "tex" / "my model.<UDIM>.png").resolve())]


def test_rewrite_mtl_falls_back_to_absolute_path_across_drives(tmp_path, monkeypatch):
    from golmok_tools.mesh import objio

    src = write_synthetic_obj(tmp_path / "src")

    def relpath(path, start=None):
        raise ValueError("path is on mount 'E:', start on mount 'D:'")

    monkeypatch.setattr(objio.os.path, "relpath", relpath)
    objio.rewrite_mtl(src.with_suffix(".mtl"), tmp_path / "out" / "alley.mtl")
    text = (tmp_path / "out" / "alley.mtl").read_text(encoding="utf-8")
    tex = (tmp_path / "src" / "tex" / "ground.<UDIM>.png").resolve().as_posix()
    assert f"map_Kd {tex}" in text


def test_obj_roundtrip_keeps_faces_without_material(tmp_path):
    p = tmp_path / "q.obj"
    p.write_text(
        "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3\nf 1 3 4\nusemtl b\nf 1 2 4\n", encoding="utf-8"
    )
    m = read_obj(p)
    back = read_obj(write_obj(m, tmp_path / "r.obj"))
    names = sorted((tuple(fv), m.materials[k]) for fv, k in zip(m.f_v.tolist(), m.f_mat, strict=True))
    names_back = sorted(
        (tuple(fv), back.materials[k]) for fv, k in zip(back.f_v.tolist(), back.f_mat, strict=True)
    )
    assert names_back == names


def test_obj_reader_mixed_corner_layouts(tmp_path):
    p = tmp_path / "t.obj"
    p.write_text(
        "v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 1\nvn 0 0 1\nf 1/1 2/1 3/1\nf 1//1 2//1 3//1\n",
        encoding="utf-8",
    )
    m = read_obj(p)
    assert m.n_faces == 2
    assert m.vt is None and m.vn is None  # neither attribute is on every face


def test_obj_reader_tabs_bom_and_bad_indices(tmp_path):
    p = tmp_path / "tabs.obj"
    p.write_bytes("﻿v\t0 0 0\nv\t1 0 0\n  v 0 1 0\nvt\t0 0\n\tusemtl\tm\nf\t1/1 2/1 3/1\n".encode())
    m = read_obj(p)
    assert len(m.v) == 3 and m.n_faces == 1 and m.materials == ["m"]
    p.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 4\n", encoding="utf-8")
    with pytest.raises(ValueError, match="index"):
        read_obj(p)
    assert main(["chunk", str(p), "--out", str(tmp_path / "x")]) == 2


def test_polyline_chunks_do_not_lump_geometry_past_the_ends():
    mesh = synthetic_alley()  # x 0..62
    chunks = ch.polyline_chunks(mesh, np.array([[5.0, 0.0], [30.0, 0.0]]), 15.0)
    cent = mesh.face_centroids()
    for c in chunks:
        assert np.ptp(cent[c.faces, 0]) <= 15.0 + 1e-9, c.id
    assert all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_]*", c.id) for c in chunks)
    assert sorted(np.concatenate([c.faces for c in chunks]).tolist()) == list(range(mesh.n_faces))
