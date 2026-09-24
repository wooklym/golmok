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

from .objio import Mesh, rewrite_mtl_text, texture_exists, write_obj

CHUNK_MANIFEST = "chunk_manifest.json"
_CHUNK_GLOBS = ("c_*.obj", "s_*.obj")


@dataclass
class ChunkInfo:
    id: str
    faces: np.ndarray  # indices into the source mesh


def _signed(i: int, pos: str, neg: str) -> str:
    """Cell index as an id-safe token (ids allow only [A-Za-z0-9_]): 3 -> e003, -2 -> w002."""
    return f"{pos}{i:03d}" if i >= 0 else f"{neg}{-i:03d}"


def grid_chunks(mesh: Mesh, size: float, origin: tuple[float, float] = (0.0, 0.0)) -> list[ChunkInfo]:
    """Horizontal grid (x, y) of `size` m cells counted from `origin` (zone-local, default the zone origin).

    Ids are absolute, so the same world cell gets the same id whichever export part it comes from:
    c_<e|w><col>_<n|s><row>, e.g. c_e000_n000 = [0, size) x [0, size), c_w001_s002 = [-size, 0) x
    [-3 size, -2 size).
    """
    if size <= 0:
        raise ValueError("size must be > 0")
    c = mesh.face_centroids()[:, :2]
    ij = np.floor((c - np.asarray(origin, dtype=np.float64)) / size).astype(np.int64)
    cells, inv = np.unique(ij, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    order = np.argsort(inv, kind="stable")
    bounds = np.searchsorted(inv[order], np.arange(len(cells) + 1))
    return [
        ChunkInfo(
            id=f"c_{_signed(int(i), 'e', 'w')}_{_signed(int(j), 'n', 's')}",
            faces=np.sort(order[bounds[k] : bounds[k + 1]]),
        )
        for k, (i, j) in enumerate(cells)
    ]


def polyline_chunks(mesh: Mesh, line_xy: np.ndarray, size: float) -> list[ChunkInfo]:
    """Chunks by arc length along a centerline (zone-local x, y): s_<n> covers [n*size, (n+1)*size).

    Beyond the line's ends the first/last segment is extended, so geometry past an end gets its own
    chunks (s_m001 = [-size, 0) before the start) instead of piling into the first or last one.
    """
    line_xy = np.asarray(line_xy, dtype=np.float64)
    if len(line_xy) < 2:
        raise ValueError("centerline needs at least 2 points")
    if size <= 0:
        raise ValueError("size must be > 0")
    c = mesh.face_centroids()[:, :2]
    a, b = line_xy[:-1], line_xy[1:]
    seg = b - a
    seg_len = np.linalg.norm(seg, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    valid = np.nonzero(seg_len > 0)[0]
    if not len(valid):
        raise ValueError("centerline has zero length")
    best_s = np.zeros(len(c))
    best_d = np.full(len(c), np.inf)
    for k in valid:
        t = ((c - a[k]) @ seg[k]) / seg_len[k] ** 2
        t = np.clip(t, -np.inf if k == valid[0] else 0.0, np.inf if k == valid[-1] else 1.0)
        p = a[k] + t[:, None] * seg[k]
        d = np.linalg.norm(c - p, axis=1)
        better = d < best_d
        best_d[better] = d[better]
        best_s[better] = cum[k] + t[better] * seg_len[k]
    n = np.floor(best_s / size).astype(np.int64)
    return [ChunkInfo(id=f"s_{_signed(int(k), '', 'm')}", faces=np.nonzero(n == k)[0]) for k in np.unique(n)]


def load_chunk_manifest(out_dir: str | Path) -> dict | None:
    p = Path(out_dir) / CHUNK_MANIFEST
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def prepare_out_dir(out_dir: str | Path, mode: str = "new") -> dict | None:
    """Check the chunk folder before writing; returns the chunk manifest to append to (or None).

    new: refuse a folder that already has chunks (a second export part would silently replace them);
    append: add to the existing chunks; overwrite: delete the chunk files and .mtl listed in the old
    chunk_manifest.json (and stray c_*.obj / s_*.obj) first.
    """
    out = Path(out_dir)
    existing = load_chunk_manifest(out)
    stray = [p for g in _CHUNK_GLOBS for p in out.glob(g)] if out.is_dir() else []
    if mode == "append":
        if existing is None and stray:
            raise ValueError(f"{out}: chunk files without {CHUNK_MANIFEST} — cannot append; use --overwrite")
        return existing
    if mode == "overwrite":
        names = [e["file"] for e in (existing or {}).get("chunks", [])] + (existing or {}).get("mtl", [])
        for p in {out / n for n in names} | set(stray) | {out / CHUNK_MANIFEST}:
            if p.is_file():
                p.unlink()
        return None
    if mode != "new":
        raise ValueError(f"unknown mode {mode!r}")
    if existing is not None or stray:
        raise ValueError(
            f"{out} already has chunks — --append adds another export part, --overwrite redoes the folder"
        )
    return None


def write_chunks(
    mesh: Mesh,
    chunks: list[ChunkInfo],
    out_dir: str | Path,
    source: str = "",
    existing: dict | None = None,
) -> dict:
    """Write <out>/<id>.obj + one rewritten .mtl per source mtllib; returns the chunk manifest dict.

    With `existing` (a loaded chunk manifest) the chunks are added to it: an id that is already taken (the
    same cell from another export part) gets a suffix _2, _3 …; existing files are never overwritten.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    doc = existing or {}
    old_entries = list(doc.get("chunks", []))
    mtl_names = []
    textures = set(doc.get("textures", []))
    missing = {k: set(v) for k, v in doc.get("missing", {"mtl": [], "textures": []}).items()}
    for lib in mesh.mtllibs:
        if not lib.is_file():
            missing["mtl"].add(str(lib))
            continue
        name = lib.name.replace(" ", "_")  # 'mtllib' separates names with spaces
        text, tex = rewrite_mtl_text(lib, out)
        dst = out / name
        if name in doc.get("mtl", []) and dst.is_file():
            if dst.read_text(encoding="utf-8") != text:
                raise ValueError(
                    f"{dst} already exists with other content (another export part with the same .mtl "
                    "name) — rename that part's .mtl and its mtllib line"
                )
        else:
            with open(dst, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        mtl_names.append(name)
        textures |= {str(t) for t in tex}
        missing["textures"] |= {str(t) for t in tex if not texture_exists(t)}
    taken = {e["id"] for e in old_entries}
    entries = []
    for ch in chunks:
        cid, k = ch.id, 1
        while cid in taken or (out / f"{cid}.obj").exists():
            k += 1
            cid = f"{ch.id}_{k}"
        taken.add(cid)
        sub = mesh.submesh(ch.faces)
        path = write_obj(
            sub, out / f"{cid}.obj", " ".join(mtl_names) or None, header=f"golmok-mesh chunk {cid}"
        )
        lo, hi = sub.bounds()
        used_mats = (
            sorted({sub.materials[m] for m in np.unique(sub.f_mat)} - {""}) if sub.f_mat is not None else []
        )
        entries.append(
            {
                "id": cid,
                "file": path.name,
                "source": source,
                "bbox_enu": [np.round(lo, 4).tolist(), np.round(hi, 4).tolist()],
                "tris": int(sub.n_faces),
                "materials": used_mats,
                "udim_tiles": mesh.udim_tiles(ch.faces),
            }
        )
    all_entries = old_entries + entries
    return {
        "sources": [*doc.get("sources", []), source],
        "chunks": all_entries,
        "mtl": sorted(set(doc.get("mtl", [])) | set(mtl_names)),
        "textures": sorted(textures),
        "missing": {k: sorted(v) for k, v in missing.items()},
        "total_tris": int(sum(e["tris"] for e in all_entries)),
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
