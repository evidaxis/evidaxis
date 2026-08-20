import { describe, expect, it } from 'vitest';
import { computePowerFunnel, computeSensitivity } from './power';
import { CITATION_AXIS, DEVELOPMENT_AXIS, type MeasurementState } from './measurement';

function entity(id: string, opts: { devZ?: number; citZ?: number; commits?: number } = {}): any {
  return {
    entity_id: id,
    cohort: 'fixture',
    axes: {
      github_commit_velocity: { slope: 0.2, cohort_z: opts.devZ ?? 1.2, recent_weekly_commits: opts.commits ?? 8 },
      openalex_citation_momentum: { status: 'present', slope: 0.3, cohort_z: opts.citZ ?? 1.3 },
    },
  };
}

function state(id: string, history: boolean, axes: number, eligible: boolean, published = false): MeasurementState {
  const coverage = axes >= 2 ? 'measurable' : 'source_not_measured';
  const historyState = { state: history ? 'sufficient' as const : 'insufficient' as const, weekly_observations: history ? 4 : 2, required: 4 };
  return {
    schema_version: 'measurement_state_1', entity_id: id, snapshot_date: '2026-08-15', period: '2026-w33',
    observation_availability: { [DEVELOPMENT_AXIS]: 'observed', [CITATION_AXIS]: axes >= 2 ? 'observed' : 'source_not_measured' },
    history_sufficiency: historyState,
    axis_coverage: {
      axes: { [DEVELOPMENT_AXIS]: 'measurable', [CITATION_AXIS]: coverage },
      coverage_reasons: { [DEVELOPMENT_AXIS]: null, [CITATION_AXIS]: null },
      measurable_axes: axes >= 2 ? [DEVELOPMENT_AXIS, CITATION_AXIS] : [DEVELOPMENT_AXIS],
      measurable_axis_count: axes,
    },
    axes: {
      [DEVELOPMENT_AXIS]: { observation_availability: 'observed', history_sufficiency: historyState, axis_coverage: 'measurable', coverage_reason: null },
      [CITATION_AXIS]: { observation_availability: axes >= 2 ? 'observed' : 'source_not_measured', history_sufficiency: historyState, axis_coverage: coverage, coverage_reason: null },
    },
    gate_eligibility: { state: eligible ? 'eligible' : history ? 'awaiting_axis_coverage' : 'awaiting_observations', evaluated_weekly: true },
    positive_signal: { state: published ? 'published' : 'not_published', label: published ? 'Rising' : null, period: published ? '2026-w33' : null },
  };
}

describe('power funnel', () => {
  const entities = [entity('e_A'), entity('e_B'), entity('e_C'), entity('e_D'), entity('e_E')];
  const snapshot: any = { methodology_version: 'm2', entities };
  const states = new Map([
    ['e_A', state('e_A', false, 1, false)],
    ['e_B', state('e_B', true, 1, false)],
    ['e_C', state('e_C', true, 2, true)],
    ['e_D', state('e_D', true, 2, true, true)],
    ['e_E', state('e_E', true, 2, false)],
  ]);
  const resolve = (candidate: any) => states.get(candidate.entity_id)!;

  it('counts every stage cumulatively from the fixture', () => {
    expect(computePowerFunnel(snapshot, resolve)).toEqual({
      registry_members: 5,
      history_sufficient: 4,
      two_axis_measurable: 3,
      gate_eligible: 2,
      rising_published: 1,
    });
  });

  it('recomputes the final signal count under threshold variation', () => {
    expect(computeSensitivity(snapshot, [1, 1.5], 5, resolve).map((row) => row.convergence_signals)).toEqual([2, 0]);
  });
});
