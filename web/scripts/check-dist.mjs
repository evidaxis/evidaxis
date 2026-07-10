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
import { relative } from 'node:path';
import { join } from 'node:path';

const DIST = new URL('../dist/', import.meta.url).pathname;
const htmlFiles = [];
const distFiles = [];
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p);
    else if (st.isFile()) {
      distFiles.push(p);
      if (name.endsWith('.html')) htmlFiles.push(p);
    }
  }
})(DIST);

const errors = [];
const warns = [];
const rel = (p) => p.replace(DIST, '');

// 0. Person-free repository publication is fail-closed. The internal id-map key
// remains stable, while public output uses the canonical repository identity.
const ID_MAP = JSON.parse(readFileSync(new URL('../../etl/id_map.json', import.meta.url), 'utf8'));
const OWNER_TYPES = JSON.parse(readFileSync(new URL('../../etl/owner_types.json', import.meta.url), 'utf8'));
const registry = OWNER_TYPES?.repos;
if (OWNER_TYPES?.schema_version !== 'owner_types_1'
  || JSON.stringify(Object.keys(OWNER_TYPES).sort()) !== JSON.stringify(['repos', 'schema_version'])
  || !registry || Array.isArray(registry) || typeof registry !== 'object') {
  errors.push('etl/owner_types.json: expected owner_types_1 repository registry');
} else {
  const internalRepos = Object.keys(ID_MAP).sort();
  const classifiedRepos = Object.keys(registry).sort();
  if (JSON.stringify(internalRepos) !== JSON.stringify(classifiedRepos)) {
    errors.push('etl/owner_types.json: repository coverage must exactly match etl/id_map.json');
  }

  const bannedOwners = new Map();
  // Cache-flip defense floor (review 2026-07-10): these handles are User-owned as of
  // 2026-07-10 and stay banned even if a (possibly poisoned) cache says otherwise.
  // Remove an entry ONLY via a deliberate, reviewed commit.
  for (const h of ['paul-gauthier', 'gcorso', 'jwohlwend', 'petergriffinjin', 'haotian-liu',
                   'hexgrad', 'dauparas', 'comfyanonymous', 'geeeekexplorer', 'arneschneuing'])
    bannedOwners.set(h, 'substring');
  for (const storedRepo of internalRepos) {
    const entry = registry[storedRepo];
    if (!entry || !['Organization', 'User'].includes(entry.owner_type)
      || !Number.isInteger(entry.repo_id) || entry.repo_id <= 0
      || typeof entry.full_name !== 'string' || !/^[^/]+\/[^/]+$/.test(entry.full_name)
      || JSON.stringify(Object.keys(entry).sort()) !== JSON.stringify(['full_name', 'owner_type', 'repo_id'])) {
      errors.push(`etl/owner_types.json: invalid classification for ${storedRepo}`);
      continue;
    }
    const storedOwner = storedRepo.split('/')[0];
    const canonicalOwner = entry.full_name.split('/')[0];
    if (entry.owner_type === 'User') bannedOwners.set(canonicalOwner.toLowerCase(), 'substring');
    // Moved Organization repositories use slug-context matching. This avoids
    // ordinary-word collisions such as the former owner "block" while still
    // rejecting stale repository paths and serialized slugs.
    if (storedOwner.toLowerCase() !== canonicalOwner.toLowerCase()) {
      bannedOwners.set(storedOwner.toLowerCase(), 'slug');
    }
  }

  for (const file of distFiles) {
    const r = rel(file);
    // WP-H: verification-bundle artifacts are frozen raw pass-through of the
    // archive (hash-pinned provenance / dropped lists). They intentionally
    // retain historical github_repo strings for auditability. Person-free is
    // enforced on derived HTML/JSON-LD surfaces, not on the integrity files.
    if (/(^|\/)(provenance\.json|dropped\.json|SHA256SUMS|manifest\.json)(\/|$)/.test(r)) {
      continue;
    }
    const raw = readFileSync(file, 'utf8');
    // Review 2026-07-10: scan decoded variants too (percent / \uXXXX / HTML-entity)
    // and the file's own relative path - an encoded handle is still a handle.
    const variants = [raw.toLowerCase(), relative(DIST, file).toLowerCase()];
    try { variants.push(decodeURIComponent(raw).toLowerCase()); } catch {}
    variants.push(raw.replace(/\\u([0-9a-fA-F]{4})/g, (_, h) => String.fromCharCode(parseInt(h, 16))).toLowerCase());
    variants.push(raw.replace(/&#(\d+);/g, (_, d) => String.fromCharCode(Number(d)).toLowerCase()));
    const body = variants.join('\n');
    for (const [owner, mode] of bannedOwners) {
      const needle = mode === 'slug' ? `${owner}/` : owner;
      if (body.includes(needle)) errors.push(`${r}: contains private or stale repository owner ${owner}`);
    }
  }
}

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
  // WP-H / F8: verification bundle must ship with every built snapshot.
  for (const artifact of ['manifest.json', 'provenance.json', 'SHA256SUMS']) {
    if (!existsSync(join(DIST, 'snapshots', date, artifact))) {
      errors.push(`snapshots/${date}/${artifact}: missing verification-bundle artifact`);
    }
  }
  // dropped.json is optional (genesis has none); if present on disk it must be built.
  const srcDropped = join(SNAPSHOTS, date, 'dropped.json');
  if (existsSync(srcDropped) && !existsSync(join(DIST, 'snapshots', date, 'dropped.json'))) {
    errors.push(`snapshots/${date}/dropped.json: source present but dist missing`);
  }
}
if (!existsSync(join(DIST, 'snapshots', 'index.html'))) errors.push('snapshots/index.html: missing snapshot archive index');
if (!existsSync(join(DIST, 'snapshots', '2026-06-27', 'index.html'))) errors.push('snapshots/2026-06-27/index.html: missing genesis route');

// WP-J / V1: homepage HTML size budget (dist, not gzip). Hard assert.
const HOME_BUDGET = 250 * 1024; // 250 KB
const homePath = join(DIST, 'index.html');
if (existsSync(homePath)) {
  const homeBytes = statSync(homePath).size;
  if (homeBytes > HOME_BUDGET) {
    errors.push(`index.html: homepage dist HTML ${homeBytes} bytes exceeds ${HOME_BUDGET} byte budget (250KB)`);
  }
} else {
  errors.push('index.html: missing homepage');
}

// WP-K: _charttest must never ship in dist or the sitemap (build-only / private).
for (const bad of ['_charttest', 'charttest']) {
  if (existsSync(join(DIST, bad)) || existsSync(join(DIST, bad, 'index.html'))) {
    errors.push(`${bad}/: charttest route must not appear in dist`);
  }
}
const sitemapPath = join(DIST, 'sitemap-0.xml');
if (existsSync(sitemapPath)) {
  const sm = readFileSync(sitemapPath, 'utf8');
  if (/charttest/i.test(sm)) errors.push('sitemap-0.xml: charttest must not be listed');
}

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
