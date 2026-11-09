import { createHash } from 'node:crypto';
import { expect, it } from 'vitest';
import { publicProvenance } from './public_provenance';
import { snapshots, readSnapshotArtifactRaw } from './archive';
import { ownerTypes } from './data';
import { GET } from '../pages/snapshots/[date]/provenance.json';

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
