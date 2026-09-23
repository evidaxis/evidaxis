import type { APIRoute } from 'astro';
import { badgePaths, rowSvg } from '../../../lib/badges';

export const getStaticPaths = () => badgePaths();
export const GET: APIRoute = ({ props }) => new Response(rowSvg((props as any).record, 'dependents', 'flat-square'), {
  headers: { 'Content-Type': 'image/svg+xml; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
});
