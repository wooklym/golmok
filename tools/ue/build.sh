#!/bin/bash
# Build the editor target (C++). Mac port of build.ps1 (D-022).
# Usage: ./tools/ue/build.sh [Development|DebugGame]
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
[ "$#" -le 1 ] || golmok_die "build: unexpected argument $2"
Config="${1:-Development}"

rc=0
"$UEBuild" GolmokEditor Mac "$Config" "-Project=$Project" -WaitMutex -NoHotReloadFromIDE || rc=$?
if [ "$rc" -ne 0 ]; then golmok_die "Build failed ($rc)"; fi
