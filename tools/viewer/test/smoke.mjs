// Headless smoke test: serve a basemap folder with golmok-viewer, open the page, wait for tiles,
// take a screenshot, fail on console errors or zero loaded tiles.
// WP-11: also loads two zones with collision / blockers GLB meshes (golmok-mesh output, glTF Y-up):
//   - the WP-02 fixture z_synthetic_001 (copied under /data/zones; collision.glb borrowed from the generator,
//     blockers.glb built from its own blockers.json with golmok-mesh)
//   - the WP-06 generator zone z_synthetic_scan_001 (tools/scripts/make_synthetic_zone.py), mounted with
//     golmok-viewer --zone, whose model placement is checked against the manifest bboxes (axis conversion)
// and exercises the overlay toggles. Generated files stay in test/out (git-ignored).
//
//   GOLMOK_DATA=<basemap out folder> node test/smoke.mjs
//   (defaults to a tiny synthetic basemap built with tools/tests helpers if GOLMOK_DATA is unset)
//
// Env: GOLMOK_PORT (default 8777), GOLMOK_SHOT (screenshot path), PLAYWRIGHT_PROXY (e.g. http://host:port)
import { spawn } from 'node:child_process';
import { copyFileSync, cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const here = dirname(fileURLToPath(import.meta.url));
const toolsDir = resolve(here, '..', '..');
const port = Number(process.env.GOLMOK_PORT || 8777);
const shot = process.env.GOLMOK_SHOT || resolve(here, 'out', 'smoke.png');
let data = process.env.GOLMOK_DATA;

function run(cmd, args, opts = {}) {
  return new Promise((res, rej) => {
    const p = spawn(cmd, args, { stdio: 'inherit', ...opts });
    p.on('exit', (code) => (code === 0 ? res() : rej(new Error(`${cmd} exited ${code}`))));
  });
}

if (!data) {
  data = resolve(here, 'out', 'synthetic');
  mkdirSync(data, { recursive: true });
  const py = process.platform === 'win32' ? 'python' : 'python3';
  await run(py, ['-c', `
import sys; sys.path.insert(0, ${JSON.stringify(resolve(toolsDir, 'tests'))})
from pathlib import Path
from argparse import Namespace
import test_basemap as t
d = Path(${JSON.stringify(data)})
t.write_shp(d/'bld.shp'); t.write_dem(d/'dem.tif'); t.write_ortho(d/'ortho.tif')
from golmok_tools.basemap.build import build
build(Namespace(buildings=d/'bld.shp', dem=[str(d/'dem.tif')], ortho=[str(d/'ortho.tif')], center=f"{t.LAT},{t.LON}",
  radius=400.0, out=d/'out', height_field='A16', floors_field='FLOORS', usage_field='A9', id_field='A1', src_crs=None,
  encoding='cp949', tile_size=200.0, terrain_spacing=10.0, texture_size=512, geoid_offset=0.0, exclude=None, no_terrain=False))
print('synthetic basemap ready')
`], { cwd: toolsDir });
  data = resolve(data, 'out');
}
if (!existsSync(resolve(data, 'tileset.json'))) throw new Error(`no tileset.json in ${data}`);

const py = process.platform === 'win32' ? 'python' : 'python3';

// WP-06 synthetic zone (real golmok-mesh pipeline): collision.glb, collision/<chunk>.glb, blockers.json/.glb
const synthOut = resolve(here, 'out', 'synthzone');
await run(py, [resolve(toolsDir, 'scripts', 'make_synthetic_zone.py'), '--out', synthOut, '--force', '--quiet'], { cwd: toolsDir });
const scanZone = resolve(synthOut, 'zones', 'z_synthetic_scan_001', 'v1');
if (!existsSync(resolve(scanZone, 'collision.glb'))) throw new Error(`no collision.glb in ${scanZone}`);

// Zone overlay: the WP-02 fixture zone next to the basemap (copied, never modified), with GLB meshes.
const fixtureZone = resolve(toolsDir, 'tests', 'fixtures', 'zones', 'z_synthetic_001');
const fixtureCopy = resolve(data, 'zones', 'z_synthetic_001');
rmSync(fixtureCopy, { recursive: true, force: true });
cpSync(fixtureZone, fixtureCopy, { recursive: true });
copyFileSync(resolve(scanZone, 'collision.glb'), resolve(fixtureCopy, 'v1', 'collision.glb'));
await run(py, ['-c', 'import sys; from golmok_tools.mesh.cli import main; sys.exit(main(sys.argv[1:]))',
  'blockers', 'build', resolve(fixtureCopy, 'v1', 'blockers.json')], { cwd: toolsDir });
const zoneParam = '&zone=/data/zones/z_synthetic_001/v1/manifest.json&zone=/zones/z_synthetic_scan_001/v1/manifest.json';

const server = spawn(py, ['-m', 'golmok_tools.viewer_server', data, '--zone', scanZone, '--port', String(port), '--no-browser'],
  { cwd: toolsDir, stdio: ['ignore', 'pipe', 'inherit'] });
await new Promise((res) => server.stdout.on('data', (d) => { if (String(d).includes('viewer:')) res(); }));

const launch = { headless: true };
if (process.env.PLAYWRIGHT_PROXY) launch.proxy = { server: process.env.PLAYWRIGHT_PROXY };
if (process.env.PLAYWRIGHT_CHROMIUM) launch.executablePath = process.env.PLAYWRIGHT_CHROMIUM;
const browser = await chromium.launch(launch);
const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, ignoreHTTPSErrors: true })).newPage();
const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', (e) => errors.push(String(e)));

