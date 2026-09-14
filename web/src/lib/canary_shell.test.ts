import { describe, expect, it } from 'vitest';
import { controlShellHash, maskWeeklyTokens } from '../../scripts/canary-shell.mjs';

const html = '<title>Example, Evidaxis measurement</title><div class="receipt mono"><span>methodology <b>m2</b></span><span>snapshot <b>deadbeef</b></span><span>2026-w37</span></div><p class="cite-urn mono muted">urn:evidaxis:claim:e_EXAMPLE:m2:2026-09-12</p><div>axis z: 1.2</div>';

describe('control shell boundary', () => {
  it('masks weekly identity tokens, excludes axis values, and pins methodology', () => {
    expect(controlShellHash(html.replaceAll('2026-09-12', '2026-09-19').replace('deadbeef', 'abcdef').replace('2026-w37', '2026-w38'))).toBe(controlShellHash(html));
    expect(controlShellHash(html.replace('axis z: 1.2', 'axis z: -2.0'))).toBe(controlShellHash(html));
    expect(controlShellHash(html.replaceAll('m2', 'm3'))).not.toBe(controlShellHash(html));
  });
  it('retains structure and non-weekly numbers', () => {
    expect(controlShellHash(html.replace('receipt mono', 'receipt mono altered'))).not.toBe(controlShellHash(html));
    expect(maskWeeklyTokens('<b>1.25</b> and <b>3 axes</b>')).toBe('<b>1.25</b> and <b>3 axes</b>');
  });
});
