import { createHash } from 'node:crypto';
import type { OwnerTypes } from './person_free';

/** Publish measurements and opaque source identifiers, never arbitrary capture text.
 * The archive hash describes the original bytes, not this public projection.
 */
export function publicProvenance(raw: Buffer, registry: OwnerTypes) {
  const source = JSON.parse(raw.toString('utf8'));
  const papers = Object.fromEntries(Object.entries(source.openalex_raw ?? {}).map(([id, value]) => {
    const paper = value as any;
    return [id, {
      by_year: paper.by_year,
      raw: Object.fromEntries(Object.entries(paper.raw ?? {}).map(([work, value]) => [work, {
        counts_by_year: (value as any).counts_by_year,
      }])),
    }];
  }));
  return {
    projection: 'person_free_provenance_1',
    archive_sha256: createHash('sha256').update(raw).digest('hex'),
    snapshot_id: source.snapshot_id,
    methodology_version: source.methodology_version,
    fetcher_version: source.fetcher_version,
    captured_at: source.captured_at,
    manifest_hash: source.manifest_hash,
    source_manifest: {
      github_repo_refs: source.source_manifest.github_repos.map((repo: string) => {
        const entry = registry.repos[repo];
        if (!entry || !Number.isSafeInteger(entry.repo_id) || entry.repo_id <= 0) {
          throw new Error(`provenance repository classification unavailable: ${repo}`);
        }
        return `gh:${entry.repo_id}`;
      }),
      openalex_works: source.source_manifest.openalex_works,
    },
    github_weekly_raw: source.github_weekly_raw,
    openalex_raw: papers,
    provisional: source.provisional,
    spine_complete: source.spine_complete,
  };
}
