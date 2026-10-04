"""WP-16a weather (docs/plan/WP-16-weather.md "16a 설계 (확정)" sections 1, 7, 13-15): static checks.

- Source/Golmok/Weather/ holds exactly the design section 1 files; named namespaces only (no anonymous
  namespace, no file-scope `static`), LogGolmok, and Niagara headers only in GolmokWeatherRainFx.cpp.
- The hook blocks are exactly the section 15 text (Golmok.Build.cs; DefaultGame.ini: one contiguous block
  somewhere after the WP-19 block) and Golmok.uproject (parsed JSON) lists
  {"Name": "Niagara", "Enabled": true} as a new element before AndroidFileServer.
- AGolmokTimeOfDay::ComposeTarget applies the weather before the interior overlay (section 5-3).
- The three automation tests are declared under the editor guard; the HUD line comes from a provider (Debug/
  untouched); the photo meta carries "weather"; Golmok.Weather.Config holds every shared error message.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from test_ue_config_weather import ERROR_CASES

REPO = Path(__file__).resolve().parents[2]
UE = REPO / "unreal" / "Golmok"
SOURCE = UE / "Source" / "Golmok"
WEATHER = SOURCE / "Weather"
TEST_CPP = SOURCE / "Tests" / "GolmokWeatherTest.cpp"
SUBSYSTEM_CPP = WEATHER / "GolmokWeatherSubsystem.cpp"
RAIN_FX_CPP = WEATHER / "GolmokWeatherRainFx.cpp"
TOD_CPP = SOURCE / "Lighting" / "GolmokTimeOfDay.cpp"
SAVE_CPP = SOURCE / "Save" / "GolmokSaveSubsystem.cpp"

WEATHER_FILES = {
    "GolmokWeatherMath.h",
    "GolmokWeatherConfig.h",
    "GolmokWeatherConfig.cpp",
    "GolmokWeatherSubsystem.h",
    "GolmokWeatherSubsystem.cpp",
    "GolmokWeatherRainFx.h",
    "GolmokWeatherRainFx.cpp",
}
WEATHER_AUTOMATION_TESTS = ("Golmok.Weather.Config", "Golmok.Weather.Lighting", "Golmok.Weather.Runtime")
BUILD_CS_HOOK = (
    "\t\t// [WP-16 hook] Niagara: rain particles (Weather/GolmokWeatherRainFx.cpp only)\n"
    '\t\tPrivateDependencyModuleNames.Add("Niagara");\n'
    "\t\t// [/WP-16 hook]\n"
)
INI_HOOK = (
    "; [WP-16 hook] weather MPC / Niagara system are referenced only from weather.json\n"
    "[/Script/UnrealEd.ProjectPackagingSettings]\n"
    '+DirectoriesToAlwaysCook=(Path="/Game/Golmok/Weather")\n'
)
# Allowed: static_assert, and function-local statics (two tabs or more of indentation).
FILE_SCOPE_STATIC = re.compile(r"^\t?static\b(?!_assert)", re.M)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def test_weather_folder_has_the_design_files():
    assert {p.name for p in WEATHER.iterdir() if p.is_file()} == WEATHER_FILES


def test_named_namespaces_and_no_file_scope_static():
    paths = [p for p in sorted(WEATHER.iterdir()) if p.name != "GolmokWeatherSubsystem.h"] + [TEST_CPP]
    for path in paths:
        code = _strip_comments(_read(path))
        assert not re.search(r"\bnamespace\s*\{", code), f"{path.name}: anonymous namespace"
        assert not FILE_SCOPE_STATIC.search(code), f"{path.name}: file-scope static"
    # helpers live in the design's namespaces (unity build)
    assert "namespace GolmokWeather\n" in _read(SUBSYSTEM_CPP)
    assert "namespace GolmokWeatherRainFx\n" in _read(RAIN_FX_CPP)
    assert "namespace GolmokWeatherMath\n" in _read(WEATHER / "GolmokWeatherMath.h")
    assert "namespace GolmokWeatherTests\n" in _read(TEST_CPP)


def test_weather_logs_to_log_golmok():
    for path in sorted(WEATHER.glob("*.cpp")):
        logs = re.findall(r"UE_LOG\(\s*(\w+)", _read(path))
        assert set(logs) <= {"LogGolmok"}, (path.name, set(logs))


def test_niagara_headers_only_in_the_rain_fx_cpp():
    including = []
    for path in sorted(SOURCE.rglob("*")):
        if path.suffix in {".h", ".cpp"} and re.search(r'^#include\s+"Niagara', _read(path), re.M):
            including.append(path.relative_to(SOURCE).as_posix())
    assert including == ["Weather/GolmokWeatherRainFx.cpp"]
    header = _strip_comments(_read(WEATHER / "GolmokWeatherRainFx.h"))
    assert "UNiagara" not in header and "FNiagara" not in header


def test_build_cs_hook_block():
    text = _read(SOURCE / "Golmok.Build.cs")
    assert text.count(BUILD_CS_HOOK) == 1
    assert text.count("[WP-16 hook]") == 1 and text.count("[/WP-16 hook]") == 1
    private = text.index("PrivateDependencyModuleNames.AddRange")
    hook = text.index(BUILD_CS_HOOK)
    assert private < hook < text.index("// Editor-only automation tests") < text.index("Target.bBuildEditor")
    assert (
        text.count('"Niagara"') == 1 and '"NiagaraCore"' not in text
    )  # design 17 #2: add only if linking fails


def test_default_game_ini_hook_after_the_wp19_block():
    # R112-U6 (a): a later WP may append its block after this one; this one stays whole and after WP-19's.
    text = _read(UE / "Config" / "DefaultGame.ini")
    assert text.count(INI_HOOK) == 1  # contiguous: the three lines exactly, in order
    assert text.count("[WP-16 hook]") == 1
    assert text.count("; [WP-19 hook]") == 1
    assert text.index("; [WP-19 hook]") < text.index(INI_HOOK)
    at = text.index(INI_HOOK)
    assert at == 0 or text[at - 1] == "\n"  # starts on its own line


def test_uproject_enables_niagara_before_android_file_server():
    # R112-U6 (b): parsed JSON only, so a reformatted .uproject (editor save) keeps passing.
    project = json.loads(_read(UE / "Golmok.uproject"))
    plugins = project["Plugins"]
    niagara = [p for p in plugins if p.get("Name") == "Niagara"]
    assert niagara == [{"Name": "Niagara", "Enabled": True}]
    names = [p["Name"] for p in plugins]
    assert names.index("Niagara") == names.index("AndroidFileServer") - 1
    assert project["Modules"][0]["AdditionalDependencies"] == [
        "Engine",
        "EnhancedInput",
    ]  # unchanged (design 7-1)


def test_compose_target_applies_weather_before_the_interior_overlay():
    code = _strip_comments(_read(TOD_CPP))
    start = code.index("FGolmokLightingState AGolmokTimeOfDay::ComposeTarget() const")
    body = code[start : code.index("\n}\n", start)]
    assert "ApplyWeather(ComposeBase())" in body
    assert body.index("ApplyWeather(ComposeBase())") < body.index("IsInterior()")
    assert (
        "ComposeBase()" in code[code.index("bool AGolmokTimeOfDay::UpdateNight()") :][:600]
    )  # night: base only


def test_three_automation_tests_under_the_editor_guard():
    text = _read(TEST_CPP)
    names = re.findall(r'IMPLEMENT_SIMPLE_AUTOMATION_TEST\(\s*\w+\s*,\s*"(Golmok\.Weather\.\w+)"', text)
    assert tuple(names) == WEATHER_AUTOMATION_TESTS
    guard = text.index("#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR")
    assert text.index("IMPLEMENT_SIMPLE_AUTOMATION_TEST") > guard
    assert text.count("EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter") == 3
    # R112-U7: the travel reset is checked as the OnTraveled binding plus the reset itself, never by a
    # broadcast (it would also run UGolmokSaveSubsystem::OnTraveled); Traveled must still call ResetRainFx().
    code = _strip_comments(text)
    for needle in ("Travel->OnTraveled.IsBoundToObject(W)", "W->ResetRainFx();", "W->GetRainFxResetCount()"):
        assert needle in code, needle
    assert "OnTraveled.Broadcast(" not in code
    subsystem = _strip_comments(_read(SUBSYSTEM_CPP))
    start = subsystem.index("void UGolmokWeatherSubsystem::Traveled(")
    assert "ResetRainFx();" in subsystem[start : subsystem.index("\n}\n", start)]
    # R113-5: the PIE step only checks that a binding exists; keep its target and Restore's one reset
    # (R112-U8) static.
    assert "OnTraveled.AddUObject(this, &UGolmokWeatherSubsystem::Traveled)" in subsystem
    save = _strip_comments(_read(SAVE_CPP))
    start = save.index("Extras += RestoreWeather(Save->Weather);")
    assert "Weather->ResetRainFx();" in save[start : save.index("UnappliedCharacterId.Reset();", start)]
    for needle in (
        'TEXT("/Game/Golmok/Maps/L_Dev")',
        'TEXT("MPC_GolmokWeather missing - skipped")',
        'TEXT("NS_GolmokRain missing - skipped")',
        "FStartPIECommand(false)",
        "StepWeather(",
        "Photo->Enter(",
        'TEXT("NightUnaffected at %s")',  # R113: V-16 §3 records the minute from this Info line
    ):
        assert needle in text, needle


def test_every_shared_error_message_is_in_the_automation_test():
    text = _read(TEST_CPP)
    for _old, _new, message in ERROR_CASES:
        literal = message.replace("\\", "\\\\").replace('"', '\\"')
        assert f'TEXT("{literal}")' in text, message


def test_hud_line_comes_from_a_provider_and_debug_is_untouched():
    code = _strip_comments(_read(SUBSYSTEM_CPP))
    assert "AddExtraHudLineProvider(" in code and "RemoveExtraHudLineProvider(" in code
    # R112-U6 (c): no weather identifiers in Debug/ (the generic word "weather" in a comment is fine).
    for path in sorted((SOURCE / "Debug").glob("*")):
        text = _read(path)
        for needle in ("WP-16", "GolmokWeather"):
            assert needle not in text, (path.name, needle)


def test_console_command_is_registered_once():
    names = []
    for path in sorted(SOURCE.rglob("*.cpp")):
        names += re.findall(
            r'FAutoConsoleCommandWithWorldAndArgs\s+(\w+)\s*\(\s*TEXT\("golmok\.weather"\)', _read(path)
        )
    assert names == ["GCmdWeather"]


def test_photo_meta_has_the_weather_key():
    math_h = _read(SOURCE / "Photo" / "GolmokPhotoMath.h")
    assert '"  \\"weather\\": "' in math_h
    assert math_h.index('\\"preset\\"') < math_h.index('\\"weather\\"')
    assert "M.bHasWeather" in _read(SOURCE / "Photo" / "GolmokPhotoModeSubsystem.cpp")


def test_weather_setup_reads_its_paths_from_weather_json():
    text = _read(UE / "Content" / "Python" / "golmok" / "weather_setup.py")
    assert "MaterialParameterCollectionFactoryNew" in text and "wp.load_config" in text
    assert "/Game/Golmok/Weather" not in text  # paths come from weather.json only
