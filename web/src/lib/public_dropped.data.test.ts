import { createHash } from 'node:crypto';
import { expect, it } from 'vitest';
import { publicDropped } from './public_dropped';
import { hasSnapshotArtifact, readSnapshotArtifactRaw, snapshots } from './archive';
import { ownerTypes } from './data';
import { handleHits } from './personFree.mjs';
import { userHandleIndex } from './person_free';
import { GET } from '../pages/snapshots/[date]/dropped.json';

// Real personal handles come from the data at run time; none is written in this file.
const userIndex = userHandleIndex(ownerTypes);

it('projects every actual archive without a User-type owner handle', async () => {
  const dates = snapshots.filter((snapshot) => hasSnapshotArtifact(snapshot.snapshot_date, 'dropped.json'));
  expect(dates.length).toBeGreaterThan(0);
  for (const snapshot of dates) {
    const date = snapshot.snapshot_date;
    const raw = readSnapshotArtifactRaw(date, 'dropped.json')!;
    const response = await GET({ props: { date } } as any);
    const projected = await response.json();
    expect(projected).toEqual(publicDropped(raw, ownerTypes));
    expect(projected.projection).toBe('person_free_dropped_1');
    expect(projected.archive_sha256).toBe(createHash('sha256').update(raw).digest('hex'));
    expect(JSON.stringify(projected)).not.toContain('"github_repo"');
    expect(handleHits(JSON.stringify(projected), userIndex)).toEqual([]);
    expect(readSnapshotArtifactRaw(date, 'dropped.json')!.equals(raw)).toBe(true);
  }
});
