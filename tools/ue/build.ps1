# Build the editor target (C++). Usage: .\tools\ue\build.ps1 [-Config Development|DebugGame]
param([string]$Config = "Development")
. (Join-Path $PSScriptRoot "common.ps1")

& (Join-Path $UERoot "Engine\Build\BatchFiles\Build.bat") GolmokEditor Win64 $Config "-Project=$Project" -WaitMutex -NoHotReloadFromIDE
if ($LASTEXITCODE -ne 0) { throw "Build failed ($LASTEXITCODE)" }
