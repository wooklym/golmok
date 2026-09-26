"""WP-09: zone index / async load conventions checkable without Unreal (design section 8-1).

- DefaultGame.ini: the four discovery keys with sane ranges, bAsyncLoad=True (keys = UPROPERTY(Config) is
  covered by test_ue_zone_fixture.py::test_ini_keys_match_config_uproperties).
- Tests/GolmokZoneTest.cpp declares the five Golmok.Zone.* automation tests under the editor guard.
- Static proof of the Evaluate() stack contract (design section 4-4): the Evaluate() body never spawns,
  destroys, registers or requests; the timer runs DiscoverZones() before Evaluate(); DiscoverZones() never
  loads and never spawns / destroys inside a `for (... : Zones)` loop; every async completion is deferred to
  the next tick.
- Portals never call AGolmokZone::Load / Unload themselves; the preload is a next-tick timer.
- MSVC C4458: no static member function parameter is named like a member (Zones / Portals / Debug headers).
- Unity build: anonymous-namespace / file-scope names are unique across Zones / Portals / Debug .cpp files.
- Debug render-time source macro + hold rule; GolmokStatsMath.h stays pure; GolmokZoneIndex.h has no
  reflection.
- Golmok.Build.cs module set unchanged since WP-05; the two UFS staging lines unchanged.
- golmok.zone.list header prefix kept (columns are only added); golmok.zone.index registered; the console
  command set is the WP-04/05 one plus golmok.zone.index; spec section 6 has the in-game location paragraph;
  the GolmokPortalTest.cpp edit is exactly the documented four lines.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from test_lighting_presets import _unity_scope_definitions
from test_ue_stats_math import assert_pure_header
from zone_util import REPO

sys.path.insert(0, str(REPO / "tools" / "scripts"))
from check_repo import parse_ue_ini  # noqa: E402

UE = REPO / "unreal" / "Golmok"
SOURCE = UE / "Source" / "Golmok"
INI = UE / "Config" / "DefaultGame.ini"
ZONE_CPP = SOURCE / "Zones" / "GolmokZone.cpp"
ZONE_H = SOURCE / "Zones" / "GolmokZone.h"
SUBSYSTEM_CPP = SOURCE / "Zones" / "GolmokZoneSubsystem.cpp"
INDEX_H = SOURCE / "Zones" / "GolmokZoneIndex.h"
DEBUG_CPP = SOURCE / "Debug" / "GolmokDebugSubsystem.cpp"
STATS_MATH_H = SOURCE / "Debug" / "GolmokStatsMath.h"
ZONE_TEST_CPP = SOURCE / "Tests" / "GolmokZoneTest.cpp"
PORTAL_TEST_CPP = SOURCE / "Tests" / "GolmokPortalTest.cpp"
SPEC = REPO / "docs" / "spec" / "zone-manifest.md"
WP09_FOLDERS = ("Zones", "Portals", "Debug")

ZONE_AUTOMATION_TESTS = (
    "Golmok.Zone.IndexParse",
    "Golmok.Zone.IndexDiscover",
    "Golmok.Zone.AsyncLoad",
    "Golmok.Zone.AsyncCancel",
    "Golmok.Zone.InteriorNotBlocked",
)

# Design section 4-4: nothing on the Evaluate() stack may reallocate Zones or re-grab records.
EVALUATE_BANNED = (
    "SpawnActor",
    "FinishSpawning(",
    "DiscoverZones(",
    "Destroy(",
    "RegisterZone(",
    "UnregisterZone(",
    "RequestLoad(",
    "RequestUnload(",
)
DISCOVER_BANNED = ("->Load(", "->Unload(", "RequestLoad(", "RequestUnload(", "Evaluate(")
ZONES_LOOP_BANNED = ("Destroy(", "SpawnActor")

# The WP-04 / WP-05 console commands (brief: names must not change) plus the one WP-09 adds.
CONSOLE_COMMANDS = {
    "golmok.zone.list",
    "golmok.zone.load",
    "golmok.zone.unload",
    "golmok.zone.refresh",
    "golmok.zone.radius",
    "golmok.zone.index",  # WP-09
    "golmok.photo",  # WP-12
    "golmok.photo.shoot",
    "golmok.photo.reset",
    "golmok.photo.set",
    "golmok.portal",
    "golmok.tod",
    "golmok.hud",
    "golmok.collision",
    "golmok.path",
    "golmok.screenshot",
    "golmok.stats",
    "golmok.geo.selftest",
}

# Golmok.Build.cs as WP-05 left it (PC fix e446504): no new module for WP-09 (StreamableManager is in Engine).
BUILD_CS_PUBLIC = {"Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "Json", "JsonUtilities"}
BUILD_CS_PRIVATE = {"RHI", "RenderCore"}
BUILD_CS_EDITOR = {"UnrealEd"}


# ---- helpers: C++ text without comments, function bodies by brace matching ---------------------------

_LITERAL_OR_COMMENT_RE = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|/\*.*?\*/|//[^\n]*", re.S)
_LITERAL_RE = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_comments(text: str) -> str:
    """The code the compiler sees: comments removed, string / char literals kept (never start a comment)."""
    return _LITERAL_OR_COMMENT_RE.sub(lambda m: m.group(0) if m.group(0)[0] in "'\"" else "", text)


def _mask_literals(code: str) -> str:
    """Same length as `code`, with literal contents blanked so braces / parens inside them are not counted."""
    return _LITERAL_RE.sub(lambda m: m.group(0)[0] + " " * (len(m.group(0)) - 2) + m.group(0)[-1], code)


def _matching(masked: str, open_idx: int) -> int:
    """Index of the bracket closing the one at open_idx ('{' / '(' pairs), raising when unbalanced."""
    pairs = {"{": "}", "(": ")"}
    opener = masked[open_idx]
    closer = pairs[opener]
    depth = 0
    for i in range(open_idx, len(masked)):
        ch = masked[i]
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError(f"unbalanced {opener!r} at {open_idx}")


def _function_body(code: str, qualified_name: str) -> str:
    """Body (between the outer braces) of the single definition `... <qualified_name>(...) [const]\\n{`.

    Allman braces (repository convention): the `{` opens on its own line after the signature. `code` must be
    comment-stripped (see _strip_comments); a signature may span lines.
    """
    sig = re.compile(re.escape(qualified_name) + r"\s*\(", re.M)
    masked = _mask_literals(code)
    bodies: list[str] = []
    for m in sig.finditer(masked):
        # a call `Foo(` inside another body is skipped unless a `{` follows the closing paren
        close = _matching(masked, m.end() - 1)
        tail = masked[close + 1 :]
        head = re.match(r"\s*(?:const\s*)?(?:override\s*)?\n\s*\{", tail)
        if not head:
            continue
        open_idx = close + 1 + head.end() - 1
        bodies.append(code[open_idx + 1 : _matching(masked, open_idx)])
    assert len(bodies) == 1, f"{qualified_name}: {len(bodies)} definitions found (expected exactly one)"
    return bodies[0]


def _call_args(code: str, call: str) -> str:
    """Argument text of the single `<call>(` occurrence (paren matched)."""
    masked = _mask_literals(code)
    hits = [m.end() - 1 for m in re.finditer(re.escape(call) + r"\s*\(", masked)]
    assert len(hits) == 1, f"{call}: {len(hits)} occurrences (expected exactly one)"
    return code[hits[0] + 1 : _matching(masked, hits[0])]


def _zones_loop_bodies(body: str) -> list[str]:
    """Bodies of every `for (... : Zones)` block in body (nested loops are covered by their outer block)."""
    masked = _mask_literals(body)
    out: list[str] = []
    for m in re.finditer(r"for\s*\([^()]*:\s*Zones\s*\)", masked):
        open_idx = masked.index("{", m.end())
        out.append(body[open_idx + 1 : _matching(masked, open_idx)])
    return out


def _assert_none_of(where: str, body: str, tokens: tuple[str, ...]) -> None:
    hits = [t for t in tokens if t in body]
    assert not hits, f"{where}: forbidden token(s) {hits}"


def _assert_all_of(where: str, body: str, tokens: tuple[str, ...]) -> None:
    missing = [t for t in tokens if t not in body]
    assert not missing, f"{where}: missing token(s) {missing}"


# ---- helpers: C4458 scanner (class members vs static member function parameters) ----------------------

_CLASS_RE = re.compile(r"^\s*(?:class|struct)\s+(?:GOLMOK_API\s+)?([A-Za-z_]\w*)\s*(?::\s*[^;{]*)?$")
_STATIC_FN_RE = re.compile(
    r"^\s*static\s+(?!constexpr\b|const\b)[\w:<>*&\s]+?[\s*&]([A-Za-z_]\w*)\s*\((.*)\)"
)
_MEMBER_RE = re.compile(
    r"^\s*(?:static\s+)?(?:constexpr\s+|const\s+|mutable\s+)*[\w:]+(?:<[^;]*>)?(?:\s*[*&])*\s+([A-Za-z_]\w*)\s*(?:=|;|\{|\[)"
)
_METHOD_RE = re.compile(r"^\s*(?:virtual\s+|explicit\s+|inline\s+)*[\w:<>*&,\s]+?[\s*&]([A-Za-z_]\w*)\s*\(")
_SKIP_PREFIXES = (
    "#",
    "UPROPERTY",
    "UFUNCTION",
    "GENERATED",
    "public",
    "private",
    "protected",
    "using ",
    "return",
    "friend",
    "template",
)


def _split_params(text: str) -> list[str]:
    out: list[str] = []
    depth = 0
    cur = ""
    for ch in text:
        if ch in "<(":
            depth += 1
        elif ch in ">)":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def _param_name(param: str) -> str | None:
    m = re.search(r"([A-Za-z_]\w*)\s*(?:\[\])?$", param.split("=")[0].strip())
    return m.group(1) if m else None


def _class_scan(header_text: str) -> dict[str, dict]:
    """{class: {"members": names, "methods": names, "static_params": {fn: param names}}} per class / struct.

    Only lines directly inside a class body (one brace level below its `{`) are read, so locals of inline
    method bodies and nested classes' members never count for the outer class. Single-line signatures
    (repository convention).
    """
    lines = _strip_comments(header_text).splitlines()
    stack: list[tuple[str | None, int]] = []  # (class name or None for other blocks, depth inside it)
    pending: str | None = None
    depth = 0
    classes: dict[str, dict] = {}
    for line in lines:
        code = _LITERAL_RE.sub('""', line)
        stripped = code.strip()
        top = stack[-1] if stack else None
        if top and top[0] and depth == top[1] and stripped and not stripped.startswith(_SKIP_PREFIXES):
            cls = classes.setdefault(top[0], {"members": set(), "methods": set(), "static_params": {}})
            if m := _STATIC_FN_RE.match(code):
                names = {_param_name(p) for p in _split_params(m.group(2))}
                cls["static_params"][m.group(1)] = {n for n in names if n}
            elif m := _MEMBER_RE.match(code):
                cls["members"].add(m.group(1))
            elif m := _METHOD_RE.match(code):
                cls["methods"].add(m.group(1))
        if m := _CLASS_RE.match(code):
            pending = m.group(1)
        opens, closes = code.count("{"), code.count("}")
        if opens and pending:
            stack.append((pending, depth + 1))
            pending = None
        elif opens and not closes:
            stack.append((None, depth + 1))
        depth += opens - closes
        while stack and depth < stack[-1][1]:
            stack.pop()
    return classes


def _shadow_clashes(classes: dict[str, dict]) -> list[str]:
    out: list[str] = []
    for cname, c in classes.items():
        names = c["members"] | c["methods"]
        for fn, params in c["static_params"].items():
            for p in sorted(params & names):
                out.append(f"{cname}::{fn}({p})")
    return out


_C4458_FIXTURE = """\
#pragma once

