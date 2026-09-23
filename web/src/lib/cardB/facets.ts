import { FACETS, COPY } from '../../data/card-b-facets';
import { scanEntityLexicon, scanEntityPageWide } from '../../../scripts/entity-lexicon.mjs';

export type FacetInput = {
  commits: number | null; zeroWeeks: number; commitWeeks: number; axes: number;
  citations: number | null; paperLinked: boolean; years: number; registryMedian: number | null;
  dependents: number | null; depsStatus: string | null; points: number | null;
  rising: boolean; incumbent: boolean; observations: number;
};

export function selectClasses(f: FacetInput) {
  const fields = ['commits', 'zeroWeeks', 'commitWeeks', 'axes', 'citations', 'paperLinked', 'years', 'registryMedian', 'dependents', 'depsStatus', 'points', 'rising', 'incumbent', 'observations'] as const;
  for (const key of fields) if (f[key] === undefined) throw new Error(`Undefined predicate input: ${key}`);
  const first = (rules: [keyof typeof FACETS, boolean][]) => rules.find(([, matches]) => matches)![0];
  return {
    code: first([
      ['C00', f.commits === null], ['C06', f.commits === 0 && f.zeroWeeks === f.commitWeeks],
      ['C15c', f.commits === 0], ['C15b', f.axes <= 1 && f.commits! < 5],
      ['C15a', f.axes <= 1], ['C16', true],
    ]),
    citations: first([
      ['C_NO_CITATION', f.citations === null && f.paperLinked],
      ['C_NO_PAPER', f.citations === null], ['C07', f.years < 3],
      ['C08', f.registryMedian !== null && f.citations! >= f.registryMedian], ['C09', true],
    ]),
    dependents: first([
      ['C11', f.depsStatus === 'out_of_panel'], ['C13b', f.dependents === null],
      ['C13', f.dependents === 0], ['C12', f.dependents! < 5],
      ['C14', f.depsStatus !== 'scored'], ['C10a', true],
    ]),
    standing: first([
      ['C01', f.rising], ['C02', f.incumbent], ['C03', f.observations < 4],
      ['C04', f.axes < 2], ['C05', true],
    ]),
  };
}

export function assertPublicText(text: string, name: string, banned: string[] = []) {
  const findings = [...scanEntityLexicon(text, name), ...scanEntityPageWide(text)];
  if (findings.length || /\u2014|\bn\/a\b|\b(dead|abandoned|dormant|stale|unmaintained|declining|suspended)\b/i.test(text)) {
    throw new Error(`Unsafe Card B text for ${name}: ${text}`);
  }
  let decoded = text.replace(/\\u([a-f\d]{4})/gi, (_, h) => String.fromCharCode(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => String.fromCharCode(+d));
  for (let i = 0; i < 3; i++) { try { decoded = decodeURIComponent(decoded); } catch { break; } }
  if (banned.some(owner => decoded.toLowerCase().includes(owner.toLowerCase()))
    || /"(?:author|founder)"|"@type"\s*:\s*"Person"/i.test(text)) {
    throw new Error(`person_free violation in Card B for ${name}`);
  }
  return text;
}

export function interpolate(template: string, vars: Record<string, string | number>, name: string, banned: string[] = []) {
  const text = template.replace(/\{(\w+)\}/g, (_, key) => {
    if (vars[key] === undefined || vars[key] === null) throw new Error(`Missing facet substitution: ${key}`);
    return String(vars[key]);
  });
  return assertPublicText(text, name, banned);
}

export function facet(id: keyof typeof FACETS, vars: Record<string, string | number>, name: string, banned: string[] = []) {
  const entry = FACETS[id];
  return { id, claim_id: entry.claim_id,
    text: interpolate(entry.text, vars, name, banned),
    answer: interpolate(entry.answer, vars, name, banned) };
}

export function copy(key: keyof typeof COPY, vars: Record<string, string | number>, name: string, banned: string[] = []) {
  return { id: key, claim_id: `urn:evidaxis:claim:class:${key}:b1`, text: interpolate(COPY[key], vars, name, banned) };
}
