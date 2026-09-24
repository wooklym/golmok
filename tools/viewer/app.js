/* Golmok review viewer: CesiumJS, no ion token, local tilesets only.
 *
 * URL params:  ?tileset=/data/tileset.json[&tileset=/data/zones/z001/tileset.json...]
 *              &manifest=/data/manifest.json  (default: manifest.json next to the first tileset)
 * Exposes window.golmok for automation (smoke test): { viewer, layers, ready, stats() }.
 */
(function () {
  'use strict';
  var status = document.getElementById('status');
  var params = new URLSearchParams(location.search);
  var tilesetUrls = params.getAll('tileset');
  if (!tilesetUrls.length && !params.getAll('zone').length) tilesetUrls = ['/data/tileset.json'];
  var zoneUrls = params.getAll('zone');

  var viewer = new Cesium.Viewer('cesiumContainer', {
    baseLayer: false,
    baseLayerPicker: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    animation: false,
    timeline: false,
    fullscreenButton: false,
    selectionIndicator: false,
    infoBox: false,
    skyAtmosphere: new Cesium.SkyAtmosphere(),
    requestRenderMode: false,
    msaaSamples: 4
  });
  viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#2a2f36');
  viewer.scene.globe.showGroundAtmosphere = true;
  viewer.scene.globe.depthTestAgainstTerrain = false;
  viewer.scene.debugShowFramesPerSecond = false;
  viewer.scene.light = new Cesium.SunLight();
  viewer.clock.currentTime = Cesium.JulianDate.fromIso8601('2026-05-01T02:00:00Z'); // ~11:00 KST

  var layers = [];
  var origin = null; // { lon, lat, height } from manifest.json
  var zones = [];
  var golmok = { viewer: viewer, layers: layers, zones: zones, ready: false, errors: [] };
  window.golmok = golmok;

  function setStatus(t) { status.textContent = t; }

  function layerRow(layer) {
    var row = document.createElement('div');
    row.className = 'layer';
    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = true;
    cb.onchange = function () { layer.tileset.show = cb.checked; };
    var name = document.createElement('span');
    name.className = 'name'; name.title = layer.url; name.textContent = layer.url.replace(/^\/data\//, '');
    var x = document.createElement('button');
    x.className = 'x'; x.textContent = '×'; x.title = '제거';
    x.onclick = function () { removeLayer(layer); };
    row.append(cb, name, x);
    layer.row = row;
    document.getElementById('layers').appendChild(row);
  }

  function removeLayer(layer) {
    viewer.scene.primitives.remove(layer.tileset);
    layer.row.remove();
    layers.splice(layers.indexOf(layer), 1);
  }

  async function addTileset(url) {
    setStatus('로딩: ' + url);
    try {
      var tileset = await Cesium.Cesium3DTileset.fromUrl(url, {
        maximumScreenSpaceError: 4,
        skipLevelOfDetail: false,
        enableCollision: false
      });
      tileset.debugWireframe = document.getElementById('wire').checked;
      tileset.debugShowBoundingVolume = document.getElementById('bounds').checked;
      viewer.scene.primitives.add(tileset);
      var layer = { url: url, tileset: tileset, loadedTiles: 0 };
      tileset.tileLoad.addEventListener(function () { layer.loadedTiles += 1; });
      tileset.tileFailed.addEventListener(function (e) { golmok.errors.push('tileFailed ' + e.url + ': ' + e.message); });
      tileset.loadProgress.addEventListener(function (pending, processing) {
        if (pending === 0 && processing === 0) { setStatus('완료: ' + url); }
      });
      layers.push(layer);
      layerRow(layer);
      return layer;
    } catch (e) {
      golmok.errors.push(String(e));
      setStatus('실패: ' + url + ' — ' + e);
      throw e;
    }
  }

  async function loadManifest(firstTileset) {
    var url = params.get('manifest') || firstTileset.replace(/[^/]*$/, 'manifest.json');
    try {
      var r = await fetch(url);
      if (!r.ok) return;
      var m = await r.json();
      origin = { lon: m.origin.lon, lat: m.origin.lat, height: m.origin.height_ellipsoidal || m.origin.height_orthometric || 0 };
      golmok.manifest = m;
    } catch (e) { /* manifest is optional */ }
  }

  function enuFromCartesian(c) {
    if (!origin) return null;
    var o = Cesium.Cartesian3.fromDegrees(origin.lon, origin.lat, origin.height);
    var inv = Cesium.Matrix4.inverse(Cesium.Transforms.eastNorthUpToFixedFrame(o), new Cesium.Matrix4());
    return Cesium.Matrix4.multiplyByPoint(inv, c, new Cesium.Cartesian3());
  }

  // Readout on mouse move: lon/lat/height and ENU meters relative to the manifest origin.
  var handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
  handler.setInputAction(function (m) {
    var picked = viewer.scene.pickPosition(m.endPosition);
    if (!Cesium.defined(picked)) return;
    var carto = Cesium.Cartographic.fromCartesian(picked);
    var lines = [
      '위도 ' + Cesium.Math.toDegrees(carto.latitude).toFixed(6) + '  경도 ' + Cesium.Math.toDegrees(carto.longitude).toFixed(6),
      '타원체고 ' + carto.height.toFixed(2) + ' m'
    ];
    var enu = enuFromCartesian(picked);
    if (enu) lines.push('ENU  E ' + enu.x.toFixed(2) + '  N ' + enu.y.toFixed(2) + '  U ' + enu.z.toFixed(2));
    document.getElementById('readout').textContent = lines.join('\n');
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

  handler.setInputAction(function (m) {
    var p = viewer.scene.pick(m.position);
    if (p && p.content && p.content.tile) {
      var uris = (p.content.innerContents || [p.content]).map(function (c) { return c.url || ''; });
      setStatus('타일: ' + uris.join(', '));
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);


  // ---- Zone overlay (docs/spec/zone-manifest.md): footprint, origin, chunk boxes, portals, blockers ----
  var ZONE_COLORS = { footprint: Cesium.Color.fromCssColorString('#ffcc00'), chunk: Cesium.Color.fromCssColorString('#33ccff'),
                      portal: Cesium.Color.fromCssColorString('#ff66cc'), glass: Cesium.Color.fromCssColorString('#66ffcc'),
                      no_entry: Cesium.Color.fromCssColorString('#ff3333') };

  function zoneMatrix(manifest) {
    return Cesium.Matrix4.fromRowMajorArray(manifest.transform);
  }
  function toEcef(mat, p) {
    return Cesium.Matrix4.multiplyByPoint(mat, new Cesium.Cartesian3(p[0], p[1], p[2]), new Cesium.Cartesian3());
  }
  function boxEdges(mat, bbox) {
    var lo = bbox[0], hi = bbox[1];
    var c = function (x, y, z) { return toEcef(mat, [x ? hi[0] : lo[0], y ? hi[1] : lo[1], z ? hi[2] : lo[2]]); };
    var edges = [
      [c(0,0,0), c(1,0,0), c(1,1,0), c(0,1,0), c(0,0,0)],
      [c(0,0,1), c(1,0,1), c(1,1,1), c(0,1,1), c(0,0,1)],
      [c(0,0,0), c(0,0,1)], [c(1,0,0), c(1,0,1)], [c(1,1,0), c(1,1,1)], [c(0,1,0), c(0,1,1)]
    ];
    return edges;
  }
  function normalize(v) { var n = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / n, v[1] / n, v[2] / n]; }
  function cross(a, b) { return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]; }
  function blockerCorners(plane) {
    // Spec §3.1: height axis = zone +z projected onto the plane (or +y when the plane is horizontal); width = height x normal.
    var n = normalize(plane.normal_enu);
    var up = [0, 0, 1];
    var d = up[0]*n[0] + up[1]*n[1] + up[2]*n[2];
    var h = [up[0] - d*n[0], up[1] - d*n[1], up[2] - d*n[2]];
    if (Math.hypot(h[0], h[1], h[2]) < 1e-6) h = [0, 1, 0];
    h = normalize(h);
    var w = normalize(cross(h, n));
    var c = plane.center_enu, hw = plane.size_m[0] / 2, hh = plane.size_m[1] / 2;
    var pt = function (sw, sh) { return [c[0] + w[0]*sw + h[0]*sh, c[1] + w[1]*sw + h[1]*sh, c[2] + w[2]*sw + h[2]*sh]; };
    return [pt(-hw, -hh), pt(hw, -hh), pt(hw, hh), pt(-hw, hh)];
  }

  async function addZone(url) {
    setStatus('Zone 로딩: ' + url);
    var r = await fetch(url);
    if (!r.ok) { golmok.errors.push('zone fetch ' + url + ' ' + r.status); setStatus('실패: ' + url); throw new Error(r.status); }
    var m = await r.json();
    var mat = zoneMatrix(m);
    var ds = new Cesium.CustomDataSource(m.zone_id + '/v' + m.version);
    var ents = ds.entities;
    var h0 = m.origin.height_ellipsoidal;

    var ring = m.footprint_wgs84.coordinates[0];
    var fp = [];
    ring.forEach(function (ll) { fp.push(ll[0], ll[1], h0); });
    ents.add({ name: 'footprint', polyline: { positions: Cesium.Cartesian3.fromDegreesArrayHeights(fp), width: 3, material: ZONE_COLORS.footprint } });
    ents.add({ name: 'origin', position: toEcef(mat, [0, 0, 0]), point: { pixelSize: 9, color: ZONE_COLORS.footprint, outlineColor: Cesium.Color.BLACK, outlineWidth: 1 },
               label: { text: m.zone_id + ' v' + m.version, font: '12px sans-serif', pixelOffset: new Cesium.Cartesian2(0, -16), fillColor: Cesium.Color.WHITE, outlineColor: Cesium.Color.BLACK, outlineWidth: 2, style: Cesium.LabelStyle.FILL_AND_OUTLINE } });

    (m.layers && m.layers.visual && m.layers.visual.chunks || []).forEach(function (ch) {
      boxEdges(mat, ch.bbox_enu).forEach(function (edge) {
        ents.add({ name: 'chunk ' + ch.id, polyline: { positions: edge, width: 1.5, material: ZONE_COLORS.chunk } });
      });
    });

    (m.portals || []).forEach(function (p) {
      var pos = p.pose_enu.position, yaw = Cesium.Math.toRadians(p.pose_enu.yaw_deg);
      var tip = [pos[0] + Math.cos(yaw) * p.radius_m, pos[1] + Math.sin(yaw) * p.radius_m, pos[2]];
      ents.add({ name: 'portal ' + p.id, position: toEcef(mat, pos), point: { pixelSize: 8, color: ZONE_COLORS.portal },
                 label: { text: p.id + ' → ' + p.to_zone, font: '11px sans-serif', pixelOffset: new Cesium.Cartesian2(0, 14), fillColor: ZONE_COLORS.portal, outlineColor: Cesium.Color.BLACK, outlineWidth: 2, style: Cesium.LabelStyle.FILL_AND_OUTLINE } });
      ents.add({ name: 'portal dir ' + p.id, polyline: { positions: [toEcef(mat, pos), toEcef(mat, tip)], width: 3, material: ZONE_COLORS.portal } });
    });

    if (m.layers && m.layers.blockers && m.layers.blockers.uri) {
      try {
        var br = await fetch(url.replace(/[^/]*$/, '') + m.layers.blockers.uri);
        var blockers = br.ok ? await br.json() : { planes: [] };
        (blockers.planes || []).forEach(function (pl) {
          var corners = blockerCorners(pl).map(function (c) { return toEcef(mat, c); });
          ents.add({ name: 'blocker ' + pl.id, polygon: { hierarchy: corners, perPositionHeight: true,
                     material: (ZONE_COLORS[pl.kind] || ZONE_COLORS.no_entry).withAlpha(0.35), outline: true, outlineColor: ZONE_COLORS[pl.kind] || ZONE_COLORS.no_entry } });
        });
      } catch (e) { golmok.errors.push('blockers ' + e); }
    }

    viewer.dataSources.add(ds);
    var zone = { url: url, manifest: m, dataSource: ds, entityCount: ents.values.length };
    zones.push(zone);
    zoneRow(zone);
    setStatus('Zone 완료: ' + m.zone_id);
    return zone;
  }

  function zoneRow(zone) {
    var row = document.createElement('div');
    row.className = 'layer';
    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = true;
    cb.onchange = function () { zone.dataSource.show = cb.checked; };
    var name = document.createElement('span');
    name.className = 'name'; name.title = zone.url; name.textContent = 'zone ' + zone.manifest.zone_id;
    name.style.cursor = 'pointer';
    name.onclick = function () { viewer.flyTo(zone.dataSource, { duration: 0.8 }); };
    var x = document.createElement('button');
    x.className = 'x'; x.textContent = '×'; x.title = '제거';
    x.onclick = function () { viewer.dataSources.remove(zone.dataSource, true); row.remove(); zones.splice(zones.indexOf(zone), 1); };
    row.append(cb, name, x);
    document.getElementById('layers').appendChild(row);
  }

  function boundsOfAll() {
    var sphere = null;
    layers.forEach(function (l) {
      var s = l.tileset.boundingSphere;
      sphere = sphere ? Cesium.BoundingSphere.union(sphere, s) : s;
    });
    if (!sphere && zones.length) {
      var pts = zones.map(function (z) { return toEcef(zoneMatrix(z.manifest), [0, 0, 0]); });
      sphere = Cesium.BoundingSphere.fromPoints(pts);
      sphere.radius = Math.max(sphere.radius, 60);
    }
    return sphere;
  }

  function viewHome() {
    var s = boundsOfAll();
    if (s) viewer.camera.flyToBoundingSphere(s, { duration: 0.8, offset: new Cesium.HeadingPitchRange(0.4, -0.5, s.radius * 2.2) });
  }
  function viewTop() {
    var s = boundsOfAll();
    if (s) viewer.camera.flyToBoundingSphere(s, { duration: 0.8, offset: new Cesium.HeadingPitchRange(0, -Cesium.Math.PI_OVER_TWO, s.radius * 2.0) });
  }
  function viewWalk() {
    var lon = origin ? origin.lon : null, lat = origin ? origin.lat : null, h = origin ? origin.height : 0;
    if (lon === null) {
      var s = boundsOfAll(); if (!s) return;
      var c = Cesium.Cartographic.fromCartesian(s.center);
      lon = Cesium.Math.toDegrees(c.longitude); lat = Cesium.Math.toDegrees(c.latitude); h = c.height;
    }
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(lon, lat, h + 1.7),
      orientation: { heading: 0, pitch: Cesium.Math.toRadians(-5), roll: 0 },
      duration: 0.8
    });
  }

  document.getElementById('viewHome').onclick = viewHome;
  document.getElementById('viewTop').onclick = viewTop;
  document.getElementById('viewWalk').onclick = viewWalk;
  document.getElementById('wire').onchange = function (e) { layers.forEach(function (l) { l.tileset.debugWireframe = e.target.checked; }); };
  document.getElementById('bounds').onchange = function (e) { layers.forEach(function (l) { l.tileset.debugShowBoundingVolume = e.target.checked; }); };
  document.getElementById('stats').onchange = function (e) {
    document.getElementById('statsBox').hidden = !e.target.checked;
    viewer.scene.debugShowFramesPerSecond = e.target.checked;
  };
  document.getElementById('addForm').onsubmit = function (e) {
    e.preventDefault();
    var url = document.getElementById('addUrl').value.trim();
    if (!url) return;
    (/manifest\.json$/i.test(url) ? addZone(url) : addTileset(url)).catch(function () {});
  };

  golmok.stats = function () {
    return layers.map(function (l) {
      var st = l.tileset.statistics;
      return { url: l.url, loadedTiles: l.loadedTiles, visited: st.visited, selected: st.selected,
               numberOfCommands: st.numberOfCommands, geometryByteLength: st.geometryByteLength, texturesByteLength: st.texturesByteLength };
    });
  };
  setInterval(function () {
    if (document.getElementById('statsBox').hidden) return;
    document.getElementById('statsText').textContent = golmok.stats().map(function (s) {
      return s.url.replace(/^\/data\//, '') + '\n  tiles ' + s.loadedTiles + '  selected ' + s.selected + '  cmds ' + s.numberOfCommands +
        '\n  geom ' + (s.geometryByteLength / 1e6).toFixed(1) + ' MB  tex ' + (s.texturesByteLength / 1e6).toFixed(1) + ' MB';
    }).join('\n');
  }, 500);

  (async function main() {
    await loadManifest(tilesetUrls[0]);
    for (var i = 0; i < tilesetUrls.length; i++) {
      try { await addTileset(tilesetUrls[i]); } catch (e) { /* reported in status */ }
    }
    for (var j = 0; j < zoneUrls.length; j++) {
      try { await addZone(zoneUrls[j]); } catch (e) { /* reported in status */ }
    }
    viewHome();
    // Ready once every layer reports tilesLoaded (or after 60 s), so automation can read stats.
    await new Promise(function (resolve) {
      var started = Date.now();
      (function poll() {
        var allDone = layers.length > 0 && layers.every(function (l) { return l.tileset.tilesLoaded; });
        if (allDone || Date.now() - started > 60000 || layers.length === 0) return resolve();
        setTimeout(poll, 250);
      })();
    });
    golmok.ready = true;
    setStatus((layers.length || zones.length) ? '준비 완료 (' + layers.length + ' 레이어, ' + zones.length + ' zone)' : '레이어 없음');
  })();
})();
