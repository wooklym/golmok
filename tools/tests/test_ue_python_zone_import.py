"""golmok/zone_import.py on the scripted fake `unreal` (WP-06 design §5-3) with the generated synthetic zone.

One synthetic zone (--interior, non-ASCII folder) is generated per module; tests that break files copy the
whole output tree into their own tmp_path (the MTL texture paths are relative to it). Every test installs
fake_unreal for its own duration, so the importer mapping cache lives in that test's Saved folder.
"""

from __future__ import annotations

import importlib
import json
import re
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("scipy")
pytest.importorskip("fast_simplification")

import fake_unreal  # noqa: E402
from fake_unreal import DEFAULT_LEVEL, M_GLB, M_OBJ  # noqa: E402
from golmok import _pure as pure  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "make_synthetic_zone.py"
GOLMOK_DIR = Path(__file__).resolve().parents[2] / "unreal" / "Golmok" / "Content" / "Python" / "golmok"
ZONE = "z_synthetic_scan_001"
ROOM = f"{ZONE}_room"
FOLDER = f"/Game/Golmok/Zones/{ZONE}/v1"
ROOM_FOLDER = f"/Game/Golmok/Zones/{ROOM}/v1"
MATERIALS = "/Game/Golmok/Materials"
M_ZONE_SCAN = f"{MATERIALS}/M_ZoneScan"
M_ZONE_SCAN_NOVT = f"{MATERIALS}/M_ZoneScan_NoVT"
DEFAULT_TEX = f"{MATERIALS}/T_ZoneScanDefault"  # the masters' own default textures (runbook #10)
DEFAULT_TEX_NOVT = f"{MATERIALS}/T_ZoneScanDefault_NoVT"
PROBE = f"{FOLDER}/_probe"
TILES = f"{FOLDER}/Textures/_tiles"
IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
SWAP_XY = ((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
CHUNKS = ("c_e000_n000", "c_w001_n000")  # plan order (sorted ids)


# ---- fixtures ------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    """One generated synthetic zone (with the interior room) shared by the module, in a non-ASCII folder."""
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        msz = importlib.import_module("make_synthetic_zone")
    finally:
        sys.path.remove(str(SCRIPT.parent))
    out = tmp_path_factory.mktemp("합성 zone")
    assert msz.main(["--out", str(out), "--interior", "--quiet"]) == 0
    return out


def _view(out: Path) -> SimpleNamespace:
    version = out / "zones" / ZONE / "v1"
    return SimpleNamespace(
        out=out,
        dir=out / "zones" / ZONE,
        version=version,
        room=out / "zones" / ROOM,
        expected=json.loads((version / "expected.json").read_text("utf-8")),
        tex=out / "recon" / ZONE / "tex",
    )


@pytest.fixture
def zone(generated) -> SimpleNamespace:
    """Read-only view of the generated zone."""
    return _view(generated)


@pytest.fixture
def zone_copy(generated, tmp_path) -> SimpleNamespace:
    """A private copy of the whole generated tree for tests that break files."""
    out = tmp_path / "zone copy"
    shutil.copytree(generated, out)
    return _view(out)


@pytest.fixture
def fake(monkeypatch, tmp_path):
    return fake_unreal.install(monkeypatch, tmp_path)


@pytest.fixture
def unreal(fake):
    return fake.module


@pytest.fixture
def zi(fake):
    return importlib.import_module("golmok.zone_import")


# ---- helpers -------------------------------------------------------------------------------------------


def _run(zi, zone, **kw):
    kw.setdefault("level", DEFAULT_LEVEL)
    kw.setdefault("geo_origin", "area")
    return zi.run(str(zone.dir), **kw)


def _usemtl(zone, cid: str) -> list[str]:
    lines = (zone.version / "visual" / f"{cid}.obj").read_text("utf-8").splitlines()
    return pure.usemtl_order(lines)


def _expected_assets(expected: dict) -> set[str]:
    folder = expected["asset_folder"]
    out = {c["asset"] for c in expected["chunks"].values()}
    out |= {c["asset"] for c in expected["collision"]["chunks"].values()}
    out |= {f"{folder}/Textures/{name}" for name in expected["textures"]}
    out |= {f"{folder}/Materials/{name}" for name in expected["materials"]}
    assert all(a.startswith("/Game/") for a in out)
    return out


def _imports(fake, suffix: str | None = None) -> list[tuple]:
    return [c for c in fake.calls_of("import") if suffix is None or c[1].endswith(suffix)]


def _geo_actors(fake, unreal):
    return [a for a in fake.actors if isinstance(a, unreal.GolmokGeoOrigin)]


def _logs(fake, prefix: str) -> list[str]:
    return [t for t in fake.logged("log") if t.startswith(prefix)]


# ---- run order, registry, logs ---------------------------------------------------------------------------


def test_run_call_order_and_registry(fake, unreal, zone, zi):
    result = _run(zi, zone)
    calls = [
        ("load_level", DEFAULT_LEVEL),
        ("import", "_probe.obj", PROBE, "SM_probe", "fbx"),
        ("delete_directory", PROBE),
        ("import", "_probe.glb", PROBE, "SM_probe_glb", None),
        ("delete_directory", PROBE),
        # V-03 (pc-findings #1): every import goes to a scratch _import folder and is moved to its path
        ("import", "facade.1001.png", f"{FOLDER}/Textures/_import", "T_facade", None),
        ("rename", f"{FOLDER}/Textures/_import/T_facade", f"{FOLDER}/Textures/T_facade"),
        ("save", f"{FOLDER}/Textures/T_facade"),
        ("import", "ground.png", f"{FOLDER}/Textures/_import", "T_ground", None),
        ("rename", f"{FOLDER}/Textures/_import/T_ground", f"{FOLDER}/Textures/T_ground"),
        ("save", f"{FOLDER}/Textures/T_ground"),
        # the master's own default texture (never a zone texture; runbook #10), created once
        ("import", "T_ZoneScanDefault.png", f"{MATERIALS}/_import", "T_ZoneScanDefault", None),
        ("rename", f"{MATERIALS}/_import/T_ZoneScanDefault", DEFAULT_TEX),
        ("save", DEFAULT_TEX),
        ("create_asset", "M_ZoneScan", MATERIALS, "Material"),
        ("save", M_ZONE_SCAN),
        ("create_asset", "MI_facade", f"{FOLDER}/Materials", "MaterialInstanceConstant"),
        ("save", f"{FOLDER}/Materials/MI_facade"),
        ("create_asset", "MI_ground", f"{FOLDER}/Materials", "MaterialInstanceConstant"),
        ("save", f"{FOLDER}/Materials/MI_ground"),
    ]
    for cid in CHUNKS:
        mesh, usemtl = f"{FOLDER}/SM_{cid}", _usemtl(zone, cid)
        assert sorted(usemtl) == ["facade", "ground"]
        calls.append(("import", f"SM_{cid}.obj", f"{FOLDER}/_import", f"SM_{cid}", "fbx"))
        calls.append(("rename", f"{FOLDER}/_import/SM_{cid}", mesh))
        calls += [("delete_asset", f"{FOLDER}/_import/{m}") for m in usemtl]  # importer by-products
        calls.append(("set_nanite", mesh, True))
        calls += [("set_material", mesh, i, f"{FOLDER}/Materials/MI_{m}") for i, m in enumerate(usemtl)]
        calls.append(("save", mesh))
    for cid in CHUNKS:
        name = f"SM_{ZONE}_collision_{cid}"
        calls += [
            ("import", f"{name}.glb", f"{FOLDER}/_import", name, None),
            ("rename", f"{FOLDER}/_import/{name}", f"{FOLDER}/{name}"),
            ("set_nanite", f"{FOLDER}/{name}", False),
            ("save", f"{FOLDER}/{name}"),
        ]
    calls += [
        ("spawn", "GolmokGeoOrigin", "GeoOrigin"),
        ("spawn", "GolmokZone", f"Zone_{ZONE}"),
        ("rebuild_in_editor", ZONE),
        ("save_current_level",),
    ]
    assert fake.calls == calls
    assert set(fake.registry) == _expected_assets(zone.expected) | {DEFAULT_LEVEL, M_ZONE_SCAN, DEFAULT_TEX}
    assert not [k for k in fake.registry if "_probe" in k or "_tiles" in k or "/_import" in k]
    default = fake.registry[M_ZONE_SCAN].expressions[0].props["texture"]
    assert default is fake.registry[DEFAULT_TEX] and default.get_editor_property("virtual_texture_streaming")
    png_tasks = [t for t in fake.tasks if t.filename.endswith(".png")]
    udim = {
        Path(t.filename).name: t.options.material_pipeline.texture_pipeline.import_udi_ms for t in png_tasks
    }
    assert udim == {"facade.1001.png": True, "ground.png": False, "T_ZoneScanDefault.png": False}
    assert f"{FOLDER}/SM_{ZONE}_collision" not in fake.registry  # collision.glb is not imported (D7)
    assert [c[1] for c in _imports(fake, ".glb")] == ["_probe.glb"] + [
        f"SM_{ZONE}_collision_{cid}.glb" for cid in CHUNKS
    ]
    assert result["route"] == "fbx" and len(result["assets"]) == 10
    # the runbook §2 expected lines (values from expected.json)
    logs = fake.logged("log")
    result_path = Path(fake.saved_dir) / "Golmok" / "zone_import" / ZONE / "v1" / "import_result.json"
    for line in (
        f"zone_import: plan {ZONE} v1: chunks=2 collision=2 (chunks) textures=2 materials=2 blockers=1",
        "zone_import: obj importer route=fbx (probe imported 1 static mesh)",
        f"zone_import: texture {FOLDER}/Textures/T_facade tiles=[1001, 1002, 1011] size=512x512 vt=on "
        "(merged by importer)",
        f"zone_import: texture {FOLDER}/Textures/T_ground tiles=[] size=256x256 vt=on (single texture)",
        f"zone_import: material {FOLDER}/Materials/MI_facade parent={M_ZONE_SCAN} texture=T_facade",
        f"zone_import: material {FOLDER}/Materials/MI_ground parent={M_ZONE_SCAN} texture=T_ground",
        f"zone_import: chunk {FOLDER}/SM_c_e000_n000 tris=66 bounds ok (error 0.00 cm) "
        "slots=facade=MI_facade,ground=MI_ground",
        f"zone_import: collision {FOLDER}/SM_{ZONE}_collision_c_w001_n000 bounds ok (error 0.00 cm) "
        "complex-as-simple nanite=off",
        f"zone_import: copied blockers.json, manifest.json -> "
        f"{Path(fake.content_dir) / 'Golmok' / 'Zones' / ZONE / 'v1'}",
        "zone_import: geo origin lat=37.560000 lon=126.923000 h=40.000 (spec area origin)",
        f"zone_import: zone Zone_{ZONE} rebuilt",
        f"zone_import: done {ZONE} v1: 8 assets, 0 warnings -> {result_path}",
        f"zone_import: moved {FOLDER}/_import/SM_c_e000_n000 -> {FOLDER}/SM_c_e000_n000 "
        "(importer placement; runbook #37)",
        f"zone_import: moved {FOLDER}/Textures/_import/T_facade -> {FOLDER}/Textures/T_facade "
        "(importer placement; runbook #37)",
    ):
        assert line in logs, line
    cache = Path(fake.saved_dir) / "Golmok" / "zone_import" / "importer_mapping.json"
    assert logs.index(f"zone_import: importer mapping cache miss -> {cache}") < logs.index(
        "zone_import: obj importer route=fbx (probe imported 1 static mesh)"
    )
    assert f"zone_import: obj importer mapping scale=100.000 M={M_OBJ} (fit error 0.00 cm)" in logs
    assert f"zone_import: glb importer mapping scale=100.000 M={IDENTITY} (fit error 0.00 cm)" in logs
    assert fake.logged("warning") == []
    assert all(line in logs for line in pure.summary_lines(result))
    # every log line of the module goes through _pure.LOG (runbook drift test) or is a summary line
    prefixes = tuple(pure.log_prefixes().values())
    for text in logs:
        assert text.startswith(prefixes) or text.startswith("  - ") or text.startswith("Created "), text
    # runbook §2 quotes the first-run master line between the texture and the material lines
    created = logs.index(f"Created {M_ZONE_SCAN}")
    last_texture = max(i for i, text in enumerate(logs) if text.startswith("zone_import: texture "))
    first_material = min(i for i, text in enumerate(logs) if text.startswith("zone_import: material "))
    assert last_texture < created < first_material


@pytest.mark.parametrize("kind", ["obj", "glb"])
@pytest.mark.parametrize("case", ["default", "identity_m", "swap_xy_cm"])
def test_bounds_are_zone_local_ue_cm(monkeypatch, tmp_path, zone, kind, case):
    mapping = {
        "default": (100.0, M_OBJ if kind == "obj" else M_GLB),
        "identity_m": (1.0, IDENTITY),
        "swap_xy_cm": (100.0, SWAP_XY),
    }[case]
    fake = fake_unreal.install(monkeypatch, tmp_path, **{f"{kind}_mapping": mapping})
    zi = importlib.import_module("golmok.zone_import")
    result = _run(zi, zone)
    for c in zone.expected["chunks"].values():
        got = fake.registry[c["asset"]].bounds
        assert [*got[0], *got[1]] == pytest.approx([*c["ue_bounds_cm"][0], *c["ue_bounds_cm"][1]], abs=0.01)
    for c in zone.expected["collision"]["chunks"].values():
        got = fake.registry[c["asset"]].bounds
        assert [*got[0], *got[1]] == pytest.approx([*c["ue_bounds_cm"][0], *c["ue_bounds_cm"][1]], abs=0.01)
    assert result[f"{kind}_mapping"]["scale"] == pytest.approx(mapping[0])
    assert all(
        a["detail"]["bounds_error_cm"] < 0.01
        for a in result["assets"]
        if a["kind"] != "file" and "bounds_error_cm" in a["detail"]
    )
    # the pre-transformed copies are what the importer read
    work = Path(fake.saved_dir) / "Golmok" / "zone_import" / ZONE / "v1"
    assert sorted(p.name for p in (work / "visual").iterdir()) == [
        "SM_c_e000_n000.obj",
        "SM_c_w001_n000.obj",
        "scan.mtl",
    ]
    assert sorted(p.name for p in (work / "collision").iterdir()) == [
        f"SM_{ZONE}_collision_{cid}.glb" for cid in CHUNKS
    ]
    mtl = (work / "visual" / "scan.mtl").read_text("utf-8")
    assert f"map_Kd -bm 1 {(zone.tex / 'facade.<UDIM>.png').as_posix()}" in mtl  # absolute texture paths


def test_route_ladder(fake, unreal, zone, zi):
    fake.obj_routes_ok = {"interchange"}
    _run(zi, zone)
    assert [c[4] for c in _imports(fake, ".obj")] == ["fbx", "interchange", "interchange", "interchange"]
    assert "zone_import: obj importer route=interchange (probe imported 1 static mesh)" in fake.logged("log")
    assert ("console", "Interchange.FeatureFlags.Import.OBJ 0") not in fake.calls
    assert isinstance(fake.tasks[-3].options, unreal.InterchangeGenericAssetsPipeline)  # chunk task options
    assert fake.tasks[-3].factory is None
    fake.calls.clear()
    fake.obj_routes_ok = {"legacy_flag"}
    _run(zi, zone, remeasure=True)
    relevant = [c for c in fake.calls if c[0] == "console" or (c[0] == "import" and c[1].endswith(".obj"))]
    assert relevant[:4] == [
        ("import", "_probe.obj", PROBE, "SM_probe", "fbx"),
        ("import", "_probe.obj", PROBE, "SM_probe", "interchange"),
        ("console", "Interchange.FeatureFlags.Import.OBJ 0"),
        ("import", "_probe.obj", PROBE, "SM_probe", "legacy_flag"),
    ]
    assert [c[4] for c in relevant[4:]] == ["legacy_flag", "legacy_flag"]
    assert "zone_import: obj importer route=legacy_flag (probe imported 1 static mesh)" in fake.logged("log")
    fake.obj_routes_ok = set()
    with pytest.raises(zi.ZoneImportError) as info:
        _run(zi, zone, remeasure=True)
    assert info.value.step == "probe"
    assert "OBJ import failed on routes fbx, interchange, legacy_flag" in str(info.value)
    assert "no asset imported from" in str(info.value) and str(info.value).startswith(
        "zone_import: ERROR probe:"
    )
    assert not [k for k in fake.registry if "_probe" in k] and fake.calls[-1] == ("delete_directory", PROBE)


def test_importer_cache_hit_and_remeasure(fake, unreal, zone, zi):
    cache = Path(fake.saved_dir) / "Golmok" / "zone_import" / "importer_mapping.json"
    _run(zi, zone)
    assert len(_imports(fake, "_probe.obj")) == 1 and len(_imports(fake, "_probe.glb")) == 1
    data = json.loads(cache.read_text("utf-8"))
    assert data == {
        "schema": 1,
        "engine": "5.8.3-fake",
        "obj": {"route": "fbx", "scale": 100.0, "m": [list(r) for r in M_OBJ], "err": 0.0},
        "glb": {"scale": 100.0, "m": [list(r) for r in IDENTITY], "err": 0.0},
    }
    fake.calls.clear()
    fake.logs.clear()
    _run(zi, zone)
    assert _imports(fake, "_probe.obj") == [] and _imports(fake, "_probe.glb") == []
    assert f"zone_import: importer mapping cache hit -> {cache}" in fake.logged("log")
    assert not [t for t in fake.logged("log") if t.startswith("zone_import: obj importer")]
    fake.calls.clear()
    _run(zi, zone, remeasure=True)
    assert len(_imports(fake, "_probe.obj")) == 1 and len(_imports(fake, "_probe.glb")) == 1
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(unreal.SystemLibrary, "get_engine_version", staticmethod(lambda: "5.9.0-fake"))
        fake.calls.clear()
        _run(zi, zone)
        assert len(_imports(fake, "_probe.obj")) == 1  # a different engine version misses the cache
        assert json.loads(cache.read_text("utf-8"))["engine"] == "5.9.0-fake"
    finally:
        monkeypatch.undo()


def test_plan_problem_aborts_before_any_editor_call(fake, zone_copy, zi):
    (zone_copy.version / "visual" / "c_e000_n000.obj").unlink()
    with pytest.raises(zi.ZoneImportError) as info:
        _run(zi, zone_copy)
    assert info.value.step == "plan" and "chunk c_e000_n000: file missing" in str(info.value)
    assert fake.calls == [] and fake.registry.keys() == {DEFAULT_LEVEL}
    with pytest.raises(zi.ZoneImportError) as info:
        zi.run(str(zone_copy.out))  # not a zone folder
    assert info.value.step == "plan" and "no v<n> folder with manifest.json" in str(info.value)
    assert fake.calls == []
    with pytest.raises(zi.ZoneImportError) as info:
        zi.run(str(zone_copy.dir), version=2)
    assert "version 2 requested" in str(info.value) and fake.calls == []


def test_bounds_mismatch_raises_and_places_no_zone(monkeypatch, tmp_path, zone):
    fake = fake_unreal.install(monkeypatch, tmp_path, bounds_offset={"SM_c_e000_n000.obj": (50.0, 0.0, 0.0)})
    zi = importlib.import_module("golmok.zone_import")
    with pytest.raises(zi.ZoneImportError) as info:
        _run(zi, zone)
    e = info.value
    assert e.step == "chunk c_e000_n000"
    assert (
        "imported bounds" in str(e)
        and "50.00 cm" in str(e)
        and "remeasure=True" in str(e)
        and "runbook #2" in str(e)
    )
    assert fake.calls_of("spawn") == [] and fake.calls_of("rebuild_in_editor") == []
    assert ("delete_directory", PROBE) in fake.calls and not [k for k in fake.registry if "_probe" in k]
    assert not (Path(fake.content_dir) / "Golmok").exists()  # files are copied only after the assets
    assert not (Path(fake.saved_dir) / "Golmok" / "zone_import" / ZONE / "v1" / "import_result.json").exists()


def test_probe_fit_failure_raises(monkeypatch, tmp_path, zone):
    fake_unreal.install(monkeypatch, tmp_path, bounds_offset={"_probe.obj": (50.0, 0.0, 0.0)})
    zi = importlib.import_module("golmok.zone_import")
    with pytest.raises(zi.ZoneImportError) as info:
        _run(zi, zone)
    assert info.value.step == "probe" and "obj importer mapping fit failed" in str(info.value)


# ---- textures ------------------------------------------------------------------------------------------


def test_texture_vt_enabled_after_import(monkeypatch, tmp_path, zone):
    fake = fake_unreal.install(monkeypatch, tmp_path, texture_vt_default=False)
    zi = importlib.import_module("golmok.zone_import")
    result = _run(zi, zone)
    for name in ("T_facade", "T_ground"):
        tex = fake.registry[f"{FOLDER}/Textures/{name}"]
        assert tex.get_editor_property("virtual_texture_streaming") is True
        assert tex.get_editor_property("srgb") is True
    logs = fake.logged("log")
    assert (
        f"zone_import: texture {FOLDER}/Textures/T_ground tiles=[] size=256x256 vt=on "
        "(single texture, vt enabled after import)"
    ) in logs
    assert (
        f"zone_import: texture {FOLDER}/Textures/T_facade tiles=[1001, 1002, 1011] size=512x512 vt=on "
        "(merged by importer, vt enabled after import)"
    ) in logs
    assert all(a["detail"]["vt"] is True for a in result["assets"] if a["kind"] == "texture")
    assert M_ZONE_SCAN in fake.registry and M_ZONE_SCAN_NOVT not in fake.registry


def test_udim_pack_fallback(monkeypatch, tmp_path, zone):
    fake = fake_unreal.install(monkeypatch, tmp_path, udim_merge=False)
    zi = importlib.import_module("golmok.zone_import")
    result = _run(zi, zone)
    tile_imports = [c for c in fake.calls_of("import") if c[2] == TILES]
    assert tile_imports == [
        ("import", f"facade.{t}.png", TILES, f"T_facade_{t}", None) for t in (1001, 1002, 1011)
    ]
    packed_at = fake.calls.index(("make_udim", f"{FOLDER}/Textures/T_facade", [(0, 0), (1, 0), (0, 1)]))
    assert fake.calls.index(tile_imports[-1]) < packed_at < fake.calls.index(("delete_directory", TILES))
    assert fake.calls.index(
        ("import", "facade.1001.png", f"{FOLDER}/Textures/_import", "T_facade", None)
    ) < fake.calls.index(tile_imports[0])
    assert [c for c in fake.calls_of("import") if c[1] == "ground.png"] == [
        ("import", "ground.png", f"{FOLDER}/Textures/_import", "T_ground", None)
    ]  # a single texture never takes the fallback
    # the anchor is packed over in place: no force delete of T_facade (runbook #10)
    assert ("delete_asset", f"{FOLDER}/Textures/T_facade") not in fake.calls
    tile_tasks = [t for t in fake.tasks if f"{TILES}" == t.destination_path]
    assert len(tile_tasks) == 3
    assert all(t.options.material_pipeline.texture_pipeline.import_udi_ms is False for t in tile_tasks)
    tex = fake.registry[f"{FOLDER}/Textures/T_facade"]
    assert tex.size == (512, 512) and tex.tiles == [1001, 1002, 1011]
    assert tex.get_editor_property("virtual_texture_streaming") is True
    assert not [k for k in fake.registry if k.startswith(TILES)]
    assert (
        f"zone_import: texture {FOLDER}/Textures/T_facade tiles=[1001, 1002, 1011] size=512x512 vt=on "
        "(packed from 3 tiles)"
    ) in fake.logged("log")
    facade = next(a for a in result["assets"] if a["asset"].endswith("T_facade"))
    assert facade["detail"] == {
        "tiles": [1001, 1002, 1011],
        "size": [512, 512],
        "vt": True,
        "how": "packed from 3 tiles",
    }
    assert fake.logged("warning") == []


def test_udim_fallback_without_library_warns(monkeypatch, tmp_path, zone):
    fake = fake_unreal.install(monkeypatch, tmp_path, udim_merge=False)
    monkeypatch.delattr(fake.module, "UDIMTextureFunctionLibrary")
    zi = importlib.import_module("golmok.zone_import")
    result = _run(zi, zone)  # no exception
    message = "texture T_facade: UDIM tiles not merged; using tile 1001 only (runbook #4)"
    assert fake.logged("warning") == [f"zone_import: WARNING {message}"]
    assert result["warnings"] == [message]
    tex = fake.registry[f"{FOLDER}/Textures/T_facade"]
    assert tex.size == (256, 256) and tex.source.endswith("facade.1001.png")
    assert not [c for c in fake.calls_of("import") if c[2] == TILES] and fake.calls_of("make_udim") == []
    assert (
        f"zone_import: texture {FOLDER}/Textures/T_facade tiles=[1001, 1002, 1011] size=256x256 vt=on "
        "(tile 1001 only (WARNING))"
    ) in fake.logged("log")
    assert f"zone_import: done {ZONE} v1: 8 assets, 1 warnings ->" in " ".join(fake.logged("log"))


def test_novt_master_when_vt_cannot_be_enabled(monkeypatch, tmp_path, zone):
    fake = fake_unreal.install(monkeypatch, tmp_path, texture_vt_default=False, vt_settable=False)
    zi = importlib.import_module("golmok.zone_import")
    result = _run(zi, zone)
    assert M_ZONE_SCAN_NOVT in fake.registry and M_ZONE_SCAN not in fake.registry  # no VT texture at all
    assert DEFAULT_TEX_NOVT in fake.registry and DEFAULT_TEX not in fake.registry
    novt = fake.registry[M_ZONE_SCAN_NOVT]
    sampler = novt.expressions[0]
    assert sampler.class_name == "MaterialExpressionTextureSampleParameter2D"
    assert sampler.props["sampler_type"] == fake.module.MaterialSamplerType.SAMPLERTYPE_COLOR
    assert sampler.props["texture"] is fake.registry[DEFAULT_TEX_NOVT]  # the master's own, VT off
    assert fake.registry[DEFAULT_TEX_NOVT].get_editor_property("virtual_texture_streaming") is False
    assert result["warnings"] == []
    for name in ("MI_facade", "MI_ground"):
        assert fake.registry[f"{FOLDER}/Materials/{name}"].parent is novt
    assert all(a["detail"]["vt"] is False for a in result["assets"] if a["kind"] == "texture")
    assert all(a["detail"]["parent"] == M_ZONE_SCAN_NOVT for a in result["assets"] if a["kind"] == "material")
    assert (
        f"zone_import: texture {FOLDER}/Textures/T_ground tiles=[] size=256x256 vt=off (single texture)"
        in fake.logged("log")
    )


def test_mixed_vt_textures_get_both_masters(monkeypatch, tmp_path, zone):
    # the packed UDIM texture is VT by construction, the single ground texture cannot be switched
    fake = fake_unreal.install(
        monkeypatch, tmp_path, udim_merge=False, texture_vt_default=False, vt_settable=False
    )
    zi = importlib.import_module("golmok.zone_import")
    result = _run(zi, zone)
    vt, novt = fake.registry[M_ZONE_SCAN], fake.registry[M_ZONE_SCAN_NOVT]
    assert (
        vt.expressions[0].props["sampler_type"] == fake.module.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR
    )
    # T_ZoneScanDefault cannot be made VT here (vt_settable=False): M_ZoneScan falls back to the zone's VT
    # texture with a warning; the NoVT master keeps its own default
    assert vt.expressions[0].props["texture"] is fake.registry[f"{FOLDER}/Textures/T_facade"]
    assert result["warnings"] == [
        f"T_ZoneScanDefault: virtual texture streaming could not be set to on; M_ZoneScan default is "
        f"{FOLDER}/Textures/T_facade (runbook #10)"
    ]
    assert novt.expressions[0].props["texture"] is fake.registry[DEFAULT_TEX_NOVT]
    assert fake.registry[f"{FOLDER}/Materials/MI_facade"].parent is vt
    assert fake.registry[f"{FOLDER}/Materials/MI_ground"].parent is novt
    assert vt.props["used_with_nanite"] is True and novt.props["used_with_nanite"] is True
    assert [c[0] for c in vt.connections] == ["MP_BASE_COLOR", "MP_ROUGHNESS"]
    assert vt.expressions[1].props["r"] == 0.8


def test_rerun_with_udim_pack_keeps_master_default(monkeypatch, tmp_path, zone):
    # delete_asset is a force delete (the fake nulls what pointed at the deleted object): a zone re-import
    # that replaces T_facade must not leave M_ZoneScan's VT sampler without a default texture (runbook #10)
    fake = fake_unreal.install(monkeypatch, tmp_path, udim_merge=False)
    zi = importlib.import_module("golmok.zone_import")
    _run(zi, zone)
    first = fake.calls.index(("make_udim", f"{FOLDER}/Textures/T_facade", [(0, 0), (1, 0), (0, 1)]))
    assert ("delete_asset", f"{FOLDER}/Textures/T_facade") not in fake.calls[:first]  # packed in place
    _run(zi, zone)  # default reimport_textures=True
    master = fake.registry[M_ZONE_SCAN]
    default = master.expressions[0].props["texture"]
    assert default is fake.registry[DEFAULT_TEX] and default.get_editor_property("virtual_texture_streaming")
    assert ("delete_asset", DEFAULT_TEX) not in fake.calls
    facade = fake.registry[f"{FOLDER}/Textures/T_facade"]
    assert fake.registry[f"{FOLDER}/Materials/MI_facade"].texture_params["BaseColor"] is facade
    assert fake.registry[f"{FOLDER}/Materials/MI_facade"].parent is master
    assert fake.logged("warning") == []


def test_existing_master_default_is_repaired(fake, unreal, zone, zi):
    # a master built before T_ZoneScanDefault existed (V-04) points at a zone texture: repaired in place
    _run(zi, zone)
    master = fake.registry[M_ZONE_SCAN]
    sampler = master.expressions[0]
    sampler.props["texture"] = fake.registry[f"{FOLDER}/Textures/T_facade"]
    fake.calls.clear()
    result = _run(zi, zone, reimport_textures=False)  # T_facade stays (a re-import would null the default)
    assert fake.registry[M_ZONE_SCAN] is master and (
        "create_asset",
        "M_ZoneScan",
        MATERIALS,
        "Material",
    ) not in (fake.calls)  # repaired, not recreated: other zones' MI_* keep their parent
    assert sampler.props["texture"] is fake.registry[DEFAULT_TEX]
    assert ("save", M_ZONE_SCAN) in fake.calls
    assert ("recompile_material", (master,)) in fake.mel_calls
    message = (
        f"M_ZoneScan BaseColor default was {FOLDER}/Textures/T_facade; set to {DEFAULT_TEX} (runbook #10)"
    )
    assert result["warnings"] == [message]
    fake.calls.clear()
    fake.logs.clear()
    result = _run(zi, zone)  # nothing left to repair
    assert result["warnings"] == [] and ("save", M_ZONE_SCAN) not in fake.calls


# ---- importer placement (V-03 pc-findings #1) ----------------------------------------------------------


def test_interchange_nested_placement_is_moved(monkeypatch, tmp_path, zone):
    fake = fake_unreal.install(monkeypatch, tmp_path, nested_glb=True)
    zi = importlib.import_module("golmok.zone_import")
    result = _run(zi, zone)
    for c in zone.expected["collision"]["chunks"].values():
        assert isinstance(fake.registry[c["asset"]], fake_unreal.FakeStaticMesh)
    for cid in CHUNKS:
        name = f"SM_{ZONE}_collision_{cid}"
        at = fake.calls.index(("import", f"{name}.glb", f"{FOLDER}/_import", name, None))
        assert fake.calls[at + 1 : at + 3] == [
            ("rename", f"{FOLDER}/_import/{name}/StaticMeshes/{name}", f"{FOLDER}/{name}"),
            ("delete_directory", f"{FOLDER}/_import"),
        ]
    assert set(fake.registry) == _expected_assets(zone.expected) | {DEFAULT_LEVEL, M_ZONE_SCAN, DEFAULT_TEX}
    assert not [k for k in fake.registry if "/_import/" in k or "/StaticMeshes/" in k]
    assert result["warnings"] == [] and fake.logged("warning") == []
    logs = fake.logged("log")
    assert f"zone_import: done {ZONE} v1: 8 assets, 0 warnings -> " in " ".join(logs)
    moved = [t for t in logs if t.startswith("zone_import: moved ") and "/StaticMeshes/" in t]
    names = [f"SM_{ZONE}_collision_{cid}" for cid in CHUNKS]
    assert moved == [
        f"zone_import: moved {FOLDER}/_import/{n}/StaticMeshes/{n} -> {FOLDER}/{n} "
        "(importer placement; runbook #37)"
        for n in names
    ]
    # the glTF material instances Interchange left beside the mesh go with the scratch folder (logged)
    for cid in CHUNKS:
        leftover = f"{FOLDER}/_import/SM_{ZONE}_collision_{cid}/Materials/collision_{cid}_mat"
        assert f"zone_import: deleted importer-created asset {leftover}" in logs


def test_ensure_path_reports_undeletable_target(fake, unreal, zone, zi, monkeypatch):
    _run(zi, zone)
    monkeypatch.setattr(unreal.EditorAssetLibrary, "delete_asset", staticmethod(lambda path: False))
    with pytest.raises(zi.ZoneImportError) as info:
        _run(zi, zone)
    target = f"{FOLDER}/Textures/T_facade"
    assert info.value.step == "texture T_facade"
    assert f"{target} exists and could not be deleted (referenced?)" in info.value.message
    assert not [k for k in fake.registry if "/_import/" in k]  # the scratch folder is dropped even then


# ---- materials and slots -------------------------------------------------------------------------------


def test_importer_materials_deleted_and_slots_assigned(fake, unreal, zone, zi):
    _run(zi, zone)
    deletes = fake.calls_of("delete_asset")
    by_products = [("delete_asset", f"{FOLDER}/_import/{m}") for m in ("facade", "ground")] * 2
    assert sorted(deletes) == sorted(by_products)
    assert not [k for k in fake.registry if k.endswith(("/facade", "/ground"))]
    assert (
        fake.logged("log").count(f"zone_import: deleted importer-created asset {FOLDER}/_import/facade") == 2
    )
    for cid in CHUNKS:
        mesh = fake.registry[f"{FOLDER}/SM_{cid}"]
        assert mesh.nanite.enabled is True
        for i, slot in enumerate(mesh.slots):
            assert mesh.get_material(i) is fake.registry[f"{FOLDER}/Materials/MI_{slot}"]
    assert fake.logged("warning") == []
    materials = importlib.import_module("golmok.materials")
    mi = fake.registry[f"{FOLDER}/Materials/MI_facade"]
    assert mi.texture_params["BaseColor"] is fake.registry[f"{FOLDER}/Textures/T_facade"]
    assert materials.ZONE_SCAN_NAME == "M_ZoneScan" and materials.ZONE_SCAN_NOVT_NAME == "M_ZoneScan_NoVT"
    assert pure.MASTER_MATERIAL == f"{materials.MATERIAL_DIR}/{materials.ZONE_SCAN_NAME}"


def test_slot_fallback_usemtl_order(monkeypatch, tmp_path, zone):
    fake = fake_unreal.install(monkeypatch, tmp_path, slot_names_from_usemtl=False)
    zi = importlib.import_module("golmok.zone_import")
    result = _run(zi, zone)
    for cid in CHUNKS:
        mesh, usemtl = f"{FOLDER}/SM_{cid}", _usemtl(zone, cid)
        assert fake.registry[mesh].slots == ["Material_0", "Material_1"]
        assert [c for c in fake.calls_of("set_material") if c[1] == mesh] == [
            ("set_material", mesh, i, f"{FOLDER}/Materials/MI_{m}") for i, m in enumerate(usemtl)
        ]
    assert fake.logged("warning") == [] and result["warnings"] == []
    usemtl = _usemtl(zone, "c_e000_n000")
    slots = ",".join(f"Material_{i}=MI_{m}" for i, m in enumerate(usemtl))
    assert (
        f"zone_import: chunk {FOLDER}/SM_c_e000_n000 tris=66 bounds ok (error 0.00 cm) slots={slots}"
        in fake.logged("log")
    )
    # a slot the OBJ does not explain stays with the importer default (one warning)
    original = fake_unreal.FakeStaticMesh.__init__

    def with_stray(
        self, fake_, path, bounds=((0.0,) * 3, (0.0,) * 3), slots=("Material_0",), materials=(), source=""
    ):
        stray = ["stray"] if path.endswith("SM_c_e000_n000") else []
        original(self, fake_, path, bounds, list(slots) + stray, materials, source)

    monkeypatch.setattr(fake_unreal.FakeStaticMesh, "__init__", with_stray)
    fake.logs.clear()
    result = _run(zi, zone)
    message = "chunk c_e000_n000: slot 'stray' left with the importer default (runbook #7)"
    assert fake.logged("warning") == [f"zone_import: WARNING {message}"] and result["warnings"] == [message]
    chunk = next(a for a in result["assets"] if a["asset"].endswith("SM_c_e000_n000"))
    assert chunk["detail"]["unmatched"] == ["stray"] and len(chunk["detail"]["slots"]) == 2


def test_engine_udim_name_single_texture(monkeypatch, tmp_path, zone_copy):
    # UTextureFactory's UDIM rule is [._]#### (>= 1001), wider than the plan's BaseName.1001..1999.ext:
    # a single 'ground_1002.png' is imported with UDIM detection off (runbook #38)
    tex = zone_copy.tex / "ground.png"
    tex.rename(tex.with_name("ground_1002.png"))
    mtl = zone_copy.version / "visual" / "scan.mtl"
    mtl.write_text(mtl.read_text("utf-8").replace("tex/ground.png", "tex/ground_1002.png"), encoding="utf-8")
    fake = fake_unreal.install(monkeypatch, tmp_path, engine_udim_regex=True)
    zi = importlib.import_module("golmok.zone_import")
    result = _run(zi, zone_copy)
    task = next(t for t in fake.tasks if t.filename.endswith("ground_1002.png"))
    assert task.options.material_pipeline.texture_pipeline.import_udi_ms is False
    facade = next(t for t in fake.tasks if t.filename.endswith("facade.1001.png"))
    assert facade.options.material_pipeline.texture_pipeline.import_udi_ms is True
    assert fake.registry[f"{FOLDER}/Textures/T_ground_1002"].size == (256, 256)
    plan_warning = next(w for w in result["warnings"] if "ground_1002.png" in w)
    assert (
        "[._]####" in plan_warning and "UDIM detection off" in plan_warning and "runbook #38" in plan_warning
    )
    assert (
        f"zone_import: texture {FOLDER}/Textures/T_ground_1002 tiles=[] size=256x256 vt=on (single texture)"
        in fake.logged("log")
    )
    # an importer that ignores the option places the tile as UDIM block (1, 0): the size check warns
    monkeypatch.setattr(zi, "_texture_options", lambda udim=True: None)
    fake.logs.clear()
    result = _run(zi, zone_copy)
    assert fake.registry[f"{FOLDER}/Textures/T_ground_1002"].size == (512, 256)
    message = (
        "texture T_ground_1002: engine imported ground_1002.png as a UDIM (512x256 != file 256x256; "
        "name matches [._]####); rename the file (runbook #38)"
    )
    assert message in result["warnings"]
    assert (
        f"zone_import: texture {FOLDER}/Textures/T_ground_1002 tiles=[] size=512x256 vt=on "
        "(imported as UDIM by the engine (WARNING))"
    ) in fake.logged("log")


def test_texture_options_hops(fake, unreal, zi, monkeypatch):
    options = zi._texture_options()
    assert isinstance(options, unreal.InterchangeGenericAssetsPipeline)
    assert options.material_pipeline.texture_pipeline.import_udi_ms is True
    single = zi._texture_options(udim=False)
    assert single.material_pipeline.texture_pipeline.import_udi_ms is False
    assert single.material_pipeline.get_editor_property("import_materials") is False
    assert options.material_pipeline.get_editor_property("import_materials") is False
    ui = zi._obj_options("fbx")
    assert isinstance(ui, unreal.FbxImportUI)
    for prop, value in (
        ("is_obj_import", True),
        ("import_mesh", True),
        ("import_materials", False),
        ("import_textures", False),
        ("import_as_skeletal", False),
        ("automated_import_should_detect_type", False),
        ("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH),
    ):
        assert ui.get_editor_property(prop) == value, prop
    data = ui.get_editor_property("static_mesh_import_data")
    assert (
        data.build_nanite,
        data.combine_meshes,
        data.auto_generate_collision,
        data.generate_lightmap_u_vs,
    ) == (
        True,
        True,
        False,
        False,
    )
    assert isinstance(zi._obj_options("legacy_flag"), unreal.FbxImportUI)
    pipeline = zi._obj_options("interchange")
    assert (
        pipeline.common_meshes_properties.force_all_mesh_as_type
        == unreal.InterchangeForceMeshType.IFMT_STATIC_MESH
    )
    assert pipeline.mesh_pipeline.import_static_meshes is True and pipeline.mesh_pipeline.build_nanite is True
    assert pipeline.material_pipeline.import_materials is False
    assert pipeline.material_pipeline.texture_pipeline.import_textures is False
    assert isinstance(zi._obj_factory("fbx"), unreal.FbxFactory)
    assert zi._obj_factory("interchange") is None and zi._obj_factory("legacy_flag") is None
    assert fake.logged("warning") == []
    monkeypatch.delattr(unreal, "InterchangeGenericAssetsPipeline")
    assert zi._texture_options() is None
    assert zi._obj_options("interchange") is None
    assert fake.logged("warning")[-1].endswith("OBJ imported with default options (runbook #3)")
    with pytest.raises(ValueError):
        zi._obj_options("nope")


# ---- geo origin, files, re-runs ------------------------------------------------------------------------


def test_geo_origin_rules(fake, unreal, zone, zi, tmp_path):
    zi.run(str(zone.dir), level=DEFAULT_LEVEL)  # None, no actor -> spawned at the zone origin
    geo = _geo_actors(fake, unreal)
    assert len(geo) == 1

    def values():
        return tuple(geo[0].get_editor_property(p) for p in ("latitude", "longitude", "height_ellipsoidal"))

    assert values() == (37.562, 126.925, 50.0)
    assert (
        "zone_import: geo origin lat=37.562000 lon=126.925000 h=50.000 "
        "(spawned from zone origin (zone at level origin))"
    ) in fake.logged("log")
    geo[0].set_editor_property("latitude", 1.0)
    geo[0].set_editor_property("longitude", 2.0)
    geo[0].set_editor_property("height_ellipsoidal", 3.0)
    zi.run(str(zone.dir))  # None, actor present -> kept
    assert values() == (
        1.0,
        2.0,
        3.0,
    ) and "zone_import: geo origin lat=1.000000 lon=2.000000 h=3.000 (kept)" in fake.logged("log")
    zi.run(str(zone.dir), geo_origin="area")
    assert values() == (37.56, 126.923, 40.0)
    zi.run(str(zone.dir), geo_origin="zone")
    assert values() == (37.562, 126.925, 50.0) and fake.logged("log")[-1].startswith("  - ")
    zi.run(str(zone.dir), geo_origin=(1.5, 2.5, 3.5))
    assert values() == (1.5, 2.5, 3.5)
    assert "zone_import: geo origin lat=1.500000 lon=2.500000 h=3.500 (given)" in fake.logged("log")
    basemap = tmp_path / "basemap"
    basemap.mkdir()
    (basemap / "manifest.json").write_text(
        json.dumps({"origin": {"lat": 37.55, "lon": 126.92, "height_ellipsoidal": 33.0}}), encoding="utf-8"
    )
    zi.run(str(zone.dir), geo_origin=str(basemap))
    assert values() == (37.55, 126.92, 33.0)
    assert (
        f"zone_import: geo origin lat=37.550000 lon=126.920000 h=33.000 (basemap {basemap})"
        in fake.logged("log")
    )
    assert (
        len(_geo_actors(fake, unreal)) == 1
        and fake.calls_of("spawn").count(("spawn", "GolmokGeoOrigin", "GeoOrigin")) == 1
    )
    with pytest.raises(zi.ZoneImportError) as info:
        zi.run(str(zone.dir), geo_origin="nope")
    assert info.value.step == "geo"


def test_content_copy_exact_two_files(fake, zone, zi):
    result = _run(zi, zone)
    dest = Path(fake.content_dir) / "Golmok" / "Zones" / ZONE / "v1"
    assert sorted(p.name for p in dest.iterdir()) == ["blockers.json", "manifest.json"]
    for name in ("blockers.json", "manifest.json"):
        assert (dest / name).read_bytes() == (zone.version / name).read_bytes()
    # rglob order is filesystem order (differs between runners): sort both sides
    zones_root = Path(fake.content_dir) / "Golmok" / "Zones"
    assert sorted(p for p in zones_root.rglob("*") if p.is_file()) == sorted(dest.iterdir())
    files = [a for a in result["assets"] if a["kind"] == "file"]
    assert [a["asset"] for a in files] == [
        f"Golmok/Zones/{ZONE}/v1/blockers.json",
        f"Golmok/Zones/{ZONE}/v1/manifest.json",
    ]
    assert files[1]["detail"] == {"bytes": (zone.version / "manifest.json").stat().st_size}
    copied = _logs(fake, "zone_import: copied")
    assert copied == [f"zone_import: copied blockers.json, manifest.json -> {dest}"]
    # the copy happens after every asset import (design D8)
    log = fake.logged("log")
    assert log.index(copied[0]) > max(i for i, t in enumerate(log) if t.startswith("zone_import: collision "))


def test_rerun_replaces_not_duplicates(fake, zone, zi):
    _run(zi, zone)
    count = len(fake.registry)
    _run(zi, zone)
    assert len(fake.registry) == count and not [k for k in fake.registry if k.endswith("_2")]
    assert all(t.replace_existing and t.automated and not t.save and not t.async_ for t in fake.tasks)
    assert fake.calls_of("create_asset") == [
        ("create_asset", "M_ZoneScan", MATERIALS, "Material"),
        ("create_asset", "MI_facade", f"{FOLDER}/Materials", "MaterialInstanceConstant"),
        ("create_asset", "MI_ground", f"{FOLDER}/Materials", "MaterialInstanceConstant"),
    ]  # the second run updates the existing master and instances
    assert fake.calls_of("spawn") == [
        ("spawn", "GolmokGeoOrigin", "GeoOrigin"),
        ("spawn", "GolmokZone", f"Zone_{ZONE}"),
    ]
    fake.calls.clear()
    fake.logs.clear()
    result = _run(zi, zone, reimport_textures=False)
    assert _imports(fake, ".png") == []
    assert _logs(fake, "zone_import: texture ") == [
        f"zone_import: texture {FOLDER}/Textures/T_facade tiles=[1001, 1002, 1011] size=512x512 vt=on "
        "(skipped: exists)",
        f"zone_import: texture {FOLDER}/Textures/T_ground tiles=[] size=256x256 vt=on (skipped: exists)",
    ]
    assert [a["detail"]["how"] for a in result["assets"] if a["kind"] == "texture"] == ["skipped: exists"] * 2
    assert (
        len(_imports(fake, ".obj")) == 2 and len(_imports(fake, ".glb")) == 2
    )  # meshes are always re-imported


def test_hasattr_branches(fake, unreal, zone, zi, monkeypatch):
    with monkeypatch.context() as m:
        m.delattr(unreal, "FbxImportUI")
        assert zi._obj_options("fbx") is None
        assert fake.logged("warning") == [
            "zone_import: WARNING FbxImportUI unavailable: OBJ imported with default options (runbook #1)"
        ]
        result = _run(zi, zone)  # the factory alone still routes the OBJ (fake: fbx)
        assert [c[4] for c in _imports(fake, ".obj")] == ["fbx"] * 3
        assert all(t.options is None for t in fake.tasks if t.filename.endswith(".obj"))
        assert result["warnings"] and all("FbxImportUI unavailable" in w for w in result["warnings"])
    fake.calls.clear()
    with monkeypatch.context() as m:
        m.delattr(unreal.StaticMeshEditorSubsystem, "set_nanite_settings")
        _run(zi, zone)
        assert [c for c in fake.calls_of("set_nanite") if c[2]] == [
            ("set_nanite", f"{FOLDER}/SM_{cid}", True) for cid in CHUNKS
        ]
        assert fake.registry[f"{FOLDER}/SM_{ZONE}_collision_c_e000_n000"].nanite.enabled is False
    fake.calls.clear()
    fake.logs.clear()
    with monkeypatch.context() as m:
        m.delattr(unreal.SystemLibrary, "get_engine_version")
        _run(zi, zone)
        _run(zi, zone)
        assert len(_imports(fake, "_probe.obj")) == 2  # no engine version: the cache never hits
        assert len(_logs(fake, "zone_import: importer mapping cache miss")) == 2
        assert not _logs(fake, "zone_import: importer mapping cache hit")
        assert any(
            "get_engine_version unavailable" in w and "runbook #26" in w for w in fake.logged("warning")
        )


def test_result_json_written(fake, zone, zi):
    result = _run(zi, zone)
    path = Path(fake.saved_dir) / "Golmok" / "zone_import" / ZONE / "v1" / "import_result.json"
    data = json.loads(path.read_text("utf-8"))
    assert data == result
    assert list(data) == [
        "schema", "zone_id", "version", "asset_folder", "route", "obj_mapping", "glb_mapping", "assets",
        "warnings", "interior",
    ]  # fmt: skip
    assert (data["schema"], data["zone_id"], data["version"], data["asset_folder"]) == (1, ZONE, 1, FOLDER)
    assert data["route"] == "fbx" and data["interior"] is None and data["warnings"] == []
    assert data["obj_mapping"] == {"scale": 100.0, "m": [list(r) for r in M_OBJ], "err": 0.0}
    assert data["glb_mapping"] == {"scale": 100.0, "m": [list(r) for r in IDENTITY], "err": 0.0}
    kinds = [a["kind"] for a in data["assets"]]
    assert kinds == ["texture"] * 2 + ["material"] * 2 + ["chunk"] * 2 + ["collision"] * 2 + ["file"] * 2
    assert all(a["ok"] for a in data["assets"])
    by_asset = {a["asset"]: a["detail"] for a in data["assets"]}
    assert by_asset[f"{FOLDER}/Textures/T_facade"] == {
        "tiles": [1001, 1002, 1011], "size": [512, 512], "vt": True, "how": "merged by importer",
    }  # fmt: skip
    assert by_asset[f"{FOLDER}/Materials/MI_ground"] == {"parent": M_ZONE_SCAN, "texture": "T_ground"}
    assert by_asset[f"{FOLDER}/SM_c_w001_n000"] == {
        "tris": 66,
        "bounds_error_cm": 0.0,
        "slots": {"facade": "MI_facade", "ground": "MI_ground"},
        "unmatched": [],
    }
    assert by_asset[f"{FOLDER}/SM_{ZONE}_collision_c_e000_n000"] == {"bounds_error_cm": 0.0}
    assert set(by_asset) == _expected_assets(zone.expected) | {
        f"Golmok/Zones/{ZONE}/v1/blockers.json",
        f"Golmok/Zones/{ZONE}/v1/manifest.json",
    }
    assert "\n" in path.read_text("utf-8") and "합성" not in path.read_text("utf-8")  # indented, no zone path


def test_import_failure_message_names_file(monkeypatch, tmp_path, zone):
    fake_unreal.install(monkeypatch, tmp_path, fail_import={"SM_c_w001_n000.obj"})
    zi = importlib.import_module("golmok.zone_import")
    with pytest.raises(zi.ZoneImportError) as info:
        _run(zi, zone)
    e = info.value
    assert e.step == "chunk c_w001_n000" and "no asset imported from" in e.message
    assert (
        e.message.endswith("SM_c_w001_n000.obj")
        and str(e) == f"zone_import: ERROR chunk c_w001_n000: {e.message}"
    )
    assert isinstance(e, RuntimeError)


def test_single_collision_mode(fake, zone_copy, zi):
    manifest_path = zone_copy.version / "manifest.json"
    manifest = json.loads(manifest_path.read_text("utf-8"))
    manifest["layers"]["collision"].pop("chunks")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    result = _run(zi, zone_copy)
    assert (
        f"zone_import: plan {ZONE} v1: chunks=2 collision=1 (single) textures=2 materials=2 blockers=1"
        in fake.logged("log")
    )
    assert [c[1] for c in _imports(fake, ".glb")] == ["_probe.glb", f"SM_{ZONE}_collision.glb"]
    mesh = fake.registry[f"{FOLDER}/SM_{ZONE}_collision"]
    assert not [k for k in fake.registry if "_collision_c_" in k]
    assert [*mesh.bounds[0], *mesh.bounds[1]] == pytest.approx(
        [-1500.0, -1500.0, -30.0, 1500.0, 0.0, 600.0], abs=0.01
    )
    assert mesh.body_setup.collision_trace_flag == fake.module.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
    assert mesh.nanite.enabled is False
    assert [a["asset"] for a in result["assets"] if a["kind"] == "collision"] == [
        f"{FOLDER}/SM_{ZONE}_collision"
    ]
    assert (
        f"zone_import: collision {FOLDER}/SM_{ZONE}_collision bounds ok (error 0.00 cm) "
        "complex-as-simple nanite=off"
    ) in fake.logged("log")


def test_interior_zone_imports_like_exterior(fake, zone, zi):
    result = zi.run(str(zone.room), level=DEFAULT_LEVEL, geo_origin="area")
    logs = fake.logged("log")
    assert (
        f"zone_import: plan {ROOM} v1: chunks=1 collision=1 (chunks) textures=1 materials=1 blockers=0"
        in logs
    )
    assert (
        f"zone_import: texture {ROOM_FOLDER}/Textures/T_room tiles=[1001] size=256x256 vt=on (single texture)"
        in logs
    )
    assert (
        f"zone_import: chunk {ROOM_FOLDER}/SM_c_e000_n000 tris=60 bounds ok (error 0.00 cm) "
        "slots=room=MI_room"
    ) in logs
    assert (
        f"zone_import: copied manifest.json -> {Path(fake.content_dir) / 'Golmok' / 'Zones' / ROOM / 'v1'}"
        in logs
    )
    assert sorted(p.name for p in (Path(fake.content_dir) / "Golmok" / "Zones" / ROOM / "v1").iterdir()) == [
        "manifest.json"
    ]
    interior = json.loads((zone.room / "v1" / "expected.json").read_text("utf-8"))
    mesh = fake.registry[f"{ROOM_FOLDER}/SM_c_e000_n000"]
    assert [*mesh.bounds[0], *mesh.bounds[1]] == pytest.approx(
        [
            *interior["chunks"]["c_e000_n000"]["ue_bounds_cm"][0],
            *interior["chunks"]["c_e000_n000"]["ue_bounds_cm"][1],
        ],
        abs=0.01,
    )
    assert set(fake.registry) == {
        DEFAULT_LEVEL,
        M_ZONE_SCAN,
        DEFAULT_TEX,
        f"{ROOM_FOLDER}/SM_c_e000_n000",
        f"{ROOM_FOLDER}/SM_{ROOM}_collision_c_e000_n000",
        f"{ROOM_FOLDER}/Textures/T_room",
        f"{ROOM_FOLDER}/Materials/MI_room",
    }
    assert [a["kind"] for a in result["assets"]] == ["texture", "material", "chunk", "collision", "file"]
    assert fake.calls_of("spawn") == [
        ("spawn", "GolmokGeoOrigin", "GeoOrigin"),
        ("spawn", "GolmokZone", f"Zone_{ROOM}"),
    ]


def test_import_assets_alone_touches_no_level(fake, zone, zi):
    plan, manifest = zi.make_plan(str(zone.dir))
    assert manifest["zone_id"] == ZONE and plan["problems"] == [] and plan["warnings"] == []
    work = zi.work_dir(plan)
    assert Path(work) == Path(fake.saved_dir) / "Golmok" / "zone_import" / ZONE / "v1"
    assert (Path(work) / "visual").is_dir() and (Path(work) / "collision").is_dir()
    mappings, assets, warnings, route = zi.import_assets(plan, work)
    assert route == "fbx" and warnings == [] and len(assets) == 10
    assert mappings["obj"][0] == 100.0 and mappings["obj"][1] == M_OBJ and mappings["glb"][1] == IDENTITY
    kinds = {c[0] for c in fake.calls}
    assert not kinds & {"spawn", "load_level", "new_level", "save_current_level", "rebuild_in_editor"}
    assert set(fake.registry) == _expected_assets(zone.expected) | {DEFAULT_LEVEL, M_ZONE_SCAN, DEFAULT_TEX}
    result = pure.result_json(plan, mappings, assets, warnings, route)
    path = zi.write_result(work, result)
    assert json.loads(Path(path).read_text("utf-8")) == result
    assert zi.run(str(zone.version)) and zi.run(str(zone.version / "manifest.json"), version=1)


def test_basemap_import_sets_geo_origin(fake, unreal):
    bm = importlib.import_module("golmok.basemap_import")
    bm._set_geo_origin({"lat": 37.5, "lon": 127.0, "height_ellipsoidal": 45.0})
    geo = _geo_actors(fake, unreal)
    assert len(geo) == 1 and geo[0].get_actor_label() == "GeoOrigin"

    def values():
        return tuple(geo[0].get_editor_property(p) for p in ("latitude", "longitude", "height_ellipsoidal"))

    assert values() == (37.5, 127.0, 45.0)
    assert fake.logs[-1] == (
        "log",
        "basemap_import: GeoOrigin lat=37.500000 lon=127.000000 h=45.000 "
        "(basemap origin; ellipsoidal = DEM orthometric + --geoid-offset)",
    )
    bm._set_geo_origin({"lat": 1.0, "lon": 2.0, "height_ellipsoidal": 3.0})
    assert values() == (1.0, 2.0, 3.0) and len(_geo_actors(fake, unreal)) == 1
    assert fake.calls_of("spawn") == [("spawn", "GolmokGeoOrigin", "GeoOrigin")]
    # run() calls it right after the Cesium georeference
    src = (GOLMOK_DIR / "basemap_import.py").read_text("utf-8")
    assert re.search(
        r'_set_georeference\(manifest\["origin"\]\)\n\s+_set_geo_origin\(manifest\["origin"\]\)', src
    )
    assert "--exclude" in src.split('"""', 2)[1]  # documented in the module docstring


def test_legacy_flag_rearmed_on_cache_hit(fake, unreal, zone, zi):
    """Review A2: the OBJ CVar is per editor session, so a cache hit on route legacy_flag must re-send it."""
    fake.obj_routes_ok = {"legacy_flag"}
    _run(zi, zone)
    assert [c[4] for c in _imports(fake, ".obj")][-2:] == ["legacy_flag", "legacy_flag"]
    fake.legacy_flag = False  # a new editor session: CVar back to its default, mapping cache still valid
    fake.calls.clear()
    fake.logs.clear()
    _run(zi, zone)
    assert _imports(fake, "_probe.obj") == []  # cache hit: no probe
    assert ("console", "Interchange.FeatureFlags.Import.OBJ 0") in fake.calls
    assert [c[4] for c in _imports(fake, ".obj")] == ["legacy_flag", "legacy_flag"]
