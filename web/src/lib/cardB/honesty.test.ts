import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { experimental_AstroContainer as AstroContainer } from 'astro/container';
import CardB from '../../components/cardB/CardB.astro';
import { GET } from '../../pages/e/[id].json';
import { archiveEntityById, entityUniverse, recordAvailability, snapshots, type RecordStatus } from '../archive';
import { ownerTypes, publicEntity, publicRepoUrl } from '../data';
import { REPO_ROOT } from '../data-path';
import { dependentReadings } from '../dependent-readings';
import { entityFeedEntries, latestFeedEntries, siteFeedEntries } from '../feed';
import { isIndexable } from './policy.mjs';
import { buildCardB } from './build';
import { assetRecords, contextFor } from './context';
import { historyCSV, systemAtom, systemFeed, valuesCSV } from './exports';

const statuses: RecordStatus[] = ['measured', 'observation_skipped', 'departure_confirmed', 'absence_unexplained'];
const twin = async (record: typeof entityUniverse[number]) => (await GET({ props: { record } } as any)).json();
const htmlFor = async (record: typeof entityUniverse[number]) => {
  const model = buildCardB(record, contextFor(record));
  const container = await AstroContainer.create();
  return container.renderToString(CardB, { props: { model, industry: record.entity.industry,
    industryLabel: record.entity.industry, subNiche: record.entity.sub_niche }, slots: { measurement: '<p>Measurement fixture</p>' } });
};

