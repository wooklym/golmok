"""golmok/weather_setup.py on the scripted fake `unreal` (WP-16a design section 8, runbook pc-verify-wp16a).

Creation of MPC_GolmokWeather (three scalar parameters, default 0, saved), idempotence (a second run only
checks), a mismatching collection is an Error and is left untouched, and NS_GolmokRain is only reported.
"""

from __future__ import annotations

import importlib
import json

import fake_unreal
import pytest
from fake_unreal import FakeAsset, FakeMaterialParameterCollection
from golmok import weather_pure as wp

MPC = "/Game/Golmok/Weather/MPC_GolmokWeather"
NS = "/Game/Golmok/Weather/NS_GolmokRain"
PARAMS = [("RainIntensity", 0.0), ("Wetness", 0.0), ("PuddleAmount", 0.0)]
NAMES = "RainIntensity, Wetness, PuddleAmount"
MANUAL_MPC = "runbook pc-verify-wp16a §2a"


@pytest.fixture
def fake(monkeypatch, tmp_path):
    return fake_unreal.install(monkeypatch, tmp_path)


@pytest.fixture
def ws(fake):
    import golmok.weather_setup as module

    return importlib.reload(module)  # binds the freshly installed fake names


def _scalars(asset) -> list[tuple[str, float]]:
    return [
        (str(p.get_editor_property("parameter_name")), float(p.get_editor_property("default_value")))
        for p in asset.get_editor_property("scalar_parameters")
    ]


def _seed_mpc(fake, params) -> FakeMaterialParameterCollection:
    asset = FakeMaterialParameterCollection(fake, MPC)
    structs = []
    for name, default in params:
        structs.append(fake_unreal.CollectionScalarParameter(parameter_name=name, default_value=default))
    asset.set_editor_property("scalar_parameters", structs)
    fake.registry[asset.path] = asset
    return asset


# ---- pure ------------------------------------------------------------------------------------------------


def test_paths_come_from_weather_json():
    config = wp.load_config()
    assert config.mpc == f"{MPC}.MPC_GolmokWeather"
    assert config.rain_fx_system == f"{NS}.NS_GolmokRain"


def test_split_object_path(ws):
    expected = (MPC, "/Game/Golmok/Weather", "MPC_GolmokWeather")
    assert ws.split_object_path(f"{MPC}.MPC_GolmokWeather") == expected


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        (PARAMS, []),
        (PARAMS + [("Ripple", 0.5)], []),  # a 16b addition after the three
        (PARAMS[:2], ["scalar parameter PuddleAmount missing"]),
        ([PARAMS[1], PARAMS[0], PARAMS[2]], ["scalar parameter RainIntensity is #1, expected #0",
                                             "scalar parameter Wetness is #0, expected #1"]),
        ([("RainIntensity", 0.0), ("Wetness", 0.25), ("PuddleAmount", 0.0)],
         ["scalar parameter Wetness default 0.25, expected 0"]),
        ([], [f"scalar parameter {n} missing" for n in wp.MPC_PARAMETERS]),
    ],
)  # fmt: skip
def test_mpc_problems(params, expected, ws):
    assert ws.mpc_problems(params) == expected


# ---- editor ----------------------------------------------------------------------------------------------


def test_creates_the_collection_with_three_scalars(fake, ws):
    result = ws.run()
    assert result == {"mpc": MPC, "created": True, "problems": [], "rain_fx": NS, "rain_fx_exists": False}
    assert fake.calls_of("create_asset") == [
        ("create_asset", "MPC_GolmokWeather", "/Game/Golmok/Weather", "MaterialParameterCollection")
    ]
    assert fake.calls_of("save") == [("save", MPC)]
    asset = fake.registry[MPC]
    assert isinstance(asset, FakeMaterialParameterCollection)
    assert _scalars(asset) == PARAMS
    assert [n for n, _ in PARAMS] == list(wp.MPC_PARAMETERS)
    assert f"weather_setup: {MPC} created ({NAMES}, default 0)" in fake.logged("log")
    assert fake.logged("error") == []


