#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { fixtureAnonymizer } from './fixture-privacy.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const cutoff = '2026-10-17';
const output = join(root, 'web', 'test-fixtures', cutoff);
const read = path => JSON.parse(readFileSync(join(root, path), 'utf8'));
const dates = readdirSync(join(root, 'data/snapshots')).filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d) && d <= cutoff).sort();
if (!dates.includes(cutoff)) throw new Error(`Missing snapshot ${cutoff}`);
const snapshots = dates.map(d => read(`data/snapshots/${d}/snapshot.json`));
const universe = new Map(snapshots.flatMap(s => s.entities.map(e => [e.entity_id, e])));
const registry = read('etl/owner_types.json');
const pending = read('etl/owner_transitions_pending.json');
const ids = new Set();
const sorted = [...universe.values()].sort((a, b) => a.entity_id.localeCompare(b.entity_id, 'en'));

function* files(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name, 'en'))) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* files(path);
    else yield path;
  }
}
for (const path of files(join(root, 'web/src'))) {
  if ((!path.endsWith('.test.ts') && !path.endsWith('.golden.json')) || path.endsWith('.data.test.ts')) continue;
  for (const [id] of readFileSync(path, 'utf8').matchAll(/\be_[A-Z0-9]{11}\b/g)) {
    if (universe.has(id)) ids.add(id);
  }
}

// Sample each dimension separately, rather than their large Cartesian product.
// Three records per status exercise branches while keeping the archive small.
function sample(rows, key, count = 3) {
  const counts = new Map();
  for (const e of rows) {
    const value = key(e), n = counts.get(value) ?? 0;
    if (n < count) { ids.add(e.entity_id); counts.set(value, n + 1); }
  }
}
sample(sorted, e => e.status);
sample(sorted, e => e.axes.deps_direct_dependents_momentum?.status ?? 'absent');
sample(sorted, e => e.axes.openalex_citation_momentum.status);
sample(sorted, e => registry.repos[e.github_repo]?.owner_type);
sample(sorted, e => e.cohort);
// Cohort median tests need both measured citations and missing/count-only cases.
sample(sorted, e => `${e.cohort}:${e.axes.openalex_citation_momentum.status}`);
sample(sorted, e => e.name.toLowerCase() === e.github_repo.split('/')[0].toLowerCase());
for (const e of sorted) if (Object.hasOwn(pending, e.github_repo)) ids.add(e.entity_id);
for (const date of dates) {
  const path = `data/snapshots/${date}/dropped.json`;
  if (existsSync(join(root, path))) sample(read(path).dropped, e => e.reason);
}
const repos = new Set(sorted.filter(e => ids.has(e.entity_id)).map(e => e.github_repo));
const keep = row => row.entity_id ? ids.has(row.entity_id) : repos.has(row.github_repo);
const byId = value => Object.fromEntries(Object.entries(value ?? {}).filter(([id]) => ids.has(id)));
const byRepo = value => Object.fromEntries(Object.entries(value ?? {}).filter(([repo]) => repos.has(repo)));

