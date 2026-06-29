import type { APIRoute } from 'astro';
import { snapshot, SNAP_DATE } from '../../../lib/data';

export function getStaticPaths() {
  return [{ params: { date: SNAP_DATE } }];
}

export const GET: APIRoute = () =>
  new Response(JSON.stringify(snapshot, null, 2), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
