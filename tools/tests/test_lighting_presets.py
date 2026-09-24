"""WP-05: Config/Golmok/lighting_presets.json is the single source of the lighting presets (design 8-1).

Checks the file itself (schema, ranges, cycle, the interior overlay), the value regression against the WP-04
lighting.py constants, the pure parser's error cases, and that the C++ loader, lighting.py and DefaultGame.ini
refer to the same keys / file. Imports golmok.lighting_presets directly: it never imports `unreal`.
"""

from __future__ import annotations

import json
import re
import sys

import pytest
from zone_util import REPO

sys.path.insert(0, str(REPO / "tools" / "scripts"))
sys.path.insert(0, str(REPO / "unreal" / "Golmok" / "Content" / "Python"))
from check_repo import parse_ue_ini  # noqa: E402
from golmok import lighting_presets as lp  # noqa: E402

UE = REPO / "unreal" / "Golmok"
PRESETS_JSON = UE / "Config" / "Golmok" / "lighting_presets.json"
TIME_OF_DAY_CPP = UE / "Source" / "Golmok" / "Lighting" / "GolmokTimeOfDay.cpp"
LIGHTING_PY = UE / "Content" / "Python" / "golmok" / "lighting.py"
CYCLE = ["overcast_morning", "clear_noon", "golden_evening", "night"]
INTERIOR = "interior"

# Values of unreal/Golmok/Content/Python/golmok/lighting.py PRESETS at the WP-04 commit (regression guard).
WP04_PRESETS = {
    "overcast_morning": dict(pitch=-35.0, yaw=110.0, lux=2.5, kelvin=6500.0, sky=1.4, fog=0.035,
                             fog_height_falloff=0.15, volumetric=False, exposure_bias=0.3),
    "clear_noon": dict(pitch=-62.0, yaw=180.0, lux=10.0, kelvin=5600.0, sky=1.0, fog=0.015,
                       fog_height_falloff=0.2, volumetric=False, exposure_bias=0.0),
    "golden_evening": dict(pitch=-8.0, yaw=265.0, lux=4.0, kelvin=3600.0, sky=0.8, fog=0.05,
                           fog_height_falloff=0.12, volumetric=True, exposure_bias=0.5),
    "night": dict(pitch=15.0, yaw=0.0, lux=0.0, kelvin=4000.0, sky=0.15, fog=0.03,
                  fog_height_falloff=0.2, volumetric=True, exposure_bias=1.5),
}  # fmt: skip


@pytest.fixture(scope="module")
def raw() -> dict:
    assert PRESETS_JSON.is_file(), PRESETS_JSON
    return json.loads(PRESETS_JSON.read_text(encoding="utf-8"))


def in_range(key: str, value: float) -> bool:
    lo, hi = lp.RANGES[key]
    return lo <= value < hi if key in lp.HALF_OPEN else lo <= value <= hi


def test_presets_file_path_and_schema(raw):
    assert lp.PRESETS_FILE == str(PRESETS_JSON), "PRESETS_FILE must resolve relative to the module file"
    assert raw["schema_version"] == 1
    assert set(raw) == {"schema_version", "cycle", "presets"}


def test_cycle_presets_are_complete_and_in_range(raw):
    assert raw["cycle"] == CYCLE
    for name in CYCLE:
        p = raw["presets"][name]
        assert set(p) == set(lp.REQUIRED_KEYS), name
        assert isinstance(p["volumetric"], bool), name
        for key in lp.RANGES:
            assert isinstance(p[key], int | float) and not isinstance(p[key], bool), (name, key)
            assert in_range(key, p[key]), (name, key, p[key])


def test_preset_names_and_keys(raw):
    assert set(raw["presets"]) == set(CYCLE) | {INTERIOR}
    for name, p in raw["presets"].items():
        assert lp.NAME_RE.match(name), name
        assert set(p) <= set(lp.REQUIRED_KEYS), (name, set(p) - set(lp.REQUIRED_KEYS))


def test_interior_is_a_partial_overlay(raw):
    p = raw["presets"][INTERIOR]
    assert lp.is_partial(p)
    assert set(p) == {"fog", "fog_height_falloff", "volumetric", "exposure_bias"}
    assert p["fog"] == 0.0 and p["exposure_bias"] > 0
    assert INTERIOR not in raw["cycle"]
    for name in CYCLE:
        assert not lp.is_partial(raw["presets"][name])


def test_cycle_values_equal_wp04_lighting_py(raw):
    for name, expected in WP04_PRESETS.items():
        assert raw["presets"][name] == expected, name


def test_load_presets_returns_the_file_content(raw):
    cycle, presets = lp.load_presets()
    assert cycle == raw["cycle"] and presets == raw["presets"]
    assert lp.parse_presets(PRESETS_JSON.read_text(encoding="utf-8")) == (cycle, presets)
    assert lp.load_presets(str(PRESETS_JSON)) == (cycle, presets)


