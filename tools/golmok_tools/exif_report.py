"""Capture QA report: shutter speed, lens used, resolution, GPS, time span.

Usage:
    golmok-exif D:\\golmok_capture\\2026-10-01_yeonnam_alley01\\photos
    golmok-exif <folder> --min-shutter 1/200 --csv report.csv
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from fractions import Fraction
from pathlib import Path

from .exif import ExifInfo, read_exif

PHOTO_EXTS = {".jpg", ".jpeg", ".heic", ".heif", ".dng", ".tif", ".tiff"}

# iPhone 35mm-equivalent focal lengths: ultra wide 13mm, main 24mm (also 28/35mm crops), tele 100mm+.
MAIN_35MM_RANGE = (20.0, 30.0)
FULL_RES_MP = 40.0  # 48MP ProRAW Max; 12/24MP means a lower resolution setting or a crop mode


def lens_class(info: ExifInfo) -> str:
    f = info.focal_35mm
    if f is None:
        return "unknown"
    if f < MAIN_35MM_RANGE[0]:
        return "ultra-wide"
    if f <= MAIN_35MM_RANGE[1]:
        return "main-1x"
    return "tele/crop"


def parse_shutter(text: str) -> float:
    return float(Fraction(text))


def fmt_shutter(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    if seconds >= 1:
        return f"{seconds:g}s"
    return f"1/{round(1 / seconds)}"


def collect(folder: Path) -> list[ExifInfo]:
    files = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in PHOTO_EXTS)
    infos = []
    for p in files:
        try:
            infos.append(read_exif(p))
        except Exception as e:  # corrupt file etc.
            print(f"[warn] {p}: {e}", file=sys.stderr)
            infos.append(ExifInfo(file=str(p)))
    return infos


def summarize(infos: list[ExifInfo], min_shutter: float) -> dict:
    total = len(infos)
    with_shutter = [i for i in infos if i.exposure_time is not None]
    fast = [i for i in with_shutter if i.exposure_time <= min_shutter + 1e-9]
    slow = sorted(
        (i for i in with_shutter if i.exposure_time > min_shutter + 1e-9),
        key=lambda i: i.exposure_time,
        reverse=True,
    )
    lenses: dict[str, int] = {}
    for i in infos:
        lenses[lens_class(i)] = lenses.get(lens_class(i), 0) + 1
    isos = [i.iso for i in infos if i.iso]
    mps = [i.megapixels for i in infos if i.megapixels]
    times = sorted(i.datetime_original for i in infos if i.datetime_original)
    return {
        "total": total,
        "shutter_known": len(with_shutter),
        "shutter_ok": len(fast),
        "slow": slow,
        "lenses": lenses,
        "iso_min": min(isos) if isos else None,
        "iso_median": statistics.median(isos) if isos else None,
        "iso_max": max(isos) if isos else None,
        "full_res": sum(1 for m in mps if m >= FULL_RES_MP),
        "res_known": len(mps),
        "no_gps": sum(1 for i in infos if i.lat is None or i.lon is None),
        "first": times[0] if times else None,
        "last": times[-1] if times else None,
    }


def render(summary: dict, min_shutter: float, max_list: int = 15) -> str:
    s = summary
    lines = [f"사진 {s['total']}장"]
    if s["shutter_known"]:
        pct = 100 * s["shutter_ok"] / s["shutter_known"]
        verdict = "OK" if pct >= 90 else "주의: 느린 셔터가 많음"
        lines.append(
            f"셔터 {fmt_shutter(min_shutter)} 이상: {s['shutter_ok']}/{s['shutter_known']} ({pct:.0f}%) → {verdict}"
        )
        for i in s["slow"][:max_list]:
            lines.append(f"  느림 {fmt_shutter(i.exposure_time):>7}  ISO {i.iso}  {Path(i.file).name}")
        if len(s["slow"]) > max_list:
            lines.append(f"  ... 외 {len(s['slow']) - max_list}장")
    lens_txt = ", ".join(f"{k} {v}" for k, v in sorted(s["lenses"].items()))
    lines.append(f"렌즈: {lens_txt}")
    if any(k != "main-1x" for k in s["lenses"]):
        lines.append(
            "  주의: 메인 1x 이외 렌즈 사진이 섞임(매크로 자동 전환/줌 확인). 재구성에서는 제외 권장"
        )
    if s["iso_min"] is not None:
        lines.append(f"ISO: 최소 {s['iso_min']} / 중앙 {s['iso_median']} / 최대 {s['iso_max']}")
    if s["res_known"]:
        lines.append(f"48MP급 해상도: {s['full_res']}/{s['res_known']}")
        if s["full_res"] < s["res_known"]:
            lines.append("  주의: 48MP 미만 사진 있음(ProRAW Max 설정 확인)")
    lines.append(f"GPS 없음: {s['no_gps']}장" + ("  주의: 카메라 위치 권한 확인" if s["no_gps"] else ""))
    if s["first"] and s["last"]:
        minutes = (s["last"] - s["first"]).total_seconds() / 60
        lines.append(f"촬영 시간: {s['first']:%Y-%m-%d %H:%M} ~ {s['last']:%H:%M} ({minutes:.0f}분)")
    return "\n".join(lines)


def write_csv(infos: list[ExifInfo], path: Path) -> None:
    rows = [dict(i.as_row(), lens_class=lens_class(i)) for i in infos]
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="촬영 사진 EXIF 점검(셔터, 렌즈, 해상도, GPS)")
    ap.add_argument("folder", type=Path)
    ap.add_argument("--min-shutter", default="1/200", help="이보다 느리면 경고 (기본 1/200)")
    ap.add_argument("--csv", type=Path, help="사진별 결과 CSV 저장 경로")
    args = ap.parse_args(argv)

    if not args.folder.is_dir():
        ap.error(f"폴더가 아님: {args.folder}")
    min_shutter = parse_shutter(args.min_shutter)
    infos = collect(args.folder)
    if not infos:
        print("사진 없음")
        return 1
    print(render(summarize(infos, min_shutter), min_shutter))
    if args.csv:
        write_csv(infos, args.csv)
        print(f"CSV: {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
