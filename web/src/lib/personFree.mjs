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
import floorHandles from '../data/person-free-handles.json' with { type: 'json' };
export const FLOOR_HANDLES = Object.freeze(floorHandles);

export function buildHandleIndex(handles) {
  const all = new Set();
  const words = new Set();
  for (const handle of handles) {
    const key = String(handle || '').trim().toLowerCase();
    if (!key) continue;
    all.add(key);
    if (key.length >= 4 && !/^\d+$/.test(key)) words.add(key);
  }
  return { all, words };
}

const SLUG = /(?<![a-z0-9_.-])([a-z0-9][a-z0-9-]{0,38})(?=\/)/g;
const MENTION = /(?<![a-z0-9_.-])@([a-z0-9][a-z0-9-]{0,38})(?![a-z0-9-])/g;
const WORD = /(?<![a-z0-9-])[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?![a-z0-9-])/g;

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

export function handleHits(text, index) {
  const lower = String(text).toLowerCase();
  const hits = new Set();
  for (const m of lower.matchAll(SLUG)) {
    const handle = m[1];
    if (!index.all.has(handle)) continue;
    if (index.words.has(handle) || GITHUB_CONTEXT.test(lower.slice(Math.max(0, m.index - 11), m.index))) hits.add(handle);
  }
  for (const m of lower.matchAll(MENTION)) if (index.all.has(m[1])) hits.add(m[1]);
  for (const m of lower.matchAll(WORD)) if (index.words.has(m[0])) hits.add(m[0]);
  for (const re of [GH_PROFILE, GH_PAGES, GH_RAW]) for (const m of lower.matchAll(re)) if (index.all.has(m[1])) hits.add(m[1]);
  return [...hits];
}

// Raw text plus its percent-decoded form (github.com%2Fhandle%2Frepo cannot hide a handle).
export function handleHitsDecoded(text, index) {
  return [...new Set([...handleHits(text, index), ...handleHits(lenientDecoded(text), index)])];
}