let ok = false;
try {
  await page.goto(`http://127.0.0.1:${port}/?tileset=/data/tileset_buildings.json&tileset=/data/tileset_terrain.json${zoneParam}`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.golmok && window.golmok.ready, null, { timeout: 120000 });
  // Software GL in CI can take a while to process textures: poll until every layer has tiles.
  await page.waitForFunction(() => window.golmok.layers.length > 0 &&
    window.golmok.layers.every((l) => l.tileset.tilesLoaded && l.loadedTiles > 0), null, { timeout: 120000 }).catch(() => {});
  await page.waitForTimeout(500);
  const stats = await page.evaluate(() => window.golmok.stats());
  const zones = await page.evaluate(() => window.golmok.zoneStats());
  console.log('zones:', JSON.stringify(zones));

  // Placement of the GLB meshes (axis conversion glTF Y-up -> zone-local -> ECEF): the model's world bounding
  // sphere centre must be the centre of the zone-local box the Python side wrote (manifest / blockers.json).
  const placement = await page.evaluate(async () => {
    const g = window.golmok, ZM = window.GolmokZoneMath;
    const z = g.zones.find((q) => q.manifest.zone_id === 'z_synthetic_scan_001');
    const mat = Cesium.Matrix4.fromRowMajorArray(z.manifest.transform);
    const centre = (box) => [0, 1, 2].map((i) => (box[0][i] + box[1][i]) / 2);
    const dist = (model, enu) => Cesium.Cartesian3.distance(model.boundingSphere.center,
      Cesium.Matrix4.multiplyByPoint(mat, new Cesium.Cartesian3(...enu), new Cesium.Cartesian3()));
    const colBox = ZM.unionBoxes(z.manifest.layers.collision.chunks.map((c) => c.bbox_enu));
    const bj = await (await fetch(ZM.resolveZoneUri(z.url, z.manifest.layers.blockers.uri))).json();
    const corners = bj.planes.flatMap((p) => ZM.blockerCorners(p));
    const blBox = [[0, 1, 2].map((i) => Math.min(...corners.map((c) => c[i]))), [0, 1, 2].map((i) => Math.max(...corners.map((c) => c[i])))];
    // what Cesium's default glTF axis correction (Y_UP_TO_Z_UP * Z_UP_TO_X_UP) would have done: east -> north
    const c = centre(colBox);
    return { collision: dist(z.models.collision.model, c), blockers: dist(z.models.blockers.model, centre(blBox)),
             collisionIfCesiumDefault: dist(z.models.collision.model, [-c[1], c[0], c[2]]) };
  });
  console.log('placement (m):', JSON.stringify(placement));
  const placementOk = placement.collision < 0.05 && placement.blockers < 0.05 && placement.collisionIfCesiumDefault > 1;

  // Toggles: overlay checkboxes (all zones) and the per-zone row checkbox.
  const vis = () => page.evaluate(() => window.golmok.zoneStats().map((z) => ({ shown: z.shown, groups: z.groups,
    models: Object.fromEntries(Object.entries(z.models).map(([k, m]) => [k, m.show])) })));
  const allModels = (v, kind, want) => v.every((z) => z.models[kind] === want);
  const toggles = [];
  await page.click('#ov_collision');
  let v = await vis();
  toggles.push(['collision off', allModels(v, 'collision', false) && allModels(v, 'blockers', true)]);
  await page.click('#ov_blockers');
  v = await vis();
  toggles.push(['blockers off', allModels(v, 'blockers', false) && v.every((z) => z.groups.blockers === false)]);
  for (const k of ['footprint', 'axes', 'chunks', 'portals']) {
    await page.click('#ov_' + k);
    v = await vis();
    toggles.push([k + ' off', v.every((z) => z.groups[k] === false)]);
  }
  for (const k of ['collision', 'blockers', 'footprint', 'axes', 'chunks', 'portals']) await page.click('#ov_' + k);
  v = await vis();
  toggles.push(['all on', v.every((z) => Object.values(z.groups).every(Boolean) && Object.values(z.models).every(Boolean))]);
  await page.evaluate(() => { const cb = document.querySelector('#layers .layer:last-child input[type=checkbox]'); cb.click(); });
  v = await vis();
  toggles.push(['last zone row off', v[v.length - 1].shown === false && Object.values(v[v.length - 1].models).every((s) => !s) &&
    Object.values(v[0].models).every(Boolean)]);
  await page.evaluate(() => { const cb = document.querySelector('#layers .layer:last-child input[type=checkbox]'); cb.click(); });
  await page.click('#wire');
  const wire = await page.evaluate(() => window.golmok.zones.every((z) => Object.values(z.models).every((m) => m.model.debugWireframe)));
  await page.click('#wire');
  const wireOff = await page.evaluate(() => window.golmok.zones.every((z) => Object.values(z.models).every((m) => !m.model.debugWireframe)));
  toggles.push(['wireframe', wire && wireOff]);
  console.log('toggles:', JSON.stringify(toggles));
  const togglesOk = toggles.every((t) => t[1]);

  // fly to the scanned zone so the screenshot shows the overlay and meshes
  await page.evaluate(() => window.golmok.viewer.flyTo(window.golmok.zones[1].dataSource, { duration: 0 }));
  await page.waitForTimeout(1500);
  const appErrors = await page.evaluate(() => window.golmok.errors);
  const appWarnings = await page.evaluate(() => window.golmok.warnings);
  mkdirSync(dirname(shot), { recursive: true });
  await page.screenshot({ path: shot });
  console.log('layers:', JSON.stringify(stats));
  const loaded = stats.reduce((n, s) => n + s.loadedTiles, 0);
  const fatal = errors.filter((e) => !/favicon/i.test(e));
  if (appErrors.length) console.error('app errors:', appErrors);
  if (appWarnings.length) console.error('app warnings:', appWarnings);
  if (fatal.length) console.error('console errors:', fatal);
  const modelsOk = zones.length === 2 && zones.every((z) => z.entities >= 10 &&
    ['collision', 'blockers'].every((k) => z.models[k] && z.models[k].ready && z.models[k].bytes > 0));
  const checks = { tiles: stats.length === 2 && loaded > 0, models: modelsOk, placement: placementOk, toggles: togglesOk,
                   appErrors: appErrors.length === 0, appWarnings: appWarnings.length === 0, console: fatal.length === 0 };
  ok = Object.values(checks).every(Boolean);
  console.log(ok ? `OK: ${loaded} tiles loaded, ${zones.length} zones with collision/blockers meshes, screenshot ${shot}`
    : 'FAIL ' + JSON.stringify(checks));
} finally {
  await browser.close();
  server.kill();
}
process.exit(ok ? 0 : 1);
