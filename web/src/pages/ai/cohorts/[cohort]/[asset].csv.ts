import type { APIRoute } from 'astro';
import { assetRecords, cardBFor } from '../../../../lib/cardB/context';
import { cohortCSV } from '../../../../lib/cardB/exports';
export function getStaticPaths() {
  const unique = new Map();
  for (const record of assetRecords()) unique.set(`${record.entity.sub_niche}:${record.snapshot.snapshot_id}`, record);
  return [...unique.values()].map(record => ({ params: { cohort: record.entity.sub_niche, asset: `values-${record.snapshot.snapshot_id}-b1` }, props: { record } }));
}
export const GET: APIRoute = ({ props }) => new Response(cohortCSV(cardBFor(props.record)), { headers: { 'Content-Type': 'text/csv; charset=utf-8' } });
