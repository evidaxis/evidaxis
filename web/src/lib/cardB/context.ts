import { snapshots, entityUniverse, provenanceForSnapshot, type ArchivedEntity } from '../archive';
import { buildDepsMap, depsSeries, backfillSeries, ownerTypes, publicRepoLabel, publicRepoUrl, publicHomepage } from '../data';
import { measurementStateFor } from '../measurement';
import { isTemplateB } from './policy.mjs';
import { buildCardB, summarizeCohort, median, metrics, numeric, type Context, type CardBModel, type HistoryPoint } from './build';

const seriesByDate = new Map<string, Record<string, number[]>>();
const papersByDate = new Map<string, Record<string, { raw?: Record<string, { title?: string }> }>>();
const dailyByDate = new Map<string, ReturnType<typeof buildDepsMap>>();
const historyById = new Map<string, { entity: ArchivedEntity['entity']; snapshot: ArchivedEntity['snapshot'] }[]>();
const summaries = new Map<string, ReturnType<typeof summarizeCohort>>();
const citationMedians = new Map<string, number | null>();
for (const snapshot of snapshots) for (const entity of snapshot.entities) {
  const rows = historyById.get(entity.entity_id) ?? [];
  rows.push({ entity, snapshot }); historyById.set(entity.entity_id, rows);
}
const rawSeries = (date: string) => {
  if (!seriesByDate.has(date)) {
    const provenance = provenanceForSnapshot(date);
    seriesByDate.set(date, provenance?.github_weekly_raw ?? {});
    papersByDate.set(date, provenance?.openalex_raw ?? {});
  }
  return seriesByDate.get(date)!;
};
const dailyFor = (snapshot: ArchivedEntity['snapshot']) => {
  if (!dailyByDate.has(snapshot.snapshot_date)) dailyByDate.set(snapshot.snapshot_date, buildDepsMap(snapshot));
  return dailyByDate.get(snapshot.snapshot_date)!;
};
const bannedOwners = [...new Set([
  'paul-gauthier', 'gcorso', 'jwohlwend', 'petergriffinjin', 'haotian-liu', 'hexgrad', 'dauparas', 'comfyanonymous', 'geeeekexplorer', 'arneschneuing',
  ...Object.values(ownerTypes.repos).filter(r => r.owner_type === 'User').map(r => r.full_name.split('/')[0]),
])];

export function contextFor(record: ArchivedEntity): Context {
  const { entity: e, snapshot: snap } = record;
  const entry = ownerTypes.repos[e.github_repo];
  // A cohort's sorted rows, medians and 52 percentile bands are shared across
  // cards; the admission batch must not recompute them for every new system.
  const key = `${snap.snapshot_id}:${e.cohort}`;
  if (!summaries.has(key)) summaries.set(key, summarizeCohort(snap.entities.filter(p => p.cohort === e.cohort), rawSeries(snap.snapshot_date)));
  if (!citationMedians.has(snap.snapshot_id)) citationMedians.set(snap.snapshot_id, median(snap.entities
    .filter(p => p.axes_present.includes('openalex_citation_momentum')).map(p => metrics(p).citations).filter(numeric)));
  const cohortSummary = summaries.get(key)!;
  const history: HistoryPoint[] = (historyById.get(e.entity_id) ?? []).filter(p => p.snapshot.snapshot_date <= snap.snapshot_date)
    .map(p => ({ ...p, commits: rawSeries(p.snapshot.snapshot_date)[e.entity_id] ?? [], daily: dailyFor(p.snapshot).get(e.entity_id) ?? null }));
  return {
    state: measurementStateFor(e, snap), commits: rawSeries(snap.snapshot_date)[e.entity_id] ?? [],
    cohort: cohortSummary.cohort, cohortCommits: rawSeries(snap.snapshot_date), history, cohortSummary, registryMedian: citationMedians.get(snap.snapshot_id)!,
    daily: dailyFor(snap).get(e.entity_id) ?? null, dailySeries: depsSeries(e.entity_id, snap),
    // Backfill is explicitly reconstructed, and dates later than the snapshot
    // are withheld even though the current archive may contain newer captures.
    backfill: backfillSeries(e.entity_id).filter(p => p.period <= snap.period),
    repoLabel: e.github_repo ? publicRepoLabel(e) : 'not linked', repoUrl: e.github_repo ? publicRepoUrl(e) : null,
    repoApi: entry ? entry.owner_type === 'Organization' ? `https://api.github.com/repos/${entry.full_name}` : `https://api.github.com/repositories/${entry.repo_id}` : null,
    homepage: e.github_repo ? publicHomepage(e) : null, bannedOwners,
    paperWorks: e.openalex_work_ids.map(id => ({ id, title: papersByDate.get(snap.snapshot_date)?.[e.entity_id]?.raw?.[id]?.title?.replace(/\u2014/g, '-') ?? null })),
  };
}

const models = new Map<string, CardBModel>();
export function cardBFor(record: ArchivedEntity): CardBModel {
  const key = `${record.entity.entity_id}:${record.snapshot.snapshot_id}`;
  if (!models.has(key)) models.set(key, buildCardB(record, contextFor(record)));
  return models.get(key)!;
}
export const bRecords = entityUniverse.filter(r => isTemplateB(r.entity.entity_id));

// Versioned download and image URLs remain addressable after the next release.
export function assetRecords(): ArchivedEntity[] {
  return bRecords.flatMap(record => (historyById.get(record.entity.entity_id) ?? []).map(p => ({
    ...record, ...p, lastSeenSnapshot: p.snapshot.snapshot_date,
  })));
}
