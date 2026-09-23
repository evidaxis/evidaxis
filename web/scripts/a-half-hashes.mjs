#!/usr/bin/env node
import { readFileSync, readdirSync, writeFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join, resolve } from 'node:path';

const dist = resolve(process.env.EVIDAXIS_DIST ?? new URL('../dist/', import.meta.url).pathname);
const output = resolve(process.argv[2] ?? new URL('../.foundation-check/after.sha256', import.meta.url).pathname);
const alphabet = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
const assignment = JSON.parse(readFileSync(new URL('../src/data/canary-assignment.json', import.meta.url), 'utf8'));
const protectedIds = new Set(assignment.pairs.flatMap(p => [p.control, p.treatment]).map(url => new URL(url).pathname.split('/')[2]));
const ids = readdirSync(join(dist, 'e'), { withFileTypes: true }).filter(e => e.isDirectory() && e.name.startsWith('e_'))
  .map(e => e.name).filter(id => protectedIds.has(id) || alphabet.indexOf(id.at(-1)) % 2 !== 0).sort();
if (protectedIds.size !== 48 || [...protectedIds].some(id => !ids.includes(id))) throw new Error('Missing protected experiment page');
const paths = ids.flatMap(id => [`e/${id}/index.html`, `e/${id}.json`]);
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, paths.map(path => `${createHash('sha256').update(readFileSync(join(dist, path))).digest('hex')}  ${path}\n`).join(''));
console.log(`${ids.length} A/protected HTML pages and JSON twins; all 48 experiment URLs included -> ${output}`);
