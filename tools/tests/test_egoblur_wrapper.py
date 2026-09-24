"""Checks EgoBlurDetector against a dummy TorchScript model with the EgoBlur Gen1 output signature."""

from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torchvision")

from golmok_tools.privacy.detector import EgoBlurDetector  # noqa: E402


class DummyModel(torch.nn.Module):
    def forward(self, image: torch.Tensor):
        # image: uint8 CHW (BGR). Return (boxes, labels, scores, dims) like EgoBlur Gen1.
        _, h, w = image.shape
        boxes = torch.tensor([[0.0, 0.0, 10.0, 10.0],
                              [1.0, 1.0, 10.0, 10.0],   # overlaps first -> removed by NMS
                              [20.0, 20.0, 30.0, 30.0]])  # low score -> filtered
        scores = torch.tensor([0.95, 0.93, 0.5])
        labels = torch.zeros(3, dtype=torch.int64)
        dims = torch.tensor([h, w])
        return boxes, labels, scores, dims


def test_wrapper_applies_nms_and_threshold(tmp_path: Path):
    path = tmp_path / "dummy.jit"
    torch.jit.script(DummyModel()).save(str(path))
    det = EgoBlurDetector("face", path, score_threshold=0.9, nms_iou_threshold=0.3, device="cpu")
    boxes = det(np.zeros((40, 50, 3), np.uint8))
    assert boxes == [(0.0, 0.0, 10.0, 10.0)]
