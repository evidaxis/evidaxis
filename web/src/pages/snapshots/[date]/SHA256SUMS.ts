import type { APIRoute } from 'astro';
import { snapshots } from '../../../lib/data';
import { hasSnapshotArtifact, readSnapshotArtifactRaw } from '../../../lib/archive';

export function getStaticPaths() {
  return snapshots
    .filter((snapshot) => hasSnapshotArtifact(snapshot.snapshot_date, 'SHA256SUMS'))
    .map((snapshot) => ({
      params: { date: snapshot.snapshot_date },
      props: { date: snapshot.snapshot_date },
    }));
}

export const GET: APIRoute = ({ props }) => {
  const { date } = props as { date: string };
  const raw = readSnapshotArtifactRaw(date, 'SHA256SUMS');
  if (!raw) return new Response('Not found', { status: 404 });
  // Frozen-byte pass-through; text/plain for auditors and curl pipelines.
  return new Response(raw, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
};
