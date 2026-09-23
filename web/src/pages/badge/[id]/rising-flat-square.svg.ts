import type { APIRoute } from 'astro';
import { badgePaths, risingRecords, rowSvg } from '../../../lib/badges';

export const getStaticPaths = () => badgePaths(risingRecords);
export const GET: APIRoute = ({ props }) => new Response(rowSvg((props as any).record, 'rising', 'flat-square'), {
  headers: { 'Content-Type': 'image/svg+xml; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
});
