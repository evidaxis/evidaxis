import type { APIRoute } from 'astro';
import { entities, snapshot } from '../../lib/data';
import { claimUrnForEntity } from '../../lib/claim_urn';

export function getStaticPaths() {
  return entities.map((e) => ({ params: { id: e.entity_id }, props: { e } }));
}

export const GET: APIRoute = ({ props }) => {
  const e = (props as any).e;
  const body = {
    entity: e,
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
  };
  return new Response(JSON.stringify(body, null, 2), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
