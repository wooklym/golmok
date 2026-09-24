"""golmok-zone end to end in a temp folder: init -> validate -> index build -> exclude (WP-02 완료 기준)."""

import json
import subprocess
import sys

from zone_util import FIXTURE_ZONES, rect_footprint

from golmok_tools.zone import manifest as zm
from golmok_tools.zone import schema
from golmok_tools.zone.cli import main


def write_fp(path, **kw):
    fp = rect_footprint(37.5620, 126.9250, 40, 20, **kw)
    path.write_text(json.dumps({"type": "Feature", "properties": {}, "geometry": fp}), encoding="utf-8")
    return path


def test_init_validate_index_exclude_chain(tmp_path, capsys):
    zones, fp = tmp_path / "zones", write_fp(tmp_path / "fp.geojson")
    vdir = zones / "z_yeonnam_alley_001" / "v1"
    rc = main(
        [
            "init", "--id", "z_yeonnam_alley_001", "--kind", "exterior",
            "--origin", "37.5620,126.9250,50", "--footprint", str(fp), "--yaw", "12.5",
            "--capture", "alley01", "--out", str(vdir),
        ]
    )  # fmt: skip
    assert rc == 0
    manifest = vdir / "manifest.json"
    d = zm.load(manifest)
    assert d["zone_id"] == "z_yeonnam_alley_001" and d["version"] == 1
    assert d["sources"] == [{"capture_id": "alley01"}]
    assert schema.validate(d) == []

    assert main(["validate", str(manifest)]) == 0
    assert main(["validate", "--strict", str(manifest)]) == 1  # empty chunks warning

    rc = main(
        [
            "init", "--id", "z_yeonnam_alley_001_cafe", "--kind", "interior",
            "--parent", "z_yeonnam_alley_001",
            "--origin", "37.5620,126.9250,50", "--footprint", str(fp),
            "--out", str(zones / "z_yeonnam_alley_001_cafe" / "v1"),
        ]
    )  # fmt: skip
    assert rc == 0

    out = tmp_path / "index"
    assert main(["index", "build", "--zones-root", str(zones), "--out", str(out), "--strict"]) == 0
    idx = json.loads((out / "zones.json").read_text(encoding="utf-8"))
    assert [z["id"] for z in idx["zones"]] == ["z_yeonnam_alley_001", "z_yeonnam_alley_001_cafe"]
    cells = sorted((out / "cells").glob("16_*.json"))
    assert cells
    for c in cells:
        assert schema.validate_index(json.loads(c.read_text(encoding="utf-8"))) == []

    ex = tmp_path / "exclude.geojson"
    assert main(["exclude", "--zones-root", str(zones), "--out", str(ex), "--buffer-m", "0.75"]) == 0
    fc = json.loads(ex.read_text(encoding="utf-8"))
    assert [f["properties"]["zone_ids"] for f in fc["features"]] == [["z_yeonnam_alley_001"]]

    capsys.readouterr()
    assert (
        main(["transform", str(manifest), "--enu", "10,0,0", "--area-origin", "37.56,126.923,40", "--json"])
        == 0
    )
    rep = json.loads(capsys.readouterr().out)
    assert rep["ue_zone_local_cm"] == [1000.0, 0.0, 0.0]
    assert len(rep["ue_actor_matrix"]) == 4

    assert main(["bump", str(manifest)]) == 0
    v2 = zones / "z_yeonnam_alley_001" / "v2" / "manifest.json"
    assert zm.load(v2)["version"] == 2
    assert zm.load(manifest)["version"] == 1  # v1 untouched
    assert main(["validate", str(v2)]) == 0
    assert main(["index", "build", "--zones-root", str(zones), "--out", str(out)]) == 0
    idx = json.loads((out / "zones.json").read_text(encoding="utf-8"))
    assert idx["zones"][0]["version"] == 2


def test_init_refuses_bad_input(tmp_path):
    fp = write_fp(tmp_path / "fp.geojson")
    out = tmp_path / "zones" / "z_a_001" / "v1"
    base = ["init", "--kind", "exterior", "--origin", "37.5620,126.9250,50", "--footprint", str(fp)]
    assert main([*base, "--id", "Bad-Id", "--out", str(out)]) == 2
    assert main([*base, "--id", "z_a_001", "--out", str(tmp_path / "zones" / "z_a_001" / "v3")]) == 2
    assert main([*base, "--id", "z_a_001", "--out", str(out)]) == 0
    assert main([*base, "--id", "z_a_001", "--out", str(out)]) == 2  # exists
    assert main([*base, "--id", "z_a_001", "--out", str(out), "--force"]) == 0
    interior = ["init", "--kind", "interior", "--origin", "37.5620,126.9250", "--footprint", str(fp)]
    assert main([*interior, "--id", "z_a_001_in", "--out", str(tmp_path / "in")]) == 2  # no --parent
    far = write_fp(tmp_path / "far.geojson", dx=500)
    assert main([*base[:-1], str(far), "--id", "z_b_001", "--out", str(tmp_path / "b" / "v1")]) == 1


def test_validate_fixture_and_check_files(capsys):
    fixture = FIXTURE_ZONES / "z_synthetic_001" / "v1" / "manifest.json"
    assert main(["validate", str(fixture)]) == 0
    assert main(["validate", "--check-files", str(fixture)]) == 1  # GLBs are not in the repo
    assert "파일 없음: collision.glb" in capsys.readouterr().out


def test_bump_refuses_to_overwrite(tmp_path):
    fp = write_fp(tmp_path / "fp.geojson")
    vdir = tmp_path / "zones" / "z_a_001" / "v1"
    base = ["init", "--kind", "exterior", "--origin", "37.5620,126.9250,50", "--footprint", str(fp)]
    assert main([*base, "--id", "z_a_001", "--out", str(vdir)]) == 0
    assert main(["bump", str(vdir / "manifest.json")]) == 0
    # bumping v1 again makes v3 (newest + 1), never touches v2
    assert main(["bump", str(vdir / "manifest.json")]) == 0
    assert (vdir.parent / "v3" / "manifest.json").is_file()
    loose = zm.save(zm.load(vdir / "manifest.json"), tmp_path / "loose" / "manifest.json")
    assert main(["bump", str(loose)]) == 2


def test_console_script_entry_point(tmp_path):
    r = subprocess.run(
        [sys.executable, "-m", "golmok_tools.zone.cli", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0 and "init" in r.stdout and "exclude" in r.stdout
