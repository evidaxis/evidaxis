import { describe, it, expect } from 'vitest';
import {
  recencySwing,
  commitSharpe,
  commitChangepoint,
  lag,
  alpha,
  gateEta,
  signalQuality,
  MIN_COMMIT_WEEKS,
  METHOD_VERSION,
} from './derived';
import type { Entity } from './data';

// ---------------------------------------------------------------------------
//  Fixtures over realistic series shapes (lengths match the real snapshot:
//  ~52 weekly commit points).
// ---------------------------------------------------------------------------

/** Rising fixture: 52 weeks, low early -> high late, no zeros. */
const RISING: number[] = Array.from({ length: 52 }, (_, i) => Math.round(4 + i * 0.8 + (i % 3)));

/** Flat fixture: 52 weeks of steady ~10 (small deterministic wobble). */
const FLAT: number[] = Array.from({ length: 52 }, (_, i) => 10 + (i % 2 === 0 ? 1 : -1));

/** Sparse fixture: only 12 non-zero weeks (below the 26-week gate). */
const SPARSE: number[] = Array.from({ length: 52 }, (_, i) => (i < 12 ? 5 : 0));

/** Step fixture: flat then a sharp acceleration (clear single changepoint). */
const STEP: number[] = Array.from({ length: 52 }, (_, i) => (i < 26 ? 5 : 5 + (i - 26) * 4));

const EMPTY: number[] = [];

function mkEntity(byYear: Record<string, number> | null): Entity {
  return {
    entity_id: 'e_test',
    name: 'Test System',
    slug: 'test-system',
    entity_type: 'library',
    homepage: null,
    github_repo: 'org/test',
    openalex_work_ids: [],
    industry: 'x',
    sub_niche: 'y',
    cohort: 'c',
    axes: {
      github_commit_velocity: { slope: 0.1, cohort_z: 0.5, recent_weekly_commits: 12, stars_not_scored: 100 },
      openalex_citation_momentum: {
        status: byYear ? 'present' : 'absent',
        slope: null,
        cohort_z: null,
        total_citations: byYear ? Object.values(byYear).reduce((a, b) => a + b, 0) : 0,
        by_year: byYear,
        proxy: null,
      },
    },
    momentum: 60,
    percentile: 70,
    confidence: 'high',
    axes_present: ['github_commit_velocity'],
    convergent_axes: [],
    rising: false,
    status: 'tracked',
    incumbent: false,
    note: null,
  };
}

// ---------------------------------------------------------------------------
//  recencySwing
// ---------------------------------------------------------------------------
describe('recencySwing', () => {
  it('ships a value on a rising series with declared windows', () => {
    const r = recencySwing(RISING);
    expect('reserved' in r).toBe(false);
    if ('reserved' in r) return;
    expect(r.recentWindow).toBe(13);
    expect(r.priorWindow).toBe(39);
    expect(typeof r.value).toBe('number');
    expect(r.meta.measurementMethod).toBe(METHOD_VERSION);
    expect(r.meta.measurementTechnique).toContain('#recency-swing');
  });
  it('labels a flat series as steady/flat (not accelerating)', () => {
    const r = recencySwing(FLAT);
    if ('reserved' in r) return;
    expect(['steady', 'flat', 'reversing', 'decelerating', 'declining from a flat base', 'accelerating from a flat base'])
      .toContain(r.label);
    expect(r.label).not.toBe('accelerating');
  });
  it('reserves on a too-short series', () => {
    const r = recencySwing([1, 2, 3]);
    expect('reserved' in r && r.reserved).toBe(true);
  });
  it('reports honest priorWindow on a 15-point series (not hardcoded 39)', () => {
    // 15 points: trailing 13 recent + 2 prior → priorWindow must be 2, not 39
    const short15 = Array.from({ length: 15 }, (_, i) => 2 + i);
    const r = recencySwing(short15);
    expect('reserved' in r).toBe(false);
    if ('reserved' in r) return;
    expect(r.recentWindow).toBe(13);
    expect(r.priorWindow).toBe(2); // actual prior.length
    expect(r.priorWindow).not.toBe(39);
  });
});

