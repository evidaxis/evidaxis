import type { APIRoute } from 'astro';
import { assetRecords, bRecords, cardBFor } from '../../../lib/cardB/context';
import { valuesCSV, historyCSV, systemFeed, systemAtom } from '../../../lib/cardB/exports';
import type { ArchivedEntity } from '../../../lib/archive';

export function getStaticPaths() {
  return [
    ...assetRecords().flatMap(record => ['values', 'history'].map(kind => ({
      params: { id: record.entity.entity_id, asset: `${kind}-${record.snapshot.snapshot_id}-b1.csv` }, props: { record, kind },
    }))),
    ...bRecords.flatMap(record => ['atom', 'json'].map(kind => ({ params: { id: record.entity.entity_id, asset: `feed.${kind}` }, props: { record, kind } }))),
  ];
}
export const GET: APIRoute = ({ props }) => {
  const { record, kind } = props as { record: ArchivedEntity; kind: string };
  const m = cardBFor(record);
  const content = kind === 'values' ? valuesCSV(m) : kind === 'history' ? historyCSV(m) : kind === 'atom' ? systemAtom(m) : JSON.stringify(systemFeed(m), null, 2);
  return new Response(content, { headers: {
    'Content-Type': kind === 'atom' ? 'application/atom+xml; charset=utf-8' : kind === 'json' ? 'application/feed+json; charset=utf-8' : 'text/csv; charset=utf-8',
    ...(kind === 'atom' || kind === 'json' ? { 'X-Robots-Tag': 'noindex' } : {}), // boldness-ok: feed headers explicitly required by the Card B contract.
  } });
};
