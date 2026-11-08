/**
 * Positive-only discovery-surface lexicon guard.
 *
 * HTML is scanned contextually after tag removal. JSON is parsed first and
 * each string value is scanned on its own, so neighbouring fields cannot form
 * a synthetic context window.
 */
export const ENTITY_LEXICON_WINDOW = 120;

// Inline elements keep a name whole ("verdict <strong>AI</strong>"). Every
// other element, known or not, is a block boundary a name cannot cross.
const INLINE_TAGS = new Set([
  'a', 'abbr', 'b', 'bdi', 'bdo', 'cite', 'code', 'data', 'del', 'dfn', 'em', 'i', 'ins', 'kbd',
  'mark', 'q', 's', 'samp', 'small', 'span', 'strong', 'sub', 'sup', 'time', 'u', 'var', 'wbr',
]);

export const ENTITY_LEXICON_ALLOWLIST = [
  'methodology/',
  'glossary/',
];

export const FORBIDDEN_ENTITY_LEXICON = [
  /\bno signal published\b/i,
  /\bverdict\b/i,
  /\bpath to rising\b/i,
  /\bdecelerat(?:e|es|ed|ing|ion)\b/i,
  /\bnot rising\b/i,
  /\bgate shut\b/i,
  /\bbelow (?:the )?(?:two-axis |convergence )?gate\b/i,
  /\bneeds? to recover\b/i,
  /\bdeclin(?:e|es|ed|ing)\b/i,
  /\bslow(?:s|ed|ing|down)\b/i,
  /\blos(?:e|es|ing) momentum\b/i,
  /\bfall(?:s|ing) behind\b/i,
  /\bwatch\b/i,
  /\btracked\b/i,
  /\bsingle-axis\b/i,
  /\bcalibration\b/i,
];

// Verdict-class terms are forbidden ANYWHERE on a named entity surface (the
// whole page is about that system); context-class terms above are checked in a
// window around the name because they can appear legitimately in shared chrome.
export const FORBIDDEN_ENTITY_PAGE_WIDE = [
  /\bno signal published\b/i,
  /\bverdict\b/i,
  /\bpath to rising\b/i,
  /\bdecelerat(?:e|es|ed|ing|ion)\b/i,
  /\bnot rising\b/i,
  /\bgate shut\b/i,
  /\bneeds? to recover\b/i,
  /\bdeclin(?:e|es|ed|ing)\b/i,
  /\blos(?:e|es|ing) momentum\b/i,
  /\bfall(?:s|ing) behind\b/i,
];

/**
 * Matches of `pattern` that are our language, not the system's own name.
 * A third-party name ("watch-skill", "verdict-ai", "stale-detector") may
 * contain a guarded word; a match lying wholly inside a whole-word occurrence
 * of the name is dropped. A match that reaches past the name ("Momentum is
 * losing momentum") is kept, so the name never hides words we wrote.
 * @param {string} surface
 * @param {RegExp} pattern
 * @param {readonly unknown[]} [identifiers]
 * @param {{ marked: string, mark: string, residue: boolean } | null} [twin] the same surface with HTML block marks
 * @returns {RegExpMatchArray[]}
 */
export function matchesOutsideOwnName(surface, pattern, identifiers = [], twin = null) {
  const spans = ownNameSpans(surface, identifiers, twin);
  const flags = pattern.flags.includes('g') ? pattern.flags : `${pattern.flags}g`;
  return [...surface.matchAll(new RegExp(pattern.source, flags))].filter((m) => {
    const start = m.index ?? 0;
    const end = start + m[0].length;
    return !spans.some(([s, e]) => s <= start && end <= e);
  });
}

/**
 * matchesOutsideOwnName over a text that may be serialized JSON or HTML. Each
 * parsed JSON string value is its own surface, so JSON syntax never joins a
 * name; in HTML only the rendered text can hold the name, markup never can.
 * @param {string} content
 * @param {RegExp} pattern
 * @param {readonly unknown[]} [identifiers]
 * @returns {RegExpMatchArray[]}
 */
