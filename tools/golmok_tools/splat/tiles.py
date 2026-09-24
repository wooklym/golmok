"""3DGS PLY -> 3D Tiles 1.1 with glTF KHR_gaussian_splatting content (local; nothing is uploaded, D-007).

glTF attributes follow the ratified extension README
(https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_gaussian_splatting/README.md):
    POSITION                                   VEC3 float
    KHR_gaussian_splatting:ROTATION            VEC4 float, unit quaternion in glTF order (x, y, z, w)
    KHR_gaussian_splatting:SCALE               VEC3 float, linear (exp of the PLY value)
    KHR_gaussian_splatting:OPACITY             SCALAR float, linear [0, 1] (sigmoid of the PLY value)
    KHR_gaussian_splatting:SH_DEGREE_0_COEF_0  VEC3 float (PLY f_dc, no bias/constant applied)
    KHR_gaussian_splatting:SH_DEGREE_l_COEF_n  VEC3 float, n = 0..2l in m order -l..l
    COLOR_0                                    VEC4 float, linear fallback color (optional in the spec)
primitive mode POINTS (0), extension object {"kernel": "ellipse", "colorSpace": ...}.

Axes: the tileset is Z-up zone-local ENU (root.transform = zone -> ECEF when a manifest is given); glTF
content is Y-up, so positions, rotations and SH are rotated by (x, y, z) -> (x, z, -y) like golmok-basemap.

LOD: an octree splits until a node holds ≤ max_splats; inner nodes carry a subsample (probability ∝
opacity × area) of their subtree for distant viewing (refine REPLACE). Kept splats are enlarged by
(n/k)^lod_scale_exp (capped at 3) so the sparse parent still covers the surface — a heuristic to tune
in the spike, 0 disables it.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import ops, ply

EXT = "KHR_gaussian_splatting"
ENU_TO_GLTF = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])  # (x, y, z) -> (x, z, -y)


@dataclass
class Node:
    address: str
    idx: np.ndarray  # splats in this node's content
    lo: np.ndarray
    hi: np.ndarray
    geometric_error: float = 0.0
    children: list[Node] = field(default_factory=list)
    content_count: int = 0


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _gltf_splats(d: np.ndarray) -> np.ndarray:
    m = np.eye(4)
    m[:3, :3] = ENU_TO_GLTF
    return ops.transform(d, m)


def write_splat_glb(d: np.ndarray, path: str | Path, color_space: str = "srgb_rec709_display") -> Path:
    """One POINTS primitive with KHR_gaussian_splatting attributes. `d` is in ENU (Z-up); written Y-up."""
    from golmok_tools.basemap.gltf import ARRAY_BUFFER, FLOAT, _Buffer

    g = _gltf_splats(d)
    buf = _Buffer()
    attrs = {}
    attrs["POSITION"] = buf.add_accessor(
        ply.positions(g).astype(np.float32), FLOAT, "VEC3", ARRAY_BUFFER, minmax=True
    )
    q = ply.quats_wxyz(g)[:, [1, 2, 3, 0]]  # wxyz -> glTF xyzw
    attrs[f"{EXT}:ROTATION"] = buf.add_accessor(q.astype(np.float32), FLOAT, "VEC4", ARRAY_BUFFER)
    attrs[f"{EXT}:SCALE"] = buf.add_accessor(ply.scales(g).astype(np.float32), FLOAT, "VEC3", ARRAY_BUFFER)
    attrs[f"{EXT}:OPACITY"] = buf.add_accessor(
        ply.opacities(g).astype(np.float32), FLOAT, "SCALAR", ARRAY_BUFFER
    )
    dc = ply.sh_dc(g)
    attrs[f"{EXT}:SH_DEGREE_0_COEF_0"] = buf.add_accessor(dc.astype(np.float32), FLOAT, "VEC3", ARRAY_BUFFER)
    rest = ply.sh_rest(g)
    i = 0
    for degree in range(1, ply.sh_degree(g) + 1):
        for n in range(2 * degree + 1):
            attrs[f"{EXT}:SH_DEGREE_{degree}_COEF_{n}"] = buf.add_accessor(
                np.ascontiguousarray(rest[:, i, :]).astype(np.float32), FLOAT, "VEC3", ARRAY_BUFFER
            )
            i += 1
    rgb = dc * ops.C0 + 0.5
    if color_space.startswith("srgb"):
        rgb = srgb_to_linear(rgb)
    rgba = np.column_stack([np.clip(rgb, 0, 1), ply.opacities(g)]).astype(np.float32)
    attrs["COLOR_0"] = buf.add_accessor(rgba, FLOAT, "VEC4", ARRAY_BUFFER)

    gltf = {
        "asset": {"version": "2.0", "generator": "golmok-splat"},
        "extensionsUsed": [EXT],
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": attrs,
                        "mode": 0,
                        "extensions": {EXT: {"kernel": "ellipse", "colorSpace": color_space}},
                    }
                ]
            }
        ],
    }
    return _write_glb(gltf, buf, path)


def _write_glb(gltf: dict, buf, path) -> Path:
    import struct

    buf._align()
    gltf["buffers"] = [{"byteLength": len(buf.data)}]
    gltf["bufferViews"] = buf.views
    gltf["accessors"] = buf.accessors
    js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    bin_bytes = bytes(buf.data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(bin_bytes)))
        fh.write(struct.pack("<I4s", len(js), b"JSON"))
        fh.write(js)
        fh.write(struct.pack("<I4s", len(bin_bytes), b"BIN\x00"))
        fh.write(bin_bytes)
    return path


def _extent_bounds(p: np.ndarray, radius: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return (p - radius[:, None]).min(axis=0), (p + radius[:, None]).max(axis=0)


def build_octree(
    d: np.ndarray, max_splats: int = 500_000, max_depth: int = 10, seed: int = 0
) -> tuple[Node, np.ndarray]:
    """Octree over splat centers. Returns (root, per-splat LOD scale factor array for inner nodes)."""
    rng = np.random.default_rng(seed)
    p = ply.positions(d)
    radius = 3.0 * ply.scales(d).max(axis=1)  # 3σ cut-off of the ellipse kernel
    weight = ply.opacities(d) * np.prod(np.sort(ply.scales(d), axis=1)[:, 1:], axis=1)  # opacity × area

    def make(address, idx, lo, hi, depth):
        blo, bhi = _extent_bounds(p[idx], radius[idx])
        node = Node(address=address, idx=idx, lo=blo, hi=bhi)
        if len(idx) <= max_splats or depth >= max_depth:
            node.content_count = len(idx)
            return node
        mid = (lo + hi) / 2
        octant = (
            (p[idx, 0] >= mid[0]).astype(int)
            + 2 * (p[idx, 1] >= mid[1]).astype(int)
            + 4 * (p[idx, 2] >= mid[2]).astype(int)
        )
        for o in range(8):
            sub = idx[octant == o]
            if not len(sub):
                continue
            clo = np.where([o & 1, o & 2, o & 4], mid, lo)
            chi = np.where([o & 1, o & 2, o & 4], hi, mid)
            node.children.append(make(address + str(o), sub, clo, chi, depth + 1))
        w = weight[idx] + 1e-12
        node.idx = rng.choice(idx, size=max_splats, replace=False, p=w / w.sum())
        node.content_count = len(node.idx)
        return node

    idx = np.arange(len(d))
    lo, hi = p.min(axis=0), p.max(axis=0)
    side = float((hi - lo).max()) or 1.0
    root = make("r", idx, lo, lo + side, 0)  # cubic cells
    _assign_errors(root)
    return root, radius


def _subtree_count(node: Node) -> int:
    return node.content_count if not node.children else sum(_subtree_count(c) for c in node.children)


def _assign_errors(node: Node) -> float:
    """Leaves 0; inner nodes ~ mean spacing of their subsample, and always > children's."""
    if not node.children:
        node.geometric_error = 0.0
        return 0.0
    child_max = max(_assign_errors(c) for c in node.children)
    size = np.maximum(node.hi - node.lo, 0.01)
    vol = float(np.prod(size))
    spacing = (vol / max(node.content_count, 1)) ** (1 / 3)
    node.geometric_error = max(spacing, 2 * child_max, 0.01)
    return node.geometric_error


