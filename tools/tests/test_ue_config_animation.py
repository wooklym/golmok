"""WP-19a: Config/Golmok/animation.json schema (design section 7), the rules of GolmokAnimation::ParseConfig.

The committed file keeps mode "abp" (D-021: main stays ① until V-15), p0 = the AGolmokCharacter constructor
values plus the engine defaults it does not set (Golmok.Animation.StateProvider checks them against the CDO),
p1 / p2 null until 19b fills them from V-08b.
"""

from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "unreal/Golmok/Config/Golmok/animation.json"
CHARACTER_CPP = REPO / "unreal/Golmok/Source/Golmok/Player/GolmokCharacter.cpp"
TEST_CPP = REPO / "unreal/Golmok/Source/Golmok/Tests/GolmokAnimationTest.cpp"

REL_OBJECT = r"([A-Za-z0-9_]+/)*[A-Za-z0-9_]+\.[A-Za-z0-9_]+"
REL_CLASS = REL_OBJECT + "_C"
ABS_OBJECT = r"/Game/([A-Za-z0-9_]+/)+[A-Za-z0-9_]+\.[A-Za-z0-9_]+"
ABS_CLASS = ABS_OBJECT + "_C"
SCRIPT_CLASS = r"/Script/Golmok\.[A-Za-z0-9_]+"
PROFILE_RANGES = {
    "max_acceleration": (100, 10000),
    "braking_deceleration_walking": (0, 10000),
    "ground_friction": (0, 20),
    "braking_friction_factor": (0, 10),
    "braking_friction": (0, 20),
}
# UCharacterMovementComponent constructor values AGolmokCharacter does not override [추정 → StateProvider].
ENGINE_DEFAULTS = {
    "max_acceleration": 2048.0,
    "ground_friction": 8.0,
    "braking_friction_factor": 2.0,
    "use_separate_braking_friction": False,
    "braking_friction": 0.0,
}


def _number(value, low, high, where):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{where}: expected a number in [{low}, {high}]: {value!r}")


def _keys(obj, names, where):
    if not isinstance(obj, dict) or set(obj) != set(names):
        raise ValueError(f"{where}: keys must be exactly {sorted(names)}")


def _match(value, pattern, where):
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError(f"{where}: {value!r} does not match {pattern}")


def validate(data) -> None:
    """Raises ValueError on the first rule GolmokAnimation::ParseConfig would also refuse."""
    _keys(data, {"schema_version", "mode", "gasp", "movement_profiles"}, "$")
    if type(data["schema_version"]) not in (int, float) or data["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    if data["mode"] not in ("abp", "gasp"):
        raise ValueError("mode must be abp or gasp")
    gasp = data["gasp"]
    _keys(
        gasp,
        {
            "content_root",
            "pawn_class",
            "pawn_interface",
            "anim_class",
            "preview",
            "movement_profile",
            "state",
        },
        "gasp",
    )
    if gasp["content_root"] not in ("/Game/GASP", "/Game"):
        raise ValueError("gasp.content_root must be /Game/GASP or /Game")
    if not isinstance(gasp["pawn_class"], str) or not (
        re.fullmatch(ABS_CLASS, gasp["pawn_class"]) or re.fullmatch(SCRIPT_CLASS, gasp["pawn_class"])
    ):
        raise ValueError("gasp.pawn_class format")
    _match(gasp["pawn_interface"], REL_CLASS, "gasp.pawn_interface")
    _match(gasp["anim_class"], REL_CLASS, "gasp.anim_class")
    preview = gasp["preview"]
    _keys(preview, {"source_mesh", "visual_mesh", "visual_anim_class"}, "gasp.preview")
    _match(preview["source_mesh"], REL_OBJECT, "gasp.preview.source_mesh")
    for key, rel, absolute in (
        ("visual_mesh", REL_OBJECT, ABS_OBJECT),
        ("visual_anim_class", REL_CLASS, ABS_CLASS),
    ):
        value = preview[key]
        if value is not None and not (
            isinstance(value, str) and (re.fullmatch(rel, value) or re.fullmatch(absolute, value))
        ):
            raise ValueError(f"gasp.preview.{key} format")
    if (preview["visual_mesh"] is None) != (preview["visual_anim_class"] is None):
        raise ValueError("gasp.preview visual fields must be both null or both set")
    state = gasp["state"]
    _keys(state, {"just_landed_seconds", "teleport_jump_cm", "reinit_anim_on_teleport"}, "gasp.state")
    _number(state["just_landed_seconds"], 0.05, 2, "gasp.state.just_landed_seconds")
    _number(state["teleport_jump_cm"], 20, 1000, "gasp.state.teleport_jump_cm")
    if type(state["reinit_anim_on_teleport"]) is not bool:
        raise ValueError("gasp.state.reinit_anim_on_teleport must be a bool")
    profiles = data["movement_profiles"]
    if not isinstance(profiles, dict) or not 1 <= len(profiles) <= 8:
        raise ValueError("movement_profiles must have 1-8 entries")
    for pid, profile in profiles.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,15}", pid):
            raise ValueError(f"movement_profiles: bad id {pid!r}")
        if profile is None:
            continue
        _keys(profile, set(PROFILE_RANGES) | {"use_separate_braking_friction"}, f"movement_profiles.{pid}")
        for key, (low, high) in PROFILE_RANGES.items():
            _number(profile[key], low, high, f"movement_profiles.{pid}.{key}")
        if type(profile["use_separate_braking_friction"]) is not bool:
            raise ValueError(f"movement_profiles.{pid}.use_separate_braking_friction must be a bool")
    selected = gasp["movement_profile"]
    if not isinstance(selected, str) or profiles.get(selected) is None:
        raise ValueError("gasp.movement_profile is missing or null")


