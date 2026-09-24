import json
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
