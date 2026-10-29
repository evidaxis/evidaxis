import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { expect, it } from 'vitest';
import { publicProvenance } from './public_provenance';
import { snapshots, readSnapshotArtifactRaw } from './archive';
import { ownerTypes } from './data';
import handles from '../data/person-free-handles.json';
import { GET } from '../pages/snapshots/[date]/provenance.json';

// Real personal handles come from the data at run time; none is written in this file.
const [userRepo] = Object.entries(ownerTypes.repos).find(([, entry]) => entry.owner_type === 'User')!;
const userLogin = userRepo.split('/')[0];
const bannedHandle = (handles as string[])[0];

it('projects every actual archive without rewriting raw bytes or losing measurements', async () => {
  for (const snapshot of snapshots) {
    const date = snapshot.snapshot_date;
    const raw = readSnapshotArtifactRaw(date, 'provenance.json')!;
    const source = JSON.parse(raw.toString());
    const response = await GET({ props: { date } } as any);
    const projected = await response.json();
    expect(projected).toEqual(publicProvenance(raw, ownerTypes));
    expect(projected.archive_sha256).toBe(createHash('sha256').update(raw).digest('hex'));
    expect(projected.github_weekly_raw).toEqual(source.github_weekly_raw);
    for (const [id, paper] of Object.entries(source.openalex_raw) as [string, any][]) {
      expect(projected.openalex_raw[id].by_year).toEqual(paper.by_year);
      for (const [work, capture] of Object.entries(paper.raw) as [string, any][]) {
        expect(projected.openalex_raw[id].raw[work]).toEqual({ counts_by_year: capture.counts_by_year });
      }
    }
    expect(projected.source_manifest.github_repo_refs).toHaveLength(source.source_manifest.github_repos.length);
    expect(projected.source_manifest).not.toHaveProperty('github_repos');
    expect(readSnapshotArtifactRaw(date, 'provenance.json')!.equals(raw)).toBe(true);
  }
});
it.each([['ban-list handle', bannedHandle], ['registry personal owner', userLogin]])(
  'check-dist rejects a %s in archived provenance', (_kind, owner) => {
    const fixture = mkdtempSync(join(tmpdir(), 'evx-archive-provenance-'));
    try {
      const dist = join(fixture, 'dist');
      const data = join(fixture, 'data');
      const date = '2026-09-26';
      const archive = join(dist, 'snapshots', date);
      mkdirSync(archive, { recursive: true });
      mkdirSync(join(data, 'snapshots'), { recursive: true });
      writeFileSync(join(data, 'latest.json'), JSON.stringify({ snapshot_date: date }));
      const path = join(archive, 'provenance.json');
      const raw = readSnapshotArtifactRaw(date, 'provenance.json')!;
      const projected = publicProvenance(raw, ownerTypes);
      writeFileSync(path, JSON.stringify({ ...projected, injected: owner }));
      const run = () => spawnSync(process.execPath, ['scripts/check-dist.mjs'], {
        encoding: 'utf8', env: { ...process.env, EVIDAXIS_DIST: dist, EVIDAXIS_DATA_DIR: data },
      });
      const broken = run();
      expect(broken.error).toBeUndefined();
      expect(broken.status).toBe(1);
      expect(broken.stderr).toContain(`snapshots/${date}/provenance.json: contains private repository owner ${owner.toLowerCase()}`);
      // The minimal fixture omits site routes; isolate the privacy failure from those.
      writeFileSync(path, JSON.stringify(projected));
      const repaired = run();
      expect(repaired.stderr).not.toContain(`snapshots/${date}/provenance.json:`);
      expect(readFileSync(path, 'utf8').toLowerCase()).not.toContain(owner.toLowerCase());
    } finally {
      rmSync(fixture, { recursive: true, force: true });
    }
  },
);
