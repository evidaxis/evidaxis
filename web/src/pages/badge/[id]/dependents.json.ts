import type { APIRoute } from 'astro';
import { badgePaths, endpointJson } from '../../../lib/badges';

export const getStaticPaths = () => badgePaths();
export const GET: APIRoute = ({ props }) => new Response(JSON.stringify(endpointJson((props as any).record, 'dependents')), {
  headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
});
