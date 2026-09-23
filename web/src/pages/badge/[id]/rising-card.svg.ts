import type { APIRoute } from 'astro';
import { badgePaths, risingCardSvg, risingRecords } from '../../../lib/badges';

export const getStaticPaths = () => badgePaths(risingRecords);
export const GET: APIRoute = ({ props }) => new Response(risingCardSvg((props as any).record), {
  headers: { 'Content-Type': 'image/svg+xml; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
});
