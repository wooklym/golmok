"""3D Gaussian Splatting PLY (as written by the reference 3DGS code, Postshot, gsplat …).

Vertex properties: x y z [nx ny nz] f_dc_0..2 f_rest_0..(3k-1) opacity scale_0..2 rot_0..3, float32,
binary little endian. Stored values are *pre-activation*: opacity is a logit (sigmoid → [0, 1]), scale is
log (exp → meters), rot is an unnormalized quaternion (w, x, y, z). f_rest is channel-major:
R coefficients 1..k, then G, then B, with k = (degree+1)² − 1 (0, 3, 8, 15 for degree 0..3).
Unknown extra properties are kept as-is.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

_PLY_TYPES = {
    "char": "i1", "int8": "i1", "uchar": "u1", "uint8": "u1",
    "short": "i2", "int16": "i2", "ushort": "u2", "uint16": "u2",
    "int": "i4", "int32": "i4", "uint": "u4", "uint32": "u4",
    "float": "f4", "float32": "f4", "double": "f8", "float64": "f8",
}  # fmt: skip
_REV = {
    "i1": "char",
    "u1": "uchar",
    "i2": "short",
    "u2": "ushort",
    "i4": "int",
    "u4": "uint",
    "f4": "float",
    "f8": "double",
}


def sh_rest_count(degree: int) -> int:
    return (degree + 1) ** 2 - 1


def sh_degree(data: np.ndarray) -> int:
    n = sum(1 for name in data.dtype.names if name.startswith("f_rest_"))
    for d in range(4):
        if 3 * sh_rest_count(d) == n:
            return d
    raise ValueError(f"f_rest_* count {n} is not 0, 9, 24 or 45")


def splat_dtype(degree: int = 3, normals: bool = False) -> np.dtype:
    names = ["x", "y", "z"]
    if normals:
        names += ["nx", "ny", "nz"]
    names += [f"f_dc_{i}" for i in range(3)]
    names += [f"f_rest_{i}" for i in range(3 * sh_rest_count(degree))]
    names += ["opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]
    return np.dtype([(n, "<f4") for n in names])


def read_ply(path: str | Path) -> np.ndarray:
    """Vertex element as a numpy structured array (fixed-size elements declared before it are skipped)."""
    with open(path, "rb") as fh:
        if fh.readline().strip() != b"ply":
            raise ValueError(f"{path}: not a PLY file")
        fmt = None
        elements: list[dict] = []  # in header order: name, count, props, has_list
        while True:
            line = fh.readline()
            if not line:
                raise ValueError(f"{path}: truncated header")
            tok = line.decode("ascii", errors="replace").split()
            if not tok or tok[0] in ("comment", "obj_info"):
                continue
            if tok[0] == "format":
                fmt = tok[1]
            elif tok[0] == "element":
                elements.append({"name": tok[1], "count": int(tok[2]), "props": [], "has_list": False})
            elif tok[0] == "property" and elements:
                el = elements[-1]
                if tok[1] == "list":
                    if el["name"] == "vertex":
                        raise ValueError(f"{path}: list properties in vertex element are not supported")
                    el["has_list"] = True
                else:
                    el["props"].append((tok[2], "<" + _PLY_TYPES[tok[1]]))
            elif tok[0] == "end_header":
                break
        if fmt != "binary_little_endian":
            raise ValueError(f"{path}: only binary_little_endian PLY is supported (got {fmt})")
        names = [el["name"] for el in elements]
        if "vertex" not in names:
            raise ValueError(f"{path}: no vertex element")
        skip = 0
        for el in elements[: names.index("vertex")]:
            if el["has_list"]:
                raise ValueError(
                    f"{path}: element {el['name']!r} with list properties before vertex is not supported"
                )
            skip += el["count"] * np.dtype(el["props"]).itemsize
        vertex = elements[names.index("vertex")]
        dtype = np.dtype(vertex["props"])
        count = vertex["count"]
        fh.seek(skip, 1)
        raw = fh.read(dtype.itemsize * count)
        if len(raw) < dtype.itemsize * count:
            raise ValueError(f"{path}: truncated vertex data")
        data = np.frombuffer(raw, dtype=dtype, count=count)
    return data.copy()


def write_ply(data: np.ndarray, path: str | Path, comment: str = "golmok-splat") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.ascontiguousarray(data)
    lines = ["ply", "format binary_little_endian 1.0", f"comment {comment}", f"element vertex {len(data)}"]
    for name in data.dtype.names:
        kind = data.dtype[name].str.lstrip("<>|=")
        lines.append(f"property {_REV[kind]} {name}")
    lines.append("end_header")
    le = data.astype(data.dtype.newbyteorder("<"), copy=False)
    with open(path, "wb") as fh:
        fh.write(("\n".join(lines) + "\n").encode("ascii"))
        fh.write(le.tobytes())
    return path


# -- accessors (activated values) -------------------------------------------------------------------


def positions(d: np.ndarray) -> np.ndarray:
    return np.stack([d["x"], d["y"], d["z"]], axis=1).astype(np.float64)


def opacities(d: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-d["opacity"].astype(np.float64)))


def scales(d: np.ndarray) -> np.ndarray:
    return np.exp(np.stack([d["scale_0"], d["scale_1"], d["scale_2"]], axis=1).astype(np.float64))


def quats_wxyz(d: np.ndarray) -> np.ndarray:
    q = np.stack([d["rot_0"], d["rot_1"], d["rot_2"], d["rot_3"]], axis=1).astype(np.float64)
    n = np.linalg.norm(q, axis=1, keepdims=True)
    return np.divide(q, n, out=np.tile([1.0, 0, 0, 0], (len(q), 1)), where=n > 0)


def sh_dc(d: np.ndarray) -> np.ndarray:
    return np.stack([d["f_dc_0"], d["f_dc_1"], d["f_dc_2"]], axis=1).astype(np.float64)


def sh_rest(d: np.ndarray) -> np.ndarray:
    """(N, k, 3): coefficient index 1..k (degree-major, m from -l to l), RGB last."""
    deg = sh_degree(d)
    k = sh_rest_count(deg)
    if k == 0:
        return np.zeros((len(d), 0, 3))
    flat = np.stack([d[f"f_rest_{i}"] for i in range(3 * k)], axis=1).astype(np.float64)
    return flat.reshape(len(d), 3, k).transpose(0, 2, 1)


def set_sh_rest(d: np.ndarray, rest: np.ndarray) -> None:
    k = rest.shape[1]
    flat = rest.transpose(0, 2, 1).reshape(len(d), 3 * k)
    for i in range(3 * k):
        d[f"f_rest_{i}"] = flat[:, i]


def random_splats(n: int, degree: int = 3, extent=(20.0, 10.0, 5.0), seed: int = 0) -> np.ndarray:
    """Synthetic splats for tests: uniform in [0, extent], plausible scales/opacity/colors."""
    rng = np.random.default_rng(seed)
    d = np.zeros(n, dtype=splat_dtype(degree))
    p = rng.uniform(0, 1, (n, 3)) * np.asarray(extent)
    d["x"], d["y"], d["z"] = p.T
    for i in range(3):
        d[f"f_dc_{i}"] = rng.normal(0, 0.8, n)
        d[f"scale_{i}"] = np.log(rng.uniform(0.005, 0.08, n))
    for i in range(3 * sh_rest_count(degree)):
        d[f"f_rest_{i}"] = rng.normal(0, 0.05, n)
    d["opacity"] = rng.normal(1.0, 1.5, n)
    q = rng.normal(0, 1, (n, 4))
    for i in range(4):
        d[f"rot_{i}"] = q[:, i]
    return d
