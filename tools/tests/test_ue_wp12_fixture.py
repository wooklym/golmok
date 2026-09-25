"""WP-12: photo mode conventions checkable without Unreal (design section 8-4).

- DefaultGame.ini: [/Script/Golmok.GolmokPhotoModeSubsystem] has exactly the eleven section 7 keys; the WP-05
  sections (test_ue_wp05_fixture.EXPECTED_KEYS) and the WP-09 zone keys are untouched.
- Golmok.Build.cs module sets equal the WP-09 baseline (no new module); the two UFS staging lines unchanged.
- Photo/ and the touched Debug / Player / Zones / Lighting files log through LogGolmok only.
- Tests/GolmokPhotoTest.cpp declares the three Golmok.Photo.* tests under the editor guard.
- No plugin symbols, no widgets (D-003), no Blueprintable photo classes (the pawn is NotBlueprintable).
- The four golmok.photo* console commands are FAutoConsoleCommandWithWorldAndArgs objects; the WP-04/05/09
  command names are all still registered.
- Unity build: anonymous-namespace / file-scope names unique across the module, Photo* prefixed in Photo/.
- MSVC C4458: static member function parameters (WP-09 scanner), every method parameter, and the local
  declarations of Photo/*.cpp never carry a member name of their class.
- Input: IA_GolmokPhoto* / IMC_GolmokPhoto / IMC_GolmokPhotoToggle exist, the WP-05 actions, contexts and the
  nine debug MapKey lines are unchanged, every photo action is bTriggerWhenPaused + bConsumeInput.
- No possession in Photo/ (view target only); no zone registration / load requests in Photo/;
  UGolmokZoneSubsystem::FindLoadedZoneAt is read-only.
- DefaultInput.ini keeps !DebugExecBindings=ClearArray; GolmokDebugSubsystem exposes RequestHighResScreenshot
  and checks the TakeHighResScreenShot() result; the golmok.screenshot messages are unchanged; the HUD comment
  no longer claims screenshots never include it; AGolmokTimeOfDay::ShiftTransitionStart is declared.
- The runbook (when present) names the commands, files, tests and ini keys; CONVENTION_FOLDERS covers Photo.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from test_lighting_presets import _unity_scope_definitions
from test_ue_wp05_fixture import EXPECTED_KEYS
from test_ue_wp09_fixture import (
    BUILD_CS_EDITOR,
    BUILD_CS_PRIVATE,
    BUILD_CS_PUBLIC,
    CONSOLE_COMMANDS,
    _class_scan,
    _function_body,
    _param_name,
    _shadow_clashes,
    _split_params,
    _strip_comments,
)
from test_ue_zone_fixture import CONVENTION_FOLDERS
from zone_util import REPO

sys.path.insert(0, str(REPO / "tools" / "scripts"))
from check_repo import parse_ue_ini  # noqa: E402

UE = REPO / "unreal" / "Golmok"
SOURCE = UE / "Source" / "Golmok"
PHOTO = SOURCE / "Photo"
INI = UE / "Config" / "DefaultGame.ini"
INPUT_INI = UE / "Config" / "DefaultInput.ini"
SUBSYSTEM_H = PHOTO / "GolmokPhotoModeSubsystem.h"
SUBSYSTEM_CPP = PHOTO / "GolmokPhotoModeSubsystem.cpp"
PAWN_H = PHOTO / "GolmokPhotoCameraPawn.h"
PAWN_CPP = PHOTO / "GolmokPhotoCameraPawn.cpp"
MATH_H = PHOTO / "GolmokPhotoMath.h"
PHOTO_TEST_CPP = SOURCE / "Tests" / "GolmokPhotoTest.cpp"
DEBUG_H = SOURCE / "Debug" / "GolmokDebugSubsystem.h"
DEBUG_CPP = SOURCE / "Debug" / "GolmokDebugSubsystem.cpp"
HUD_H = SOURCE / "Debug" / "GolmokHUD.h"
HUD_CPP = SOURCE / "Debug" / "GolmokHUD.cpp"
PC_H = SOURCE / "Player" / "GolmokPlayerController.h"
PC_CPP = SOURCE / "Player" / "GolmokPlayerController.cpp"
CHARACTER_CPP = SOURCE / "Player" / "GolmokCharacter.cpp"
ZONE_SUBSYSTEM_H = SOURCE / "Zones" / "GolmokZoneSubsystem.h"
ZONE_SUBSYSTEM_CPP = SOURCE / "Zones" / "GolmokZoneSubsystem.cpp"
TOD_H = SOURCE / "Lighting" / "GolmokTimeOfDay.h"
TOD_CPP = SOURCE / "Lighting" / "GolmokTimeOfDay.cpp"
RUNBOOK = REPO / "docs" / "runbooks" / "pc-verify-wp12.md"

PHOTO_SECTION = "/Script/Golmok.GolmokPhotoModeSubsystem"
# design section 7: the eleven keys of the photo section
PHOTO_KEYS = {
    "ConfigFile",
    "PhotoFolder",
    "ScreenshotMultiplier",
    "MaxMultiplier",
    "MaxDistanceM",
    "CollisionRadiusCm",
    "FootprintMarginM",
    "MoveSpeedMps",
    "PreCaptureFrames",
    "PostCaptureFrames",
    "PauseMode",
}
WP09_ZONE_KEYS = ("bDiscoverFromIndex", "DiscoveryIntervalSeconds", "DespawnDistanceM", "DespawnGraceSeconds")
PHOTO_AUTOMATION_TESTS = ("Golmok.Photo.EnterExit", "Golmok.Photo.Clamp", "Golmok.Photo.MetaJson")
PHOTO_CONSOLE_COMMANDS = ("golmok.photo", "golmok.photo.shoot", "golmok.photo.reset", "golmok.photo.set")
# design section 3-2: the photo actions the subsystem creates (plus the toggle owned by the controller)
PHOTO_ACTIONS = (
    "IA_GolmokPhotoShoot",
    "IA_GolmokPhotoReset",
    "IA_GolmokPhotoDof",
    "IA_GolmokPhotoHideCharacter",
    "IA_GolmokPhotoHideOverlay",
    "IA_GolmokPhotoFovUp",
    "IA_GolmokPhotoFovDown",
    "IA_GolmokPhotoFovWheel",
    "IA_GolmokPhotoEvUp",
    "IA_GolmokPhotoEvDown",
    "IA_GolmokPhotoFocusUp",
    "IA_GolmokPhotoFocusDown",
    "IA_GolmokPhotoFstopUp",
    "IA_GolmokPhotoFstopDown",
    "IA_GolmokPhotoRollUp",
    "IA_GolmokPhotoRollDown",
    "IA_GolmokPhotoMove",
    "IA_GolmokPhotoUpDown",
    "IA_GolmokPhotoLook",
    "IA_GolmokPhotoFast",
)
# WP-05 / character input assets that must keep their names
EXISTING_ACTIONS = {
    PC_CPP: (
        "IA_GolmokHud",
        "IA_GolmokCollision",
        "IA_GolmokPreset1",
        "IA_GolmokPreset2",
        "IA_GolmokPreset3",
        "IA_GolmokPreset4",
        "IA_GolmokNextPreset",
        "IA_GolmokRecord",
        "IA_GolmokPlay",
        "IMC_GolmokDebug",
    ),
    CHARACTER_CPP: ("IA_Move", "IA_Look", "IA_Jump", "IA_Run", "IMC_Default"),
}
DEBUG_MAPKEY_LINES = (
    "Context->MapKey(HudAction, EKeys::F1);",
    "Context->MapKey(CollisionAction, EKeys::F2);",
    "Context->MapKey(Preset1Action, EKeys::One);",
    "Context->MapKey(Preset2Action, EKeys::Two);",
    "Context->MapKey(Preset3Action, EKeys::Three);",
    "Context->MapKey(Preset4Action, EKeys::Four);",
    "Context->MapKey(NextPresetAction, EKeys::F5);",
    "Context->MapKey(RecordAction, EKeys::F9);",
    "Context->MapKey(PlayAction, EKeys::F10);",
)
SCREENSHOT_MESSAGES = (
    'TEXT("screenshot requested -> %s.png (%dx, written on the next frame)%s")',
    'TEXT(" [multiplier reduced: the requested size exceeds the max texture size]")',
    'TEXT("screenshot requested via HighResShot -> %s00000.png '
    '(no viewport size; written on the next frame)")',
)
TOUCHED_FILES = (
    DEBUG_H,
    DEBUG_CPP,
    HUD_H,
    HUD_CPP,
    PC_H,
    PC_CPP,
    ZONE_SUBSYSTEM_H,
    ZONE_SUBSYSTEM_CPP,
    TOD_H,
    TOD_CPP,
)
RUNBOOK_MENTIONS = (
    *PHOTO_CONSOLE_COMMANDS,
    "photo.json",
    "Screenshots/Golmok/photo",
    *PHOTO_AUTOMATION_TESTS,
    "test.ps1 -Filter Golmok.Photo",
    *sorted(PHOTO_KEYS),
    "에디터 창을 전면",
    "| 번호 | 호출/가정 | 불확실한 점 | 대안 | PC 검증 |",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _photo_sources() -> list[Path]:
    files = sorted(PHOTO.glob("*.h")) + sorted(PHOTO.glob("*.cpp"))
    assert len(files) == 5, [p.name for p in files]
    return files


# ---- (1) ini -----------------------------------------------------------------------------------------------


def test_ini_photo_section_has_exactly_the_eleven_keys():
    cp = parse_ue_ini(INI.read_text(encoding="utf-8-sig"))
    assert cp.has_section(PHOTO_SECTION)
    assert set(cp[PHOTO_SECTION]) == PHOTO_KEYS
    photo = cp[PHOTO_SECTION]
    assert photo["ConfigFile"] == "Golmok/photo.json"
    assert photo["PhotoFolder"] == "Screenshots/Golmok/photo"
    assert 1 <= int(photo["ScreenshotMultiplier"]) <= int(photo["MaxMultiplier"]) <= 8
    assert photo["PauseMode"] in {"GamePause", "TimeDilation"}


def test_ini_other_sections_unchanged():
    cp = parse_ue_ini(INI.read_text(encoding="utf-8-sig"))
    for section, keys in EXPECTED_KEYS.items():
        assert set(cp[section]) == keys, section
    zone = cp["/Script/Golmok.GolmokZoneSubsystem"]
    for key in WP09_ZONE_KEYS:
        assert key in zone, key
    # the Debug section keeps its own ScreenshotMultiplier (distinct from the photo one, design 12 #23)
    assert "ScreenshotMultiplier" in cp["/Script/Golmok.GolmokDebugSubsystem"]


# ---- (2) Build.cs ------------------------------------------------------------------------------------------


def test_build_cs_unchanged_since_wp09():
    text = _strip_comments(_read(SOURCE / "Golmok.Build.cs"))
    public_block = text[
        text.index("PublicDependencyModuleNames") : text.index("PrivateDependencyModuleNames")
    ]
    private_block = text[text.index("PrivateDependencyModuleNames") : text.index("Target.bBuildEditor")]
    editor_block = text[text.index("Target.bBuildEditor") :]
    assert set(re.findall(r'"(\w+)"', public_block)) == BUILD_CS_PUBLIC
    assert set(re.findall(r'"(\w+)"', private_block)) == BUILD_CS_PRIVATE
    assert set(re.findall(r'"(\w+)"', editor_block)) == BUILD_CS_EDITOR
    ini = INI.read_text(encoding="utf-8-sig")
    assert ini.count("+DirectoriesToAlwaysStageAsUFS=") == 2
    assert '+DirectoriesToAlwaysStageAsUFS=(Path="../Config/Golmok")' in ini  # stages photo.json


# ---- (3) logging -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("path", [*_photo_sources(), *TOUCHED_FILES], ids=lambda p: p.name)
def test_log_category_is_golmok_only(path: Path):
    code = _strip_comments(_read(path))
    assert "LogTemp" not in code, path
    categories = set(re.findall(r"UE_LOG\(\s*(\w+)\s*,", code))
    assert categories <= {"LogGolmok"}, (path.name, categories)
    if path == SUBSYSTEM_CPP:
        assert "LogGolmok" in categories, f"{path.name}: logs nothing?"


# ---- (4) automation tests ----------------------------------------------------------------------------------


def test_photo_automation_tests_declared():
    text = _read(PHOTO_TEST_CPP)
    assert "#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR" in text
    for name in PHOTO_AUTOMATION_TESTS:
        assert f'"{name}"' in text, name
    assert text.count("IMPLEMENT_SIMPLE_AUTOMATION_TEST(") == len(PHOTO_AUTOMATION_TESTS)
    assert "EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter" in text
    assert "FPlatformTime::Seconds()" in text and "GetTimeSeconds()" not in _strip_comments(text)


# ---- (5) plugins / widgets / Blueprintable -----------------------------------------------------------------


@pytest.mark.parametrize("path", _photo_sources(), ids=lambda p: p.name)
def test_no_plugins_widgets_or_blueprintable(path: Path):
    code = _strip_comments(_read(path))
    for banned in ("Cesium", "XGRIDS", "UUserWidget", "CreateWidget", "WBP_", ".uasset"):
        assert banned not in code, (path.name, banned)
    assert re.search(r"(?<!Not)Blueprintable", code) is None, path.name


def test_pawn_and_subsystem_are_not_blueprint_classes():
    pawn = _strip_comments(_read(PAWN_H))
    assert re.search(r"UCLASS\(\s*NotPlaceable\s*,\s*NotBlueprintable\s*\)", pawn), (
        "pawn: UCLASS(NotPlaceable, NotBlueprintable)"
    )
    subsystem = _strip_comments(_read(SUBSYSTEM_H))
    assert re.search(
        r"UCLASS\(\s*Config\s*=\s*Game\s*\)\s*class GOLMOK_API UGolmokPhotoModeSubsystem", subsystem
    )
    assert "UWorldSubsystem" in subsystem
    # only PauseMode is reflected (design section 0 #23)
    assert subsystem.count("UENUM(") == 1
    assert re.search(r"UENUM\(\)\s*enum class EGolmokPhotoPauseMode", subsystem)
    for plain in ("EGolmokPhotoState", "EGolmokPhotoParam"):
        assert re.search(r"(?<!UENUM\(\)\n)enum class " + plain, subsystem)
        assert "Count" not in re.search(r"enum class " + plain + r"[^{]*\{([^}]*)\}", subsystem).group(1)


# ---- (6) console commands ----------------------------------------------------------------------------------


def test_photo_console_commands_registered():
    code = _strip_comments(_read(SUBSYSTEM_CPP))
    names = re.findall(r'FAutoConsoleCommandWithWorldAndArgs\s+\w+\s*\(\s*TEXT\("([^"]+)"\)', code)
    assert sorted(names) == sorted(PHOTO_CONSOLE_COMMANDS)
    assert set(PHOTO_CONSOLE_COMMANDS) <= CONSOLE_COMMANDS
    # the WP-04/05/09 names all still register (the wp09 fixture asserts the set equals CONSOLE_COMMANDS)
    everything: list[str] = []
    for path in sorted(SOURCE.rglob("*.cpp")):
        everything += re.findall(
            r'FAutoConsoleCommandWithWorldAndArgs\s+\w+\s*\(\s*TEXT\("([^"]+)"\)',
            _strip_comments(_read(path)),
        )
    assert set(everything) == CONSOLE_COMMANDS
    for option in ("fov", "ev", "focus", "fstop", "roll", "dof", "char", "overlay", "mult"):
        assert f'TEXT("{option}")' in code, f"golmok.photo.set {option}"


# ---- (7) unity build ---------------------------------------------------------------------------------------


def test_anonymous_namespace_names_unique_and_photo_prefixed():
    owners: dict[str, set[str]] = {}
    for path in sorted(SOURCE.rglob("*.cpp")):
        for name in _unity_scope_definitions(_read(path)):
            owners.setdefault(name, set()).add(path.name)
    clashes = {name: sorted(files) for name, files in owners.items() if len(files) > 1}
    assert not clashes, f"anonymous-namespace / file-scope definitions in more than one file: {clashes}"
    photo_names = {name for name, files in owners.items() if files <= {SUBSYSTEM_CPP.name, PAWN_CPP.name}}
    assert photo_names, "the scanner saw nothing in Photo/"
    for expected in (
        "PhotoSubsystemFor",
        "PhotoParseToggle",
        "CmdPhoto",
        "CmdPhotoShoot",
        "CmdPhotoReset",
        "CmdPhotoSet",
    ):
        assert expected in photo_names, expected
    unprefixed = sorted(n for n in photo_names if "Photo" not in n)
    assert not unprefixed, f"Photo/ anonymous-namespace names must carry 'Photo': {unprefixed}"
    assert "namespace GolmokPhotoJson" in _read(SUBSYSTEM_CPP)


# ---- (8) C4458 ---------------------------------------------------------------------------------------------

_METHOD_SIG_RE = re.compile(
    r"^\s*(?:virtual\s+|static\s+|explicit\s+|inline\s+)*[\w:<>*&,\s]+?[\s*&]([A-Za-z_]\w*)\s*\((.*)\)"
)
_LOCAL_DECL_RE = re.compile(
    r"^\s*(?:const\s+)?(?:[\w:]+(?:<[^;=]*>)?)(?:\s*[*&])*\s+([A-Za-z_]\w*)\s*(?:=|;|\()"
)
_DEFINITION_RE = re.compile(r"^[^\s#/].*?\b([A-Z]\w+)::([A-Za-z_~]\w*)\s*\(")


def _members_by_class() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for header in (SUBSYSTEM_H, PAWN_H):
        for cls, d in _class_scan(_read(header)).items():
            out.setdefault(cls, set()).update(d["members"])
    return out


def _method_param_clashes(header: Path, members: dict[str, set[str]]) -> list[str]:
    """Every method (static or not) whose parameter carries a member name of its class."""
    out: list[str] = []
    cls: str | None = None
    depth = 0
    for line in _strip_comments(_read(header)).splitlines():
        code = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
        if m := re.match(r"^\s*(?:class|struct)\s+(?:GOLMOK_API\s+)?([A-Za-z_]\w*)\s*(?::|$)", code):
            cls = m.group(1)
        if (
            cls
            and (m := _METHOD_SIG_RE.match(code))
            and not code.lstrip().startswith(("UPROPERTY", "UCLASS", "UENUM", "GENERATED"))
        ):
            names = {_param_name(p) for p in _split_params(m.group(2))}
            for name in sorted(n for n in names if n and n in members.get(cls, set())):
                out.append(f"{cls}::{m.group(1)}({name})")
        depth += code.count("{") - code.count("}")
        if depth == 0 and code.strip().startswith("};"):
            cls = None
    return out


_C4458_METHOD_FIXTURE = """\
#pragma once

