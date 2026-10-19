import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { describe, expect, it } from 'vitest';
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

const userPairs = Object.entries(ownerTypes.repos).filter(([, entry]) => entry.owner_type === 'User');
const [userKey, userEntry] = userPairs.find(([key, entry]) => entry.full_name.toLowerCase() !== key.toLowerCase()) ?? userPairs[0];
const [orgKey] = Object.entries(ownerTypes.repos).find(([, entry]) => entry.owner_type === 'Organization')!;

// Invented login, checked absent from the owner registry before use.
const FAKE_OWNER = 'zzdroppedfixture';
const FAKE_REPO = `${FAKE_OWNER}/zznotarepo`;

function leaksLogin(text: string, login: string): boolean {
  const body = login.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`(?<![A-Za-z0-9-])${body}(?![A-Za-z0-9-])`, 'i').test(text);
}

describe('archived public dropped lists', () => {
  it('replaces a User-type repository in github_repo and in reason text', () => {
    const owners = [userKey.split('/')[0], userEntry.full_name.split('/')[0]];
    const raw = Buffer.from(JSON.stringify({
      v: 'dropped_1',
      snapshot_date: '2026-01-01',
      checked_at: '2026-01-01T00:00:00Z',
      seeded: 2,
      in_snapshot: 0,
      drop_fraction: 1,
      max_drop_fraction: 0.15,
      note: `see https://github.com/${userKey}.git and ${userEntry.full_name}; organization ${orgKey} stays`,
      extra_top: owners[0],
      dropped: [{
        entity_id: 'e_TEST',
        github_repo: userKey,
        previously_tracked: true,
        reason: `missing ${userKey} at https://github.com/${userEntry.full_name} and ${userEntry.full_name}.git`,
        extra_row: owners[0],
      }],
    }));
    const projected = publicDropped(raw, ownerTypes) as any;
    expect(projected.projection).toBe('person_free_dropped_1');
    expect(projected.archive_sha256).toBe(createHash('sha256').update(raw).digest('hex'));
    expect(projected.dropped).toHaveLength(1);
    expect(projected.dropped[0].repo_ref).toBe(`gh:${userEntry.repo_id}`);
    expect(projected.dropped[0].entity_id).toBe('e_TEST');
    expect(projected.dropped[0].previously_tracked).toBe(true);
    expect(projected.dropped[0]).not.toHaveProperty('github_repo');
    expect(projected.dropped[0]).not.toHaveProperty('extra_row');
    expect(projected).not.toHaveProperty('extra_top');
    expect(projected.note).toContain(orgKey);
    const text = JSON.stringify(projected);
    for (const login of owners) {
      expect(leaksLogin(text, login)).toBe(false);
      expect(text.toLowerCase()).not.toContain(`${login.toLowerCase()}/`);
    }
    expect(text).not.toContain(userKey);
    expect(text).not.toContain(userEntry.full_name);
    expect(projected.dropped[0].reason).toContain(`gh:${userEntry.repo_id}`);
    expect(projected.note).toContain(`gh:${userEntry.repo_id}`);
  });

  it('publishes an unclassified repository as gh:unclassified and does not throw', () => {
    const known = JSON.stringify(diskRegistry).toLowerCase();
    expect(known).not.toContain(FAKE_OWNER);
    const raw = Buffer.from(JSON.stringify({
      v: 'dropped_1',
      dropped: [{ entity_id: 'e_X', github_repo: FAKE_REPO, previously_tracked: false, reason: 'absent' }],
    }));
    expect(() => publicDropped(raw, ownerTypes)).not.toThrow();
    expect((publicDropped(raw, ownerTypes) as any).dropped[0].repo_ref).toBe('gh:unclassified');
    const empty = publicDropped(raw, { schema_version: 'owner_types_1', repos: {} }) as any;
    expect(empty.dropped[0].repo_ref).toBe('gh:unclassified');
    expect(empty.dropped[0].reason).toBe('absent');
  });

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
});
