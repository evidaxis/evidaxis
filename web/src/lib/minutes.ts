import type { Entity, Snapshot } from './data';
import { snapshots } from './archive';
import { diffFeedEntries, type FeedEntry } from './feed';
import { CITATION_AXIS, DEVELOPMENT_AXIS, measurementStateFor, type MeasurementState } from './measurement';

export type MinuteSentence = {
  event_kind: string;
  text: string;
  entity_ids: string[];
  source_fields: string[];
};

export type CohortMinutes = {
  schema_version: 'cohort_minutes_1';
  cohort: string;
  slug: string;
  label: string;
  period: string;
  week: string;
  snapshot_date: string;
  previous_snapshot_date: string;
  sentences: MinuteSentence[];
  noindex: boolean;
};

type StateResolver = (entity: Entity, snapshot: Snapshot) => MeasurementState;

export const MINUTES_SENTENCE_CAP = 50;
// D3 cutover: W30-W31 are the two-week prose backfill seed; W32 and every later
// snapshot are forward records. This boundary must not slide as snapshots land.
export const MINUTES_BACKFILL_START_PERIOD = '2026-w30';
export const MINUTES_FORWARD_START_PERIOD = '2026-w32';

const NEWSWORTHY = new Set([
  'measurement_activated',
  'measurement_resumed',
  'reference_baseline_added',
  'reference_baseline_recorded',
  'axis_available',
  'history_sufficient',
  'gate_eligible',
  'axis_threshold_recorded',
  'convergence_published',
  'collection_failed',
]);

const EVENT_PRIORITY: Record<string, number> = {
  convergence_published: 0,
  collection_failed: 1,
  cohort_added: 2,
  coverage_changed: 3,
  reference_baseline_recorded: 4,
  reference_baseline_added: 4,
  gate_eligible: 5,
  axis_threshold_recorded: 6,
  history_sufficient: 7,
  axis_available: 8,
  measurement_resumed: 9,
  measurement_activated: 10,
  quiet_week: 11,
};

export function weekSlug(period: string): string {
  const match = period.match(/^(\d{4})-w(\d{2})$/i);
  return match ? `${match[1]}-W${match[2]}` : period;
}

function nameForEntry(entry: FeedEntry, previousById: Map<string, Entity>, currentById: Map<string, Entity>): string {
  const id = entry.entity_ids[0];
  const entity = currentById.get(id) ?? previousById.get(id);
  if (!entity) throw new Error(`minute_entity_missing: ${id}`);
  return entity.name;
}

function axisName(entry: FeedEntry): string {
  if (entry.source_fields.some((field) => field.includes(DEVELOPMENT_AXIS))) return 'Development velocity';
  if (entry.source_fields.some((field) => field.includes(CITATION_AXIS))) return 'Citation';
  throw new Error(`minute_axis_missing: ${entry.id}`);
}

function sentenceForEntry(
  entry: FeedEntry,
  previousById: Map<string, Entity>,
  currentById: Map<string, Entity>,
): string {
  const name = nameForEntry(entry, previousById, currentById);
  if (entry.event_kind === 'measurement_activated') return `Weekly measurement activated for ${name}.`;
  if (entry.event_kind === 'measurement_resumed') return `Weekly measurement resumed for ${name}.`;
  if (entry.event_kind === 'reference_baseline_added') return `Reference baseline added for ${name}.`;
  if (entry.event_kind === 'reference_baseline_recorded') return `Reference baseline recorded for ${name}.`;
  if (entry.event_kind === 'axis_available') return `${axisName(entry)} axis available for ${name}.`;
  if (entry.event_kind === 'history_sufficient') return `Four-week history recorded for ${name}.`;
  if (entry.event_kind === 'gate_eligible') return `Weekly gate evaluation activated for ${name}.`;
  if (entry.event_kind === 'axis_threshold_recorded') return `Axis threshold recorded for ${name}.`;
  if (entry.event_kind === 'convergence_published') return `Rising signal published for ${name}.`;
  if (entry.event_kind === 'collection_failed') return `Collection record unavailable for ${name}.`;
  throw new Error(`unsupported minute event: ${entry.event_kind}`);
}

function twoAxisCoverage(snapshot: Snapshot, cohort: string, resolveState: StateResolver): { members: number; measured: number; ratio: number } {
  const members = snapshot.entities.filter((entity) => entity.cohort === cohort);
  const measured = members.filter((entity) => resolveState(entity, snapshot).axis_coverage.measurable_axis_count >= 2).length;
  return { members: members.length, measured, ratio: members.length ? measured / members.length : 0 };
}

function sentenceOrder(a: MinuteSentence, b: MinuteSentence): number {
  return a.event_kind.localeCompare(b.event_kind)
    || a.entity_ids.join(',').localeCompare(b.entity_ids.join(','));
}

function cappedSentences(sentences: MinuteSentence[]): MinuteSentence[] {
  return [...sentences]
    .sort((a, b) =>
      (EVENT_PRIORITY[a.event_kind] ?? Number.MAX_SAFE_INTEGER)
      - (EVENT_PRIORITY[b.event_kind] ?? Number.MAX_SAFE_INTEGER)
      || sentenceOrder(a, b))
    .slice(0, MINUTES_SENTENCE_CAP)
    .sort(sentenceOrder);
}

