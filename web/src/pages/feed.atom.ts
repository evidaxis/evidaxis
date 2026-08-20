import type { APIRoute } from 'astro';
import { atomFeed } from '../lib/feed';

export const GET: APIRoute = () => new Response(atomFeed(), {
  headers: { 'Content-Type': 'application/atom+xml; charset=utf-8' },
});
