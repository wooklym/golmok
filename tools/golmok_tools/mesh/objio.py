"""Mesh I/O that keeps what RealityScan exports: separate position/UV/normal indices, materials, UDIM UVs.

Coordinates are zone-local ENU (x=east, y=north, z=up, m). OBJ is read as-is (RealityScan export set to
the zone's local frame, Z-up). GLB is glTF Y-up and is converted back: (x, y, z)_gltf -> (x, -z, y)_enu.

Memory: read_obj parses the text in batches of _BATCH lines, so the peak is the finished arrays
(~9 int64 index columns + float64 attributes) plus a bounded batch. Measured peak (tracemalloc/RSS on a
RealityScan-like OBJ with v/vt/vn) is in docs/runbooks/recon-postprocess.md §0. Export larger scenes in parts.
"""

from __future__ import annotations

import io
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Mesh:
    v: np.ndarray  # (N, 3) float64 positions
    f_v: np.ndarray  # (F, 3) int64 position indices
    vt: np.ndarray | None = None  # (M, 2) UVs (UDIM tiles may exceed [0, 1])
    f_vt: np.ndarray | None = None  # (F, 3)
    vn: np.ndarray | None = None  # (K, 3)
    f_vn: np.ndarray | None = None  # (F, 3)
    f_mat: np.ndarray | None = None  # (F,) index into materials
    materials: list[str] = field(default_factory=list)
    mtllibs: list[Path] = field(default_factory=list)  # absolute paths of .mtl files

    @property
    def n_faces(self) -> int:
        return len(self.f_v)

    def face_centroids(self) -> np.ndarray:
        return self.v[self.f_v].mean(axis=1)

    def face_areas(self) -> np.ndarray:
        a, b, c = (self.v[self.f_v[:, i]] for i in range(3))
        return 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)

    def face_normals(self) -> np.ndarray:
        a, b, c = (self.v[self.f_v[:, i]] for i in range(3))
        n = np.cross(b - a, c - a)
        norm = np.linalg.norm(n, axis=1, keepdims=True)
        return np.divide(n, norm, out=np.zeros_like(n), where=norm > 0)

    def bounds(self) -> np.ndarray:
        used = self.v[np.unique(self.f_v)] if self.n_faces else self.v
        return np.array([used.min(axis=0), used.max(axis=0)]) if len(used) else np.zeros((2, 3))

    def udim_tiles(self, faces: np.ndarray | None = None) -> list[int]:
        """UDIM tile (1001 + u + 10 v) of each face's UV centroid, unique and sorted."""
        if self.vt is None or self.f_vt is None:
            return []
        f = self.f_vt if faces is None else self.f_vt[faces]
        if not len(f):
            return []
        c = self.vt[f].mean(axis=1)
        tiles = 1001 + np.floor(c[:, 0]).astype(np.int64) + 10 * np.floor(c[:, 1]).astype(np.int64)
        return sorted(int(t) for t in np.unique(tiles))

    def submesh(self, faces: np.ndarray) -> Mesh:
        """Faces subset with compacted attribute arrays (vertices duplicated per chunk, never merged)."""
        faces = np.asarray(faces)

        def compact(values, idx):
            if values is None or idx is None:
                return None, None
            sel = idx[faces]
            used, inv = np.unique(sel, return_inverse=True)
            return values[used], inv.reshape(sel.shape)

        v, f_v = compact(self.v, self.f_v)
        vt, f_vt = compact(self.vt, self.f_vt)
        vn, f_vn = compact(self.vn, self.f_vn)
        return Mesh(
            v=v if v is not None else np.zeros((0, 3)),
            f_v=f_v if f_v is not None else np.zeros((0, 3), np.int64),
            vt=vt,
            f_vt=f_vt,
            vn=vn,
            f_vn=f_vn,
            f_mat=None if self.f_mat is None else self.f_mat[faces],
            materials=list(self.materials),
            mtllibs=list(self.mtllibs),
        )


# -- OBJ ------------------------------------------------------------------------------------------