export function matchesOutsideOwnNameIn(content, pattern, identifiers = []) {
  const trimmed = content.trimStart();
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      return jsonStrings(JSON.parse(content)).flatMap((value) => matchesOutsideOwnName(value, pattern, identifiers));
    } catch {
      // Not JSON after all: scan the raw text.
    }
  }
  const twin = markBlocks(content);
  if (!twin) return matchesOutsideOwnName(content, pattern, identifiers);
  // HTML: rendered text gets the name exemption; markup (tags, scripts,
  // styles) is still read raw and never exempt, as before.
  const markup = content.match(/<script\b[^>]*>[\s\S]*?<\/script>|<style\b[^>]*>[\s\S]*?<\/style>|<[^>]+>/gi) ?? [];
  return [
    ...markup.flatMap((piece) => matchesOutsideOwnName(piece, pattern)),
    // Block boundaries read as spaces here, so adjacent blocks never glue our
    // word to the next one ("dead</p><p>links").
    ...matchesOutsideOwnName(twin.marked.replaceAll(twin.mark, ' '), pattern, identifiers, twin),
  ];
}

/**
 * Page-wide scan of an entity surface: verdict-class terms are forbidden
 * regardless of proximity to the name. JSON is parsed to string values first.
 * @param {string} content
 * @param {readonly unknown[]} [identifiers] the system's own name and repo; masked before matching
 * @returns {{ term: string, context: string }[]}
 */
export function scanEntityPageWide(content, identifiers = []) {
  /** @type {{ surface: string, twin: { marked: string, mark: string, residue: boolean } | null }[]} */
  const surfaces = [];
  const html = () => {
    const twin = markBlocks(content);
    return { surface: twin ? twin.marked.replaceAll(twin.mark, '') : content, twin };
  };
  const trimmed = content.trimStart();
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      surfaces.push(...jsonStrings(JSON.parse(content)).map((value) => ({ surface: value, twin: null })));
    } catch {
      surfaces.push(html());
    }
  } else {
    surfaces.push(html());
  }
  const findings = [];
  for (const { surface, twin } of surfaces) {
    for (const pattern of FORBIDDEN_ENTITY_PAGE_WIDE) {
      for (const forbidden of matchesOutsideOwnName(surface, pattern, identifiers, twin)) {
        const start = Math.max(0, (forbidden.index ?? 0) - 60);
        findings.push({ term: forbidden[0], context: surface.slice(start, (forbidden.index ?? 0) + forbidden[0].length + 60) });
      }
    }
  }
  return findings;
}

/** @param {string} file */
export function entityLexiconAllowed(file) {
  return ENTITY_LEXICON_ALLOWLIST.some((prefix) => file.replace(/^\/+/, '').startsWith(prefix));
}

/** @param {string} content */
export function normalizeLexiconSurface(content) {
  const twin = markBlocks(content);
  return twin ? twin.marked.replaceAll(twin.mark, '') : content;
}

/**
 * The lexicon surface with a mark where an HTML block starts or ends, or null
 * for text without tags. The mark is a private-use character absent from the
 * content, so literal characters survive and removing every mark gives exactly
 * the plain surface (tags dropped, whitespace runs collapsed, ends trimmed).
 * Marks exist only to stop a system name being stitched from two blocks.
 * @param {string} content
 * `residue` is set when tag removal leaves markup text behind (a `>` inside a
 * comment or a quoted attribute); such a surface gets no name exemption.
 * @returns {{ marked: string, mark: string, residue: boolean } | null}
 */
