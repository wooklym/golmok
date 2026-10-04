"""MPC_GolmokWeather and the NS_GolmokRain check (WP-16a design section 8; runbook pc-verify-wp16a §2).

    import golmok.weather_setup as w; w.run()

What it does (paths from Config/Golmok/weather.json through weather_pure.load_config, nothing hard-coded):
1. "mpc" missing: creates it with MaterialParameterCollectionFactoryNew, writes the three scalar parameters
   of weather_pure.MPC_PARAMETERS (RainIntensity, Wetness, PuddleAmount; that order, default 0) and saves it.
   When Python cannot write scalar_parameters [미확인 §17 #9] the empty collection is kept and an Error
   names the manual procedure (runbook §2a).
2. "mpc" present: only checks it. The three parameters must be the first scalar parameters, in order, with
   default 0; later ones are 16b additions and are kept. A mismatch is an Error and nothing is modified:
   16b materials reference this asset, so a rename here would break them (fix it by hand).
3. Logs whether "rain_fx.system" (NS_GolmokRain) exists; it is authored by hand from the recipe in
   runbook §2b (design 7-4), so a missing one is a Warning, not an Error.

The checks are pure functions (mpc_problems, split_object_path); the unreal calls are the thin adapters
below them (DEVELOPMENT-PLAN §7.5).
"""

from __future__ import annotations

import unreal

from . import weather_pure as wp

MANUAL_MPC = "runbook pc-verify-wp16a §2a"
MANUAL_NS = "runbook pc-verify-wp16a §2b"


# ---- pure -----------------------------------------------------------------------------------------------


def split_object_path(object_path: str) -> tuple[str, str, str]:
    """'/Game/A/B.B' -> (package '/Game/A/B', folder '/Game/A', asset name 'B')."""
    package = object_path.split(".", 1)[0]
    folder, _, name = package.rpartition("/")
    return package, folder, name


def mpc_problems(params: list[tuple[str, float]]) -> list[str]:
    """Problems of an existing collection's scalar parameters ([(name, default), ...] in asset order)."""
    problems = []
    names = [name for name, _ in params]
    for index, expected in enumerate(wp.MPC_PARAMETERS):
        if expected not in names:
            problems.append(f"scalar parameter {expected} missing")
            continue
        at = names.index(expected)
        if at != index:
            problems.append(f"scalar parameter {expected} is #{at}, expected #{index}")
        default = params[at][1]
        if default != 0.0:
            problems.append(f"scalar parameter {expected} default {default:g}, expected 0")
    return problems


# ---- unreal adapters ------------------------------------------------------------------------------------


def _read_scalars(mpc) -> list[tuple[str, float]]:
    return [
        (str(p.get_editor_property("parameter_name")), float(p.get_editor_property("default_value")))
        for p in mpc.get_editor_property("scalar_parameters")
    ]


def _write_scalars(mpc) -> None:
    params = []
    for name in wp.MPC_PARAMETERS:
        p = unreal.CollectionScalarParameter()
        p.set_editor_property("parameter_name", unreal.Name(name))
        p.set_editor_property("default_value", 0.0)
        params.append(p)
    mpc.set_editor_property("scalar_parameters", params)


def _create_mpc(package: str, folder: str, name: str) -> tuple[object, list[str]]:
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mpc = tools.create_asset(
        name, folder, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew()
    )
    if mpc is None:
        raise RuntimeError(f"weather_setup: could not create {package} (create it by hand: {MANUAL_MPC})")
    problems = []
    try:
        _write_scalars(mpc)
        problems = mpc_problems(_read_scalars(mpc))
    except Exception as e:  # [미확인 §17 #9] the struct or the property may not be writable from Python
        problems = [f"scalar_parameters not writable from Python ({type(e).__name__}: {e})"]
    if not unreal.EditorAssetLibrary.save_loaded_asset(mpc, only_if_is_dirty=False):
        raise RuntimeError(f"weather_setup: could not save {package}")
    return mpc, problems


def run(config_path: str | None = None) -> dict:
    """Creates or checks MPC_GolmokWeather and reports NS_GolmokRain; returns what it found (for tests)."""
    config = wp.load_config(config_path)
    package, folder, name = split_object_path(config.mpc)
    assets = unreal.EditorAssetLibrary
    created = False
    if assets.does_asset_exist(package):
        mpc = assets.load_asset(package)
        if not isinstance(mpc, unreal.MaterialParameterCollection):
            problems = [f"{type(mpc).__name__} is not a MaterialParameterCollection"]
        else:
            params = _read_scalars(mpc)
            problems = mpc_problems(params)
            if not problems and len(params) > len(wp.MPC_PARAMETERS):
                extra = ", ".join(n for n, _ in params[len(wp.MPC_PARAMETERS) :])
                unreal.log(
                    f"weather_setup: {package} keeps {len(params) - len(wp.MPC_PARAMETERS)} more: {extra}"
                )
        for problem in problems:
            unreal.log_error(
                f"weather_setup: {package}: {problem} - not modified, fix it by hand ({MANUAL_MPC})"
            )
    else:
        mpc, problems = _create_mpc(package, folder, name)
        created = True
        for problem in problems:
            unreal.log_error(
                f"weather_setup: {package} created but {problem} - add "
                f"{', '.join(wp.MPC_PARAMETERS)} (default 0) by hand ({MANUAL_MPC})"
            )
    if not problems:
        state = "created" if created else "ok"
        unreal.log(f"weather_setup: {package} {state} ({', '.join(wp.MPC_PARAMETERS)}, default 0)")

    system_package = split_object_path(config.rain_fx_system)[0]
    rain_fx_exists = bool(assets.does_asset_exist(system_package))
    if rain_fx_exists:
        unreal.log(f"weather_setup: {system_package} ok")
    else:
        unreal.log_warning(f"weather_setup: {system_package} missing - author it with {MANUAL_NS}")
    return {
        "mpc": package,
        "created": created,
        "problems": problems,
        "rain_fx": system_package,
        "rain_fx_exists": rain_fx_exists,
    }
