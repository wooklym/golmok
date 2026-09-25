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
