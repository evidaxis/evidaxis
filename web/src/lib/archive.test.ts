import { describe, expect, it } from 'vitest';
import {
  buildEntityUniverse, enumerateSnapshots, hasSnapshotArtifact, readSnapshotArtifactRaw, snapshots,
} from './archive';

const entity = (entity_id: string, name: string): any => ({ entity_id, name });
const snap = (snapshot_date: string, entities: any[]): any => ({ snapshot_date, entities });

describe('archive enumeration', () => {
  it('finds every real dated snapshot and sorts them chronologically', () => {
    expect(enumerateSnapshots()).toEqual(snapshots);
    expect(snapshots.length).toBeGreaterThanOrEqual(4);
    expect(snapshots.map((s) => s.snapshot_date)).toEqual(
      [...snapshots.map((s) => s.snapshot_date)].sort(),
    );
    expect(snapshots.every((s) => /^\d{4}-\d{2}-\d{2}$/.test(s.snapshot_date))).toBe(true);
  });
});

describe('verification artifacts (WP-H)', () => {
  it('every snapshot has the required frozen verification files', () => {
    for (const s of snapshots) {
      for (const name of ['manifest.json', 'provenance.json', 'SHA256SUMS'] as const) {
        expect(hasSnapshotArtifact(s.snapshot_date, name)).toBe(true);
        const raw = readSnapshotArtifactRaw(s.snapshot_date, name);
        expect(raw).not.toBeNull();
        expect(raw!.byteLength).toBeGreaterThan(0);
      }
    }
  });

  it('dropped.json is optional (absent on genesis, present later)', () => {
    expect(hasSnapshotArtifact('2026-06-27', 'dropped.json')).toBe(false);
    expect(hasSnapshotArtifact('2026-07-10', 'dropped.json')).toBe(true);
  });
});

describe('entity universe', () => {
  const old = snap('2026-07-03', [entity('e_OLDOLDOLD01', 'Old v1'), entity('e_SHARED00001', 'Shared v1')]);
  const latest = snap('2026-07-04', [entity('e_SHARED00001', 'Shared v2'), entity('e_CURRENT0001', 'Current')]);
  const universe = buildEntityUniverse([latest, old], latest.snapshot_date);

  it('preserves an old-only entity with its last-seen snapshot and superseded status', () => {
    const record = universe.find((r) => r.entity.entity_id === 'e_OLDOLDOLD01')!;
    expect(record.entity.name).toBe('Old v1');
    expect(record.firstSeenSnapshot).toBe('2026-07-03');
    expect(record.lastSeenSnapshot).toBe('2026-07-03');
    expect(record.snapshot).toBe(old);
    expect(record.recordStatus).toBe('superseded');
  });

  it('uses the latest complete record, marks it current, and does not duplicate IDs', () => {
    const record = universe.find((r) => r.entity.entity_id === 'e_SHARED00001')!;
    expect(record.entity.name).toBe('Shared v2');
    expect(record.firstSeenSnapshot).toBe('2026-07-03');
    expect(record.lastSeenSnapshot).toBe('2026-07-04');
    expect(record.recordStatus).toBe('current');
    expect(universe.filter((r) => r.entity.entity_id === 'e_SHARED00001')).toHaveLength(1);
  });
});
