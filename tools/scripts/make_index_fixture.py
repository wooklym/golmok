"""Generate the WP-09 Zone Index fixture: z_synthetic_002 v1 (manifest + blockers only) + index/ (design §2).

Run from anywhere:

    python tools/scripts/make_index_fixture.py            # (re)write both copies of everything
    python tools/scripts/make_index_fixture.py --check    # exit 1 if a committed file differs

What is written (byte-identical in both places; nothing else of the generated zone is committed):

    tools/tests/fixtures/zones/z_synthetic_002/v1/{manifest.json, blockers.json}       (tests)
    unreal/Golmok/Content/Golmok/Zones/z_synthetic_002/v1/{manifest.json, blockers.json}  (AGolmokZone reads)
    tools/tests/fixtures/zones/index/{zones.json, cells/16_<x>_<y>.json}         (spec §6 path: <zones>/index)
    unreal/Golmok/Content/Golmok/Zones/index/{zones.json, cells/16_<x>_<y>.json}   (FGolmokZoneIndex reads)

z_synthetic_002 is make_synthetic_zone.py with `--zone-id z_synthetic_002 --offset-m 200,0`: the same
synthetic scan as the WP-06 zone, but its origin 200 m east of z_synthetic_001's (spec §4 B), which puts it in
the next z16 cell column (x 55874). It has no portals and no assets in the project (wire boxes in UE).
The index is `golmok_tools.zone.index.build_index` over a temporary zones root holding the committed
z_synthetic_001, z_synthetic_001_interior and the generated z_synthetic_002 — the same three zones as
Content/Golmok/Zones, so the committed index describes the Content tree exactly (design §2 cell table).
No timestamps, no randomness: two runs give identical bytes; tests/test_ue_zone_index_fixture.py regenerates
with write_all() into a temp folder and compares. The zone tests' shared `sys.path` entry for tools/scripts
lets `import make_index_fixture` work from pytest.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path

try:
    from golmok_tools.zone import index as zone_index
    from golmok_tools.zone import manifest as zm
except ImportError:  # no `pip install -e tools`: import from the checkout
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from golmok_tools.zone import index as zone_index
    from golmok_tools.zone import manifest as zm

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import make_synthetic_zone as msz  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
FIXTURE_ZONES_REL = Path("tools/tests/fixtures/zones")
CONTENT_ZONES_REL = Path("unreal/Golmok/Content/Golmok/Zones")
ZONE_ID = "z_synthetic_002"
VERSION = 1
OFFSET_M = "200,0"  # --offset-m east,north of z_synthetic_001's origin (design §0 "픽스처")
SOURCE_ZONES = ("z_synthetic_001", "z_synthetic_001_interior")  # committed fixtures the index is built with
COPY_FILES = (zm.MANIFEST_NAME, "blockers.json")  # exactly what zone_import._copy_files puts into Content
INDEX_DIR_NAME = zone_index.INDEX_DIR_NAME
OUTPUT_DIRS = (  # relative to a repo root; every written file lives under one of these
    FIXTURE_ZONES_REL / ZONE_ID,
    CONTENT_ZONES_REL / ZONE_ID,
    FIXTURE_ZONES_REL / INDEX_DIR_NAME,
    CONTENT_ZONES_REL / INDEX_DIR_NAME,
)


def generate_zone_002(tmp: Path) -> Path:
    """make_synthetic_zone into <tmp>; returns the generated <tmp>/zones/z_synthetic_002/v1 folder."""
    argv = ["--out", str(tmp), "--zone-id", ZONE_ID, "--offset-m", OFFSET_M, "--quiet"]
    with contextlib.redirect_stdout(io.StringIO()):  # its "next: ..." line is not ours
        rc = msz.main(argv)
    if rc != 0:
        raise RuntimeError(f"make_synthetic_zone.py {' '.join(argv)} failed (rc {rc})")
    vdir = tmp / "zones" / ZONE_ID / f"v{VERSION}"
    for name in COPY_FILES:
        if not (vdir / name).is_file():
            raise RuntimeError(f"{vdir / name} was not generated")
    return vdir


def build(tmp: Path, repo: Path = REPO) -> tuple[Path, dict, dict]:
    """(generated v1 folder of z_synthetic_002, zones.json dict, {(z, x, y): cell dict}) using <tmp>."""
    vdir = generate_zone_002(tmp)
    root = tmp / "zones_root"
    for zone_id in SOURCE_ZONES:
        src = repo / FIXTURE_ZONES_REL / zone_id
        if not src.is_dir():
            raise RuntimeError(f"committed fixture {src} is missing")
        shutil.copytree(src, root / zone_id)
    target = root / ZONE_ID / f"v{VERSION}"
    target.mkdir(parents=True)
    for name in COPY_FILES:
        shutil.copyfile(vdir / name, target / name)
    problems: list[str] = []
    zones, cells = zone_index.build_index(root, problems)
    if problems:
        raise RuntimeError("index build reported problems:\n" + "\n".join(problems))
    ids = [z["id"] for z in zones["zones"]]
    if ids != sorted([*SOURCE_ZONES, ZONE_ID]):
        raise RuntimeError(f"index holds {ids}, expected {sorted([*SOURCE_ZONES, ZONE_ID])}")
    return vdir, zones, cells


def write_all(repo: Path = REPO) -> list[Path]:
    """Write the four output folders under <repo> (OUTPUT_DIRS); returns every file written, sorted."""
    repo = Path(repo)
    tmp = Path(tempfile.mkdtemp(prefix="golmok_index_fixture_")).resolve()
    try:
        vdir, zones, cells = build(tmp)
        written: list[Path] = []
        for zones_rel in (FIXTURE_ZONES_REL, CONTENT_ZONES_REL):
            zone_dir = repo / zones_rel / ZONE_ID / f"v{VERSION}"
            if (repo / zones_rel / ZONE_ID).exists():
                shutil.rmtree(repo / zones_rel / ZONE_ID)
            zone_dir.mkdir(parents=True)
            for name in COPY_FILES:
                shutil.copyfile(vdir / name, zone_dir / name)
                written.append(zone_dir / name)
            index_dir = repo / zones_rel / INDEX_DIR_NAME
            if index_dir.exists():
                shutil.rmtree(index_dir)
            written += zone_index.write_index(zones, cells, index_dir)
        return sorted(written)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _tree(folder: Path) -> dict[str, bytes]:
    """{normalized relative path: bytes} of every file under folder (sorted rglob; CRLF folded to LF)."""
    out = {}
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            rel = os.path.normpath(str(p.relative_to(folder)))
            out[rel] = p.read_bytes().replace(b"\r\n", b"\n")
    return out


def check(repo: Path = REPO) -> list[str]:
    """Regenerate into a temp repo root and compare with the committed copies; [] when identical."""
    repo = Path(repo)
    tmp = Path(tempfile.mkdtemp(prefix="golmok_index_check_")).resolve()
    try:
        write_all(tmp)
        diffs = []
        for rel in OUTPUT_DIRS:
            want = _tree(tmp / rel)
            got = _tree(repo / rel) if (repo / rel).is_dir() else {}
            for name in sorted(set(want) | set(got)):
                if name not in got:
                    diffs.append(f"missing {rel.as_posix()}/{name}")
                elif name not in want:
                    diffs.append(f"extra {rel.as_posix()}/{name}")
                elif want[name] != got[name]:
                    diffs.append(f"differs {rel.as_posix()}/{name}")
        return diffs
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="compare the committed files instead of writing")
    args = ap.parse_args(argv)
    if args.check:
        diffs = check()
        for d in diffs:
            print(d)
        print(f"check: {'OK' if not diffs else f'FAIL ({len(diffs)} files)'}")
        return 1 if diffs else 0
    for p in write_all():
        print(f"wrote {p.relative_to(REPO).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