_FACE_TOKEN = re.compile(r"^(-?\d+)(?:/(-?\d*)(?:/(-?\d+))?)?$")
_BATCH = 200_000  # lines converted to arrays at a time: bounds the Python string/token lists while reading
_TAGS = ("v ", "vt", "vn", "f ")


def _floats(lines: list[str], n: int) -> np.ndarray:
    if not lines:
        return np.zeros((0, n))
    # "v x y z [w]" / "vt u v [w]": take the first n numbers after the tag
    arr = [ln.split()[1 : n + 1] for ln in lines]
    return np.asarray(arr, dtype=np.float64)


def _parse_faces(path, lines, meta) -> tuple[np.ndarray, np.ndarray]:
    """(F, 3, 3) indices [v, vt, vn] 0-based (-1 = missing) and (F,) material per triangle."""
    if not lines:
        return np.full((0, 3, 3), -1, np.int64), np.zeros(0, np.int64)
    first = lines[0].split()[1]
    if "/" not in first:
        cols = [0]
    elif "//" in first:
        cols = [0, 2]
    else:
        cols = [0, 1, 2][: first.count("/") + 1]
    # Fast path (RealityScan): all triangles, same token layout on every line, positive indices
    n_slash, n_double = 3 * first.count("/"), 3 * first.count("//")
    arr = None
    if all(ln.count("/") == n_slash and ln.count("//") == n_double for ln in lines):
        try:
            flat = " ".join(ln[2:] for ln in lines).replace("/", " ").split()
            arr = np.asarray(flat, dtype=np.int64)
            del flat
        except ValueError:
            arr = None
    if arr is not None and arr.size == 3 * len(cols) * len(lines) and (arr > 0).all():
        arr = arr.reshape(len(lines), 3, len(cols)) - 1
        f = np.full((len(lines), 3, 3), -1, np.int64)
        f[:, :, cols] = arr
        return f, np.asarray([m[0] for m in meta], np.int64)
    return _parse_faces_slow(path, lines, meta)


def _parse_faces_slow(path, lines, meta):
    rows, mats = [], []
    for line, (mat, nv, nvt, nvn) in zip(lines, meta, strict=True):
        toks = line.split()[1:]
        base = (nv, nvt, nvn)
        idx = []
        for tok in toks:
            m = _FACE_TOKEN.match(tok)
            if not m:
                raise ValueError(f"{path}: bad face token {tok!r}")
            corner = [-1, -1, -1]
            for k in range(3):
                g = m.group(k + 1)
                if g:
                    i = int(g)
                    corner[k] = i - 1 if i > 0 else base[k] + i
                    if corner[k] < 0:
                        raise ValueError(f"{path}: face index {i} out of range in {line.strip()!r}")
            idx.append(corner)
        for i in range(1, len(idx) - 1):  # fan triangulation
            rows.append([idx[0], idx[i], idx[i + 1]])
            mats.append(mat)
    return np.asarray(rows, np.int64).reshape(-1, 3, 3), np.asarray(mats, np.int64)


def _resolve_mtllibs(folder: Path, rest: str) -> list[Path]:
    """'mtllib a.mtl b.mtl' or 'mtllib my model.mtl': the whole remainder first, then space-separated."""
    rest = rest.strip()
    if not rest:
        return []
    whole = (folder / rest).resolve()
    names = rest.split()
    if whole.is_file() or len(names) == 1:
        return [whole]
    parts = [(folder / n).resolve() for n in names]
    return parts if any(p.is_file() for p in parts) else [whole]


