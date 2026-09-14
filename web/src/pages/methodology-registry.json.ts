import type { APIRoute } from 'astro';
import registry from '../lib/methodology-registry.json';
import { latest } from '../lib/archive';
import { methodologyEntry } from '../lib/methodology';

// Public methodology version registry, served at /methodology-registry.json.
// Single source of truth (src/lib/methodology-registry.json), also consumed by
// the JSON-LD builders and the methodology pages. Contract: METHODOLOGY-VERSIONING.md.
const current = methodologyEntry(latest.methodology_version).version;
// Rows are append-only and may be published before their effective date (m3 shipped
// ahead of its first snapshot). Status is presented relative to the latest published
// snapshot, so the served registry never calls a version current before any snapshot
// uses it; the stored rows themselves stay untouched.
const versions = registry.versions.map((row) => ({
  ...row,
  status: row.version === current ? 'current' : row.effective_at > latest.snapshot_date ? 'scheduled' : row.status,
}));

export const GET: APIRoute = () =>
  new Response(JSON.stringify({ ...registry, current, versions }, null, 2), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
