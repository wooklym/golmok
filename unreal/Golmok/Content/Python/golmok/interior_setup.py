"""Interior zone (kind=interior): assets + AGolmokZone + sublevel L_<zone_id> with one PointLight, then the
parent zone is rebuilt.

    import golmok.interior_setup as it
    r = it.run(r"D:\\golmok_synth\\zones\\z_synthetic_scan_001_room", level="/Game/Golmok/Maps/L_ZoneTest")
    it.run(..., register=True)     # NamedStreamingLevel path only (DefaultGame.ini InteriorStreamingMode)

What it does (docs/runbooks/pc-verify-wp06.md §4; WP-06 design §3-3). Steps 1-4 make no editor call:
1. Reads the interior manifest: kind must be "interior" and parent_zone must be set.
2. Reads the parent's Content manifest <Content>/Golmok/Zones/<parent>/v<max n>/manifest.json, the file
   zone_import.run copied there (the C++ AGolmokZone reads the same file).
3. Portal round trip (design D9): the parent's door to this zone and this zone's door back must meet at the
   same point (<= 5 cm) facing opposite ways (yaw error <= 1 deg); otherwise nothing is imported.
4. Import plan (_pure.import_plan), exactly like zone_import.
5. Opens `level` (when given) and requires the parent's Zone_<parent> actor in it.
6. zone_import.import_assets: textures, M_ZoneScan / MI_*, chunks, collision, manifest.json copy.
7. Finds or spawns Zone_<zone_id>, rebuild_in_editor() as an editor check, takes its transform and
   unload_in_editor() (in PIE the parent's door portal loads it; runbook #11).
8. Sublevel L_<zone_id> through synthetic_zone._spawn_interior_sublevel: one PointLight
   Interior_Light_<zone_id> in *level* coordinates, tagged GolmokInteriorSetup; a re-run removes only the
   actors carrying that tag (design D10). No AGolmokZone, PostProcessVolume, DirectionalLight or
   AGolmokPortal goes in (C++ spawns the portals from the manifests).
9. register=True adds the sublevel to the persistent level's Levels list (NamedStreamingLevel path only).
10. Rebuilds the parent zone: reopening the persistent level dropped its transient components and portals.
11. Saves the level and writes <Saved>/Golmok/zone_import/<zone_id>/v<n>/import_result.json with an
    "interior" block (sublevel, round_trip, parent, parent_version, actors).

Failures raise InteriorSetupError, a zone_import.ZoneImportError whose text is the
`interior_setup: ERROR <step>: <message>` line; failures inside the asset part keep zone_import's own text.
"""

from __future__ import annotations

import contextlib
import json
import os

import unreal

from . import _pure, zone_import
from . import synthetic_zone as sz


class InteriorSetupError(zone_import.ZoneImportError):
    """One failed interior_setup step; str() is the `interior_setup: ERROR <step>: <message>` line."""

    log_key = "is.error"


# ---- small helpers -----------------------------------------------------------------------------------


def _log(key: str, **kw) -> None:
    unreal.log(_pure.fmt(key, **kw))


@contextlib.contextmanager
def _step(name: str):
    """Wrap any unexpected exception of an editor step into InteriorSetupError(name, ...)."""
    try:
        yield
    except zone_import.ZoneImportError:
        raise
    except Exception as e:
        raise InteriorSetupError(name, str(e) or type(e).__name__) from e


def _read_json(path: str) -> dict:
    with open(os.path.normpath(path), encoding="utf-8") as f:
        return json.load(f)


# ---- steps 1-4: files only, no editor call -------------------------------------------------------------


def _interior_manifest(zone_dir, version) -> tuple[str, int, dict]:
    """(version_dir, version, manifest) of an interior zone folder (step 1)."""
    try:
        version_dir, version = _pure.resolve_zone_dir(
            str(zone_dir), version, os.listdir, os.path.isdir, os.path.isfile
        )
    except ValueError as e:
        raise InteriorSetupError("plan", str(e)) from e
    try:
        manifest = _read_json(f"{version_dir}/manifest.json")
    except (OSError, ValueError) as e:
        raise InteriorSetupError("manifest", f"manifest.json: {e}") from e
    if manifest.get("kind") != "interior":
        raise InteriorSetupError("manifest", "kind must be interior (use zone_import.run for exterior zones)")
    parent = manifest.get("parent_zone")
    if not parent:
        raise InteriorSetupError("manifest", "parent_zone missing")
    if not isinstance(parent, str) or not _pure.ZONE_ID_RE.match(parent):
        raise InteriorSetupError("manifest", f"parent_zone invalid: {parent!r}")
    return version_dir, version, manifest


def _parent_manifest(parent: str) -> tuple[dict, int]:
    """(manifest, version) of the parent's newest Content manifest, copied there by zone_import (step 2)."""
    content = os.path.normpath(unreal.Paths.project_content_dir())
    root = os.path.join(content, *_pure.CONTENT_ZONES_REL.split("/"), parent)
    try:
        version_dir, version = _pure.resolve_zone_dir(root, None, os.listdir, os.path.isdir, os.path.isfile)
        manifest = _read_json(f"{version_dir}/manifest.json")
    except (OSError, ValueError) as e:
        raise InteriorSetupError(
            "parent", f"no Content manifest for {parent}: run zone_import.run on the parent zone first"
        ) from e
    return manifest, version