describe('honest observations across public formats', () => {
  it('uses the same dated state in Card B, JSON, CSV and both system feeds without changing indexability', async () => {
    const original = archiveEntityById.get('e_X33782S1M13')!;
    for (const status of statuses) {
      const record = { ...original, recordStatus: status };
      const model = buildCardB(record, contextFor(record)), json = await twin(record);
      const html = await htmlFor(record);
      expect(json.record_status).toBe(status);
      expect(json.observation).toEqual(model.availability);
      // Dates come from the record: the archive gains a snapshot every week.
      const seen = record.lastSeenSnapshot;
      expect(json.observation.message).toBe({
        measured: `Measured in snapshot ${seen}.`,
        observation_skipped: `Not measured in this snapshot: the weekly collection produced no record for this system (a declared gap). Last measured ${seen}. The next attempt is the next weekly snapshot.`,
        departure_confirmed: `Preserved historical record; record status: superseded; last measured ${seen}.`,
        absence_unexplained: `Not in the latest snapshot; last measured ${seen}.`,
      }[status]);
      expect(isIndexable(json)).toBe(true);
      expect(valuesCSV(model)).toContain(`,${status},${record.latestSnapshot},${record.lastSeenSnapshot}`);
      expect(historyCSV(model)).toContain(`,${status},${record.latestSnapshot},${record.lastSeenSnapshot}`);
      if (status !== 'measured') {
        expect(html).toContain(recordAvailability(record).message);
        expect(systemFeed(model).items.some(item => item.content_text === model.availability.message)).toBe(true);
        expect(systemAtom(model)).toContain(model.availability.message);
      }
      expect(html.includes('record status: superseded')).toBe(status === 'departure_confirmed');
    }
  });

  it('keeps weekly 21 and daily 0 separate with their dates, sources, scopes and scoring roles', async () => {
    // Pinned to the immutable 2026-10-17 snapshot, not the latest one, so next week's capture cannot move it.
    const snap = snapshots.find(s => s.snapshot_date === '2026-10-17')!;
    const record = { ...archiveEntityById.get('e_X33782S1M13')!, snapshot: snap,
      entity: snap.entities.find(e => e.entity_id === 'e_X33782S1M13')! };
    const model = buildCardB(record, contextFor(record));
    const weekly = model.readings.find(r => r.key === 'dependents')!, daily = model.readings.find(r => r.key === 'daily')!;
    expect(weekly).toMatchObject({ label: 'Weekly direct dependents', value: 21, date: '2026-09-28', role: 'weekly_axis_input',
      source: 'https://evidaxis.org/snapshots/2026-10-17/snapshot.json', verification: 'may_include_unverified' });
    expect(daily).toMatchObject({ label: 'Daily package dependents (unscored)', value: 0, role: 'unscored_context',
      source: 'https://api.deps.dev/v3alpha/systems/npm/packages/qwen-code', package_scope: 'npm/qwen-code', verification: 'identity_verified_pin' });
    expect(daily.date).toBe('2026-10-16');
    expect(weekly.definition).toContain('no_link');
    expect(weekly.definition).toContain('unverified');
    expect(daily.definition).toContain('never scored');
    const json = await twin(record);
    expect(json.dependent_readings).toEqual(model.dependents);
    const csv = valuesCSV(model);
    expect(csv).toContain('dependents,2026-09-28,21,packages');
    expect(csv).toContain('daily,2026-10-16,0,packages');
    const history = historyCSV(model).split('\r\n').filter(Boolean).at(-1)!;
    expect(history).toContain(',21,2026-09-28,0,');
    expect(history).toContain(',2026-10-16,https://api.deps.dev/');
    const html = await htmlFor(record);
    expect(html).toContain('weekly axis input; partition 2026-09-28');
    expect(html).toContain('captured 2026-10-16; package: npm/qwen-code');
    expect(html).toContain('no_link');
    const item = systemFeed(model).items.find(i => 'dependent_readings' in i._evidaxis)!;
    expect((item._evidaxis as any).dependent_readings.weekly.value).toBe(21);
    expect((item._evidaxis as any).dependent_readings.daily.value).toBe(0);
    expect(systemAtom(model)).toContain('partition 2026-09-28; weekly axis input');
    expect(systemAtom(model)).toContain('Daily package dependents (unscored): 0; captured 2026-10-16');
    expect(dependentReadings(record.entity, { ...record.snapshot, methodology_version: 'm3' }, null).weekly.definition).not.toContain('no_link');
    const olderRelease = assetRecords().find(r => r.snapshot.snapshot_date < archiveEntityById.get(r.entity.entity_id)!.lastSeenSnapshot)!;
    expect(buildCardB(olderRelease, contextFor(olderRelease)).availability).toEqual(recordAvailability(archiveEntityById.get(olderRelease.entity.entity_id)!));
  });

  it('retains threshold losses in individual feeds and entity JSON, with shared state for repeated declared gaps', async () => {
    const lost = latestFeedEntries().find(e => e.event_kind === 'axis_threshold_lost')!;
    expect(lost).toBeDefined();
    const record = archiveEntityById.get(lost.entity_ids[0])!, model = buildCardB(record, contextFor(record));
    expect(entityFeedEntries(record.entity.entity_id)).toContainEqual(lost);
    expect(systemFeed(model).items.some(i => i.id === lost.url)).toBe(true);
    expect(systemAtom(model)).toContain('no longer recorded');
    expect((await twin(record)).events).toContainEqual(lost);
    expect(siteFeedEntries().some(e => e.id === lost.id)).toBe(false);
    // Whichever system the latest snapshot skipped, its collection event carries the shared state.
    const event = latestFeedEntries().find(e => e.event_kind === 'collection_failed');
    if (event) {
      const gap = archiveEntityById.get(event.entity_ids[0])!;
      expect(event.state).toMatchObject({ record_status: gap.recordStatus, observation: recordAvailability(gap) });
    }
  });

  it('preserves pending owner masks and neutral-name masks in every observation state', async () => {
    const pending = JSON.parse(readFileSync(join(REPO_ROOT, 'etl/owner_transitions_pending.json'), 'utf8'));
    const neutral = entityUniverse.filter(r => r.entity.name === `System ${r.entity.entity_id}`);
    expect(neutral.length).toBeGreaterThan(0);
    const records = [...Object.keys(pending).map(repo => entityUniverse.find(r => r.entity.github_repo === repo)!),
      ...neutral];
    expect(records.every(Boolean)).toBe(true);
    for (const original of records) for (const status of statuses) {
      const record = { ...original, recordStatus: status }, entity = record.entity;
      const json = await twin(record), projected = publicEntity(entity);
      expect(json.entity).toMatchObject(projected.repository ? { repository: projected.repository, homepage: projected.homepage } : {});
      expect(json.entity).not.toHaveProperty('github_repo');
      const entry = ownerTypes.repos[entity.github_repo];
      expect(entry.owner_type).toBe('User');
      expect(JSON.stringify(json)).not.toContain(`github.com/${entry.full_name}`);
      expect(publicRepoUrl(entity)?.startsWith('https://github.com/')).not.toBe(true);
      expect(json.entity.name).toBe(original.entity.name);
    }
    const masked = { ...records[0], recordStatus: 'observation_skipped' as const };
    const html = await htmlFor(masked);
    expect(html).not.toContain(`github.com/${masked.entity.github_repo}`);
    expect(html).toContain(recordAvailability(masked).message);
  });
});
