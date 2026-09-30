"""WP-19a (D-021) conventions checkable without Unreal (design sections 1, 9, 11, 12, 15).

- Animation/ is in the header / source convention folders; its .cpp helpers live in namespace GolmokAnimation
  (unity build: no anonymous namespace, no file-scope static).
- The AGolmokGameMode hook is exactly the documented override; the untouched hot spots carry no WP-19 text.
- No PoseSearch / Chooser / Mover / GameplayCameras include in Source/ and no such Build.cs module (D-021
  condition 1); Golmok.uproject plugins stay inside the D-021 allowed list (19b enables the GASP ones apart).
- .gitignore / DefaultGame.ini hook lines, add-gasp.ps1 -> gasp_import, golmok.anim registered once, the four
  Golmok.Animation.* automation tests under the editor guard, the runbook carries the D-021 criteria verbatim.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from test_ue_wp09_fixture import BUILD_CS_EDITOR, BUILD_CS_PRIVATE, BUILD_CS_PUBLIC, _strip_comments
from test_ue_zone_fixture import CONVENTION_FOLDERS

REPO = Path(__file__).resolve().parents[2]
UE = REPO / "unreal" / "Golmok"
SOURCE = UE / "Source" / "Golmok"
ANIMATION = SOURCE / "Animation"
RUNBOOK = REPO / "docs" / "runbooks" / "pc-verify-wp19.md"

ANIMATION_FILES = (
    "GolmokLocomotionMath.h",
    "GolmokLocomotionStateComponent.h",
    "GolmokLocomotionStateComponent.cpp",
    "GolmokGaspCharacter.h",
    "GolmokGaspCharacter.cpp",
    "GolmokAnimationConfig.h",
    "GolmokAnimationConfig.cpp",
    "GolmokAnimationSubsystem.h",
    "GolmokAnimationSubsystem.cpp",
)
AUTOMATION_TESTS = (
    "Golmok.Animation.Config",
    "Golmok.Animation.StateProvider",
    "Golmok.Animation.Fallback",
    "Golmok.Animation.GaspSmoke",
)
FORBIDDEN_MODULES = ("PoseSearch", "Chooser", "Mover", "GameplayCameras")
# D-021 "Experimental 허용 범위": plugins the unmodified GASP locomotion assets need (+ what the project had).
ALLOWED_PLUGINS = {
    "EnhancedInput", "PythonScriptPlugin", "EditorScriptingUtilities", "AndroidFileServer",
    "PoseSearch", "Chooser", "AnimationWarping", "MotionWarping", "AnimationLocomotionLibrary", "BlendStack",
    "CurveExpression", "DrawDebugLibrary", "MovieSceneAnimMixer", "Mover",
}  # fmt: skip
FORBIDDEN_PLUGINS = {
    "GameplayCameras", "ChaosMover", "MoverExamples", "Locomotor", "SmartObjects", "GameplayInteractions",
    "MetaHuman", "LiveLink", "RigLogic", "HairStrands",
}  # fmt: skip
# D-021 decision text the runbook must quote unchanged (V-15 pre-registered criteria).
D021_CRITERIA = (
    "같은 메시·같은 카메라·블라인드 채점. 합계 ≥ ① + 4, ≥ ②b − 2. S1·S2 미끄러짐 ≤ ①의 1/2. "
    "S3은 돌아서기로 측정. 평균 fps 하락 5 % 이하 또는 60 fps 이상."
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_animation_folder_files_and_conventions():
    assert "Animation" in CONVENTION_FOLDERS
    assert sorted(p.name for p in ANIMATION.iterdir()) == sorted(ANIMATION_FILES)
    for name in ANIMATION_FILES:
        text = _read(ANIMATION / name)
        if name.endswith(".cpp"):
            assert "namespace\n" not in text and "namespace {" not in text, f"{name}: no anonymous namespace"
            assert re.search(r"^static\s", text, re.M) is None, f"{name}: no file-scope static (unity build)"
            helpers = re.findall(r"^namespace (\w+)", text, re.M)
            assert set(helpers) <= {"GolmokAnimation"}, (name, helpers)
        for module in FORBIDDEN_MODULES:
            assert not re.search(rf'#include\s+[<"]{module}', text), (name, module)


def test_no_gasp_plugin_module_dependency_in_source_or_build_cs():
    for path in SOURCE.rglob("*.[ch]*"):
        text = _read(path)
        for module in FORBIDDEN_MODULES:
            assert not re.search(rf'#include\s+[<"]{module}/', text), (path, module)
    build = _strip_comments(_read(SOURCE / "Golmok.Build.cs"))
    modules = set(re.findall(r'"(\w+)"', build))
    assert modules == BUILD_CS_PUBLIC | BUILD_CS_PRIVATE | BUILD_CS_EDITOR
    assert not modules & set(FORBIDDEN_MODULES)


def test_uproject_plugins_inside_the_d021_allowed_list():
    plugins = json.loads(_read(UE / "Golmok.uproject")).get("Plugins", [])
    enabled = {p["Name"] for p in plugins if p.get("Enabled", False)}
    listed = {p["Name"] for p in plugins}
    assert listed <= ALLOWED_PLUGINS, sorted(listed - ALLOWED_PLUGINS)
    assert not enabled & FORBIDDEN_PLUGINS
    # 19a keeps the uproject as it was: the GASP plugins are enabled by 19b (WP-19 design section 13-1).
    assert not enabled & (
        ALLOWED_PLUGINS - {"EnhancedInput", "PythonScriptPlugin", "EditorScriptingUtilities"}
    )


def test_game_mode_hook_is_exactly_the_documented_override():
    header = _read(SOURCE / "GolmokGameMode.h")
    block = re.search(r"\t// \[WP-19 hook\][^\n]*\n(.*?)\t// \[/WP-19 hook\]\n};", header, re.S)
    assert block, "GolmokGameMode.h WP-19 hook block before };"
    assert block.group(1) == (
        "\tvirtual UClass* GetDefaultPawnClassForController_Implementation(AController* InController)"
        " override;\n"
    )
    cpp = _read(SOURCE / "GolmokGameMode.cpp")
    includes = re.findall(r'^#include "([^"]+)"(.*)$', cpp, re.M)
    assert includes[-1] == ("Animation/GolmokAnimationConfig.h", " // [WP-19 hook]")
    body = re.search(r"^// \[WP-19 hook\][^\n]*\n(.*?)^// \[/WP-19 hook\]\n\Z", cpp, re.S | re.M)
    assert body, "GolmokGameMode.cpp WP-19 hook block at the end"
    assert body.group(1) == (
        "UClass* AGolmokGameMode::GetDefaultPawnClassForController_Implementation("
        "AController* InController)\n"
        "{\n"
        "\treturn GolmokAnimation::ResolvePlayerPawnClass(InController, "
        "Super::GetDefaultPawnClassForController_Implementation(InController));\n"
        "}\n"
    )
    assert "DefaultPawnClass = AGolmokCharacter::StaticClass();" in cpp


def test_untouched_hot_spots_carry_no_wp19_text():
    for rel in (
        "Player/GolmokCharacter.h",
        "Player/GolmokCharacter.cpp",
        "Player/GolmokPlayerController.h",
        "Player/GolmokPlayerController.cpp",
        "Golmok.Build.cs",
    ):
        assert "WP-19" not in _read(SOURCE / rel), rel
    for rel in ("Config/DefaultEngine.ini", "Config/DefaultInput.ini", "Golmok.uproject"):
        assert "WP-19" not in _read(UE / rel), rel
    for folder in ("Characters", "Audio"):  # Astra lanes
        for path in (SOURCE / folder).iterdir():
            assert "WP-19" not in _read(path) and "GolmokAnimation" not in _read(path), path


def test_gitignore_and_default_game_ini_hooks():
    lines = _read(REPO / ".gitignore").splitlines()
    start, end = (
        lines.index(next(ln for ln in lines if ln.startswith("# [WP-19 hook]"))),
        lines.index("# [/WP-19 hook]"),
    )
    block = lines[start:end]
    for line in (
        "unreal/Golmok/Content/*",
        "!unreal/Golmok/Content/Golmok/",
        "!unreal/Golmok/Content/Python/",
        "unreal/Golmok/Config/Golmok/local/",
        "unreal/Golmok/Config/Tags/GASP*.ini",
    ):
        assert line in block, line
    ini = _read(UE / "Config" / "DefaultGame.ini")
    tail = ini[ini.index("; [WP-19 hook]") :]
    assert tail.splitlines()[-3:] == [
        "[/Script/UnrealEd.ProjectPackagingSettings]",
        '+DirectoriesToAlwaysCook=(Path="/Game/GASP")',
        '+DirectoriesToAlwaysCook=(Path="/Game/GolmokLocal")',
    ]
    assert "DDCvar" not in ini.replace("; [WP-19 hook]", "")


def test_console_command_and_automation_tests():
    cpp = _read(ANIMATION / "GolmokAnimationSubsystem.cpp")
    assert re.search(r'FAutoConsoleCommandWithWorldAndArgs GCmdAnim\(TEXT\("golmok\.anim"\)', cpp)
    for sub in ("status", "mode <abp|gasp|config>", "profile <id>", "preview [off]"):
        assert sub in cpp, sub
    assert "AddExtraHudLineProvider" in cpp and "RemoveExtraHudLineProvider" in cpp
    test = _read(SOURCE / "Tests" / "GolmokAnimationTest.cpp")
    guard = test.index("#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR")
    names = re.findall(r'IMPLEMENT_SIMPLE_AUTOMATION_TEST\(\s*\w+\s*,\s*"(Golmok\.Animation\.\w+)"', test)
    assert tuple(names) == AUTOMATION_TESTS
    assert test.index("IMPLEMENT_SIMPLE_AUTOMATION_TEST") > guard
    assert "GASP not installed — skipped" in test


def test_add_gasp_calls_gasp_import_and_nothing_gasp_is_committed():
    ps1 = _read(REPO / "tools" / "ue" / "add-gasp.ps1")
    assert "gasp_import.py" in ps1 and "common.ps1" in ps1
    assert "git add -A" in ps1  # the warning line ("Never `git add -A` ...")
    for path in (REPO / "tools" / "ue" / "gasp").iterdir():
        assert path.suffix == ".json", path  # names and paths only; T3D text arrives with 19b
    # Tracked files only: add-gasp writes these ignored local files on a PC by design.
    tracked = subprocess.run(
        [
            "git",
            "-C",
            str(REPO),
            "ls-files",
            "unreal/Golmok/Config/Tags",
            "unreal/Golmok/Config/Golmok/local",
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    assert tracked.strip() == ""


def test_runbook_quotes_the_d021_criteria():
    text = _read(RUNBOOK)
    assert D021_CRITERIA in text
    assert "## A. 19b" in text and "## B. V-15" in text
    for name in AUTOMATION_TESTS:
        assert name in text
    assert "git add -A" in text
    assert "불확실 API" in text
    decisions = _read(REPO / "docs" / "DECISIONS.md")
    assert D021_CRITERIA in decisions