def _portal_check(parent: dict, interior: dict) -> dict:
    """Step 3 (design D9): both doors must meet at one point facing opposite ways, or nothing is imported."""
    try:
        check = _pure.portal_round_trip_check(parent, interior)
    except KeyError as e:
        raise InteriorSetupError("portal", f"manifest key {e} missing") from e
    except (ValueError, TypeError) as e:
        raise InteriorSetupError("portal", str(e) or type(e).__name__) from e
    if not check["ok"]:
        raise InteriorSetupError(
            "portal",
            f"{check['interior_portal']} vs {check['parent_portal']}: {check['dist_m']:.3f} m apart, "
            f"yaw error {check['yaw_err_deg']:.1f} deg (fix the manifests before importing)",
        )
    _log(
        "is.portal",
        interior_portal=check["interior_portal"],
        parent_portal=check["parent_portal"],
        dist_m=check["dist_m"],
        yaw_err=check["yaw_err_deg"],
    )
    return check


def _plan(version_dir: str, version: int) -> dict:
    """zone_import's plan of the interior folder (step 4); problems read as interior_setup errors."""
    try:
        plan, _manifest = zone_import.make_plan(version_dir, version)
    except zone_import.ZoneImportError as e:
        raise InteriorSetupError(e.step, e.message) from e
    zone_import.log_plan(plan)
    return plan


# ---- editor steps ----------------------------------------------------------------------------------------


def _find_zone_actor(zone_id: str):
    """The level's AGolmokZone with this zone_id, or None."""
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    for actor in actors:
        if isinstance(actor, unreal.GolmokZone) and str(actor.get_editor_property("zone_id")) == zone_id:
            return actor
    return None


def _sublevel_specs(manifest: dict) -> list[dict]:
    """The sublevel's actors (design D10): only point lights may go in."""
    try:
        specs = _pure.interior_sublevel_specs(manifest)
    except (KeyError, ValueError) as e:
        raise InteriorSetupError("sublevel", str(e) or type(e).__name__) from e
    other = [s.get("label") for s in specs if s.get("kind") != "point_light"]
    if other:
        raise InteriorSetupError(
            "sublevel", f"only point_light actors may go into the sublevel (design D10), not {other}"
        )
    return specs


def run(
    zone_dir, version=None, level=None, save=True, register=False, remeasure=False, reimport_textures=True
):
    """Import an interior zone folder ('.../<zone_id>', '.../<zone_id>/v<n>' or a manifest.json path), spawn
    its AGolmokZone (unloaded) and sublevel, and rebuild the parent zone in the open level (or in `level`,
    opened first). The parent zone must have been imported with zone_import.run into the same level.
    Returns the import_result dict (with its "interior" block). Raises InteriorSetupError(step, message).
    """
    version_dir, version, manifest = _interior_manifest(zone_dir, version)
    parent = manifest["parent_zone"]
    parent_manifest, parent_version = _parent_manifest(parent)
    check = _portal_check(parent_manifest, manifest)
    plan = _plan(version_dir, version)
    zone_id = plan["zone_id"]
    if level:
        with _step("level"):
            sz.open_or_create_level(level)
    with _step("parent"):
        parent_actor = _find_zone_actor(parent)
    if parent_actor is None:
        raise InteriorSetupError(
            "parent", f"Zone_{parent} not in level: run zone_import.run on the parent zone first"
        )
    work = zone_import.work_dir(plan)
    mappings, assets, warnings, route = zone_import.import_assets(plan, work, remeasure, reimport_textures)
    with _step("zone"):
        zone = sz.find_or_spawn_zone(zone_id, plan["version"])
        zone.rebuild_in_editor()  # editor check; the expected LogGolmok lines are in the runbook §4
        transform = zone.get_actor_transform()  # taken before unload_in_editor (runbook #11)
        zone.unload_in_editor()  # in PIE the parent's door portal loads it
    specs = _sublevel_specs(manifest)
    package = sz.sublevel_path(manifest)
    labels = [s["label"] for s in specs]
    with _step("sublevel"):
        return_level = level or sz._current_level_path()
        built = sz._spawn_interior_sublevel(
            manifest,
            transform,
            return_level,
            specs=specs,
            delete_tag=_pure.INTERIOR_SETUP_TAG,
            on_removed=lambda n: _log("is.rerun", n=n, package=package),
        )
        if built != package:
            raise RuntimeError(f"sublevel package {built} != {package}")
    _log("is.sublevel", package=package, actors=labels)
    if register:
        with _step("register"):
            sz.register_interior_sublevel(zone_id, plan["version"])
    with _step("exterior"):
        sz.find_or_spawn_zone(parent, parent_version).rebuild_in_editor()
    _log("is.exterior", zone_id=parent)
    if save:
        with _step("save"):
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    result = _pure.result_json(plan, mappings, assets, warnings, route)
    result["interior"] = {
        "sublevel": package,
        "round_trip": check,
        "parent": parent,
        "parent_version": parent_version,
        "actors": labels,
    }
    with _step("result"):
        result_path = zone_import.write_result(work, result)
    _log("is.done", zone_id=zone_id, version=plan["version"], result=result_path)
    for line in _pure.summary_lines(result):
        unreal.log(line)
    return result