def read_obj(path: str | Path) -> Mesh:
    """Read a Wavefront OBJ (polygons are fan-triangulated; negative indices supported).

    Lines are converted to arrays every _BATCH lines, so peak memory stays near the size of the result.
    """
    path = Path(path)
    lines = {"v ": [], "vt": [], "vn": []}
    arrays = {"v ": [], "vt": [], "vn": []}
    width = {"v ": 3, "vt": 2, "vn": 3}
    face_lines: list[str] = []
    face_meta: list[tuple[int, int, int, int]] = []  # material, v/vt/vn counts so far (negative indices)
    f_cols: list[list[np.ndarray]] = [[], [], []]  # per batch: v, vt, vn index columns (F, 3)
    f_mats: list[np.ndarray] = []
    materials: list[str] = []
    mat_index: dict[str, int] = {}
    mtllibs: list[Path] = []
    cur = -1
    nv = nvt = nvn = 0

    def flush_faces():
        f, mats = _parse_faces(path, face_lines, face_meta)
        for k in range(3):
            f_cols[k].append(f[:, :, k].copy())
        f_mats.append(mats)
        face_lines.clear()
        face_meta.clear()

    with open(path, encoding="utf-8-sig", errors="replace") as fh:  # -sig: drop a UTF-8 BOM
        for line in fh:
            tag = line[:2]
            if tag not in _TAGS:
                # tabs / leading whitespace after or before the keyword are valid OBJ whitespace
                parts = line.split(maxsplit=1)
                if not parts:
                    continue
                key, rest = parts[0], (parts[1] if len(parts) > 1 else "")
                if key == "usemtl":
                    name = rest.strip()
                    if name not in mat_index:
                        mat_index[name] = len(materials)
                        materials.append(name)
                    cur = mat_index[name]
                    continue
                if key == "mtllib":
                    mtllibs += _resolve_mtllibs(path.parent, rest)
                    continue
                if key not in ("v", "vt", "vn", "f"):
                    continue
                line = f"{key} {rest}"
                tag = line[:2]
            if tag == "f ":
                face_lines.append(line)
                face_meta.append((cur, nv, nvt, nvn))
                if len(face_lines) >= _BATCH:
                    flush_faces()
                continue
            if tag == "v ":
                nv += 1
            elif tag == "vt":
                nvt += 1
            else:
                nvn += 1
            buf = lines[tag]
            buf.append(line)
            if len(buf) >= _BATCH:
                arrays[tag].append(_floats(buf, width[tag]))
                buf.clear()
    flush_faces()
    for tag, buf in lines.items():
        if buf:
            arrays[tag].append(_floats(buf, width[tag]))
            buf.clear()

    def cat(parts, w):
        out = np.concatenate(parts) if parts else np.zeros((0, w))
        parts.clear()
        return out

    v = cat(arrays["v "], 3)
    vt = cat(arrays["vt"], 2) if nvt else None
    vn = cat(arrays["vn"], 3) if nvn else None
    f_v, f_vt, f_vn = (np.concatenate(c) for c in f_cols)
    f_cols.clear()
    f_mat = np.concatenate(f_mats)
    for col, count, what in ((f_v, nv, "v"), (f_vt, nvt, "vt"), (f_vn, nvn, "vn")):
        if len(col) and col.max() >= count:
            raise ValueError(
                f"{path}: face {what} index {int(col.max()) + 1} out of range ({count} {what} lines)"
            )
    if len(f_v) and f_v.min() < 0:
        raise ValueError(f"{path}: face without a vertex index")
    has_vt = vt is not None and len(f_v) and (f_vt >= 0).all()
    has_vn = vn is not None and len(f_v) and (f_vn >= 0).all()
    if len(f_mat) and (f_mat < 0).any():  # faces before any usemtl
        if "" not in mat_index:
            mat_index[""] = len(materials)
            materials.append("")
        f_mat[f_mat < 0] = mat_index[""]
    return Mesh(
        v=v,
        f_v=f_v,
        vt=vt if has_vt else None,
        f_vt=f_vt if has_vt else None,
        vn=vn if has_vn else None,
        f_vn=f_vn if has_vn else None,
        f_mat=f_mat,
        materials=materials,
        mtllibs=mtllibs,
    )


def _fmt_rows(a: np.ndarray, tag: str, fmt: str) -> str:
    if a is None or not len(a):
        return ""
    body = "\n".join(tag + " " + " ".join(fmt % x for x in row) for row in a)
    return body + "\n"


