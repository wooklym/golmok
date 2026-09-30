"""WP-19 (D-021) GASP setup, the thin `unreal` adapter of tools/ue/add-gasp.ps1 (design section 8).

Run by add-gasp.ps1 as `UnrealEditor-Cmd <project> -ExecutePythonScript=<this file>` with the job file path
in the GOLMOK_GASP_JOB environment variable; each step writes its result JSON (job["result"]) and quits:

    migrate   (GASP project)   dependency closure of tools/ue/gasp/closure.json -> AssetTools.migrate_packages
                               into Golmok Content (name conflicts skipped; the GASP project is not modified)
    relocate  (Golmok project) rename_directory / rename_asset to /Game/GASP/<...> (relocation_plan),
                               redirector fix-up, then Config/Golmok/local/gasp_manifest.json and
                               gasp_ddcvars.json, Config/Tags/GASP.ini; a failed move is rolled back and
                               content_root stays /Game (exit 2)
    verify    (Golmok project) manifest sizes / hashes, ABP / BPI classes load, 27 DDCvars / 39 tags,
                               tools/ue/gasp/expected.json, and no GASP path committable in git status

Nothing here is committed or uploaded; the calculations are in golmok.gasp_pure (cloud pytest).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

if __package__ in (None, ""):  # -ExecutePythonScript runs this file as a script: make `golmok` importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import unreal  # noqa: E402

from golmok import gasp_pure as pure  # noqa: E402

JOB_ENV = "GOLMOK_GASP_JOB"


def _tools():
    return unreal.AssetToolsHelpers.get_asset_tools()


def _wait_for_registry():
    """-ExecutePythonScript can run while the asset registry still scans: finish the scan first."""
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    if hasattr(registry, "wait_for_completion"):
        registry.wait_for_completion()
    return registry


def _dependency_options():
    options = unreal.AssetRegistryDependencyOptions()
    for name, value in (
        ("include_soft_package_references", True),
        ("include_hard_package_references", True),
        ("include_searchable_names", False),
        ("include_soft_management_references", False),
        ("include_hard_management_references", False),
    ):
        options.set_editor_property(name, value)
    return options


def _project_content_dir() -> Path:
    paths = unreal.Paths
    return Path(paths.convert_relative_path_to_full(paths.project_content_dir()))


def _same_file(a: Path | None, b: Path | None) -> bool:
    return (
        a is not None
        and b is not None
        and a.stat().st_size == b.stat().st_size
        and pure.sha256_file(a) == pure.sha256_file(b)
    )


def migrate(closure_path, dest_content_dir, source_content_dir=None, history_path=None) -> dict:
    """In the GASP project: migrate the closure of the roots into Golmok Content (conflicts skipped).

    Nothing is copied unless the preconditions hold (review R76 T1, T4): no /Game/GASP install, no leftover of
    an earlier run at the Migrate paths, no /Game dependency with a name UE cannot hold. The GASP files of the
    closure are hashed before and after the copy (source_digest, R76 T2: the acquired GASP, pinned by
    tools/ue/gasp/expected.json); every package copied is added to the migrate history of this checkout.
    """
    roots = pure.parse_closure(pure.load_json(closure_path))
    registry = _wait_for_registry()
    library = unreal.EditorAssetLibrary
    found = [r for r in roots if library.does_asset_exist(r)]
    missing = [r for r in roots if r not in found]
    options = _dependency_options()

    def dependencies(package):
        return [str(d) for d in (registry.get_dependencies(unreal.Name(package), options) or [])]

    packages, rejected = pure.closure(found, dependencies)
    if not packages:
        raise RuntimeError(f"no closure root exists in this project: {roots}")
    dest = Path(dest_content_dir)
    source = Path(source_content_dir) if source_content_dir else _project_content_dir()
    existing = pure.packages_on_disk(dest)
    conflicts = sorted(set(packages) & existing)
    pre = pure.migrate_preconditions(
        packages,
        existing,
        pure.load_history(history_path),
        lambda p: _same_file(pure.package_file(dest, p), pure.package_file(source, p)),
    )
    report = {
        "roots_missing": missing,
        "packages": packages,
        "existing_before": sorted(existing),
        "conflicts": conflicts,
        "rejected": rejected,
        "leftovers": pre["leftovers"],
        "delete": pre["delete"],
        "engine_version": unreal.SystemLibrary.get_engine_version(),
    }
    notes = [f"closure root not in the GASP project (19b fixes the path): {r}" for r in missing]
    problems = [
        f"/Game dependency with a name no package can have (not copied; report it): {r}" for r in rejected
    ] + pre["problems"]
    try:  # the GASP ini text must be usable before 1 GB is copied (R76 T1, verification B)
        _read_local_files(source.parent)
    except ValueError as error:
        problems.append(f"GASP ini: {error}")
    if problems:
        unreal.log_warning(f"WP-19 add-gasp migrate: stopped before copying ({len(problems)} problems)")
        return {
            **report,
            "ok": False,
            "exit": 1,
            "migrated": [],
            "not_copied": [],
            "messages": notes + problems,
        }

    before = pure.source_entries(source, packages)
    source_digest = pure.aggregate_digest(before)
    migration = unreal.MigrationOptions()
    migration.set_editor_property("prompt", False)
    migration.set_editor_property("ignore_dependencies", True)  # the closure above is the dependency set
    migration.set_editor_property("asset_conflict", unreal.AssetMigrationConflict.SKIP)
    migrated = sorted(set(packages) - existing)
    # Recorded before copying: an editor that dies mid-copy leaves partly written files that neither the
    # history nor a byte match would catch, and the next run would skip them as name conflicts (review R78-1).
    pure.record_history(history_path, migrated)
    _tools().migrate_packages([unreal.Name(p) for p in packages], str(dest), migration)
    after = pure.packages_on_disk(dest)
    not_copied = [p for p in migrated if p not in after]
    copied = [p for p in migrated if p not in not_copied]
    unchanged = pure.aggregate_digest(pure.source_entries(source, packages)) == source_digest
    unreal.log(f"WP-19 add-gasp migrate: {len(packages)} closure packages, {len(copied)} copied")
    messages = notes + [f"kept the existing Golmok package (name conflict skipped): {p}" for p in conflicts]
    messages += [f"not copied: {p}" for p in not_copied]
    if not unchanged:
        messages.append(
            "GASP project changed during migrate (its closure files differ before / after): add-gasp only "
            "reads it; do not open and save the GASP project, re-create it from Fab if in doubt"
        )
    return {
        **report,
        "ok": not not_copied,
        "exit": 0 if not not_copied else 1,
        "migrated": copied,
        "not_copied": not_copied,
        "source_digest": source_digest,
        "source_package_count": len(before),
        "source_unchanged": unchanged,
        "messages": messages,
    }


def _apply(plan) -> list[tuple[str, str, str]]:
    """Runs the moves in order; returns the ones that succeeded until the first failure (then stops)."""
    library = unreal.EditorAssetLibrary
    done = []
    for kind, source, destination in plan:
        mover = library.rename_directory if kind == "dir" else library.rename_asset
        if not mover(source, destination):
            unreal.log_warning(f"WP-19 add-gasp: {kind} move failed: {source} -> {destination}")
            break
        done.append((kind, source, destination))
    return done


def _assets_at(registry, plan) -> list:
    """AssetData still registered at the old paths of the plan (folders recursively, assets by name)."""
    found = []
    for kind, source, _ in plan:
        if kind == "dir":
            query = unreal.ARFilter(package_paths=[unreal.Name(source)], recursive_paths=True)
        else:
            query = unreal.ARFilter(package_names=[unreal.Name(source)])
        found.extend(registry.get_assets(query) or [])
    return found


def _is_redirector(data) -> bool:
    helpers = unreal.AssetRegistryHelpers
    if hasattr(helpers, "is_redirector"):
        return bool(helpers.is_redirector(data))
    return str(data.get_editor_property("asset_class_path").asset_name) == "ObjectRedirector"


def _fixup_redirectors(plan) -> list[str]:
    """Fix up and delete the redirectors the moves left behind (folders and single assets), found through the
    asset registry (review R76 T5: no load_asset guess); returns the packages still at an old path afterwards
    (must be nothing: no reference to the Migrate paths remains)."""
    registry = _wait_for_registry()
    redirectors = [d.get_asset() for d in _assets_at(registry, plan) if _is_redirector(d)]
    redirectors = [r for r in redirectors if r is not None]
    if redirectors and hasattr(_tools(), "fixup_referencers"):
        _tools().fixup_referencers(redirectors)
    return sorted({str(d.package_name) for d in _assets_at(registry, plan)})


def _read_local_files(gasp: Path) -> dict:
    """GASP DDCvar / tag ini text -> the two local files' data (checked before anything is copied or moved,
    R76 T1): both files must exist and hold the V-08 counts, so a wrong project never writes empty files."""
    engine_ini = gasp / "Config" / "DefaultEngine.ini"
    tags_source = gasp / "Config" / "DefaultGameplayTags.ini"
    for path in (engine_ini, tags_source):
        if not path.is_file():
            raise ValueError(f"{path} is missing (is {gasp} the GASP 5.8 project?)")
    cvars = pure.parse_cvars(engine_ini.read_text(encoding="utf-8-sig"))
    tags = pure.parse_tags(tags_source.read_text(encoding="utf-8-sig"))
    if len(cvars) != pure.EXPECTED_DDCVARS or len(tags) != pure.EXPECTED_TAGS:
        raise ValueError(
            f"{len(cvars)} DDCvars / {len(tags)} tags in the GASP ini, expected "
            f"{pure.EXPECTED_DDCVARS} / {pure.EXPECTED_TAGS} (V-08); nothing written"
        )
    return {"cvars": cvars, "engine_ini": engine_ini, "tags": tags, "tags_source": tags_source}


def _write_local_files(local_dir, tags_path, data) -> None:
    pure.write_json(
        Path(local_dir) / "gasp_ddcvars.json", pure.ddcvars_json(data["cvars"], data["engine_ini"])
    )
    pure.write_text(tags_path, pure.tags_ini(data["tags"], data["tags_source"]))


def local_files(local_dir, tags_path, gasp_project) -> dict:
    """add-gasp.ps1 -LocalFiles: rewrite only gasp_ddcvars.json and Config/Tags/GASP.ini (nothing moves)."""
    try:
        data = _read_local_files(Path(gasp_project))
    except ValueError as error:
        return {"ok": False, "exit": 1, "messages": [f"GASP ini: {error}; local files kept"]}
    _write_local_files(local_dir, tags_path, data)
    unreal.log(f"WP-19 add-gasp local_files: {len(data['cvars'])} DDCvars, {len(data['tags'])} tags")
    return {"ok": True, "exit": 0, "ddcvars": len(data["cvars"]), "tags": len(data["tags"]), "messages": []}


def relocate(
    migrate_report, content_dir, local_dir, tags_path, gasp_project, content_root="/Game/GASP"
) -> dict:
    """In Golmok: move the migrated packages under content_root, then write the three local files.

    A migrate report that is not ok or copied nothing is refused and the previous manifest stays (R76 T1).
    """
    report = pure.load_json(migrate_report)
    migrated = report.get("migrated") or []
    if not report.get("ok") or not migrated:
        return {
            "ok": False,
            "exit": 1,
            "package_count": 0,
            "messages": [
                "migrate report is not ok or has no migrated package: nothing relocated, the previous "
                "manifest is kept (see the migrate messages; runbook A3 re-run)"
            ],
        }
    gasp = Path(gasp_project)
    try:
        local = _read_local_files(gasp)
    except ValueError as error:
        return {
            "ok": False,
            "exit": 1,
            "package_count": 0,
            "messages": [f"GASP ini: {error}; nothing moved (fix it, then re-run add-gasp)"],
        }
    _wait_for_registry()  # the files migrate just copied must be discovered before the moves
    plan = pure.relocation_plan(migrated, report["existing_before"], content_root)
    done = _apply(plan)
    messages = []
    left = [] if len(done) != len(plan) else _fixup_redirectors(plan)
    root = content_root
    if len(done) != len(plan) or left:
        # Roll back to the Migrate paths: content_root "/Game" (animation.json must say so; exit 2).
        for kind, source, destination in reversed(done):
            mover = (
                unreal.EditorAssetLibrary.rename_directory
                if kind == "dir"
                else unreal.EditorAssetLibrary.rename_asset
            )
            mover(destination, source)
        root = "/Game"
        messages.append(
            f"rename to {content_root} failed ({len(done)}/{len(plan)} moves, {len(left)} old-path assets); "
            "GASP stays at the Migrate paths: set animation.json gasp.content_root to /Game"
        )
    packages = [pure.map_to_root(p, root) for p in migrated]
    source = {k: report.get(k) for k in ("source_digest", "source_package_count")}
    manifest = pure.build_manifest(
        content_dir, packages, root, gasp, report.get("engine_version", ""), source=source
    )
    pure.write_json(Path(local_dir) / "gasp_manifest.json", manifest)
    _write_local_files(local_dir, tags_path, local)
    unreal.log(
        f"WP-19 add-gasp relocate: {len(packages)} packages in {root}, {len(local['cvars'])} DDCvars, "
        f"{len(local['tags'])} tags"
    )
    return {
        "ok": True,
        "exit": 0 if root == content_root else 2,
        "content_root": root,
        "moves": len(done),
        "planned": len(plan),
        "package_count": manifest["package_count"],
        "digest": manifest["digest"],
        "source_digest": manifest["source_digest"],
        "ddcvars": len(local["cvars"]),
        "tags": len(local["tags"]),
        "messages": messages,
    }


def manifest(migrate_report, content_dir, local_dir, gasp_project) -> dict:
    """add-gasp.ps1 -Manifest: rewrite gasp_manifest.json for the packages of the last successful migrate
    where they are now (/Game/GASP or the Migrate paths), e.g. after a GUI Move + Fix Up Redirectors (runbook
    section C #16). Nothing moves."""
    report = pure.load_json(migrate_report)
    migrated = report.get("migrated") or []
    root = pure.installed_root(content_dir, migrated)
    if not report.get("ok") or root is None:
        return {
            "ok": False,
            "exit": 1,
            "messages": [
                f"{len(migrated)} migrated packages are neither all under /Game/GASP nor all at their "
                "Migrate paths: manifest not written"
            ],
        }
    source = {k: report.get(k) for k in ("source_digest", "source_package_count")}
    packages = [pure.map_to_root(p, root) for p in migrated]
    data = pure.build_manifest(
        content_dir, packages, root, Path(gasp_project), report.get("engine_version", ""), source=source
    )
    pure.write_json(Path(local_dir) / "gasp_manifest.json", data)
    return {
        "ok": True,
        "exit": 0,
        "content_root": root,
        "package_count": data["package_count"],
        "digest": data["digest"],
        "source_digest": data["source_digest"],
        "messages": [f"manifest rewritten: {data['package_count']} packages in {root}"],
    }


def _class_loads(path) -> bool:
    try:
        return unreal.load_class(None, path) is not None
    except Exception:  # noqa: BLE001 - a missing class raises in some engine versions
        return False


def verify(
    content_dir, local_dir, tags_path, expected_path, git_status_path, animation_json=pure.ANIMATION_JSON
) -> dict:
    """In Golmok: the manifest matches the files, classes load, the ini counts and git status are clean."""
    problems, warnings = [], []
    manifest_path = Path(local_dir) / "gasp_manifest.json"
    if not manifest_path.is_file():
        return {
            "ok": False,
            "exit": 1,
            "messages": [f"no {manifest_path.name}: run add-gasp.ps1 without -Verify first"],
        }
    manifest = pure.load_json(manifest_path)
    problems += pure.check_manifest(content_dir, manifest)
    if not manifest.get("source_digest"):
        problems.append("manifest has no source_digest (a 19a install): re-install (runbook A3)")
    config = pure.load_animation_config(animation_json)
    if config["content_root"] != manifest["content_root"]:
        problems.append(
            f"animation.json content_root {config['content_root']} != installed {manifest['content_root']}"
            f" (set animation.json content_root to {manifest['content_root']})"
        )
    for key in ("anim_class", "pawn_interface"):
        path = pure.asset_path(manifest["content_root"], config[key])
        if not _class_loads(path):
            problems.append(f"{key} does not load: {path}")
    ddcvars_path = Path(local_dir) / "gasp_ddcvars.json"
    cvars = pure.load_json(ddcvars_path)["cvars"] if ddcvars_path.is_file() else []
    if len(cvars) != pure.EXPECTED_DDCVARS:
        problems.append(f"{len(cvars)} DDCvars in {ddcvars_path.name}, expected {pure.EXPECTED_DDCVARS}")
    tags_text = Path(tags_path).read_text(encoding="utf-8") if Path(tags_path).is_file() else ""
    tag_count = sum(1 for line in tags_text.splitlines() if line.startswith("GameplayTagList="))
    if tag_count != pure.EXPECTED_TAGS:
        problems.append(f"{tag_count} tags in {Path(tags_path).name}, expected {pure.EXPECTED_TAGS}")
    note = pure.compare_expected(manifest, pure.load_json(expected_path))
    if note:
        warnings.append(note)
    porcelain = Path(git_status_path).read_text(encoding="utf-8") if Path(git_status_path).is_file() else ""
    leaks = pure.committable_local_paths(porcelain)
    problems += [f"committable GASP / local path (never git add it): {p}" for p in leaks]
    unreal.log(f"WP-19 add-gasp verify: {len(problems)} problems, {len(warnings)} warnings")
    return {
        "ok": not problems,
        "exit": 0 if not problems else 1,
        "package_count": manifest.get("package_count"),
        "digest": manifest.get("digest"),
        "source_digest": manifest.get("source_digest"),
        "source_package_count": manifest.get("source_package_count"),
        "messages": problems + warnings,
    }


def run_job(job: dict) -> dict:
    step = job.get("step")
    if step == "migrate":
        return migrate(job["closure"], job["dest_content"], job.get("source_content"), job.get("history"))
    if step == "local_files":
        return local_files(job["local_dir"], job["tags_ini"], job["gasp_project"])
    if step == "manifest":
        return manifest(job["migrate_report"], job["content_dir"], job["local_dir"], job["gasp_project"])
    if step == "relocate":
        return relocate(
            job["migrate_report"], job["content_dir"], job["local_dir"], job["tags_ini"], job["gasp_project"]
        )
    if step == "verify":
        return verify(
            job["content_dir"], job["local_dir"], job["tags_ini"], job["expected"], job["git_status"]
        )
    raise ValueError(f"unknown add-gasp step {step!r}")


def main() -> int:
    job_path = os.environ.get(JOB_ENV)
    if not job_path:
        unreal.log_error(f"WP-19 add-gasp: {JOB_ENV} is not set (run tools/ue/add-gasp.ps1)")
        return 1
    result_path = None
    try:
        job = pure.load_json(job_path)
        result_path = job["result"]
        result = run_job(job)
    except Exception as error:  # noqa: BLE001 - reported to add-gasp.ps1 through the result file
        result = {"ok": False, "exit": 1, "messages": [f"{type(error).__name__}: {error}"]}
    if result_path:
        pure.write_json(result_path, result)
    for message in result.get("messages", []):
        unreal.log_warning(f"WP-19 add-gasp: {message}")
    return int(result["exit"])


if __name__ == "__main__":
    try:
        main()  # add-gasp.ps1 reads the exit code from the result file
    finally:
        unreal.SystemLibrary.quit_editor()  # never leave the headless editor running
