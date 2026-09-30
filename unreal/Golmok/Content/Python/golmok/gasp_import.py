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


def _class_name(asset) -> str:
    return asset.get_class().get_name() if hasattr(asset, "get_class") else type(asset).__name__


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


def migrate(closure_path, dest_content_dir) -> dict:
    """In the GASP project: migrate the closure of the roots into Golmok Content (conflicts skipped)."""
    roots = pure.parse_closure(pure.load_json(closure_path))
    registry = _wait_for_registry()
    library = unreal.EditorAssetLibrary
    found = [r for r in roots if library.does_asset_exist(r)]
    missing = [r for r in roots if r not in found]
    options = _dependency_options()

    def dependencies(package):
        return [str(d) for d in (registry.get_dependencies(unreal.Name(package), options) or [])]

    packages = pure.closure(found, dependencies)
    if not packages:
        raise RuntimeError(f"no closure root exists in this project: {roots}")
    existing = pure.packages_on_disk(dest_content_dir)
    migration = unreal.MigrationOptions()
    migration.set_editor_property("prompt", False)
    migration.set_editor_property("ignore_dependencies", True)  # the closure above is the dependency set
    migration.set_editor_property("asset_conflict", unreal.AssetMigrationConflict.SKIP)
    _tools().migrate_packages([unreal.Name(p) for p in packages], str(dest_content_dir), migration)
    after = pure.packages_on_disk(dest_content_dir)
    migrated = sorted(set(packages) - existing)
    not_copied = [p for p in migrated if p not in after]
    unreal.log(
        f"WP-19 add-gasp migrate: {len(packages)} closure packages, {len(migrated) - len(not_copied)} copied"
    )
    return {
        "ok": not not_copied,
        "exit": 0 if not not_copied else 1,
        "roots_missing": missing,
        "packages": packages,
        "existing_before": sorted(existing),
        "conflicts": sorted(set(packages) & existing),
        "migrated": [p for p in migrated if p not in not_copied],
        "not_copied": not_copied,
        "engine_version": unreal.SystemLibrary.get_engine_version(),
        "messages": [f"closure root not in the GASP project (19b fixes the path): {r}" for r in missing]
        + [
            f"kept the existing Golmok package (name conflict skipped): {p}"
            for p in sorted(set(packages) & existing)
        ],
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


def _fixup_redirectors(plan) -> list[str]:
    """Fix up and delete the redirectors the moves left behind (folders and single assets); returns what is
    still at an old path afterwards (must be nothing: no reference to the Migrate paths remains)."""
    library = unreal.EditorAssetLibrary

    def old_assets():
        paths = []
        for kind, source, _ in plan:
            if kind == "dir":
                if library.does_directory_exist(source):
                    paths.extend(library.list_assets(source, recursive=True, include_folder=False))
            elif library.does_asset_exist(source):
                paths.append(source)
        return paths

    redirectors = []
    for path in old_assets():
        asset = library.load_asset(path)
        if asset is not None and _class_name(asset) == "ObjectRedirector":
            redirectors.append(asset)
    if redirectors and hasattr(_tools(), "fixup_referencers"):
        _tools().fixup_referencers(redirectors)
    return old_assets()


def relocate(
    migrate_report, content_dir, local_dir, tags_path, gasp_project, content_root="/Game/GASP"
) -> dict:
    """In Golmok: move the migrated packages under content_root, then write the three local files."""
    report = pure.load_json(migrate_report)
    _wait_for_registry()  # the files migrate just copied must be discovered before the moves
    migrated = report["migrated"]
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
    gasp = Path(gasp_project)
    manifest = pure.build_manifest(content_dir, packages, root, gasp, report.get("engine_version", ""))
    pure.write_json(Path(local_dir) / "gasp_manifest.json", manifest)
    engine_ini = gasp / "Config" / "DefaultEngine.ini"
    cvars = pure.parse_cvars(engine_ini.read_text(encoding="utf-8-sig")) if engine_ini.is_file() else []
    pure.write_json(Path(local_dir) / "gasp_ddcvars.json", pure.ddcvars_json(cvars, engine_ini))
    tags_source = gasp / "Config" / "DefaultGameplayTags.ini"
    tags = pure.parse_tags(tags_source.read_text(encoding="utf-8-sig")) if tags_source.is_file() else []
    pure.write_text(tags_path, pure.tags_ini(tags, tags_source))
    unreal.log(
        f"WP-19 add-gasp relocate: {len(packages)} packages in {root}, {len(cvars)} DDCvars, {len(tags)} tags"
    )
    return {
        "ok": True,
        "exit": 0 if root == content_root else 2,
        "content_root": root,
        "moves": len(done),
        "planned": len(plan),
        "package_count": manifest["package_count"],
        "digest": manifest["digest"],
        "ddcvars": len(cvars),
        "tags": len(tags),
        "messages": messages,
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
        "messages": problems + warnings,
    }


def run_job(job: dict) -> dict:
    step = job.get("step")
    if step == "migrate":
        return migrate(job["closure"], job["dest_content"])
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
