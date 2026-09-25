/* Golmok review viewer: CesiumJS, no ion token, local tilesets only.
 *
 * URL params:  ?tileset=/data/tileset.json[&tileset=/data/zones/z001/tileset.json...]
 *              &manifest=/data/manifest.json  (default: manifest.json next to the first tileset)
 *              &zone=/zones/<zone_id>/v<n>/manifest.json  (repeatable; golmok-viewer --zone mounts the folder)
 * Exposes window.golmok for automation (smoke test): { viewer, layers, zones, overlay, ready, errors, warnings,
 * stats(), zoneStats(), setOverlay(kind, on) }.
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
    var url = params.get('manifest') || (firstTileset ? firstTileset.replace(/[^/]*$/, 'manifest.json') : null);
    if (!url) return;
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


  // ---- Zone overlay (docs/spec/zone-manifest.md): footprint, origin axes, chunk boxes, portals, blockers,
  // collision / blockers GLB meshes. Pure math (axes, blocker rectangles, uri rules) lives in zonemath.js.
  var ZM = window.GolmokZoneMath;
  var ZONE_COLORS = { footprint: Cesium.Color.fromCssColorString('#ffcc00'), chunk: Cesium.Color.fromCssColorString('#33ccff'),
                      portal: Cesium.Color.fromCssColorString('#ff66cc'), glass: Cesium.Color.fromCssColorString('#66ffcc'),
                      no_entry: Cesium.Color.fromCssColorString('#ff3333'), collision: Cesium.Color.fromCssColorString('#ff9933'),
                      blockersMesh: Cesium.Color.fromCssColorString('#cc66ff'),
                      axisE: Cesium.Color.RED, axisN: Cesium.Color.LIME, axisU: Cesium.Color.DODGERBLUE };
  // Overlay groups toggled by the "Zone 오버레이" checkboxes (all zones at once).
  var OVERLAY_KINDS = ['footprint', 'axes', 'chunks', 'portals', 'collision', 'blockers'];
  var overlay = { footprint: true, axes: true, chunks: true, portals: true, collision: true, blockers: true };
  var MODEL_ALPHA = 0.45;
  var AXIS_LEN_M = 5;
  golmok.overlay = overlay;
  golmok.warnings = [];

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
  function outlinedLabel(text, color, dy) {
    return { text: text, font: '12px sans-serif', pixelOffset: new Cesium.Cartesian2(0, dy), fillColor: color,
             outlineColor: Cesium.Color.BLACK, outlineWidth: 2, style: Cesium.LabelStyle.FILL_AND_OUTLINE };
  }

  /** Fetch a zone GLB and add it as a Cesium.Model placed by ZM.gltfModelMatrix (glTF Y-up -> zone-local
   *  -> ECEF). Cesium's own glTF axis correction is switched off (upAxis Z, forwardAxis X): by default it
   *  applies Y_UP_TO_Z_UP *and* Z_UP_TO_X_UP (glTF +Z forward -> +X), which would turn the zone 90 deg. */
  async function addZoneModel(zone, kind, url, color, missingIsError) {
    var r = await fetch(url);
    if (!r.ok) {
      var msg = kind + ' ' + url + ' ' + r.status;
      if (missingIsError) golmok.errors.push(msg); else golmok.warnings.push(msg);
      return null;
    }
    var bytes = new Uint8Array(await r.arrayBuffer());
    var model = await Cesium.Model.fromGltfAsync({
      gltf: bytes,
      basePath: url,
      modelMatrix: Cesium.Matrix4.fromRowMajorArray(ZM.gltfModelMatrix(zone.manifest.transform)),
      upAxis: Cesium.Axis.Z,
      forwardAxis: Cesium.Axis.X,
      color: color.withAlpha(MODEL_ALPHA),
      colorBlendMode: Cesium.ColorBlendMode.REPLACE,
      backFaceCulling: false,
      enableDebugWireframe: true,
      debugWireframe: document.getElementById('wire').checked,
      show: false
    });
    if (zone.removed) { model.destroy(); return null; }  // zone row removed while the GLB was loading
    zone.models[kind] = { url: url, model: model, bytes: bytes.length, failed: false };
    model.errorEvent.addEventListener(function (e) {
      zone.models[kind].failed = true;
      golmok.errors.push(kind + ' model ' + url + ': ' + (e && e.message || e));
    });
    viewer.scene.primitives.add(model);
    applyZoneVisibility(zone);
    return model;
  }

  function applyZoneVisibility(zone) {
    zone.dataSource.show = zone.shown;
    Object.keys(zone.groups).forEach(function (k) { zone.groups[k].show = overlay[k]; });
    Object.keys(zone.models).forEach(function (k) { zone.models[k].model.show = zone.shown && overlay[k]; });
  }

  golmok.setOverlay = function (kind, on) {
    if (OVERLAY_KINDS.indexOf(kind) < 0) throw new Error('unknown overlay ' + kind);
    overlay[kind] = !!on;
    var cb = document.getElementById('ov_' + kind);
    if (cb) cb.checked = !!on;
    zones.forEach(applyZoneVisibility);
  };

  async function addZone(url) {
    setStatus('Zone 로딩: ' + url);
    var r = await fetch(url);
    if (!r.ok) { golmok.errors.push('zone fetch ' + url + ' ' + r.status); setStatus('실패: ' + url); throw new Error(r.status); }
    var m, mat;
    try {
      m = await r.json();
      if (!m || !m.origin || !m.footprint_wgs84 || !Array.isArray(m.transform) || m.transform.length !== 16 ||
          !m.transform.every(Number.isFinite)) throw new Error('origin / footprint_wgs84 / transform(4×4 row-major) 없음');
      mat = zoneMatrix(m);
    } catch (e) {
      golmok.errors.push('zone manifest ' + url + ': ' + (e && e.message || e)); setStatus('실패: ' + url); throw e;
    }
    var ds = new Cesium.CustomDataSource(m.zone_id + '/v' + m.version);
    var ents = ds.entities;
    var h0 = m.origin.height_ellipsoidal;
    var groups = {};
    ['footprint', 'axes', 'chunks', 'portals', 'blockers'].forEach(function (k) { groups[k] = ents.add({ name: k }); });
    function add(group, e) { e.parent = groups[group]; return ents.add(e); }

    var ring = m.footprint_wgs84.coordinates[0];
    var fp = [];
    ring.forEach(function (ll) { fp.push(ll[0], ll[1], h0); });
    add('footprint', { name: 'footprint', polyline: { positions: Cesium.Cartesian3.fromDegreesArrayHeights(fp), width: 3, material: ZONE_COLORS.footprint } });

    // Origin and zone-local axes (x = east red, y = north green, z = up blue): a check that the GLB meshes
    // and the manifest transform agree.
    var o = toEcef(mat, [0, 0, 0]);
    add('axes', { name: 'origin', position: o, point: { pixelSize: 9, color: ZONE_COLORS.footprint, outlineColor: Cesium.Color.BLACK, outlineWidth: 1 },
                  label: outlinedLabel(m.zone_id + ' v' + m.version, Cesium.Color.WHITE, -16) });
    [['E', [AXIS_LEN_M, 0, 0], ZONE_COLORS.axisE], ['N', [0, AXIS_LEN_M, 0], ZONE_COLORS.axisN], ['U', [0, 0, AXIS_LEN_M], ZONE_COLORS.axisU]].forEach(function (a) {
      var tip = toEcef(mat, a[1]);
      add('axes', { name: 'axis ' + a[0], polyline: { positions: [o, tip], width: 8, material: new Cesium.PolylineArrowMaterialProperty(a[2]) } });
      add('axes', { name: 'axis label ' + a[0], position: tip, label: outlinedLabel(a[0], a[2], -10) });
    });

    // Visual chunks are OBJ + MTL (WP-03, UDIM textures); the viewer draws only their boxes (README).
    (m.layers && m.layers.visual && m.layers.visual.chunks || []).forEach(function (ch) {
      boxEdges(mat, ch.bbox_enu).forEach(function (edge) {
        add('chunks', { name: 'chunk ' + ch.id, polyline: { positions: edge, width: 1.5, material: ZONE_COLORS.chunk } });
      });
    });

    (m.portals || []).forEach(function (p) {
      var pos = p.pose_enu.position, yaw = Cesium.Math.toRadians(p.pose_enu.yaw_deg);
      var tip = [pos[0] + Math.cos(yaw) * p.radius_m, pos[1] + Math.sin(yaw) * p.radius_m, pos[2]];
      add('portals', { name: 'portal ' + p.id, position: toEcef(mat, pos), point: { pixelSize: 8, color: ZONE_COLORS.portal },
                       label: outlinedLabel(p.id + ' → ' + p.to_zone, ZONE_COLORS.portal, 14) });
      add('portals', { name: 'portal dir ' + p.id, polyline: { positions: [toEcef(mat, pos), toEcef(mat, tip)], width: 3, material: ZONE_COLORS.portal } });
    });

    var zone = { url: url, manifest: m, dataSource: ds, groups: groups, models: {}, shown: true, removed: false, entityCount: 0 };
    var layersM = m.layers || {};
    var blockersUri = layersM.blockers && layersM.blockers.uri;
    if (blockersUri && !/\.glb$/i.test(blockersUri)) {
      // blockers.json (authoritative, spec §3.1): flat translucent rectangles
      var bUrl = ZM.resolveZoneUri(url, blockersUri);
      try {
        if (!bUrl) throw new Error('bad uri ' + blockersUri);
        var br = await fetch(bUrl);
        if (!br.ok) throw new Error(bUrl + ' ' + br.status);
        var blockers = await br.json();
        (blockers.planes || []).forEach(function (pl) {
          var corners = ZM.blockerCorners(pl).map(function (c) { return toEcef(mat, c); });
          var col = ZONE_COLORS[pl.kind] || ZONE_COLORS.no_entry;
          add('blockers', { name: 'blocker ' + pl.id, polygon: { hierarchy: corners, perPositionHeight: true,
                            material: col.withAlpha(0.35), outline: true, outlineColor: col } });
        });
      } catch (e) { golmok.errors.push('blockers ' + e); }
    }

    zone.entityCount = ents.values.length - Object.keys(groups).length;
    viewer.dataSources.add(ds);
    zones.push(zone);
    zoneRow(zone);

    // GLB meshes (golmok-mesh: glTF Y-up). collision is required by the spec; blockers.glb is derived from
    // blockers.json, so a missing one is only a warning unless the manifest points at the GLB itself.
    var colUri = layersM.collision && layersM.collision.uri;
    if (colUri) {
      var cUrl = ZM.resolveZoneUri(url, colUri);
      if (!cUrl) golmok.errors.push('collision bad uri ' + colUri);
      else if (!/\.glb$/i.test(colUri)) golmok.warnings.push('collision not a GLB: ' + colUri);
      else await addZoneModel(zone, 'collision', cUrl, ZONE_COLORS.collision, true).catch(function (e) { golmok.errors.push('collision ' + e); });
    }
    if (blockersUri) {
      var gUri = ZM.blockersGlbUri(blockersUri);
      var gUrl = gUri && ZM.resolveZoneUri(url, gUri);
      if (gUrl) await addZoneModel(zone, 'blockers', gUrl, ZONE_COLORS.blockersMesh, /\.glb$/i.test(blockersUri)).catch(function (e) { golmok.errors.push('blockers glb ' + e); });
      else golmok.errors.push('blockers bad uri ' + blockersUri);
    }
    applyZoneVisibility(zone);
    setStatus('Zone 완료: ' + m.zone_id);
    return zone;
  }

  function zoneRow(zone) {
    var row = document.createElement('div');
    row.className = 'layer';
    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = true;
    cb.onchange = function () { zone.shown = cb.checked; applyZoneVisibility(zone); };
    var name = document.createElement('span');
    name.className = 'name'; name.title = zone.url; name.textContent = 'zone ' + zone.manifest.zone_id;
    name.style.cursor = 'pointer';
    name.onclick = function () { viewer.flyTo(zone.dataSource, { duration: 0.8 }); };
    var x = document.createElement('button');
    x.className = 'x'; x.textContent = '×'; x.title = '제거';
    x.onclick = function () {
      zone.removed = true;
      viewer.dataSources.remove(zone.dataSource, true);
      Object.keys(zone.models).forEach(function (k) { viewer.scene.primitives.remove(zone.models[k].model); });
      row.remove(); zones.splice(zones.indexOf(zone), 1);
    };
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
  document.getElementById('wire').onchange = function (e) {
    layers.forEach(function (l) { l.tileset.debugWireframe = e.target.checked; });
    zones.forEach(function (z) { Object.keys(z.models).forEach(function (k) { z.models[k].model.debugWireframe = e.target.checked; }); });
  };
  OVERLAY_KINDS.forEach(function (k) {
    var cb = document.getElementById('ov_' + k);
    if (cb) cb.onchange = function () { golmok.setOverlay(k, cb.checked); };
  });
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

  // Zone summary for automation: entity count, and per GLB model its state and bounding sphere.
  golmok.zoneStats = function () {
    return zones.map(function (z) {
      var models = {};
      Object.keys(z.models).forEach(function (k) {
        var md = z.models[k].model;
        var bs = md.ready ? md.boundingSphere : null;
        models[k] = { url: z.models[k].url, bytes: z.models[k].bytes, ready: md.ready, show: md.show,
                      center: bs ? [bs.center.x, bs.center.y, bs.center.z] : null, radius: bs ? bs.radius : null };
      });
      var groups = {};
      Object.keys(z.groups).forEach(function (k) { groups[k] = z.groups[k].isShowing; });
      return { id: z.manifest.zone_id, entities: z.entityCount, shown: z.shown, groups: groups, models: models };
    });
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
    if (!origin && zones.length) {  // zone only: ENU readout relative to the first zone origin
      var zo = zones[0].manifest.origin;
      origin = { lon: zo.lon, lat: zo.lat, height: zo.height_ellipsoidal };
    }
    viewHome();
    // Ready once every layer reports tilesLoaded (or after 60 s), so automation can read stats.
    await new Promise(function (resolve) {
      var started = Date.now();
      (function poll() {
        var tilesDone = layers.every(function (l) { return l.tileset.tilesLoaded; });
        var modelsDone = zones.every(function (z) { return Object.keys(z.models).every(function (k) { return z.models[k].model.ready || z.models[k].failed; }); });
        if ((tilesDone && modelsDone) || Date.now() - started > 60000) return resolve();
        setTimeout(poll, 250);
      })();
    });
    golmok.ready = true;
    setStatus((layers.length || zones.length) ? '준비 완료 (' + layers.length + ' 레이어, ' + zones.length + ' zone)' : '레이어 없음');
  })();
})();
