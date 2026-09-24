"""Tests the pure-math part of unreal/.../golmok/basemap_import.py with a stub `unreal` module."""

import importlib
import itertools
import sys
import types
from pathlib import Path

import pytest

PY_DIR = Path(__file__).resolve().parents[2] / "unreal" / "Golmok" / "Content" / "Python"


@pytest.fixture(scope="module")
def mod():
    sys.modules.setdefault("unreal", types.ModuleType("unreal"))
    sys.path.insert(0, str(PY_DIR))
    try:
        yield importlib.import_module("golmok.basemap_import")
    finally:
        sys.path.remove(str(PY_DIR))


def apply(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def fake_import(bbox, scale, m):
    corners = [apply(m, c) for c in itertools.product(*zip(*bbox))]
    lo = tuple(min(c[i] for c in corners) * scale for i in range(3))
    hi = tuple(max(c[i] for c in corners) * scale for i in range(3))
    return lo, hi


TILES = [
    ([-400.0, -400.0, -2.0], [-200.0, -200.0, 1.0]),  # square terrain tile (symmetric on its own)
    ([100.0, -30.0, -0.4], [120.0, -20.0, 9.6]),  # building tile
    ([-15.0, 300.0, 1.5], [15.0, 330.0, 23.0]),
    ([200.0, 0.0, -1.0], [400.0, 200.0, 3.0]),
]


@pytest.mark.parametrize(
    "true_m",
    [
        ((1, 0, 0), (0, 0, -1), (0, 1, 0)),  # e.g. glTF (x, y, z) -> UE (x, -z, y)
        ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
        ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    ],
)
def test_recovers_scale_and_axes(mod, true_m):
    samples = [(fake_import(b, 100.0, true_m), b) for b in TILES]
    err, scale, m = mod._measure_import_mapping(samples)
    assert scale == pytest.approx(100.0, rel=1e-6)
    assert m == tuple(tuple(float(v) for v in row) for row in true_m)
    assert err == pytest.approx(0.0, abs=1e-6)


def test_target_matrix_maps_enu_to_east_south_up(mod):
    assert apply(mod.TARGET, (1, 0, 0)) == (100.0, 0.0, 0.0)
    assert apply(mod.TARGET, (0, 1, 0)) == (0.0, -100.0, 0.0)  # north -> -Y (Y is south)
    assert apply(mod.TARGET, (0, 0, 1)) == (0.0, 0.0, 100.0)
