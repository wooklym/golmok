# Build, cook and package a Windows build. Usage: .\tools\ue\package.ps1 [-Config Development|Shipping]
param([string]$Config = "Development", [string]$OutDir = "")
. (Join-Path $PSScriptRoot "common.ps1")

if (-not $OutDir) { $OutDir = Join-Path $RepoRoot "build\Windows" }
& (Join-Path $UERoot "Engine\Build\BatchFiles\RunUAT.bat") BuildCookRun `
    "-project=$Project" -platform=Win64 "-clientconfig=$Config" `
    -build -cook -stage -pak -archive "-archivedirectory=$OutDir" -utf8output
if ($LASTEXITCODE -ne 0) { throw "Packaging failed ($LASTEXITCODE)" }
