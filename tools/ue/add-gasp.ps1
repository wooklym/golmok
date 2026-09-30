# WP-19 (D-021): copy the GASP locomotion assets into this checkout as /Game/GASP, local only (never committed).
# Same idea as add-mannequin.ps1: every PC gets GASP from Fab itself (Fab EULA section 5(a): the public repo carries
# no GASP content, DDCvar or tag text). The GASP project is only read. Three headless editor sessions run
# unreal/Golmok/Content/Python/golmok/gasp_import.py (job file in $env:GOLMOK_GASP_JOB):
#   1. migrate  (GASP project)   closure of tools/ue/gasp/closure.json -> Golmok Content (conflicts skipped)
#   2. relocate (Golmok project) move it under /Game/GASP; write Config/Golmok/local/gasp_manifest.json,
#                                gasp_ddcvars.json and Config/Tags/GASP.ini (all git-ignored)
#   3. verify   (Golmok project) sizes / hashes, ABP / BPI load, 27 DDCvars / 39 tags, tools/ue/gasp/expected.json,
#                                and no GASP path committable in git status
# Exit code 2: the rename failed and GASP stays at the Migrate paths -> set animation.json gasp.content_root to /Game.
# Never `git add -A` after this script; check_repo.py fails if a GASP / local path becomes committable.
# Usage: .\tools\ue\add-gasp.ps1 [-GaspProject C:\UE\GASP_58] [-Verify] [-Force]
#   -Verify  only step 3      -Force  migrate again although Content\GASP exists (name conflicts are skipped)
param([string]$GaspProject = "C:\UE\GASP_58", [switch]$Verify, [switch]$Force)
. (Join-Path $PSScriptRoot "common.ps1")

$Script = Join-Path $RepoRoot "unreal\Golmok\Content\Python\golmok\gasp_import.py"
$Content = Join-Path $RepoRoot "unreal\Golmok\Content"
$Local = Join-Path $RepoRoot "unreal\Golmok\Config\Golmok\local"
$Tags = Join-Path $RepoRoot "unreal\Golmok\Config\Tags\GASP.ini"
$Work = Join-Path $RepoRoot "unreal\Golmok\Saved\Golmok\add-gasp"
$Editor = Join-Path $UERoot "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
New-Item -ItemType Directory -Force -Path $Work | Out-Null

function Invoke-GaspStep([string]$UProject, [hashtable]$Job) {
    $Result = Join-Path $Work "$($Job.step).json"
    $JobFile = Join-Path $Work "$($Job.step)-job.json"
    $Job.result = $Result
    if (Test-Path $Result) { Remove-Item $Result -Force }
    # BOM-less UTF-8 (Windows PowerShell 5.1 Set-Content -Encoding UTF8 adds a BOM).
    [IO.File]::WriteAllText($JobFile, ($Job | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
    $env:GOLMOK_GASP_JOB = $JobFile
    Write-Host "add-gasp: $($Job.step) ($UProject)"
    & $Editor "$UProject" "-ExecutePythonScript=$Script" -unattended -nullrhi -nosplash -nopause -nosound | Out-Null
    Remove-Item Env:\GOLMOK_GASP_JOB
    if (-not (Test-Path $Result)) {
        throw "add-gasp: $($Job.step) wrote no result ($Result); see the editor log under Saved\Logs."
    }
    $Report = Get-Content $Result -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($Message in $Report.messages) { Write-Host "    $Message" }
    return $Report
}

$ExitCode = 0
if (-not $Verify) {
    $GaspUProject = Get-ChildItem -Path $GaspProject -Filter *.uproject -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $GaspUProject) { throw "No .uproject in '$GaspProject' (create the GASP 5.8 project from Fab first)." }
    if ((Test-Path (Join-Path $Content "GASP")) -and -not $Force) {
        Write-Host "Already present: $(Join-Path $Content 'GASP') (use -Force to migrate again); verifying."
    }
    else {
        $Migrate = Invoke-GaspStep $GaspUProject.FullName @{
            step = "migrate"; closure = (Join-Path $PSScriptRoot "gasp\closure.json"); dest_content = "$Content"
        }
        if (-not $Migrate.ok) { throw "add-gasp: migrate failed (see the messages above)." }
        $Relocate = Invoke-GaspStep $Project @{
            step = "relocate"; migrate_report = (Join-Path $Work "migrate.json"); content_dir = "$Content"
            local_dir = $Local; tags_ini = $Tags; gasp_project = $GaspUProject.DirectoryName
        }
        if (-not $Relocate.ok) { throw "add-gasp: relocate failed (see the messages above)." }
        if ($Relocate.exit -eq 2) {
            # verify would fail on the content_root mismatch: stop here with the instruction (exit 2).
            Write-Warning ("GASP stays at the Migrate paths: set Config/Golmok/animation.json gasp.content_root to " +
                "/Game, then run .\tools\ue\add-gasp.ps1 -Verify. /Game/GASP cook lines no longer cover it (runbook A3).")
            exit 2
        }
    }
}

$GitStatus = Join-Path $Work "git-status.txt"
& git -C "$RepoRoot" status --porcelain --untracked-files=all -- unreal/Golmok | Set-Content -Path $GitStatus -Encoding UTF8
$Check = Invoke-GaspStep $Project @{
    step = "verify"; content_dir = "$Content"; local_dir = $Local; tags_ini = $Tags
    expected = (Join-Path $PSScriptRoot "gasp\expected.json"); git_status = $GitStatus
}
Write-Host ("add-gasp verify: {0} packages, digest {1}" -f $Check.package_count, $Check.digest)
if (-not $Check.ok) { throw "add-gasp: verify failed (see the messages above)." }
exit $ExitCode
