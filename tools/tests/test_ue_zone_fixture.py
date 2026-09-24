"""WP-04: UE zone fixture, packaging config and C++ source conventions checkable without Unreal.

- Content/Golmok/Zones/z_synthetic_001/v1/{manifest,blockers}.json equal the WP-02 fixture, pass the schema.
- DefaultGame.ini stages Content/Golmok/Zones into packaged builds and configures UGolmokZoneSubsystem radii.
- Golmok.Build.cs pulls in Json/JsonUtilities; Geo/ and Zones/ headers follow the module conventions
  (#pragma once, GENERATED_BODY + *.generated.h for reflected types, module-root-relative includes).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
from zone_util import FIXTURE_ZONES, REPO

from golmok_tools.zone import manifest as zm
from golmok_tools.zone import schema

sys.path.insert(0, str(REPO / "tools" / "scripts"))
from check_repo import parse_ue_ini  # noqa: E402

UE = REPO / "unreal" / "Golmok"
CONTENT_ZONES = UE / "Content" / "Golmok" / "Zones"
UE_FIXTURE = CONTENT_ZONES / "z_synthetic_001" / "v1"
SOURCE = UE / "Source" / "Golmok"
ASSET_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_]*$")


def test_ue_fixture_is_the_wp02_fixture():
    for name in ("manifest.json", "blockers.json"):
        ue = (UE_FIXTURE / name).read_text(encoding="utf-8")
        ref = (FIXTURE_ZONES / "z_synthetic_001" / "v1" / name).read_text(encoding="utf-8")
        assert json.loads(ue) == json.loads(ref), (
            f"{name}: copy tools/tests/fixtures/zones/z_synthetic_001/v1/"
        )


def test_ue_fixture_passes_schema_and_semantics():
    path = UE_FIXTURE / "manifest.json"
    d = zm.load(path)
    assert schema.validate(d) == []
    rep = zm.check(d, path)  # also checks <zone_id>/v<version>/manifest.json folder layout
    assert rep.errors == [] and rep.warnings == []
    blockers = json.loads((UE_FIXTURE / "blockers.json").read_text(encoding="utf-8"))
    assert schema.validate_blockers(blockers) == []
    # Shape the runbook (docs/runbooks/pc-verify-wp04.md) relies on
    assert len(d["layers"]["visual"]["chunks"]) == 3
    assert d["layers"]["collision"]["uri"] == "collision.glb"
    assert d["layers"]["blockers"]["uri"] == "blockers.json"
    assert len(blockers["planes"]) == 1 and len(d["portals"]) == 1
    assert len(d["transform"]) == 16


def test_ue_fixture_asset_names_follow_spec_convention():
    """docs/spec/zone-manifest.md §5: SM_<chunk_id>, SM_<zone_id>_collision; ids become component names."""
    d = zm.load(UE_FIXTURE / "manifest.json")
    names = [f"SM_{c['id']}" for c in d["layers"]["visual"]["chunks"]] + [f"SM_{d['zone_id']}_collision"]
    for n in names:
        assert ASSET_NAME.match(n), n
    for c in d["layers"]["visual"]["chunks"]:
        lo, hi = c["bbox_enu"]
        assert all(a <= b for a, b in zip(lo, hi, strict=True))


def test_every_content_zone_folder_matches_manifest_id_and_version():
    manifests = sorted(CONTENT_ZONES.glob("*/v*/manifest.json"))
    assert manifests, "no zone manifests under Content/Golmok/Zones"
    for path in manifests:
        d = json.loads(path.read_text(encoding="utf-8"))
        assert path.parent.parent.name == d["zone_id"], path
        assert path.parent.name == f"v{d['version']}", path


def test_default_game_ini_stages_zone_manifests_and_configures_subsystem():
    text = (UE / "Config" / "DefaultGame.ini").read_text(encoding="utf-8-sig")
    cp = parse_ue_ini(text)
    packaging = cp["/Script/UnrealEd.ProjectPackagingSettings"]
    assert packaging.get("+DirectoriesToAlwaysStageAsUFS") == '(Path="Golmok/Zones")'
    zone = cp["/Script/Golmok.GolmokZoneSubsystem"]
    load_m, unload_m = float(zone["LoadRadiusM"]), float(zone["UnloadRadiusM"])
    assert 0 < load_m < unload_m, "hysteresis needs LoadRadiusM < UnloadRadiusM"
    assert float(zone["UpdateIntervalSeconds"]) >= 0.1, "never evaluate zones per frame (WP-04 checklist f)"


def test_build_cs_has_json_modules():
    text = (SOURCE / "Golmok.Build.cs").read_text(encoding="utf-8")
    assert '"Json"' in text and '"JsonUtilities"' in text
    assert "PublicIncludePaths.Add(ModuleDirectory)" in text  # module-root-relative includes


def _headers(*folders: str) -> list[Path]:
    out: list[Path] = []
    for f in folders:
        out.extend(sorted((SOURCE / f).glob("*.h")))
    return out


@pytest.mark.parametrize("header", _headers("Geo", "Zones"), ids=lambda p: p.name)
def test_wp04_header_conventions(header: Path):
    text = header.read_text(encoding="utf-8")
    assert text.lstrip().startswith("#pragma once"), header
    reflected = re.search(r"^\s*(UCLASS|USTRUCT|UENUM|UINTERFACE)\b", text, re.M) is not None
    includes = re.findall(r'^#include\s+"([^"]+)"', text, re.M)
    if reflected:
        assert "GENERATED_BODY()" in text or "GENERATED_USTRUCT_BODY()" in text, header
        assert includes and includes[-1] == f"{header.stem}.generated.h", f"{header}: *.generated.h last"
        assert re.search(r"\b(class|struct)\s+GOLMOK_API\s+\w+", text), f"{header}: needs GOLMOK_API"
    else:
        assert f"{header.stem}.generated.h" not in text, header
    for inc in includes:
        assert not inc.startswith(("../", "./")), f"{header}: use module-root-relative includes ({inc})"


@pytest.mark.parametrize(
    "source",
    sorted((SOURCE / "Geo").glob("*.cpp")) + sorted((SOURCE / "Zones").glob("*.cpp")),
    ids=lambda p: p.name,
)
def test_wp04_source_conventions(source: Path):
    text = source.read_text(encoding="utf-8")
    includes = re.findall(r'^#include\s+"([^"]+)"', text, re.M)
    assert includes and includes[0] == f"{source.parent.name}/{source.stem}.h", f"{source}: own header first"
    for inc in includes:
        assert not inc.startswith(("../", "./")), f"{source}: use module-root-relative includes ({inc})"
    assert "UE_LOG(LogTemp" not in text, f"{source}: use LogGolmok (WP-04 checklist d)"


def test_pure_geo_math_header_has_no_unreal_includes():
    header = SOURCE / "Geo" / "GolmokGeoMath.h"
    assert header.is_file(), "Geo/GolmokGeoMath.h (pure header-only math) missing"
    text = header.read_text(encoding="utf-8")
    quoted = re.findall(r'^#include\s+"([^"]+)"', text, re.M)
    angled = re.findall(r"^#include\s+<([^>]+)>", text, re.M)
    assert quoted == [], f"pure header must not include project/UE headers: {quoted}"
    assert set(angled) <= {"cmath", "array", "cstddef"}, angled
    assert "CoreMinimal" not in text and "UCLASS" not in text and "UE_LOG" not in text
