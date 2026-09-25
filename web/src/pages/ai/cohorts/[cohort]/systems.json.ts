import type { APIRoute } from 'astro';
import { industries } from '../../../../lib/data';
import { nicheJSON, nicheSummary } from '../../../../lib/hubs';

export function getStaticPaths() {
  return [...industries().values()].flatMap((f) => [...f.subniches.values()])
    .map((c) => ({ params: { cohort: c.slug }, props: { cohortKey: c.cohortKey } }));
}
export const GET: APIRoute = ({ props }) => new Response(`${JSON.stringify(nicheJSON(nicheSummary(props.cohortKey)))}\n`, { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
