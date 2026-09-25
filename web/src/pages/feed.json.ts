import type { APIRoute } from 'astro';
import { jsonFeed, siteFeedEntries } from '../lib/feed';

export const GET: APIRoute = () => new Response(`${JSON.stringify(jsonFeed(siteFeedEntries()), null, 2)}\n`, {
  headers: { 'Content-Type': 'application/feed+json; charset=utf-8' },
});
