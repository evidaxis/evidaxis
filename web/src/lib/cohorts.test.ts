import { describe, it, expect } from 'vitest';
import { cohortVarIndex, cohortColor, cohortLabel, fmtZsafe, COHORT_ORDER } from './cohorts';

describe('cohortVarIndex', () => {
  it('maps the first three cohorts to 1..3 in snapshot order', () => {
    expect(cohortVarIndex(COHORT_ORDER[0])).toBe(1);
    expect(cohortVarIndex(COHORT_ORDER[1])).toBe(2);
    expect(cohortVarIndex(COHORT_ORDER[2])).toBe(3);
  });
  it('cycles modulo 3 and never returns 0 or >3', () => {
    for (const ck of COHORT_ORDER) {
      const i = cohortVarIndex(ck);
      expect(i).toBeGreaterThanOrEqual(1);
      expect(i).toBeLessThanOrEqual(3);
    }
  });
  it('unknown cohort falls back to index 1 (never 0)', () => {
    expect(cohortVarIndex('does-not-exist')).toBe(1);
  });
});

describe('cohortColor', () => {
  it('returns a css var reference, never a hardcoded hex', () => {
    const c = cohortColor(COHORT_ORDER[0]);
    expect(c).toMatch(/^var\(--c[123]\)$/);
    expect(c).not.toMatch(/#/);
  });
});

describe('cohortLabel', () => {
  it('strips the brand-banned em-dash (U+2014) to a comma', () => {
    // at least one real cohort label carries an em-dash; none must survive in the output
    for (const ck of COHORT_ORDER) expect(cohortLabel(ck)).not.toContain('—');
  });
  it('falls back to the key for an unknown cohort', () => {
    expect(cohortLabel('nope')).toBe('nope');
  });
});

describe('fmtZsafe', () => {
  it('null/undefined/non-finite -> "no axis"', () => {
    expect(fmtZsafe(null)).toBe('no axis');
    expect(fmtZsafe(undefined)).toBe('no axis');
    expect(fmtZsafe(NaN)).toBe('no axis');
    expect(fmtZsafe(Infinity)).toBe('no axis');
  });
  it('signs and fixes to 2 decimals', () => {
    expect(fmtZsafe(0)).toBe('+0.00');
    expect(fmtZsafe(1.234)).toBe('+1.23');
    expect(fmtZsafe(-0.5)).toBe('-0.50');
  });
});
