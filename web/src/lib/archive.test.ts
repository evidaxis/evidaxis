import { describe, expect, it } from 'vitest';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  buildEntityUniverse, hasSnapshotArtifact, readSnapshotArtifactRaw, snapshots,
  observationEvidence, observationStatus, recordAvailability,
} from './archive';

const entity = (entity_id: string, name: string): any => ({ entity_id, name });
const snap = (snapshot_date: string, entities: any[]): any => ({ snapshot_date, entities });

describe('verification artifacts (WP-H)', () => {
  it('dropped.json is optional (absent on genesis, present later)', () => {
    expect(hasSnapshotArtifact('2026-06-27', 'dropped.json')).toBe(false);
    expect(hasSnapshotArtifact('2026-07-10', 'dropped.json')).toBe(true);
  });
});

describe('entity universe', () => {
  const old = snap('2026-07-03', [entity('e_OLDOLDOLD01', 'Old v1'), entity('e_SHARED00001', 'Shared v1')]);
  const latest = snap('2026-07-04', [entity('e_SHARED00001', 'Shared v2'), entity('e_CURRENT0001', 'Current')]);
  const universe = buildEntityUniverse([latest, old], latest.snapshot_date);

  it('preserves an unexplained absence with its last measured values and date', () => {
    const record = universe.find((r) => r.entity.entity_id === 'e_OLDOLDOLD01')!;
    expect(record.entity.name).toBe('Old v1');
    expect(record.firstSeenSnapshot).toBe('2026-07-03');
    expect(record.lastSeenSnapshot).toBe('2026-07-03');
    expect(record.snapshot).toBe(old);
    expect(record.recordStatus).toBe('absence_unexplained');
    expect(recordAvailability(record).message).toBe('Not in the latest snapshot; last measured 2026-07-03.');
  });

  it('uses the latest complete record, marks it current, and does not duplicate IDs', () => {
    const record = universe.find((r) => r.entity.entity_id === 'e_SHARED00001')!;
    expect(record.entity.name).toBe('Shared v2');
    expect(record.firstSeenSnapshot).toBe('2026-07-03');
    expect(record.lastSeenSnapshot).toBe('2026-07-04');
    expect(record.recordStatus).toBe('measured');
    expect(universe.filter((r) => r.entity.entity_id === 'e_SHARED00001')).toHaveLength(1);
  });
});

describe('evidence-based observation states', () => {
  it('distinguishes all four states, keeps departures until measured again, and ignores future snapshots', () => {
    const old = snap('2026-10-03', ['current', 'gap', 'gone', 'renamed', 'unknown', 'returned'].map(id => entity(id, id)));
    const current = snap('2026-10-17', [entity('current', 'Current'), entity('returned', 'Returned')]);
    const evidence = { declaredGaps: new Set(['gap']), departures: [
      { entity_id: 'gone', reason: 'gone', date: '2026-10-10' },
      { entity_id: 'renamed', reason: 'repo_id_changed', date: '2026-10-10' },
      { entity_id: 'returned', reason: 'gone', date: '2026-10-10' },
    ] };
    const universe = buildEntityUniverse([old, current, snap('2026-10-24', [entity('unknown', 'Future')])], current.snapshot_date, evidence);
    expect(Object.fromEntries(universe.map(r => [r.entity.entity_id, r.recordStatus]))).toEqual({
      current: 'measured', gap: 'observation_skipped', gone: 'departure_confirmed', renamed: 'departure_confirmed', unknown: 'absence_unexplained', returned: 'measured',
    });
    for (const record of universe) {
      expect(record.snapshot.snapshot_date).toBe(record.lastSeenSnapshot);
      expect(recordAvailability(record).message.includes('superseded')).toBe(record.recordStatus === 'departure_confirmed');
    }
  });

  it('reads declared gaps and both departure filenames, excludes unsupported reasons and future evidence', () => {
    const root = mkdtempSync(join(tmpdir(), 'honesty-states-'));
    const put = (path: string, body: object) => { const full = join(root, 'data', path); mkdirSync(join(full, '..'), { recursive: true }); writeFileSync(full, JSON.stringify(body)); };
    try {
      put('snapshots/2026-10-17/dropped.json', { dropped: [
        { entity_id: 'gap', reason: 'A DECLARED gap, not a silent drop.' }, { entity_id: 'other', reason: 'unknown' },
      ] });
      put('observations/2026-10-10/seed-departures.json', { departures: [
        { github_repo: 'org/gone', reason: 'gone' }, { entity_id: 'uncertain', reason: 'timeout' },
      ] });
      put('observations/2026-10-17/departed.json', { departed: [{ entity_id: 'renamed', reason: 'repo_id_changed' }] });
      put('observations/2026-10-24/seed-departures.json', { departures: [{ entity_id: 'future', reason: 'gone' }] });
      const evidence = observationEvidence('2026-10-17', root);
      expect([...evidence.declaredGaps]).toEqual(['gap']);
      expect(evidence.departures).toHaveLength(2);
      expect(observationStatus({ ...entity('gone', 'Gone'), github_repo: 'Org/Gone' }, '2026-10-03', '2026-10-17', evidence)).toBe('departure_confirmed');
      expect(observationStatus(entity('unrelated', 'Other'), '2026-10-03', '2026-10-17', evidence)).toBe('absence_unexplained');
      expect(observationStatus(entity('renamed', 'Renamed'), '2026-10-03', '2026-10-17', evidence)).toBe('departure_confirmed');
      expect(observationStatus(entity('future', 'Future'), '2026-10-03', '2026-10-17', evidence)).toBe('absence_unexplained');
    } finally { rmSync(root, { recursive: true, force: true }); }
  });

  it.each(['2026-10-10', '2026-10-17'])('never retires any declared gap in the real %s snapshot', (date) => {
    const evidence = observationEvidence(date);
    const rows = JSON.parse(readSnapshotArtifactRaw(date, 'dropped.json')!.toString()).dropped;
    expect(rows.length).toBeGreaterThan(0);
    const universe = buildEntityUniverse(snapshots, date, evidence);
    for (const row of rows) {
      expect(observationStatus(row, null, date, evidence)).toBe('observation_skipped');
      const record = universe.find(r => r.entity.entity_id === row.entity_id);
      if (record) {
        expect(record.recordStatus).toBe('observation_skipped');
        expect(recordAvailability(record).message).not.toContain('superseded');
      }
    }
    for (const id of ['e_EY620A0EAK9', 'e_TEXN6TK2CRK']) {
      const record = universe.find(r => r.entity.entity_id === id)!;
      expect(record).toBeDefined();
      expect(record.recordStatus).not.toBe('departure_confirmed');
    }
  });
});

describe('legacy collection-gap evidence', () => {
  it('counts every 2026-07-01 dropped row as a declared gap, though its reason names 202-exhaustion', () => {
    const rows = JSON.parse(readSnapshotArtifactRaw('2026-07-01', 'dropped.json')!.toString('utf8')).dropped as { entity_id: string }[];
    expect(rows.length).toBeGreaterThan(0);
    const gaps = observationEvidence('2026-07-01').declaredGaps;
    for (const row of rows) expect(gaps.has(row.entity_id)).toBe(true);
  });
});
