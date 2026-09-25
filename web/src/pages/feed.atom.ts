import type { APIRoute } from 'astro';
import { atomFeed, siteFeedEntries } from '../lib/feed';

export const GET: APIRoute = () => new Response(atomFeed(siteFeedEntries()), {
  headers: { 'Content-Type': 'application/atom+xml; charset=utf-8' },
});
