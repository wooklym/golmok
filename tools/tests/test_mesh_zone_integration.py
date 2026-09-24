"""WP-03 완료 기준: 합성 메시 → chunk → collision → blockers → manifest → validate --check-files."""

import json

import pytest

pytest.importorskip("trimesh")
pytest.importorskip("fast_simplification")

from mesh_util import write_synthetic_obj  # noqa: E402
from zone_util import make_zone  # noqa: E402

from golmok_tools.mesh.cli import main as mesh_main  # noqa: E402
from golmok_tools.zone import manifest as zm  # noqa: E402
from golmok_tools.zone.cli import main as zone_main  # noqa: E402


def test_mesh_pipeline_produces_a_valid_zone(tmp_path):
    src = write_synthetic_obj(tmp_path / "recon")
    manifest, _ = make_zone(tmp_path / "zones", "z_synth_alley_001", size=(70, 30))
    vdir = manifest.parent

    assert (
        mesh_main(
            ["chunk", str(src), "--size", "15", "--out", str(vdir / "visual"), "--manifest", str(manifest)]
        )
        == 0
    )
    assert (
        mesh_main(
            [
                "collision",
                str(src),
                "--out",
                str(vdir / "collision.glb"),
                "--target-tris",
                "800",
                "--per-chunk",
                str(vdir / "visual"),
                "--manifest",
                str(manifest),
            ]
        )  # fmt: skip
        == 0
    )
    blockers = vdir / "blockers.json"
    assert (
        mesh_main(
            [
                "blockers",
                "add",
                str(blockers),
                "--center",
                "5,5,1.5",
                "--normal",
                "0,-1,0",
                "--size",
                "3,2.4",
                "--kind",
                "glass",
            ]
        )
        == 0
    )
    assert mesh_main(["blockers", "build", str(blockers), "--manifest", str(manifest)]) == 0

    d = zm.load(manifest)
    chunks = d["layers"]["visual"]["chunks"]
    assert d["layers"]["visual"]["format"] == "nanite_mesh"
    assert len(chunks) >= 8 and all(
        c["uri"].startswith("visual/c_") and c["uri"].endswith(".obj") for c in chunks
    )
    assert d["layers"]["collision"]["uri"] == "collision.glb"
    assert {c["id"] for c in d["layers"]["collision"]["chunks"]} <= {c["id"] for c in chunks}
    assert d["layers"]["blockers"] == {"uri": "blockers.json"}

    rep = zm.check(d, manifest, check_files=True)
    assert rep.errors == [], rep.errors
    assert zone_main(["validate", "--check-files", str(manifest)]) == 0

    cm = json.loads((vdir / "visual" / "chunk_manifest.json").read_text(encoding="utf-8"))
    assert sum(c["tris"] for c in cm["chunks"]) == sum(c["tris"] for c in chunks)


def test_chunk_outside_zone_folder_is_refused(tmp_path):
    src = write_synthetic_obj(tmp_path / "recon")
    manifest, _ = make_zone(tmp_path / "zones", "z_synth_alley_001", size=(70, 30))
    assert (
        mesh_main(["chunk", str(src), "--out", str(tmp_path / "elsewhere"), "--manifest", str(manifest)]) == 2
    )
