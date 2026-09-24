"""Split a reconstructed mesh into chunks for UE (Nanite static meshes, docs/spec/zone-manifest.md).

Faces are assigned whole (by centroid) to one chunk; vertices/UVs/normals are duplicated per chunk, so
UVs, materials and UDIM tiles are kept exactly. Output is OBJ + MTL:
- glTF has no UDIM concept (UVs outside [0, 1] per image) and would need textures copied or embedded;
- OBJ keeps RealityScan's UVs and material names untouched and the .mtl points at the original
  8K UDIM textures (<name>.1001.png ...), which UE imports as UDIM virtual textures.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .objio import Mesh, rewrite_mtl, write_obj

CHUNK_MANIFEST = "chunk_manifest.json"


@dataclass
class ChunkInfo:
    id: str
    faces: np.ndarray  # indices into the source mesh


def grid_chunks(mesh: Mesh, size: float, origin: tuple[float, float] | None = None) -> list[ChunkInfo]:
    """Horizontal grid (x, y) of `size` m; ids c_<col>_<row> counted from the grid's south-west cell."""
    if size <= 0:
        raise ValueError("size must be > 0")
    c = mesh.face_centroids()[:, :2]
    o = np.asarray(origin if origin is not None else np.floor(c.min(axis=0) / size) * size)
    ij = np.floor((c - o) / size).astype(np.int64)
    ij -= ij.min(axis=0)
    keys = ij[:, 0] * 100000 + ij[:, 1]
    out = []
    for key in np.unique(keys):
        faces = np.nonzero(keys == key)[0]
        i, j = divmod(int(key), 100000)
        out.append(ChunkInfo(id=f"c_{i:03d}_{j:03d}", faces=faces))
    return out


def polyline_chunks(mesh: Mesh, line_xy: np.ndarray, size: float) -> list[ChunkInfo]:
    """Chunks by arc length along a centerline (zone-local x, y): s_<n> covers [n*size, (n+1)*size)."""
    line_xy = np.asarray(line_xy, dtype=np.float64)
    if len(line_xy) < 2:
        raise ValueError("centerline needs at least 2 points")
    c = mesh.face_centroids()[:, :2]
    a, b = line_xy[:-1], line_xy[1:]
    seg = b - a
    seg_len = np.linalg.norm(seg, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    best_s = np.zeros(len(c))
    best_d = np.full(len(c), np.inf)
    for k in range(len(seg)):
        if seg_len[k] == 0:
            continue
        t = np.clip(((c - a[k]) @ seg[k]) / seg_len[k] ** 2, 0.0, 1.0)
        p = a[k] + t[:, None] * seg[k]
        d = np.linalg.norm(c - p, axis=1)
        better = d < best_d
        best_d[better] = d[better]
        best_s[better] = cum[k] + t[better] * seg_len[k]
    n = np.floor(best_s / size).astype(np.int64)
    return [ChunkInfo(id=f"s_{k:03d}", faces=np.nonzero(n == k)[0]) for k in np.unique(n)]


def write_chunks(
    mesh: Mesh,
    chunks: list[ChunkInfo],
    out_dir: str | Path,
    source: str = "",
) -> dict:
    """Write chunks/<id>.obj + one rewritten .mtl per source mtllib; returns the chunk manifest dict."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    mtl_names, textures = [], []
    for lib in mesh.mtllibs:
        if lib.is_file():
            dst = out / lib.name
            textures += [str(t) for t in rewrite_mtl(lib, dst)]
            mtl_names.append(lib.name)
    entries = []
    for ch in chunks:
        sub = mesh.submesh(ch.faces)
        path = write_obj(
            sub, out / f"{ch.id}.obj", " ".join(mtl_names) or None, header=f"golmok-mesh chunk {ch.id}"
        )
        lo, hi = sub.bounds()
        used_mats = (
            sorted({sub.materials[m] for m in np.unique(sub.f_mat)} - {""}) if sub.f_mat is not None else []
        )
        entries.append(
            {
                "id": ch.id,
                "file": path.name,
                "bbox_enu": [np.round(lo, 4).tolist(), np.round(hi, 4).tolist()],
                "tris": int(sub.n_faces),
                "materials": used_mats,
                "udim_tiles": mesh.udim_tiles(ch.faces),
            }
        )
    return {
        "source": source,
        "chunks": entries,
        "mtl": mtl_names,
        "textures": sorted(set(textures)),
        "total_tris": int(sum(e["tris"] for e in entries)),
    }


def update_zone_manifest(manifest_path: str | Path, chunk_manifest: dict, chunk_dir: str | Path) -> dict:
    """Set layers.visual.chunks (format nanite_mesh) from a chunk manifest. URIs relative to the manifest."""
    from golmok_tools.zone import manifest as zm

    manifest_path = Path(manifest_path)
    d = zm.load(manifest_path)
    base = manifest_path.parent.resolve()
    chunk_dir = Path(chunk_dir).resolve()
    rel_dir = os.path.relpath(chunk_dir, base).replace(os.sep, "/")
    if rel_dir.startswith(".."):
        raise ValueError(f"chunk folder {chunk_dir} must be inside the zone version folder {base}")
    prefix = "" if rel_dir == "." else rel_dir + "/"
    d["layers"]["visual"]["format"] = "nanite_mesh"
    d["layers"]["visual"]["chunks"] = [
        {"id": e["id"], "uri": prefix + e["file"], "bbox_enu": e["bbox_enu"], "tris": e["tris"]}
        for e in chunk_manifest["chunks"]
    ]
    zm.save(d, manifest_path)
    return d


def save_chunk_manifest(doc: dict, out_dir: str | Path) -> Path:
    p = Path(out_dir) / CHUNK_MANIFEST
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    return p
