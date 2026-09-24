"""Image read/write helpers that keep bit depth and work with non-ASCII (Korean) paths on Windows.

cv2.imread/imwrite fail on non-ASCII paths on Windows, so bytes go through numpy + imdecode/imencode.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .dng import is_jpeg_xl

RASTER_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
RAW_EXTS = {".dng"}
HEIC_EXTS = {".heic", ".heif"}
SUPPORTED_EXTS = RASTER_EXTS | RAW_EXTS | HEIC_EXTS


class DecodeError(RuntimeError):
    pass


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTS


def output_suffix(path: Path) -> str:
    """Suffix used for the processed copy. RAW/HEIC become lossless TIFF; others keep their format."""
    ext = path.suffix.lower()
    if ext in RAW_EXTS or ext in HEIC_EXTS:
        return ".tif"
    return path.suffix


def decoder_applies_orientation(path: Path) -> bool:
    """True when read_image() already rotated pixels per EXIF orientation.

    Output Orientation must then be 1.
    """
    return path.suffix.lower() in RAW_EXTS | HEIC_EXTS


def read_image(path: Path) -> np.ndarray:
    """Read an image as BGR (uint8 or uint16). RAW is developed to 16-bit."""
    ext = path.suffix.lower()
    if ext in RAW_EXTS:
        return _read_raw(path)
    if ext in HEIC_EXTS:
        return _read_heic(path)

    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise DecodeError(f"cannot decode {path}")
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


def write_image(img: np.ndarray, path: Path, jpeg_quality: int = 97) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()
    params: list[int] = []
    if ext in {".jpg", ".jpeg"}:
        if img.dtype != np.uint8:
            img = to_uint8(img)
        params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
    elif ext in {".tif", ".tiff"}:
        # 1 = no compression; 5 = LZW (lossless, smaller). RealityScan/Postshot read LZW TIFF.
        params = [cv2.IMWRITE_TIFF_COMPRESSION, 5]
    ok, buf = cv2.imencode(ext, img, params)
    if not ok:
        raise RuntimeError(f"cannot encode {path}")
    buf.tofile(str(path))


def to_uint8(img: np.ndarray) -> np.ndarray:
    if img.dtype == np.uint8:
        return img
    if img.dtype == np.uint16:
        return (img // 257).astype(np.uint8)
    raise TypeError(f"unsupported dtype {img.dtype}")


def _read_raw(path: Path) -> np.ndarray:
    try:
        import rawpy
    except ImportError as e:  # pragma: no cover - optional dependency
        raise DecodeError("DNG needs rawpy: pip install -e .[raw]") from e
    try:
        with rawpy.imread(str(path)) as raw:
            # Camera white balance, no auto brightening, 16-bit output. rawpy applies the RAW flip.
            rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=True, output_bps=16)
        if not rgb.any():
            raise ValueError("developed image is all black")
    except Exception as e:  # LibRaw may not support every Apple ProRAW variant
        if is_jpeg_xl(path):
            raise DecodeError(
                f"cannot develop DNG {path}: JPEG-XL ProRAW (DNG 1.7) needs LibRaw built with the Adobe DNG SDK, "
                f"which rawpy is not; shoot ProRAW format 'JPEG Lossless' (LibRaw: {e})") from e
        raise DecodeError(f"cannot develop DNG {path}: {e}") from e
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _read_heic(path: Path) -> np.ndarray:
    try:
        import pillow_heif
        from PIL import Image, ImageOps
    except ImportError as e:  # pragma: no cover - optional dependency
        raise DecodeError("HEIC needs pillow-heif: pip install -e .[heic]") from e
    pillow_heif.register_heif_opener()
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        rgb = np.asarray(im)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
