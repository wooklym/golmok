"""Synthetic 'alley' mesh for the golmok-mesh tests: sloped ground + UV-mapped boxes + floating junk."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from golmok_tools.mesh.objio import Mesh, write_obj

SLOPE = 0.03  # ground rises 3 cm per m toward +x


def ground(x0, x1, y0, y1, step=1.0, noise=0.0, rng=None):
    xs = np.arange(x0, x1 + 1e-9, step)
    ys = np.arange(y0, y1 + 1e-9, step)
    gx, gy = np.meshgrid(xs, ys, indexing="ij")
    z = SLOPE * gx
    if noise:
        z = z + (rng or np.random.default_rng(0)).normal(0, noise, z.shape)
    v = np.stack([gx, gy, z], axis=-1).reshape(-1, 3)
    nx, ny = len(xs), len(ys)
    f = []
    for i in range(nx - 1):
        for j in range(ny - 1):
            a, b, c, d = i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1
            f += [[a, b, c], [a, c, d]]
    uv = np.stack([(gx - x0) / (x1 - x0), (gy - y0) / (y1 - y0)], axis=-1).reshape(-1, 2)
    return v, np.asarray(f), uv


def box(center, size, udim_tile=1001):
    c, s = np.asarray(center, float), np.asarray(size, float) / 2
    v = np.array([[x, y, z] for z in (-1, 1) for y in (-1, 1) for x in (-1, 1)], float) * s + c
    f = np.array(
        [[0, 2, 1], [1, 2, 3], [4, 5, 6], [5, 7, 6], [0, 1, 4], [1, 5, 4],
         [2, 6, 3], [3, 6, 7], [0, 4, 2], [2, 4, 6], [1, 3, 5], [3, 7, 5]]
    )  # fmt: skip
    t = udim_tile - 1001
    u0, v0 = t % 10, t // 10
    uv = np.column_stack([u0 + 0.1 + 0.8 * (v[:, 0] - v[:, 0].min()) / (np.ptp(v[:, 0]) or 1),
                          v0 + 0.1 + 0.8 * (v[:, 2] - v[:, 2].min()) / (np.ptp(v[:, 2]) or 1)])  # fmt: skip
    return v, f, uv


def synthetic_alley(noise=0.0) -> Mesh:
    parts = [(ground(0, 60, -5, 5, noise=noise), 0)]
    for k, x in enumerate(range(5, 60, 12)):  # buildings on both sides, UDIM tiles 1001/1002
        tile = 1001 + (k % 2)
        parts.append((box((x, 7, 4 + SLOPE * x), (8, 4, 8), tile), 1))
        parts.append((box((x + 6, -7, 3 + SLOPE * x), (6, 4, 6), tile), 1))
    parts.append((box((30, 0, 12), (0.3, 0.3, 0.3)), 1))  # floating junk (0.54 m²)
    vs, fs, uvs, mats, off = [], [], [], [], 0
    for (v, f, uv), mat in parts:
        vs.append(v)
        uvs.append(uv)
        fs.append(f + off)
        mats.append(np.full(len(f), mat))
        off += len(v)
    v, f = np.vstack(vs), np.vstack(fs)
    return Mesh(
        v=v,
        f_v=f,
        vt=np.vstack(uvs),
        f_vt=f.copy(),
        f_mat=np.concatenate(mats),
        materials=["ground", "facade"],
    )


def write_synthetic_obj(folder: Path, noise=0.0) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "tex").mkdir(exist_ok=True)
    for name in ("ground.1001.png", "facade.1001.png", "facade.1002.png"):
        (folder / "tex" / name).write_bytes(b"\x89PNG fake")
    (folder / "alley.mtl").write_text(
        "newmtl ground\nKd 1 1 1\nmap_Kd tex/ground.<UDIM>.png\n\n"
        "newmtl facade\nKd 1 1 1\nmap_Kd -bm 1 tex/facade.<UDIM>.png\n",
        encoding="utf-8",
    )
    return write_obj(synthetic_alley(noise), folder / "alley.obj", mtllib="alley.mtl")
