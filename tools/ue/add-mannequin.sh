#!/bin/bash
# Add the UE mannequin (Manny/Quinn meshes, ABP_Unarmed, anims) to the project as /Game/Characters.
# Same files the editor copies for Content Browser > Add > Add Feature or Content Pack > Third Person
# (the "Characters" shared pack). Not committed to git; run once per checkout. Mac port of add-mannequin.ps1.
# Usage: ./tools/ue/add-mannequin.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

Source="$UERoot/Templates/TemplateResources/High/Characters/Content"
Destination="$RepoRoot/unreal/Golmok/Content/Characters"

if [ ! -e "$Source" ]; then golmok_die "Mannequin pack not found at '$Source'."; fi
if [ -e "$Destination" ]; then
    echo "Already present: $Destination (left unchanged)"
    exit 0
fi
cp -R "$Source" "$Destination"
echo "Copied mannequin pack to $Destination"
