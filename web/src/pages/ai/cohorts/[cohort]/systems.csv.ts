import type { APIRoute } from 'astro';
import { industries } from '../../../../lib/data';
import { nicheCSV, nicheSummary } from '../../../../lib/hubs';

// The niche table as a CC0 download: all rows (never paginated), one per system.
export function getStaticPaths() {
  return [...industries().values()].flatMap((f) => [...f.subniches.values()])
    .map((c) => ({ params: { cohort: c.slug }, props: { cohortKey: c.cohortKey } }));
}
export const GET: APIRoute = ({ props }) => new Response(nicheCSV(nicheSummary(props.cohortKey)), { headers: { 'Content-Type': 'text/csv; charset=utf-8' } });
