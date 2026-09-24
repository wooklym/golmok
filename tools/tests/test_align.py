"""golmok-align on synthetic data: basemap from test_basemap helpers, zone mesh = perturbed walls."""

import math
from argparse import Namespace

import numpy as np
import pytest

pytest.importorskip("trimesh")
pytest.importorskip("scipy")

import test_basemap as tb  # noqa: E402
from zone_util import make_zone  # noqa: E402

from golmok_tools.align import icp as icp_mod  # noqa: E402
from golmok_tools.align import metrics, poses, prior  # noqa: E402
from golmok_tools.align.cli import main, run_align  # noqa: E402
from golmok_tools.basemap.build import build  # noqa: E402
from golmok_tools.basemap.gltf import MeshData, write_glb  # noqa: E402
from golmok_tools.zone import manifest as zm  # noqa: E402
from golmok_tools.zone import transform as zt  # noqa: E402

LAT, LON = tb.LAT, tb.LON


def rot_z(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def box_walls_mesh(center, size, height, z0=0.0):
    """Open box (4 walls + floor slab) as a MeshData in ENU: like a collision mesh of an alley block."""
    cx, cy = center
    hx, hy = size[0] / 2, size[1] / 2
    corners = np.array([[cx - hx, cy - hy], [cx + hx, cy - hy], [cx + hx, cy + hy], [cx - hx, cy + hy]])
    pos, nrm, idx = [], [], []
    n = 0
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        d = b - a
        normal = np.array([d[1], -d[0], 0.0]) / np.linalg.norm(d)  # outward for CCW ring
        quad = np.array([[*a, z0], [*b, z0], [*b, z0 + height], [*a, z0 + height]])
        pos.append(quad)
        nrm.append(np.tile(normal, (4, 1)))
        idx.append(np.array([0, 1, 2, 0, 2, 3]) + n)
        n += 4
    # ground slab around the block (upward normal)
    g = np.array(
        [
            [cx - hx - 6, cy - hy - 6, z0],
            [cx + hx + 6, cy - hy - 6, z0],
            [cx + hx + 6, cy + hy + 6, z0],
            [cx - hx - 6, cy + hy + 6, z0],
        ]
    )
    pos.append(g)
    nrm.append(np.tile([0, 0, 1.0], (4, 1)))
    idx.append(np.array([0, 1, 2, 0, 2, 3]) + n)
    return MeshData(
        positions=np.concatenate(pos),
        indices=np.concatenate(idx).astype(np.uint32),
        normals=np.concatenate(nrm),
        name="walls",
    )


@pytest.fixture(scope="module")
def basemap(tmp_path_factory):
    d = tmp_path_factory.mktemp("bm")
    tb.write_shp(d / "bld.shp")
    tb.write_dem(d / "dem.tif")
    args = Namespace(
        buildings=d / "bld.shp",
        dem=[str(d / "dem.tif")],
        ortho=[],
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
    m = build(args)
    return d / "out", m


def make_perturbed_zone(tmp_path, basemap, yaw_deg, shift, z_shift=0.0):
    """Zone whose collision mesh is the center building's walls, but placed wrong by (yaw, shift)."""
    out, bm = basemap
    h0 = bm["origin"]["height_ellipsoidal"]
    # true walls in area ENU: center building (10x10 m, 12 m high) at the origin, ground at z~0
    truth = box_walls_mesh((0.0, 0.0), (10.0, 10.0), 12.0)
    # zone-local = area ENU rotated/shifted the wrong way: local = R(-yaw)(p - shift)
    r = rot_z(-yaw_deg)
    local_pos = (truth.positions - np.array([*shift, z_shift])) @ r.T
    local_nrm = truth.normals @ r.T
    zone_dir = tmp_path / "zones"
    path, d = make_zone(zone_dir, "z_test_align", lat=LAT, lon=LON, h=h0, size=(24.0, 24.0))
    write_glb(
        path.parent / "collision.glb", [MeshData(local_pos, truth.indices, local_nrm, name="collision")]
    )
    d["layers"]["collision"] = {"format": "glb", "uri": "collision.glb"}
    zm.save(d, path)
    return path


def run_args(zone_path, basemap_out, **kw):
    base = dict(
        zone=str(zone_path),
        basemap=str(basemap_out),
        poses=None,
        gps=None,
        gps_alt_offset=0.0,
        gps_inlier_m=8.0,
        already_georeferenced=False,
        apply_scale=False,
        mesh_axes="gltf-yup",
        max_points=20000,
        max_corr_m=3.0,
        dof=4,
        ground=True,
        no_walls=False,
        max_shift_m=5.0,
        max_yaw_deg=5.0,
        scale_check=None,
        write=True,
    )
    base.update(kw)
    return Namespace(**base)


def test_icp_recovers_known_rigid_offset():
    rng = np.random.default_rng(1)
    # target: a box surface sampled with exact normals
    truth = box_walls_mesh((0, 0), (10, 10), 12)
    import trimesh

    mesh = trimesh.Trimesh(truth.positions, truth.indices.reshape(-1, 3), process=False)
    dst, fidx = trimesh.sample.sample_surface(mesh, 20000, seed=0)
    dst_n = mesh.face_normals[fidx]
    src_true, sidx = trimesh.sample.sample_surface(mesh, 8000, seed=1)
    r = rot_z(1.5)
    shift = np.array([0.8, -0.5, 0.3])
    src = (src_true - shift) @ r.T  # wrong placement
    res = icp_mod.icp_point_to_plane(
        src,
        dst,
        dst_n,
        max_correspondence_m=3.0,
        dof=6,
        src_normals=mesh.face_normals[sidx] @ r.T,
        normal_agreement=0.5,
    )
    recovered = zt.apply(res.transform, src)
    assert res.rmse < 0.05
    assert np.abs(recovered - src_true).max() < 0.05
    dec = icp_mod.decompose(res.transform)
    assert abs(dec["yaw_deg"] + 1.5) < 0.2  # undoes the +1.5° perturbation
    assert rng is not None


def test_umeyama_roundtrip_and_ransac():
    rng = np.random.default_rng(0)
    src = rng.uniform(-50, 50, (30, 3))
    s, r, t = 1.02, rot_z(7.0), np.array([100.0, -40.0, 3.0])
    dst = s * (src @ r.T) + t + rng.normal(0, 0.3, src.shape)
    dst[3] += [60, 0, 0]  # a bad GPS fix
    dst[11] += [0, -45, 0]
    sim = prior.fit_prior(src, dst, with_scale=True, inlier_m=5.0)
    assert abs(sim.scale - s) < 0.01
    assert np.allclose(sim.rotation, r, atol=0.01)
    assert np.linalg.norm(sim.translation - t) < 1.5
    assert not sim.inliers[3] and not sim.inliers[11]
    fixed = prior.fit_prior(src, dst, with_scale=False, inlier_m=5.0)
    assert fixed.scale == 1.0


def test_realityscan_csv_and_gps_join(tmp_path):
    (tmp_path / "cams.csv").write_text(
        "#name,x,y,alt,yaw,pitch,roll,f,px,py,k1,k2,k3,k4,t1,t2\n"
        "IMG_0001.DNG,1.5,2.5,0.7,10,0,0,30,0,0,0,0,0,0,0,0\n"
        "IMG_0002.DNG,3.5,2.5,0.8,10,0,0,30,0,0,0,0,0,0,0,0\n",
        encoding="utf-8",
    )
    (tmp_path / "gps.csv").write_text(
        "name,lat,lon,alt\nIMG_0001.tif,37.562,126.925,40\nIMG_0003.tif,37.5,126.9,\n", encoding="utf-8"
    )
    cams = poses.read_realityscan_csv(tmp_path / "cams.csv")
    fixes = poses.read_gps_csv(tmp_path / "gps.csv")
    assert len(cams) == 2 and cams[0].position.tolist() == [1.5, 2.5, 0.7]
    assert len(fixes) == 2 and fixes[1].alt is None
    pairs = poses.join(cams, fixes)
    assert len(pairs) == 1 and pairs[0][0].name == "IMG_0001.DNG"


def test_metrics_basic():
    from shapely.geometry import box

    pts = np.array([[-5, -5, 0], [5, -5, 0], [5, 5, 0], [-5, 5, 0], [0, 0, 12.0]])
    assert metrics.footprint_iou(box(-5, -5, 5, 5), pts) == pytest.approx(1.0)
    assert metrics.footprint_iou(box(0, 0, 10, 10), pts) == pytest.approx(25 / 175, abs=1e-6)
    ground = np.array([[x, y, 0.02 * x] for x in range(-5, 6) for y in range(-5, 6)], dtype=float)
    assert metrics.ground_tilt_deg(ground) == pytest.approx(math.degrees(math.atan(0.02)), abs=0.01)
    assert metrics.scale_check([0, 0, 0], [3, 4, 0], 5.0)["ratio"] == pytest.approx(1.0)
    assert metrics.verdict(
        {"icp_rmse_m": 0.9, "tilt_deg": 0.1, "footprint_iou": 0.9, "icp_inlier_ratio": 0.9}
    )


def test_run_aligns_perturbed_zone_and_writes_manifest(tmp_path, basemap):
    out, bm = basemap
    zone_path = make_perturbed_zone(tmp_path, basemap, yaw_deg=2.0, shift=(1.2, -0.8), z_shift=0.4)
    before = zm.load(zone_path)
    d, report = run_align(run_args(zone_path, out))
    assert "failed" not in report, report
    c = report["correction_area_enu"]
    # correction must undo the perturbation: +yaw 2°, +shift (1.2, -0.8, 0.4)
    assert abs(c["yaw_deg"] - 2.0) < 0.25
    assert np.allclose(c["shift_m"], [1.2, -0.8, 0.4], atol=0.15)
    assert report["quality"]["icp_rmse_m"] < 0.05
    assert report["quality"]["footprint_iou"] > 0.3
    # manifest updated, still valid, origin moved by ~ the shift
    after = zm.load(zone_path)
    assert after["transform"] != before["transform"]
    rep = zm.check(after, zone_path, check_files=True)
    assert not rep.errors, rep.errors
    assert after["quality"]["aligned_by"] == "golmok-align"
    assert (zone_path.parent / "align_report.md").exists()
    # aligned walls sit on the basemap building: distance median small
    assert after["quality"]["wall_distance_median_m"] < 0.1


def test_run_refuses_large_correction(tmp_path, basemap):
    out, _ = basemap
    zone_path = make_perturbed_zone(tmp_path, basemap, yaw_deg=1.0, shift=(0.5, 0.2))
    before = zm.load(zone_path)
    _, report = run_align(run_args(zone_path, out, max_shift_m=0.1))
    assert "failed" in report
    assert zm.load(zone_path)["transform"] == before["transform"]


def test_gps_prior_path(tmp_path, basemap):
    out, bm = basemap
    zone_path = make_perturbed_zone(
        tmp_path, basemap, yaw_deg=0.0, shift=(30.0, -20.0)
    )  # far off: ICP alone can't
    h0 = bm["origin"]["height_ellipsoidal"]
    origin = (LAT, LON, h0)
    # cameras in zone-local (= area ENU shifted by -(30,-20)); GPS = truth in area ENU
    rng = np.random.default_rng(3)
    truth = rng.uniform(-12, 12, (12, 3))
    truth[:, 2] = 1.6
    local = truth - np.array([30.0, -20.0, 0.0])
    lon, lat, h = zt.enu_to_lonlat(truth + rng.normal(0, 1.0, truth.shape), origin)
    lines = ["#name,x,y,alt,yaw,pitch,roll,f,px,py,k1,k2,k3,k4,t1,t2"]
    lines += [f"IMG_{i:04d}.DNG,{p[0]},{p[1]},{p[2]},0,0,0,30,0,0,0,0,0,0,0,0" for i, p in enumerate(local)]
    (tmp_path / "cams.csv").write_text("\n".join(lines), encoding="utf-8")
    (tmp_path / "gps.csv").write_text(
        "name,lat,lon,alt\n"
        + "\n".join(
            f"IMG_{i:04d}.tif,{la},{lo},{hh}" for i, (la, lo, hh) in enumerate(zip(lat, lon, h, strict=True))
        ),
        encoding="utf-8",
    )
    _, report = run_align(
        run_args(
            zone_path,
            out,
            poses=str(tmp_path / "cams.csv"),
            gps=str(tmp_path / "gps.csv"),
            already_georeferenced=True,
            max_shift_m=50.0,
            max_yaw_deg=10.0,
        )
    )
    assert report["gps_prior"]["inliers"] >= 10
    assert np.allclose(report["correction_area_enu"]["shift_m"][:2], [30.0, -20.0], atol=0.5)
    assert report["quality"]["icp_rmse_m"] < 0.05


def test_cli_compare(tmp_path):
    p1, _ = make_zone(tmp_path, "z_a", h=50.0)
    p2, d2 = make_zone(tmp_path, "z_b", h=50.0, edit=lambda d: None)
    t = zt.from_row_major(d2["transform"])
    # shift zone_b by 2 m east in its own frame
    t2 = t.copy()
    t2[:3, 3] = t2[:3, 3] + t[:3, :3] @ np.array([2.0, 0, 0])
    d2["transform"] = zt.to_row_major(t2)
    zm.save(d2, p2)
    assert main(["compare", "--before", str(p1), "--after", str(p2)]) == 0


def test_check_blur_without_models_reports_clearly(tmp_path, capsys):
    (tmp_path / "a.png").write_bytes(b"")
    rc = main(
        [
            "check-blur",
            str(tmp_path),
            "--face-model",
            str(tmp_path / "no.jit"),
            "--lp-model",
            str(tmp_path / "no.jit"),
        ]
    )
    assert rc == 2
    assert "EgoBlur" in capsys.readouterr().out