def write_obj(mesh: Mesh, path: str | Path, mtllib: str | None = None, header: str = "") -> Path:
    """Write OBJ (1-based indices, faces grouped by material). Positions keep 1e-6 m precision."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = [f"# {line}\n" for line in header.splitlines()]
    if mtllib:
        parts.append(f"mtllib {mtllib}\n")
    parts.append(_fmt_rows(mesh.v, "v", "%.6f"))
    parts.append(_fmt_rows(mesh.vt, "vt", "%.7f"))
    parts.append(_fmt_rows(mesh.vn, "vn", "%.6f"))
    f_mat = mesh.f_mat if mesh.f_mat is not None else np.zeros(mesh.n_faces, np.int64)
    order = np.argsort(f_mat, kind="stable")
    cols = [mesh.f_v]
    if mesh.f_vt is not None:
        cols.append(mesh.f_vt)
    if mesh.f_vn is not None:
        cols.append(mesh.f_vn)
    corner = "/".join(["%d"] * len(cols))
    if mesh.f_vt is None and mesh.f_vn is not None:
        corner = "%d//%d"
    fmt = "f " + " ".join([corner] * 3)
    idx = np.stack(cols, axis=2) + 1  # (F, 3 corners, k) 1-based

    def name_of(m):
        return mesh.materials[m] if mesh.materials and m < len(mesh.materials) else ""

    # faces without a material go first (before any usemtl), or re-reading would give them the previous one
    for m in sorted(np.unique(f_mat), key=lambda m: (name_of(m) != "", m)):
        sel = order[f_mat[order] == m]
        name = name_of(m)
        if name:
            parts.append(f"usemtl {name}\n")
        buf = io.StringIO()
        np.savetxt(buf, idx[sel].reshape(len(sel), -1), fmt=fmt)
        parts.append(buf.getvalue())
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("".join(parts))
    return path


# -- MTL ------------------------------------------------------------------------------------------

_MAP_KEYS = ("map_", "bump", "disp", "decal", "norm", "refl")
# MTL texture options and how many arguments they take (-o/-s/-t take 1 to 3 numbers)
_MAP_OPTS = {
    "-blendu": 1, "-blendv": 1, "-bm": 1, "-boost": 1, "-cc": 1, "-clamp": 1, "-imfchan": 1,
    "-mm": 2, "-o": 3, "-s": 3, "-t": 3, "-texres": 1, "-type": 1,
}  # fmt: skip
_UP_TO_3 = ("-o", "-s", "-t")


def _is_number(tok: str) -> bool:
    try:
        float(tok)
    except ValueError:
        return False
    return True


def split_map_line(line: str) -> tuple[str, str] | None:
    """'map_Kd -bm 1 tex/my file.png' -> ('map_Kd -bm 1', 'tex/my file.png'); None if not a texture line.

    Known options and their arguments are skipped; everything after them is the file name, spaces included.
    """
    s = line.strip()
    if not s.lower().startswith(_MAP_KEYS):
        return None
    toks = s.split()
    i = 1
    while i < len(toks) - 1 and toks[i].lower() in _MAP_OPTS:
        opt = toks[i].lower()
        i += 1
        if opt in _UP_TO_3:
            k = 0
            while k < 3 and i < len(toks) - 1 and _is_number(toks[i]):
                i += 1
                k += 1
        else:
            i += _MAP_OPTS[opt]
    if i >= len(toks):
        return None
    parts = s.split(maxsplit=i)
    return " ".join(parts[:i]), parts[i]


def mtl_textures(mtl_path: Path) -> list[str]:
    """Texture paths referenced by a .mtl (as written, options stripped)."""
    out = []
    for line in Path(mtl_path).read_text(encoding="utf-8-sig", errors="replace").splitlines():
        split = split_map_line(line)
        if split:
            out.append(split[1])
    return out


def texture_exists(tex: Path) -> bool:
    """True if the file exists; for '<UDIM>' names, if at least one tile (1001 …) exists."""
    tex = Path(tex)
    if "<udim>" in tex.name.lower():
        pattern = re.sub("<udim>", "[0-9][0-9][0-9][0-9]", tex.name, flags=re.IGNORECASE)
        return any(tex.parent.glob(pattern)) if tex.parent.is_dir() else False
    return tex.is_file()


def _rel_or_abs(target: Path, start: Path) -> str:
    """Relative path with '/', or the absolute path when there is none (Windows: another drive)."""
    try:
        return os.path.relpath(target, start).replace(os.sep, "/")
    except ValueError:
        return Path(target).as_posix()


def rewrite_mtl_text(src: Path, dst_dir: Path) -> tuple[str, list[Path]]:
    """Text of src's .mtl with texture paths rewritten for a .mtl in dst_dir, and the resolved textures."""
    src = Path(src).resolve()
    base = Path(dst_dir).resolve()
    textures, lines = [], []
    for line in src.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        split = split_map_line(line)
        if split:
            prefix, name = split
            tex = (src.parent / name).resolve()
            textures.append(tex)
            line = f"{prefix} {_rel_or_abs(tex, base)}"
        lines.append(line)
    return "\n".join(lines) + "\n", textures


