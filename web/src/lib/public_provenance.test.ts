import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { describe, expect, it } from 'vitest';
import { publicProvenance } from './public_provenance';
import { snapshots, readSnapshotArtifactRaw } from './archive';
import { ownerTypes } from './data';
import { GET } from '../pages/snapshots/[date]/provenance.json';

describe('archived public provenance', () => {
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
      expect(projected.source_manifest.github_repo_refs).toHaveLength(source.source_manifest.github_repos.length);
      expect(projected.source_manifest).not.toHaveProperty('github_repos');
      expect(readSnapshotArtifactRaw(date, 'provenance.json')!.equals(raw)).toBe(true);
    }
  }, 20000);

  it('omits personal repository names, titles, authors and unknown capture fields', () => {
    const raw = Buffer.from(JSON.stringify({
      source_manifest: { github_repos: ['mensfeld/code-on-incus'], openalex_works: ['W1'] },
      author: 'mensfeld',
      openalex_raw: { e_TEST: { by_year: { '2026': 3 }, raw: {
        W1: { title: 'mensfeld', authors: ['mensfeld'], counts_by_year: [{ year: 2026, cited_by_count: 3 }] },
      } } },
    }));
    const projected = publicProvenance(raw, ownerTypes);
    expect(JSON.stringify(projected)).not.toContain('mensfeld');
    expect(projected.openalex_raw.e_TEST.raw.W1.counts_by_year).toEqual([{ year: 2026, cited_by_count: 3 }]);
    expect(() => publicProvenance(raw, { schema_version: 'owner_types_1', repos: {} })).toThrow(/classification/);
  });

  it('npm check-dist rejects a personal handle injected into an archived provenance fixture', () => {
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
      writeFileSync(path, JSON.stringify({ ...projected, injected: '\u006densfeld' }));
      const run = () => spawnSync('npm', ['run', 'check-dist'], {
        encoding: 'utf8', env: { ...process.env, EVIDAXIS_DIST: dist, EVIDAXIS_DATA_DIR: data },
      });
      const broken = run();
      expect(broken.error).toBeUndefined();
      expect(broken.status).toBe(1);
      expect(broken.stderr).toContain(`snapshots/${date}/provenance.json: contains private repository owner mensfeld`);
      // The minimal fixture omits site routes; isolate the privacy failure from those.
      writeFileSync(path, JSON.stringify(projected));
      const repaired = run();
      expect(repaired.stderr).not.toContain(`snapshots/${date}/provenance.json:`);
      expect(readFileSync(path, 'utf8')).not.toContain('mensfeld');
    } finally {
      rmSync(fixture, { recursive: true, force: true });
    }
  }, 20000);
});
