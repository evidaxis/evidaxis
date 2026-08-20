import { createHash } from 'node:crypto';
import type { Entity, Snapshot } from './data';
import { readSnapshotArtifactRaw, snapshots } from './archive';
import {
  CITATION_AXIS,
  DEVELOPMENT_AXIS,
  measurementPhrases,
  measurementStateFor,
  serializeMeasurementState,
  type AxisKey,
  type MeasurementState,
} from './measurement';

export type FeedEntryType = 'observation' | 'moment_signal';
export type ObservationEventKind =
  | 'measurement_activated'
  | 'measurement_resumed'
  | 'reference_baseline_added'
  | 'reference_baseline_recorded'
  | 'axis_available'
  | 'history_sufficient'
  | 'gate_eligible'
  | 'axis_threshold_recorded'
  | 'axis_threshold_lost'
  | 'collection_failed'
  | 'baseline_unavailable'
  | 'quiet_week';

export type FeedEntry = {
  schema_version: 'typed_feed_entry_1';
  id: string;
  type: FeedEntryType;
  event_kind: ObservationEventKind | 'convergence_published';
  title: string;
  summary: string;
  url: string;
  snapshot_date: string;
  period: string;
  date_published: string;
  cohort: string | null;
  entity_ids: string[];
  source_fields: string[];
  state: unknown;
};

type StateResolver = (entity: Entity, snapshot: Snapshot) => MeasurementState;

const axisLabel: Record<AxisKey, string> = {
  [DEVELOPMENT_AXIS]: 'Development velocity',
  [CITATION_AXIS]: 'Citation',
};

export function entryId(payload: Omit<FeedEntry, 'id' | 'url'>): string {
  const canonical = JSON.stringify({
    type: payload.type,
    event_kind: payload.event_kind,
    period: payload.period,
    snapshot_date: payload.snapshot_date,
    cohort: payload.cohort,
    entity_ids: [...payload.entity_ids].sort((a, b) => a.localeCompare(b)),
    title: payload.title,
    summary: payload.summary,
    schema_version: payload.schema_version,
  });
  const digest = createHash('sha256').update(canonical).digest('hex').slice(0, 16);
  return `${payload.type === 'moment_signal' ? 'moment' : 'observation'}-${payload.period}-${digest}`;
}

function finalize(payload: Omit<FeedEntry, 'id' | 'url'>): FeedEntry {
  const normalized = {
    ...payload,
    entity_ids: [...payload.entity_ids].sort((a, b) => a.localeCompare(b)),
    source_fields: [...payload.source_fields].sort((a, b) => a.localeCompare(b)),
  };
  const id = entryId(normalized);
  return { ...normalized, id, url: `https://evidaxis.org/signals/${id}/` };
}

function entityPointer(entity: Entity, suffix = ''): string {
  return `/entities/${entity.entity_id}${suffix}`;
}

function typedObservation(
  current: Snapshot,
  entity: Entity,
  state: MeasurementState,
  eventKind: ObservationEventKind,
  title: string,
  sourceFields: string[],
): FeedEntry {
  const gate = measurementPhrases(state).gate;
  const canonicalSummary = `${title}. ${gate}${gate.endsWith('.') ? '' : '.'}`;
  return finalize({
    schema_version: 'typed_feed_entry_1',
    type: 'observation',
    event_kind: eventKind,
    title,
    summary: canonicalSummary,
    snapshot_date: current.snapshot_date,
    period: current.period,
    date_published: current.captured_at,
    cohort: entity.cohort,
    entity_ids: [entity.entity_id],
    source_fields: [...sourceFields].sort(),
    state: serializeMeasurementState(state),
  });
}

function droppedIds(snapshotDate: string): Set<string> {
  const raw = readSnapshotArtifactRaw(snapshotDate, 'dropped.json');
  if (!raw) return new Set();
  try {
    const body = JSON.parse(raw.toString('utf8'));
    return new Set((body?.dropped ?? []).map((row: any) => row.entity_id).filter((id: unknown): id is string => typeof id === 'string'));
  } catch {
    return new Set();
  }
}