// ---------------------------------------------------------------------------
//  commitSharpe (sufficiency gate)
// ---------------------------------------------------------------------------
describe('commitSharpe', () => {
  it('ships value + CI + dof on a sufficient rising series', () => {
    const r = commitSharpe(RISING);
    expect('reserved' in r).toBe(false);
    if ('reserved' in r) return;
    expect(typeof r.value).toBe('number');
    expect(r.ci).toHaveLength(2);
    expect(r.ci[0]).toBeLessThanOrEqual(r.value);
    expect(r.ci[1]).toBeGreaterThanOrEqual(r.value);
    expect(r.dof).toBeGreaterThan(0);
    expect(r.value).toBeGreaterThan(0); // rising slope
    expect(r.meta.measurementTechnique).toContain('#commit-sharpe');
  });
  it('RESERVES when non-zero weeks < 26 (sufficiency gate)', () => {
    const r = commitSharpe(SPARSE);
    expect('reserved' in r && r.reserved).toBe(true);
    if (!('reserved' in r)) return;
    expect(r.reason).toContain(String(MIN_COMMIT_WEEKS));
  });
  it('RESERVES on empty series', () => {
    const r = commitSharpe(EMPTY);
    expect('reserved' in r && r.reserved).toBe(true);
  });
});

// ---------------------------------------------------------------------------
//  commitChangepoint
// ---------------------------------------------------------------------------
describe('commitChangepoint', () => {
  it('detects a single changepoint on a clear step series', () => {
    const r = commitChangepoint(STEP);
    expect('reserved' in r).toBe(false);
    expect('none' in r).toBe(false);
    if ('reserved' in r || 'none' in r) return;
    expect(r.dateIndex).toBeGreaterThan(3);
    expect(r.dateIndex).toBeLessThan(STEP.length - 3);
    expect(Math.abs(r.deltaSlope)).toBeGreaterThan(0);
    expect(r.meta.measurementTechnique).toContain('#commit-changepoint');
  });
  it('reports "none" on a flat series (no significant changepoint)', () => {
    const r = commitChangepoint(FLAT);
    expect('reserved' in r).toBe(false);
    expect('none' in r && (r as { none: true }).none).toBe(true);
    if (!('none' in r)) return;
    expect(r.label).toMatch(/no significant changepoint/i);
  });
  it('RESERVES on empty series (insufficient, not "no changepoint")', () => {
    const r = commitChangepoint(EMPTY);
    expect('reserved' in r && r.reserved).toBe(true);
    if (!('reserved' in r)) return;
    expect(r.reason).toMatch(/<8|insufficient|got 0/i);
    expect(r.reason).not.toMatch(/no significant changepoint/i);
  });
  it('RESERVES on a 7-point series (undersampled)', () => {
    const r = commitChangepoint([1, 2, 3, 4, 5, 6, 7]);
    expect('reserved' in r && r.reserved).toBe(true);
    if (!('reserved' in r)) return;
    expect(r.reason).toMatch(/<8|got 7/i);
    expect('none' in r).toBe(false);
  });
});

// ---------------------------------------------------------------------------
//  reserved-by-design signals
// ---------------------------------------------------------------------------
describe('reserved signals are honest objects, never numbers', () => {
  it('lag is reserved', () => {
    const r = lag();
    expect(r.reserved).toBe(true);
    expect(r.reason).toMatch(/cross-correlation/);
  });
  it('alpha is reserved', () => {
    const r = alpha();
    expect(r.reserved).toBe(true);
    expect(r.reason).toMatch(/power ~0/);
  });
  it('gateEta is reserved', () => {
    const r = gateEta();
    expect(r.reserved).toBe(true);
    expect(r.reason).toMatch(/snapshot history/);
  });
});

// ---------------------------------------------------------------------------
//  signalQuality
// ---------------------------------------------------------------------------
describe('signalQuality', () => {
  it('reports commit weeks, citation years, and shipped/reserved lists', () => {
    const e = mkEntity({ '2021': 11, '2022': 16, '2023': 24, '2024': 33, '2025': 37 });
    const sq = signalQuality(e, RISING);
    expect(sq.commit_weeks).toBe(52);
    expect(sq.citation_years).toBe(5);
    expect(sq.derived_reserved).toContain('gate-eta');
    expect(sq.derived_reserved).toContain('code-leads-citation-lag');
    expect(sq.derived_reserved).toContain('axis-alpha');
    expect(sq.derived_shipped).toContain('recency-swing');
    expect(sq.derived_shipped).toContain('commit-sharpe');
  });
  it('moves commit-sharpe to reserved on a sparse series', () => {
    const e = mkEntity(null);
    const sq = signalQuality(e, SPARSE);
    expect(sq.citation_years).toBe(0);
    expect(sq.derived_reserved).toContain('commit-sharpe');
    expect(sq.derived_shipped).not.toContain('commit-sharpe');
  });
  it('marks undersampled changepoint as reserved (insufficient), not shipped', () => {
    const e = mkEntity(null);
    const sq = signalQuality(e, [1, 2, 3, 4, 5, 6, 7]);
    expect(sq.derived_reserved).toContain('commit-changepoint');
    expect(sq.derived_shipped).not.toContain('commit-changepoint');
  });
});
