import type { APIRoute } from 'astro';
import registry from '../lib/methodology-registry.json';

// Public methodology version registry, served at /methodology-registry.json.
// Single source of truth (src/lib/methodology-registry.json), also consumed by
// the JSON-LD builders and the methodology pages. Contract: METHODOLOGY-VERSIONING.md.
export const GET: APIRoute = () =>
  new Response(JSON.stringify(registry, null, 2), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
