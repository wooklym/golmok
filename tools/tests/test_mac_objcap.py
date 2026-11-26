"""WP-21 (D-022): tools/mac/objcap (golmok-objcap, Apple Object Capture wrapper) — static checks only.

The Swift package needs Xcode and macOS, so CI does not build it. These checks pin the parts other docs rely
on: the command/option names in the README, the availability guards around newer RealityKit API, no package
dependencies (license rule D-002: only Apple OS frameworks), and that build products stay out of git.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "tools" / "mac" / "objcap"
MAIN = PKG / "Sources" / "golmok-objcap" / "main.swift"
COLMAP = PKG / "Sources" / "golmok-objcap" / "Colmap.swift"
README = PKG / "README.md"

RUN_OPTIONS = (
    "--detail",
    "--format",
    "--ordering",
    "--sensitivity",
    "--poses",
    "--point-cloud",
    "--no-object-masking",
    "--ignore-bounding-box",
    "--checkpoint",
)
DETAILS = ("preview", "reduced", "medium", "full", "raw")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_package_files_exist():
    for p in (PKG / "Package.swift", MAIN, COLMAP, README, PKG / ".gitignore"):
        assert p.is_file(), p


def test_package_has_no_dependencies_and_targets_macos14():
    text = read(PKG / "Package.swift")
    assert text.startswith("// swift-tools-version:")
    assert ".package(" not in text, "golmok-objcap must not pull third-party packages (D-002)"
    assert "dependencies:" not in text
    assert ".macOS(.v14)" in text


def test_only_apple_frameworks_imported():
    allowed = {"CoreGraphics", "Foundation", "ImageIO", "RealityKit", "simd"}
    for src in (MAIN, COLMAP):
        imports = set(re.findall(r"^import (\w+)", read(src), re.MULTILINE))
        assert imports <= allowed, (src.name, imports - allowed)


def test_build_products_ignored():
    lines = read(PKG / ".gitignore").splitlines()
    assert ".build/" in lines and ".swiftpm/" in lines


def test_only_text_sources_in_package():
    for p in PKG.rglob("*"):
        if p.is_file() and ".build" not in p.parts and ".swiftpm" not in p.parts:
            assert p.suffix in {".swift", ".md"} or p.name == ".gitignore", p


def test_commands_and_options_in_usage_and_readme():
    main, readme = read(MAIN), read(README)
    for cmd in ("limits", "run", "colmap"):
        assert f'case "{cmd}":' in main, cmd
        assert f"golmok-objcap {cmd}" in readme, cmd
    for opt in RUN_OPTIONS:
        assert f'case "{opt}"' in main, opt
        assert opt in readme, opt
    for detail in DETAILS:
        assert f'case "{detail}": o.detail = .{detail}' in main, detail


def test_newer_api_behind_availability_checks():
    main = read(MAIN)
    # Limits / poses need macOS 14; Pose.intrinsics / lensDistortionData need macOS 26; ignoreBoundingBox 15.
    assert "if #available(macOS 14.0, *)" in main
    assert "@available(macOS 14.0, *)\nfunc runCommand" in main
    i = main.index("p.intrinsics")
    k = main.rfind("if #available(macOS 26.0, *)", 0, i)
    assert k >= 0 and i - k < 200
    j = main.index("config.ignoreBoundingBox = true")
    k = main.rfind("#available(macOS 15.0, *)", 0, j)
    assert k >= 0 and j - k < 120
    assert "PhotogrammetrySession.isSupported" in main
    assert "maximumNumberOfInputImages" in main and "maximumInputImageDimension" in main


def test_exit_codes_documented():
    main, readme = read(MAIN), read(README)
    assert "return ok ? 0 : 1" in main
    assert "return 3" in main
    for code in ("0", "1", "2", "3"):
        assert f"`{code}`" in readme, code


def test_poses_written_unconverted_and_convention_marked():
    main, colmap, readme = read(MAIN), read(COLMAP), read(README)
    assert "No conversion applied" in main
    assert "EXPERIMENTAL" in colmap
    assert "diag(1, -1, -1)" in colmap
    # The measured (not Apple-documented) convention and the open items stay marked in the README.
    assert "[미확인]" in readme
    assert "Buddha" in readme and "CC BY 4.0" in readme


def test_no_data_paths_inside_repo():
    readme = read(README)
    assert "~/golmok-tools/objcap" in readme
    assert "~/golmok_data/recon-smoke/objcap" in readme
    assert "--scratch-path" in readme