def _box(lo, hi) -> list[float]:
    c = (lo + hi) / 2
    h = (hi - lo) / 2
    return [*c.tolist(), float(h[0]), 0.0, 0.0, 0.0, float(h[1]), 0.0, 0.0, 0.0, float(h[2])]


def write_tileset(
    d: np.ndarray,
    out_dir: str | Path,
    max_splats: int = 500_000,
    root_transform: np.ndarray | None = None,
    lod_scale_exp: float = 0.5,
    color_space: str = "srgb_rec709_display",
    seed: int = 0,
) -> dict:
    """Write tileset.json + tiles/<address>.glb. root_transform: 4x4 zone-local -> ECEF (matrix form)."""
    out = Path(out_dir)
    (out / "tiles").mkdir(parents=True, exist_ok=True)
    root, _ = build_octree(d, max_splats=max_splats, seed=seed)
    n_files = 0

    def emit(node: Node) -> dict:
        nonlocal n_files
        content = d[node.idx]
        if node.children and lod_scale_exp:
            total = _subtree_count(node)
            factor = min(3.0, (total / max(len(node.idx), 1)) ** lod_scale_exp)
            content = content.copy()
            for i in range(3):
                content[f"scale_{i}"] = content[f"scale_{i}"] + math.log(factor)
        uri = f"tiles/{node.address}.glb"
        write_splat_glb(content, out / uri, color_space=color_space)
        n_files += 1
        tile = {
            "boundingVolume": {"box": _box(node.lo, node.hi)},
            "geometricError": node.geometric_error,
            "refine": "REPLACE",
            "content": {"uri": uri},
        }
        if node.children:
            tile["children"] = [emit(c) for c in node.children]
        return tile

    root_tile = emit(root)
    if root_transform is not None:
        root_tile["transform"] = (
            np.asarray(root_transform, dtype=np.float64).T.reshape(16).tolist()
        )  # column-major
    diag = float(np.linalg.norm(root.hi - root.lo))
    tileset = {
        "asset": {"version": "1.1", "generator": "golmok-splat"},
        "geometricError": max(diag, root.geometric_error * 2),
        "root": root_tile,
    }
    with open(out / "tileset.json", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(tileset, indent=2) + "\n")
    return {
        "tiles": n_files,
        "splats": int(len(d)),
        "depth": _depth(root),
        "tileset": str(out / "tileset.json"),
    }


def _depth(node: Node) -> int:
    return 1 + max((_depth(c) for c in node.children), default=0)
