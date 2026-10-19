import type { APIRoute } from 'astro';
import { ownerTypes, snapshots } from '../../../lib/data';
import { hasSnapshotArtifact, readSnapshotArtifactRaw } from '../../../lib/archive';
import { publicDropped } from '../../../lib/public_dropped';

/** Optional artifact: only emit routes for snapshots that shipped dropped.json. */
export function getStaticPaths() {
  return snapshots
    .filter((snapshot) => hasSnapshotArtifact(snapshot.snapshot_date, 'dropped.json'))
    .map((snapshot) => ({
      params: { date: snapshot.snapshot_date },
      props: { date: snapshot.snapshot_date },
    }));
}

export const GET: APIRoute = ({ props }) => {
  const { date } = props as { date: string };
  const raw = readSnapshotArtifactRaw(date, 'dropped.json');
  if (!raw) return new Response('Not found', { status: 404 });
  return new Response(JSON.stringify(publicDropped(raw, ownerTypes)), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