def test_second_run_only_checks(fake, ws):
    ws.run()
    calls_before = list(fake.calls)
    result = ws.run()
    assert result["created"] is False and result["problems"] == []
    assert fake.calls == calls_before  # no create_asset, no save
    assert f"weather_setup: {MPC} ok ({NAMES}, default 0)" in fake.logged("log")
    assert fake.logged("error") == []


def test_existing_with_extra_parameter_is_kept(fake, ws):
    _seed_mpc(fake, PARAMS + [("Ripple", 0.5)])
    result = ws.run()
    assert result["problems"] == [] and fake.calls_of("save") == []
    assert f"weather_setup: {MPC} keeps 1 more: Ripple" in fake.logged("log")
    assert fake.logged("error") == []


@pytest.mark.parametrize(
    ("params", "problem"),
    [
        ([PARAMS[0], ("Wetness", 1.0), PARAMS[2]], "scalar parameter Wetness default 1"),
        ([PARAMS[0], ("Wet", 0.0), PARAMS[2]], "scalar parameter Wetness missing"),
    ],
)
def test_mismatch_is_an_error_and_not_modified(fake, ws, params, problem):
    asset = _seed_mpc(fake, params)
    result = ws.run()
    assert result["created"] is False
    assert any(p.startswith(problem) for p in result["problems"]), result["problems"]
    assert _scalars(asset) == params  # untouched
    assert fake.calls_of("save") == [] and fake.calls_of("create_asset") == []
    errors = fake.logged("error")
    assert errors and all(e.startswith(f"weather_setup: {MPC}: ") for e in errors)
    assert all(f"not modified, fix it by hand ({MANUAL_MPC})" in e for e in errors)
    assert not any(line.startswith(f"weather_setup: {MPC} ok") for line in fake.logged("log"))


def test_wrong_asset_class_is_an_error(fake, ws):
    fake.registry[MPC] = FakeAsset(fake, MPC)
    result = ws.run()
    assert result["problems"] == ["FakeAsset is not a MaterialParameterCollection"]
    assert len(fake.logged("error")) == 1 and fake.calls_of("save") == []


def test_python_cannot_write_scalars_names_the_manual_procedure(fake, ws, monkeypatch):
    monkeypatch.delattr(fake.module, "CollectionScalarParameter")  # [미확인 §17 #9]
    result = ws.run()
    assert result["created"] is True
    assert result["problems"][0].startswith("scalar_parameters not writable from Python")
    assert fake.calls_of("save") == [("save", MPC)]  # the empty collection stays for the manual step
    (error,) = fake.logged("error")
    assert error.startswith(f"weather_setup: {MPC} created but scalar_parameters not writable")
    assert f"add {NAMES} (default 0) by hand ({MANUAL_MPC})" in error


def test_rain_system_missing_is_a_warning(fake, ws):
    ws.run()
    assert fake.logged("warning") == [
        f"weather_setup: {NS} missing - author it with runbook pc-verify-wp16a §2b"
    ]


def test_rain_system_present_is_logged(fake, ws):
    fake.registry[NS] = FakeAsset(fake, NS)
    result = ws.run()
    assert result["rain_fx_exists"] is True
    assert f"weather_setup: {NS} ok" in fake.logged("log")
    assert fake.logged("warning") == []
    assert NS in fake.registry and fake.calls_of("save") == [("save", MPC)]  # never touched


def test_paths_follow_the_config_file(fake, ws, tmp_path):
    with open(wp.CONFIG_FILE, encoding="utf-8") as f:
        data = json.load(f)
    data["mpc"] = "/Game/Test/MPC_Other.MPC_Other"
    data["rain_fx"]["system"] = "/Game/Test/NS_Other.NS_Other"
    path = tmp_path / "weather.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = ws.run(str(path))
    assert result["mpc"] == "/Game/Test/MPC_Other" and result["rain_fx"] == "/Game/Test/NS_Other"
    assert "/Game/Test/MPC_Other" in fake.registry


def test_broken_config_raises_before_any_editor_call(fake, ws, tmp_path):
    path = tmp_path / "weather.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match=r"^weather\.json: schema_version: must be 1$"):
        ws.run(str(path))
    assert fake.calls == []
