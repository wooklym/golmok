"""golmok-viewer: serve the review viewer (tools/viewer) plus a data folder on localhost.

    golmok-viewer D:\\golmok_basemap\\yeonnam            -> http://127.0.0.1:8765/?tileset=/data/tileset.json
    golmok-viewer <folder> --port 9000 --no-browser
    golmok-viewer <basemap> --zone D:\\zones\\z_x\\v1     -> ...&zone=/zones/z_x/v1/manifest.json
    golmok-viewer --zone D:\\zones\\z_x\\v1\\manifest.json   (zone only, no basemap)

Routes:
    /            tools/viewer (index.html, app.js, zonemath.js, style.css)
    /data/...    the given folder (tileset.json, tiles/*.glb, manifest.json, splat tilesets ...)
    /zones/<zone_id>/v<version>/...
                 a zone version folder given with --zone (the folder holding manifest.json); only
                 ZONE_SUFFIXES are served (manifest/blockers JSON, collision/blockers GLB), not the OBJ chunks
    /cesium/...  tools/viewer/node_modules/cesium/Build/Cesium when installed (offline use);
                 otherwise the page falls back to the CDN build.

Every route stays inside its root: `..` segments, absolute or drive paths, backslashes, NUL and symbolic
links that lead outside the root are refused with 404 (resolve()).
"""

from __future__ import annotations

import argparse
import functools
import json
import re
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


ZONE_SUFFIXES = frozenset({".json", ".glb", ".gltf", ".bin", ".png", ".jpg", ".jpeg", ".ktx2"})
ZONE_ID_RE = re.compile(r"^z_[a-z0-9]+(_[a-z0-9]+)*$")  # docs/spec/zone-manifest.md §2


def _safe_rel(rel: str) -> bool:
    """Reject request paths that could name something outside a root before touching the file system."""
    if not rel:
        return True
    if "\x00" in rel or "\\" in rel or ":" in rel or rel.startswith("/"):
        return False
    return ".." not in rel.split("/")


def resolve(url_path: str, data_dir: Path | None, zones: dict[str, Path] | None = None) -> Path | None:
    """Map a request path to a file; None when outside the allowed roots.

    `zones` maps a mount prefix `<zone_id>/v<version>` to its zone version folder (zone_mount()).
    """
    path = unquote(urlsplit(url_path).path)
    suffixes = None
    if path.startswith("/data/"):
        if data_dir is None:
            return None
        root, rel = data_dir, path[len("/data/") :]
    elif path.startswith("/zones/"):
        parts = path[len("/zones/") :].split("/", 2)
        if len(parts) < 3 or not zones or f"{parts[0]}/{parts[1]}" not in zones:
            return None
        root, rel, suffixes = zones[f"{parts[0]}/{parts[1]}"], parts[2], ZONE_SUFFIXES
    elif path.startswith("/cesium/"):
        root, rel = CESIUM_BUILD, path[len("/cesium/") :]
    else:
        root, rel = VIEWER_DIR, path.lstrip("/") or "index.html"
    if not _safe_rel(rel):
        return None
    try:
        root_r = root.resolve()
        full = (root / rel).resolve()  # follows symbolic links: a link out of the root fails below
        full.relative_to(root_r)
    except (ValueError, OSError):
        return None
    if full.is_dir():
        full = full / "index.html"
    if suffixes is not None and full.suffix.lower() not in suffixes:
        return None
    return full


def zone_mount(path: Path) -> tuple[str, Path]:
    """(`<zone_id>/v<version>`, folder) for a zone manifest.json or the folder that holds it."""
    manifest = path / "manifest.json" if path.is_dir() else path
    if manifest.name != "manifest.json" or not manifest.is_file():
        raise ValueError(f"zone manifest.json 없음: {path}")
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"manifest가 객체가 아님: {manifest}")
    zone_id, version = doc.get("zone_id"), doc.get("version")
    if not isinstance(zone_id, str) or not ZONE_ID_RE.match(zone_id):
        raise ValueError(f"zone_id 형식 오류: {zone_id!r} ({manifest})")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError(f"version 형식 오류: {version!r} ({manifest})")
    return f"{zone_id}/v{version}", manifest.parent.resolve()


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, **EXTRA_TYPES}

    def __init__(self, *args, data_dir: Path | None, zones: dict[str, Path] | None = None, **kwargs):
        self.data_dir = data_dir
        self.zones = zones or {}
        super().__init__(*args, directory=str(VIEWER_DIR), **kwargs)

    def translate_path(self, path: str) -> str:
        full = resolve(path, self.data_dir, self.zones)
        # A path outside the roots maps to a file that cannot exist, so the base handler answers 404.
        return str(full) if full else str(VIEWER_DIR / "__forbidden__" / "denied")

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, fmt, *args):  # quieter than the default
        if "404" in str(args):
            super().log_message(fmt, *args)


def make_server(
    data_dir: Path | None, port: int, host: str = "127.0.0.1", zones: dict[str, Path] | None = None
) -> ThreadingHTTPServer:
    handler = functools.partial(Handler, data_dir=data_dir, zones=zones)
    return ThreadingHTTPServer((host, port), handler)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="베이스맵·Zone 검수 뷰어 서버")
    ap.add_argument("data_dir", type=Path, nargs="?", help="tileset.json / manifest.json 이 있는 폴더")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--tileset", default="tileset.json", help="처음 열 타일셋 (data_dir 기준 상대경로)")
    ap.add_argument(
        "--zone",
        type=Path,
        action="append",
        default=[],
        help="zone 버전 폴더 또는 그 manifest.json (반복 가능): /zones/<zone_id>/v<n>/ 로 서빙하고 오버레이",
    )
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    if args.data_dir is None and not args.zone:
        ap.error("data_dir 또는 --zone 이 필요함")
    if args.data_dir is not None and not args.data_dir.is_dir():
        ap.error(f"폴더가 아님: {args.data_dir}")
    zones: dict[str, Path] = {}
    for z in args.zone:
        try:
            prefix, folder = zone_mount(z)
        except (ValueError, OSError) as e:
            ap.error(str(e))
        if prefix in zones:
            ap.error(f"같은 zone 버전이 두 번: {prefix}")
        zones[prefix] = folder
    data_dir = args.data_dir.resolve() if args.data_dir is not None else None
    server = make_server(data_dir, args.port, zones=zones)
    query = [f"tileset=/data/{args.tileset}"] if data_dir is not None else []
    query += [f"zone=/zones/{prefix}/manifest.json" for prefix in zones]
    url = f"http://127.0.0.1:{args.port}/?" + "&".join(query)
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
