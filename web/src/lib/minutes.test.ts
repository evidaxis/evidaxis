import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { snapshots } from './archive';
import { CITATION_AXIS, DEVELOPMENT_AXIS, deriveMeasurementState } from './measurement';
import {
  MINUTES_SENTENCE_CAP,
  canonicalWeeklySnapshots,
  cohortMinutesForPair,
  renderCohortMinutes,
} from './minutes';

function snapshot(date: string) {
  const found = snapshots.find((candidate) => candidate.snapshot_date === date);
  if (!found) throw new Error(`missing historical fixture snapshot ${date}`);
  return found;
}

function golden(name: string): string {
  return readFileSync(resolve(import.meta.dirname, 'fixtures', name), 'utf8');
}

describe('deterministic cohort minutes goldens', () => {
  const previous = snapshot('2026-08-08');
  const current = snapshot('2026-08-15');
  const minutes = cohortMinutesForPair(previous, current);

  it('matches the unassigned-cohort historical golden byte for byte', () => {
    const record = minutes.find((candidate) => candidate.cohort === 'unassigned-v1');
    expect(record).toBeTruthy();
    expect(renderCohortMinutes(record!)).toBe(golden('minutes-unassigned-2026-W33.golden.json'));
  });

  it('matches the post-training historical golden byte for byte', () => {
    const record = minutes.find((candidate) => candidate.cohort === 'post-training-alignment');
    expect(record).toBeTruthy();
    expect(renderCohortMinutes(record!)).toBe(golden('minutes-post-training-2026-W33.golden.json'));
  });

  it('has no template sentence without one or more source fields', () => {
    for (const record of minutes) {
      for (const sentence of record.sentences) {
        expect(sentence.text.trim().endsWith('.')).toBe(true);
        expect(sentence.source_fields.length).toBeGreaterThan(0);
      }
    }
  });

  it('is byte-identical for identical input snapshots', () => {
    const again = cohortMinutesForPair(previous, current);
    expect(again.map(renderCohortMinutes)).toEqual(minutes.map(renderCohortMinutes));
  });
});

function fixtureEntity(id: string, cohort = 'fixture', name = `System ${id}`): any {
  return {
    entity_id: id, name, cohort, incumbent: false, openalex_work_ids: ['W1'],
    axes_present: [DEVELOPMENT_AXIS, CITATION_AXIS], convergent_axes: [], rising: false,
    axes: {
      github_commit_velocity: { slope: 0.2, cohort_z: 0.3 },
      openalex_citation_momentum: { status: 'present', slope: 0.2, cohort_z: 0.3 },
    },
  };
}

function fixtureSnapshot(date: string, period: string, entities: any[], capturedAt = `${date}T08:00:00Z`): any {
  const cohorts = Object.fromEntries([...new Set(entities.map((entity) => entity.cohort))]
    .map((cohort) => [cohort, { label: `Label ${cohort}`, industry: 'ai', sub_niche: cohort }]));
  return { snapshot_date: date, period, captured_at: capturedAt, methodology_version: 'm2', entities, cohorts };
}

const resolveFixtureState = (candidate: any, snap: any) => deriveMeasurementState(candidate, snap, 4);

describe('cohort minutes edge contracts', () => {
  it('keeps a continuous indexed page for a quiet live cohort', () => {
    const members = [fixtureEntity('e_1')];
    const minutes = cohortMinutesForPair(
      fixtureSnapshot('2026-08-08', '2026-w32', members),
      fixtureSnapshot('2026-08-15', '2026-w33', members),
      { resolveState: resolveFixtureState, dropped: new Set() },
    );
    expect(minutes).toHaveLength(1);
    expect(minutes[0].sentences).toEqual([expect.objectContaining({
      event_kind: 'quiet_week', text: 'No measurement-state changes this week.',
    })]);
    expect(minutes[0].noindex).toBe(false);
  });

  it('marks a newly appearing cohort without a false 0-to-N coverage change', () => {
    const existing = fixtureEntity('e_old', 'old');
    const added = fixtureEntity('e_new', 'new');
    const minutes = cohortMinutesForPair(
      fixtureSnapshot('2026-08-08', '2026-w32', [existing]),
      fixtureSnapshot('2026-08-15', '2026-w33', [existing, added]),
      { resolveState: resolveFixtureState, dropped: new Set() },
    ).find((record) => record.cohort === 'new');
    expect(minutes?.sentences.some((sentence) => sentence.event_kind === 'cohort_added')).toBe(true);
    expect(minutes?.sentences.some((sentence) => sentence.event_kind === 'coverage_changed')).toBe(false);
  });

  it('uses snapshot entity data for names and includes collection failures', () => {
    const member = fixtureEntity('e_1', 'fixture', 'System: Alpha');
    const minutes = cohortMinutesForPair(
      fixtureSnapshot('2026-08-08', '2026-w32', [member]),
      fixtureSnapshot('2026-08-15', '2026-w33', [member]),
      { resolveState: resolveFixtureState, dropped: new Set(['e_1']) },
    )[0];
    expect(minutes.sentences).toEqual([expect.objectContaining({
      event_kind: 'collection_failed', text: 'Collection record unavailable for System: Alpha.',
    })]);
  });

  it('caps sentences deterministically after applying event priority', () => {
    const prior = fixtureEntity('e_prior', 'other');
    const added = Array.from({ length: 60 }, (_, index) => fixtureEntity(`e_${String(index).padStart(2, '0')}`));
    const minutes = cohortMinutesForPair(
      fixtureSnapshot('2026-08-08', '2026-w32', [prior]),
      fixtureSnapshot('2026-08-15', '2026-w33', [prior, ...added]),
      { resolveState: resolveFixtureState, dropped: new Set() },
    ).find((record) => record.cohort === 'fixture');
    expect(minutes?.sentences).toHaveLength(MINUTES_SENTENCE_CAP);
    expect(minutes?.sentences.some((sentence) => sentence.event_kind === 'cohort_added')).toBe(true);
    expect(minutes?.sentences.map((sentence) => sentence.entity_ids[0]).filter(Boolean))
      .toEqual(Array.from({ length: 49 }, (_, index) => `e_${String(index).padStart(2, '0')}`));
  });

  it('deduplicates a period by latest captured_at, independent of insertion order', () => {
    const member = fixtureEntity('e_1');
    const early = fixtureSnapshot('2026-08-09', '2026-w32', [member], '2026-08-09T09:00:00Z');
    const late = fixtureSnapshot('2026-08-08', '2026-w32', [member], '2026-08-10T09:00:00Z');
    const next = fixtureSnapshot('2026-08-15', '2026-w33', [member]);
    expect(canonicalWeeklySnapshots([late, next, early])[0]).toBe(late);
  });
});
