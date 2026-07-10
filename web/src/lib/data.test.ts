import { describe, it, expect } from 'vitest';
import {
  snapshot, entities, entityById, entitiesInCohort, industries,
  cleanLabel, fmtZ, fmtSlope, SNAP_DATE, commitSeries, citationSeries,
  isCapturedAsOf, normalizeTs, risingZFloor, depsSeriesFromRows, buildDepsMap,
  type Snapshot, type Entity,
} from './data';

describe('snapshot integrity (loaded from the canonical git artifact)', () => {
  it('counts.entities matches the entities array length', () => {
    expect(snapshot.counts.entities).toBe(entities.length);
  });
  it('exposes the genesis snapshot date', () => {
    expect(SNAP_DATE).toBe(snapshot.snapshot_date);
    expect(snapshot.snapshot_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

describe('entityById', () => {
  it('resolves a real id and returns undefined for an unknown one', () => {
    const e = entities[0];
    expect(entityById(e.entity_id)).toBe(e);
    expect(entityById('e_DOES_NOT_EXIST')).toBeUndefined();
  });
});

describe('entitiesInCohort', () => {
  it('returns members of the cohort sorted by momentum descending', () => {
    const ck = Object.keys(snapshot.cohorts)[0];
    const got = entitiesInCohort(ck);
    expect(got.length).toBeGreaterThan(0);
    expect(got.every((e) => e.cohort === ck)).toBe(true);
    for (let i = 1; i < got.length; i++) {
      expect((got[i - 1].momentum ?? -1) >= (got[i].momentum ?? -1)).toBe(true);
    }
  });
});

describe('industries() taxonomy join', () => {
  it('returns one entry per industry with its sub-niches and clean labels', () => {
    const map = industries();
    expect(map.size).toBeGreaterThan(0);
    for (const ind of map.values()) {
      expect(ind.label).not.toContain('—');
      expect(ind.subniches.size).toBeGreaterThan(0);
    }
  });
});

describe('cleanLabel', () => {
  it('replaces the em-dash with a comma and leaves clean text alone', () => {
    expect(cleanLabel('Robotics — Embodied AI')).toBe('Robotics, Embodied AI');
    expect(cleanLabel('Already clean')).toBe('Already clean');
  });
});

describe('fmtZ / fmtSlope null-handling and signs', () => {
  it('fmtZ', () => {
    expect(fmtZ(null)).toBe('no axis');
    expect(fmtZ(1.2)).toBe('+1.20');
    expect(fmtZ(-0.3)).toBe('-0.30');
  });
  it('fmtSlope', () => {
    expect(fmtSlope(null)).toBe('n/a');
    expect(fmtSlope(0.123456)).toBe('+0.123');
    expect(fmtSlope(-0.5)).toBe('-0.500');
  });
});

describe('series helpers', () => {
  it('commitSeries returns an array (empty for an unknown id)', () => {
    expect(Array.isArray(commitSeries('e_nope'))).toBe(true);
    expect(commitSeries('e_nope')).toEqual([]);
  });
  it('citationSeries is year-sorted', () => {
    const withCites = entities.find((e) => e.axes.openalex_citation_momentum.by_year);
    if (withCites) {
      const s = citationSeries(withCites);
      for (let i = 1; i < s.length; i++) expect(s[i].year).toBeGreaterThan(s[i - 1].year);
    }
  });
});

// ---------------------------------------------------------------------------
//  F9 · point-in-time cutoff: future observations must not leak into older snaps
// ---------------------------------------------------------------------------
describe('point-in-time cutoff (F9)', () => {
  const olderCutoff = '2026-07-04T09:09:53+00:00';
  const futureRows = [
    {
      entity_id: 'e_TESTFUTURE01',
      coverage: 'matched',
      status: 'active',
      period: '2026-w27',
      captured_at: '2026-07-04T09:00:00Z',
      signals: { deps_dev_dependents: { value: 412, direct: 400, indirect: 12, source_system: 'pypi', package: 'diffusers' } },
    },
    {
      entity_id: 'e_TESTFUTURE01',
      coverage: 'matched',
      status: 'active',
      period: '2026-w28',
      captured_at: '2026-07-06T11:09:29Z', // AFTER older snapshot
      signals: { deps_dev_dependents: { value: 416, direct: 404, indirect: 12, source_system: 'pypi', package: 'diffusers' } },
    },
  ];

  it('isCapturedAsOf rejects captures after the snapshot cutoff', () => {
    expect(isCapturedAsOf('2026-07-04T09:00:00Z', olderCutoff)).toBe(true);
    expect(isCapturedAsOf('2026-07-04T09:09:53+00:00', olderCutoff)).toBe(true);
    expect(isCapturedAsOf('2026-07-06T11:09:29Z', olderCutoff)).toBe(false);
    expect(isCapturedAsOf(null, olderCutoff)).toBe(false);
    expect(normalizeTs('2026-07-04T09:09:53+00:00')).toBe('2026-07-04T09:09:53Z');
  });

  it('depsSeriesFromRows excludes future observations from an older cutoff', () => {
    const series = depsSeriesFromRows(futureRows, olderCutoff);
    expect(series).toEqual([{ period: '2026-w27', value: 412 }]);
    expect(series.some((p) => p.value === 416)).toBe(false);
    // full cutoff would include both
    const full = depsSeriesFromRows(futureRows, '2026-07-10T19:53:41+00:00');
    expect(full).toEqual([
      { period: '2026-w27', value: 412 },
      { period: '2026-w28', value: 416 },
    ]);
  });

  it('buildDepsMap fallback never surfaces a post-cutoff history row', () => {
    const olderSnap = {
      ...snapshot,
      snapshot_date: '2026-07-04',
      captured_at: olderCutoff,
      entities: [{ entity_id: 'e_TESTFUTURE01' } as Entity],
    } as Snapshot;
    const map = buildDepsMap(olderSnap, olderSnap.entities, {
      dayRows: [], // force history fallback
      historyByEntity: new Map([['e_TESTFUTURE01', futureRows]]),
      pinOk: () => true,
    });
    expect(map.get('e_TESTFUTURE01')?.value).toBe(412);
    expect(map.get('e_TESTFUTURE01')?.value).not.toBe(416);
  });

  it('risingZFloor follows methodology (m1: 0, m2+: 1)', () => {
    expect(risingZFloor('m1')).toBe(0);
    expect(risingZFloor('m2')).toBe(1);
    expect(risingZFloor('m3')).toBe(1);
  });
});
