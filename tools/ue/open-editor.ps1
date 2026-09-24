# Open the project in the Unreal Editor. Usage: .\tools\ue\open-editor.ps1
. (Join-Path $PSScriptRoot "common.ps1")

Start-Process (Join-Path $UERoot "Engine\Binaries\Win64\UnrealEditor.exe") -ArgumentList "`"$Project`""
