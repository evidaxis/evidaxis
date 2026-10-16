#!/usr/bin/env node
/** Regenerate one version's control hashes from an explicitly selected build. */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { parseArgs } from 'node:util';
import { controlShellHash, controlShellPatterns } from './canary-shell.mjs';

const { values } = parseArgs({ options: { version: { type: 'string' } } });
const registry = JSON.parse(readFileSync(new URL('../src/lib/methodology-registry.json', import.meta.url), 'utf8'));
if (!registry.versions.some(row => row.version === values.version)) throw new Error('--version must name a registered methodology');
const dist = process.env.EVIDAXIS_DIST ? resolve(process.env.EVIDAXIS_DIST) : new URL('../dist/', import.meta.url).pathname;
const assignment = JSON.parse(readFileSync(new URL('../src/data/canary-assignment.json', import.meta.url), 'utf8'));
const baselinePath = new URL('../src/data/canary-control-baseline.json', import.meta.url);
const baseline = JSON.parse(readFileSync(baselinePath, 'utf8'));
if (baseline.versions[values.version]) throw new Error('Frozen experiment baselines cannot be rewritten');
const known = registry.versions.map(row => row.version);
const controls = {};
const derived = [];
for (const pair of assignment.pairs) {
  const id = new URL(pair.control).pathname.split('/')[2];
  const record = JSON.parse(readFileSync(join(dist, 'e', `${id}.json`), 'utf8'));
  let html = readFileSync(join(dist, 'e', id, 'index.html'), 'utf8');
  const built = record.score_receipt.methodology_version;
  if (built !== values.version) {
    // A control missing from the first snapshot of a new version (declared /stats gap) still
    // renders its last record under the earlier version. Its shell differs only by the version
    // token (verified on 23 of 24 controls at the m3 -> m4 bump, 2026-10-12), so derive it; the
    // next build that carries the control under the new version checks the derived hash.
    if (known.indexOf(built) < 0 || known.indexOf(built) >= known.indexOf(values.version)) {
      throw new Error(`${id}: build uses ${built}, requested ${values.version}`);
    }
    html = html.replace(new RegExp(`\\b${built}\\b`, 'g'), values.version);
    derived.push(`${id} (${built})`);
  }
  if (controlShellPatterns.some(pattern => !pattern.test(html))) throw new Error(`${id}: incomplete control shell`);
  controls[id] = controlShellHash(html);
}
if (derived.length) console.log(`derived from an earlier-version render: ${derived.join(', ')}`);
const additions = new URL('../src/data/methodology-control-baselines/', import.meta.url);
mkdirSync(additions, { recursive: true });
writeFileSync(new URL(`${values.version}.json`, additions), JSON.stringify({ controls }, null, 2) + '\n');
console.log(`canary baseline ${values.version}: ${Object.keys(controls).length} controls from ${dist}`);
