"""WP-05: portal / lighting / debug integration checks that need no Unreal (design section 8-3).

- Golmok.Build.cs pulls in RHI (RHIGetGPUFrameCycles for the HUD's GPU ms).
- DefaultGame.ini has the five WP-05 sections with exactly the section 6 keys and sane values, plus the two
  packaging lines (Config/Golmok staged as UFS, /Game/Golmok/Zones always cooked).
- AGolmokGameMode sets PlayerControllerClass / HUDClass; Tests/ declares the eight automation tests.
- No compile dependency on plugins (Cesium / XGRIDS) in code; Debug/GolmokStatsMath.h stays pure.
- AGolmokPortal is an AActor (not an AGolmokZone) and no WP-05 folder calls RegisterZone (the
  UGolmokZoneSubsystem::Evaluate() pointer contract of WP-04).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from test_ue_stats_math import assert_pure_header
from zone_util import REPO

sys.path.insert(0, str(REPO / "tools" / "scripts"))
from check_repo import parse_ue_ini  # noqa: E402

UE = REPO / "unreal" / "Golmok"
SOURCE = UE / "Source" / "Golmok"
INI = UE / "Config" / "DefaultGame.ini"
WP05_FOLDERS = ("Portals", "Lighting", "Debug", "Player")

# docs/plan/WP-05 design section 6: every key of the five new sections
EXPECTED_KEYS = {
    "/Script/Golmok.GolmokTimeOfDay": {
        "TransitionSeconds",
        "PresetsFile",
        "InitialPreset",
        "InteriorPreset",
        "LightingActorTag",
    },
    "/Script/Golmok.GolmokPortal": {
        "InteriorStreamingMode",
        "DebounceSeconds",
        "UnloadDelaySeconds",
        "TriggerHeightCm",
        "CrossingHysteresisCm",
        "MinCrossingIntervalSeconds",
        "bStreamSublevel",
        "bSwitchLighting",
    },
    "/Script/Golmok.GolmokDebugSubsystem": {
        "StatsWindowSeconds",
        "StatsCapacity",
        "bSampleWhenHudHidden",
        "RecordHz",
        "PathFolder",
        "ScreenshotFolder",
        "ScreenshotMultiplier",
        "CollisionDebugMaterialPath",
        "bCollisionShowFlag",
        "CollisionRefreshSeconds",
        "HudTextRefreshSeconds",
        "bHudOnAtStart",
        "bHidePlayerDuringPlayback",
        "QuickPathName",
        "PlaybackFov",
    },
    "/Script/Golmok.GolmokHUD": {"HudScale", "MarginPx"},
    "/Script/Golmok.GolmokPlayerController": {"bDebugKeysEnabled", "DebugMappingPriority"},
}

AUTOMATION_TESTS = (
    "Golmok.Lighting.PresetsFile",
    "Golmok.Lighting.PresetApply",
    "Golmok.Debug.StatsMath",
    "Golmok.Debug.PathFormat",
    "Golmok.Debug.PathRoundTrip",
    "Golmok.Debug.HudStats",
    "Golmok.Portal.SpawnFromManifest",
    "Golmok.Portal.RoundTrip",
    "Golmok.Portal.PawnSwap",
    "Golmok.Portal.SharedInterior",
)


def _ini_text() -> str:
    return INI.read_text(encoding="utf-8-sig")


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def test_build_cs_has_rhi_for_gpu_frame_cycles():
    text = (SOURCE / "Golmok.Build.cs").read_text(encoding="utf-8")
    assert '"RHI"' in text
    assert "RHIGetGPUFrameCycles" in text  # the reason stays next to the dependency


def test_default_game_ini_has_the_wp05_sections_with_exactly_the_design_keys():
    cp = parse_ue_ini(_ini_text())
    for section, keys in EXPECTED_KEYS.items():
        assert cp.has_section(section), section
        assert set(cp[section]) == keys, f"{section}: keys differ from WP-05 design section 6"


def test_default_game_ini_values_are_sane():
    cp = parse_ue_ini(_ini_text())
    portal = cp["/Script/Golmok.GolmokPortal"]
    assert portal["InteriorStreamingMode"] in {"LevelInstance", "NamedStreamingLevel"}
    debounce, unload = float(portal["DebounceSeconds"]), float(portal["UnloadDelaySeconds"])
    assert unload > debounce > 0
    debug = cp["/Script/Golmok.GolmokDebugSubsystem"]
    assert int(debug["RecordHz"]) >= 1
    assert float(debug["StatsWindowSeconds"]) > 0
    assert debug["ScreenshotFolder"] == "Screenshots/Golmok"  # same tree as viewpoints.py
    tod = cp["/Script/Golmok.GolmokTimeOfDay"]
    assert float(tod["TransitionSeconds"]) >= 0


def test_default_game_ini_packaging_lines():
    text = _ini_text()
    assert text.count("+DirectoriesToAlwaysStageAsUFS=") == 2
    assert '+DirectoriesToAlwaysStageAsUFS=(Path="Golmok/Zones")' in text
    assert '+DirectoriesToAlwaysStageAsUFS=(Path="../Config/Golmok")' in text
    assert text.count("+DirectoriesToAlwaysCook=") == 1
    assert '+DirectoriesToAlwaysCook=(Path="/Game/Golmok/Zones")' in text


def test_game_mode_sets_player_controller_and_hud_classes():
    text = (SOURCE / "GolmokGameMode.cpp").read_text(encoding="utf-8")
    assert "PlayerControllerClass = AGolmokPlayerController::StaticClass()" in text
    assert "HUDClass = AGolmokHUD::StaticClass()" in text
    assert '#include "Debug/GolmokHUD.h"' in text
    assert '#include "Player/GolmokPlayerController.h"' in text


def test_automation_tests_are_declared_under_the_editor_guard():
    sources = {p.name: p.read_text(encoding="utf-8") for p in sorted((SOURCE / "Tests").glob("*.cpp"))}
    joined = "\n".join(sources.values())
    for name in AUTOMATION_TESTS:
        assert f'"{name}"' in joined, name
    for name, text in sources.items():
        if "IMPLEMENT_SIMPLE_AUTOMATION_TEST" in text:
            assert "#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR" in text, name


def test_no_plugin_compile_dependency_in_code():
    """DEVELOPMENT-PLAN section 7.5: no Cesium / XGRIDS includes or symbols (comments may mention them)."""
    for path in sorted(SOURCE.rglob("*")):
        if path.suffix not in {".h", ".cpp", ".cs"}:
            continue
        code = _strip_comments(path.read_text(encoding="utf-8"))
        assert "Cesium" not in code and "XGRIDS" not in code, path


def test_stats_math_header_is_pure():
    assert_pure_header(SOURCE / "Debug" / "GolmokStatsMath.h")


def test_debug_subsystem_samples_on_end_frame_with_gpu_switch():
    text = (SOURCE / "Debug" / "GolmokDebugSubsystem.cpp").read_text(encoding="utf-8")
    assert "GOLMOK_GPU_TIME_SOURCE" in text
    assert "OnEndFrame" in text


def test_wp05_folders_never_call_register_zone():
    """WP-04 Evaluate() keeps FGolmokZoneRecord* across Load(); nothing in WP-05 may reallocate Zones."""
    files: list[Path] = []
    for folder in WP05_FOLDERS:
        files.extend(sorted((SOURCE / folder).glob("*.h")))
        files.extend(sorted((SOURCE / folder).glob("*.cpp")))
    assert files
    for path in files:
        assert "RegisterZone(" not in path.read_text(encoding="utf-8"), path


def test_portal_is_an_actor_not_a_zone():
    text = (SOURCE / "Portals" / "GolmokPortal.h").read_text(encoding="utf-8")
    assert "class GOLMOK_API AGolmokPortal : public AActor" in text
    assert "public AGolmokZone" not in text
