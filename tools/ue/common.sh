# Shared paths for the UE helper scripts (Mac port of common.ps1, D-022). Sourced, not run.
# Override the engine location with UE_ROOT. DEVELOPER_DIR is left as the user set it (UE-396802: on 5.8.3 with
# Xcode 27 point it at an Xcode 26.x Developer folder; 5.8.4 fixed it). Needs only macOS system bash 3.2.
# Engine paths below on a real 5.8 install: 확인(2026-11-27, mac-setup §8 #1·#2).
set -euo pipefail

UE_ROOT="${UE_ROOT:-/Users/Shared/Epic Games/UE_5.8}"
UERoot="${UE_ROOT%/}"
# cd -- … >/dev/null: with CDPATH set, cd prints the directory and it would end up in the result.
RepoRoot="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." >/dev/null && pwd)"
Project="$RepoRoot/unreal/Golmok/Golmok.uproject"

# Layout of a Launcher 5.8 install on macOS: 확인(2026-11-27, mac-setup §8 #2). Change here only.
UEEditorApp="$UERoot/Engine/Binaries/Mac/UnrealEditor.app"
UEEditor="$UEEditorApp/Contents/MacOS/UnrealEditor"
UEEditorCmd="$UERoot/Engine/Binaries/Mac/UnrealEditor-Cmd"
UEBuild="$UERoot/Engine/Build/BatchFiles/Mac/Build.sh"
UERunUAT="$UERoot/Engine/Build/BatchFiles/RunUAT.sh"

golmok_die() {
    echo "$*" >&2
    exit 1
}

# 확인(2026-11-27, mac-setup §8 #2): on a Launcher install UnrealEditor-Cmd sits next to the .app, not inside
# it. Use the first candidate that exists, else the editor binary itself (it also takes -ExecCmds /
# -ExecutePythonScript on the command line).
if [ ! -x "$UEEditorCmd" ]; then
    if [ -x "$UEEditorApp/Contents/MacOS/UnrealEditor-Cmd" ]; then
        UEEditorCmd="$UEEditorApp/Contents/MacOS/UnrealEditor-Cmd"
    else
        UEEditorCmd="$UEEditor"
    fi
fi

# Scripts that run headless sessions call this first.
golmok_require_editor_cmd() {
    [ -x "$UEEditorCmd" ] || golmok_die "UnrealEditor-Cmd not found at '$UEEditorCmd' (check UE_ROOT)."
}

# JSON is read and written with Python (no jq on stock macOS). GOLMOK_PYTHON overrides python3.
GolmokPython="${GOLMOK_PYTHON:-python3}"

# -nullrhi for headless editor sessions, unless GOLMOK_TEST_RHI is set (not 0): 확인(2026-11-27, mac-setup
# §8 #5) for test.sh runs; under add-gasp.sh it is still [미확인] (J-15).
golmok_use_rhi() {
    case "${GOLMOK_TEST_RHI:-}" in "" | 0) return 1 ;; *) return 0 ;; esac
}

# Strip leading and trailing whitespace (plain bash 3.2 parameter expansion).
golmok_trim() {
    local v="$1"
    v="${v#"${v%%[![:space:]]*}"}"
    v="${v%"${v##*[![:space:]]}"}"
    printf '%s' "$v"
}

if [ ! -e "$UEEditor" ]; then
    golmok_die "Unreal Engine not found at '$UERoot'. Set UE_ROOT to your UE 5.8 folder."
fi
