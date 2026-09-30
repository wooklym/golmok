"""The shipped roster satisfies its schema and cross-field constraints before UE loads it."""

from __future__ import annotations

import copy
import json
import math

import jsonschema
import pytest
from zone_util import REPO

SCHEMA = json.loads((REPO / "docs/spec/characters.schema.json").read_text(encoding="utf-8"))
ROSTER = json.loads((REPO / "unreal/Golmok/Config/Golmok/characters.json").read_text(encoding="utf-8"))


def validate(data):
    jsonschema.Draft202012Validator(SCHEMA).validate(data)
    ids = [e["id"] for e in data["characters"]]
    assert len(ids) == len(set(ids)), "duplicate id"
    assert data["default"] in ids, "missing default"
    assert all(id in ids for id in data.get("default_by_anim_mode", {}).values()), "missing mode default"
    for entry in data["characters"]:
        cap, movement = entry["capsule"], entry["movement"]
        assert cap["half_height_cm"] >= cap["radius_cm"], "capsule radius exceeds half height"
        assert movement["run_cm_s"] > movement["walk_cm_s"], "run must exceed walk"

    def finite(value):
        if isinstance(value, dict):
            return all(finite(v) for v in value.values())
        if isinstance(value, list):
            return all(finite(v) for v in value)
        return not isinstance(value, float) or math.isfinite(value)

    assert finite(data), "non-finite number"


def test_shipped_roster_and_schema():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    validate(ROSTER)
    assert ROSTER["default"] == "manny"
    assert {e["id"] for e in ROSTER["characters"]} == {
        "manny",
        "quinn",
        "proxy135",
        "proxy110",
        "manny_gasp",
        "uefn_gasp",
    }
    assert all(e["footstep_set"] is None for e in ROSTER["characters"])


@pytest.mark.parametrize(
    "path,value",
    [
        (("schema_version",), 2),
        (("default",), "absent"),
        (("characters", 1, "id"), "manny"),
        (("characters", 0, "id"), "list"),
        (("characters", 0, "mesh"), "../asset"),
        (("characters", 0, "anim_class"), "/Game/A/A.A"),
        (("characters", 0, "mesh_scale"), [1, 0, 1]),
        (("characters", 0, "height_cm"), True),
        (("characters", 0, "camera", "fov_deg"), 120),
        (("characters", 0, "capsule", "half_height_cm"), 40),
        (("characters", 0, "movement", "run_cm_s"), 180),
        (("characters", 0, "camera", "socket_cm"), [0, 1]),
        (("characters", 0, "display_name", "ko"), "  "),
        (("characters", 0, "height_cm"), float("nan")),
        (("characters", 0, "height_cm"), float("inf")),
        (("characters", 0, "unknown"), 1),
    ],
)
def test_invalid_roster_is_rejected(path, value):
    data = copy.deepcopy(ROSTER)
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises((jsonschema.ValidationError, AssertionError)):
        validate(data)


def test_optional_gasp_fields_and_legacy_roster():
    validate(ROSTER)
    legacy = copy.deepcopy(ROSTER)
    del legacy["default_by_anim_mode"]
    for entry in legacy["characters"]:
        entry.pop("visual", None)
    validate(legacy)


@pytest.mark.parametrize(
    "value",
    [
        None,
        {},
        {"abp": "manny"},
        {"abp": "manny", "gasp": "missing"},
        {"abp": 1, "gasp": "manny"},
        {"abp": "manny", "gasp": "manny", "typo": "manny"},
    ],
)
def test_mode_defaults_are_strict(value):
    data = copy.deepcopy(ROSTER)
    data["default_by_anim_mode"] = value
    with pytest.raises((jsonschema.ValidationError, AssertionError)):
        validate(data)


@pytest.mark.parametrize(
    "key,value",
    [
        ("mesh", "../bad"),
        ("anim_class", "/Game/A/A.A"),
        ("mesh_scale", [1, 0, 1]),
        ("mesh_scale", [1, True, 1]),
        ("mesh_scale", [1, float("nan"), 1]),
        ("mesh_scale", [1, 1]),
        ("typo", 1),
    ],
)
def test_visual_is_strict(key, value):
    data = copy.deepcopy(ROSTER)
    data["characters"][4]["visual"][key] = value
    with pytest.raises((jsonschema.ValidationError, AssertionError)):
        validate(data)


