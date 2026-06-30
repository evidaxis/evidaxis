import { describe, it, expect } from 'vitest';
import {
  snapshot, entities, entityById, entitiesInCohort, industries,
  cleanLabel, fmtZ, fmtSlope, SNAP_DATE, commitSeries, citationSeries,
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
