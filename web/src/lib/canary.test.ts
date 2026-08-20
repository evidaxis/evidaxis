import { describe, expect, it } from 'vitest';
import { CANARY_PAIRS, canaryGroup, citationText, treatmentAnswerFirst, treatmentTitle } from './canary';
import { CITATION_AXIS, DEVELOPMENT_AXIS, type MeasurementState } from './measurement';

const state = (citationMeasured: boolean): MeasurementState => ({
  schema_version: 'measurement_state_1',
  entity_id: 'e_TESTSYSTEM01',
  snapshot_date: '2026-08-15',
  period: '2026-w33',
  observation_availability: {
    [DEVELOPMENT_AXIS]: 'observed',
    [CITATION_AXIS]: citationMeasured ? 'observed' : 'source_not_measured',
  },
  history_sufficiency: { state: 'sufficient', weekly_observations: 7, required: 4 },
  axis_coverage: {
    axes: {
      [DEVELOPMENT_AXIS]: 'measurable',
      [CITATION_AXIS]: citationMeasured ? 'measurable' : 'source_not_measured',
    },
    coverage_reasons: {
      [DEVELOPMENT_AXIS]: null,
      [CITATION_AXIS]: null,
    },
    measurable_axes: citationMeasured ? [DEVELOPMENT_AXIS, CITATION_AXIS] : [DEVELOPMENT_AXIS],
    measurable_axis_count: citationMeasured ? 2 : 1,
  },
  axes: {
    [DEVELOPMENT_AXIS]: {
      observation_availability: 'observed',
      history_sufficiency: { state: 'sufficient', weekly_observations: 7, required: 4 },
      axis_coverage: 'measurable',
      coverage_reason: null,
    },
    [CITATION_AXIS]: {
      observation_availability: citationMeasured ? 'observed' : 'source_not_measured',
      history_sufficiency: { state: 'sufficient', weekly_observations: 7, required: 4 },
      axis_coverage: citationMeasured ? 'measurable' : 'source_not_measured',
      coverage_reason: null,
    },
  },
  gate_eligibility: { state: citationMeasured ? 'eligible' : 'awaiting_axis_coverage', evaluated_weekly: true },
  positive_signal: { state: 'not_published', label: null, period: null },
});

describe('matched-control CTR canary', () => {
  it('contains 24 disjoint treatment/control pairs', () => {
    expect(CANARY_PAIRS).toHaveLength(24);
    const ids = CANARY_PAIRS.flatMap((pair) => [pair.treatment, pair.control]);
    expect(new Set(ids).size).toBe(48);
    for (const pair of CANARY_PAIRS) {
      expect(canaryGroup(pair.treatment)).toBe('treatment');
      expect(canaryGroup(pair.control)).toBe('control');
    }
  });

  it('selects the title only from actually measurable axes', () => {
    expect(treatmentTitle('System Delta', state(true))).toContain('development velocity & citation signals');
    expect(treatmentTitle('System Delta', state(false))).toContain('development velocity signals');
    expect(treatmentTitle('System Delta', state(false))).not.toContain('& citation');
  });

  it('builds answer-first and citation text deterministically', () => {
    expect(treatmentAnswerFirst('System Delta', 'Test cohort', state(false))).toBe(
      'As of 2026-08-15: System Delta (Test cohort) is under weekly measurement. Axis coverage: 1 measurable axis. Gate: not computable — 1 of 2 axes measurable (unmeasured)',
    );
    expect(citationText('System Delta', 'e_TESTSYSTEM01', '2026-08-15')).toEqual(
      citationText('System Delta', 'e_TESTSYSTEM01', '2026-08-15'),
    );
  });
});
