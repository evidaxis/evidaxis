import { describe, expect, it } from 'vitest';
import { atomFeed, diffFeedEntries, entryId, jsonFeed } from './feed';
import { CITATION_AXIS, DEVELOPMENT_AXIS, deriveMeasurementState } from './measurement';

function entity(id: string, axes: string[], rising = false): any {
  return {
    entity_id: id, name: `System ${id}`, cohort: 'fixture', incumbent: false,
    openalex_work_ids: axes.includes(CITATION_AXIS) ? ['W1'] : [], axes_present: axes,
    convergent_axes: rising ? [DEVELOPMENT_AXIS, CITATION_AXIS] : [], rising,
    axes: {
      github_commit_velocity: { slope: 0.2, cohort_z: 1.2, recent_weekly_commits: 8 },
      openalex_citation_momentum: axes.includes(CITATION_AXIS)
        ? { status: 'present', slope: 0.3, cohort_z: 1.3 }
        : { status: 'absent', slope: null, cohort_z: null },
    },
  };
}

function snap(date: string, period: string, entities: any[]): any {
  return { snapshot_date: date, period, captured_at: `${date}T08:00:00Z`, methodology_version: 'm2', entities };
}

describe('typed feeds and immutable signal ids', () => {
  it('emits moment_signal only for two-axis convergence and keeps ids deterministic', () => {
    const previous = snap('2026-08-08', '2026-w32', Array.from({ length: 5 }, (_, i) => entity(`e_${i}`, [DEVELOPMENT_AXIS, CITATION_AXIS])));
    const currentEntities = Array.from({ length: 5 }, (_, i) => entity(`e_${i}`, [DEVELOPMENT_AXIS, CITATION_AXIS], i === 0));
    const current = snap('2026-08-15', '2026-w33', currentEntities);
    const counts = new Map(currentEntities.map((candidate) => [candidate.entity_id, 4]));
    const resolve = (candidate: any, snapshot: any) => deriveMeasurementState(candidate, snapshot, counts.get(candidate.entity_id) ?? 4);
    const first = diffFeedEntries(previous, current, { resolveState: resolve, dropped: new Set() });
    const second = diffFeedEntries(previous, current, { resolveState: resolve, dropped: new Set() });
    expect(first.map((entry) => entry.id)).toEqual(second.map((entry) => entry.id));
    expect(first.filter((entry) => entry.type === 'moment_signal')).toHaveLength(1);
    expect(first.find((entry) => entry.type === 'moment_signal')?.entity_ids).toEqual(['e_0']);
  });

  it('emits one aggregate record for a quiet week', () => {
    const entities = Array.from({ length: 5 }, (_, i) => entity(`e_${i}`, [DEVELOPMENT_AXIS]));
    const previous = snap('2026-08-08', '2026-w32', entities);
    const current = snap('2026-08-15', '2026-w33', entities);
    const resolve = (candidate: any, snapshot: any) => deriveMeasurementState(candidate, snapshot, 4);
    const entries = diffFeedEntries(previous, current, { resolveState: resolve, dropped: new Set() });
    expect(entries).toHaveLength(1);
    expect(entries[0].event_kind).toBe('quiet_week');
  });

  it('uses the canonical gate phrase in typed state, JSON Feed, and Atom', () => {
    const currentEntities = Array.from({ length: 5 }, (_, i) => entity(`e_${i}`, [DEVELOPMENT_AXIS]));
    const previous = snap('2026-08-08', '2026-w32', [entity('e_prior', [DEVELOPMENT_AXIS])]);
    const current = snap('2026-08-15', '2026-w33', currentEntities);
    const resolve = (candidate: any, snapshot: any) => deriveMeasurementState(candidate, snapshot, 4);
    const entries = diffFeedEntries(previous, current, { resolveState: resolve, dropped: new Set() });
    const gate = 'Gate: not computable — 1 of 2 axes measurable (unmeasured)';
    const gateSentence = `${gate}.`;
    expect(entries).toHaveLength(5);
    expect(entries.every((entry: any) => entry.state.phrases.gate === gate && entry.summary.endsWith(gateSentence))).toBe(true);

    const json = jsonFeed(entries);
    expect(json.items.every((item) => item.content_text.endsWith(gateSentence))).toBe(true);
    expect(atomFeed(entries)).toContain(gate);
  });

  it('serializes valid JSON Feed and Atom structures', () => {
    const body = jsonFeed([]);
    expect(body.version).toBe('https://jsonfeed.org/version/1.1');
    expect(body.items).toEqual([]);
    const atom = atomFeed([]);
    expect(atom).toMatch(/^<\?xml version="1\.0"/);
    expect(atom).toContain('<feed xmlns="http://www.w3.org/2005/Atom">');
    expect(atom.trimEnd().endsWith('</feed>')).toBe(true);
  });

  it('hashes only the fixed canonical identity fields, with snapshot date included', () => {
    const payload: any = {
      schema_version: 'typed_feed_entry_1', type: 'observation', event_kind: 'quiet_week',
      title: 'Quiet', summary: 'Quiet.', snapshot_date: '2026-08-15', period: '2026-w33',
      date_published: '2026-08-15T08:00:00Z', cohort: null, entity_ids: ['e_b', 'e_a'],
      source_fields: ['/one'], state: { volatile: 1 },
    };
    const first = entryId(payload);
    expect(entryId({ ...payload, state: { volatile: 2 }, source_fields: ['/two'], date_published: '2026-08-16T00:00:00Z' }))
      .toBe(first);
    expect(entryId({ ...payload, entity_ids: ['e_a', 'e_b'] })).toBe(first);
    expect(entryId({ ...payload, snapshot_date: '2026-08-16' })).not.toBe(first);
  });

  it('suppresses diffs when the previous baseline is empty', () => {
    const current = snap('2026-08-15', '2026-w33', Array.from({ length: 5 }, (_, i) => entity(`e_${i}`, [DEVELOPMENT_AXIS])));
    const entries = diffFeedEntries(snap('2026-08-08', '2026-w32', []), current, { dropped: new Set() });
    expect(entries).toHaveLength(1);
    expect(entries[0].event_kind).toBe('baseline_unavailable');
    expect(entries.some((entry) => entry.event_kind === 'measurement_resumed')).toBe(false);
  });

  it('fails closed on undefined inputs and an empty current snapshot', () => {
    const previous = snap('2026-08-08', '2026-w32', [entity('e_1', [DEVELOPMENT_AXIS])]);
    expect(() => diffFeedEntries(undefined, previous)).toThrow('snapshot_diff_input_undefined');
    expect(() => diffFeedEntries(previous, snap('2026-08-15', '2026-w33', []))).toThrow('current_snapshot_empty');
  });

  it('excludes dropped rows from normal events and emits only collection_failed', () => {
    const priorEntity = entity('e_drop', [DEVELOPMENT_AXIS]);
    const previous = snap('2026-08-08', '2026-w32', [priorEntity]);
    const current = snap('2026-08-15', '2026-w33', [{ ...priorEntity, convergent_axes: [DEVELOPMENT_AXIS] }]);
    const resolve = (candidate: any, snapshot: any) => deriveMeasurementState(candidate, snapshot, 4);
    const entries = diffFeedEntries(previous, current, { resolveState: resolve, dropped: new Set(['e_drop']) });
    expect(entries.map((entry) => entry.event_kind)).toEqual(['collection_failed']);
  });

  it('records threshold loss in feed without publishing a moment', () => {
    const priorEntity = { ...entity('e_1', [DEVELOPMENT_AXIS]), convergent_axes: [DEVELOPMENT_AXIS] };
    const currentEntity = entity('e_1', [DEVELOPMENT_AXIS]);
    const resolve = (candidate: any, snapshot: any) => deriveMeasurementState(candidate, snapshot, 4);
    const entries = diffFeedEntries(
      snap('2026-08-08', '2026-w32', [priorEntity]),
      snap('2026-08-15', '2026-w33', [currentEntity]),
      { resolveState: resolve, dropped: new Set() },
    );
    expect(entries.map((entry) => entry.event_kind)).toContain('axis_threshold_lost');
    expect(entries.some((entry) => entry.type === 'moment_signal')).toBe(false);
  });

  it('uses reference baseline events for incumbents and never publishes their convergence', () => {
    const peers = Array.from({ length: 4 }, (_, i) => entity(`e_peer_${i}`, [DEVELOPMENT_AXIS, CITATION_AXIS]));
    const incumbent = { ...entity('e_ref', [DEVELOPMENT_AXIS, CITATION_AXIS], true), incumbent: true };
    const previous = snap('2026-08-08', '2026-w32', peers);
    const current = snap('2026-08-15', '2026-w33', [...peers, incumbent]);
    const resolve = (candidate: any, snapshot: any) => deriveMeasurementState(candidate, snapshot, 4);
    const entries = diffFeedEntries(previous, current, { resolveState: resolve, dropped: new Set() });
    expect(entries.find((entry) => entry.entity_ids.includes('e_ref'))?.event_kind).toBe('reference_baseline_added');
    expect(entries.some((entry) => entry.event_kind === 'convergence_published' && entry.entity_ids.includes('e_ref'))).toBe(false);
  });

  it('uses the maximum publication date for Atom updated', () => {
    const base: any = {
      schema_version: 'typed_feed_entry_1', id: 'one', url: 'https://evidaxis.org/signals/one/',
      type: 'observation', event_kind: 'quiet_week', title: 'One', summary: 'One.',
      snapshot_date: '2026-08-15', period: '2026-w33', cohort: null, entity_ids: [], source_fields: [], state: {},
    };
    const atom = atomFeed([
      { ...base, date_published: '2026-08-15T08:00:00Z' },
      { ...base, id: 'two', url: 'https://evidaxis.org/signals/two/', date_published: '2026-08-16T08:00:00Z' },
    ]);
    expect(atom).toContain('<updated>2026-08-16T08:00:00Z</updated>');
  });
});
