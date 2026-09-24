"""JSON Schema validation for zone manifests, blocker files and the Zone Index.

The schemas are package data (golmok_tools/zone/schemas/) copied from docs/spec/, which is the source of
truth; tests/test_zone_schema.py fails if the two copies drift.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources

from jsonschema import Draft202012Validator

MANIFEST = "zone-manifest.schema.json"
BLOCKERS = "zone-blockers.schema.json"
INDEX = "zone-index.schema.json"
SCHEMA_FILES = (MANIFEST, BLOCKERS, INDEX)


@cache
def load_schema(name: str = MANIFEST) -> dict:
    text = resources.files("golmok_tools.zone").joinpath("schemas", name).read_text(encoding="utf-8")
    return json.loads(text)


@cache
def _validator(name: str) -> Draft202012Validator:
    schema = load_schema(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _errors(doc, name: str) -> list[str]:
    out = []
    for e in sorted(_validator(name).iter_errors(doc), key=lambda e: list(e.absolute_path)):
        path = "/".join(str(p) for p in e.absolute_path) or "(root)"
        out.append(f"{path}: {e.message}")
    return out


def validate(manifest) -> list[str]:
    """Schema errors of a manifest dict ('' list = valid)."""
    return _errors(manifest, MANIFEST)


def validate_blockers(doc) -> list[str]:
    return _errors(doc, BLOCKERS)


def validate_index(doc) -> list[str]:
    return _errors(doc, INDEX)
