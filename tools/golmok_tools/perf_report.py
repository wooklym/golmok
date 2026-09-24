"""Summarize Unreal CSV profiler captures (fps, frame/game/render/GPU times) for spike comparisons.

Capture in the game or PIE console:
    CsvProfile Start      ... walk the fixed route ...      CsvProfile Stop
CSV files land in unreal/Golmok/Saved/Profiling/CSV/. Then:
    golmok-perf Saved\\Profiling\\CSV\\Profile(...).csv --label "a: mesh 1440p"
    golmok-perf a.csv b.csv c.csv --markdown >> docs\\research\\08-spike-results.md
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Column name candidates (Unreal CSV profiler names vary slightly between versions).
COLUMNS = {
    "frame": ("FrameTime",),
    "game": ("GameThreadTime", "GameThread"),
    "render": ("RenderThreadTime", "RenderThread"),
    "gpu": ("GPUTime", "GPU/Total", "GPU"),
}


@dataclass
class Summary:
    label: str
    frames: int
    fps_avg: float
    fps_1pct_low: float
    frame_ms_p50: float
    frame_ms_p99: float
    game_ms: float | None
    render_ms: float | None
    gpu_ms: float | None


def _find(header: list[str], names: tuple[str, ...]) -> int | None:
    for n in names:
        if n in header:
            return header.index(n)
    for i, h in enumerate(header):
        if any(h.endswith("/" + n) or h == n for n in names):
            return i
    return None


def read_csv(path: Path) -> dict[str, np.ndarray]:
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise ValueError(f"{path} is empty")
    header = [h.strip() for h in rows[0]]
    data = []
    for r in rows[1:]:
        if not r or r[0].startswith("["):  # metadata / footer rows
            continue
        if r[: len(header)] == header:  # repeated header at the end
            continue
        data.append(r)
    out: dict[str, np.ndarray] = {}
    for key, names in COLUMNS.items():
        idx = _find(header, names)
        if idx is None:
            continue
        vals = []
        for r in data:
            try:
                vals.append(float(r[idx]))
            except (ValueError, IndexError):
                pass
        if vals:
            out[key] = np.asarray(vals)
    if "frame" not in out:
        raise ValueError(f"{path}: no FrameTime column (header starts {header[:6]})")
    return out


def summarize(cols: dict[str, np.ndarray], label: str, skip_seconds: float = 2.0) -> Summary:
    frame = cols["frame"]
    # Drop warm-up frames (streaming, shader compile hitches) at the start.
    keep = np.cumsum(frame) / 1000.0 > skip_seconds
    if keep.sum() < 10:
        keep = np.ones_like(frame, dtype=bool)
    f = frame[keep]
    fps = 1000.0 / f

    def mean(key):
        return float(np.mean(cols[key][keep[: len(cols[key])]])) if key in cols else None

    return Summary(
        label=label,
        frames=int(len(f)),
        fps_avg=float(len(f) / (f.sum() / 1000.0)),
        fps_1pct_low=float(np.percentile(fps, 1)),
        frame_ms_p50=float(np.percentile(f, 50)),
        frame_ms_p99=float(np.percentile(f, 99)),
        game_ms=mean("game"),
        render_ms=mean("render"),
        gpu_ms=mean("gpu"),
    )


def _fmt(v, nd=1):
    return "-" if v is None else f"{v:.{nd}f}"


def to_markdown(rows: list[Summary]) -> str:
    lines = [
        "| 구성 | 프레임 | 평균 fps | 1% low fps | 프레임 p50 ms | p99 ms | Game ms | Render ms | GPU ms |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in rows:
        lines.append(
            f"| {s.label} | {s.frames} | {_fmt(s.fps_avg)} | {_fmt(s.fps_1pct_low)} | "
            f"{_fmt(s.frame_ms_p50, 2)} | {_fmt(s.frame_ms_p99, 2)} | {_fmt(s.game_ms, 2)} | "
            f"{_fmt(s.render_ms, 2)} | {_fmt(s.gpu_ms, 2)} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Unreal CSV 프로파일 요약 (fps, 1% low, 스레드·GPU 시간)")
    ap.add_argument("csv", nargs="+", type=Path)
    ap.add_argument("--label", action="append", help="각 CSV의 표시 이름 (순서대로, 생략 시 파일명)")
    ap.add_argument("--skip-seconds", type=float, default=2.0, help="시작 워밍업 제외 초 (기본 2)")
    ap.add_argument("--markdown", action="store_true", help="마크다운 표만 출력")
    args = ap.parse_args(argv)

    labels = args.label or []
    rows = []
    for i, path in enumerate(args.csv):
        label = labels[i] if i < len(labels) else path.stem
        rows.append(summarize(read_csv(path), label, args.skip_seconds))
    if args.markdown:
        print(to_markdown(rows))
    else:
        for s in rows:
            print(
                f"{s.label}: 평균 {s.fps_avg:.1f} fps, 1% low {s.fps_1pct_low:.1f} fps, "
                f"GPU {_fmt(s.gpu_ms, 2)} ms, 프레임 {s.frames}"
            )
        print()
        print(to_markdown(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
