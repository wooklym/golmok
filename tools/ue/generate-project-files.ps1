# Generate the Visual Studio / Rider solution. Usage: .\tools\ue\generate-project-files.ps1
. (Join-Path $PSScriptRoot "common.ps1")

& (Join-Path $UERoot "Engine\Build\BatchFiles\Build.bat") -ProjectFiles "-Project=$Project" -Game -Progress
if ($LASTEXITCODE -ne 0) { throw "Project file generation failed ($LASTEXITCODE)" }
