# Shared paths for the UE helper scripts. Override the engine location with $env:UE_ROOT.
$ErrorActionPreference = "Stop"

$UERoot = if ($env:UE_ROOT) { $env:UE_ROOT } else { "C:\Program Files\Epic Games\UE_5.8" }
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Project = Join-Path $RepoRoot "unreal\Golmok\Golmok.uproject"

if (-not (Test-Path (Join-Path $UERoot "Engine\Binaries\Win64\UnrealEditor.exe"))) {
    throw "Unreal Engine not found at '$UERoot'. Set `$env:UE_ROOT to your UE 5.8 folder."
}
