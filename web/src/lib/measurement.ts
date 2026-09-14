/**
 * Canonical typed measurement-state projection.
 *
 * Snapshot rows remain the immutable source data. Every public status phrase
 * and machine serialization is derived here from explicit mechanical states.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { REPO_ROOT as ROOT, dataPath, repoDataPath } from './data-path';
import { CITATION_AXIS, DEVELOPMENT_AXIS, DEPENDENTS_AXIS, methodologyAxes, type AxisKey, type VersionedAxes } from './methodology';
export { CITATION_AXIS, DEVELOPMENT_AXIS, DEPENDENTS_AXIS, type AxisKey } from './methodology';

export const HISTORY_REQUIRED = 4;

export type ObservationAvailability = 'observed' | 'source_not_measured' | 'no_data';
export type AxisCoverageState = 'measurable' | 'insufficient_source_coverage' | 'source_not_measured' | 'no_data'
  | 'below_floor' | 'held' | 'stale' | 'out_of_panel';
export type AxisCoverageReason =
  | 'cohort_z_unavailable'
  | 'source_returned_too_few'
  | 'axis_not_declared_measurable'
  | null;
export type HistorySufficiencyState = 'sufficient' | 'insufficient';
export type GateEligibilityState =
  | 'eligible'
  | 'awaiting_observations'
  | 'awaiting_axis_coverage'
  | 'reference_measurement'
  | 'awaiting_cohort_floor';
export type PositiveSignalState = 'published' | 'not_published';

export type AxisMeasurementState = {
  observation_availability: ObservationAvailability;
  history_sufficiency: {
    state: HistorySufficiencyState;
    weekly_observations: number;
    required: number;
  };
  axis_coverage: AxisCoverageState;
  coverage_reason: AxisCoverageReason;
};

export type MeasurementState = {
  schema_version: 'measurement_state_1';
  entity_id: string;
  snapshot_date: string;
  period: string;
  observation_availability: VersionedAxes<ObservationAvailability>;
  history_sufficiency: {
    state: HistorySufficiencyState;
    weekly_observations: number;
    required: number;
  };
  axis_coverage: {
    axes: VersionedAxes<AxisCoverageState>;
    coverage_reasons: VersionedAxes<AxisCoverageReason>;
    measurable_axes: AxisKey[];
    measurable_axis_count: number;
  };
  axes: VersionedAxes<AxisMeasurementState>;
  gate_eligibility: {
    state: GateEligibilityState;
    evaluated_weekly: true;
  };
  positive_signal: {
    state: PositiveSignalState;
    label: 'Rising' | null;
    period: string | null;
  };
};

type EntityLike = {
  entity_id: string;
  incumbent?: boolean;
  openalex_work_ids?: string[];
  axes?: {
    github_commit_velocity?: { slope?: number | null; cohort_z?: number | null };
    openalex_citation_momentum?: { status?: string; slope?: number | null; cohort_z?: number | null };
    deps_direct_dependents_momentum?: {
      status?: string; slope?: number | null; cohort_z?: number | null;
      latest?: number | null; points?: number | null; rising_vote?: boolean; unstable?: boolean | null;
    };
  };
  axes_present?: string[];
  convergent_axes?: string[];
  rising?: boolean;
  cohort: string;
};

type SnapshotLike = {
  snapshot_date: string;
  captured_at: string;
  period: string;
  methodology_version: string;
  entities: EntityLike[];
};

function historyState(weeklyObservations: number) {
  if (!Number.isFinite(weeklyObservations) || weeklyObservations < 0) {
    throw new Error('invalid_weekly_observations');
  }
  return {
    state: weeklyObservations >= HISTORY_REQUIRED ? 'sufficient' as const : 'insufficient' as const,
    weekly_observations: weeklyObservations,
    required: HISTORY_REQUIRED,
  };
}

function axisObservationAndCoverage(entity: EntityLike, axis: AxisKey): {
  observation: ObservationAvailability;
  coverage: AxisCoverageState;
  reason: AxisCoverageReason;
} {
  if (axis === DEPENDENTS_AXIS) {
    const record = entity.axes?.deps_direct_dependents_momentum;
    if (!record) return { observation: 'no_data', coverage: 'no_data', reason: null };
    if (!['scored', 'below_floor', 'held', 'stale', 'out_of_panel'].includes(String(record.status))) {
      throw new Error(`unknown_dependents_status: ${String(record.status)}`);
    }
    if (record.status === 'out_of_panel') {
      return { observation: 'source_not_measured', coverage: 'out_of_panel', reason: null };
    }
    const observation = record.latest != null ? 'observed' as const : 'no_data' as const;
    if (record.status !== 'scored') return { observation, coverage: record.status as AxisCoverageState, reason: null };
    if (record.slope == null || record.cohort_z == null) {
      throw new Error('scored_dependents_axis_missing_values');
    }
    return entity.axes_present?.includes(DEPENDENTS_AXIS)
      ? { observation, coverage: 'measurable', reason: null }
      : { observation, coverage: 'insufficient_source_coverage', reason: 'axis_not_declared_measurable' };
  }
  if (axis === DEVELOPMENT_AXIS) {
    const record = entity.axes?.github_commit_velocity;
    if (!record || record.slope == null) return { observation: 'no_data', coverage: 'no_data', reason: null };
    if (record.cohort_z == null) {
      return {
        observation: 'observed',
        coverage: 'insufficient_source_coverage',
        reason: 'cohort_z_unavailable',
      };
    }
    return entity.axes_present?.includes(DEVELOPMENT_AXIS)
      ? { observation: 'observed', coverage: 'measurable', reason: null }
      : {
          observation: 'observed',
          coverage: 'insufficient_source_coverage',
          reason: 'axis_not_declared_measurable',
        };
  }

  const record = entity.axes?.openalex_citation_momentum;
  if (!record) return { observation: 'no_data', coverage: 'no_data', reason: null };
  if (!['present', 'insufficient', 'absent'].includes(String(record.status))) {
    throw new Error(`unknown_citation_status: ${String(record.status)}`);
  }
  const sourceConfigured = (entity.openalex_work_ids?.length ?? 0) > 0;
  if (!sourceConfigured) {
    return { observation: 'source_not_measured', coverage: 'source_not_measured', reason: null };
  }
  if (record.status === 'insufficient') {
    return {
      observation: 'observed',
      coverage: 'insufficient_source_coverage',
      reason: 'source_returned_too_few',
    };
  }
  if (record.status === 'absent' || record.slope == null) {
    return { observation: 'no_data', coverage: 'no_data', reason: null };
  }
  if (record.cohort_z == null) {
    return {
      observation: 'observed',
      coverage: 'insufficient_source_coverage',
      reason: 'cohort_z_unavailable',
    };
  }
  return entity.axes_present?.includes(CITATION_AXIS)
    ? { observation: 'observed', coverage: 'measurable', reason: null }
    : {
        observation: 'observed',
        coverage: 'insufficient_source_coverage',
        reason: 'axis_not_declared_measurable',
      };
}

export function deriveMeasurementState(
  entity: EntityLike,
  snapshot: SnapshotLike,
  weeklyObservations: number,
): MeasurementState {
  const axisKeys = methodologyAxes(snapshot.methodology_version);
  const projected = Object.fromEntries(axisKeys.map((axis) => [axis, axisObservationAndCoverage(entity, axis)])) as VersionedAxes<ReturnType<typeof axisObservationAndCoverage>>;
  const history = historyState(weeklyObservations);
  const coverage = Object.fromEntries(axisKeys.map((axis) => [axis, projected[axis]!.coverage])) as VersionedAxes<AxisCoverageState>;
  const coverageReasons = Object.fromEntries(axisKeys.map((axis) => [axis, projected[axis]!.reason])) as VersionedAxes<AxisCoverageReason>;
  const measurableAxes = axisKeys
    .filter((axis) => coverage[axis] === 'measurable')
    .sort((a, b) => a.localeCompare(b));
  const cohortSize = snapshot.entities.filter((candidate) => candidate.cohort === entity.cohort).length;
  const cohortFloor = snapshot.methodology_version === 'm1' ? 0 : 5;

  let gateState: GateEligibilityState;
  if (history.state === 'insufficient') gateState = 'awaiting_observations';
  else if (measurableAxes.length < 2) gateState = 'awaiting_axis_coverage';
  else if (entity.incumbent) gateState = 'reference_measurement';
  else if (cohortSize < cohortFloor) gateState = 'awaiting_cohort_floor';
  else gateState = 'eligible';

  if (entity.rising === true) {
    const convergentAxes = [...new Set(entity.convergent_axes ?? [])];
    const allConvergentAxesMeasurable = convergentAxes.every((axis) =>
      measurableAxes.includes(axis as AxisKey));
    const dependents = entity.axes?.deps_direct_dependents_momentum;
    const validDependentsVote = !convergentAxes.includes(DEPENDENTS_AXIS)
      || (dependents?.rising_vote === true && dependents.unstable === false);
    if (convergentAxes.length < 2 || !allConvergentAxesMeasurable || !validDependentsVote) {
      throw new Error(`inconsistent_positive_signal: ${entity.entity_id}`);
    }
  }
  const positivePublished = entity.rising === true && gateState === 'eligible';
  const observationAvailability = Object.fromEntries(axisKeys.map((axis) => [axis, projected[axis]!.observation])) as VersionedAxes<ObservationAvailability>;

  return {
    schema_version: 'measurement_state_1',
    entity_id: entity.entity_id,
    snapshot_date: snapshot.snapshot_date,
    period: snapshot.period,
    observation_availability: observationAvailability,
    history_sufficiency: history,
    axis_coverage: {
      axes: coverage,
      coverage_reasons: coverageReasons,
      measurable_axes: measurableAxes,
      measurable_axis_count: measurableAxes.length,
    },
    axes: Object.fromEntries(axisKeys.map((axis) => [axis, {
      observation_availability: projected[axis]!.observation,
      history_sufficiency: axis === DEPENDENTS_AXIS ? {
        state: (entity.axes?.deps_direct_dependents_momentum?.points ?? 0) >= 14 ? 'sufficient' : 'insufficient',
        weekly_observations: entity.axes?.deps_direct_dependents_momentum?.points ?? 0,
        required: 14,
      } : history,
      axis_coverage: projected[axis]!.coverage,
      coverage_reason: projected[axis]!.reason,
    }])) as VersionedAxes<AxisMeasurementState>,
    gate_eligibility: { state: gateState, evaluated_weekly: true },
    positive_signal: {
      state: positivePublished ? 'published' : 'not_published',
      label: positivePublished ? 'Rising' : null,
      period: positivePublished ? snapshot.period : null,
    },
  };
}

export type HistoryRejectionCounters = {
  parse_error: number;
  unsupported_version: number;
  entity_mismatch: number;
  missing_period: number;
  invalid_captured_at: number;
  captured_after_cutoff: number;
  noncanonical_capture: number;
  duplicate_period: number;
};

export type ObservationHistoryInspection = {
  periods: string[];
  rejected: HistoryRejectionCounters;
};

const emptyHistoryRejections = (): HistoryRejectionCounters => ({
  parse_error: 0,
  unsupported_version: 0,
  entity_mismatch: 0,
  missing_period: 0,
  invalid_captured_at: 0,
  captured_after_cutoff: 0,
  noncanonical_capture: 0,
  duplicate_period: 0,
});

function historyError(message: string, rejected: HistoryRejectionCounters): Error {
  const error = new Error(message) as Error & { rejected: HistoryRejectionCounters };
  error.rejected = { ...rejected };
  return error;
}

export function inspectObservationHistory(
  entityId: string,
  cutoff: string,
  options: { repoRoot?: string; canonicalCapturedAtByPeriod?: Map<string, string> } = {},
): ObservationHistoryInspection {
  if (!/^[a-z0-9_-]{1,64}$/i.test(entityId)) throw new Error('invalid_entity_id');
  const cutoffMs = Date.parse(cutoff);
  if (!Number.isFinite(cutoffMs)) throw new Error('invalid_history_cutoff');

  const rejected = emptyHistoryRejections();
  let raw = '';
  try {
    raw = readFileSync(repoDataPath(options.repoRoot ?? ROOT, 'history', `${entityId}.jsonl`), 'utf8');
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return { periods: [], rejected };
    throw error;
  }

  const periodCounts = new Map<string, number>();
  for (const line of raw.split('\n')) {
    if (!line.trim()) continue;
    let row: any;
    try {
      row = JSON.parse(line);
    } catch {
      rejected.parse_error += 1;
      continue;
    }
    if (row?.v !== 'ts_1') {
      rejected.unsupported_version += 1;
      continue;
    }
    if (row?.entity_id !== entityId) {
      rejected.entity_mismatch += 1;
      continue;
    }
    if (typeof row?.period !== 'string' || !row.period) {
      rejected.missing_period += 1;
      continue;
    }
    const capturedMs = Date.parse(String(row.captured_at ?? ''));
    if (!Number.isFinite(capturedMs)) {
      rejected.invalid_captured_at += 1;
      continue;
    }
    if (capturedMs > cutoffMs) {
      rejected.captured_after_cutoff += 1;
      continue;
    }
    const canonicalCapturedAt = options.canonicalCapturedAtByPeriod?.get(row.period);
    if (canonicalCapturedAt !== undefined && row.captured_at !== canonicalCapturedAt) {
      rejected.noncanonical_capture += 1;
      continue;
    }
    periodCounts.set(row.period, (periodCounts.get(row.period) ?? 0) + 1);
  }

  for (const count of periodCounts.values()) {
    if (count > 1) rejected.duplicate_period += count - 1;
  }
  if (rejected.parse_error > 0) throw historyError('history_source_corrupt', rejected);
  if (rejected.duplicate_period > 0) throw historyError('history_duplicate_period', rejected);
  return { periods: [...periodCounts.keys()].sort(), rejected };
}

type ArchivedCapture = { period: string; captured_at: string };
let archivedCaptures: ArchivedCapture[] | undefined;

function canonicalCapturesAsOf(cutoff: string): Map<string, string> {
  if (!archivedCaptures) {
    archivedCaptures = readdirSync(dataPath('snapshots'), { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
      .map((entry) => JSON.parse(readFileSync(dataPath('snapshots', entry.name, 'snapshot.json'), 'utf8')))
      .map((snapshot) => ({ period: String(snapshot.period), captured_at: String(snapshot.captured_at) }));
  }
  const cutoffMs = Date.parse(cutoff);
  const canonical = new Map<string, string>();
  for (const capture of archivedCaptures) {
    const capturedMs = Date.parse(capture.captured_at);
    if (!Number.isFinite(capturedMs) || capturedMs > cutoffMs) continue;
    const prior = canonical.get(capture.period);
    if (!prior || capturedMs > Date.parse(prior)) canonical.set(capture.period, capture.captured_at);
  }
  return canonical;
}

function observationPeriods(entityId: string, cutoff: string): string[] {
  return inspectObservationHistory(entityId, cutoff, {
    canonicalCapturedAtByPeriod: canonicalCapturesAsOf(cutoff),
  }).periods;
}

export function measurementStateFor(entity: EntityLike, snapshot: SnapshotLike): MeasurementState {
  if (!/^[a-z0-9_-]{1,64}$/i.test(entity.entity_id)) throw new Error('invalid_entity_id');
  let bySnapshot = stateCache.get(entity);
  if (!bySnapshot) {
    bySnapshot = new WeakMap();
    stateCache.set(entity, bySnapshot);
  }
  const cached = bySnapshot.get(snapshot);
  if (cached) return cached;
  const state = deriveMeasurementState(entity, snapshot, observationPeriods(entity.entity_id, snapshot.captured_at).length);
  bySnapshot.set(snapshot, state);
  return state;
}

const stateCache = new WeakMap<object, WeakMap<object, MeasurementState>>();

export type MeasurementPhrases = {
  history: string;
  development_axis: string;
  citation_axis: string;
  dependents_axis?: string;
  axis_coverage: string;
  gate: string;
  signal: string;
  compact: string;
};

function coverageReasonPhrase(reason: AxisCoverageReason): string | null {
  if (reason === 'cohort_z_unavailable') return 'cohort comparison unavailable';
  if (reason === 'source_returned_too_few') return 'source returned too few observations';
  if (reason === 'axis_not_declared_measurable') return 'axis was not declared measurable';
  return null;
}

function axisPhrase(
  axis: string,
  state: AxisCoverageState,
  reason: AxisCoverageReason,
): string {
  if (state === 'out_of_panel') return `${axis} axis: outside the frozen panel; not measured.`;
  if (state === 'below_floor') return `${axis} axis: minimum of 14 clean points and 5 latest dependents not met.`;
  if (state === 'held') return `${axis} axis: cohort source agreement insufficient; score withheld.`;
  if (state === 'stale') return `${axis} axis: confirmed-clean partition older than 28 days; score withheld.`;
  if (state === 'measurable') return `${axis} axis: measured.`;
  if (state === 'insufficient_source_coverage') {
    const detail = coverageReasonPhrase(reason);
    return `${axis} axis: insufficient source coverage${detail ? ` (${detail})` : ''}.`;
  }
  if (state === 'source_not_measured') return `${axis} source: not measured.`;
  return `${axis} axis: no observation data.`;
}

function unavailableAxisReason(state: MeasurementState): string | null {
  const unavailable = (Object.keys(state.axes) as AxisKey[])
    .filter((axis) => state.axis_coverage.axes[axis] !== 'measurable');
  if (unavailable.length !== 1) return null;
  const coverage = state.axis_coverage.axes[unavailable[0]];
  if (coverage === 'insufficient_source_coverage') {
    return coverageReasonPhrase(state.axis_coverage.coverage_reasons[unavailable[0]] ?? null) ?? 'coverage';
  }
  if (coverage === 'source_not_measured') return 'unmeasured';
  if (coverage === 'no_data') return 'missing';
  return null;
}

function gatePhrase(state: MeasurementState): string {
  if (state.positive_signal.state === 'published') {
    return `Convergence gate: evaluated weekly; Rising signal published for ${state.positive_signal.period}.`;
  }

  const history = state.history_sufficiency;
  const measurable = state.axis_coverage.measurable_axis_count;
  switch (state.gate_eligibility.state) {
    case 'awaiting_observations':
      return `Gate: not computable — history ${history.weekly_observations} of ${history.required} weekly observations`;
    case 'awaiting_axis_coverage': {
      const reason = unavailableAxisReason(state);
      return `Gate: not computable — ${measurable} of ${Object.keys(state.axes).length} axes measurable${reason ? ` (${reason})` : ''}`;
    }
    case 'awaiting_cohort_floor':
      return 'Gate: not computable — cohort below comparison floor';
    case 'reference_measurement':
      return 'Gate: not computable — reference measurement';
    case 'eligible':
      return 'Gate: computed weekly across the cohort; no convergence event this week';
  }
}

export function measurementPhrases(state: MeasurementState): MeasurementPhrases {
  const history = state.history_sufficiency;
  const historyPhrase = history.state === 'sufficient'
    ? `History: ${history.weekly_observations} weekly observations; minimum ${history.required}.`
    : `History: ${history.weekly_observations} of ${history.required} weekly observations.`;
  const developmentPhrase = axisPhrase(
    'Development velocity',
    state.axis_coverage.axes[DEVELOPMENT_AXIS],
    state.axis_coverage.coverage_reasons[DEVELOPMENT_AXIS],
  );
  const citationPhrase = axisPhrase(
    'Citation',
    state.axis_coverage.axes[CITATION_AXIS],
    state.axis_coverage.coverage_reasons[CITATION_AXIS],
  );
  const n = state.axis_coverage.measurable_axis_count;
  const axisCount = Object.keys(state.axes).length;
  const coverageReadout = axisCount === 3 ? `${n} of ${axisCount} axes measurable` : `${n} measurable ${n === 1 ? 'axis' : 'axes'}`;
  const axisCoveragePhrase = `Axis coverage: ${coverageReadout}.`;
  const gate = gatePhrase(state);
  const signalPhrase = state.positive_signal.state === 'published'
    ? `Rising signal published for ${state.positive_signal.period}.`
    : gate;
  return {
    history: historyPhrase,
    development_axis: developmentPhrase,
    citation_axis: citationPhrase,
    ...(state.axes[DEPENDENTS_AXIS] ? { dependents_axis: axisPhrase(
      'Direct-dependents', state.axes[DEPENDENTS_AXIS]!.axis_coverage, state.axes[DEPENDENTS_AXIS]!.coverage_reason,
    ) } : {}),
    axis_coverage: axisCoveragePhrase,
    gate,
    signal: signalPhrase,
    compact: state.positive_signal.state === 'published'
      ? 'Rising'
      : coverageReadout,
  };
}

export function serializeMeasurementState(state: MeasurementState) {
  return {
    ...state,
    phrases: measurementPhrases(state),
  };
}
