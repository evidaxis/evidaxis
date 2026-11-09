// Person-free matching of GitHub user handles (constitution invariant 1: systems, not people).
//
// A GitHub login is letters, digits and hyphens, up to 39 characters, case-insensitive.
// A handle counts as published when it appears
//   (a) as a path or slug prefix "handle/" (repository full names, github.com URLs),
//   (b) as an @mention, or
//   (c) as a standalone word, when the handle is distinctive: 4+ characters, not only digits.
// Plain substring matching was sound at 60 user owners; at 2,319 (registry of 2026-09-26)
// handles such as "f", "av", "78" or "100" matched ordinary words and numbers in every card,
// so the guard failed every build without finding a single real handle.
// Keep known personal owners banned after a transfer or cache change. The HF
// exporter reads the same data; removal requires a deliberate, reviewed record.
import { readFileSync, readdirSync } from 'node:fs';
import { createHash, randomBytes } from 'node:crypto';
import { join } from 'node:path';
import { REPO_ROOT } from './path-policy.mjs';
import floorHandles from '../data/person-free-handles.json' with { type: 'json' };
export const FLOOR_HANDLES = Object.freeze(floorHandles);

let vocabulary;
export function templateWords() {
  if (!vocabulary) {
    vocabulary = new Set();
    const walk = dir => {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const path = join(dir, entry.name);
        if (entry.isDirectory()) walk(path);
        else if (/\.(astro|ts)$/.test(entry.name) && !entry.name.includes('.test.')) {
          for (const token of readFileSync(path, 'utf8').toLowerCase().match(/[a-z0-9]+(?:-[a-z0-9]+)*/g) ?? []) vocabulary.add(token);
        }
      }
    };
    // Template source only: never derive ordinary words from the owner registry.
    // REPO_ROOT is stable for source modules and Astro's dist/chunks modules.
    walk(join(REPO_ROOT, 'web/src'));
  }
  return vocabulary;
}

export function buildHandleIndex(handles, templateVocabulary = templateWords()) {
  const all = new Set();
  const words = new Set();
  const contextOnly = new Set();
  for (const handle of handles) {
    const key = String(handle || '').trim().toLowerCase();
    if (!key) continue;
    all.add(key);
    // Rule f exempts distinctive template words, not exact short field values.
    if (key.length >= 4 && !/^\d+$/.test(key)) {
      (templateVocabulary.has(key) ? contextOnly : words).add(key);
    }
  }
  return { all, words, contextOnly, maxWordLength: Math.max(0, ...[...words].map(word => word.length)) };
}

const SLUG = /(?<![a-z0-9_.-])([a-z0-9][a-z0-9-]{0,38})(?=\/)/g;
const MENTION = /(?<![a-z0-9_.-])@([a-z0-9][a-z0-9-]{0,38})(?![a-z0-9-])/g;
const WORD = /[a-z0-9]+(?:-+[a-z0-9]+)*/g;

// Short (under 4 characters) or all-digit handles collide with the site's own paths
// ("/e/", "/ai/", "/page/12/"); they count only in an explicit GitHub context.
const GITHUB_CONTEXT = /(?:github\.com\/|repos\/)$/;
// Explicit GitHub contexts count ANY handle, whatever its length (review 2026-10-04):
// a profile URL without a trailing slash, a Pages host, a raw-content path.
const GH_PROFILE = /github\.com\/([a-z0-9][a-z0-9-]{0,38})(?![a-z0-9-])/g;
const GH_PAGES = /(?<![a-z0-9-])([a-z0-9][a-z0-9-]{0,38})\.github\.io(?![a-z0-9-])/g;
const GH_RAW = /githubusercontent\.com\/([a-z0-9][a-z0-9-]{0,38})\//g;

// Percent-decode until stable (at most 3 rounds); malformed sequences stay as is.
export function lenientDecoded(text) {
  let out = String(text);
  for (let i = 0; i < 3; i += 1) {
    const next = out.replace(/(?:%[0-9a-fA-F]{2})+/g, (seq) => {
      try { return decodeURIComponent(seq); } catch { return seq; }
    });
    if (next === out) break;
    out = next;
  }
  return out;
}

