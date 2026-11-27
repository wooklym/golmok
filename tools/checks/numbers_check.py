# /// rules-check: R147-2 절차 3 (every number in the text has log ground)
"""Numbers checker (rules 10(f), 영록 procedure R147-2 #3).

Targets are evidence log files only: the fixed list is
  ls "$E"/*.log "$E"/*.json "$E"/*.txt
    | grep -v -E 'body|published|postpublish|quotes-check|numbers-check
                  |task\.txt|commands\.txt'
and is printed at the head of the check log. Body drafts and published
copies never count as ground for their own numbers.
"""

# /// script
# dependencies = []
# ///
import argparse
import re
import sys
from pathlib import Path

TOKEN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
    r"|\d{1,2}:\d{2}:\d{2}"
    r"|\d{1,2}:\d{2}(?!:)"
    r"|\b[A-Za-z]{3} \d{1,2} \d{2}:\d{2}\b"
    r"|\b[0-9a-f]{7,40}\b"
    r"|\d+\.\d+"
    r"|\b\d+\b"
)
EXCLUDE = re.compile(
    r"body|published|postpublish|quotes-check|numbers-check"
    r"|task\.txt|commands\.txt"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e", required=True, type=Path)
    ap.add_argument("--text", required=True, nargs="+", type=Path)
    args = ap.parse_args()

    targets = sorted(
        p
        for p in list(args.e.glob("*.log")) + list(args.e.glob("*.json")) + list(args.e.glob("*.txt"))
        if p.is_file() and not EXCLUDE.search(p.name)
    )
    out = ["=== numbers-check (규칙 10f — 대상: 로그 파일만) ==="]
    out += [f"--- 대상 파일 {len(targets)}개(고정 목록) ---"]
    out += [p.name for p in targets]

    text = "\n".join(p.read_text(errors="ignore") for p in args.text)
    tokens = sorted(set(TOKEN.findall(text)))
    zero = []
    for t in tokens:
        n, hits = 0, []
        for p in targets:
            c = p.read_text(errors="ignore").count(t)
            if c:
                n += c
                hits.append(p.name)
        shown = ", ".join(hits[:4]) + (" …" if len(hits) > 4 else "")
        out.append(f"[{n}] {t}" + (f" {shown}" if hits else " -> 0건"))
        if n == 0:
            zero.append(t)
    out += [
        f"--- 토큰 {len(tokens)}개 / 0건 {len(zero)}개 ---",
        "0건: " + (" ".join(zero) if zero else "없음"),
        "판정: " + ("PASS" if not zero else "FAIL"),
    ]
    print("\n".join(out))
    return 0 if not zero else 1


if __name__ == "__main__":
    sys.exit(main())