// The output directory is exclusively generated. Inspect it before removing stale
// files so regeneration cannot retain entities dropped from the selection.
if (existsSync(output)) {
  const entries = readdirSync(output);
  if (entries.some(name => !['data', 'etl', 'selection.json'].includes(name))) throw new Error('Unexpected fixture contents');
  rmSync(output, { recursive: true });
}
const outputFiles = new Map();
const put = (path, text) => outputFiles.set(path, text);
let bytes = 0, count = 0;
function write(path, text) {
  const target = join(output, path);
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, text);
  bytes += Buffer.byteLength(text); count++;
}
const json = (path, body) => put(path, `${JSON.stringify(body)}\n`);
function jsonl(path) {
  const source = join(root, path);
  if (!existsSync(source)) return;
  let rows = readFileSync(source, 'utf8').split('\n').filter(Boolean).map(line => JSON.parse(line))
    .filter(row => keep(row) && String(row.captured_at ?? row.computed_at ?? '').slice(0, 10) <= cutoff
      && Boolean(row.captured_at ?? row.computed_at));
  if (path.endsWith('deps.jsonl')) {
    // data.ts consumes these fields only; HTTP receipt metadata is never read by
    // the web loaders. Keep all selected captures, including unmatched/retracted.
    const fields = ['entity_id', 'coverage', 'status', 'period', 'captured_at', 'signals'];
    rows = rows.map(row => Object.fromEntries(fields.filter(key => Object.hasOwn(row, key)).map(key => [key, row[key]])));
  }
  if (rows.length) put(path, rows.map(row => JSON.stringify(row)).join('\n') + '\n');
}
for (const snapshot of snapshots) {
  const date = snapshot.snapshot_date, base = `data/snapshots/${date}`;
  const entities = snapshot.entities.filter(keep);
  const counts = { ...snapshot.counts, entities: entities.length };
  for (const status of ['rising', 'watch', 'tracked', 'calibration', 'single-axis']) {
    if (Object.hasOwn(counts, status)) counts[status] = entities.filter(e => e.status === status
      || (status === 'tracked' && !Object.hasOwn(counts, 'single-axis') && e.status === 'single-axis')).length;
  }
  counts.axis2_present = entities.filter(e => e.axes.openalex_citation_momentum.status === 'present').length;
  json(`${base}/snapshot.json`, { ...snapshot, entities, counts });
  json(`${base}/manifest.json`, read(`${base}/manifest.json`));
  const provenance = read(`${base}/provenance.json`);
  const works = new Set(entities.flatMap(e => e.openalex_work_ids));
  json(`${base}/provenance.json`, { ...provenance,
    github_weekly_raw: byId(provenance.github_weekly_raw), openalex_raw: byId(provenance.openalex_raw),
    source_manifest: { ...provenance.source_manifest,
      github_repos: provenance.source_manifest.github_repos.filter(repo => repos.has(repo)),
      openalex_works: provenance.source_manifest.openalex_works.filter(work => works.has(work)),
    },
  });
  if (existsSync(join(root, base, 'dropped.json'))) {
    const dropped = read(`${base}/dropped.json`);
    json(`${base}/dropped.json`, { ...dropped, dropped: dropped.dropped.filter(keep) });
  }
}
json('data/latest.json', { snapshot_date: cutoff });
for (const id of [...ids].sort()) {
  jsonl(`data/history/${id}.jsonl`);
  jsonl(`data/observations/history/${id}.deps.jsonl`);
  jsonl(`data/observations/backfill/${id}.backfill.jsonl`);
}
for (const day of readdirSync(join(root, 'data/observations')).filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d) && d <= cutoff).sort()) {
  // Loaders open daily deps only on snapshot dates; other captures are already
  // retained in per-entity history, which supplies the point-in-time fallback.
  if (dates.includes(day)) jsonl(`data/observations/${day}/deps.jsonl`);
  for (const name of ['seed-departures.json', 'departed.json']) {
    const path = `data/observations/${day}/${name}`;
    if (!existsSync(join(root, path))) continue;
    const body = read(path);
    json(path, Array.isArray(body) ? body.filter(keep) : { ...body,
      ...Object.fromEntries(['departures', 'departed'].filter(key => Array.isArray(body[key])).map(key => [key, body[key].filter(keep)])),
    });
  }
}
const pins = read('data/deps_id_map.json');
json('data/deps_id_map.json', { ...pins, pins: byRepo(pins.pins) });
json('etl/owner_types.json', { ...registry, repos: byRepo(registry.repos) });
json('etl/id_map.json', byRepo(read('etl/id_map.json')));
json('etl/owner_transitions_pending.json', byRepo(pending));
const accounts = read('etl/project_accounts.json');
const owners = new Set([...repos].map(repo => repo.split('/')[0].toLowerCase()));
json('etl/project_accounts.json', { ...accounts, accounts: Object.fromEntries(Object.entries(accounts.accounts)
  .filter(([owner]) => owners.has(owner.toLowerCase()))) });
json('selection.json', { cutoff, entity_ids: [...ids].sort(), snapshots: dates });
// Collect all locators before replacing any bytes, so historical packages and
// registry keys receive the same surrogate wherever they occur.
const documents = [...outputFiles].flatMap(([path, text]) => path.endsWith('.jsonl')
  ? text.trimEnd().split('\n').map(line => JSON.parse(line)) : [JSON.parse(text)]);
const anonymize = fixtureAnonymizer(documents, registry, accounts.accounts, read('web/src/data/person-free-handles.json'));
for (const [path, text] of outputFiles) {
  const rows = path.endsWith('.jsonl') ? text.trimEnd().split('\n').map(line => JSON.parse(line)) : [JSON.parse(text)];
  write(path, rows.map(row => JSON.stringify(anonymize(row))).join('\n') + '\n');
}
for (const date of dates) {
  const base = `data/snapshots/${date}`;
  // Checksums describe the anonymized fixture, not the original archive.
  const sums = readdirSync(join(output, base)).sort().map(name =>
    `${createHash('sha256').update(readFileSync(join(output, base, name))).digest('hex')}  ${name}\n`).join('');
  write(`${base}/SHA256SUMS`, sums);
}
console.log(`${ids.size} entity ids, ${dates.length} snapshots, ${count} files, ${bytes} bytes`);
// Enforce the requested 8 MB ceiling in decimal bytes, including all fixture files.
if (bytes > 8_000_000) throw new Error('Fixture exceeds the 8 MB budget');