def rewrite_mtl(src: Path, dst: Path) -> list[Path]:
    """Copy a .mtl to dst, rewriting texture paths relative to dst's folder. Returns resolved textures."""
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    text, textures = rewrite_mtl_text(src, dst.parent)
    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return textures


# -- GLB / generic ----------------------------------------------------------------------------------


def gltf_to_enu(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64)
    return np.stack([v[:, 0], -v[:, 2], v[:, 1]], axis=1)


def read_mesh(path: str | Path, up: str | None = None) -> Mesh:
    """OBJ (own reader) or any trimesh-readable file.

    `up`: 'z' (zone-local as-is) or 'y' (glTF). Default: 'y' for .glb/.gltf, 'z' otherwise.
    """
    path = Path(path)
    ext = path.suffix.lower()
    if up is None:
        up = "y" if ext in (".glb", ".gltf") else "z"
    if ext == ".obj":
        mesh = read_obj(path)
    else:
        import trimesh

        loaded = trimesh.load(path, process=False, force="mesh")
        uv = getattr(loaded.visual, "uv", None)
        f = np.asarray(loaded.faces, dtype=np.int64)
        has_uv = uv is not None and len(uv) == len(loaded.vertices)
        mesh = Mesh(
            v=np.asarray(loaded.vertices, dtype=np.float64),
            f_v=f,
            vt=np.asarray(uv, dtype=np.float64) if has_uv else None,
            f_vt=f.copy() if has_uv else None,
            f_mat=np.zeros(len(f), np.int64),
            materials=[""],
        )
    if up == "y":
        mesh.v = gltf_to_enu(mesh.v)
        if mesh.vn is not None:
            mesh.vn = gltf_to_enu(mesh.vn)
    elif up != "z":
        raise ValueError(f"up must be 'y' or 'z', got {up!r}")
    return mesh


def is_manifold_edges(mesh: Mesh) -> tuple[int, int]:
    """(boundary edges, non-manifold edges) counted on position indices."""
    e = np.sort(mesh.f_v[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    _, counts = np.unique(e, axis=0, return_counts=True)
    return int((counts == 1).sum()), int((counts > 2).sum())


def stats(mesh: Mesh) -> dict:
    lo, hi = mesh.bounds()
    boundary, nonmanifold = is_manifold_edges(mesh) if mesh.n_faces else (0, 0)
    areas = mesh.face_areas() if mesh.n_faces else np.zeros(0)
    nz = mesh.face_normals()[:, 2] if mesh.n_faces else np.zeros(0)
    total = float(areas.sum())
    up = float(areas[nz > math.cos(math.radians(30))].sum() / total) if total > 0 else 0.0
    return {
        "faces": mesh.n_faces,
        "vertices": len(mesh.v),
        "uvs": 0 if mesh.vt is None else len(mesh.vt),
        "normals": 0 if mesh.vn is None else len(mesh.vn),
        "bounds_enu": [lo.tolist(), hi.tolist()],
        "size_m": (hi - lo).tolist(),
        "area_m2": total,
        "up_facing_ratio": up,
        "materials": [m for m in mesh.materials if m != ""] or [],
        "udim_tiles": mesh.udim_tiles(),
        "boundary_edges": boundary,
        "non_manifold_edges": nonmanifold,
        "mtllibs": [str(p) for p in mesh.mtllibs],
    }
