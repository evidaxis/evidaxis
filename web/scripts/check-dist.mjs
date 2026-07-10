#!/usr/bin/env node
/**
 * Build-output guardrails for the Evidaxis site. Run after `astro build` against
 * dist/. Encodes the non-negotiable invariants so a regression fails CI loudly
 * instead of shipping. No dependencies; pure Node.
 *
 *   node scripts/check-dist.mjs
 *
 * HARD failures (exit 1):
 *   1. em-dash (U+2014) in any rendered HTML        (anti-AI-slop brand rule)
 *   2. client-injected chart placeholders (data-ev) (GEO: charts must be SSR)
 *   3. a <script type=application/ld+json> that does not parse / lacks @context
 *   4. a page missing <title>, meta description, or canonical
 *   5. more than one <h1> on a page
 * SOFT warnings (reported, exit 0): meta description length, pages with 0 SSR charts.
 */
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const DIST = new URL('../dist/', import.meta.url).pathname;
const htmlFiles = [];
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p);
    else if (name.endsWith('.html')) htmlFiles.push(p);
  }
})(DIST);

const errors = [];
const warns = [];
const rel = (p) => p.replace(DIST, '');

for (const file of htmlFiles) {
  const html = readFileSync(file, 'utf8');
  const r = rel(file);

  // 1. em-dash
  const emdash = (html.match(/—/g) || []).length;
  if (emdash > 0) errors.push(`${r}: ${emdash} em-dash (U+2014) in rendered HTML`);

  // 2. client-injected chart placeholders
  const dataEv = (html.match(/data-ev=/g) || []).length;
  if (dataEv > 0) errors.push(`${r}: ${dataEv} data-ev placeholder(s) — charts must be server-rendered`);

  // 3. JSON-LD validity
  const ld = [...html.matchAll(/<script[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g)];
  for (const [, body] of ld) {
    try {
      const obj = JSON.parse(body);
      const blocks = Array.isArray(obj) ? obj : [obj];
      for (const b of blocks) {
        if (!b['@context'] && !b['@graph']) errors.push(`${r}: ld+json block missing @context`);
        if (!b['@type'] && !b['@graph']) errors.push(`${r}: ld+json block missing @type`);
      }
    } catch (e) {
      errors.push(`${r}: ld+json does not parse (${e.message})`);
    }
  }

  // 3b. person-free invariant on the GEO surface: no Person node and no byline/author
  // person field may appear in any rendered structured data (systems, never people).
  if (/"@type"\s*:\s*"Person"/.test(html)) errors.push(`${r}: JSON-LD contains a Person node (person-free invariant)`);
  if (/"(author|founder)"\s*:\s*\{[^}]*"@type"\s*:\s*"Person"/.test(html)) errors.push(`${r}: author/founder Person field (person-free invariant)`);

  // 4. head essentials
  if (!/<title>[^<]+<\/title>/.test(html)) errors.push(`${r}: missing non-empty <title>`);
  const descM = html.match(/<meta\s+name="description"\s+content="([^"]*)"/);
  if (!descM) errors.push(`${r}: missing meta description`);
  else {
    const len = descM[1].length;
    if (len < 40 || len > 170) warns.push(`${r}: meta description length ${len} (aim 50-160)`);
  }
  if (!/<link\s+rel="canonical"/.test(html)) errors.push(`${r}: missing canonical link`);

  // 4b. every entity page must carry a durable claim-URN (cite-as signpost + JSON-LD)
  if (/^e\/e_[^/]+\/index\.html$/.test(r)) {
    if (!/<link\s+rel="cite-as"\s+href="urn:evidaxis:claim:/.test(html))
      errors.push(`${r}: entity page missing rel="cite-as" claim-URN link`);
    if (!/urn:evidaxis:claim:/.test(html.match(/type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/)?.[1] ?? ''))
      warns.push(`${r}: claim-URN not found in first JSON-LD block`);
  }

  // 4c. reconstructed (backfill) data must ALWAYS carry the "reconstructed / not
  // point-in-time capture" honesty label. Presenting it as captured would break the moat.
  if (/data-backfill=/.test(html)) {
    if (!/reconstructed/i.test(html) || !/not a point-in-time capture/i.test(html))
      errors.push(`${r}: backfill/reconstructed data shown without the "reconstructed, not point-in-time" label`);
  }

  // 5. single h1
  const h1 = (html.match(/<h1[\s>]/g) || []).length;
  if (h1 > 1) errors.push(`${r}: ${h1} <h1> elements (expected 1)`);
  if (h1 === 0) warns.push(`${r}: no <h1>`);

  // 5b. heading order: no skipped levels (h2 -> h4 without an h3)
  const levels = [...html.matchAll(/<h([1-6])[\s>]/g)].map((m) => Number(m[1]));
  let prev = 0;
  for (const lvl of levels) {
    if (prev !== 0 && lvl > prev + 1) {
      errors.push(`${r}: heading level skip h${prev} -> h${lvl} (no intermediate h${prev + 1})`);
      break;
    }
    prev = lvl;
  }

  // GEO soft: chart-bearing pages should carry real numeric text
  const svgImg = (html.match(/role="img"/g) || []).length;
  const dataVals = (html.match(/<data value=/g) || []).length;
  if (svgImg > 0 && dataVals === 0) warns.push(`${r}: ${svgImg} role=img charts but 0 <data value> nodes`);
}

// 6. Archive permanence: every published snapshot and every entity ever present
// must retain both its human and machine-readable static routes.
const SNAPSHOTS = new URL('../../data/snapshots/', import.meta.url).pathname;
const archiveSnapshots = readdirSync(SNAPSHOTS, { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
  .map((entry) => ({
    date: entry.name,
    snapshot: JSON.parse(readFileSync(join(SNAPSHOTS, entry.name, 'snapshot.json'), 'utf8')),
  }))
  .sort((a, b) => a.date.localeCompare(b.date));
const latestDate = JSON.parse(readFileSync(new URL('../../data/latest.json', import.meta.url), 'utf8')).snapshot_date;
const latestSnapshot = archiveSnapshots.find((entry) => entry.date === latestDate)?.snapshot;
if (!latestSnapshot) errors.push(`data/latest.json points to missing snapshot ${latestDate}`);

for (const { date } of archiveSnapshots) {
  if (!existsSync(join(DIST, 'snapshots', date, 'index.html'))) errors.push(`snapshots/${date}/index.html: missing frozen snapshot route`);
  if (!existsSync(join(DIST, 'snapshots', date, 'snapshot.json'))) errors.push(`snapshots/${date}/snapshot.json: missing frozen snapshot JSON twin`);
}
if (!existsSync(join(DIST, 'snapshots', 'index.html'))) errors.push('snapshots/index.html: missing snapshot archive index');
if (!existsSync(join(DIST, 'snapshots', '2026-06-27', 'index.html'))) errors.push('snapshots/2026-06-27/index.html: missing genesis route');

const lastSeen = new Map();
for (const { date, snapshot } of archiveSnapshots) {
  for (const entity of snapshot.entities) lastSeen.set(entity.entity_id, date);
}
for (const [id, date] of lastSeen) {
  const htmlPath = join(DIST, 'e', id, 'index.html');
  const jsonPath = join(DIST, 'e', `${id}.json`);
  if (!existsSync(htmlPath)) errors.push(`e/${id}/index.html: missing permanent entity route`);
  if (!existsSync(jsonPath)) errors.push(`e/${id}.json: missing permanent entity JSON twin`);
  if (date !== latestDate && existsSync(htmlPath) && !/superseded/i.test(readFileSync(htmlPath, 'utf8'))) {
    errors.push(`e/${id}/index.html: superseded entity page lacks superseded status`);
  }
}

console.log(`checked ${htmlFiles.length} HTML pages`);
if (warns.length) {
  console.log(`\n${warns.length} warning(s):`);
  for (const w of warns) console.log(`  ⚠ ${w}`);
}
if (errors.length) {
  console.error(`\n${errors.length} HARD failure(s):`);
  for (const e of errors) console.error(`  ✗ ${e}`);
  console.error('\ncheck-dist: FAIL');
  process.exit(1);
}
console.log('\ncheck-dist: PASS — all invariants hold');
