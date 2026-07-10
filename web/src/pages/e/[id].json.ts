import type { APIRoute } from 'astro';
import { entityUniverse, publicEntity, publicHomepage, publicRepoUrl } from '../../lib/data';
import type { ArchivedEntity } from '../../lib/archive';
import { claimUrnForEntity } from '../../lib/claim_urn';

export function getStaticPaths() {
  return entityUniverse.map((record) => ({ params: { id: record.entity.entity_id }, props: { record } }));
}

export const GET: APIRoute = ({ props }) => {
  const record = (props as any).record as ArchivedEntity;
  const e = record.entity;
  const snapshot = record.snapshot;
  const repoUrl = publicRepoUrl(e);
  const homepage = publicHomepage(e);
  const body = {
    entity: publicEntity(e),
    record_status: record.recordStatus,
    last_seen_snapshot: record.lastSeenSnapshot,
    // Format-independent canonical reference (CLAIM-URN.md); cite this, not the URL.
    claim_urn: claimUrnForEntity(e, snapshot),
    score_receipt: {
      methodology_version: snapshot.methodology_version,
      snapshot_id: snapshot.snapshot_id,
      snapshot_date: snapshot.snapshot_date,
      period: snapshot.period,
      source: `https://evidaxis.org/snapshots/${snapshot.snapshot_date}/`,
    },
    license: 'CC0-1.0',
    canonical: `https://evidaxis.org/e/${e.entity_id}/`,
    sameAs: [
      ...new Set([repoUrl, homepage].filter((url): url is string => !!url)),
      ...(e.openalex_work_ids?.length ? [`https://openalex.org/${e.openalex_work_ids[0]}`] : []),
    ],
  };
  return new Response(JSON.stringify(body, null, 2), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
