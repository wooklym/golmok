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
    assert {e["id"] for e in ROSTER["characters"]} == {"manny", "quinn", "proxy135", "proxy110"}
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
