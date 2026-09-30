# WP-19 (D-021): copy the GASP locomotion assets into this checkout as /Game/GASP, local only (never committed).
# Same idea as add-mannequin.ps1: every PC gets GASP from Fab itself (Fab EULA section 5(a): the public repo carries
# no GASP content, DDCvar or tag text). The GASP project is only read. Headless editor sessions run
# unreal/Golmok/Content/Python/golmok/gasp_import.py (job file in $env:GOLMOK_GASP_JOB):
#   1. migrate  (GASP project)   closure of tools/ue/gasp/closure.json -> Golmok Content (conflicts skipped).
#                                Stops BEFORE copying when /Game/GASP exists or leftovers of an earlier run sit at
#                                the Migrate paths (it names what to delete); hashes the GASP files (source_digest)
#   2. relocate (Golmok project) parse the GASP ini text, move under /Game/GASP; write Config/Golmok/local/
#                                gasp_manifest.json, gasp_ddcvars.json and Config/Tags/GASP.ini (all git-ignored).
#                                An empty or failed migrate is refused and the previous manifest is kept
#   3. verify   (Golmok project) sizes / hashes, ABP / BPI load, 27 DDCvars / 39 tags, tools/ue/gasp/expected.json
#                                (source_digest + engine), and no GASP path committable in git status
# Exit code 2: the rename failed and GASP stays at the Migrate paths -> set animation.json gasp.content_root to /Game.
# Never `git add -A` after this script; check_repo.py fails if a GASP / local path becomes committable.
# Usage: .\tools\ue\add-gasp.ps1 [-GaspProject C:\UE\GASP_58] [-Verify] [-Force] [-LocalFiles] [-Manifest]
#   (none)      install when nothing is installed (no Content\GASP, no manifest), then verify
#   -Verify     only step 3
#   -Force      install again although a manifest exists (a /Game install of exit 2). Never overwrites
#               Content\GASP: delete Content\GASP and Config\Golmok\local first (runbook A3 re-install)
#   -LocalFiles only rewrite gasp_ddcvars.json and Config\Tags\GASP.ini from the GASP project, then verify
#   -Manifest   only rewrite gasp_manifest.json where the migrated packages are now (after a GUI Move), then verify
param([string]$GaspProject = "C:\UE\GASP_58", [switch]$Verify, [switch]$Force, [switch]$LocalFiles, [switch]$Manifest)
. (Join-Path $PSScriptRoot "common.ps1")

$Script = Join-Path $RepoRoot "unreal\Golmok\Content\Python\golmok\gasp_import.py"
$Content = Join-Path $RepoRoot "unreal\Golmok\Content"
$Local = Join-Path $RepoRoot "unreal\Golmok\Config\Golmok\local"
$ManifestFile = Join-Path $Local "gasp_manifest.json"
$Tags = Join-Path $RepoRoot "unreal\Golmok\Config\Tags\GASP.ini"
$Work = Join-Path $RepoRoot "unreal\Golmok\Saved\Golmok\add-gasp"
$Editor = Join-Path $UERoot "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"

# -ExecutePythonScript=<file> stops at the first space (UE command line parsing): refuse such a clone path.
if ($Script -match '\s') {
    throw "add-gasp: the repository path has a space ($RepoRoot); clone it to a path without spaces (e.g. C:\src\golmok)."
}
# A running editor on either project holds packages open (moves / reads race with it).
$Running = Get-CimInstance Win32_Process -Filter "Name LIKE 'UnrealEditor%'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and ($_.CommandLine -like "*Golmok.uproject*" -or
        $_.CommandLine -like "*$([WildcardPattern]::Escape($GaspProject))*") }
if ($Running) {
    throw "add-gasp: close the Unreal Editor first (running: $(($Running | ForEach-Object { $_.ProcessId }) -join ', '))."
}
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

function Get-GaspUProject {
    $Found = Get-ChildItem -Path $GaspProject -Filter *.uproject -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $Found) { throw "No .uproject in '$GaspProject' (create the GASP 5.8 project from Fab first)." }
    return $Found
}

if ($LocalFiles) {
    $GaspUProject = Get-GaspUProject
    $Files = Invoke-GaspStep $Project @{
        step = "local_files"; local_dir = $Local; tags_ini = $Tags; gasp_project = $GaspUProject.DirectoryName
    }
    if (-not $Files.ok) { throw "add-gasp: local_files failed (see the messages above)." }
}
elseif ($Manifest) {
    $GaspUProject = Get-GaspUProject
    $Rebuilt = Invoke-GaspStep $Project @{
        step = "manifest"; migrate_report = (Join-Path $Work "migrate-last-ok.json"); content_dir = "$Content"
        local_dir = $Local; gasp_project = $GaspUProject.DirectoryName
    }
    if (-not $Rebuilt.ok) { throw "add-gasp: manifest failed (see the messages above)." }
}
elseif (-not $Verify) {
    $GaspUProject = Get-GaspUProject
    if (Test-Path (Join-Path $Content "GASP")) {
        if ($Force) {
            throw ("add-gasp -Force never overwrites an install: delete $(Join-Path $Content 'GASP') and $Local, " +
                "then run add-gasp again (runbook A3 re-install).")
        }
        Write-Host "Already installed: $(Join-Path $Content 'GASP'); verifying."
    }
    elseif ((Test-Path $ManifestFile) -and -not $Force) {
        Write-Host "Already installed ($ManifestFile, content_root /Game?); verifying. -Force re-installs."
    }
    else {
        if (-not (Test-Path (Join-Path $Content "Characters\Mannequins"))) {
            throw "add-gasp: run .\tools\ue\add-mannequin.ps1 first (Content\Characters\Mannequins is missing)."
        }
        $Migrate = Invoke-GaspStep $GaspUProject.FullName @{
            step = "migrate"; closure = (Join-Path $PSScriptRoot "gasp\closure.json"); dest_content = "$Content"
            source_content = (Join-Path $GaspUProject.DirectoryName "Content")
            history = (Join-Path $Work "migrated-history.json")
        }
        if (-not $Migrate.ok) { throw "add-gasp: migrate failed (see the messages above)." }
        # -Manifest needs the last successful migrate even after later refused runs rewrote migrate.json.
        Copy-Item (Join-Path $Work "migrate.json") (Join-Path $Work "migrate-last-ok.json") -Force
        Write-Host ("add-gasp migrate: {0} closure packages, {1} copied, source_digest {2}" -f
            $Migrate.source_package_count, $Migrate.migrated.Count, $Migrate.source_digest)
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
& git -C "$RepoRoot" status --porcelain --untracked-files=all | Set-Content -Path $GitStatus -Encoding UTF8
if ($LASTEXITCODE -ne 0) {
    throw "add-gasp: git status failed ($LASTEXITCODE; PATH / safe.directory): the leak check cannot run."
}
$Check = Invoke-GaspStep $Project @{
    step = "verify"; content_dir = "$Content"; local_dir = $Local; tags_ini = $Tags
    expected = (Join-Path $PSScriptRoot "gasp\expected.json"); git_status = $GitStatus
}
Write-Host ("add-gasp verify: {0} packages, digest {1}, source {2} packages, source_digest {3}" -f
    $Check.package_count, $Check.digest, $Check.source_package_count, $Check.source_digest)
if (-not $Check.ok) { throw "add-gasp: verify failed (see the messages above)." }
exit 0
