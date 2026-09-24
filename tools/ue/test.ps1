# Run the project's automation tests headless (no window). Build first with build.ps1.
# Usage: .\tools\ue\test.ps1 [-Filter Golmok.] [-SetupDevLevel]
#   -SetupDevLevel  create /Game/Golmok/Maps/L_Dev first if it is missing (golmok.setup_dev_level)
param([string]$Filter = "Golmok.", [switch]$SetupDevLevel)
. (Join-Path $PSScriptRoot "common.ps1")

$ReportDir = Join-Path $RepoRoot "unreal\Golmok\Saved\Automation\Report"
if (Test-Path $ReportDir) { Remove-Item $ReportDir -Recurse -Force }

$Commands = @()
if ($SetupDevLevel) { $Commands += "py import golmok.setup_dev_level as s; s.run()" }
$Commands += "Automation RunTests $Filter;Quit"

# The full engine log goes to unreal\Golmok\Saved\Logs\Golmok.log; only the report is printed here.
& (Join-Path $UERoot "Engine\Binaries\Win64\UnrealEditor-Cmd.exe") "$Project" `
    "-ExecCmds=$($Commands -join ',')" "-ReportExportPath=$ReportDir" `
    -unattended -nullrhi -nosplash -nopause -nosound | Out-Null

$Index = Join-Path $ReportDir "index.json"
if (-not (Test-Path $Index)) { throw "No automation report at $Index (see unreal\Golmok\Saved\Logs\Golmok.log)." }
$Report = Get-Content $Index -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($T in $Report.tests) {
    Write-Host ("{0,-10} {1}" -f $T.state, $T.fullTestPath)
    foreach ($E in $T.entries) { Write-Host ("    [{0}] {1}" -f $E.event.type, $E.event.message) }
}
Write-Host ("Succeeded: {0}  Failed: {1}  Not run: {2}" -f $Report.succeeded, $Report.failed, $Report.notRun)
if ($Report.failed -gt 0 -or $Report.succeeded -eq 0) { throw "Automation tests failed" }
