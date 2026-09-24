# Add the UE mannequin (Manny/Quinn meshes, ABP_Unarmed, anims) to the project as /Game/Characters.
# Same files the editor copies for Content Browser > Add > Add Feature or Content Pack > Third Person
# (the "Characters" shared pack). Not committed to git; run once per checkout.
# Usage: .\tools\ue\add-mannequin.ps1
. (Join-Path $PSScriptRoot "common.ps1")

$Source = Join-Path $UERoot "Templates\TemplateResources\High\Characters\Content"
$Destination = Join-Path $RepoRoot "unreal\Golmok\Content\Characters"

if (-not (Test-Path $Source)) { throw "Mannequin pack not found at '$Source'." }
if (Test-Path $Destination) {
    Write-Host "Already present: $Destination (left unchanged)"
    return
}
Copy-Item $Source $Destination -Recurse
Write-Host "Copied mannequin pack to $Destination"
