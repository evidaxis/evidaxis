/**
 * Positive-only discovery-surface lexicon guard.
 *
 * HTML is scanned contextually after tag removal. JSON is parsed first and
 * each string value is scanned on its own, so neighbouring fields cannot form
 * a synthetic context window.
 */
export const ENTITY_LEXICON_WINDOW = 120;

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
 * Page-wide scan of an entity surface: verdict-class terms are forbidden
 * regardless of proximity to the name. JSON is parsed to string values first.
 * @param {string} content
 * @returns {{ term: string, context: string }[]}
 */
export function scanEntityPageWide(content) {
  const surfaces = [];
  const trimmed = content.trimStart();
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      surfaces.push(...jsonStrings(JSON.parse(content)));
    } catch {
      surfaces.push(normalizeLexiconSurface(content));
    }
  } else {
    surfaces.push(normalizeLexiconSurface(content));
  }
  const findings = [];
  for (const surface of surfaces) {
    for (const pattern of FORBIDDEN_ENTITY_PAGE_WIDE) {
      const flags = pattern.flags.includes('g') ? pattern.flags : `${pattern.flags}g`;
      for (const forbidden of surface.matchAll(new RegExp(pattern.source, flags))) {
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
  if (!/<[a-z!/][\s\S]*>/i.test(content)) return content;
  return content
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;|&#160;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&quot;|&#34;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/\s+/g, ' ')
    .trim();
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
 * @returns {{ term: string, index: number, context: string }[]}
 */
function scanSurface(surface, entityName, windowSize) {
  const findings = [];
  for (const nameMatch of surface.matchAll(entityNamePattern(entityName))) {
    const nameIndex = (nameMatch.index ?? 0) + nameMatch[1].length;
    const start = Math.max(0, nameIndex - windowSize);
    const end = Math.min(surface.length, nameIndex + entityName.length + windowSize);
    const context = surface.slice(start, end);
    for (const pattern of FORBIDDEN_ENTITY_LEXICON) {
      const flags = pattern.flags.includes('g') ? pattern.flags : `${pattern.flags}g`;
      for (const forbidden of context.matchAll(new RegExp(pattern.source, flags))) {
        const forbiddenIndex = start + (forbidden.index ?? 0);
        const isEntityNameItself = forbidden[0].localeCompare(entityName, undefined, { sensitivity: 'accent' }) === 0
          && forbiddenIndex === nameIndex;
        if (!isEntityNameItself) findings.push({ term: forbidden[0], index: nameIndex, context });
      }
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
  return scanSurface(normalizeLexiconSurface(content), entityName, windowSize);
}