export function diffFeedEntries(
  previous: Snapshot | null | undefined,
  current: Snapshot | null | undefined,
  options: { resolveState?: StateResolver; dropped?: Set<string> } = {},
): FeedEntry[] {
  if (!previous || !current) throw new Error('snapshot_diff_input_undefined');
  if (!Array.isArray(previous.entities) || !Array.isArray(current.entities)) {
    throw new Error('snapshot_entities_invalid');
  }
  if (current.entities.length === 0) throw new Error('current_snapshot_empty');

  const resolveState = options.resolveState ?? measurementStateFor;
  const dropped = options.dropped ?? droppedIds(current.snapshot_date);
  const previousById = new Map(previous.entities.map((entity) => [entity.entity_id, entity]));
  const entries: FeedEntry[] = [];

  if (previous.entities.length === 0) {
    return [finalize({
      schema_version: 'typed_feed_entry_1',
      type: 'observation',
      event_kind: 'baseline_unavailable',
      title: 'Comparison baseline unavailable',
      summary: `No prior entity baseline is available for ${current.period}; snapshot diff suppressed.`,
      snapshot_date: current.snapshot_date,
      period: current.period,
      date_published: current.captured_at,
      cohort: null,
      entity_ids: current.entities.map((entity) => entity.entity_id),
      source_fields: ['/previous/entities', '/current/entities'],
      state: { comparison_baseline: 'unavailable', diff_suppressed: true },
    })];
  }

  for (const entity of [...current.entities].sort((a, b) => a.entity_id.localeCompare(b.entity_id))) {
    if (dropped.has(entity.entity_id)) continue;
    const state = resolveState(entity, current);
    const prior = previousById.get(entity.entity_id);
    if (!prior) {
      if (entity.incumbent) {
        entries.push(typedObservation(
          current,
          entity,
          state,
          'reference_baseline_added',
          `Reference baseline added: ${entity.name}`,
          [entityPointer(entity)],
        ));
        continue;
      }
      const resumed = state.history_sufficiency.weekly_observations > 1;
      entries.push(typedObservation(
        current,
        entity,
        state,
        resumed ? 'measurement_resumed' : 'measurement_activated',
        `${resumed ? 'Weekly measurement resumed' : 'Weekly measurement activated'}: ${entity.name}`,
        [entityPointer(entity)],
      ));
      continue;
    }

    const priorState = resolveState(prior, previous);
    for (const axis of [DEVELOPMENT_AXIS, CITATION_AXIS] as AxisKey[]) {
      if (priorState.axis_coverage.axes[axis] !== 'measurable' && state.axis_coverage.axes[axis] === 'measurable') {
        entries.push(typedObservation(
          current,
          entity,
          state,
          'axis_available',
          `${axisLabel[axis]} axis available: ${entity.name}`,
          [entityPointer(entity, `/axes/${axis}`)],
        ));
      }
    }
    if (priorState.history_sufficiency.state !== 'sufficient' && state.history_sufficiency.state === 'sufficient') {
      entries.push(typedObservation(
        current,
        entity,
        state,
        'history_sufficient',
        `Four-week history recorded: ${entity.name}`,
        [entityPointer(entity, '/history_sufficiency')],
      ));
    }
    if (priorState.gate_eligibility.state !== 'eligible' && state.gate_eligibility.state === 'eligible') {
      entries.push(typedObservation(
        current,
        entity,
        state,
        'gate_eligible',
        `Weekly gate evaluation activated: ${entity.name}`,
        [entityPointer(entity, '/gate_eligibility')],
      ));
    }
    const priorThresholds = new Set(prior.convergent_axes ?? []);
    const currentThresholds = new Set(entity.convergent_axes ?? []);
    for (const axis of [...currentThresholds].filter((value) => !priorThresholds.has(value)).sort()) {
      entries.push(typedObservation(
        current,
        entity,
        state,
        'axis_threshold_recorded',
        `Axis threshold event: ${entity.name}`,
        [entityPointer(entity, `/convergent_axes/${axis}`)],
      ));
    }
    for (const axis of [...priorThresholds].filter((value) => !currentThresholds.has(value)).sort()) {
      entries.push(typedObservation(
        current,
        entity,
        state,
        'axis_threshold_lost',
        `Axis threshold no longer recorded: ${entity.name}`,
        [entityPointer(entity, `/convergent_axes/${axis}`)],
      ));
    }
    if (entity.incumbent && entity.rising === true && prior.rising !== true) {
      entries.push(typedObservation(
        current,
        entity,
        state,
        'reference_baseline_recorded',
        `Reference baseline recorded: ${entity.name}`,
        [entityPointer(entity, '/reference_measurement')],
      ));
    } else if (state.positive_signal.state === 'published' && priorState.positive_signal.state !== 'published') {
      const gate = measurementPhrases(state).gate;
      entries.push(finalize({
        schema_version: 'typed_feed_entry_1',
        type: 'moment_signal',
        event_kind: 'convergence_published',
        title: `Rising signal published: ${entity.name}`,
        summary: `${entity.name} has a published two-axis convergence signal for ${current.period}. ${gate}`,
        snapshot_date: current.snapshot_date,
        period: current.period,
        date_published: current.captured_at,
        cohort: entity.cohort,
        entity_ids: [entity.entity_id],
        source_fields: [entityPointer(entity, '/positive_signal')],
        state: serializeMeasurementState(state),
      }));
    }
  }

  const rawCurrentById = new Map(current.entities.map((entity) => [entity.entity_id, entity]));
  for (const id of [...dropped].sort((a, b) => a.localeCompare(b))) {
    const entity = previousById.get(id) ?? rawCurrentById.get(id);
    if (!entity) continue;
    entries.push(finalize({
      schema_version: 'typed_feed_entry_1',
      type: 'observation',
      event_kind: 'collection_failed',
      title: `Collection record unavailable: ${entity.name}`,
      summary: `No observation record was produced for ${entity.name} in ${current.period}; collection state: failed.`,
      snapshot_date: current.snapshot_date,
      period: current.period,
      date_published: current.captured_at,
      cohort: entity.cohort,
      entity_ids: [id],
      source_fields: [`/dropped/${id}`],
      state: { observation_availability: 'collection_failed', collection_status: 'failed' },
    }));
  }

  if (entries.length === 0) {
    entries.push(finalize({
      schema_version: 'typed_feed_entry_1',
      type: 'observation',
      event_kind: 'quiet_week',
      title: `${current.entities.length} systems measured, no convergence signals`,
      summary: `${current.entities.length} systems were measured in ${current.period}; no convergence signals were published.`,
      snapshot_date: current.snapshot_date,
      period: current.period,
      date_published: current.captured_at,
      cohort: null,
      entity_ids: [],
      source_fields: ['/counts/entities', '/counts/rising'],
      state: { systems_measured: current.entities.length, convergence_signals: 0 },
    }));
  }

  return entries.sort((a, b) =>
    a.type.localeCompare(b.type)
    || a.event_kind.localeCompare(b.event_kind)
    || a.entity_ids.join(',').localeCompare(b.entity_ids.join(','))
    || a.id.localeCompare(b.id));
}

