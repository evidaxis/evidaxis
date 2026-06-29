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
import { readFileSync, readdirSync, statSync } from 'node:fs';
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

  // 4. head essentials
  if (!/<title>[^<]+<\/title>/.test(html)) errors.push(`${r}: missing non-empty <title>`);
  const descM = html.match(/<meta\s+name="description"\s+content="([^"]*)"/);
  if (!descM) errors.push(`${r}: missing meta description`);
  else {
    const len = descM[1].length;
    if (len < 40 || len > 170) warns.push(`${r}: meta description length ${len} (aim 50-160)`);
  }
  if (!/<link\s+rel="canonical"/.test(html)) errors.push(`${r}: missing canonical link`);

  // 5. single h1
  const h1 = (html.match(/<h1[\s>]/g) || []).length;
  if (h1 > 1) errors.push(`${r}: ${h1} <h1> elements (expected 1)`);
  if (h1 === 0) warns.push(`${r}: no <h1>`);

  // GEO soft: chart-bearing pages should carry real numeric text
  const svgImg = (html.match(/role="img"/g) || []).length;
  const dataVals = (html.match(/<data value=/g) || []).length;
  if (svgImg > 0 && dataVals === 0) warns.push(`${r}: ${svgImg} role=img charts but 0 <data value> nodes`);
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
