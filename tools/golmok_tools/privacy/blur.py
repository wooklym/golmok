"""Blur faces and license plates in a capture folder before any reconstruction (docs/research/05).

Every image under INPUT is processed and written under OUTPUT with the same relative path.
RAW (DNG) and HEIC are written as 16/8-bit LZW TIFF. Reconstruction (RealityScan / Postshot)
must only ever read OUTPUT.

Outputs in OUTPUT/_golmok/:
    blur_log.csv     per image: detections, output path, status
    gps_priors.csv   name, lat, lon, alt from source EXIF (RealityScan GPS import)
    preview/         small JPEGs of blurred output with detections outlined (for spot checks)

Usage:
    golmok-blur photos\\ photos_blurred\\ --face-model models\\ego_blur_face.jit --lp-model models\\ego_blur_lp.jit
"""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from ..exif import read_exif
from ..imageio import (
    DecodeError,
    decoder_applies_orientation,
    is_supported,
    output_suffix,
    read_image,
    to_uint8,
    write_image,
)
from .detector import Box, Detector, EgoBlurDetector, detect_scaled

META_DIR = "_golmok"


def scale_box(box: Box, width: int, height: int, scale: float) -> Box:
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    w, h = (x2 - x1) * scale, (y2 - y1) * scale
    return (
        max(cx - w / 2, 0.0),
        max(cy - h / 2, 0.0),
        min(cx + w / 2, float(width)),
        min(cy + h / 2, float(height)),
    )


