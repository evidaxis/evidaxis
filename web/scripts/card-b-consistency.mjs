#!/usr/bin/env node
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseHTML, elements, cardArticle, hasClass, plainText } from './card-b-html.mjs';

const dist = resolve(process.env.EVIDAXIS_DIST ?? fileURLToPath(new URL('../dist/', import.meta.url)));
const failures = [];
const fail = (id, message) => failures.push(`${id}: ${message}`);
function csvRows(body) {
  const rows = []; let row = [], field = '', quoted = false;
  for (let i = 0; i < body.length; i++) {
    const c = body[i];
    if (c === '"' && quoted && body[i + 1] === '"') { field += '"'; i++; }
    else if (c === '"') quoted = !quoted;
    else if (c === ',' && !quoted) { row.push(field); field = ''; }
    else if ((c === '\n' || c === '\r') && !quoted) {
      if (c === '\r' && body[i + 1] === '\n') i++;
      row.push(field); if (row.some(Boolean)) rows.push(row); row = []; field = '';
    } else field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  const [head, ...data] = rows;
  if (!head?.length || !head.includes('metric') && !head.includes('snapshot_date') || !data.length) return [];
  return data.map(values => Object.fromEntries(head.map((key, i) => [key, values[i] ?? ''])));
}
const relativeAsset = path => {
  const clean = decodeURIComponent(path.split(/[?#]/)[0]).replace(/^\//, '');
  return join(dist, clean.endsWith('/') ? `${clean}index.html` : clean);
};
let checked = 0;
for (const entry of readdirSync(join(dist, 'e'), { withFileTypes: true })) {
  if (!entry.isDirectory() || !entry.name.startsWith('e_')) continue;
  const id = entry.name, htmlPath = join(dist, 'e', id, 'index.html');
  const article = cardArticle(parseHTML(readFileSync(htmlPath, 'utf8')));
  if (!article) continue;
  checked++;
  const release = article.attrs['data-release'];
  const twin = JSON.parse(readFileSync(join(dist, 'e', `${id}.json`), 'utf8'));
  if (release !== twin.display?.release_id) fail(id, 'HTML and JSON release_id differ');
  const csvPath = join(dist, 'e', id, `values-${release}.csv`);
  if (!existsSync(csvPath)) { fail(id, 'current values CSV missing'); continue; }
  const rows = csvRows(readFileSync(csvPath, 'utf8'));
  if (!rows.length) { fail(id, 'current values CSV has no data rows'); continue; }
  if (rows.some(row => row.release_id !== release)) fail(id, 'CSV release_id differs');
  const tiles = elements(article, node => hasClass(node, 'card-b-tile'));
  const labels = { commits: 'commits/wk', citations: 'citations', dependents: 'direct dependents', stars: 'stars' };
  for (const [key, label] of Object.entries(labels)) {
    const expected = twin.display?.tiles?.find(tile => tile.key === key);
    const tile = tiles.find(node => elements(node, child => hasClass(child, 'card-b-tile-label')).some(child => plainText(child).trim() === label));
    if (!tile) { fail(id, `${key} tile missing`); continue; }
    const tileValue = elements(tile, node => node.tag === 'strong')[0];
    const datum = elements(tileValue, node => node.tag === 'data' && 'value' in node.attrs)[0];
    const htmlValue = datum ? Number(datum.attrs.value) : null;
    const csv = rows.find(row => row.metric === key);
    const csvValue = csv?.value === '' ? null : Number(csv?.value);
    if (!expected || !csv || htmlValue !== expected.value || csvValue !== expected.value) fail(id, `${key} tile, JSON display and CSV differ`);
  }
  for (const chart of elements(article, node => node.tag === 'img' && /^\/charts\/e\//.test(node.attrs.src ?? ''))) {
    if (!chart.attrs.src.includes(`-${release}.svg`)) fail(id, `chart release differs: ${chart.attrs.src}`);
    if (!existsSync(relativeAsset(chart.attrs.src))) fail(id, `chart missing: ${chart.attrs.src}`);
  }
  const historyPath = join(dist, 'e', id, `history-${release}.csv`);
  const history = existsSync(historyPath) ? csvRows(readFileSync(historyPath, 'utf8')) : [];
  if (!history.length) fail(id, 'current history CSV missing or empty');
  const partitions = new Map();
  for (const row of history) if (row.dependents_partition && row.direct_dependents !== '') partitions.set(row.dependents_partition, row.direct_dependents);
  const series = {
    commits: { metric: 'weekly_commits', row: rows.filter(row => row.metric === 'weekly_commits').at(-1) },
    citations: { metric: 'yearly_citing_works', row: rows.filter(row => row.metric === 'yearly_citing_works').at(-1) },
    dependents: { metric: 'dependents', row: [...partitions].sort(([a], [b]) => a.localeCompare(b)).at(-1) },
  };
  for (const [block, { metric, row }] of Object.entries(series)) {
    const path = join(dist, 'charts', 'e', id, `${block}-${release}.svg`);
    if (!existsSync(path)) {
      if (row) fail(id, `${block} chart missing for CSV series`);
      continue;
    }
    const svg = readFileSync(path, 'utf8');
    const point = svg.match(new RegExp(`data-chart-latest="${metric}" data-value="([^"]+)" data-period="([^"]+)"`));
    const expectedValue = block === 'dependents' ? row?.[1] : row?.value;
    const expectedPeriod = block === 'dependents' ? row?.[0] : row?.period;
    if (!point || !row || Number(point[1]) !== Number(expectedValue) || point[2] !== expectedPeriod) fail(id, `${block} chart latest label differs from CSV`);
  }
  for (const node of elements(article, node => ['a', 'img'].includes(node.tag))) {
    const href = node.attrs.href ?? node.attrs.src ?? '';
    if (!href.startsWith('/')) continue;
    if (!existsSync(relativeAsset(href))) fail(id, `internal target missing: ${href}`);
    if (/\/(?:values|history)-[^/]+\.csv$/.test(href) && href.startsWith(`/e/${id}/`) && !href.includes(`-${release}.csv`)) fail(id, `CSV release differs: ${href}`);
  }
}
console.log(`Card B consistency: ${checked} cards, ${failures.length} discrepancies`);
for (const failure of failures) console.error(failure);
if (failures.length) process.exitCode = 1;
