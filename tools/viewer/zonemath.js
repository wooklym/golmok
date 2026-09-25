/* Golmok viewer: pure zone math (no Cesium), shared by app.js (browser global `GolmokZoneMath`) and the
 * unit tests (Node `require`, tools/viewer/test/unit.mjs and tools/tests/test_viewer_zonemath.py).
 *
 * Frames (docs/spec/zone-manifest.md §1):
 *   zone-local  x = east, y = north, z = up (m, right-handed)
 *   glTF        what golmok-mesh writes for collision.glb / collision/<id>.glb / blockers.glb:
 *               (x, y, z)_gltf = (east, up, -north)  -- golmok_tools/basemap/gltf.py `enu_to_gltf`,
 *               read back by golmok_tools/mesh/objio.py `gltf_to_enu`: (x, y, z)_gltf -> (x, -z, y)_enu
 *   ECEF        manifest.transform (row-major 4x4, zone-local -> ECEF)
 *
 * Matrices here are row-major arrays of 16 numbers (same layout as manifest.transform); app.js turns them
 * into Cesium.Matrix4 with Matrix4.fromRowMajorArray.
 */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GolmokZoneMath = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // glTF Y-up -> zone-local Z-up: east = x, north = -z, up = y. A +90 deg rotation about x (det +1);
  // numerically equal to Cesium's Axis.Y_UP_TO_Z_UP.
  var GLTF_TO_ZONE = [
    1, 0, 0, 0,
    0, 0, -1, 0,
    0, 1, 0, 0,
    0, 0, 0, 1
  ];

  function mul4(a, b) {
    var out = new Array(16);
    for (var r = 0; r < 4; r++) {
      for (var c = 0; c < 4; c++) {
        var s = 0;
        for (var k = 0; k < 4; k++) s += a[r * 4 + k] * b[k * 4 + c];
        out[r * 4 + c] = s;
      }
    }
    return out;
  }

  function apply4(m, p) {
    var x = p[0], y = p[1], z = p[2];
    return [
      m[0] * x + m[1] * y + m[2] * z + m[3],
      m[4] * x + m[5] * y + m[6] * z + m[7],
      m[8] * x + m[9] * y + m[10] * z + m[11]
    ];
  }

  function gltfToZoneLocal(p) { return apply4(GLTF_TO_ZONE, p); }

  /** Model matrix for a golmok-mesh GLB (glTF Y-up) placed in a zone: ECEF <- zone-local <- glTF.
   *  The GLB must be loaded WITHOUT Cesium's own axis correction (upAxis Z, forwardAxis X), see app.js. */
  function gltfModelMatrix(transform) {
    if (!transform || transform.length !== 16) throw new Error('manifest.transform must have 16 numbers');
    return mul4(transform, GLTF_TO_ZONE);
  }

  function normalize(v) { var n = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / n, v[1] / n, v[2] / n]; }
  function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }

  /** Blocker rectangle axes (spec §3.1, golmok_tools/mesh/blockers.py `plane_axes`): height = zone +z
   *  projected onto the plane (north when the plane is horizontal), width = height x normal. */
  function blockerAxes(normal) {
    var n = normalize(normal);
    var up = [0, 0, 1];
    var d = dot(up, n);
    var h = [up[0] - d * n[0], up[1] - d * n[1], up[2] - d * n[2]];
    if (Math.hypot(h[0], h[1], h[2]) < 1e-6) {
      var north = [0, 1, 0], dn = dot(north, n);
      h = [north[0] - dn * n[0], north[1] - dn * n[1], north[2] - dn * n[2]];
    }
    h = normalize(h);
    return { width: cross(h, n), height: h, normal: n };
  }

  /** Four zone-local corners of a blocker plane: (-w,-h), (+w,-h), (+w,+h), (-w,+h). */
  function blockerCorners(plane) {
    var ax = blockerAxes(plane.normal_enu), w = ax.width, h = ax.height;
    var c = plane.center_enu, hw = plane.size_m[0] / 2, hh = plane.size_m[1] / 2;
    function pt(sw, sh) { return [c[0] + w[0] * sw + h[0] * sh, c[1] + w[1] * sw + h[1] * sh, c[2] + w[2] * sw + h[2] * sh]; }
    return [pt(-hw, -hh), pt(hw, -hh), pt(hw, hh), pt(-hw, hh)];
  }

  /** Union of axis-aligned boxes [[min],[max]] (null for an empty list). */
  function unionBoxes(boxes) {
    if (!boxes || !boxes.length) return null;
    var lo = boxes[0][0].slice(), hi = boxes[0][1].slice();
    boxes.forEach(function (b) {
      for (var i = 0; i < 3; i++) { lo[i] = Math.min(lo[i], b[0][i]); hi[i] = Math.max(hi[i], b[1][i]); }
    });
    return [lo, hi];
  }

  /** Resolve a manifest-relative uri (spec §2: relative, '/', no '..', no absolute path, no scheme) against
   *  the manifest URL. Returns null when the uri breaks those rules. */
  function resolveZoneUri(manifestUrl, uri) {
    if (typeof uri !== 'string' || !uri || uri.charAt(0) === '/' || uri.indexOf('\\') >= 0 ||
        /^[A-Za-z][A-Za-z0-9+.-]*:/.test(uri) || uri.split('/').some(function (s) { return s === '..' || s === '.' || s === ''; })) {
      return null;
    }
    return manifestUrl.replace(/[^/]*$/, '') + uri;
  }

  /** GLB for a blockers layer: the uri itself when it is a GLB, else the derived blockers.glb next to the
   *  authoritative blockers.json (golmok-mesh blockers build writes <file>.glb, spec §2). */
  function blockersGlbUri(uri) {
    if (/\.glb$/i.test(uri)) return uri;
    if (/\.json$/i.test(uri)) return uri.replace(/\.json$/i, '.glb');
    return null;
  }

  return {
    GLTF_TO_ZONE: GLTF_TO_ZONE,
    mul4: mul4,
    apply4: apply4,
    gltfToZoneLocal: gltfToZoneLocal,
    gltfModelMatrix: gltfModelMatrix,
    blockerAxes: blockerAxes,
    blockerCorners: blockerCorners,
    unionBoxes: unionBoxes,
    resolveZoneUri: resolveZoneUri,
    blockersGlbUri: blockersGlbUri
  };
});
