"""Copy a Zone Index (golmok-zone index build) into Content/Golmok/Zones/index (spec §6 "게임 내 위치").

    golmok-zone index build --zones-root D:\\golmok\\zones --out D:\\golmok\\zones\\index --strict
    import golmok.zone_index as zx; zx.sync(r"D:\\golmok\\zones")          # <zones>/index -> Content
    zx.sync(r"D:\\golmok\\zones", index_dir=r"D:\\golmok_index")           # index built somewhere else
    zx.describe()                                                          # what Content holds now
    import golmok.zone_import as zi; zi.run(r"D:\\golmok\\zones\\z_x_001", with_index=True)   # after the zone

What it does (docs/plan/WP-09-ue-zone-index-async.md §3-7):
1. plan(): read <index_dir>/zones.json and cells/*.json (sorted) and check them with _pure.check_index; any
   problem raises ZoneIndexError("plan", ...) (no zones.json) or ZoneIndexError("check", ...). Nothing written.
2. sync(): _pure.index_sync_plan -> byte copies (shutil.copyfile) of zones.json and every cell file into
   <Content>/Golmok/Zones/index -> stale dest cell files removed -> a warning for indexed zones whose
   manifest is not under Content yet (zone_import.run has not copied it). The game (FGolmokZoneIndex) reads
   exactly these files; they are staged into a .pak by the existing `Golmok/Zones` UFS line.

Editor API used: unreal.Paths.project_content_dir(), unreal.log, unreal.log_warning — nothing else.
"""

from __future__ import annotations

import json
import os
import shutil

import unreal

from . import _pure
from . import zone_import as zi

INDEX_REL = "Golmok/Zones/index"  # under the project Content folder (== _pure.CONTENT_ZONES_REL/index)


class ZoneIndexError(zi.ZoneImportError):
    """One failed step; str() is the `zone_index: ERROR <step>: <message>` line."""

    log_key = "zx.error"


def _log(key: str, **kw) -> None:
    unreal.log(_pure.fmt(key, **kw))


def warn(message: str) -> None:
    """The zone_index: WARNING line (LOG zx.warn)."""
    unreal.log_warning(_pure.fmt("zx.warn", message=message))


def _content_dir(content_dir=None) -> str:
    return os.path.normpath(str(content_dir) if content_dir else unreal.Paths.project_content_dir())


def _dest(content_dir=None) -> str:
    return os.path.join(_content_dir(content_dir), *INDEX_REL.split("/"))


def _read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _cell_files(cells_dir: str) -> list[str]:
    """Sorted *.json file names in a cells folder ([] when the folder does not exist)."""
    if not os.path.isdir(cells_dir):
        return []
    return sorted(
        n for n in os.listdir(cells_dir) if n.endswith(".json") and os.path.isfile(os.path.join(cells_dir, n))
    )


def plan(zones_root, index_dir=None) -> dict:
    """Read and check an index without writing anything: {'index_dir', 'zones': doc, 'cells': {name: doc}}.

    index_dir defaults to <zones_root>/index (the spec §6 layout). ZoneIndexError('plan', ...) when zones.json
    is missing or unreadable, ZoneIndexError('check', ...) with every _pure.check_index problem.
    """
    root = os.path.normpath(str(zones_root))
    index_dir = os.path.normpath(str(index_dir)) if index_dir else os.path.join(root, _pure.INDEX_DIR_NAME)
    zones_path = os.path.join(index_dir, _pure.INDEX_ZONES_NAME)
    if not os.path.isfile(zones_path):
        raise ZoneIndexError(
            "plan",
            f"{_pure.INDEX_ZONES_NAME} not found in {index_dir} "
            "(run golmok-zone index build --zones-root <zones> --out <zones>/index first)",
        )
    try:
        zones_doc = _read_json(zones_path)
    except (OSError, ValueError) as e:
        raise ZoneIndexError("plan", f"{_pure.INDEX_ZONES_NAME}: {e}") from e
    cells_dir = os.path.join(index_dir, _pure.INDEX_CELLS_DIR)
    cells: dict[str, dict] = {}
    problems: list[str] = []
    for name in _cell_files(cells_dir):
        try:
            cells[name] = _read_json(os.path.join(cells_dir, name))
        except (OSError, ValueError) as e:
            problems.append(f"cells/{name}: {e}")
    problems += _pure.check_index(zones_doc, cells)
    if problems:
        raise ZoneIndexError("check", "; ".join(problems))
    return {"index_dir": index_dir, "zones": zones_doc, "cells": cells}


def sync(zones_root, index_dir=None, content_dir=None) -> dict:
    """plan() -> copy zones.json + cells into <Content>/Golmok/Zones/index -> remove stale cells -> warn about
    indexed zones without a manifest under Content. Returns
    {'dest', 'zones': n, 'cells': k, 'removed': [names], 'missing': [ids]}."""
    p = plan(zones_root, index_dir)
    zones_doc, cells = p["zones"], p["cells"]
    _log("zx.plan", zones=len(zones_doc["zones"]), cells=len(cells), index_dir=p["index_dir"])
    content = _content_dir(content_dir)
    dest = _dest(content)
    dest_cells = _cell_files(os.path.join(dest, _pure.INDEX_CELLS_DIR))
    sp = _pure.index_sync_plan(p["index_dir"], content, sorted(cells), dest_cells)
    os.makedirs(os.path.join(sp["dest"], _pure.INDEX_CELLS_DIR), exist_ok=True)
    for src, dst in sp["copy"]:
        shutil.copyfile(src, dst)
    _log("zx.copied", cells=len(cells), dest=sp["dest"])
    removed = []
    for path in sp["remove"]:
        os.remove(path)
        removed.append(os.path.basename(path))
    if removed:
        _log("zx.removed", n=len(removed), names=", ".join(removed))
    zones_root_content = os.path.join(content, *_pure.CONTENT_ZONES_REL.split("/"))
    missing = _pure.index_missing_manifests(
        zones_doc, lambda rel: os.path.isfile(os.path.join(zones_root_content, *rel.split("/")))
    )
    if missing:
        unreal.log_warning(_pure.fmt("zx.missing", n=len(missing), ids=", ".join(missing)))
    _log("zx.done", zones=len(zones_doc["zones"]), cells=len(cells), dest=sp["dest"])
    return {
        "dest": sp["dest"],
        "zones": len(zones_doc["zones"]),
        "cells": len(cells),
        "removed": removed,
        "missing": missing,
    }


def describe(content_dir=None) -> str:
    """'index: 3 zones, 4 cells at <dest>' or 'index: none at <dest>' (what the game will read)."""
    dest = _dest(content_dir)
    zones_path = os.path.join(dest, _pure.INDEX_ZONES_NAME)
    if not os.path.isfile(zones_path):
        return f"index: none at {dest}"
    try:
        n = len(_read_json(zones_path).get("zones", []))
    except (OSError, ValueError) as e:
        return f"index: unreadable at {dest} ({e})"
    cells = len(_cell_files(os.path.join(dest, _pure.INDEX_CELLS_DIR)))
    return f"index: {n} zones, {cells} cells at {dest}"
