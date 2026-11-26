#!/bin/bash
# WP-19 (D-021): copy the GASP locomotion assets into this checkout as /Game/GASP, local only (never committed).
# Mac port of add-gasp.ps1 (D-022); the steps, job keys, messages and exit codes are the same.
# Same idea as add-mannequin.sh: every machine gets GASP from Fab itself (Fab EULA section 5(a): the public repo
# carries no GASP content, DDCvar or tag text). The GASP project is only read. Headless editor sessions run
# unreal/Golmok/Content/Python/golmok/gasp_import.py (job file in $GOLMOK_GASP_JOB):
#   1. migrate  (GASP project)   closure of tools/ue/gasp/closure.json -> Golmok Content (conflicts skipped).
#                                Stops BEFORE copying when /Game/GASP exists or leftovers of an earlier run sit at
#                                the Migrate paths (it names what to delete); hashes the GASP files (source_digest)
#   2. relocate (Golmok project) parse the GASP ini text, move under /Game/GASP; write Config/Golmok/local/
#                                gasp_manifest.json, gasp_ddcvars.json and Config/Tags/GASP.ini (all git-ignored).
#                                An empty or failed migrate is refused and the previous manifest is kept
#   3. verify   (Golmok project) sizes / hashes, ABP / BPI load, 27 DDCvars / 39 tags, tools/ue/gasp/expected.json
#                                (source_digest + engine), and no GASP path committable in git status
# Exit code 2: the rename failed and GASP stays at the Migrate paths -> set animation.json gasp.content_root to /Game.
# Never `git add -A` after this script; check_repo.py fails if a GASP / local path becomes committable.
# Usage: ./tools/ue/add-gasp.sh [--gasp-project ~/UE/GASP_58] [--verify] [--force] [--local-files] [--manifest]
#   (none)        install when nothing is installed (no Content/GASP, no manifest), then verify
#   --verify      only step 3
#   --force       install again although a manifest exists (a /Game install of exit 2). Never overwrites
#                 Content/GASP: delete Content/GASP and Config/Golmok/local first (runbook A3 re-install)
#   --local-files only rewrite gasp_ddcvars.json and Config/Tags/GASP.ini from the GASP project, then verify
#   --manifest    only rewrite gasp_manifest.json where the migrated packages are now (after a GUI Move), then verify
# GOLMOK_TEST_RHI=1 drops -nullrhi from the editor sessions (as for test.sh; -nullrhi on macOS is [미확인]).
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

GaspProject="$HOME/UE/GASP_58"
Verify=0
Force=0
LocalFiles=0
Manifest=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --gasp-project) [ "$#" -ge 2 ] || golmok_die "add-gasp: --gasp-project needs a value"; GaspProject="$2"; shift 2 ;;
        --gasp-project=*) GaspProject="${1#--gasp-project=}"; shift ;;
        --verify) Verify=1; shift ;;
        --force) Force=1; shift ;;
        --local-files) LocalFiles=1; shift ;;
        --manifest) Manifest=1; shift ;;
        *) golmok_die "add-gasp: unknown argument $1" ;;
    esac
done
GaspProject="${GaspProject%/}"

Here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
Script="$RepoRoot/unreal/Golmok/Content/Python/golmok/gasp_import.py"
Content="$RepoRoot/unreal/Golmok/Content"
Local="$RepoRoot/unreal/Golmok/Config/Golmok/local"
ManifestFile="$Local/gasp_manifest.json"
Tags="$RepoRoot/unreal/Golmok/Config/Tags/GASP.ini"
Work="$RepoRoot/unreal/Golmok/Saved/Golmok/add-gasp"

# -ExecutePythonScript=<file> stops at the first space (UE command line parsing): refuse such a clone path.
case "$Script" in
    *[[:space:]]*)
        golmok_die "add-gasp: the repository path has a space ($RepoRoot); clone it to a path without spaces (e.g. ~/src/golmok)."
        ;;
esac
golmok_require_editor_cmd

# A running editor on either project holds packages open (moves / reads race with it).
# Only processes whose executable name starts with UnrealEditor count (as Name LIKE 'UnrealEditor%' in add-gasp.ps1).
Running=""
while read -r Pid Exe; do
    [ -n "${Pid:-}" ] || continue
    case "${Exe##*/}" in UnrealEditor*) ;; *) continue ;; esac
    CommandLine="$(ps -o command= -p "$Pid" 2>/dev/null || true)"
    case "$CommandLine" in
        *Golmok.uproject* | *"$GaspProject"*) Running="${Running:+$Running, }$Pid" ;;
    esac
done <<EOF_PS
$(ps -axo pid=,comm= 2>/dev/null || true)
EOF_PS
if [ -n "$Running" ]; then golmok_die "add-gasp: close the Unreal Editor first (running: $Running)."; fi
mkdir -p "$Work"

RhiArgs="-nullrhi"
if golmok_use_rhi; then RhiArgs=""; fi

# json_get FILE KEY: a top-level value of a step report (true/false for booleans, "" for null, len for #KEY).
json_get() {
    "$GolmokPython" - "$1" "$2" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8-sig") as f:
    report = json.load(f)
key = sys.argv[2]
if key.startswith("#"):
    print(len(report.get(key[1:]) or []))
else:
    value = report.get(key)
    print("" if value is None else ("true" if value is True else "false" if value is False else value))
PY
}

