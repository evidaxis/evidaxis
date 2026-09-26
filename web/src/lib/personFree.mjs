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
// User-owned as of 2026-07-10; banned even if a (possibly poisoned) cache says otherwise.
export const FLOOR_HANDLES = ['paul-gauthier', 'gcorso', 'jwohlwend', 'petergriffinjin', 'haotian-liu', 'hexgrad', 'dauparas', 'comfyanonymous', 'geeeekexplorer', 'arneschneuing'];

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
  return [...hits];
}