export function decimalEntitiesDecoded(text) {
  return text.replace(/&#(\d+);/g, (_, d) => String.fromCharCode(Number(d)));
}

export function handleHits(text, index) {
  const lower = String(text).toLowerCase();
  const hits = new Set();
  for (const m of lower.matchAll(SLUG)) {
    const handle = m[1];
    if (!index.all.has(handle)) continue;
    if (index.words.has(handle) || GITHUB_CONTEXT.test(lower.slice(Math.max(0, m.index - 11), m.index))) hits.add(handle);
  }
  for (const m of lower.matchAll(MENTION)) if (index.all.has(m[1])) hits.add(m[1]);
  // Rule g: hyphens delimit tokens but may also belong to a login.
  for (const m of lower.matchAll(WORD)) {
    const parts = m[0].split('-');
    for (let start = 0; start < parts.length; start++) {
      let token = '';
      for (let end = start; end < parts.length; end++) {
        token += (end === start ? '' : '-') + parts[end];
        if (token.length > index.maxWordLength) break;
        if (index.words.has(token)) hits.add(token);
      }
    }
  }
  for (const re of [GH_PROFILE, GH_PAGES, GH_RAW]) for (const m of lower.matchAll(re)) if (index.all.has(m[1])) hits.add(m[1]);
  return [...hits];
}

// Raw text plus its percent-decoded form (github.com%2Fhandle%2Frepo cannot hide a handle).
export function handleHitsDecoded(text, index) {
  return [...new Set([...handleHits(text, index), ...handleHits(lenientDecoded(text), index)])];
}

// A canonical Organization path may contain an old slug. Exempt only the occurrence
// at its exact offset, so a separate stale path (including after a JSON escape) fails.
export function staleSlugHits(text, staleSlugs, canonicalPaths) {
  const paths = [...canonicalPaths];
  const hits = new Set();
  for (const slug of staleSlugs) {
    let position = text.indexOf(slug);
    if (position < 0) continue;
    const exemptions = [];
    for (const path of paths) {
      for (let offset = path.indexOf(slug); offset >= 0; offset = path.indexOf(slug, offset + 1)) {
        exemptions.push({ path, offset });
      }
    }
    for (; position >= 0; position = text.indexOf(slug, position + 1)) {
      const exempt = exemptions.some(({ path, offset }) =>
        position >= offset && text.startsWith(path, position - offset));
      if (!exempt) {
        hits.add(slug);
        break;
      }
    }
  }
  return [...hits];
}

// Rules a-e. The same pure classifier is exercised by the Python/JS vectors.
export function classifyRegistry(registry, accounts = {}, floor = []) {
  const entries = Object.entries(registry ?? {}).filter(([, entry]) => entry && typeof entry.full_name === 'string');
  const organizations = new Set(Object.keys(accounts).map(owner => owner.toLowerCase()));
  for (const [, entry] of entries) if (entry.owner_type === 'Organization') organizations.add(entry.full_name.split('/')[0].toLowerCase());
  const handles = new Set(floor.filter(Boolean).map(owner => String(owner).trim().toLowerCase()));
  for (const [stored, entry] of entries) {
    const current = entry.full_name.split('/')[0].toLowerCase();
    const former = stored.split('/')[0].toLowerCase();
    if (entry.owner_type === 'User') handles.add(current);
    if (former !== current) handles.add(former);
  }
  for (const owner of organizations) handles.delete(owner);
  const stalePaths = new Set(), personalPaths = new Set(), canonicalPaths = new Set(), publicRepos = new Set();
  for (const [stored, entry] of entries) {
    const path = entry.full_name.toLowerCase();
    const current = path.split('/')[0], former = stored.split('/')[0].toLowerCase();
    if (organizations.has(current)) { publicRepos.add(stored); canonicalPaths.add(path); }
    if (handles.has(current)) { personalPaths.add(path); personalPaths.add(stored.toLowerCase()); }
    if (former !== current && (handles.has(former) || handles.has(current))) {
      stalePaths.add(stored.toLowerCase()); personalPaths.add(stored.toLowerCase());
    }
  }
  return { handles, organizations, stalePaths, personalPaths, canonicalPaths, publicRepos };
}

export const personalOwnerHandles = registry => [...classifyRegistry(registry).handles];
export const personalStalePaths = registry => [...classifyRegistry(registry).stalePaths];

export function validOwnerEntry(entry) {
  return !!entry && ['Organization', 'User'].includes(entry.owner_type)
    && Number.isInteger(entry.repo_id) && entry.repo_id > 0
    && typeof entry.full_name === 'string' && /^[^/]+\/[^/]+$/.test(entry.full_name);
}

export function revealsHandleText(text, index) {
  if (!text) return false;
  const exact = lenientDecoded(text).trim().toLowerCase();
  return (index.all.has(exact) && !index.contextOnly?.has(exact)) || handleHitsDecoded(text, index).length > 0;
}

const diagnosticSalt = randomBytes(32);
export function privacyDiagnostic(path, rule, value, index, classified) {
  const digest = text => createHash('sha256').update(diagnosticSalt).update('\0').update(text.toLowerCase()).digest('hex').slice(0, 8);
  const privatePath = (index && revealsHandleText(path, index))
    || (classified && staleSlugHits(lenientDecoded(path).toLowerCase(), classified.stalePaths, classified.canonicalPaths).length > 0)
    || (rule === 'd' && lenientDecoded(path).toLowerCase().includes(value.toLowerCase()));
  const safePath = privatePath ? `[path:${digest(path)}]` : path;
  return `${safePath}: rule=${rule} hash=${digest(value)}`;
}

// A listed User account that is a project's identity is published like an Organization.
// The owner-types file stays unchanged; callers pass the accounts map (missing file = {}).
export function applyProjectAccounts(registry, accounts) {
  if (!registry || typeof registry !== 'object' || Array.isArray(registry)) return registry;
  if (!accounts || typeof accounts !== 'object' || Array.isArray(accounts)) return registry;
  for (const [key, entry] of Object.entries(registry)) {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry) || entry.owner_type !== 'User') continue;
    const fullName = entry.full_name;
    if (typeof fullName !== 'string' || !fullName.includes('/')) continue;
    const owner = fullName.split('/')[0].toLowerCase();
    if (!owner || !Object.prototype.hasOwnProperty.call(accounts, owner)) continue;
    registry[key] = {
      ...entry,
      owner_type: 'Organization',
      github_owner_type: 'User',
      publication_basis: 'project_account',
    };
  }
  return registry;
}
