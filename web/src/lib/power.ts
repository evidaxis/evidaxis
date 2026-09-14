import type { Entity, Snapshot } from './data';
import type { MeasurementState } from './measurement';
import { CITATION_AXIS, DEVELOPMENT_AXIS, DEPENDENTS_AXIS, measurementStateFor } from './measurement';
import { methodologyAxes } from './methodology';

export type PowerFunnel = {
  registry_members: number;
  history_sufficient: number;
  two_axis_measurable: number;
  three_axis_measurable?: number;
  gate_eligible: number;
  rising_published: number;
};

export type SensitivityRow = {
  z_threshold: number;
  activity_floor_weekly_commits: number;
  convergence_signals: number;
};

type StateResolver = (entity: Entity) => MeasurementState;

export function computePowerFunnel(
  snapshot: Snapshot,
  resolveState: StateResolver = (entity) => measurementStateFor(entity, snapshot),
): PowerFunnel {
  const rows = snapshot.entities.map((entity) => ({ entity, state: resolveState(entity) }));
  const history = rows.filter(({ state }) => state.history_sufficiency.state === 'sufficient');
  const twoAxis = history.filter(({ state }) => state.axis_coverage.measurable_axis_count >= 2);
  const eligible = twoAxis.filter(({ state }) => state.gate_eligibility.state === 'eligible');
  const published = eligible.filter(({ state }) => state.positive_signal.state === 'published');
  return {
    registry_members: rows.length,
    history_sufficient: history.length,
    two_axis_measurable: twoAxis.length,
    ...(methodologyAxes(snapshot.methodology_version).length === 3 ? {
      three_axis_measurable: history.filter(({ state }) => state.axis_coverage.measurable_axis_count === 3).length,
    } : {}),
    gate_eligible: eligible.length,
    rising_published: published.length,
  };
}

export function computeSensitivity(
  snapshot: Snapshot,
  thresholds = [0.5, 1, 1.5],
  activityFloor = 5,
  resolveState: StateResolver = (entity) => measurementStateFor(entity, snapshot),
): SensitivityRow[] {
  return thresholds.map((zThreshold) => {
    let convergenceSignals = 0;
    for (const entity of snapshot.entities) {
      const state = resolveState(entity);
      if (state.gate_eligibility.state !== 'eligible') continue;
      const development = entity.axes.github_commit_velocity;
      const citation = entity.axes.openalex_citation_momentum;
      const developmentQualified = state.axis_coverage.measurable_axes.includes(DEVELOPMENT_AXIS) && development.slope != null
        && development.slope > 0
        && development.cohort_z != null
        && development.cohort_z >= zThreshold
        && development.recent_weekly_commits != null
        && development.recent_weekly_commits >= activityFloor;
      const citationQualified = state.axis_coverage.measurable_axes.includes(CITATION_AXIS) && citation.slope != null
        && citation.slope > 0
        && citation.cohort_z != null
        && citation.cohort_z >= zThreshold;
      const dependents = entity.axes.deps_direct_dependents_momentum;
      const dependentsQualified = methodologyAxes(snapshot.methodology_version).includes(DEPENDENTS_AXIS)
        && state.axis_coverage.measurable_axes.includes(DEPENDENTS_AXIS)
        && dependents?.status === 'scored' && dependents.unstable === false
        && dependents.slope != null && dependents.slope > 0
        && dependents.cohort_z != null && dependents.cohort_z >= zThreshold;
      if ([developmentQualified, citationQualified, dependentsQualified].filter(Boolean).length >= 2) convergenceSignals += 1;
    }
    return {
      z_threshold: zThreshold,
      activity_floor_weekly_commits: activityFloor,
      convergence_signals: convergenceSignals,
    };
  });
}