UCLASS()
class GOLMOK_API AThing : public AActor
{
	GENERATED_BODY()

public:
	void SetLook(const FRotator& Look);
	void SetRoll(float InRollDeg);
	static AThing* Find(UWorld* World, int32 State);

private:
	FRotator Look = FRotator::ZeroRotator;
	float RollDeg = 0.f;
	int32 State = 0;
};
"""


def test_c4458_scanners_catch_the_known_shapes(tmp_path: Path):
    header = tmp_path / "AThing.h"
    header.write_text(_C4458_METHOD_FIXTURE, encoding="utf-8")
    members = {"AThing": _class_scan(_C4458_METHOD_FIXTURE)["AThing"]["members"]}
    assert members["AThing"] >= {"Look", "RollDeg", "State"}
    assert _method_param_clashes(header, members) == ["AThing::SetLook(Look)", "AThing::Find(State)"]
    assert _LOCAL_DECL_RE.match("\tFRotator Look = GetLook();").group(1) == "Look"
    assert (
        _LOCAL_DECL_RE.match("\tconst UGolmokPhotoModeSubsystem* LocalOwner = Owner.Get();").group(1)
        == "LocalOwner"
    )
    assert _LOCAL_DECL_RE.match("\tState = EGolmokPhotoState::Active;") is None
    assert (
        _DEFINITION_RE.match("void AGolmokPhotoCameraPawn::Tick(float DeltaSeconds)").group(1)
        == "AGolmokPhotoCameraPawn"
    )


def test_static_and_method_params_do_not_shadow_members():
    members = _members_by_class()
    assert {
        "UGolmokPhotoModeSubsystem",
        "AGolmokPhotoCameraPawn",
        "FGolmokPhotoConfig",
        "FGolmokPhotoParamSpec",
    } <= set(members)
    assert {"State", "Config", "Values", "PhotoPawn", "SavedPawn"} <= members["UGolmokPhotoModeSubsystem"]
    assert {"Look", "RollDeg", "Owner", "Camera", "Sphere"} <= members["AGolmokPhotoCameraPawn"]
    for header in (SUBSYSTEM_H, PAWN_H):
        classes = _class_scan(_read(header))
        assert not _shadow_clashes(classes), header.name
        assert not _method_param_clashes(header, members), header.name
    # the scan is not vacuous: the design's static helpers are seen
    seen = {f"{c}::{fn}" for c, d in _class_scan(_read(SUBSYSTEM_H)).items() for fn in d["static_params"]}
    assert {"UGolmokPhotoModeSubsystem::Get", "UGolmokPhotoModeSubsystem::ParseParamName"} <= seen


def test_cpp_locals_do_not_shadow_members():
    """Loose: a local `Type Name =` / `Type Name;` inside a method of class X must not be a member of X."""
    members = _members_by_class()
    clashes: list[str] = []
    for path in (SUBSYSTEM_CPP, PAWN_CPP):
        cls: str | None = None
        for no, line in enumerate(_strip_comments(_read(path)).splitlines(), 1):
            if m := _DEFINITION_RE.match(line):
                cls = m.group(1)
                continue
            if cls is None or line.startswith("}"):
                cls = None if line.startswith("}") else cls
                continue
            if line.lstrip().startswith(("return ", "case ", "else", "delete ", "throw ")):
                continue
            if m := _LOCAL_DECL_RE.match(line):
                if m.group(1) in members.get(cls, set()):
                    clashes.append(f"{path.name}:{no}: {m.group(1)} ({cls})")
    assert not clashes, clashes
    # the design's canonical names (section 0 #23)
    pawn = _strip_comments(_read(PAWN_CPP))
    assert re.search(r"\bNewLook\b", pawn) and re.search(r"\bLocalOwner\b", pawn)
    for name in ("Fov", "Ev", "Focus", "Fstop", "Roll", "Look", "State", "Config"):
        assert (
            re.search(r"^\s*[\w:<>]+\s+" + name + r"\s*=", _strip_comments(_read(SUBSYSTEM_CPP)), re.M)
            is None
        ), name


def test_free_function_calls_are_qualified():
    """Member functions call the pure helpers as GolmokPhotoMath::X (design section 0 #23)."""
    for path in (SUBSYSTEM_CPP, PAWN_CPP):
        code = _strip_comments(_read(path))
        for fn in (
            "StepLinear",
            "StepGeometric",
            "StepTable",
            "Quantize",
            "Constrain",
            "ClampParam",
            "FormatPhotoMetaJson",
        ):
            assert re.search(r"(?<![\w:])" + fn + r"\(", code) is None, f"{path.name}: unqualified {fn}("
    assert "GolmokPhotoMath::Constrain(" in _read(PAWN_CPP)
    assert "GolmokPhotoMath::FormatPhotoMetaJson(" in _read(SUBSYSTEM_CPP)


# ---- (9)(10) input -----------------------------------------------------------------------------------------


def test_input_asset_names():
    subsystem = _read(SUBSYSTEM_CPP)
    for action in PHOTO_ACTIONS:
        assert f'TEXT("{action}")' in subsystem, action
    assert 'TEXT("IMC_GolmokPhoto")' in subsystem
    assert set(re.findall(r'TEXT\("(IA_GolmokPhoto\w*)"\)', subsystem)) >= set(PHOTO_ACTIONS)
    pc = _read(PC_CPP)
    assert 'TEXT("IA_GolmokPhotoToggle")' in pc and 'TEXT("IMC_GolmokPhotoToggle")' in pc
    assert "EKeys::P)" in pc and "EKeys::Gamepad_Special_Left)" in pc
    for path, names in EXISTING_ACTIONS.items():
        text = _read(path)
        for name in names:
            assert f'TEXT("{name}")' in text, (path.name, name)
    for line in DEBUG_MAPKEY_LINES:
        assert pc.count(line) == 1, line
    header = _read(PC_H)
    assert "static constexpr int32 PhotoTogglePriority = 2;" in header
    assert "void SetDebugKeysSuspended(bool bSuspended);" in header
    assert "bool IsDebugKeysSuspended() const" in header
    assert "static constexpr int32 PhotoMappingPriority = 3;" in _read(SUBSYSTEM_H)


def test_photo_actions_trigger_when_paused_and_consume_input():
    for path in (SUBSYSTEM_CPP, PC_CPP):
        code = _strip_comments(_read(path))
        assert "bTriggerWhenPaused = true" in code, path.name
        assert "bConsumeInput = true" in code, path.name


# ---- (11)(12) no possession, no zone registration ----------------------------------------------------------


@pytest.mark.parametrize("path", _photo_sources(), ids=lambda p: p.name)
def test_photo_never_possesses_or_registers_zones(path: Path):
    code = _strip_comments(_read(path))
    for banned in (
        "->Possess(",
        "RestartPlayer(",
        "RegisterZone(",
        "RequestLoad(",
        "RequestUnload(",
        "TActorIterator",
    ):
        assert banned not in code, (path.name, banned)


def test_photo_uses_the_view_target_only():
    code = _strip_comments(_read(SUBSYSTEM_CPP))
    assert "SetViewTargetWithBlend(" in code
    assert "AutoPossessPlayer = EAutoReceiveInput::Disabled" in _strip_comments(_read(PAWN_CPP))


def test_find_loaded_zone_at_is_read_only():
    header = _strip_comments(_read(ZONE_SUBSYSTEM_H))
    assert header.count("AGolmokZone* FindLoadedZoneAt(const FVector2D& LevelUEPointCm) const;") == 1
    body = _function_body(
        _strip_comments(_read(ZONE_SUBSYSTEM_CPP)), "UGolmokZoneSubsystem::FindLoadedZoneAt"
    )
    for banned in (
        "RegisterZone(",
        "RequestLoad(",
        "RequestUnload(",
        "SpawnDiscoveredZone(",
        "SpawnActor",
        "Destroy(",
        "->Load(",
        "Evaluate(",
    ):
        assert banned not in body, banned
    assert "ZoneWins(" in body and "IsLoaded()" in body and "FootprintContains(" in body


# ---- (13)-(16) touched files -------------------------------------------------------------------------------


def test_default_input_ini_keeps_the_debug_exec_bindings_cleared():
    assert "!DebugExecBindings=ClearArray" in INPUT_INI.read_text(encoding="utf-8-sig").splitlines()


def test_debug_subsystem_request_high_res_screenshot():
    header = _read(DEBUG_H)
    assert (
        "bool RequestHighResScreenshot(const FString& InAbsolutePathNoExt, int32 InMultiplier, "
        "FString& OutMessage, int32& OutEffectiveMultiplier);" in header
    )
    cpp = _read(DEBUG_CPP)
    for message in SCREENSHOT_MESSAGES:
        assert message in cpp, message
    code = _strip_comments(cpp)
    assert re.search(
        r"(bAccepted\s*=\s*View->TakeHighResScreenShot\(\)|if\s*\(\s*!View->TakeHighResScreenShot\(\))", code
    ), "the TakeHighResScreenShot() result must be checked (1x retry)"
    take = _function_body(code, "UGolmokDebugSubsystem::TakeScreenshot")
    assert "RequestHighResScreenshot(FullPath, ScreenshotMultiplier, OutMessage" in take
    for fn in ("UGolmokDebugSubsystem::StartPlayback", "UGolmokDebugSubsystem::StartRecording"):
        body = _function_body(code, fn)
        assert "UGolmokPhotoModeSubsystem::IsActiveIn(GetWorld())" in body, fn
        assert 'TEXT("photo mode is on (golmok.photo 0 first)")' in body, fn


def test_hud_comment_and_capture_guard():
    assert "never include it" not in _read(HUD_H)
    code = _strip_comments(_read(HUD_CPP))
    assert "IsHudSuppressed()" in code and "GetOverlayLines()" in code and "IsOverlayHidden()" in code


def test_time_of_day_shift_transition_start():
    assert "void ShiftTransitionStart(double DeltaSeconds);" in _read(TOD_H)
    body = _function_body(_strip_comments(_read(TOD_CPP)), "AGolmokTimeOfDay::ShiftTransitionStart")
    assert "TransitionStart += DeltaSeconds;" in body and "bTransitioning" in body


# ---- (17) runbook / (18) conventions -----------------------------------------------------------------------


def test_runbook_mentions_commands_files_tests_and_keys():
    if not RUNBOOK.is_file():
        pytest.skip(f"{RUNBOOK.name} is written by the runbook step of WP-12 (design section 9)")
    text = _read(RUNBOOK)
    missing = [m for m in RUNBOOK_MENTIONS if m not in text]
    assert not missing, missing


def test_convention_folders_include_photo():
    assert "Photo" in CONVENTION_FOLDERS
    for header in _photo_sources():
        text = _read(header)
        assert text.lstrip().startswith("#pragma once") or header.suffix == ".cpp", header.name
    assert MATH_H.is_file() and PAWN_H.is_file() and SUBSYSTEM_H.is_file()
