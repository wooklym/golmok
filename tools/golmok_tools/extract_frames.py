"""Extract sharp frames from capture video (needs ffmpeg on PATH).

Frames are decoded at fps * oversample, then the sharpest frame (variance of Laplacian) in each
window of `oversample` consecutive frames is kept, giving roughly `fps` sharp frames per second.

Usage:
    golmok-frames video\\IMG_0001.mov frames\\ --fps 2
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

from .imageio import read_image, to_uint8


def sharpness(img: np.ndarray) -> float:
    gray = cv2.cvtColor(to_uint8(img), cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def best_per_window(scores: list[float], window: int) -> list[int]:
    """Index of the highest score in each consecutive window (last partial window included)."""
    if window < 1:
        raise ValueError("window must be >= 1")
    picks = []
    for start in range(0, len(scores), window):
        chunk = scores[start : start + window]
        picks.append(start + int(np.argmax(chunk)))
    return picks


def run_ffmpeg(video: Path, out_dir: Path, rate: float, bit_depth: int) -> list[Path]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg가 PATH에 없음. https://ffmpeg.org 에서 설치 후 다시 실행")
    pix_fmt = "rgb48be" if bit_depth == 16 else "rgb24"
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video),
        "-vf",
        f"fps={rate}",
        "-pix_fmt",
        pix_fmt,
        str(out_dir / "f_%06d.png"),
    ]
    subprocess.run(cmd, check=True)
    return sorted(out_dir.glob("f_*.png"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="영상에서 선명한 프레임 추출")
    ap.add_argument("video", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--fps", type=float, default=2.0, help="초당 남길 프레임 수 (기본 2)")
    ap.add_argument(
        "--oversample", type=int, default=3, help="창 크기: fps*oversample로 뽑아 창마다 1장 선택 (기본 3)"
    )
    ap.add_argument("--bit-depth", type=int, choices=[8, 16], default=8)
    args = ap.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="golmok_frames_") as tmp:
        frames = run_ffmpeg(args.video, Path(tmp), args.fps * args.oversample, args.bit_depth)
        if not frames:
            print("프레임 없음")
            return 1
        scores = [sharpness(read_image(p)) for p in frames]
        keep = best_per_window(scores, args.oversample)
        stem = args.video.stem
        for n, idx in enumerate(keep):
            shutil.copy2(frames[idx], args.out_dir / f"{stem}_{n:05d}.png")
    print(f"{len(frames)}프레임 중 {len(keep)}장 저장 → {args.out_dir}")
    print("참고: 영상 프레임에는 GPS EXIF가 없다. 정합은 사진 패스 기준으로 한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