@pytest.fixture(scope="module")
def committed():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_committed_file_is_valid_and_abp(committed):
    validate(committed)
    assert (
        committed["mode"] == "abp"
    )  # D-021: main stays ① until V-15 (runbook §B8 changes it with this line)
    assert committed["gasp"]["movement_profile"] in committed["movement_profiles"]
    assert list(committed["movement_profiles"]) == ["p0", "p1", "p2"]  # p1 / p2 null until 19b (V-08b)
    assert committed["gasp"]["pawn_class"].startswith("/Game/GolmokLocal/GASP/")


def test_p0_is_the_current_character(committed):
    text = CHARACTER_CPP.read_text(encoding="utf-8")
    braking = re.search(r"Movement->BrakingDecelerationWalking\s*=\s*([\d.]+)f;", text)
    assert braking, "GolmokCharacter.cpp BrakingDecelerationWalking"
    for field in (
        "MaxAcceleration",
        "GroundFriction",
        "BrakingFrictionFactor",
        "bUseSeparateBrakingFriction",
        "BrakingFriction =",
    ):
        assert f"Movement->{field}" not in text, (
            f"{field} is now set by the constructor: update p0 / ENGINE_DEFAULTS"
        )
    expected = dict(ENGINE_DEFAULTS, braking_deceleration_walking=float(braking.group(1)))
    assert committed["movement_profiles"]["p0"] == expected


def _cases(base):
    def edit(fn):
        data = copy.deepcopy(base)
        fn(data)
        return data

    yield "schema_version 2", edit(lambda d: d.update(schema_version=2))
    yield "missing mode", edit(lambda d: d.pop("mode"))
    yield "extra root key", edit(lambda d: d.update(extra=1))
    yield "extra gasp key", edit(lambda d: d["gasp"].update(x=1))
    yield "mode motion", edit(lambda d: d.update(mode="motion"))
    yield "pawn_class without _C", edit(lambda d: d["gasp"].update(pawn_class=d["gasp"]["pawn_class"][:-2]))
    yield "pawn_class outside /Game", edit(lambda d: d["gasp"].update(pawn_class="/Engine/X/Y.Y_C"))
    yield "anim_class absolute", edit(lambda d: d["gasp"].update(anim_class="/" + d["gasp"]["anim_class"]))
    yield "path with a space", edit(lambda d: d["gasp"].update(pawn_interface="Blue prints/X.X_C"))
    yield "content_root other", edit(lambda d: d["gasp"].update(content_root="/Game/Other"))
    yield "max_acceleration 99", edit(lambda d: d["movement_profiles"]["p0"].update(max_acceleration=99))
    yield "ground_friction 21", edit(lambda d: d["movement_profiles"]["p0"].update(ground_friction=21))
    yield (
        "flag as number",
        edit(lambda d: d["movement_profiles"]["p0"].update(use_separate_braking_friction=0)),
    )
    yield "just_landed 3", edit(lambda d: d["gasp"]["state"].update(just_landed_seconds=3))
    yield "teleport 5", edit(lambda d: d["gasp"]["state"].update(teleport_jump_cm=5))
    yield (
        "null profile selected",
        edit(lambda d: (d["movement_profiles"].update(p1=None), d["gasp"].update(movement_profile="p1"))),
    )
    yield "unknown profile selected", edit(lambda d: d["gasp"].update(movement_profile="p9"))
    yield (
        "visual mesh alone",
        edit(lambda d: d["gasp"]["preview"].update(visual_mesh="Characters/X/SKM_X.SKM_X")),
    )
    yield "bad profile id", edit(lambda d: d["movement_profiles"].update(P3=None))


def test_invalid_variants_are_rejected(committed):
    for name, data in _cases(committed):
        with pytest.raises(ValueError):
            validate(data)
        assert json.dumps(data, sort_keys=True) != json.dumps(committed, sort_keys=True), name


def test_valid_variants(committed):
    both = copy.deepcopy(committed)
    both["gasp"]["preview"].update(
        visual_mesh="/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple",
        visual_anim_class="Characters/UE5_Mannequins/Rigs/RTG.RTG_C",
    )
    validate(both)
    root = copy.deepcopy(committed)
    root["gasp"]["content_root"] = "/Game"
    root["gasp"]["pawn_class"] = "/Script/Golmok.GolmokGaspCharacter"
    validate(root)
    filled = copy.deepcopy(committed)
    filled["movement_profiles"]["p1"] = dict(committed["movement_profiles"]["p0"], max_acceleration=1500)
    filled["gasp"]["movement_profile"] = "p1"
    filled["mode"] = "gasp"
    validate(filled)


def test_cpp_test_base_config_has_the_committed_schema(committed):
    # Golmok.Animation.Config builds its error cases from a literal: a valid file of the same schema.
    text = TEST_CPP.read_text(encoding="utf-8")
    match = re.search(r'const TCHAR\* BaseConfig = TEXT\(R"JSON\((.*?)\)JSON"\);', text, re.S)
    assert match, "BaseConfig literal"
    base = json.loads(match.group(1))
    validate(base)
    assert base["mode"] == "abp" and base["gasp"]["movement_profile"] == "p0"
    assert set(base) == set(committed) and set(base["gasp"]) == set(committed["gasp"])
    assert set(base["movement_profiles"]) == set(committed["movement_profiles"])
    assert set(base["gasp"]["preview"]) == set(committed["gasp"]["preview"])
    assert set(base["gasp"]["state"]) == set(committed["gasp"]["state"])
