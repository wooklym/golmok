"""golmok-viewer: serve the review viewer (tools/viewer) plus a data folder on localhost.

    golmok-viewer D:\\golmok_basemap\\yeonnam            -> http://127.0.0.1:8765/?tileset=/data/tileset.json
    golmok-viewer <folder> --port 9000 --no-browser

Routes:
    /            tools/viewer (index.html, app.js, style.css)
    /data/...    the given folder (tileset.json, tiles/*.glb, manifest.json, splat tilesets ...)
    /cesium/...  tools/viewer/node_modules/cesium/Build/Cesium when installed (offline use);
                 otherwise the page falls back to the CDN build.
"""

from __future__ import annotations

import argparse
import functools
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

VIEWER_DIR = Path(__file__).resolve().parent.parent / "viewer"
CESIUM_BUILD = VIEWER_DIR / "node_modules" / "cesium" / "Build" / "Cesium"

EXTRA_TYPES = {
    ".glb": "model/gltf-binary",
    ".gltf": "model/gltf+json",
    ".json": "application/json",
    ".spz": "application/octet-stream",
    ".wasm": "application/wasm",
    ".mjs": "text/javascript",
}


def resolve(url_path: str, data_dir: Path) -> Path | None:
    """Map a request path to a file; None when outside the allowed roots."""
    path = unquote(urlsplit(url_path).path)
    if path.startswith("/data/"):
        root, rel = data_dir, path[len("/data/") :]
    elif path.startswith("/cesium/"):
        root, rel = CESIUM_BUILD, path[len("/cesium/") :]
    else:
        root, rel = VIEWER_DIR, path.lstrip("/") or "index.html"
    full = (root / rel).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError:
        return None
    if full.is_dir():
        full = full / "index.html"
    return full


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, **EXTRA_TYPES}

    def __init__(self, *args, data_dir: Path, **kwargs):
        self.data_dir = data_dir
        super().__init__(*args, directory=str(VIEWER_DIR), **kwargs)

    def translate_path(self, path: str) -> str:
        full = resolve(path, self.data_dir)
        # A path outside the roots maps to a file that cannot exist, so the base handler answers 404.
        return str(full) if full else str(VIEWER_DIR / "__forbidden__" / "denied")

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, fmt, *args):  # quieter than the default
        if "404" in str(args):
            super().log_message(fmt, *args)


def make_server(data_dir: Path, port: int, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    handler = functools.partial(Handler, data_dir=data_dir)
    return ThreadingHTTPServer((host, port), handler)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="베이스맵·Zone 검수 뷰어 서버")
    ap.add_argument("data_dir", type=Path, help="tileset.json / manifest.json 이 있는 폴더")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--tileset", default="tileset.json", help="처음 열 타일셋 (data_dir 기준 상대경로)")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    if not args.data_dir.is_dir():
        ap.error(f"폴더가 아님: {args.data_dir}")
    server = make_server(args.data_dir.resolve(), args.port)
    url = f"http://127.0.0.1:{args.port}/?tileset=/data/{args.tileset}"
    print(f"viewer: {url}")
    source = "local node_modules" if CESIUM_BUILD.exists() else "CDN (internet needed)"
    print(f"cesium: {source}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
