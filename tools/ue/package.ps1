# Build, cook and package a Windows build. Usage: .\tools\ue\package.ps1 [-Config Development|Shipping]
param([string]$Config = "Development", [string]$OutDir = "")
. (Join-Path $PSScriptRoot "common.ps1")

if (-not $OutDir) { $OutDir = Join-Path $RepoRoot "build\Windows" }
# WP-19 (review R76 T6): DefaultGame.ini [WP-19 hook] always cooks /Game/GASP and /Game/GolmokLocal when present.
if (Test-Path (Join-Path $RepoRoot "unreal\Golmok\Content\GASP")) {
    Write-Warning ("Content\GASP exists: this package cooks the whole local GASP copy (about 1 GB, also in mode abp) " +
        "and must never be distributed (D-021). Without the GASP plugins enabled the cook may fail (runbook B7).")
}
# -NoHotReloadFromIDE (as in build.ps1): any running editor/-game of this engine install with Live Coding
# otherwise fails the editor-target build with "Unable to build while Live Coding is active" (V-10).
& (Join-Path $UERoot "Engine\Build\BatchFiles\RunUAT.bat") BuildCookRun `
    "-project=$Project" -platform=Win64 "-clientconfig=$Config" `
    -build -cook -stage -pak -archive "-archivedirectory=$OutDir" -utf8output "-ubtargs=-NoHotReloadFromIDE"
if ($LASTEXITCODE -ne 0) { throw "Packaging failed ($LASTEXITCODE)" }
