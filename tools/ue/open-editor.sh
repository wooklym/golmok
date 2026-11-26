#!/bin/bash
# Open the project in the Unreal Editor without waiting (Mac port of open-editor.ps1).
# Usage: ./tools/ue/open-editor.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# `open -n` starts a new editor instance; --args hands the project path to the app.
open -n -a "$UEEditorApp" --args "$Project"
