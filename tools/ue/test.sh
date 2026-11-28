#!/bin/bash
# Run the project's automation tests headless (no window). Build first with build.sh. Mac port of test.ps1 (D-022).
# Usage: ./tools/ue/test.sh [--filter Golmok.] [--setup-dev-level] [--rhi]
#   --setup-dev-level  create /Game/Golmok/Maps/L_Dev first if it is missing (golmok.setup_dev_level)
#   --rhi              keep the Metal RHI (drop -nullrhi); same as GOLMOK_TEST_RHI=1. -nullrhi works for the
#                      editor on macOS in test.sh runs: 확인(2026-11-27, mac-setup §8 #5). Use this if a run
#                      produces no report.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

Filter="Golmok."
SetupDevLevel=0
UseRhi=0
if golmok_use_rhi; then UseRhi=1; fi
while [ "$#" -gt 0 ]; do
    case "$1" in
        --filter) [ "$#" -ge 2 ] || golmok_die "test: --filter needs a value"; Filter="$2"; shift 2 ;;
        --filter=*) Filter="${1#--filter=}"; shift ;;
        --setup-dev-level) SetupDevLevel=1; shift ;;
        --rhi) UseRhi=1; shift ;;
        *) golmok_die "test: unknown argument $1" ;;
    esac
done
golmok_require_editor_cmd

ReportDir="$RepoRoot/unreal/Golmok/Saved/Automation/Report"
if [ -e "$ReportDir" ]; then rm -rf "$ReportDir"; fi

Commands=""
if [ "$SetupDevLevel" -eq 1 ]; then Commands="py import golmok.setup_dev_level as s; s.run(),"; fi
Commands="${Commands}Automation RunTests $Filter;Quit"

RhiArgs="-nullrhi"
if [ "$UseRhi" -eq 1 ]; then RhiArgs=""; fi

# The full engine log goes to ~/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log (mac-setup §8 #14); each editor
# launch rotates the previous file to Golmok-backup-<time>.log there, so copy the log right after a run. Only the
# report is printed here.
# Like test.ps1 the editor's output and exit code are ignored: the report decides.
# shellcheck disable=SC2086  # RhiArgs is one flag or nothing
"$UEEditorCmd" "$Project" \
    "-ExecCmds=$Commands" "-ReportExportPath=$ReportDir" \
    -unattended $RhiArgs -nosplash -nopause -nosound >/dev/null 2>&1 || true

Index="$ReportDir/index.json"
if [ ! -f "$Index" ]; then
    golmok_die "No automation report at $Index (see the editor log at ~/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log; each launch rotates the previous log to Golmok-backup-*.log there, so copy it right after a run)."
fi
rc=0
"$GolmokPython" - "$Index" <<'PY' || rc=$?
import json
import sys


def text(value):
    return "" if value is None else str(value)


with open(sys.argv[1], encoding="utf-8-sig") as f:
    report = json.load(f)
for test in report.get("tests") or []:
    print(f"{text(test.get('state')):<10} {text(test.get('fullTestPath'))}")
    for entry in test.get("entries") or []:
        event = entry.get("event") or {}
        print(f"    [{text(event.get('type'))}] {text(event.get('message'))}")
succeeded = report.get("succeeded") or 0
with_warnings = report.get("succeededWithWarnings") or 0  # J-36: "succeeded" counts only successes without a warning
failed = report.get("failed") or 0
print(f"Succeeded: {text(report.get('succeeded'))}  Failed: {text(report.get('failed'))}  Not run: {text(report.get('notRun'))}  Succeeded with warnings: {text(report.get('succeededWithWarnings'))}")
sys.exit(3 if failed > 0 or succeeded + with_warnings == 0 else 0)
PY
if [ "$rc" -ne 0 ]; then golmok_die "Automation tests failed"; fi