# gasp_step UPROJECT STEP [KEY VALUE]...: write <step>-job.json, run gasp_import.py headless, print the messages.
# The report is left at $Work/<step>.json (StepResult).
gasp_step() {
    local uproject="$1" step="$2"
    shift 2
    StepResult="$Work/$step.json"
    local job="$Work/$step-job.json"
    rm -f "$StepResult"
    # BOM-less UTF-8 JSON, all values strings (as ConvertTo-Json of the add-gasp.ps1 hashtable).
    "$GolmokPython" - "$job" step "$step" "$@" result "$StepResult" <<'PY'
import json
import sys

args = sys.argv[2:]
job = dict(zip(args[0::2], args[1::2]))
with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as f:
    json.dump(job, f, indent=2, ensure_ascii=False)
PY
    echo "add-gasp: $step ($uproject)"
    # shellcheck disable=SC2086  # RhiArgs is one flag or nothing
    GOLMOK_GASP_JOB="$job" "$UEEditorCmd" "$uproject" "-ExecutePythonScript=$Script" \
        -unattended $RhiArgs -nosplash -nopause -nosound >/dev/null 2>&1 || true
    if [ ! -f "$StepResult" ]; then
        golmok_die "add-gasp: $step wrote no result ($StepResult); see the editor log under Saved/Logs."
    fi
    "$GolmokPython" - "$StepResult" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8-sig") as f:
    report = json.load(f)
for message in report.get("messages") or []:
    print(f"    {message}")
PY
}

GaspUProject=""
GaspDir=""
find_gasp_uproject() {
    local found=""
    local candidate
    for candidate in "$GaspProject"/*.uproject; do
        if [ -f "$candidate" ]; then
            found="$candidate"
            break
        fi
    done
    if [ -z "$found" ]; then golmok_die "No .uproject in '$GaspProject' (create the GASP 5.8 project from Fab first)."; fi
    GaspDir="$(cd -- "$(dirname -- "$found")" >/dev/null && pwd)"
    GaspUProject="$GaspDir/$(basename "$found")"
}

if [ "$LocalFiles" -eq 1 ]; then
    find_gasp_uproject
    gasp_step "$Project" local_files local_dir "$Local" tags_ini "$Tags" gasp_project "$GaspDir"
    if [ "$(json_get "$StepResult" ok)" != "true" ]; then golmok_die "add-gasp: local_files failed (see the messages above)."; fi
elif [ "$Manifest" -eq 1 ]; then
    find_gasp_uproject
    gasp_step "$Project" manifest migrate_report "$Work/migrate-last-ok.json" content_dir "$Content" \
        local_dir "$Local" gasp_project "$GaspDir"
    if [ "$(json_get "$StepResult" ok)" != "true" ]; then golmok_die "add-gasp: manifest failed (see the messages above)."; fi
elif [ "$Verify" -eq 0 ]; then
    find_gasp_uproject
    if [ -e "$Content/GASP" ]; then
        if [ "$Force" -eq 1 ]; then
            golmok_die "add-gasp --force never overwrites an install: delete $Content/GASP and $Local, then run add-gasp again (runbook A3 re-install)."
        fi
        echo "Already installed: $Content/GASP; verifying."
    elif [ -e "$ManifestFile" ] && [ "$Force" -eq 0 ]; then
        echo "Already installed ($ManifestFile, content_root /Game?); verifying. --force re-installs."
    else
        if [ ! -e "$Content/Characters/Mannequins" ]; then
            golmok_die "add-gasp: run ./tools/ue/add-mannequin.sh first (Content/Characters/Mannequins is missing)."
        fi
        gasp_step "$GaspUProject" migrate closure "$Here/gasp/closure.json" dest_content "$Content" \
            source_content "$GaspDir/Content" history "$Work/migrated-history.json"
        Migrate="$StepResult"
        if [ "$(json_get "$Migrate" ok)" != "true" ]; then golmok_die "add-gasp: migrate failed (see the messages above)."; fi
        # --manifest needs the last successful migrate even after later refused runs rewrote migrate.json.
        cp -f "$Work/migrate.json" "$Work/migrate-last-ok.json"
        echo "add-gasp migrate: $(json_get "$Migrate" source_package_count) closure packages," \
            "$(json_get "$Migrate" '#migrated') copied, source_digest $(json_get "$Migrate" source_digest)"
        gasp_step "$Project" relocate migrate_report "$Work/migrate.json" content_dir "$Content" \
            local_dir "$Local" tags_ini "$Tags" gasp_project "$GaspDir"
        Relocate="$StepResult"
        if [ "$(json_get "$Relocate" ok)" != "true" ]; then golmok_die "add-gasp: relocate failed (see the messages above)."; fi
        if [ "$(json_get "$Relocate" exit)" = "2" ]; then
            # verify would fail on the content_root mismatch: stop here with the instruction (exit 2).
            echo "WARNING: GASP stays at the Migrate paths: set Config/Golmok/animation.json gasp.content_root to" \
                "/Game, then run ./tools/ue/add-gasp.sh --verify. /Game/GASP cook lines no longer cover it (runbook A3)." >&2
            exit 2
        fi
    fi
fi

GitStatus="$Work/git-status.txt"
rc=0
git -C "$RepoRoot" status --porcelain --untracked-files=all >"$GitStatus" || rc=$?
if [ "$rc" -ne 0 ]; then
    golmok_die "add-gasp: git status failed ($rc; PATH / safe.directory): the leak check cannot run."
fi
gasp_step "$Project" verify content_dir "$Content" local_dir "$Local" tags_ini "$Tags" \
    expected "$Here/gasp/expected.json" git_status "$GitStatus"
Check="$StepResult"
echo "add-gasp verify: $(json_get "$Check" package_count) packages, digest $(json_get "$Check" digest)," \
    "source $(json_get "$Check" source_package_count) packages, source_digest $(json_get "$Check" source_digest)"
if [ "$(json_get "$Check" ok)" != "true" ]; then golmok_die "add-gasp: verify failed (see the messages above)."; fi
exit 0
