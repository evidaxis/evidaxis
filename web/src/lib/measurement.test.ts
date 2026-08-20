import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  CITATION_AXIS,
  DEVELOPMENT_AXIS,
  deriveMeasurementState,
  inspectObservationHistory,
  measurementPhrases,
  serializeMeasurementState,
} from './measurement';

const entity = {
  entity_id: 'e_TESTSYSTEM01',
  cohort: 'test-cohort',
  incumbent: false,
  openalex_work_ids: ['W1'],
  axes_present: [DEVELOPMENT_AXIS],
  convergent_axes: [],
  rising: false,
  axes: {
    github_commit_velocity: { slope: 0.1, cohort_z: 0.2 },
    openalex_citation_momentum: { status: 'insufficient' as const, slope: null, cohort_z: null },
  },
};
const snapshot = {
  snapshot_date: '2026-08-15',
  captured_at: '2026-08-15T07:00:00Z',
  period: '2026-w33',
  methodology_version: 'm2',
  entities: Array.from({ length: 5 }, (_, index) => ({ ...entity, entity_id: `e_TEST${index}` })),
};

const twoAxisEntity = {
  ...entity,
  axes_present: [DEVELOPMENT_AXIS, CITATION_AXIS],
  axes: {
    ...entity.axes,
    openalex_citation_momentum: { status: 'present' as const, slope: 0.2, cohort_z: 0.3 },
  },
};

const snapshotWith = (candidate: typeof twoAxisEntity, count = 5) => ({
  ...snapshot,
  entities: Array.from({ length: count }, (_, index) => ({ ...candidate, entity_id: `e_TEST${index}` })),
});

