import { describe, expect, it } from 'vitest';
import { enumerateSnapshots, snapshots, hasSnapshotArtifact, readSnapshotArtifactRaw } from './archive';
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
