"""golmok/zone_index.py (WP-09 design §3-7) on the scripted fake `unreal`: sync() copies the committed fixture
index byte for byte into <Content>/Golmok/Zones/index, removes stale cells, refuses a broken index before
writing, and zone_import.run(with_index=True) runs it between the zone rebuild and the save.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
from pathlib import Path

import fake_unreal
import pytest
from fake_unreal import DEFAULT_LEVEL
from golmok import _pure as pure

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "scripts" / "make_synthetic_zone.py"
FIXTURE_ZONES = Path(__file__).parent / "fixtures" / "zones"
FIXTURE_INDEX = FIXTURE_ZONES / "index"
INDEX_IDS = ["z_synthetic_001", "z_synthetic_001_interior", "z_synthetic_002"]
CELLS = ["16_55873_25379.json", "16_55873_25380.json", "16_55874_25379.json", "16_55874_25380.json"]
ZONE = "z_synthetic_scan_001"


# ---- fixtures ------------------------------------------------------------------------------------------


@pytest.fixture
def fake(monkeypatch, tmp_path):
    return fake_unreal.install(monkeypatch, tmp_path)


@pytest.fixture
def zx(fake):
    return importlib.import_module("golmok.zone_index")


@pytest.fixture
def zi(fake):
    return importlib.import_module("golmok.zone_import")


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    """One generated synthetic zone (no interior) shared by the run() tests."""
    pytest.importorskip("scipy")
    pytest.importorskip("fast_simplification")
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        msz = importlib.import_module("make_synthetic_zone")
    finally:
        sys.path.remove(str(SCRIPT.parent))
    out = tmp_path_factory.mktemp("index zone")
    assert msz.main(["--out", str(out), "--quiet"]) == 0
    return out


@pytest.fixture
def zone_copy(generated, tmp_path) -> Path:
    """A private copy of the generated tree; returns its zones root (<copy>/zones)."""
    out = tmp_path / "zone copy"
    shutil.copytree(generated, out)
    return out / "zones"


# ---- helpers -------------------------------------------------------------------------------------------


def _tree(folder: Path) -> dict[str, bytes]:
    return {
        os.path.normpath(str(p.relative_to(folder))): p.read_bytes()
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


def _dest(fake) -> Path:
    return Path(fake.content_dir) / "Golmok" / "Zones" / "index"


def _index_copy(tmp_path: Path, name: str = "zones") -> Path:
    """A private zones root holding a copy of the fixture index; returns the root."""
    root = tmp_path / name
    shutil.copytree(FIXTURE_INDEX, root / "index")
    return root


def _logs(fake, prefix: str = "zone_index:") -> list[str]:
    return [t for t in fake.logged() if t.startswith(prefix)]


# ---- sync ----------------------------------------------------------------------------------------------


def test_sync_copies_fixture_index_bytes(fake, zx):
    assert zx.describe() == f"index: none at {_dest(fake)}"
    result = zx.sync(str(FIXTURE_ZONES))
    dest = _dest(fake)
    assert os.path.normpath(result["dest"]) == os.path.normpath(str(dest))
    assert _tree(dest) == _tree(FIXTURE_INDEX)
    assert sorted(_tree(dest)) == sorted(
        os.path.normpath(p) for p in ["zones.json", *[f"cells/{c}" for c in CELLS]]
    )
    assert result == {
        "dest": result["dest"],
        "zones": 3,
        "cells": 4,
        "removed": [],
        "missing": INDEX_IDS,  # the fake Content holds no zone manifests yet
    }
    index_dir = os.path.normpath(str(FIXTURE_INDEX))
    assert fake.logged("log") == [
        f"zone_index: plan 3 zones, 4 cells from {index_dir}",
        f"zone_index: copied zones.json + 4 cells -> {result['dest']}",
        f"zone_index: done 3 zones, 4 cells -> {result['dest']}",
    ]
    assert fake.logged("warning") == [
        "zone_index: WARNING 3 indexed zones have no manifest under Content yet "
        "(z_synthetic_001, z_synthetic_001_interior, z_synthetic_002)"
    ]
    assert not fake.calls  # no editor call: plain file copies
    assert zx.describe() == f"index: 3 zones, 4 cells at {dest}"
    # a manifest under Content clears its id from the missing list
    target = Path(fake.content_dir) / "Golmok" / "Zones" / "z_synthetic_002" / "v1" / "manifest.json"
    target.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURE_ZONES / "z_synthetic_002" / "v1" / "manifest.json", target)
    assert zx.sync(str(FIXTURE_ZONES))["missing"] == INDEX_IDS[:2]
    # index_dir= overrides the <zones_root>/index default (the runbook §1 D:\golmok_index flow)
    assert zx.sync(str(FIXTURE_ZONES / "nowhere"), index_dir=str(FIXTURE_INDEX))["cells"] == 4


def test_sync_with_index_built_inside_content_is_a_no_op_copy(fake, zx):
    """index_dir == <Content>/Golmok/Zones/index (index built with --out straight into Content): no
    SameFileError, files untouched."""
    first = zx.sync(str(FIXTURE_ZONES))
    dest = _dest(fake)
    before = {p: (dest / p).read_bytes() for p in _tree(dest)}
    again = zx.sync(str(FIXTURE_ZONES / "nowhere"), index_dir=str(dest))
    assert again["cells"] == first["cells"] == 4 and again["removed"] == []
    assert {p: (dest / p).read_bytes() for p in _tree(dest)} == before


def test_sync_removes_stale_cells_and_is_idempotent(fake, zx):
    dest = _dest(fake)
    (dest / "cells").mkdir(parents=True)
    stale = dest / "cells" / "16_1_1.json"
    stale.write_text(
        '{"schema_version": 1, "z": 16, "x": 1, "y": 1, "zones": []}\n', encoding="utf-8", newline="\n"
    )
    (dest / "cells" / "notes.txt").write_text("kept: not a cell file\n", encoding="utf-8", newline="\n")
    result = zx.sync(str(FIXTURE_ZONES))
    assert result["removed"] == ["16_1_1.json"] and not stale.exists()
    assert (dest / "cells" / "notes.txt").is_file()
    assert "zone_index: removed 1 stale cell files (16_1_1.json)" in fake.logged("log")
    assert _tree(dest) == _tree(FIXTURE_INDEX) | {
        os.path.normpath("cells/notes.txt"): b"kept: not a cell file\n"
    }
    del fake.logs[:]
    again = zx.sync(str(FIXTURE_ZONES))
    assert again["removed"] == [] and _tree(dest) == _tree(FIXTURE_INDEX) | {
        os.path.normpath("cells/notes.txt"): b"kept: not a cell file\n"
    }
    assert not [t for t in fake.logged("log") if t.startswith("zone_index: removed")]
    assert [t.split(" ")[1] for t in _logs(fake)] == ["plan", "copied", "WARNING", "done"]


@pytest.mark.parametrize(
    "case",
    ["broken_cell_json", "version_mismatch", "manifest_path", "name_vs_content", "unknown_zone_in_cell"],
)
def test_sync_rejects_broken_index_before_writing(fake, zx, tmp_path, case):
    root = _index_copy(tmp_path)
    cells = root / "index" / "cells"
    zones_path = root / "index" / "zones.json"
    if case == "broken_cell_json":
        (cells / CELLS[0]).write_text("{not json", encoding="utf-8", newline="\n")
    elif case == "version_mismatch":
        cell = json.loads((cells / CELLS[1]).read_text("utf-8"))
        cell["zones"][0]["version"] = 2
        (cells / CELLS[1]).write_text(json.dumps(cell), encoding="utf-8", newline="\n")
    elif case == "manifest_path":
        doc = json.loads(zones_path.read_text("utf-8"))
        doc["zones"][0]["manifest"] = "z_synthetic_001/v2/manifest.json"
        zones_path.write_text(json.dumps(doc), encoding="utf-8", newline="\n")
    elif case == "name_vs_content":
        (cells / CELLS[0]).rename(cells / "16_55873_25381.json")
    else:
        cell = json.loads((cells / CELLS[1]).read_text("utf-8"))
        cell["zones"].append({"id": "z_ghost_001", "version": 1})
        (cells / CELLS[1]).write_text(json.dumps(cell), encoding="utf-8", newline="\n")
    with pytest.raises(zx.ZoneIndexError) as info:
        zx.sync(str(root))
    err = info.value
    assert err.step == "check" and str(err).startswith("zone_index: ERROR check: ")
    assert isinstance(err, importlib.import_module("golmok.zone_import").ZoneImportError)
    assert not _dest(fake).exists() and _tree(Path(fake.content_dir)) == {}
    assert fake.logged() == []  # nothing logged before the check passes
    with pytest.raises(zx.ZoneIndexError):
        zx.plan(str(root))


def test_sync_missing_index_dir(fake, zx, tmp_path):
    root = tmp_path / "zones"
    root.mkdir()
    with pytest.raises(zx.ZoneIndexError) as info:
        zx.sync(str(root))
    err = info.value
    assert err.step == "plan" and "zones.json" in err.message
    assert str(err) == pure.fmt("zx.error", step="plan", message=err.message)
    assert not _dest(fake).exists() and fake.logged() == []
    # an index folder without zones.json is the same case
    (root / "index" / "cells").mkdir(parents=True)
    with pytest.raises(zx.ZoneIndexError) as info:
        zx.plan(str(root))
    assert info.value.step == "plan"


# ---- zone_import.run(with_index=...) ---------------------------------------------------------------------


def _save_probe(fake, unreal, monkeypatch, seen: list):
    """Record what <Content>/Golmok/Zones/index holds at the moment save_current_level() is called."""
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    original = subsystem.save_current_level

    def probe():
        seen.append(sorted(_tree(_dest(fake))) if _dest(fake).is_dir() else [])
        return original()

    monkeypatch.setattr(subsystem, "save_current_level", probe)


def test_run_with_index_true_uses_zones_root(fake, zi, zone_copy, monkeypatch):
    shutil.copytree(FIXTURE_INDEX, zone_copy / "index")
    seen: list = []
    _save_probe(fake, fake.module, monkeypatch, seen)
    result = zi.run(str(zone_copy / ZONE), level=DEFAULT_LEVEL, geo_origin="area", with_index=True)
    assert list(result)[-2:] == ["interior", "index"]
    assert result["index"]["cells"] == 4 and result["index"]["zones"] == 3
    assert result["index"]["missing"] == INDEX_IDS  # the imported zone is not one of the indexed ones
    assert os.path.normpath(result["index"]["dest"]) == os.path.normpath(str(_dest(fake)))
    assert _tree(_dest(fake)) == _tree(FIXTURE_INDEX)
    # order: zone rebuilt -> index synced -> level saved (the index was on disk when save ran)
    logs = fake.logged()
    zone_line = logs.index(f"zone_import: zone Zone_{ZONE} rebuilt")
    index_line = logs.index(f"zone_index: done 3 zones, 4 cells -> {result['index']['dest']}")
    assert (
        zone_line
        < index_line
        < logs.index(f"zone_import: done {ZONE} v1: 8 assets, 0 warnings -> " + result_path(fake))
    )
    assert fake.calls_of("rebuild_in_editor") == [("rebuild_in_editor", ZONE)]
    assert fake.calls[-1] == ("save_current_level",)
    assert seen == [sorted(_tree(FIXTURE_INDEX))]
    written = json.loads(Path(result_path(fake)).read_text("utf-8"))
    assert written["index"] == result["index"]
    assert not [t for t in logs if t.startswith("zone_index: WARNING") and "not synced" in t]


def result_path(fake) -> str:
    return str(Path(fake.saved_dir) / "Golmok" / "zone_import" / ZONE / "v1" / "import_result.json")


def test_run_with_index_missing_folder_warns_not_fails(fake, zi, zone_copy):
    assert not (zone_copy / "index").exists()
    result = zi.run(str(zone_copy / ZONE), level=DEFAULT_LEVEL, geo_origin="area", with_index=True)
    assert result["index"] is None
    warnings = [t for t in fake.logged("warning") if t.startswith("zone_index: WARNING")]
    assert len(warnings) == 1 and "index not synced" in warnings[0] and "zones.json" in warnings[0]
    assert warnings[0].startswith(pure.log_prefixes()["zx.warn"])
    assert not _dest(fake).exists()
    assert fake.calls[-1] == ("save_current_level",)
    assert f"zone_import: done {ZONE} v1: 8 assets, 0 warnings -> {result_path(fake)}" in fake.logged("log")
    # with_index=False (the default) never mentions the index
    del fake.logs[:]
    result = zi.run(str(zone_copy / ZONE), level=DEFAULT_LEVEL, geo_origin="area")
    assert result["index"] is None and not _logs(fake)
    # a broken index is still a failure of the "index" step (only a missing one is tolerated)
    shutil.copytree(FIXTURE_INDEX, zone_copy / "index")
    (zone_copy / "index" / "cells" / CELLS[0]).write_text("{", encoding="utf-8", newline="\n")
    with pytest.raises(zi.ZoneImportError) as info:
        zi.run(str(zone_copy / ZONE), level=DEFAULT_LEVEL, geo_origin="area", with_index=True)
    assert info.value.step == "check" and str(info.value).startswith("zone_index: ERROR check: ")