describe('typed measurement states', () => {
  it('keeps observation, history, axis coverage, gate, and signal distinct', () => {
    const state = deriveMeasurementState(entity, snapshot, 3);
    expect(state.observation_availability[DEVELOPMENT_AXIS]).toBe('observed');
    expect(state.history_sufficiency).toEqual({ state: 'insufficient', weekly_observations: 3, required: 4 });
    expect(state.axis_coverage.axes[CITATION_AXIS]).toBe('insufficient_source_coverage');
    expect(state.gate_eligibility.state).toBe('awaiting_observations');
    expect(state.positive_signal.state).toBe('not_published');
  });

  it('publishes human phrases only from the typed state projection', () => {
    const serialized = serializeMeasurementState(deriveMeasurementState(entity, snapshot, 3));
    expect(serialized.phrases.history).toBe('History: 3 of 4 weekly observations.');
    expect(serialized.phrases.citation_axis).toBe(
      'Citation axis: insufficient source coverage (source returned too few observations).',
    );
    expect(serialized.phrases.gate).toBe('Gate: not computable — history 3 of 4 weekly observations');
    expect(serialized.phrases.signal).toBe(serialized.phrases.gate);
    expect(measurementPhrases(serialized).compact).toBe('1 measurable axis');
  });

  it('explains every non-published gate state in instrument voice', () => {
    const coverage = deriveMeasurementState(entity, snapshot, 4);
    expect(measurementPhrases(coverage).gate).toBe(
      'Gate: not computable — 1 of 2 axes measurable (source returned too few observations)',
    );

    const unmeasured = deriveMeasurementState({
      ...entity,
      openalex_work_ids: [],
      axes: {
        ...entity.axes,
        openalex_citation_momentum: { status: 'absent' as const, slope: null, cohort_z: null },
      },
    }, snapshot, 4);
    expect(measurementPhrases(unmeasured).gate).toBe('Gate: not computable — 1 of 2 axes measurable (unmeasured)');

    const missing = deriveMeasurementState({
      ...entity,
      axes: { ...entity.axes, openalex_citation_momentum: undefined },
    }, snapshot, 4);
    expect(measurementPhrases(missing).gate).toBe('Gate: not computable — 1 of 2 axes measurable (missing)');

    const cohortFloor = deriveMeasurementState(twoAxisEntity, snapshotWith(twoAxisEntity, 4), 4);
    expect(measurementPhrases(cohortFloor).gate).toBe('Gate: not computable — cohort below comparison floor');

    const eligible = deriveMeasurementState(twoAxisEntity, snapshotWith(twoAxisEntity), 4);
    expect(measurementPhrases(eligible).gate).toBe('Gate: computed weekly across the cohort; no convergence event this week');

    const reference = deriveMeasurementState({ ...twoAxisEntity, incumbent: true }, snapshotWith(twoAxisEntity), 4);
    expect(measurementPhrases(reference).gate).toBe('Gate: not computable — reference measurement');
  });

  it('keeps the published gate phrase unchanged', () => {
    const published = deriveMeasurementState({
      ...twoAxisEntity,
      rising: true,
      convergent_axes: [DEVELOPMENT_AXIS, CITATION_AXIS],
    }, snapshotWith(twoAxisEntity), 4);
    expect(measurementPhrases(published).gate).toBe(
      'Convergence gate: evaluated weekly; Rising signal published for 2026-w33.',
    );
  });

  it('distinguishes missing slopes from unavailable cohort comparisons', () => {
    const noSlope = deriveMeasurementState({
      ...entity,
      axes: { ...entity.axes, github_commit_velocity: { slope: null, cohort_z: null } },
    }, snapshot, 4);
    expect(noSlope.observation_availability[DEVELOPMENT_AXIS]).toBe('no_data');
    expect(noSlope.axis_coverage.axes[DEVELOPMENT_AXIS]).toBe('no_data');

    const noCohortZ = deriveMeasurementState({
      ...entity,
      axes: { ...entity.axes, github_commit_velocity: { slope: 0.2, cohort_z: null } },
    }, snapshot, 4);
    expect(noCohortZ.observation_availability[DEVELOPMENT_AXIS]).toBe('observed');
    expect(noCohortZ.axis_coverage.axes[DEVELOPMENT_AXIS]).toBe('insufficient_source_coverage');
    expect(noCohortZ.axis_coverage.coverage_reasons[DEVELOPMENT_AXIS]).toBe('cohort_z_unavailable');
    expect(measurementPhrases(noCohortZ).development_axis).toContain('cohort comparison unavailable');
  });

  it('fails closed on unknown citation status and invalid history counts', () => {
    expect(() => deriveMeasurementState({
      ...entity,
      axes: { ...entity.axes, openalex_citation_momentum: { status: 'mystery', slope: null, cohort_z: null } },
    }, snapshot, 4)).toThrow('unknown_citation_status: mystery');
    expect(() => deriveMeasurementState(entity, snapshot, Number.NaN)).toThrow('invalid_weekly_observations');
    expect(() => deriveMeasurementState(entity, snapshot, -1)).toThrow('invalid_weekly_observations');
  });

  it('publishes positive state only for eligible, internally consistent data', () => {
    const published = deriveMeasurementState({
      ...twoAxisEntity,
      rising: true,
      convergent_axes: [CITATION_AXIS, DEVELOPMENT_AXIS],
    }, snapshotWith(twoAxisEntity), 4);
    expect(published.axis_coverage.measurable_axes).toEqual([DEVELOPMENT_AXIS, CITATION_AXIS]);
    expect(published.positive_signal.state).toBe('published');

    const reference = deriveMeasurementState({
      ...twoAxisEntity,
      incumbent: true,
      rising: true,
      convergent_axes: [DEVELOPMENT_AXIS, CITATION_AXIS],
    }, snapshotWith(twoAxisEntity), 4);
    expect(reference.gate_eligibility.state).toBe('reference_measurement');
    expect(reference.positive_signal.state).toBe('not_published');
    expect(measurementPhrases(reference).gate).toBe('Gate: not computable — reference measurement');

    expect(() => deriveMeasurementState({
      ...entity,
      rising: true,
      convergent_axes: [DEVELOPMENT_AXIS, CITATION_AXIS],
    }, snapshot, 4)).toThrow('inconsistent_positive_signal');
  });

  it('validates history paths and fails on corrupt or duplicate canonical rows', () => {
    const root = mkdtempSync(join(tmpdir(), 'evidaxis-measurement-'));
    mkdirSync(join(root, 'data', 'history'), { recursive: true });
    const row = (period: string) => JSON.stringify({
      v: 'ts_1', entity_id: 'e_TEST', period, captured_at: '2026-08-15T08:00:00Z',
    });

    expect(() => inspectObservationHistory('../escape', '2026-08-15T09:00:00Z', { repoRoot: root }))
      .toThrow('invalid_entity_id');

    writeFileSync(join(root, 'data', 'history', 'e_TEST.jsonl'), `${row('2026-w32')}\n{broken\n`);
    try {
      inspectObservationHistory('e_TEST', '2026-08-15T09:00:00Z', { repoRoot: root });
      throw new Error('expected corrupt history to fail');
    } catch (error) {
      expect((error as Error).message).toBe('history_source_corrupt');
      expect((error as Error & { rejected: { parse_error: number } }).rejected.parse_error).toBe(1);
    }

    writeFileSync(join(root, 'data', 'history', 'e_TEST.jsonl'), `${row('2026-w32')}\n${row('2026-w32')}\n`);
    expect(() => inspectObservationHistory('e_TEST', '2026-08-15T09:00:00Z', { repoRoot: root }))
      .toThrow('history_duplicate_period');

    writeFileSync(join(root, 'data', 'history', 'e_TEST.jsonl'), `${row('2026-w31')}\n${row('2026-w32')}\n`);
    const inspected = inspectObservationHistory('e_TEST', '2026-08-15T09:00:00Z', {
      repoRoot: root,
      canonicalCapturedAtByPeriod: new Map([
        ['2026-w31', '2026-08-08T08:00:00Z'],
        ['2026-w32', '2026-08-15T08:00:00Z'],
      ]),
    });
    expect(inspected.periods).toEqual(['2026-w32']);
    expect(inspected.rejected.noncanonical_capture).toBe(1);
  });

  it('is byte-deterministic for identical inputs', () => {
    const first = JSON.stringify(serializeMeasurementState(deriveMeasurementState(entity, snapshot, 4)));
    const second = JSON.stringify(serializeMeasurementState(deriveMeasurementState(entity, snapshot, 4)));
    expect(second).toBe(first);
  });
});
