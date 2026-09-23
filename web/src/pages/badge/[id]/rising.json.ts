import type { APIRoute } from 'astro';
import { badgePaths, risingRecords, endpointJson } from '../../../lib/badges';

export const getStaticPaths = () => badgePaths(risingRecords);
export const GET: APIRoute = ({ props }) => new Response(JSON.stringify(endpointJson((props as any).record, 'rising')), {
  headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
});
