import type { APIRoute } from 'astro';
import { searchIndex } from '../lib/hubs';

// Home "Find a system": every system in the latest snapshot, {name, id}, A to Z.
export const GET: APIRoute = () => new Response(JSON.stringify(searchIndex()), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