function markBlocks(content) {
  if (!/<[a-z!/][\s\S]*>/i.test(content)) return null;
  let code = 0xe000;
  while (content.includes(String.fromCharCode(code))) code += 1;
  const mark = String.fromCharCode(code);
  const run = new RegExp(`[\\s${mark}]+`, 'g');
  const ends = new RegExp(`^[\\s${mark}]+|[\\s${mark}]+$`, 'g');
  const marked = content
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '')
    // One pass with the same spans the old `<[^>]+>` removal used: a block
    // element becomes a mark, everything else (inline, comment, doctype) goes.
    .replace(/<[^>]+>/g, (tag) => {
      const name = /^<\/?([a-z][^\s/>]*)/i.exec(tag)?.[1]?.toLowerCase();
      return name && !INLINE_TAGS.has(name) ? mark : '';
    })
    .replace(/&nbsp;|&#160;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&quot;|&#34;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    // A run of whitespace and marks becomes one space (if it held whitespace)
    // plus one mark (if it held a mark); ends are trimmed with their marks.
    .replace(run, (found) => (/\s/.test(found) ? ' ' : '') + (found.includes(mark) ? mark : ''))
    .replace(ends, '');
  const residue = /<!--(?:(?!-->)[\s\S])*?>/.test(content) || /<[a-z][^>]*?=\s*["'][^"'>]*>/i.test(content);
  return { marked, mark, residue };
}

/**
 * Whole-word spans of the identifiers in `surface`. With a marked twin, spans
 * are found there (a name never crosses a block mark) and mapped back.
 * @param {string} surface
 * @param {readonly unknown[]} identifiers
 * @param {{ marked: string, mark: string, residue: boolean } | null} twin
 * @returns {[number, number][]}
 */
function ownNameSpans(surface, identifiers, twin) {
  if (twin?.residue) return [];
  const text = twin ? twin.marked : surface;
  // Same length means marks were kept as one character each (spaced twin):
  // indices are shared. Otherwise marks were removed and are skipped.
  const keepsMarks = text.length === surface.length;
  const toSurface = [];
  for (let i = 0, j = 0; i < text.length; i++) {
    if (!twin || keepsMarks || text[i] !== twin.mark) toSurface[i] = j++;
  }
  const spans = [];
  for (const identifier of identifiers) {
    if (typeof identifier !== 'string' || !identifier) continue;
    for (const m of text.matchAll(entityNamePattern(identifier))) {
      const start = (m.index ?? 0) + m[1].length;
      const end = start + m[2].length;
      if (twin && m[2].includes(twin.mark)) continue;
      if (toSurface[start] === undefined || toSurface[end - 1] === undefined) continue;
      spans.push([toSurface[start], toSurface[end - 1] + 1]);
    }
  }
  return spans;
}

/** @param {string} value */
function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** @param {string} entityName */
function entityNamePattern(entityName) {
  // Unicode letter/number/underscore boundaries are explicit because JS \b is
  // ASCII-only and treats punctuation-heavy system names inconsistently.
  return new RegExp(`(^|[^\\p{L}\\p{N}_])(${escapeRegExp(entityName)})(?=$|[^\\p{L}\\p{N}_])`, 'giu');
}

/** @param {unknown} value @returns {string[]} */
function jsonStrings(value) {
  if (typeof value === 'string') return [value];
  if (Array.isArray(value)) return value.flatMap(jsonStrings);
  if (value && typeof value === 'object') return Object.values(value).flatMap(jsonStrings);
  return [];
}

/**
 * @param {string} surface
 * @param {string} entityName
 * @param {number} windowSize
 * @param {{ marked: string, mark: string, residue: boolean } | null} [twin] the surface with HTML block marks
 * @returns {{ term: string, index: number, context: string }[]}
 */
function scanSurface(surface, entityName, windowSize, twin = null) {
  const findings = [];
  // A guarded word wholly inside the name itself never counts. Terms are
  // matched on the whole surface, then windowed: a window edge must not cut a
  // second mention of the name into a fragment that no longer reads as the
  // name. One finding per occurrence, even when two mentions share a window.
  const ours = FORBIDDEN_ENTITY_LEXICON.flatMap((pattern) => matchesOutsideOwnName(surface, pattern, [entityName], twin));
  const seen = new Set();
  for (const nameMatch of surface.matchAll(entityNamePattern(entityName))) {
    const nameIndex = (nameMatch.index ?? 0) + nameMatch[1].length;
    const start = Math.max(0, nameIndex - windowSize);
    const end = Math.min(surface.length, nameIndex + entityName.length + windowSize);
    const context = surface.slice(start, end);
    for (const forbidden of ours) {
      const at = forbidden.index ?? 0;
      const key = `${at}:${forbidden[0].length}`;
      if (at < start || at + forbidden[0].length > end || seen.has(key)) continue;
      seen.add(key);
      findings.push({ term: forbidden[0], index: nameIndex, context });
    }
  }
  return findings;
}

/**
 * @param {string} content
 * @param {string} entityName
 * @param {number} [windowSize]
 * @returns {{ term: string, index: number, context: string }[]}
 */
export function scanEntityLexicon(content, entityName, windowSize = ENTITY_LEXICON_WINDOW) {
  if (!entityName) return [];
  const trimmed = content.trimStart();
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      return jsonStrings(JSON.parse(content)).flatMap((value) => scanSurface(value, entityName, windowSize));
    } catch {
      // Malformed JSON is reported by the caller's JSON validity check. Scan
      // the raw surface too so malformed syntax cannot bypass this guard.
    }
  }
  const twin = markBlocks(content);
  return scanSurface(twin ? twin.marked.replaceAll(twin.mark, '') : content, entityName, windowSize, twin);
}
