"""WP-12: Config/Golmok/photo.json is the single source of the photo mode values (design section 8-3).

Pure (no compiler, no Unreal): the file's shape and the section 2-1 rules, the spec regression constants, the
key hints against the EKeys names the C++ maps, the C++ parser's key strings, the absence of range literals in
Photo/*.cpp, the ini pointer to the file and its staging, and the legal note the feature adds.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
from zone_util import REPO

sys.path.insert(0, str(REPO / "tools" / "scripts"))
from check_repo import parse_ue_ini  # noqa: E402

UE = REPO / "unreal" / "Golmok"
PHOTO_JSON = UE / "Config" / "Golmok" / "photo.json"
INI = UE / "Config" / "DefaultGame.ini"
PHOTO = UE / "Source" / "Golmok" / "Photo"
SUBSYSTEM_CPP = PHOTO / "GolmokPhotoModeSubsystem.cpp"
CONTROLLER_CPP = UE / "Source" / "Golmok" / "Player" / "GolmokPlayerController.cpp"
LEGAL_DOC = REPO / "docs" / "research" / "05-legal-policy.md"
PHOTO_SECTION = "/Script/Golmok.GolmokPhotoModeSubsystem"

PARAM_ORDER = ["fov", "ev", "focus", "fstop", "roll"]
SHAPES = ({"min", "max", "step"}, {"min", "max", "step_ratio"}, {"values"})
# design section 2-1 spec numbers: the pytest regression copy (photo.json is the only source the game reads)
SPEC_RANGES = {"fov": (20.0, 110.0), "ev": (-3.0, 3.0), "focus": (0.3, 50.0), "roll": (-15.0, 15.0)}
FSTOP_ENDS = (1.4, 16.0)
TOGGLES = {"dof", "character_hidden", "overlay_hidden"}
MAX_HINT_LINES, MAX_HINT_CHARS = 4, 72

# Display names of the hint lines -> EKeys names (design section 5-1). Words that are not keys are listed so
# that an unknown token fails the test instead of slipping through.
KEYBOARD_KEYS: dict[str, tuple[str, ...]] = {
    "P": ("P",),
    "Space": ("SpaceBar",),
    "R": ("R",),
    "F": ("F",),
    "H": ("H",),
    "O": ("O",),
    "WASD/EQ": ("W", "A", "S", "D", "E", "Q"),
    "Shift": ("LeftShift",),
    "mouse": ("Mouse2D",),
    "Z/C": ("Z", "C"),
    "wheel": ("MouseWheelAxis",),
    "[": ("LeftBracket",),
    "]": ("RightBracket",),
    "-": ("Hyphen",),
    "=": ("Equals",),
    ",": ("Comma",),
    ".": ("Period",),
    "N": ("N",),
    "M": ("M",),
}
GAMEPAD_KEYS: dict[str, tuple[str, ...]] = {
    "View": ("Gamepad_Special_Left",),
    "A": ("Gamepad_FaceButton_Bottom",),
    "Menu": ("Gamepad_Special_Right",),
    "R3": ("Gamepad_RightThumbstick",),
    "B": ("Gamepad_FaceButton_Right",),
    "LS": ("Gamepad_Left2D",),
    "LT/RT": ("Gamepad_LeftTriggerAxis", "Gamepad_RightTriggerAxis"),
    "RS": ("Gamepad_Right2D",),
    "L3": ("Gamepad_LeftThumbstick",),
    "DPad L/R": ("Gamepad_DPad_Left", "Gamepad_DPad_Right"),
    "DPad D/U": ("Gamepad_DPad_Down", "Gamepad_DPad_Up"),
    "LB/RB": ("Gamepad_LeftShoulder", "Gamepad_RightShoulder"),
    "X/Y": ("Gamepad_FaceButton_Left", "Gamepad_FaceButton_Top"),
}
HINT_WORDS = {
    "exit", "shoot", "reset", "dof", "char", "overlay", "move", "fast", "look", "roll", "fov", "ev",
    "focus", "f-stop", "down/up",
}  # fmt: skip
# the toggle keys live in the controller (IMC_GolmokPhotoToggle); everything else in the subsystem
TOGGLE_KEYS = {"P", "Gamepad_Special_Left"}
# design section 8-3 (7): the parser's key strings
CPP_KEYS = (
    "schema_version", "params", "toggles", "hints", "keyboard", "gamepad", "label", "unit", "default", "min",
    "max", "step", "step_ratio", "values", "dof", "character_hidden", "overlay_hidden", *PARAM_ORDER,
)  # fmt: skip
# design section 8-3 (8): spec numbers that must not be duplicated in C++ (20 / 3.0 are too common to check)
RANGE_LITERALS = ("110", "1.4", "16.0", "0.3", "50.0", "15.0")


@pytest.fixture(scope="module")
def raw() -> dict:
    assert PHOTO_JSON.is_file(), PHOTO_JSON
    return json.loads(PHOTO_JSON.read_text(encoding="utf-8"))


def _number(v) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool)


def _strip_code(text: str) -> str:
    """C++ without comments and string literals (numbers inside TEXT("...") are messages, not ranges)."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return re.sub(r'"(?:\\.|[^"\\])*"', '""', text)


# ---- (1)-(5) the file --------------------------------------------------------------------------------------


def test_top_level_shape(raw):
    assert set(raw) == {"schema_version", "params", "toggles", "hints"}
    assert raw["schema_version"] == 1 and _number(raw["schema_version"])


def test_params_order_and_shapes(raw):
    params = raw["params"]
    assert list(params) == PARAM_ORDER  # file order = EGolmokPhotoParam order = overlay order
    for name, p in params.items():
        assert isinstance(p["label"], str) and isinstance(p["unit"], str), name
        assert _number(p["default"]), name
        extra = set(p) - {"label", "unit", "default"}
        assert extra in SHAPES, (name, extra)
        for key in extra:
            if key != "values":
                assert _number(p[key]), (name, key)
        if "values" in p:
            values = p["values"]
            assert len(values) >= 2 and all(_number(v) and v > 0 for v in values), name
            assert values == sorted(values) and len(set(values)) == len(values), name
            assert p["default"] in values, name
        else:
            assert p["min"] < p["max"], name
            assert p["min"] <= p["default"] <= p["max"], name
            if "step" in p:
                assert p["step"] > 0, name
            else:
                assert p["step_ratio"] > 1 and p["min"] > 0, name


def test_spec_regression_constants(raw):
    params = raw["params"]
    for name, (lo, hi) in SPEC_RANGES.items():
        assert (params[name]["min"], params[name]["max"]) == (lo, hi), name
    assert (params["fstop"]["values"][0], params["fstop"]["values"][-1]) == FSTOP_ENDS
    assert params["ev"]["step"] == pytest.approx(1.0 / 3.0, abs=1e-9)
    assert params["fov"]["default"] == 65.0 and params["fov"]["step"] == 5.0
    assert params["fstop"]["default"] == 2.8
    assert params["focus"]["default"] == 3.0 and params["focus"]["step_ratio"] == 1.25
    assert params["roll"]["default"] == 0.0 and params["roll"]["step"] == 1.0
    assert params["ev"]["default"] == 0.0


def test_toggles(raw):
    toggles = raw["toggles"]
    assert set(toggles) == TOGGLES
    assert all(isinstance(v, bool) for v in toggles.values())
    assert toggles["dof"] is False  # design section 0 #11: DOF off by default


def _hint_tokens(line: str, keys: dict[str, tuple[str, ...]]) -> list[str]:
    """Key tokens of one hint line; multi-word keys ("DPad L/R") are matched first."""
    found: list[str] = []
    rest = f" {line} "
    for token in sorted(keys, key=len, reverse=True):
        if f" {token} " in rest:
            found.append(token)
            rest = rest.replace(f" {token} ", "  ")
    for word in rest.split():
        assert word in HINT_WORDS, f"unknown hint token {word!r} in {line!r}"
    return found


def test_hints_shape_and_tokens(raw):
    hints = raw["hints"]
    assert set(hints) == {"keyboard", "gamepad"}
    for device, keys in (("keyboard", KEYBOARD_KEYS), ("gamepad", GAMEPAD_KEYS)):
        lines = hints[device]
        assert isinstance(lines, list) and 1 <= len(lines) <= MAX_HINT_LINES, device
        assert all(isinstance(line, str) and len(line) <= MAX_HINT_CHARS for line in lines), device
        tokens = {t for line in lines for t in _hint_tokens(line, keys)}
        assert tokens == set(keys), (device, set(keys) ^ tokens)


# ---- (6) hints <-> EKeys in the C++ ------------------------------------------------------------------------


def test_hint_keys_are_mapped_in_cpp(raw):
    subsystem = re.findall(r"EKeys::(\w+)", SUBSYSTEM_CPP.read_text(encoding="utf-8"))
    controller = re.findall(r"EKeys::(\w+)", CONTROLLER_CPP.read_text(encoding="utf-8"))
    for device, keys in (("keyboard", KEYBOARD_KEYS), ("gamepad", GAMEPAD_KEYS)):
        for line in raw["hints"][device]:
            for token in _hint_tokens(line, keys):
                for ekey in keys[token]:
                    if ekey in TOGGLE_KEYS:
                        assert ekey in controller and ekey not in subsystem, ekey
                    else:
                        assert ekey in subsystem, (device, token, ekey)
    # the shoot key Enter and the mouse look are mapped although the hints do not spell them out
    assert "Enter" in subsystem and "Mouse2D" in subsystem and "SpaceBar" in subsystem


# ---- (7)(8) the C++ side -----------------------------------------------------------------------------------


def test_cpp_parser_uses_the_same_keys():
    text = SUBSYSTEM_CPP.read_text(encoding="utf-8")
    for key in CPP_KEYS:
        assert f'TEXT("{key}")' in text, f'missing TEXT("{key}")'
    assert "FJsonSerializer::Deserialize" in text and "TryGetField" in text
    assert "Values.Find(" not in text  # UE 5.8: FJsonObject::Values keys are UE::FSharedString
    assert "FString(*Pair.Key)" in text
    assert "namespace GolmokPhotoJson" in text
    assert "ParseConfigText" in text and "LoadConfigFile" in text and "FFileHelper::LoadFileToString" in text


@pytest.mark.parametrize("source", sorted(PHOTO.glob("*.cpp")), ids=lambda p: p.name)
def test_no_range_literals_in_cpp(source: Path):
    code = _strip_code(source.read_text(encoding="utf-8"))
    tokens = set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", code))
    hits = sorted(t for t in RANGE_LITERALS if t in tokens)
    assert not hits, f"{source.name}: photo.json range literal(s) {hits} duplicated in C++"


# ---- (9)(10) ini / staging ---------------------------------------------------------------------------------


def test_ini_points_at_the_file_and_has_sane_values():
    text = INI.read_text(encoding="utf-8-sig")
    cp = parse_ue_ini(text)
    photo = cp[PHOTO_SECTION]
    assert photo["ConfigFile"] == "Golmok/photo.json"
    assert (UE / "Config" / photo["ConfigFile"]).resolve() == PHOTO_JSON.resolve()
    assert 1 <= int(photo["ScreenshotMultiplier"]) <= int(photo["MaxMultiplier"]) <= 8
    assert float(photo["MaxDistanceM"]) >= 0.5
    assert photo["PhotoFolder"].startswith("Screenshots/Golmok/")
    assert photo["PauseMode"] in {"GamePause", "TimeDilation"}
    assert int(photo["PreCaptureFrames"]) >= 0 and int(photo["PostCaptureFrames"]) >= 1
    assert float(photo["CollisionRadiusCm"]) >= 5 and float(photo["FootprintMarginM"]) >= 0
    assert float(photo["MoveSpeedMps"]) > 0


def test_photo_json_is_staged_by_the_existing_ufs_line():
    text = INI.read_text(encoding="utf-8-sig")
    assert '+DirectoriesToAlwaysStageAsUFS=(Path="../Config/Golmok")' in text
    assert text.count("+DirectoriesToAlwaysStageAsUFS=") == 2  # no staging line added for the photo config
    assert PHOTO_JSON.parent == UE / "Config" / "Golmok"


# ---- (11) legal note ---------------------------------------------------------------------------------------


def test_legal_policy_lists_the_screenshot_sharing_question():
    text = LEGAL_DOC.read_text(encoding="utf-8")
    assert re.search(r"^7\. \*\*사용자 촬영 스크린샷의 외부 공유\*\*", text, re.M)
    assert "D-013" in text and "D-009" in text
