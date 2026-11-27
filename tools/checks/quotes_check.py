# /// rules-check: R147-2 절차 2 (in-runbook quotes must exist in the cited log)
"""Runbook cell citation checker (rules 10(e), 영록 procedure R147-2 #2).

Each mapped string must appear with grep -F at least once in its cited log.
Strings with a label instead of a log file must carry one of LABELS.
"""

# /// script
# dependencies = []
# ///
import argparse
import re
import sys
from pathlib import Path

BACKTICK = re.compile(r"`([^`\n]+)`")
LABELS = {"명령", "경로", "로그이름", "태스크원문"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True, type=Path)
    ap.add_argument("--e", required=True, type=Path)
    ap.add_argument("--targets", type=Path, default=None)
    args = ap.parse_args()

    out = ["=== quotes-check (규칙 10e) ===", f"map={args.map}"]
    if args.targets:
        out += ["--- 검사 대상 셀 텍스트 목록(원문 첫 줄) ---"]
        out += [ln for ln in args.targets.read_text().splitlines() if ln.strip()]
    rows, fails = [], []
    for raw in args.map.read_text().splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        s, log = raw.rsplit("\t", 1)  # rsplit: 인용 문자열에 탭이 있어도 로그 이름은 마지막 필드
        if log in LABELS:
            rows.append(f"[label:{log}] {s}")
            continue
        lf = args.e / log
        if not lf.exists():
            fails.append(f"[missing-log] {log} :: {s}")
            continue
        hay = lf.read_text(errors="ignore")
        n = hay.count(s)
        rows.append(f"[{n}] {s} <- {log}")
        if n == 0:
            fails.append(f"[0hit] {s} <- {log}")
    out += [f"--- 결과 {len(rows)}행 ---", *rows]
    out += [f"--- 0건/오류 {len(fails)}건 ---", *(fails or ["없음"])]
    verdict = "PASS" if not fails else "FAIL"
    out += [f"판정: {verdict}"]
    print("\n".join(out))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
