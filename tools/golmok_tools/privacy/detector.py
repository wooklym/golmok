"""EgoBlur Gen1 TorchScript detector wrapper (Apache-2.0, Meta).

Mirrors the reference demo (github.com/facebookresearch/EgoBlur, gen1/script/demo_ego_blur_gen1.py):
input is a BGR uint8 CHW tensor, the model returns (boxes, labels, scores, dims), then NMS and a
score threshold are applied. Model files (ego_blur_face.jit, ego_blur_lp.jit) are downloaded
separately from https://www.projectaria.com/tools/egoblur after accepting the model license.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

Box = tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels


class Detector(Protocol):
    name: str

    def __call__(self, bgr_u8: np.ndarray) -> list[Box]: ...


def resolve_device(device: str) -> str:
    import torch

    if device != "auto":
        return device
    return f"cuda:{torch.cuda.current_device()}" if torch.cuda.is_available() else "cpu"


class EgoBlurDetector:
    def __init__(
        self,
        name: str,
        model_path: Path,
        score_threshold: float = 0.9,
        nms_iou_threshold: float = 0.3,
        device: str = "auto",
    ):
        import torch

        self.name = name
        self.score_threshold = score_threshold
        self.nms_iou_threshold = nms_iou_threshold
        self.device = resolve_device(device)
        self.model = torch.jit.load(str(model_path), map_location="cpu").to(self.device)
        self.model.eval()

    def __call__(self, bgr_u8: np.ndarray) -> list[Box]:
        import torch
        import torchvision

        tensor = torch.from_numpy(np.ascontiguousarray(np.transpose(bgr_u8, (2, 0, 1)))).to(self.device)
        with torch.no_grad():
            boxes, _, scores, _ = self.model(tensor)
        keep = torchvision.ops.nms(boxes, scores, self.nms_iou_threshold)
        boxes = boxes[keep].cpu().numpy()
        scores = scores[keep].cpu().numpy()
        boxes = boxes[scores > self.score_threshold]
        return [tuple(map(float, b)) for b in boxes]


def detect_scaled(detector: Detector, bgr_u8: np.ndarray, max_side: int) -> list[Box]:
    """Run detection on a downscaled copy (long side <= max_side) and map boxes back. 0 = full res."""
    h, w = bgr_u8.shape[:2]
    scale = 1.0
    if max_side and max(h, w) > max_side:
        scale = max_side / max(h, w)
        bgr_u8 = cv2.resize(bgr_u8, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    boxes = detector(bgr_u8)
    if scale == 1.0:
        return boxes
    return [(x1 / scale, y1 / scale, x2 / scale, y2 / scale) for x1, y1, x2, y2 in boxes]
