import { describe, expect, it } from 'vitest';
import { controlShellHash, maskWeeklyTokens } from '../../scripts/canary-shell.mjs';
import registry from './methodology-registry.json';
import baseline from '../../scripts/control-baselines.mjs';
import assignment from '../data/canary-assignment.json';

const html = '<title>Example, Evidaxis measurement</title><div class="receipt mono"><span>methodology <b>m2</b></span><span>snapshot <b>deadbeef</b></span><span>2026-w37</span></div><p class="cite-urn mono muted">urn:evidaxis:claim:e_EXAMPLE:m2:2026-09-12</p><div>axis z: 1.2</div>';

describe('control shell boundary', () => {
  it('masks weekly identity tokens, excludes axis values, and pins methodology', () => {
    expect(controlShellHash(html.replaceAll('2026-09-12', '2026-09-19').replace('deadbeef', 'abcdef').replace('2026-w37', '2026-w38'))).toBe(controlShellHash(html));
    expect(controlShellHash(html.replace('axis z: 1.2', 'axis z: -2.0'))).toBe(controlShellHash(html));
    expect(controlShellHash(html.replaceAll('m2', 'm3'))).not.toBe(controlShellHash(html));
  });
  it('pins a control baseline for the current methodology before its first snapshot ships', () => {
    // 2026-10-12: m4 went current on 2026-10-04 without a baseline; the first m4 snapshot
    // (2026-10-10) then failed check-dist on all 24 controls after a 3 h collection.
    // A methodology bump fails here, in the activation commit, instead: build the site from a
    // snapshot scored under the new version and run
    // `node web/scripts/canary-baseline.mjs --version <version>`.
    const versions = baseline.versions as Record<string, { controls?: Record<string, string> }>;
    const current = (registry.versions as { version: string; status: string }[]).filter((row) => row.status === 'current');
    expect(current.length).toBe(1);
    // Exact assigned control ids, not a count: a control absent from the snapshot is checked
    // against its older version, so a wrong key here would only fail when it returns.
    const assigned = assignment.pairs.map((pair: { control: string }) => new URL(pair.control).pathname.split('/')[2]).sort();
    for (const row of current) {
      const controls = versions[row.version]?.controls ?? {};
      expect(Object.keys(controls).sort(), `canary baseline for ${row.version}`).toEqual(assigned);
      for (const hash of Object.values(controls)) expect(hash).toMatch(/^[0-9a-f]{64}$/);
    }
  });
  it('retains structure and non-weekly numbers', () => {
    expect(controlShellHash(html.replace('receipt mono', 'receipt mono altered'))).not.toBe(controlShellHash(html));
    expect(maskWeeklyTokens('<b>1.25</b> and <b>3 axes</b>')).toBe('<b>1.25</b> and <b>3 axes</b>');
  });
});