@pytest.mark.parametrize("value", [None, {}, [], {"mesh": "/Game/A/A.A"}])
def test_visual_requires_complete_object(value):
    data = copy.deepcopy(ROSTER)
    data["characters"][4]["visual"] = value
    with pytest.raises(jsonschema.ValidationError):
        validate(data)


ANIMATION = json.loads((REPO / "unreal/Golmok/Config/Golmok/animation.json").read_text(encoding="utf-8"))


def validate_animation_contract(roster, animation):
    """Deployment contract: 19b path changes require a paired Astra roster update.

    Ordinary (①) entries share one ABP; introduce an allowlist if another ABP is added.
    """
    root = animation["gasp"]["content_root"].rstrip("/") + "/"
    expected = root + animation["gasp"]["anim_class"]
    abp = next(e["anim_class"] for e in roster["characters"] if e["id"] == roster["default"])
    assert abp != expected, "common ABP must differ from GASP animation"
    gasp_ids = set()
    for entry in roster["characters"]:
        is_gasp = "visual" in entry or entry["anim_class"] != abp
        if is_gasp:
            assert entry["anim_class"] == expected, "GASP roster animation path differs from animation.json"
            assert entry["mesh_scale"] == [1, 1, 1], "GASP source scale must stay one"
            if "visual" in entry:
                assert entry["visual"]["mesh_scale"] == [1, 1, 1], "GASP visual scale must stay one"
            gasp_ids.add(entry["id"])
    defaults = roster["default_by_anim_mode"]
    assert defaults["gasp"] in gasp_ids, "gasp default must select a GASP entry"
    assert defaults["abp"] == roster["default"], "abp default must preserve common default"
    assert defaults["abp"] not in gasp_ids, "abp/default must not select GASP"


def test_shipped_animation_roster_contract():
    validate_animation_contract(ROSTER, ANIMATION)


@pytest.mark.parametrize(
    "case,reason",
    [
        ("relocate", "GASP roster animation path differs"),
        ("abp_path", "GASP roster animation path differs"),
        ("visual_path", "GASP roster animation path differs"),
        ("direct_path", "GASP roster animation path differs"),
        ("stale_direct", "GASP roster animation path differs"),
        ("gasp_default", "gasp default must select a GASP entry"),
        ("abp_default", "common ABP must differ"),
        ("scale", "GASP source scale must stay one"),
        ("visual_scale", "GASP visual scale must stay one"),
    ],
)
def test_animation_roster_contract_detects_drift(case, reason):
    roster, animation = copy.deepcopy(ROSTER), copy.deepcopy(ANIMATION)
    entries = {entry["id"]: entry for entry in roster["characters"]}
    if case == "relocate":
        animation["gasp"]["content_root"] = "/Game/Relocated"
    elif case == "abp_path":
        animation["gasp"]["anim_class"] = "Blueprints/New.New_C"
    elif case in ("visual_path", "direct_path", "stale_direct"):
        entry = entries["manny_gasp" if case == "visual_path" else "uefn_gasp"]
        entry["anim_class"] = "/Game/Wrong/ABP.ABP_C"
        if case == "stale_direct":
            entry["mesh"] = "/Game/Wrong/Mesh.Mesh"
    elif case == "gasp_default":
        roster["default_by_anim_mode"]["gasp"] = "manny"
    elif case == "abp_default":
        roster["default"] = roster["default_by_anim_mode"]["abp"] = "manny_gasp"
    elif case == "visual_scale":
        entries["manny_gasp"]["visual"]["mesh_scale"] = [1, 1, 0.75]
    else:
        entries["uefn_gasp"]["mesh_scale"] = [1, 1, 0.75]
    with pytest.raises(AssertionError, match=reason):
        validate_animation_contract(roster, animation)


def test_animation_roster_contract_allows_game_root_relocation():
    roster, animation = copy.deepcopy(ROSTER), copy.deepcopy(ANIMATION)
    animation["gasp"]["content_root"] = "/Game"
    animation["gasp"]["anim_class"] = "Relocated/ABP.ABP_C"
    abp = next(e["anim_class"] for e in roster["characters"] if e["id"] == roster["default"])
    for entry in roster["characters"]:
        if "visual" in entry or entry["anim_class"] != abp:
            entry["anim_class"] = "/Game/Relocated/ABP.ABP_C"
            entry["mesh"] = "/Game/Relocated/Mesh.Mesh"
    validate(roster)
    validate_animation_contract(roster, animation)