def _mutated(raw: dict, mutate) -> str:
    d = json.loads(json.dumps(raw))
    mutate(d)
    return json.dumps(d)


def _del_key(preset: str, key: str):
    return lambda d: d["presets"][preset].pop(key)


def _set(preset: str, key: str, value):
    return lambda d: d["presets"][preset].__setitem__(key, value)


def _top(key: str, value):
    return lambda d: d.__setitem__(key, value)


@pytest.mark.parametrize(
    ("mutate", "words"),
    [
        pytest.param(_del_key("clear_noon", "kelvin"), ["clear_noon", "kelvin"], id="missing-key"),
        pytest.param(_set("clear_noon", "kelvin", 100), ["clear_noon", "kelvin"], id="kelvin-out-of-range"),
        pytest.param(_set("night", "yaw", 360.0), ["night", "yaw"], id="yaw-half-open"),
        pytest.param(_set("night", "volumetric", 1), ["night", "volumetric"], id="volumetric-not-bool"),
        pytest.param(_top("schema_version", 2), ["schema_version"], id="schema-version-2"),
        pytest.param(
            _top("cycle", ["dawn", "clear_noon", "golden_evening", "night"]), ["dawn"], id="cycle-unknown"
        ),
        pytest.param(_top("cycle", CYCLE[:3]), ["cycle"], id="cycle-not-4"),
        pytest.param(_top("cycle", [CYCLE[0]] * 4), ["cycle"], id="cycle-duplicate"),
        pytest.param(_top("cycle", CYCLE[:3] + [INTERIOR]), [INTERIOR], id="interior-in-cycle"),
        pytest.param(_set(INTERIOR, "fog", 0.1), [INTERIOR, "fog"], id="interior-fog"),
        pytest.param(
            _set(INTERIOR, "exposure_bias", 0.0), [INTERIOR, "exposure_bias"], id="interior-exposure"
        ),
        pytest.param(lambda d: d["presets"].pop(INTERIOR), [INTERIOR], id="interior-missing"),
        pytest.param(_set("night", "haze", 1.0), ["night", "haze"], id="unknown-key"),
        pytest.param(_top("notes", "x"), ["notes"], id="unknown-top-level-key"),
        pytest.param(_set(INTERIOR, "lux", 1.0), [INTERIOR, "pitch"], id="sun-group-partial"),
        pytest.param(
            _del_key(INTERIOR, "fog_height_falloff"), [INTERIOR, "fog_height_falloff"], id="fog-group"
        ),
    ],
)
def test_parse_presets_errors_name_preset_and_key(raw, mutate, words):
    with pytest.raises(ValueError, match=r"^lighting_presets\.json: ") as info:
        lp.parse_presets(_mutated(raw, mutate))
    for word in words:
        assert word in str(info.value), str(info.value)


def test_parse_presets_rejects_non_object_root():
    with pytest.raises(ValueError):
        lp.parse_presets("[]")


def test_cpp_loader_uses_the_same_keys():
    text = TIME_OF_DAY_CPP.read_text(encoding="utf-8")
    for key in (*lp.REQUIRED_KEYS, "cycle", "presets", "schema_version"):
        assert f'TEXT("{key}")' in text, f'GolmokTimeOfDay.cpp: missing TEXT("{key}")'
    assert "FJsonSerializer::Deserialize" in text
    assert 'TEXT("interior")' in text  # the interior preset rules (fog == 0, exposure_bias > 0, not in cycle)


def test_lighting_py_reads_the_json_instead_of_hardcoding_values():
    text = LIGHTING_PY.read_text(encoding="utf-8")
    assert "PRESETS = {" not in text and "pitch=" not in text
    assert re.search(r"^from \.lighting_presets import ", text, re.M), (
        "lighting.py must import lighting_presets"
    )
    for name in ("def presets", "def cycle", "def reload", "def list_presets", "def apply"):
        assert name in text, name


def test_default_game_ini_points_at_the_presets_file(raw):
    cp = parse_ue_ini((UE / "Config" / "DefaultGame.ini").read_text(encoding="utf-8-sig"))
    section = "/Script/Golmok.GolmokTimeOfDay"
    if not cp.has_section(section):
        # Existence of the WP-05 sections is enforced by test_ue_wp05_fixture.py (integrator step).
        pytest.skip(f"[{section}] not in DefaultGame.ini yet (WP-05 design section 6)")
    tod = cp[section]
    assert tod["PresetsFile"] == "Golmok/lighting_presets.json"
    assert (UE / "Config" / tod["PresetsFile"]) == PRESETS_JSON
    assert tod["InteriorPreset"] in raw["presets"] and tod["InteriorPreset"] not in raw["cycle"]
    assert float(tod["TransitionSeconds"]) >= 0
    assert tod["LightingActorTag"] == "GolmokLighting"


def test_setup_dev_level_tags_the_lighting_actors():
    text = (UE / "Content" / "Python" / "golmok" / "setup_dev_level.py").read_text(encoding="utf-8")
    assert text.count('unreal.Name("GolmokLighting")') == 4  # Sun, SkyLight, HeightFog, PostProcess


