/**
 * Build-time data layer. Reads the canonical snapshot the collector wrote (git = truth);
 * the site is a pure derived view of these files. No DB, no runtime fetch.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('../../../', import.meta.url)); // repo root (Evidaxis/)

function readJson(rel: string): any {
  return JSON.parse(readFileSync(ROOT + rel, 'utf8'));
}

// JSONL reader (one JSON object per non-blank line). Tolerant of a missing file:
// coverage of side-signals like deps.dev is partial, so absence is normal, not an error.
function readJsonl(rel: string): any[] {
  let txt: string;
  try {
    txt = readFileSync(ROOT + rel, 'utf8');
  } catch {
    return [];
  }
  const out: any[] = [];
  for (const line of txt.split('\n')) {
    const s = line.trim();
    if (s) out.push(JSON.parse(s));
  }
  return out;
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

// deps.dev "dependents" — an R0 adoption signal ("who builds on it"), captured
// point-in-time. It is DISPLAYED, never folded into the momentum score: the
// scoring methodology is frozen (byte-frozen genesis), and this is a partial-
// coverage side signal, not a scored axis. Honesty about that is the moat.
export type DepsSignal = {
  value: number; direct: number; indirect: number; system: string; package: string;
};

const toDepsSignal = (s: any): DepsSignal | null =>
  s && typeof s.value === 'number'
    ? { value: s.value, direct: s.direct ?? 0, indirect: s.indirect ?? 0, system: s.source_system ?? '', package: s.package ?? '' }
    : null;

export const deps: Map<string, DepsSignal> = (() => {
  const m = new Map<string, DepsSignal>();
  // Primary: the deps capture aligned to this snapshot's date folder.
  for (const r of readJsonl(`data/observations/${SNAP_DATE}/deps.jsonl`)) {
    if (r?.coverage !== 'matched') continue;
    const sig = toDepsSignal(r?.signals?.deps_dev_dependents);
    if (sig) m.set(r.entity_id, sig);
  }
  // Fallback: deps are captured daily into per-day folders, so a future weekly
  // snapshot date may lack a same-day file. For any entity not covered above,
  // take its latest capture from the per-entity history so the value never
  // silently vanishes across snapshots (guards stale-state drift).
  for (const e of entities) {
    if (m.has(e.entity_id)) continue;
    const rows = readJsonl(`data/observations/history/${e.entity_id}.deps.jsonl`)
      .filter((r) => r?.coverage === 'matched' && r?.period)
      .sort((a, b) => String(a.period).localeCompare(String(b.period)));
    const sig = rows.length ? toDepsSignal(rows[rows.length - 1]?.signals?.deps_dev_dependents) : null;
    if (sig) m.set(e.entity_id, sig);
  }
  return m;
})();

// Latest archive-wide Merkle integrity root (collectors/merkle_root.py). A compact
// witness that the whole data/ archive existed as-is at that date. null before the
// first anchor. See METHODOLOGY-VERSIONING.md sibling contract on integrity.
export function latestArchiveRoot(): { date: string; root: string; n_files: number } | null {
  try {
    const files = readdirSync(ROOT + 'data/integrity/')
      .filter((f) => /^archive-root-.*\.json$/.test(f)).sort();
    if (!files.length) return null;
    const j = readJson('data/integrity/' + files[files.length - 1]);
    return { date: j.date, root: j.root, n_files: j.n_files };
  } catch {
    return null;
  }
}

// RECONSTRUCTED (not point-in-time captured) weekly commit-velocity history for a
// system, from data/observations/backfill/. Labeled reconstructed everywhere it is
// shown (collectors/shadow_backfill.py writes reconstructable:true). Never mixed with
// the captured Type-2 signals. Missing file -> [].
export function backfillSeries(id: string): { period: string; value: number }[] {
  return readJsonl(`data/observations/backfill/${id}.backfill.jsonl`)
    .filter((r) => r?.reconstructable === true && r?.signal === 'github_commit_velocity_weekly' && r?.period)
    .map((r) => ({ period: r.period, value: Number(r.value) || 0 }))
    .sort((a, b) => a.period.localeCompare(b.period));
}

// Point-in-time dependents series for a system (one value per snapshot period).
// History files accumulate weekly; today most systems have 1 point (flat/absent),
// which is honest and fills in over time. Missing file -> [].
export function depsSeries(id: string): { period: string; value: number }[] {
  const byPeriod = new Map<string, number>();
  for (const r of readJsonl(`data/observations/history/${id}.deps.jsonl`)) {
    const v = r?.signals?.deps_dev_dependents?.value;
    if (typeof v === 'number' && r.period) byPeriod.set(r.period, v); // last capture per period wins
  }
  return [...byPeriod.entries()]
    .map(([period, value]) => ({ period, value }))
    .sort((a, b) => a.period.localeCompare(b.period));
}
