import type { APIRoute } from 'astro';
import { latest } from '../lib/archive';
import { methodologyRegistryFor } from '../lib/methodology';

// Public methodology version registry, served at /methodology-registry.json.
// Single source of truth (src/lib/methodology-registry.json), also consumed by
// the JSON-LD builders and the methodology pages. Contract: METHODOLOGY-VERSIONING.md.
// Rows are append-only and may be published before their effective date (m3 shipped
// ahead of its first snapshot). Status is presented relative to the latest published
// snapshot, so the served registry never calls a version current before any snapshot
// uses it; the stored rows themselves stay untouched.
export const GET: APIRoute = () =>
  new Response(JSON.stringify(methodologyRegistryFor(latest), null, 2), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