export function allSignalEntries(allSnapshots: Snapshot[] = snapshots): FeedEntry[] {
  const entries: FeedEntry[] = [];
  for (let index = 1; index < allSnapshots.length; index += 1) {
    entries.push(...diffFeedEntries(allSnapshots[index - 1], allSnapshots[index]));
  }
  return entries;
}

export function signalEntries(allSnapshots: Snapshot[] = snapshots): FeedEntry[] {
  return allSignalEntries(allSnapshots);
}

export function latestFeedEntries(allSnapshots: Snapshot[] = snapshots): FeedEntry[] {
  return allSnapshots.length >= 2
    ? diffFeedEntries(allSnapshots[allSnapshots.length - 2], allSnapshots[allSnapshots.length - 1])
    : [];
}

export function jsonFeed(entries: FeedEntry[] = latestFeedEntries()) {
  return {
    version: 'https://jsonfeed.org/version/1.1',
    title: 'Evidaxis typed measurement feed',
    home_page_url: 'https://evidaxis.org/',
    feed_url: 'https://evidaxis.org/feed.json',
    description: 'Weekly observation events and published two-axis convergence signals.',
    items: entries.map((entry) => ({
      id: entry.url,
      url: entry.url,
      title: entry.title,
      content_text: entry.summary,
      date_published: entry.date_published,
      tags: [entry.type, entry.event_kind],
      _evidaxis: entry,
    })),
  };
}

function xml(value: string): string {
  return value.replace(/[<>&'\"]/g, (char) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[char]!));
}

export function atomFeed(entries: FeedEntry[] = latestFeedEntries()): string {
  const updated = entries.reduce<string | null>((latest, entry) => {
    if (!latest) return entry.date_published;
    const entryMs = Date.parse(entry.date_published);
    const latestMs = Date.parse(latest);
    if (!Number.isFinite(entryMs)) throw new Error(`invalid_date_published: ${entry.date_published}`);
    if (!Number.isFinite(latestMs)) throw new Error(`invalid_date_published: ${latest}`);
    return entryMs > latestMs || (entryMs === latestMs && entry.date_published > latest)
      ? entry.date_published
      : latest;
  }, null) ?? snapshots.at(-1)?.captured_at ?? '1970-01-01T00:00:00Z';
  const body = entries.map((entry) => `  <entry>\n    <id>${xml(entry.url)}</id>\n    <title>${xml(entry.title)}</title>\n    <link href="${xml(entry.url)}"/>\n    <updated>${xml(entry.date_published)}</updated>\n    <category term="${entry.type}"/>\n    <category term="${entry.event_kind}"/>\n    <content type="text">${xml(entry.summary)}</content>\n  </entry>`).join('\n');
  return `<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">\n  <id>https://evidaxis.org/feed.atom</id>\n  <title>Evidaxis typed measurement feed</title>\n  <updated>${xml(updated)}</updated>\n  <link rel="self" href="https://evidaxis.org/feed.atom"/>\n  <link rel="alternate" href="https://evidaxis.org/"/>\n${body}\n</feed>\n`;
}
