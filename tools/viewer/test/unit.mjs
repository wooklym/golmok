// Unit tests for zonemath.js (no browser, no dependencies): node test/unit.mjs
// The Python side (tools/tests/test_viewer_zonemath.py) checks the same functions against golmok-mesh's
// GLB writer (golmok_tools/basemap/gltf.py enu_to_gltf) and blocker axes (golmok_tools/mesh/blockers.py).
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import test from 'node:test';

const ZM = createRequire(import.meta.url)('../zonemath.js');
const close = (a, b, tol = 1e-9) => a.forEach((v, i) => assert.ok(Math.abs(v - b[i]) <= tol, `${a} != ${b}`));

test('glTF (east, up, -north) -> zone-local (east, north, up)', () => {
  close(ZM.gltfToZoneLocal([1, 0, 0]), [1, 0, 0]); // east
  close(ZM.gltfToZoneLocal([0, 1, 0]), [0, 0, 1]); // glTF +y = up
  close(ZM.gltfToZoneLocal([0, 0, -1]), [0, 1, 0]); // glTF -z = north
  close(ZM.gltfToZoneLocal([3, 5, -7]), [3, 7, 5]);
});

test('GLTF_TO_ZONE is a proper rotation (+90 deg about x) and equals Cesium Axis.Y_UP_TO_Z_UP', () => {
  const m = ZM.GLTF_TO_ZONE;
  const r = [[m[0], m[1], m[2]], [m[4], m[5], m[6]], [m[8], m[9], m[10]]];
  const det = r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1]) - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0]) +
    r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0]);
  assert.equal(det, 1);
  // Cesium: Axis.Y_UP_TO_Z_UP = Matrix4.fromRotationTranslation(Matrix3.fromRotationX(PI/2)), row-major:
  const c = Math.cos(Math.PI / 2), s = Math.sin(Math.PI / 2);
  close(m, [1, 0, 0, 0, 0, c, -s, 0, 0, s, c, 0, 0, 0, 0, 1], 1e-15);
});

test('gltfModelMatrix = transform * GLTF_TO_ZONE (row-major)', () => {
  // spec §4 B fixture transform (tools/tests/fixtures/zones/z_synthetic_001/v1/manifest.json)
  const t = [-0.7994225996253806, 0.3662405942358524, -0.4762261378189653, -3041244.8025000524,
    -0.6007690964157514, -0.4873436561220112, 0.6336976042478246, 4046878.9766597343,
    0.0, 0.7926941326712345, 0.6096195633578366, 3867051.561014832, 0, 0, 0, 1];
  const mm = ZM.gltfModelMatrix(t);
  const g = [2, 3, -4]; // glTF: east 2, up 3, north 4
  close(ZM.apply4(mm, g), ZM.apply4(t, [2, 4, 3]), 1e-6);
  close(ZM.apply4(mm, [0, 0, 0]), [t[3], t[7], t[11]], 1e-6);
  assert.throws(() => ZM.gltfModelMatrix([1, 2, 3]));
});

test('blocker corners follow spec §3.1 (height = up projected, width = height x normal)', () => {
  const [a, b, c, d] = ZM.blockerCorners({ center_enu: [-8, 5, 1.5], normal_enu: [0, -1, 0], size_m: [3, 2.5] });
  // normal -y: height +z, width = z x (-y) = +x
  close(a, [-9.5, 5, 0.25]); close(b, [-6.5, 5, 0.25]); close(c, [-6.5, 5, 2.75]); close(d, [-9.5, 5, 2.75]);
  const ax = ZM.blockerAxes([0, 0, 2]); // horizontal plane: height = north
  close(ax.height, [0, 1, 0]); close(ax.width, [1, 0, 0]); close(ax.normal, [0, 0, 1]);
});

test('uri rules (spec §2) and blockers GLB path', () => {
  const m = '/zones/z_a/v1/manifest.json';
  assert.equal(ZM.resolveZoneUri(m, 'collision.glb'), '/zones/z_a/v1/collision.glb');
  assert.equal(ZM.resolveZoneUri(m, 'collision/c_e000_n000.glb'), '/zones/z_a/v1/collision/c_e000_n000.glb');
  for (const bad of ['../x.glb', 'a/../../x.glb', '/abs.glb', 'http://evil/x.glb', 'C:/x.glb', 'a\\b.glb', './x.glb', 'a//b.glb', '', null]) {
    assert.equal(ZM.resolveZoneUri(m, bad), null, String(bad));
  }
  assert.equal(ZM.blockersGlbUri('blockers.json'), 'blockers.glb');
  assert.equal(ZM.blockersGlbUri('sub/b.GLB'), 'sub/b.GLB');
  assert.equal(ZM.blockersGlbUri('blockers.txt'), null);
  assert.deepEqual(ZM.unionBoxes([[[0, 0, 0], [1, 1, 1]], [[-1, 2, -3], [0, 3, 0]]]), [[-1, 0, -3], [1, 3, 1]]);
  assert.equal(ZM.unionBoxes([]), null);
});
