import type { APIRoute } from 'astro';
import { snapshots } from '../../../lib/data';
import { hasSnapshotArtifact, readSnapshotArtifactRaw } from '../../../lib/archive';
import { publicProvenance } from '../../../lib/public_provenance';
import { ownerTypes } from '../../../lib/data';

export function getStaticPaths() {
  return snapshots
    .filter((snapshot) => hasSnapshotArtifact(snapshot.snapshot_date, 'provenance.json'))
    .map((snapshot) => ({
      params: { date: snapshot.snapshot_date },
      props: { date: snapshot.snapshot_date },
    }));
}

export const GET: APIRoute = ({ props }) => {
  const { date } = props as { date: string };
  const raw = readSnapshotArtifactRaw(date, 'provenance.json');
  if (!raw) return new Response('Not found', { status: 404 });
  return new Response(JSON.stringify(publicProvenance(raw, ownerTypes)), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
