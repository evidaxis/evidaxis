/**
 * Build-time data layer. Reads the canonical snapshot the collector wrote (git = truth);
 * the site is a pure derived view of these files. No DB, no runtime fetch.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('../../../', import.meta.url)); // repo root (Evidaxis/)

function readJson(rel: string): any {
  return JSON.parse(readFileSync(ROOT + rel, 'utf8'));
}

export type AxisGithub = {
  slope: number | null; cohort_z: number | null;
  recent_weekly_commits: number | null; stars_not_scored: number | null;
};
export type AxisOpenAlex = {
  status: 'present' | 'insufficient' | 'absent';
  slope: number | null; cohort_z: number | null;
  total_citations: number; by_year: Record<string, number> | null; proxy: string | null;
};
export type Entity = {
  entity_id: string; name: string; slug: string; entity_type: string;
  homepage: string | null; github_repo: string; openalex_work_ids: string[];
  industry: string; sub_niche: string; cohort: string;
  axes: { github_commit_velocity: AxisGithub; openalex_citation_momentum: AxisOpenAlex };
  momentum: number | null; percentile: number | null; confidence: string;
  axes_present: string[]; convergent_axes: string[]; rising: boolean;
  status: 'rising' | 'watch' | 'tracked' | 'single-axis' | 'calibration';
  incumbent: boolean; note: string | null;
};
export type Snapshot = {
  schema_version: string; snapshot_date: string; period: string; captured_at: string;
  methodology_version: string; snapshot_id: string; fetcher_version: string; license: string;
  domain: { slug: string; label: string };
  axes: Record<string, string>; gate: string;
  cohorts: Record<string, { label: string; industry: string; sub_niche: string }>;
  entities: Entity[];
  counts: { entities: number; rising: number; watch: number; tracked: number; calibration: number; axis2_present: number };
};

const latest = readJson('data/latest.json');
export const SNAP_DATE: string = latest.snapshot_date;
export const snapshot: Snapshot = readJson(`data/snapshots/${SNAP_DATE}/snapshot.json`);
export const provenance = readJson(`data/snapshots/${SNAP_DATE}/provenance.json`);
export const manifest = readJson(`data/snapshots/${SNAP_DATE}/manifest.json`);
export const taxonomy = readJson('taxonomy/nodes.json');

export const entities = snapshot.entities;
export const entityById = (id: string) => entities.find((e) => e.entity_id === id);

export function commitSeries(id: string): number[] {
  return provenance.github_weekly_raw?.[id] ?? [];
}
export function citationSeries(e: Entity): { year: number; n: number }[] {
  const by = e.axes.openalex_citation_momentum.by_year;
  if (!by) return [];
  return Object.entries(by).map(([y, n]) => ({ year: +y, n: n as number })).sort((a, b) => a.year - b.year);
}

// Em-dash (U+2014) is the brand's #1 "AI-written" tell; strip it from any label
// surfaced from the raw data (the published dataset keeps its value untouched).
export const cleanLabel = (s: string) => s.replace(/\s*—\s*/g, ', ');

export const industries = () => {
  const map = new Map<string, { slug: string; label: string; subniches: Map<string, { slug: string; label: string; cohortKey: string }> }>();
  for (const [ck, c] of Object.entries(snapshot.cohorts)) {
    if (!map.has(c.industry)) {
      const node = taxonomy.nodes.find((n: any) => n.level === 'field' && n.slug === c.industry);
      map.set(c.industry, { slug: c.industry, label: cleanLabel(node?.name ?? c.industry), subniches: new Map() });
    }
    map.get(c.industry)!.subniches.set(c.sub_niche, { slug: c.sub_niche, label: cleanLabel(c.label), cohortKey: ck });
  }
  return map;
};

export const entitiesInCohort = (cohortKey: string) =>
  entities.filter((e) => e.cohort === cohortKey)
    .sort((a, b) => (b.momentum ?? -1) - (a.momentum ?? -1));

export const STATUS_LABEL: Record<Entity['status'], string> = {
  rising: 'Rising', watch: 'Watch', tracked: 'Tracked',
  'single-axis': 'Single-axis', calibration: 'Calibration',
};
export const AXIS_LABEL: Record<string, string> = {
  github_commit_velocity: 'Development velocity',
  openalex_citation_momentum: 'Citation momentum',
};

export const fmtZ = (z: number | null) => (z == null ? 'no axis' : (z >= 0 ? '+' : '') + z.toFixed(2));
export const fmtSlope = (s: number | null) => (s == null ? 'n/a' : (s >= 0 ? '+' : '') + s.toFixed(3));