def blur_regions(img: np.ndarray, boxes: list[Box], scale: float = 1.15) -> np.ndarray:
    """Replace an ellipse inside each (scaled) box with a heavy box blur. Keeps dtype (uint8/uint16)."""
    if not boxes:
        return img
    h, w = img.shape[:2]
    out = img.copy()
    for box in boxes:
        x1, y1, x2, y2 = (int(round(v)) for v in scale_box(box, w, h, scale))
        bw, bh = x2 - x1, y2 - y1
        if bw < 2 or bh < 2:
            continue
        crop = img[y1:y2, x1:x2]
        blurred = cv2.blur(crop, (max(3, bw), max(3, bh)))
        blurred = cv2.blur(blurred, (max(3, bw // 2), max(3, bh // 2)))
        mask = np.zeros((bh, bw), dtype=np.uint8)
        cv2.ellipse(mask, ((bw / 2, bh / 2), (bw, bh), 0), 255, -1)
        region = out[y1:y2, x1:x2]
        region[mask > 0] = blurred[mask > 0]
    return out


@dataclass
class Result:
    src: Path
    dst: Path | None
    faces: int = 0
    plates: int = 0
    status: str = "ok"
    error: str = ""


def process_image(
    src: Path,
    dst: Path,
    detectors: list[Detector],
    max_side: int,
    scale: float,
    preview_path: Path | None = None,
) -> Result:
    img = read_image(src)
    det_input = to_uint8(img)
    counts: dict[str, int] = {}
    all_boxes: list[Box] = []
    for det in detectors:
        boxes = detect_scaled(det, det_input, max_side)
        counts[det.name] = len(boxes)
        all_boxes.extend(boxes)
    out = blur_regions(img, all_boxes, scale)
    write_image(out, dst)
    if preview_path is not None:
        write_preview(out, all_boxes, scale, preview_path)
    return Result(src, dst, faces=counts.get("face", 0), plates=counts.get("plate", 0))


def write_preview(img: np.ndarray, boxes: list[Box], scale: float, path: Path, long_side: int = 1600) -> None:
    small = to_uint8(img)
    h, w = small.shape[:2]
    k = min(1.0, long_side / max(h, w))
    small = cv2.resize(small, (round(w * k), round(h * k)), interpolation=cv2.INTER_AREA)
    for b in boxes:
        x1, y1, x2, y2 = (int(v * k) for v in scale_box(b, w, h, scale))
        cv2.rectangle(small, (x1, y1), (x2, y2), (0, 0, 255), 2)
    write_image(small, path, jpeg_quality=85)


def copy_metadata(src: Path, dst: Path) -> bool:
    """Copy EXIF/XMP (incl. GPS) with exiftool when available. Returns False if exiftool is missing."""
    exiftool = shutil.which("exiftool")
    if not exiftool:
        return False
    cmd = [exiftool, "-q", "-q", "-overwrite_original", "-TagsFromFile", str(src), "-all:all", "-unsafe"]
    if decoder_applies_orientation(src):
        cmd.append("-Orientation=1")
    cmd.append(str(dst))
    subprocess.run(cmd, check=False)
    return True


def iter_images(root: Path, skip: Path | None = None):
    for p in sorted(root.rglob("*")):
        if skip is not None and skip in p.parents:
            continue
        if p.is_file() and is_supported(p):
            yield p


def run(
    input_dir: Path,
    output_dir: Path,
    detectors: list[Detector],
    max_side: int = 4032,
    scale: float = 1.15,
    preview: bool = True,
    overwrite: bool = False,
) -> list[Result]:
    meta = output_dir / META_DIR
    meta.mkdir(parents=True, exist_ok=True)
    preview_dir = meta / "preview" if preview else None
    have_exiftool = shutil.which("exiftool") is not None
    skip = output_dir.resolve() if output_dir.resolve().is_relative_to(input_dir.resolve()) else None

    results: list[Result] = []
    gps_rows = []
    images = list(iter_images(input_dir, skip))
    t0 = time.time()
    for n, src in enumerate(images, 1):
        rel = src.relative_to(input_dir)
        dst = (output_dir / rel).with_suffix(output_suffix(src))
        if dst.exists() and not overwrite:
            results.append(Result(src, dst, status="skipped"))
            continue
        try:
            preview_path = None
            if preview_dir is not None:
                preview_path = preview_dir / ("__".join(rel.with_suffix("").parts) + ".jpg")
            res = process_image(src, dst, detectors, max_side, scale, preview_path)
            if have_exiftool:
                copy_metadata(src, dst)
        except DecodeError as e:
            res = Result(src, None, status="decode_error", error=str(e))
        except Exception as e:  # keep going; failures are listed in the log
            res = Result(src, None, status="error", error=repr(e))
        results.append(res)
        try:
            ex = read_exif(src)
            if ex.lat is not None and ex.lon is not None and res.dst is not None:
                gps_rows.append({"name": res.dst.name, "lat": ex.lat, "lon": ex.lon, "alt": ex.alt})
        except Exception:
            pass
        rate = n / max(time.time() - t0, 1e-6)
        print(
            f"[{n}/{len(images)}] {rel}  얼굴 {res.faces} 번호판 {res.plates}  {res.status}  ({rate:.2f}장/s)"
        )

    with open(meta / "blur_log.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["source", "output", "faces", "plates", "status", "error"])
        for r in results:
            w.writerow([r.src, r.dst or "", r.faces, r.plates, r.status, r.error])
    with open(meta / "gps_priors.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "lat", "lon", "alt"])
        w.writeheader()
        w.writerows(gps_rows)
    if not have_exiftool:
        print(
            "참고: exiftool이 없어 출력 파일에 EXIF를 복사하지 않았다. GPS는 _golmok/gps_priors.csv를 쓴다."
        )
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="얼굴·번호판 블러 (EgoBlur Gen1). 재구성 전에 반드시 실행")
    ap.add_argument("input_dir", type=Path)
    ap.add_argument("output_dir", type=Path)
    ap.add_argument("--face-model", type=Path, required=True, help="ego_blur_face.jit")
    ap.add_argument("--lp-model", type=Path, required=True, help="ego_blur_lp.jit")
    ap.add_argument("--face-threshold", type=float, default=0.9)
    ap.add_argument("--lp-threshold", type=float, default=0.9)
    ap.add_argument("--nms-iou", type=float, default=0.3)
    ap.add_argument("--scale", type=float, default=1.15, help="검출 박스 확대 비율 (기본 1.15)")
    ap.add_argument(
        "--detect-max-side",
        type=int,
        default=4032,
        help="검출용 축소 긴 변 픽셀 (0=원본). 블러는 항상 원본 해상도에 적용",
    )
    ap.add_argument("--device", default="auto", help="auto | cpu | cuda:0")
    ap.add_argument("--no-preview", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args(argv)

    if not args.input_dir.is_dir():
        ap.error(f"폴더가 아님: {args.input_dir}")
    if args.output_dir.resolve() == args.input_dir.resolve():
        ap.error("출력 폴더는 입력 폴더와 달라야 한다(원본 보존)")

    detectors: list[Detector] = [
        EgoBlurDetector("face", args.face_model, args.face_threshold, args.nms_iou, args.device),
        EgoBlurDetector("plate", args.lp_model, args.lp_threshold, args.nms_iou, args.device),
    ]
    print(f"device: {detectors[0].device}")
    results = run(
        args.input_dir,
        args.output_dir,
        detectors,
        args.detect_max_side,
        args.scale,
        preview=not args.no_preview,
        overwrite=args.overwrite,
    )
    failed = [r for r in results if r.status not in {"ok", "skipped"}]
    print(f"완료: {len(results)}장, 실패 {len(failed)}장 → {args.output_dir / META_DIR / 'blur_log.csv'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
