#!/usr/bin/env node
/** Regenerate one version's control hashes from an explicitly selected build. */
import { readFileSync, writeFileSync } from 'node:fs';
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
const controls = {};
for (const pair of assignment.pairs) {
  const id = new URL(pair.control).pathname.split('/')[2];
  const record = JSON.parse(readFileSync(join(dist, 'e', `${id}.json`), 'utf8'));
  if (record.score_receipt.methodology_version !== values.version) {
    throw new Error(`${id}: build uses ${record.score_receipt.methodology_version}, requested ${values.version}`);
  }
  const html = readFileSync(join(dist, 'e', id, 'index.html'), 'utf8');
  if (controlShellPatterns.some(pattern => !pattern.test(html))) throw new Error(`${id}: incomplete control shell`);
  controls[id] = controlShellHash(html);
}
baseline.versions[values.version] = { controls };
writeFileSync(baselinePath, JSON.stringify(baseline, null, 2) + '\n');
console.log(`canary baseline ${values.version}: ${Object.keys(controls).length} controls from ${dist}`);
