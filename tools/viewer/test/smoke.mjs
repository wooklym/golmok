// Headless smoke test: serve a basemap folder with golmok-viewer, open the page, wait for tiles,
// take a screenshot, fail on console errors or zero loaded tiles.
//
//   GOLMOK_DATA=<basemap out folder> node test/smoke.mjs
//   (defaults to a tiny synthetic basemap built with tools/tests helpers if GOLMOK_DATA is unset)
//
// Env: GOLMOK_PORT (default 8777), GOLMOK_SHOT (screenshot path), PLAYWRIGHT_PROXY (e.g. http://host:port)
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
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
const server = spawn(py, ['-m', 'golmok_tools.viewer_server', data, '--port', String(port), '--no-browser'],
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
  await page.goto(`http://127.0.0.1:${port}/?tileset=/data/tileset_buildings.json&tileset=/data/tileset_terrain.json`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.golmok && window.golmok.ready, null, { timeout: 120000 });
  // Software GL in CI can take a while to process textures: poll until every layer has tiles.
  await page.waitForFunction(() => window.golmok.layers.length > 0 &&
    window.golmok.layers.every((l) => l.tileset.tilesLoaded && l.loadedTiles > 0), null, { timeout: 120000 }).catch(() => {});
  await page.waitForTimeout(500);
  const stats = await page.evaluate(() => window.golmok.stats());
  const appErrors = await page.evaluate(() => window.golmok.errors);
  mkdirSync(dirname(shot), { recursive: true });
  await page.screenshot({ path: shot });
  console.log('layers:', JSON.stringify(stats));
  const loaded = stats.reduce((n, s) => n + s.loadedTiles, 0);
  const fatal = errors.filter((e) => !/favicon/i.test(e));
  if (appErrors.length) console.error('app errors:', appErrors);
  if (fatal.length) console.error('console errors:', fatal);
  ok = stats.length === 2 && loaded > 0 && appErrors.length === 0 && fatal.length === 0;
  console.log(ok ? `OK: ${loaded} tiles loaded, screenshot ${shot}` : 'FAIL');
} finally {
  await browser.close();
  server.kill();
}
process.exit(ok ? 0 : 1);
