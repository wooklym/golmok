#!/bin/bash
# Generate the Xcode workspace (unreal/Golmok/*.xcworkspace, git-ignored). Mac port of generate-project-files.ps1.
# Usage: ./tools/ue/generate-project-files.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

rc=0
"$UEBuild" -ProjectFiles "-Project=$Project" -Game -Progress || rc=$?
if [ "$rc" -ne 0 ]; then golmok_die "Project file generation failed ($rc)"; fi