# Definitions that a unity build (one translation unit per module chunk) sees in one scope: whatever sits at
# the top level of an unnamed `namespace { ... }` block (functions, console-command objects, constants) plus
# column-0 `static` file-scope definitions. Signatures are single-line here (repository convention).
_ANON_NAMESPACE_RE = re.compile(r"^namespace\s*(//.*)?$")
_ANON_DECL_RE = re.compile(r"^\t(?:static |inline )*[A-Za-z_][\w:<>*&, ]*?[\s*&]([A-Za-z_]\w*)\s*\(")
_ANON_CONST_RE = re.compile(r"^\t(?:static )?(?:constexpr |const )[\w:<>*&]+\s+([A-Za-z_]\w*)\s*(=|\[|;)")
_FILE_STATIC_RE = re.compile(r"^static\s+[\w:<>*&, ]*?[\s*&]([A-Za-z_]\w*)\s*(\(|=|\[|;)")


def _code_only(line: str) -> str:
    """The line without string / char literals and comments, so braces inside them are not counted."""
    stripped = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
    stripped = re.sub(r"'(?:\\.|[^'\\])*'", "''", stripped)
    stripped = re.sub(r"/\*.*?\*/", "", stripped)
    return stripped.split("//")[0]


def _unity_scope_definitions(text: str) -> list[str]:
    """Names defined at the top level of anonymous namespaces and as column-0 file-scope statics."""
    names: list[str] = []
    in_anon = False
    depth = 0
    for line in text.splitlines():
        code = _code_only(line)
        if not in_anon:
            if _ANON_NAMESPACE_RE.match(line):
                in_anon, depth = True, -1
            elif m := _FILE_STATIC_RE.match(code):
                names.append(m.group(1))
            continue
        if line.startswith("}"):
            in_anon = False
            continue
        if depth == 0 and not line.lstrip().startswith(("//", "*", "return", "using ")):
            if m := _ANON_DECL_RE.match(code) or _ANON_CONST_RE.match(code):
                names.append(m.group(1))
        depth += code.count("{") - code.count("}")
    return names


# Shapes the scanner must catch (a miss here is a future redefinition error that this test would not see).
_SCANNER_FIXTURE = """\
#include "X.h"

static const TCHAR* GFileScopeName = TEXT("x");
static void FileScopeHelper(const TArray<FString>& Args, UWorld* World)
{
\tUE_LOG(LogX, Log, TEXT("{"));
}

namespace // helpers
{
\tconstexpr int32 MaxRows = 4;
\tstatic const TCHAR* Msg = TEXT("{");
\tbool Fail(FString& Out, const FString& What) // comment { with brace
\t{
\t\tconst TCHAR C = '{';
\t\treturn false;
\t}

\tFAutoConsoleCommandWithWorldAndArgs GCmd(TEXT("x"), TEXT("y"),
\t\tFConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&FileScopeHelper));
} // namespace

namespace Named
{
\tbool NotCollected(int X)
\t{
\t\treturn X > 0;
\t}
} // namespace Named

void AThing::Method()
{
\tstatic const int32 NotFileScope = 1;
}
"""


def test_unity_scope_scanner_catches_the_known_shapes():
    assert _unity_scope_definitions(_SCANNER_FIXTURE) == [
        "GFileScopeName",
        "FileScopeHelper",
        "MaxRows",
        "Msg",
        "Fail",
        "GCmd",
    ]
    # The plain header and an unclosed brace in a literal before the function must not hide it either.
    plain = _SCANNER_FIXTURE.replace("namespace // helpers", "namespace")
    assert "Fail" in _unity_scope_definitions(plain)
    literal_brace = 'namespace\n{\n\tconst TCHAR* S = TEXT("{");\n\tbool Fail(int X)\n\t{\n\t}\n}\n'
    assert _unity_scope_definitions(literal_brace) == ["S", "Fail"]


def test_anonymous_namespace_helpers_do_not_repeat_across_module_files():
    # A unity build concatenates the module's .cpp files, where every unnamed namespace is the same namespace
    # and a second `bool Fail(FString&, const FString&)` body is a redefinition (MSVC C2084).
    # GolmokTimeOfDay.cpp keeps its JSON helpers in the named namespace GolmokLightingJson for that reason.
    owners: dict[str, set[str]] = {}
    for path in sorted((UE / "Source" / "Golmok").rglob("*.cpp")):
        for name in _unity_scope_definitions(path.read_text(encoding="utf-8")):
            owners.setdefault(name, set()).add(path.name)
    clashes = {name: sorted(files) for name, files in owners.items() if len(files) > 1}
    assert not clashes, f"anonymous-namespace / file-scope definitions in more than one file: {clashes}"
    tod = TIME_OF_DAY_CPP.read_text(encoding="utf-8")
    assert "namespace GolmokLightingJson" in tod
