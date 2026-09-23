#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const dist = resolve(process.env.EVIDAXIS_DIST ?? fileURLToPath(new URL('../dist/', import.meta.url)));
const baseline = JSON.parse(readFileSync(new URL('./dated-badge-hashes.json', import.meta.url), 'utf8'));
const fail = [];
const check = (condition, message) => { if (!condition) fail.push(message); };
const sitemap = readdirSync(dist).filter(file => /^sitemap.*\.xml$/.test(file))
  .map(file => readFileSync(join(dist, file), 'utf8')).join('');
const archive = fileURLToPath(new URL('../../data/snapshots/', import.meta.url));
const ids = [...new Set(readdirSync(archive).filter(name => /^\d{4}-\d{2}-\d{2}$/.test(name))
  .flatMap(date => JSON.parse(readFileSync(join(archive, date, 'snapshot.json'), 'utf8')).entities.map(entity => entity.entity_id)))].sort();
check(new Set(Object.keys(baseline).map(path => path.split('/')[1])).size === Object.keys(baseline).length, 'dated badge fixture contains duplicate entities');
for (const [path, hash] of Object.entries(baseline)) {
  const file = join(dist, path);
  check(existsSync(file), `${path}: dated badge missing`);
  if (existsSync(file)) check(createHash('sha256').update(readFileSync(file)).digest('hex') === hash, `${path}: dated badge changed`);
}
for (const id of ids) {
  const dir = join(dist, 'badge', id);
  const htmlPath = join(dir, 'index.html');
  check(existsSync(htmlPath), `${id}: builder page missing`);
  if (!existsSync(htmlPath)) continue;
  const html = readFileSync(htmlPath, 'utf8');
  check(/<meta name="robots" content="noindex, follow"/.test(html), `${id}: builder is indexable`);
  check(!sitemap.includes(`/badge/${id}/`), `${id}: builder is in sitemap`);
  check(!html.includes('\u2014'), `${id}: builder has em dash`);
  for (const match of html.matchAll(/(?<![-\w])(?:min-)?width\s*:\s*(\d+)px/g)) check(+match[1] <= 390, `${id}: fixed width exceeds 390px`);
  for (const key of ['citations', 'dependents']) for (const suffix of ['', '-flat-square', '-for-the-badge']) {
    check(existsSync(join(dir, `${key}${suffix}.svg`)), `${id}: ${key}${suffix}.svg missing`);
  }
  const rising = html.includes('data-badge="rising"');
  for (const suffix of ['', '-flat-square', '-for-the-badge'])
    check(existsSync(join(dir, `rising${suffix}.svg`)) === rising, `${id}: rising${suffix}.svg availability differs from builder`);
  check(existsSync(join(dir, 'rising-card.svg')) === rising, `${id}: rising card availability differs from builder`);
  check(existsSync(join(dir, 'rising.json')) === rising, `${id}: rising endpoint availability differs from builder`);
  for (const key of ['citations', 'dependents', ...(rising ? ['rising'] : [])]) {
    const path = join(dir, `${key}.json`);
    check(existsSync(path), `${id}: ${key}.json missing`);
    if (!existsSync(path)) continue;
    const endpoint = JSON.parse(readFileSync(path, 'utf8'));
    check(JSON.stringify(Object.keys(endpoint)) === JSON.stringify(['schemaVersion', 'label', 'message', 'color', 'labelColor', 'logoSvg', 'cacheSeconds']), `${id}: ${key} endpoint fields differ`);
    check(endpoint.schemaVersion === 1 && endpoint.label === key && endpoint.labelColor === '555' && endpoint.cacheSeconds === 21600 && /^([0-9a-f]{6})$/.test(endpoint.color) && endpoint.logoSvg.startsWith('<svg'), `${id}: ${key} endpoint invalid`);
  }
  const twinPath = join(dist, 'e', `${id}.json`);
  if (existsSync(twinPath)) {
    const twin = JSON.parse(readFileSync(twinPath, 'utf8'));
    if (twin.display?.template === 'B') for (const key of ['citations', 'dependents']) {
      const reading = twin.display.tiles.find(tile => tile.key === key)?.value ?? null;
      const expected = reading === null ? 'not measured' : Math.round(reading).toLocaleString('en-US');
      const endpoint = JSON.parse(readFileSync(join(dir, `${key}.json`), 'utf8'));
      check(endpoint.message === expected, `${id}: ${key} badge differs from card B`);
      const svg = readFileSync(join(dir, `${key}.svg`), 'utf8');
      check(svg.includes(expected), `${id}: ${key} SVG differs from card B`);
    }
  }
}

// Python's standard XML parser checks every emitted badge without adding a web dependency.
const parsed = spawnSync('python3', ['-c', 'from pathlib import Path\nimport sys, xml.etree.ElementTree as ET\nfiles=list(Path(sys.argv[1]).glob("badge/e_*/*.svg"))\nfor path in files: ET.parse(path)\nprint(f"{len(files)} SVG files parsed as XML")', dist], { encoding: 'utf8' });
check(parsed.status === 0, `SVG XML parse failed: ${parsed.stderr.trim()}`);
console.log(`Badge dist: ${ids.length} builders, ${Object.keys(baseline).length} dated hashes, ${parsed.stdout.trim()}, ${fail.length} discrepancies`);
for (const message of fail) console.error(message);
if (fail.length) process.exitCode = 1;
