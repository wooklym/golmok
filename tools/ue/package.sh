#!/bin/bash
# Build, cook and package a Mac build (Mac port of package.ps1, D-022).
# Usage: ./tools/ue/package.sh [Development|Shipping] [DIR | --out-dir DIR] (positional DIR as in package.ps1)
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

Config="Development"
OutDir=""
Positional=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --out-dir) [ "$#" -ge 2 ] || golmok_die "package: --out-dir needs a value"; OutDir="$2"; shift 2 ;;
        --out-dir=*) OutDir="${1#--out-dir=}"; shift ;;
        -*) golmok_die "package: unknown option $1" ;;
        *)
            Positional=$((Positional + 1))
            case "$Positional" in
                1) Config="$1" ;;
                2) [ -z "$OutDir" ] || golmok_die "package: output dir given twice ($1)"; OutDir="$1" ;;
                *) golmok_die "package: unexpected argument $1" ;;
            esac
            shift ;;
    esac
done

# C-07: a fixed GOLMOK_PKG_DIR keeps one output path for every worktree (on Windows this avoided a firewall prompt
# per new exe path; whether the macOS application firewall prompts for TraceLog TCP 1985 is [미확인]).
# GOLMOK_PKG_DIR is read only when --out-dir is empty; whitespace-only counts as empty. Trailing "/" are trimmed.
if [ -z "$OutDir" ]; then
    EnvDir="$(golmok_trim "${GOLMOK_PKG_DIR:-}")"
    if [ -n "$EnvDir" ]; then
        OutDir="$EnvDir"
        while [ "$OutDir" != "/" ] && [ "${OutDir%/}" != "$OutDir" ]; do OutDir="${OutDir%/}"; done
    else
        OutDir="$RepoRoot/build/Mac"
    fi
fi
echo "Package output: $OutDir"
# WP-19 (review R76 T6): DefaultGame.ini [WP-19 hook] always cooks /Game/GASP and /Game/GolmokLocal when present.
if [ -e "$RepoRoot/unreal/Golmok/Content/GASP" ]; then
    echo "WARNING: Content/GASP exists: this package cooks the whole local GASP copy (about 1 GB, also in mode abp)" \
        "and must never be distributed (D-021). Without the GASP plugins enabled the cook may fail (runbook B7)." >&2
fi
# -NoHotReloadFromIDE (as in build.sh): any running editor/-game of this engine install with Live Coding
# otherwise fails the editor-target build with "Unable to build while Live Coding is active" (V-10).
# -package (Mac only; package.ps1 has none): without it the archived Golmok.app holds only the executable and
# fails at launch with "Library not loaded: @rpath/libtbb.12.dylib" (measured 2026-11-27, UE 5.8.4).
rc=0
"$UERunUAT" BuildCookRun \
    "-project=$Project" -platform=Mac "-clientconfig=$Config" \
    -build -cook -stage -pak -package -archive "-archivedirectory=$OutDir" -utf8output "-ubtargs=-NoHotReloadFromIDE" || rc=$?
if [ "$rc" -ne 0 ]; then golmok_die "Packaging failed ($rc)"; fi
