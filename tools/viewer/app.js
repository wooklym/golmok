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
  if (!tilesetUrls.length) tilesetUrls = ['/data/tileset.json'];

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
  var golmok = { viewer: viewer, layers: layers, ready: false, errors: [] };
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

  function boundsOfAll() {
    var sphere = null;
    layers.forEach(function (l) {
      var s = l.tileset.boundingSphere;
      sphere = sphere ? Cesium.BoundingSphere.union(sphere, s) : s;
    });
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
    if (url) addTileset(url).catch(function () {});
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
    setStatus(layers.length ? '준비 완료 (' + layers.length + ' 레이어)' : '레이어 없음');
  })();
})();
