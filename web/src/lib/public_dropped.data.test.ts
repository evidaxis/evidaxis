import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { expect, it } from 'vitest';
import { publicDropped } from './public_dropped';
import { hasSnapshotArtifact, readSnapshotArtifactRaw, snapshots } from './archive';
import { ownerTypes } from './data';
import { buildHandleIndex, handleHits } from './personFree.mjs';
import { GET } from '../pages/snapshots/[date]/dropped.json';

// Real personal handles come from the data at run time; none is written in this file.
const diskRegistry = JSON.parse(readFileSync(new URL('../../../etl/owner_types.json', import.meta.url), 'utf8'));
const userOwners: string[] = [];
for (const [key, entry] of Object.entries(diskRegistry.repos) as [string, { owner_type?: string; full_name?: string }][]) {
  if (entry?.owner_type !== 'User') continue;
  userOwners.push(key.split('/')[0]);
  if (typeof entry.full_name === 'string') userOwners.push(entry.full_name.split('/')[0]);
}
const userIndex = buildHandleIndex(userOwners);

// Invented login, checked absent from the owner registry before use.
const FAKE_OWNER = 'zzdroppedfixture';
const FAKE_REPO = `${FAKE_OWNER}/zznotarepo`;

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
it('check-dist rejects a raw dropped.json that still carries an invented User handle', () => {
  expect(JSON.stringify(diskRegistry).toLowerCase()).not.toContain(FAKE_OWNER);
  const fixture = mkdtempSync(join(tmpdir(), 'evx-archive-dropped-'));
  try {
    const dist = join(fixture, 'dist');
    const data = join(fixture, 'data');
    const date = '2026-09-26';
    const archive = join(dist, 'snapshots', date);
    mkdirSync(archive, { recursive: true });
    mkdirSync(join(data, 'snapshots'), { recursive: true });
    writeFileSync(join(data, 'latest.json'), JSON.stringify({ snapshot_date: date }));
    const path = join(archive, 'dropped.json');
    const raw = Buffer.from(JSON.stringify({
      v: 'dropped_1',
      snapshot_date: date,
      note: 'synthetic fixture',
      dropped: [{
        entity_id: 'e_FIXTURE',
        github_repo: FAKE_REPO,
        previously_tracked: true,
        reason: `no record for ${FAKE_REPO}`,
      }],
    }));
    writeFileSync(path, raw);
    const run = () => spawnSync(process.execPath, ['scripts/check-dist.mjs'], {
      encoding: 'utf8', env: { ...process.env, EVIDAXIS_DIST: dist, EVIDAXIS_DATA_DIR: data },
    });
    const broken = run();
    expect(broken.error).toBeUndefined();
    expect(broken.status).toBe(1);
    expect(broken.stderr).toContain(`snapshots/${date}/dropped.json: missing projection person_free_dropped_1`);
    expect(broken.stderr).toContain(`snapshots/${date}/dropped.json: contains github_repo`);
    expect(readFileSync(path, 'utf8').toLowerCase()).toContain(FAKE_OWNER);
    writeFileSync(path, JSON.stringify(publicDropped(raw, ownerTypes)));
    const repaired = run();
    expect(repaired.stderr).not.toContain(`snapshots/${date}/dropped.json:`);
    expect(readFileSync(path, 'utf8').toLowerCase()).not.toContain('"github_repo"');
    expect(readFileSync(path, 'utf8')).toContain('person_free_dropped_1');
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});
