import type { APIRoute } from 'astro';
import { jsonFeed } from '../lib/feed';

export const GET: APIRoute = () => new Response(`${JSON.stringify(jsonFeed(), null, 2)}\n`, {
  headers: { 'Content-Type': 'application/feed+json; charset=utf-8' },
});
