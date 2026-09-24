import copy
import json

import pytest
from zone_util import FIXTURE_ZONES, REPO

from golmok_tools.zone import manifest as zm
from golmok_tools.zone import schema

FIXTURE = FIXTURE_ZONES / "z_synthetic_001" / "v1" / "manifest.json"


@pytest.mark.parametrize("name", schema.SCHEMA_FILES)
def test_package_schema_matches_docs_spec(name):
    docs = (REPO / "docs" / "spec" / name).read_text(encoding="utf-8")
    pkg = (REPO / "tools" / "golmok_tools" / "zone" / "schemas" / name).read_text(encoding="utf-8")
    assert json.loads(pkg) == json.loads(docs), f"cp docs/spec/{name} tools/golmok_tools/zone/schemas/"


@pytest.mark.parametrize("name", schema.SCHEMA_FILES)
def test_schemas_are_valid_draft_2020_12(name):
    from jsonschema import Draft202012Validator

    s = schema.load_schema(name)
    assert s["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(s)


def test_fixture_passes_schema_and_semantics():
    d = zm.load(FIXTURE)
    assert schema.validate(d) == []
    rep = zm.check(d, FIXTURE)
    assert rep.errors == [] and rep.warnings == []
    # The shape WP-04 relies on
    assert len(d["layers"]["visual"]["chunks"]) == 3
    assert d["layers"]["collision"]["uri"] == "collision.glb"
    assert d["layers"]["blockers"]["uri"] == "blockers.json"
    assert len(d["portals"]) == 1


def test_fixture_blockers_pass_schema():
    doc = json.loads((FIXTURE.parent / "blockers.json").read_text(encoding="utf-8"))
    assert schema.validate_blockers(doc) == []
    assert len(doc["planes"]) == 1


def _mutated(fn):
    d = copy.deepcopy(zm.load(FIXTURE))
    fn(d)
    return schema.validate(d)


@pytest.mark.parametrize(
    "mutate, needle",
    [
        (lambda d: d.pop("transform"), "transform"),
        (lambda d: d.update(transform=d["transform"][:15]), "transform"),
        (lambda d: d.update(schema_version=2), "schema_version"),
        (lambda d: d.update(zone_id="Zone-1"), "zone_id"),
        (lambda d: d.update(version=0), "version"),
        (lambda d: d.update(kind="rooftop"), "kind"),
        (lambda d: d.update(extra_field=1), "extra_field"),
        (lambda d: d.update(parent_zone="z_other"), "parent_zone"),  # exterior must have null parent
        (lambda d: d["layers"]["visual"].update(format="rad"), "format"),
        (lambda d: d["layers"]["visual"]["chunks"][0].update(uri="../escape.glb"), "uri"),
        (lambda d: d["layers"]["visual"]["chunks"][0].update(uri="/abs/chunk.glb"), "uri"),
        (lambda d: d["layers"]["visual"]["chunks"][0].update(uri="visual\\chunk.glb"), "uri"),
        (lambda d: d["layers"]["visual"]["chunks"][0].update(uri="https://cdn/x.glb"), "uri"),
        (lambda d: d["layers"]["visual"]["chunks"][0].update(id="chunk-00"), "id"),
        (lambda d: d["layers"]["visual"]["chunks"][0].update(bbox_enu=[[0, 0, 0]]), "bbox_enu"),
        (lambda d: d["layers"]["collision"].update(format="obj"), "format"),
        (lambda d: d["layers"].pop("collision"), "collision"),
        (lambda d: d["portals"][0].update(kind="window"), "kind"),
        (lambda d: d["portals"][0].update(radius_m=0), "radius_m"),
        (lambda d: d["portals"][0].update(to_zone="interior"), "to_zone"),
        (lambda d: d["footprint_wgs84"].update(type="MultiPolygon"), "type"),
        (lambda d: d["footprint_wgs84"]["coordinates"][0][0].__setitem__(1, 95.0), "coordinates"),
        (lambda d: d["consent"].update(type="implied"), "type"),
        (lambda d: d["quality"].update(footprint_iou=1.5), "footprint_iou"),
        (lambda d: d["sources"].append({"note": "no id"}), "capture_id"),
    ],
)
def test_schema_rejects(mutate, needle):
    errors = _mutated(mutate)
    assert errors, "expected a schema error"
    assert any(needle in e for e in errors), errors


def test_interior_needs_parent():
    def interior(d):
        d.update(kind="interior", parent_zone=None)

    assert any("parent_zone" in e for e in _mutated(interior))

    def interior_ok(d):
        d.update(kind="interior", parent_zone="z_synthetic_001_street")

    assert _mutated(interior_ok) == []


def test_optional_layers_and_quality_extras_allowed():
    def edit(d):
        d["layers"].pop("blockers")
        d["layers"]["navmesh"] = {"format": "recast", "uri": "navmesh.bin"}
        d["layers"]["visual"]["textures"] = [
            {"uri": "visual/t0.png", "chunk_id": "chunk_00", "role": "base_color"}
        ]
        d["quality"]["vertical_tilt_deg"] = 0.1

    assert _mutated(edit) == []


def test_blockers_schema_rejects():
    bad = {
        "planes": [
            {"id": "g", "center_enu": [0, 0, 0], "normal_enu": [0, 1], "size_m": [1, 1], "kind": "glass"}
        ]
    }
    assert schema.validate_blockers(bad)
    bad = {
        "planes": [
            {"id": "g", "center_enu": [0, 0, 0], "normal_enu": [0, 1, 0], "size_m": [0, 1], "kind": "x"}
        ]
    }
    assert len(schema.validate_blockers(bad)) == 2
