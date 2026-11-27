import contextlib
import json
import os
import queue
import signal
import socket
import subprocess
import sys
import threading
import time
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


def test_zone_id_limit_is_64_chars(tmp_path: Path):
    zdir = _zone(tmp_path / "z", zone_id="z_" + "a" * 62)
    assert vs.zone_mount(zdir)[0] == "z_" + "a" * 62 + "/v1"


def test_no_cors_header(served):
    base, _ = served
    with urllib.request.urlopen(base + "/data/tileset.json", timeout=5) as r:
        assert r.headers.get("Access-Control-Allow-Origin") is None
        assert r.headers.get("Cache-Control") == "no-store"


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
        {"zone_id": "z_ok\n", "version": 1},
        {"zone_id": "z_" + "a" * 63, "version": 1},
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
        "/zones/z_test_001/v1/CON.json",
        "/zones/z_test_001/v1/nul",
        "/zones/z_test_001/v1/visual/com1.glb",
        "/zones/z_test_001/v1/LPT9%20.json",
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
        "/data/tiles/AUX.glb",
        "/data/prn",
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


def _raw_get_status(port: int, path: str) -> str:
    """One HTTP/1.1 GET over a raw socket; returns the status code or the client-side error name."""
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=10)
        try:
            s.sendall(f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n".encode())
            buf = b""
            while len(buf) < 12:  # "HTTP/1.1 200"
                chunk = s.recv(64)
                if not chunk:
                    break
                buf += chunk
        finally:
            s.close()
        return buf.split(b" ")[1].decode(errors="replace") if buf.startswith(b"HTTP/") else "NO-RESPONSE"
    except (OSError, IndexError) as e:  # ConnectionResetError / timeout / short response
        return type(e).__name__


def test_tile_burst_of_18_connections_are_all_answered(served):
    """Regression (2026-11-27): the viewer requests 18 tile .glb in the same second. With socketserver's
    default listen backlog (request_queue_size = 5) macOS RST some connections before accept — the smoke
    test saw net::ERR_CONNECTION_RESET with no server access-log line and no handler exception
    (5/20 runs; raw-socket repro: 18 simultaneous GETs → RST 7/6/5 of 18, server alive). At 128 the burst
    is clean (0 RST in repro, 0/20 smoke). On Linux an overflowing queue retries the SYN instead of
    RST-ing, so only the attribute pin below can catch a revert on Linux/Windows (that part is [미확인]
    as behaviour — only the macOS side was reproduced here); the burst test pins the macOS behaviour."""
    assert vs.Server.request_queue_size >= 18, (
        "accept 큐가 타일 18건 동시 접속을 못 받음 (기본 5로 되돌리면 안 됨)"
    )  # noqa: E501
    base, data = served
    port = int(base.rsplit(":", 1)[1])
    for i in range(18):  # real terrain tiles are ~30 KB each
        (data / "tiles" / f"t_{i}.glb").write_bytes(b"glTF" + bytes(4) + b"\0" * (30 * 1024))
    res: list[str] = [""] * 18

    def worker(i: int) -> None:
        res[i] = _raw_get_status(port, f"/data/tiles/t_{i}.glb")

    ts = [threading.Thread(target=worker, args=(i,)) for i in range(18)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=20)
    assert res.count("200") == 18, f"실패 접속: {[r for r in res if r != '200']}"


def test_readiness_line_arrives_through_a_pipe(tmp_path: Path):
    # Regression (2026-11-27, macOS): smoke.mjs waits for the "viewer:" readiness line reading the server's
    # stdout through a pipe. Without flush=True CPython block-buffers a piped stdout (all OSes) and the line
    # never arrives. The child therefore runs without PYTHONUNBUFFERED and with stdout as a pipe.
    # select() cannot wait on pipes on Windows (WinError 10038), so a daemon reader thread feeds a Queue.
    with socket.socket() as s:  # find a free port so parallel runs do not collide
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {k: v for k, v in os.environ.items() if k != "PYTHONUNBUFFERED"}
    proc = subprocess.Popen(
        [
            sys.executable,
            "-X",
            "faulthandler",
            "-m",
            "golmok_tools.viewer_server",
            str(tmp_path),
            "--port",
            str(port),
            "--no-browser",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    out_q: queue.Queue = queue.Queue()
    err_q: queue.Queue = queue.Queue()

    def pump(pipe, q: queue.Queue) -> None:
        try:
            for line in pipe:
                q.put(line)
        except (OSError, ValueError):  # pipe closed during teardown
            pass

    for pipe, q in ((proc.stdout, out_q), (proc.stderr, err_q)):
        threading.Thread(target=pump, args=(pipe, q), daemon=True).start()

    def drain(q: queue.Queue) -> str:
        got = []
        while True:
            try:
                got.append(q.get_nowait())
            except queue.Empty:
                return "".join(got)

    try:
        deadline = time.monotonic() + 30.0
        line = ""
        while time.monotonic() < deadline:
            try:
                candidate = out_q.get(timeout=0.5)
            except queue.Empty:
                # If the child died before printing, do not burn the whole deadline waiting for it.
                if proc.poll() is not None:
                    break
                continue
            if "viewer:" in candidate:
                line = candidate
                break
        if "viewer:" not in line:
            # Record BEFORE SIGABRT: after the abort poll() is always not-None, and a plain
            # timeout would be mislabelled "준비 줄 전에 종료됨 (returncode=-6)" (review R133 (B2)).
            exited = proc.poll() is not None
            if os.name == "posix" and not exited:
                # -X faulthandler is on: SIGABRT makes the child dump all thread stacks to stderr
                # before dying, so a CI timeout shows where it is stuck (e.g. a slow DNS lookup).
                with contextlib.suppress(OSError):
                    proc.send_signal(signal.SIGABRT)
                time.sleep(1.0)
            why = (
                f"자식 프로세스가 준비 줄 전에 종료됨 (returncode={proc.poll()})"
                if exited
                else "30초 안에 'viewer:' 준비 줄이 오지 않음"
            )
            raise AssertionError(f"{why} (stderr={drain(err_q)!r}, stdout={drain(out_q)!r})")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        for pipe in (proc.stdout, proc.stderr):
            try:
                pipe.close()
            except OSError:
                pass
