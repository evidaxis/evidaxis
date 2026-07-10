import type { APIRoute } from 'astro';
import { snapshots } from '../../../lib/data';

export function getStaticPaths() {
  return snapshots.map((snapshot) => ({
    params: { date: snapshot.snapshot_date },
    props: { snapshot },
  }));
}

export const GET: APIRoute = ({ props }) =>
  new Response(JSON.stringify((props as any).snapshot, null, 2), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
