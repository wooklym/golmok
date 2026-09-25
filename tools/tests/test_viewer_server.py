import json
import os
import threading
import urllib.request
from pathlib import Path

import pytest

from golmok_tools import viewer_server as vs


@pytest.fixture
def served(tmp_path: Path):
    data = tmp_path / "data"
    (data / "tiles").mkdir(parents=True)
    (data / "tileset.json").write_text(json.dumps({"asset": {"version": "1.1"}}), encoding="utf-8")
    (data / "tiles" / "b_0_0.glb").write_bytes(b"glTF" + b"\0" * 12)
    (tmp_path / "secret.txt").write_text("nope")
    server = vs.make_server(data, 0)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", data
    server.shutdown()


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, None, b""


def test_serves_viewer_and_data(served):
    base, _ = served
    status, ctype, body = get(base + "/")
    assert status == 200 and "text/html" in ctype and b"Golmok" in body
    status, ctype, body = get(base + "/data/tileset.json")
    assert status == 200 and "application/json" in ctype and json.loads(body)["asset"]["version"] == "1.1"
    status, ctype, body = get(base + "/data/tiles/b_0_0.glb")
    assert status == 200 and ctype == "model/gltf-binary" and body.startswith(b"glTF")


def test_blocks_paths_outside_roots(served):
    base, data = served
    assert vs.resolve("/data/../secret.txt", data) is None
    assert vs.resolve("/../../etc/passwd", data) is None
    status, _, _ = get(base + "/data/%2e%2e/secret.txt")
    assert status == 404
    status, _, _ = get(base + "/data/missing.json")
    assert status == 404


# -- WP-11: zone mounts (/zones/<zone_id>/v<n>/) and path escapes ----------------------------------------


def _zone(folder: Path, zone_id="z_test_001", version=1) -> Path:
    folder.mkdir(parents=True)
    doc = {"zone_id": zone_id, "version": version}
    (folder / "manifest.json").write_text(json.dumps(doc), encoding="utf-8")
    (folder / "collision.glb").write_bytes(b"glTF" + b"\0" * 12)
    (folder / "blockers.json").write_text('{"planes": []}', encoding="utf-8")
    (folder / "visual").mkdir()
    (folder / "visual" / "c_e000_n000.obj").write_text("v 0 0 0\n", encoding="utf-8")
    return folder


@pytest.fixture
def zone_served(tmp_path: Path):
    zdir = _zone(tmp_path / "zones" / "z_test_001" / "v1")
    (tmp_path / "zones" / "secret.glb").write_bytes(b"glTF-secret")
    prefix, folder = vs.zone_mount(zdir)
    zones = {prefix: folder}
    server = vs.make_server(None, 0, zones=zones)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", zones, zdir
    server.shutdown()


def test_zone_mount_from_folder_or_manifest(tmp_path: Path):
    zdir = _zone(tmp_path / "z" / "v3", version=3)
    prefix, folder = vs.zone_mount(zdir)
    assert prefix == "z_test_001/v3"
    assert os.path.normpath(folder) == os.path.normpath(zdir.resolve())
    assert vs.zone_mount(zdir / "manifest.json") == (prefix, folder)


@pytest.mark.parametrize(
    "doc",
    [
        {"zone_id": "../evil", "version": 1},
        {"zone_id": "Z_UPPER", "version": 1},
        {"zone_id": "z_ok", "version": 0},
        {"zone_id": "z_ok", "version": True},
        {"zone_id": "z_ok", "version": "1"},
        ["not", "a", "dict"],
    ],
)
def test_zone_mount_rejects_bad_manifest(tmp_path: Path, doc):
    (tmp_path / "manifest.json").write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError):
        vs.zone_mount(tmp_path)