export function cohortMinutesForPair(
  previous: Snapshot,
  current: Snapshot,
  options: { resolveState?: StateResolver; coverageChangeThreshold?: number; dropped?: Set<string> } = {},
): CohortMinutes[] {
  const resolveState = options.resolveState ?? measurementStateFor;
  const coverageChangeThreshold = options.coverageChangeThreshold ?? 0.05;
  const entries = diffFeedEntries(previous, current, { resolveState, dropped: options.dropped });
  const previousById = new Map(previous.entities.map((entity) => [entity.entity_id, entity]));
  const currentById = new Map(current.entities.map((entity) => [entity.entity_id, entity]));
  const cohortKeys = [...new Set([
    ...Object.keys(previous.cohorts ?? {}),
    ...Object.keys(current.cohorts ?? {}),
    ...previous.entities.map((entity) => entity.cohort),
    ...current.entities.map((entity) => entity.cohort),
  ])].sort();
  const out: CohortMinutes[] = [];

  for (const cohort of cohortKeys) {
    const sentences: MinuteSentence[] = entries
      .filter((entry) => entry.cohort === cohort && NEWSWORTHY.has(entry.event_kind))
      .map((entry) => ({
        event_kind: entry.event_kind,
        text: sentenceForEntry(entry, previousById, currentById),
        entity_ids: [...entry.entity_ids].sort((a, b) => a.localeCompare(b)),
        source_fields: [...entry.source_fields].sort((a, b) => a.localeCompare(b)),
      }));

    const priorCoverage = twoAxisCoverage(previous, cohort, resolveState);
    const currentCoverage = twoAxisCoverage(current, cohort, resolveState);
    if (priorCoverage.members === 0 && currentCoverage.members > 0) {
      sentences.push({
        event_kind: 'cohort_added',
        text: `Cohort added with ${currentCoverage.members} measured ${currentCoverage.members === 1 ? 'system' : 'systems'}.`,
        entity_ids: [],
        source_fields: [`/current/cohorts/${cohort}`, `/current/cohorts/${cohort}/members`],
      });
    } else if (
      priorCoverage.members > 0
      && currentCoverage.members > 0
      && Math.abs(currentCoverage.ratio - priorCoverage.ratio) > coverageChangeThreshold
    ) {
      const percent = (value: number) => (value * 100).toFixed(1);
      sentences.push({
        event_kind: 'coverage_changed',
        text: `Two-axis coverage changed from ${percent(priorCoverage.ratio)}% to ${percent(currentCoverage.ratio)}%.`,
        entity_ids: [],
        source_fields: [
          `/diff/cohorts/${cohort}/two_axis_coverage/previous`,
          `/diff/cohorts/${cohort}/two_axis_coverage/current`,
        ],
      });
    }

    if (sentences.length === 0 && currentCoverage.members > 0) {
      sentences.push({
        event_kind: 'quiet_week',
        text: 'No measurement-state changes this week.',
        entity_ids: [],
        source_fields: [`/diff/cohorts/${cohort}/measurement_state_changes`],
      });
    }
    if (sentences.length === 0) continue;

    const meta = current.cohorts?.[cohort] ?? previous.cohorts?.[cohort];
    out.push({
      schema_version: 'cohort_minutes_1',
      cohort,
      slug: meta?.sub_niche ?? cohort,
      label: meta?.label ?? cohort,
      period: current.period,
      week: weekSlug(current.period),
      snapshot_date: current.snapshot_date,
      previous_snapshot_date: previous.snapshot_date,
      sentences: cappedSentences(sentences),
      noindex: false,
    });
  }
  return out;
}

export function renderCohortMinutes(minutes: CohortMinutes): string {
  return `${JSON.stringify(minutes, null, 2)}\n`;
}

export function canonicalWeeklySnapshots(allSnapshots: Snapshot[]): Snapshot[] {
  const byPeriod = new Map<string, Snapshot>();
  for (const snapshot of allSnapshots) {
    const prior = byPeriod.get(snapshot.period);
    const capturedMs = Date.parse(snapshot.captured_at);
    const priorMs = prior ? Date.parse(prior.captured_at) : Number.NEGATIVE_INFINITY;
    if (!Number.isFinite(capturedMs)) throw new Error(`invalid_snapshot_captured_at: ${snapshot.captured_at}`);
    if (!prior || capturedMs > priorMs || (capturedMs === priorMs && snapshot.snapshot_date > prior.snapshot_date)) {
      byPeriod.set(snapshot.period, snapshot);
    }
  }
  return [...byPeriod.values()].sort((a, b) => {
    const captured = Date.parse(a.captured_at) - Date.parse(b.captured_at);
    return captured || a.snapshot_date.localeCompare(b.snapshot_date);
  });
}

export function allCohortMinutes(allSnapshots: Snapshot[] = snapshots): CohortMinutes[] {
  const weekly = canonicalWeeklySnapshots(allSnapshots);
  const out: CohortMinutes[] = [];
  for (let index = 1; index < weekly.length; index += 1) {
    if (weekly[index].period.localeCompare(MINUTES_BACKFILL_START_PERIOD) < 0) continue;
    out.push(...cohortMinutesForPair(weekly[index - 1], weekly[index]));
  }
  return out;
}

export function cohortMinutes(allSnapshots: Snapshot[] = snapshots): CohortMinutes[] {
  return allCohortMinutes(allSnapshots);
}