class UWorld;

UCLASS()
class GOLMOK_API AThing : public AActor
{
	GENERATED_BODY()

public:
	/** portals[].id */
	UPROPERTY(VisibleAnywhere)
	FString PortalId;

	bool IsHolding() const
	{
		return State == 1; // { not a member
	}

	static AThing* Find(UWorld* World, const FString& PortalId); // C4458 on MSVC
	static bool Any(UWorld* W, TFunctionRef<bool(const AThing&, int)> Pred, const FString& InPortalId = "");
	static constexpr int MaxRows = 4;

private:
	struct Inner
	{
		int Depth = 0;
		static void Use(int Depth);
	};
	int State = 0;
	TMap<FString, int> Rows;
};
"""


# ---- tests --------------------------------------------------------------------------------------------


def test_ini_keys_and_values():
    cp = parse_ue_ini(INI.read_text(encoding="utf-8-sig"))
    zone = cp["/Script/Golmok.GolmokZoneSubsystem"]
    for key in ("bDiscoverFromIndex", "DiscoveryIntervalSeconds", "DespawnDistanceM", "DespawnGraceSeconds"):
        assert key in zone, key
    assert zone["bDiscoverFromIndex"] in {"True", "False"}
    update_s = float(zone["UpdateIntervalSeconds"])
    assert float(zone["DiscoveryIntervalSeconds"]) >= update_s, (
        "discovery runs inside the Evaluate timer, never faster"
    )
    despawn_m, unload_m = float(zone["DespawnDistanceM"]), float(zone["UnloadRadiusM"])
    assert despawn_m == 0 or despawn_m >= unload_m, (
        "0 = 2 x UnloadRadiusM; never despawn inside the unload radius"
    )
    assert float(zone["DespawnGraceSeconds"]) >= 0
    actor = cp["/Script/Golmok.GolmokZone"]
    assert actor["bAsyncLoad"] == "True"  # spec default changed by WP-09 (FStreamableManager path)


def test_automation_tests_declared():
    text = _read(ZONE_TEST_CPP)
    assert "#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR" in text
    for name in ZONE_AUTOMATION_TESTS:
        assert f'"{name}"' in text, name
    assert text.count("IMPLEMENT_SIMPLE_AUTOMATION_TEST(") == len(ZONE_AUTOMATION_TESTS)


def test_evaluate_body_never_spawns_registers_or_destroys():
    """Design 4-4: Evaluate() holds FGolmokZoneRecord* into Zones across Load(): no Zones reallocation."""
    body = _function_body(_strip_comments(_read(SUBSYSTEM_CPP)), "UGolmokZoneSubsystem::Evaluate")
    assert "for (FGolmokZoneRecord& R : Zones)" in body  # the body really is the evaluation loop
    _assert_none_of("Evaluate()", body, EVALUATE_BANNED)


def test_timer_runs_discovery_before_evaluate():
    text = _read(SUBSYSTEM_CPP)
    code = _strip_comments(text)
    for name in ("UGolmokZoneSubsystem::OnEvaluateTimer", "CmdZoneRefresh"):
        body = _function_body(code, name)
        discover = body.find("DiscoverZones(")
        evaluate = re.search(r"\bEvaluate\(", body)
        assert discover >= 0 and evaluate, f"{name}: must call DiscoverZones() and Evaluate()"
        assert discover < evaluate.start(), f"{name}: DiscoverZones() must run before Evaluate()"
    assert "SetTimer(EvaluateTimer, this, &UGolmokZoneSubsystem::OnEvaluateTimer" in code
    assert "&UGolmokZoneSubsystem::Evaluate," not in code, "the timer must go through OnEvaluateTimer"


def test_discover_never_loads_and_destroys_outside_zones_loop():
    body = _function_body(_strip_comments(_read(SUBSYSTEM_CPP)), "UGolmokZoneSubsystem::DiscoverZones")
    _assert_none_of("DiscoverZones()", body, DISCOVER_BANNED)
    loops = _zones_loop_bodies(body)
    assert loops, "DiscoverZones() collects candidates from Zones"
    for loop in loops:
        _assert_none_of("DiscoverZones() `for (... : Zones)` block", loop, ZONES_LOOP_BANNED)


def test_async_completion_is_always_deferred():
    """Design 5: the streamable completion only schedules FinishAsyncLoad() for the next tick."""
    code = _strip_comments(_read(ZONE_CPP))
    load_async = _function_body(code, "AGolmokZone::LoadAsync")
    named = re.search(r"FStreamableDelegate\s+\w+\s*=\s*FStreamableDelegate::CreateWeakLambda", load_async)
    assert named, "LoadAsync: bind a named FStreamableDelegate (classic RequestAsyncLoad overload)"
    assert named.start() < load_async.index("RequestAsyncLoad(")
    args = _call_args(load_async, "RequestAsyncLoad")
    assert "CreateWeakLambda" not in args and "CreateUObject" not in args
    on_complete = _function_body(code, "AGolmokZone::OnStreamableComplete")
    for name, body in (("LoadAsync", load_async), ("OnStreamableComplete", on_complete)):
        assert "FinishAsyncLoad(" not in body, f"{name}: FinishAsyncLoad() must only be bound, never called"
    _assert_all_of(
        "OnStreamableComplete",
        on_complete,
        ("AsyncSerial", "SetTimerForNextTick", "AsyncFinishTimer =", "&AGolmokZone::FinishAsyncLoad"),
    )
    finish = _function_body(code, "AGolmokZone::FinishAsyncLoad")
    _assert_all_of("FinishAsyncLoad", finish, ("PendingFinishSerial", "NoteAsyncFinish("))
    _assert_none_of("FinishAsyncLoad", finish, ("RegisterZone(", "RequestLoad(", "SpawnActor<AGolmokZone"))
    cancel = _function_body(code, "AGolmokZone::CancelAsyncLoad")
    _assert_all_of("CancelAsyncLoad", cancel, ("ClearTimer(AsyncFinishTimer)", "CancelHandle()"))
    acquire = _function_body(code, "AGolmokZone::AcquireMeshAsset")
    assert "DoesPackageExist(" in acquire
    # enum: Loading appended after Failed (uint8 values of the WP-04 states unchanged)
    header = _strip_comments(_read(ZONE_H))
    enum = re.search(r"enum class EGolmokZoneState\s*:\s*uint8\s*\{([^}]*)\}", header)
    assert enum
    states = re.findall(r"\b([A-Z]\w*)\b", enum.group(1))
    assert states == ["Unloaded", "Loaded", "Failed", "Loading"], states


def test_portals_never_load_zones_directly():
    """Portals go through RequestLoad / RequestUnload(Source = Portal); the preload is a next-tick timer."""
    sources = sorted((SOURCE / "Portals").glob("*.cpp"))
    assert sources
    for path in sources:
        _assert_none_of(path.name, _strip_comments(_read(path)), ("->Load(", "->Unload(", "RegisterZone("))
    portal = _strip_comments(_read(SOURCE / "Portals" / "GolmokPortal.cpp"))
    assert re.search(r"SetTimerForNextTick\(\s*this,\s*&AGolmokPortal::PreloadInterior\s*\)", portal)
    assert re.search(r"(?<![:\w])PreloadInterior\(\)", portal) is None, "PreloadInterior() is only ever bound"


def test_static_member_params_do_not_shadow_members():
    """MSVC C4458 (warning as error): a static member function parameter named like a member of its class."""
    fixture = _class_scan(_C4458_FIXTURE)
    assert fixture["AThing"]["members"] >= {"PortalId", "State", "Rows", "MaxRows"}
    assert fixture["AThing"]["methods"] == {"IsHolding"}
    assert fixture["AThing"]["static_params"] == {
        "Find": {"World", "PortalId"},
        "Any": {"W", "Pred", "InPortalId"},
    }
    assert fixture["Inner"]["static_params"] == {"Use": {"Depth"}}
    assert _shadow_clashes(fixture) == ["AThing::Find(PortalId)", "Inner::Use(Depth)"]

    headers = [p for folder in WP09_FOLDERS for p in sorted((SOURCE / folder).glob("*.h"))]
    assert headers
    clashes: dict[str, list[str]] = {}
    seen: set[str] = set()
    for path in headers:
        classes = _class_scan(_read(path))
        seen.update(f"{c}::{fn}" for c, d in classes.items() for fn in d["static_params"])
        if found := _shadow_clashes(classes):
            clashes[path.name] = found
    assert not clashes, f"static member function parameters hide members (C4458): {clashes}"
    # the scan is not vacuous: the WP-09 / WP-05 static helpers with In* parameters are seen
    for expected in (
        "FGolmokZoneIndex::ParseZonesText",
        "AGolmokPortal::FindPortal",
        "UGolmokZoneSubsystem::ZoneWins",
    ):
        assert expected in seen, expected


def test_anonymous_namespace_names_unique_across_zones_portals_debug():
    """Unity build: every unnamed namespace of the module is one namespace (test_lighting_presets scanner)."""
    owners: dict[str, set[str]] = {}
    for folder in WP09_FOLDERS:
        for path in sorted((SOURCE / folder).glob("*.cpp")):
            for name in _unity_scope_definitions(_read(path)):
                owners.setdefault(name, set()).add(path.name)
    clashes = {name: sorted(files) for name, files in owners.items() if len(files) > 1}
    assert not clashes, f"anonymous-namespace / file-scope definitions in more than one file: {clashes}"
    assert owners.get("GCmdZoneIndex") == {"GolmokZoneSubsystem.cpp"}  # the WP-09 command object was scanned
    assert any(
        files == {"GolmokZoneIndex.cpp"} for name, files in owners.items() if name.startswith("IndexJson")
    )


def test_debug_render_source_macro_and_hold_rule():
    cpp = _read(DEBUG_CPP)
    assert re.search(r"^#define GOLMOK_RENDER_TIME_SOURCE [012]$", cpp, re.M)
    for token in (
        "GOLMOK_GPU_TIME_SOURCE",
        "OnBeginFrame",
        "OnEndFrame",
        "HoldLastPositive",
        "DescribeRenderSource",
    ):
        assert token in cpp, token
    header = _read(STATS_MATH_H)
    assert "struct HeldValue" in header and "HoldLastPositive" in header
    assert_pure_header(STATS_MATH_H)


def test_zone_index_header_is_plain():
    text = _strip_comments(_read(INDEX_H))  # the doc comment may say "no UCLASS"; the code may not use it
    for banned in ("UCLASS", "USTRUCT", "UENUM", ".generated.h"):
        assert banned not in text, banned
    assert "class GOLMOK_API FGolmokZoneIndex" in text
    assert re.search(r"using FReadFile = TFunction<bool\(", text), "injectable file reader (design 3-2)"
    assert "NumFileReads()" in text


def test_build_cs_and_staging_unchanged():
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
    assert '+DirectoriesToAlwaysStageAsUFS=(Path="Golmok/Zones")' in ini  # covers index/ and cells/
    assert '+DirectoriesToAlwaysStageAsUFS=(Path="../Config/Golmok")' in ini


def test_describe_zones_header_prefix_kept():
    """golmok.zone.list / HUD parsers read the header line; WP-09 may only append columns after it."""
    code = _strip_comments(_read(SUBSYSTEM_CPP))
    assert '"%d zones (load < %.0f m, unload > %.0f m), %d basemap actors tagged' in code
    assert 'TEXT("golmok.zone.index")' in code
    names: list[str] = []
    definitions = 0
    for path in sorted(SOURCE.rglob("*.cpp")):
        cpp = _strip_comments(_read(path))
        definitions += cpp.count("FAutoConsoleCommandWithWorldAndArgs")
        names.extend(re.findall(r'FAutoConsoleCommandWithWorldAndArgs\s+\w+\s*\(\s*TEXT\("([^"]+)"\)', cpp))
    assert set(names) == CONSOLE_COMMANDS, sorted(set(names) ^ CONSOLE_COMMANDS)
    assert len(names) == len(CONSOLE_COMMANDS) == definitions, "one registration object per command"


def test_spec_has_in_game_location():
    text = SPEC.read_text(encoding="utf-8")
    assert "게임 내 위치" in text
    assert "Content/Golmok/Zones/index/zones.json" in text
    assert "index/cells/16_<x>_<y>.json" in text


def test_wp05_portal_test_edit_is_the_documented_one():
    text = _read(PORTAL_TEST_CPP)
    assert text.count("Zone->bAsyncLoad = false;") == 1
    assert text.count("StreamInTimeoutSeconds = 5.0") == 3
    assert "StreamInTimeoutSeconds = 2.0" not in text


# ---- review fixes (round 1): portal cycle state, retire of loaded twins, runbook expectations -------------

PORTAL_CPP = SOURCE / "Portals" / "GolmokPortal.cpp"
PORTAL_H = SOURCE / "Portals" / "GolmokPortal.h"
LEVEL_STREAMING_CPP = SOURCE / "Portals" / "GolmokLevelStreaming.cpp"
RUNBOOK = REPO / "docs" / "runbooks" / "pc-verify-wp09.md"
DESIGN = REPO / "docs" / "plan" / "WP-09-ue-zone-index-async.md"
ZONE_TEST_COPY = "unreal/Golmok/Content/Golmok/Maps/L_ZoneTest09"
INTERIOR_SUBLEVEL = "/Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior"


def _if_block(body: str, condition: str) -> str:
    """Body of the single `if (<condition>)` block in body (condition text matched literally)."""
    masked = _mask_literals(body)
    hits = [m.start() for m in re.finditer(r"if\s*\(" + re.escape(condition) + r"\)", masked)]
    assert len(hits) == 1, f"if ({condition}): {len(hits)} occurrences (expected exactly one)"
    open_idx = masked.index("{", hits[0])
    return body[open_idx + 1 : _matching(masked, open_idx)]


def _runbook_section(number: int) -> str:
    text = _read(RUNBOOK)
    start = text.index(f"\n## {number}. ")
    end = text.find("\n## ", start + 1)
    return text[start : end if end >= 0 else len(text)]


def test_portal_reentry_after_preload_shortcut_resumes_activation():
    """Leaving reached without CompleteActivation (preload + early exit) must not turn Active on re-entry.

    EndPlayerOverlap / OnDebounceElapsed / LeaveInterior send a Pending portal that already requested the
    interior through State = Active + StartLeaving to return the pin; re-entering within the unload delay
    used to set Active with no StreamIn and a possibly Loading interior. `bActivated` tells a real activation
    from that shortcut.
    """
    header = _strip_comments(_read(PORTAL_H))
    assert re.search(r"^\s*bool bActivated = false;$", header, re.M)
    code = _strip_comments(_read(PORTAL_CPP))
    assert code.count("bActivated = true;") == 1
    assert "bActivated = true;" in _function_body(code, "AGolmokPortal::CompleteActivation")
    leaving = _if_block(
        _function_body(code, "AGolmokPortal::BeginPlayerOverlap"), "State == EGolmokPortalState::Leaving"
    )
    assert "bActivated" in leaving
    assert "State = EGolmokPortalState::Pending;" in leaving
    assert "&AGolmokPortal::OnDebounceElapsed" in leaving, "the Pending wait (IsInteriorReady) resumes"
    assert 'TEXT("re-entered trigger; unload cancelled")' in leaving  # the WP-05 path of an activated portal
    for fn in ("EndPlay", "OnUnloadDelayElapsed", "Activate"):
        assert "bActivated = false;" in _function_body(code, f"AGolmokPortal::{fn}"), fn


def test_portal_interior_request_stamp_is_per_cycle():
    """InteriorRequestSeconds (the 10 s Pending timeout) starts over with every cycle that clears the request.

    Activate() from Idle (golmok.portal enter) is a cycle start like BeginPlayerOverlap's Idle -> Pending; a
    stale stamp from an earlier visit made IsInteriorReady time out at once (Active while the interior was
    Loading).
    """
    code = _strip_comments(_read(PORTAL_CPP))
    masked = _mask_literals(code)
    clears = [m.end() for m in re.finditer(r"bInteriorRequested = false;", masked)]
    assert len(clears) >= 4
    for end in clears:
        block_end = masked.find("}", end)
        assert "InteriorRequestSeconds = 0.0;" in code[end:block_end], code[max(0, end - 200) : block_end]
    activate = _function_body(code, "AGolmokPortal::Activate")
    idle = _if_block(activate, "State == EGolmokPortalState::Idle")
    assert "InteriorRequestSeconds = 0.0;" in idle and "bInteriorRequested = false;" in idle
    assert activate.index("State == EGolmokPortalState::Idle") < activate.index("RequestInterior(")


def test_evaluate_unloads_retire_pending_twins():
    """A discovered zone whose placed twin registered is unloaded by Evaluate (then retired by DiscoverZones).

    bRetirePending keeps it out of the load rule (bManaged), but it must still be an unload reason; otherwise
    a Loaded / Loading discovered twin never becomes idle and is never destroyed.
    """
    code = _strip_comments(_read(SUBSYSTEM_CPP))
    evaluate = _function_body(code, "UGolmokZoneSubsystem::Evaluate")
    assert "!R.bRetirePending" in evaluate, "retire-pending records are never (re)loaded"
    masked = _mask_literals(evaluate)
    add = masked.index("ToUnload.Add(&R)")
    cond_start = masked.rindex("if (", 0, add)
    condition = evaluate[cond_start : _matching(masked, cond_start + 3) + 1]
    assert "bRetireNow" in condition, condition
    assert re.search(r"if \(R\.bRetirePending\)\s*\{[^}]*bRetireNow = ", evaluate)
    discover = _function_body(code, "UGolmokZoneSubsystem::DiscoverZones")
    twin = _if_block(discover, "bTwin")
    assert "EGolmokZoneState::Unloaded" in twin and "ToRetire.Add(" in twin
    assert "bIdle" not in twin, (
        "a pinned twin cannot be unpinned (FindZone resolves the id to the placed actor)"
    )
    test = _read(ZONE_TEST_CPP)
    assert (
        "placed twin" in test and "bRetire" not in test
    )  # the automation test drives it through the public API


_ROW_HEAD_RE = re.compile(
    r"(?P<id>z_\w+)(?P<idpad> +)v(?P<ver>\d+)(?P<verpad> +)prio (?P<prio>\d+)(?P<priopad> +)(?=[a-zA-Z])"
)
_ROW_DIST_RE = re.compile(
    r"(?P<state>loaded|unloaded|loading|FAILED)(?P<statepad> +)dist (?P<field>[ >=]*[0-9][0-9.x]*) m"
)


def test_runbook_zone_list_rows_match_describe_zones_format():
    """golmok.zone.list rows quoted in the runbook follow DescribeZones' Printf and Evaluate's `>=` rule.

    `  %-28s v%-3d prio %-4d %-9s dist %s%8.1f m…` with `%s` = `>=` or two spaces; `>=` = only the bounds
    distance was measured: an unloaded zone farther than LoadRadiusM or a loaded one at / beyond UnloadRadiusM
    (ini defaults; the runbook's rows are taken with them or with the wider `golmok.zone.radius 300 400`,
    which flips no row).
    """
    code = _strip_comments(_read(SUBSYSTEM_CPP))
    assert 'TEXT("  %-28s v%-3d prio %-4d %-9s dist %s%8.1f m' in code
    zone = parse_ue_ini(INI.read_text(encoding="utf-8-sig"))["/Script/Golmok.GolmokZoneSubsystem"]
    load_m, unload_m = float(zone["LoadRadiusM"]), float(zone["UnloadRadiusM"])
    text = _read(RUNBOOK)
    heads = list(_ROW_HEAD_RE.finditer(text))
    assert len(heads) >= 5
    for m in heads:
        assert len(m.group("id") + m.group("idpad")) == 29, m.group(0)
        assert len(m.group("ver") + m.group("verpad")) == 4, m.group(0)
        assert len(m.group("prio") + m.group("priopad")) == 5, m.group(0)
    rows = list(_ROW_DIST_RE.finditer(text))
    assert len(rows) >= 6
    for m in rows:
        row, field = m.group(0), m.group("field")
        assert len(m.group("state") + m.group("statepad")) == 10, row
        flag, number = field[:2], field[2:]
        assert flag in (">=", "  ") and len(number) == 8 and ">" not in number, row
        distance = float(number.strip().replace("x", "0"))
        lower_bound = distance > load_m if m.group("state") == "unloaded" else distance >= unload_m
        assert (flag == ">=") == lower_bound, row


def test_docs_quote_index_parse_longitudes_that_the_test_asserts():
    """Runbook section 3 / design section 8-2 name Golmok.Zone.IndexParse assertions by their literals."""
    test = _read(ZONE_TEST_CPP)
    runbook_line = next(
        line for line in _read(RUNBOOK).splitlines() if "`Golmok.Zone.IndexParse`의 `LonLatToCell" in line
    )
    design_row = next(
        line for line in _read(DESIGN).splitlines() if line.startswith("| `Golmok.Zone.IndexParse`")
    )
    for where, line in (("runbook", runbook_line), ("design 8-2", design_row)):
        lons = re.findall(r"\((12\d\.\d+), 37\.5620", line)
        assert len(lons) == 2, (where, line)
        for lon in lons:
            assert f"LonLatToCell({lon}, 37.5620, 16" in test, (where, lon)


def test_gitignore_covers_the_runbook_map_copy():
    """Runbook section 4 saves L_ZoneTest09 (placed zones removed) and says .gitignore covers it."""
    assert "(`.gitignore`에 사본 포함)" in _read(RUNBOOK)
    lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert f"{ZONE_TEST_COPY}*" in lines
    git = shutil.which("git")
    if git is None or not (REPO / ".git").exists():
        return
    for rel in (f"{ZONE_TEST_COPY}.umap", f"{ZONE_TEST_COPY}_BuiltData.uasset"):
        assert subprocess.run([git, "check-ignore", "-q", rel], cwd=REPO).returncode == 0, rel
    other = "unreal/Golmok/Content/Golmok/Maps/L_ZoneTest10.umap"  # the pattern covers only the WP-09 copy
    assert subprocess.run([git, "check-ignore", "-q", other], cwd=REPO).returncode == 1


def test_runbook_portal_exit_lines_match_the_code():
    """PIE end skips the next-tick unload (world torn down); an early exit never streamed the sublevel in."""
    code = _strip_comments(_read(PORTAL_CPP))
    end_play = _function_body(code, "AGolmokPortal::EndPlay")
    assert "Reason != EEndPlayReason::EndPlayInEditor" in end_play
    scheduled = _if_block(end_play, "bWorldAlive && Subsystem && Subsystem->FindZone(TargetZoneId)")
    assert '"; zone unload scheduled"' in scheduled and "SetTimerForNextTick" in scheduled
    calls = re.findall(r"(?<![:\w])StreamIn\(", code)
    assert len(calls) == 1, "CompleteActivation is the only StreamIn caller"
    assert "StreamIn(" in _function_body(code, "AGolmokPortal::CompleteActivation")
    assert 'TEXT("sublevel %s was not streamed")' in _strip_comments(_read(LEVEL_STREAMING_CPP))

    pie_end = _runbook_section(10)
    in_room = next(line for line in pie_end.splitlines() if "**방 안(오버레이 on)에서 종료**" in line)
    assert "`Portal door_1: end play while active -> sublevel out`" in in_room
    assert "sublevel out; zone unload scheduled" not in in_room
    assert re.search(r"^\s*LogGolmok: Portal door_1: end play while active -> sublevel out$", pie_end, re.M)
    pending = next(
        line for line in pie_end.splitlines() if "`Portal door_1: end play while pending -> " in line
    )
    assert "was not streamed`" in pending and "zone unload scheduled" not in pending
    # the scheduled unload + `gone ->` belong to the optional in-PIE exterior unload (world alive)
    mid_pie = next(
        line
        for line in pie_end.splitlines()
        if "golmok.zone.unload z_synthetic_001`" in line and "gone ->" in line
    )
    assert "sublevel out; zone unload scheduled" in mid_pie

    early = _runbook_section(8)
    lines = [line.strip() for line in early.splitlines() if "load cancelled); sublevel" in line]
    assert lines, "section 8 quotes the early-exit line"
    for line in lines:
        assert line.endswith(f"; sublevel {INTERIOR_SUBLEVEL} was not streamed"), line
