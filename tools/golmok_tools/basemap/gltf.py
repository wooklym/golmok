"""Minimal binary glTF (GLB) writer for basemap tiles.

Input positions are in the ENU frame (x=east, y=north, z=up, meters). glTF is Y-up, so vertices
are written as (east, up, -north); 3D Tiles and Unreal's glTF importer both undo that rotation.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field

import numpy as np

FLOAT, UINT8, UINT32 = 5126, 5121, 5125
ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963


def enu_to_gltf(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64)
    return np.stack([v[:, 0], v[:, 2], -v[:, 1]], axis=1)


@dataclass
class MeshData:
    positions: np.ndarray  # (N, 3) ENU
    indices: np.ndarray  # (M,) uint32, counter-clockwise when seen from outside
    normals: np.ndarray | None = None  # (N, 3) ENU
    uv0: np.ndarray | None = None  # (N, 2)
    uv1: np.ndarray | None = None  # (N, 2)
    colors: np.ndarray | None = None  # (N, 4) uint8
    feature_ids: np.ndarray | None = None  # (N,) float (EXT_mesh_features requires float/int)
    texture_jpeg: bytes | None = None  # base color texture sampled with uv0
    name: str = "mesh"
    extras: dict = field(default_factory=dict)


class _Buffer:
    def __init__(self):
        self.data = bytearray()
        self.views: list[dict] = []
        self.accessors: list[dict] = []

    def _align(self):
        while len(self.data) % 4:
            self.data.append(0)

    def add_view(self, raw: bytes, target: int | None = None) -> int:
        self._align()
        view = {"buffer": 0, "byteOffset": len(self.data), "byteLength": len(raw)}
        if target:
            view["target"] = target
        self.data.extend(raw)
        self.views.append(view)
        return len(self.views) - 1

    def add_accessor(
        self,
        arr: np.ndarray,
        comp: int,
        typ: str,
        target: int | None,
        normalized: bool = False,
        minmax: bool = False,
    ) -> int:
        view = self.add_view(arr.tobytes(), target)
        acc = {"bufferView": view, "componentType": comp, "count": int(arr.shape[0]), "type": typ}
        if normalized:
            acc["normalized"] = True
        if minmax:
            acc["min"] = arr.min(axis=0).tolist()
            acc["max"] = arr.max(axis=0).tolist()
        self.accessors.append(acc)
        return len(self.accessors) - 1


def write_glb(path, meshes: list[MeshData], metadata: dict | None = None) -> None:
    """Write meshes as one GLB (one node per mesh). `metadata` goes to asset.extras.

    Keep metadata values strings: the UE glTF importer reads asset.extras as string metadata and
    logs a LogJson error for nested objects.
    """
    buf = _Buffer()
    gltf: dict = {
        "asset": {"version": "2.0", "generator": "golmok-basemap"},
        "scenes": [{"nodes": []}],
        "scene": 0,
        "nodes": [],
        "meshes": [],
        "materials": [],
    }
    if metadata:
        gltf["asset"]["extras"] = metadata
    images, textures, samplers = [], [], []
    uses_features = False

    for mesh in meshes:
        if len(mesh.indices) == 0:
            continue
        attrs = {}
        pos = enu_to_gltf(mesh.positions).astype(np.float32)
        attrs["POSITION"] = buf.add_accessor(pos, FLOAT, "VEC3", ARRAY_BUFFER, minmax=True)
        if mesh.normals is not None:
            nrm = enu_to_gltf(mesh.normals).astype(np.float32)
            attrs["NORMAL"] = buf.add_accessor(nrm, FLOAT, "VEC3", ARRAY_BUFFER)
        if mesh.uv0 is not None:
            attrs["TEXCOORD_0"] = buf.add_accessor(
                np.asarray(mesh.uv0, np.float32), FLOAT, "VEC2", ARRAY_BUFFER
            )
        if mesh.uv1 is not None:
            attrs["TEXCOORD_1"] = buf.add_accessor(
                np.asarray(mesh.uv1, np.float32), FLOAT, "VEC2", ARRAY_BUFFER
            )
        if mesh.colors is not None:
            attrs["COLOR_0"] = buf.add_accessor(
                np.asarray(mesh.colors, np.uint8), UINT8, "VEC4", ARRAY_BUFFER, normalized=True
            )
        primitive: dict = {"attributes": attrs, "mode": 4}
        if mesh.feature_ids is not None:
            attrs["_FEATURE_ID_0"] = buf.add_accessor(
                np.asarray(mesh.feature_ids, np.float32), FLOAT, "SCALAR", ARRAY_BUFFER
            )
            n_features = int(np.max(mesh.feature_ids)) + 1 if len(mesh.feature_ids) else 0
            primitive["extensions"] = {
                "EXT_mesh_features": {"featureIds": [{"featureCount": n_features, "attribute": 0}]}
            }
            uses_features = True
        primitive["indices"] = buf.add_accessor(
            np.asarray(mesh.indices, np.uint32), UINT32, "SCALAR", ELEMENT_ARRAY_BUFFER
        )

        material = {
            "name": f"{mesh.name}_mat",
            "pbrMetallicRoughness": {"metallicFactor": 0.0, "roughnessFactor": 0.9},
        }
        if mesh.texture_jpeg:
            img_view = buf.add_view(mesh.texture_jpeg)
            images.append({"bufferView": img_view, "mimeType": "image/jpeg"})
            if not samplers:
                samplers.append({"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071})
            textures.append({"source": len(images) - 1, "sampler": 0})
            material["pbrMetallicRoughness"]["baseColorTexture"] = {"index": len(textures) - 1, "texCoord": 0}
        gltf["materials"].append(material)
        primitive["material"] = len(gltf["materials"]) - 1

        gltf["meshes"].append(
            {"name": mesh.name, "primitives": [primitive], **({"extras": mesh.extras} if mesh.extras else {})}
        )
        gltf["nodes"].append({"name": mesh.name, "mesh": len(gltf["meshes"]) - 1})
        gltf["scenes"][0]["nodes"].append(len(gltf["nodes"]) - 1)

    if images:
        gltf["images"], gltf["textures"], gltf["samplers"] = images, textures, samplers
    if uses_features:
        gltf["extensionsUsed"] = ["EXT_mesh_features"]
    buf._align()
    gltf["buffers"] = [{"byteLength": len(buf.data)}]
    gltf["bufferViews"] = buf.views
    gltf["accessors"] = buf.accessors

    json_bytes = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    bin_bytes = bytes(buf.data)
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<I4s", len(json_bytes), b"JSON"))
        f.write(json_bytes)
        f.write(struct.pack("<I4s", len(bin_bytes), b"BIN\x00"))
        f.write(bin_bytes)