def test_zone_mount_needs_manifest(tmp_path: Path):
    with pytest.raises(ValueError):
        vs.zone_mount(tmp_path)
    (tmp_path / "other.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        vs.zone_mount(tmp_path / "other.json")


def test_serves_zone_files(zone_served):
    base, _, _ = zone_served
    status, ctype, body = get(base + "/zones/z_test_001/v1/collision.glb")
    assert status == 200 and ctype == "model/gltf-binary" and body.startswith(b"glTF")
    status, ctype, body = get(base + "/zones/z_test_001/v1/manifest.json")
    assert status == 200 and "application/json" in ctype and json.loads(body)["zone_id"] == "z_test_001"
    status, _, _ = get(base + "/zones/z_test_001/v1/blockers.json")
    assert status == 200
    # the viewer still works with a zone only (no data folder)
    status, _, body = get(base + "/")
    assert status == 200 and b"Golmok" in body
    assert get(base + "/data/tileset.json")[0] == 404


def test_zone_serves_only_whitelisted_suffixes(zone_served):
    base, zones, _ = zone_served
    assert vs.resolve("/zones/z_test_001/v1/visual/c_e000_n000.obj", None, zones) is None
    assert get(base + "/zones/z_test_001/v1/visual/c_e000_n000.obj")[0] == 404
    # directory -> index.html (not a listing), which is not a zone suffix either
    assert get(base + "/zones/z_test_001/v1/")[0] == 404
    assert get(base + "/zones/z_test_001/v1/visual/")[0] == 404


@pytest.mark.parametrize(
    "path",
    [
        "/zones/z_test_001/v1/../secret.glb",
        "/zones/z_test_001/v1/%2e%2e/secret.glb",
        "/zones/z_test_001/v1/%2E%2E%2Fsecret.glb",
        "/zones/z_test_001/v1/visual/../../secret.glb",
        "/zones/z_test_001/v1/..%5csecret.glb",
        "/zones/z_test_001/v1/%5c..%5csecret.glb",
        "/zones/z_test_001/v1//etc/passwd",
        "/zones/z_test_001/v1/%2fetc%2fpasswd",
        "/zones/z_test_001/v1/C:/Windows/win.ini",
        "/zones/z_test_001/v1/C:%5cWindows%5cwin.ini",
        "/zones/z_test_001/v1/collision.glb%00.json",
        "/zones/z_test_001/v1/collision.glb::$DATA",
        "/zones/z_test_001/v2/collision.glb",
        "/zones/z_other/v1/collision.glb",
        "/zones/z_test_001/collision.glb",
        "/zones/../zones/z_test_001/v1/collision.glb",
        "/data/collision.glb",
    ],
)
def test_zone_path_escapes_are_refused(zone_served, path):
    base, zones, _ = zone_served
    assert vs.resolve(path, None, zones) is None
    assert get(base + path)[0] in (400, 404)


def test_data_path_escapes_are_refused(served):
    _, data = served
    for path in (
        "/data//etc/passwd",
        "/data/%2fetc%2fpasswd",
        "/data/..%5csecret.txt",
        "/data/tiles/../../secret.txt",
        "/data/C:/Windows/win.ini",
        "/data/tileset.json%00",
    ):
        assert vs.resolve(path, data) is None, path
    assert os.path.normpath(vs.resolve("/data/tiles/b_0_0.glb", data)) == os.path.normpath(
        (data / "tiles" / "b_0_0.glb").resolve()
    )


def _symlink(link: Path, target: Path, is_dir=False) -> None:
    try:
        link.symlink_to(target, target_is_directory=is_dir)
    except (OSError, NotImplementedError) as e:  # Windows without developer mode / admin
        pytest.skip(f"symlinks not available: {e}")


def test_zone_symlink_out_of_root_is_refused(zone_served, tmp_path: Path):
    base, zones, zdir = zone_served
    _symlink(zdir / "leak.glb", tmp_path / "zones" / "secret.glb")
    _symlink(zdir / "outdir", tmp_path / "zones", is_dir=True)
    assert vs.resolve("/zones/z_test_001/v1/leak.glb", None, zones) is None
    assert vs.resolve("/zones/z_test_001/v1/outdir/secret.glb", None, zones) is None
    assert get(base + "/zones/z_test_001/v1/leak.glb")[0] == 404
    assert get(base + "/zones/z_test_001/v1/outdir/secret.glb")[0] == 404


def test_zone_symlink_inside_root_is_served(zone_served):
    base, zones, zdir = zone_served
    _symlink(zdir / "alias.glb", zdir / "collision.glb")
    assert vs.resolve("/zones/z_test_001/v1/alias.glb", None, zones) is not None
    assert get(base + "/zones/z_test_001/v1/alias.glb")[0] == 200


def test_data_symlink_out_of_root_is_refused(served, tmp_path: Path):
    _, data = served
    _symlink(data / "leak.txt", tmp_path / "secret.txt")
    assert vs.resolve("/data/leak.txt", data) is None


def test_main_requires_data_or_zone(capsys):
    with pytest.raises(SystemExit):
        vs.main(["--no-browser"])
    assert "--zone" in capsys.readouterr().err


def test_main_rejects_duplicate_zone(tmp_path: Path, capsys):
    zdir = _zone(tmp_path / "a" / "v1")
    with pytest.raises(SystemExit):
        vs.main(["--zone", str(zdir), "--zone", str(zdir / "manifest.json"), "--no-browser"])
    assert "두 번" in capsys.readouterr().err


def test_overlong_names_give_404_not_a_dropped_connection(zone_served, served):
    # Linux raises ENAMETOOLONG in is_dir() (resolve() returns None); Windows just finds no such file.
    # Either way the client must get a 404, not a dropped connection.
    base, _, _ = zone_served
    long = "a" * 300
    assert get(f"{base}/zones/z_test_001/v1/{long}.json")[0] == 404
    dbase, _ = served
    assert get(f"{dbase}/data/{long}")[0] == 404
    assert get(f"{dbase}/{long}")[0] == 404
