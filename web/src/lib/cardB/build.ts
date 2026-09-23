import type { Entity, Snapshot, DepsSignal } from '../data';
import type { ArchivedEntity } from '../archive';
import type { MeasurementState } from '../measurement';
import { measurementPhrases } from '../measurement';
import { claimUrnForEntity } from '../claim_urn';
import { TEMPLATE_VERSION } from './config';
import { assertPublicText, copy, facet, selectClasses } from './facets';

export const numeric = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n);
export const fmt = (n: number | null): string => n === null ? 'no reading' : Number(n.toFixed(3)).toLocaleString('en-US', { maximumFractionDigits: 3 });
export function quantile(values: number[], q: number): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b), i = (sorted.length - 1) * q;
  return sorted[Math.floor(i)] + (sorted[Math.ceil(i)] - sorted[Math.floor(i)]) * (i % 1);
}
export const median = (values: number[]) => quantile(values, .5);
export function paperRef(note: string | null): string | null {
  return note?.match(/(?:paper_ref:\s*(?:arxiv:\s*)?|\barxiv:\s*)(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?\/\d{7}(?:v\d+)?)/i)?.[1] ?? null;
}
const nullable = (value: unknown, field: string): number | null => {
  if (value === null) return null;
  if (!numeric(value)) throw new Error(`Undefined or invalid reading: ${field}`);
  return value;
};

export function metrics(e: Entity) {
  const gh = e.axes?.github_commit_velocity, oa = e.axes?.openalex_citation_momentum, dd = e.axes?.deps_direct_dependents_momentum;
  return {
    commits: gh ? nullable(gh.recent_weekly_commits, 'recent_weekly_commits') : null,
    citations: oa && oa.status !== 'absent' && e.openalex_work_ids?.length ? nullable(oa.total_citations, 'total_citations') : null,
    dependents: dd && dd.status !== 'out_of_panel' ? nullable(dd.latest, 'dependents.latest') : null,
    stars: gh ? nullable(gh.stars_not_scored, 'stars_not_scored') : null,
  };
}
export type MetricKey = keyof ReturnType<typeof metrics>;
export function summarizeCohort(cohort: Entity[], raw: Record<string, number[]>) {
  const peers = [...cohort].sort((a, b) => a.name.localeCompare(b.name, 'en') || a.entity_id.localeCompare(b.entity_id))
    .map(peer => ({ id: peer.entity_id, name: peer.name, ...metrics(peer), momentum: peer.momentum, percentile: peer.percentile }));
  const medians = Object.fromEntries((['commits', 'citations', 'dependents', 'stars'] as MetricKey[]).map(key => {
    const values = peers.map(peer => peer[key]).filter(numeric);
    return [key, { value: median(values), n: values.length }];
  })) as Record<MetricKey, { value: number | null; n: number }>;
  const length = Math.max(0, ...cohort.map(peer => (raw[peer.entity_id] ?? []).length));
  const commitBand = Array.from({ length }, (_, i) => {
    const v = cohort.map(peer => (raw[peer.entity_id] ?? [])[i]).filter(numeric);
    return { p25: quantile(v, .25), median: median(v), p75: quantile(v, .75), n: v.length };
  });
  return { cohort, peers, medians, commitBand };
}
export type HistoryPoint = { entity: Entity; snapshot: Snapshot; commits: number[]; daily: DepsSignal | null };
export type Context = {
  state: MeasurementState; commits: number[]; cohort: Entity[]; cohortCommits: Record<string, number[]>;
  history: HistoryPoint[]; daily: DepsSignal | null; dailySeries: { period: string; value: number }[];
  backfill: { period: string; value: number }[]; repoLabel: string; repoUrl: string | null;
  repoApi: string | null; homepage: string | null; bannedOwners: string[];
  cohortSummary?: ReturnType<typeof summarizeCohort>; registryMedian?: number | null;
  paperWorks?: { id: string; title: string | null }[];
};
export type Reading = {
  key: string; entity_id: string; label: string; value: number | number[] | null; unit: string;
  date: string; source: string; definition: string; median: number | null; n: number;
  delta4: number | null; delta26: number | null; range: [number, number] | null; previous: number | null;
};
const span = (values: number[]): [number, number] | null => values.length ? [Math.min(...values), Math.max(...values)] : null;
const difference = (a: number | null, b: number | null) => a === null || b === null ? null : a - b;
const dateAgo = (date: string, weeks: number) => new Date(Date.parse(`${date}T00:00:00Z`) - weeks * 604800000).toISOString().slice(0, 10);
function roundedAverage(values: number[]) {
  const scaled = values.reduce((a, b) => a + b, 0) / values.length * 10;
  // Match the collector's one-decimal round-to-even, so unchanged windows do
  // not acquire a spurious delta by mixing a rounded mean and an exact mean.
  return (scaled % 1 === .5 ? Math.round(scaled / 2) * 2 : Math.round(scaled)) / 10;
}

export function commitRuler(values: number[], capture: string) {
  if (values.some(v => !numeric(v) || v < 0)) throw new Error('Invalid raw commit series');
  // Provenance retains counts but drops GitHub timestamps. Week labels are
  // explicitly reconstructed from the capture's Sunday, not a last-commit date.
  const sunday = new Date(`${capture.slice(0, 10)}T00:00:00Z`);
  sunday.setUTCDate(sunday.getUTCDate() - sunday.getUTCDay());
  const weeks = values.map((value, i) => ({ date: dateAgo(sunday.toISOString().slice(0, 10), values.length - i - 1), value }));
  let zeroWeeks = 0;
  for (let i = values.length - 1; i >= 0 && values[i] === 0; i--) zeroWeeks++;
  const last = values.at(-1) ?? null;
  return { weeks, zeroWeeks, lastCommitWeek: [...weeks].reverse().find(w => w.value > 0)?.date ?? null,
    firstWeek: weeks[0]?.date ?? null, delta4: difference(last, values.at(-5) ?? null),
    delta26: difference(last, values.at(-27) ?? null), range: span(values) };
}

export function buildCardB(record: ArchivedEntity, ctx: Context) {
  const e = record.entity, snap = record.snapshot, state = ctx.state, name = e.name;
  const date = snap.snapshot_date, release = `${snap.snapshot_id}-${TEMPLATE_VERSION}`;
  const path = `/e/${e.entity_id}/`, url = `https://evidaxis.org${path}`;
  const urn = claimUrnForEntity(e, snap), own = metrics(e);
  const summary = ctx.cohortSummary?.cohort === ctx.cohort ? ctx.cohortSummary : summarizeCohort(ctx.cohort, ctx.cohortCommits);
  const cohort = ctx.cohort;
  const cohortLabel = (snap.cohorts[e.cohort]?.label ?? e.sub_niche).replace(/\u2014/g, ',');
  const medians = summary.medians;
  const registryMedian = ctx.registryMedian !== undefined ? ctx.registryMedian : median(snap.entities.filter(peer => peer.axes_present.includes('openalex_citation_momentum'))
    .map(peer => metrics(peer).citations).filter(numeric));
  const ruler = commitRuler(ctx.commits, snap.captured_at);
  const oa = e.axes?.openalex_citation_momentum, dd = e.axes?.deps_direct_dependents_momentum;
  const years = Object.entries(oa?.by_year ?? {}).map(([year, value]) => ({ year: +year, value }))
    .filter(row => row.year < +date.slice(0, 4)).sort((a, b) => a.year - b.year);
  const paper = paperRef(e.note);
  const classes = selectClasses({ commits: own.commits, zeroWeeks: ruler.zeroWeeks, commitWeeks: ctx.commits.length,
    axes: state.axis_coverage.measurable_axis_count, citations: own.citations, paperLinked: e.openalex_work_ids.length > 0, years: years.length,
    registryMedian, dependents: own.dependents, depsStatus: dd?.status ?? null, points: dd?.points ?? null,
    rising: state.positive_signal.state === 'published', incumbent: e.incumbent,
    observations: state.history_sufficiency.weekly_observations });
  const phrases = Object.fromEntries(Object.entries(measurementPhrases(state)).map(([key, value]) => [key, value.replace(/\u2014/g, '-')])) as ReturnType<typeof measurementPhrases>;
  const vars = { name, date, cohort: cohortLabel, n: cohort.length, rwc: fmt(own.commits), zero_weeks: ruler.zeroWeeks,
    last_commit_week: ruler.lastCommitWeek ?? 'not observed', first_week: ruler.firstWeek ?? 'no reading',
    total: fmt(own.citations), n_years: years.length, reg_med: fmt(registryMedian),
    by_year: years.map(y => `${y.year}: ${y.value}`).join('; ') || 'no completed yearly reading',
    latest: fmt(own.dependents), partition: dd?.as_of_partition ?? 'not captured', points: dd?.points ?? 'no reading',
    ts: fmt(dd?.theil_sen ?? null), daily: fmt(ctx.daily?.value ?? null), daily_date: ctx.dailySeries.at(-1)?.period ?? date,
    period: state.positive_signal.period ?? snap.period, k: e.convergent_axes.length,
    observations: state.history_sufficiency.weekly_observations, stars: fmt(own.stars), paper_ref: paper ?? '',
    gate: phrases.gate, history: phrases.history, coverage: phrases.axis_coverage, urn, url,
    work_ids: (e.openalex_work_ids ?? []).join(', '),
  };
  const make = (id: Parameters<typeof facet>[0], extra = {}) => facet(id, { ...vars, ...extra }, name, ctx.bannedOwners);
  const facets = {
    code: make(classes.code, { med: fmt(medians.commits.value), n: medians.commits.n }),
    citations: make(classes.citations, { slope: fmt(oa?.slope ?? null) }),
    dependents: make(classes.dependents, { med: fmt(medians.dependents.value), slope: fmt(dd?.slope ?? null) }),
    standing: make(classes.standing), stars: own.stars === null ? null : make('STARS'),
    paper_ref: paper ? make('PAPERREF') : null,
  };
  const text = (key: Parameters<typeof copy>[0], extra = {}) => copy(key, { ...vars, ...extra }, name, ctx.bannedOwners);
  const primaryKey: MetricKey | null = own.commits !== null ? 'commits' : own.citations !== null ? 'citations' : own.dependents !== null ? 'dependents' : null;
  const lead = own.commits !== null ? facets.code.answer : primaryKey ? text('repository_free', {
    value: fmt(own[primaryKey]), unit: primaryKey === 'citations' ? 'OpenAlex citing works' : 'deps.dev direct dependents',
    median: fmt(medians[primaryKey].value), n: medians[primaryKey].n,
  }).text : facets.code.answer;
  const parts = [lead, ...(primaryKey !== 'citations' ? [facets.citations.answer] : []),
    ...(primaryKey !== 'dependents' ? [facets.dependents.answer] : []),
    ...(['C01', 'C02', 'C03'].includes(classes.standing) ? [facets.standing.answer] : [])];
  let answer = [...parts, ...(facets.stars ? [facets.stars.answer] : []), text('capture_short').text].join(' ');
  const wordCount = (s: string) => s.trim().split(/\s+/).length;
  if (wordCount(answer) > 60) answer = [...parts, text('capture_short').text].join(' ');
  if (wordCount(answer) < 40) answer = [...parts, ...(facets.stars ? [facets.stars.answer] : []), text('capture').text].join(' ');
  if (wordCount(answer) < 40) answer += ' ' + text('answer_context').text;
  assertPublicText(answer, name, ctx.bannedOwners);

  const history = ctx.history.filter(p => p.snapshot.snapshot_date <= date).sort((a, b) => a.snapshot.snapshot_date.localeCompare(b.snapshot.snapshot_date));
  const previous = history.filter(p => p.snapshot.snapshot_date < date).at(-1) ?? null;
  const historical = (key: MetricKey, weeks: number) => history.find(p => p.snapshot.snapshot_date === dateAgo(date, weeks));
  const priorValue = (key: MetricKey, weeks: number) => { const p = historical(key, weeks); return p ? metrics(p.entity)[key] : null; };
  const trailingAverage = (offset: number) => {
    const end = ctx.commits.length - offset;
    return end >= 12 ? roundedAverage(ctx.commits.slice(end - 12, end)) : null;
  };
  const averages = ctx.commits.slice(11).map((_, i) => roundedAverage(ctx.commits.slice(i, i + 12)));
  const source = (key: string) => key === 'citations' || key === 'citation_series'
    ? `https://api.openalex.org/works?filter=openalex:${e.openalex_work_ids.join('|')}`
    : key === 'dependents' || key === 'dependents_series' ? `https://evidaxis.org/snapshots/${date}/snapshot.json`
    : key === 'daily' && ctx.daily ? `https://api.deps.dev/v3alpha/systems/${encodeURIComponent(ctx.daily.system)}/packages/${encodeURIComponent(ctx.daily.package)}`
    : ctx.repoApi ? `${ctx.repoApi}${key === 'stars' ? '' : '/stats/commit_activity'}` : '';
  const definitions = {
    commits: 'GitHub averaged commits per week over the trailing window (12 weeks); deltas compare trailing averages, range spans rolling averages within 52 weeks.',
    citations: 'OpenAlex citing works in the published completed calendar years.',
    dependents: 'deps.dev weekly package-union direct dependents, frozen m3 panel; partition dates can repeat across snapshots.',
    stars: 'GitHub stargazers count; recorded, not scored.',
  };
  const labels = { commits: 'Commits per week', citations: 'Citing works', dependents: 'Direct dependents', stars: 'Stars' };
  const units = { commits: 'commits/wk', citations: 'citing works', dependents: 'packages', stars: 'stars' };
  const readings: Reading[] = (Object.keys(own) as MetricKey[]).map(key => ({
    key, entity_id: e.entity_id, label: labels[key], value: own[key], unit: units[key],
    date: key === 'dependents' ? dd?.as_of_partition ?? date : date, source: source(key), definition: definitions[key],
    median: medians[key].value, n: medians[key].n,
    delta4: difference(own[key], key === 'commits' ? trailingAverage(4) : priorValue(key, 4)),
    delta26: difference(own[key], key === 'commits' ? trailingAverage(26) : priorValue(key, 26)),
    range: key === 'commits' ? span(averages) : span(history.filter(p => p.snapshot.snapshot_date >= dateAgo(date, 52)).map(p => metrics(p.entity)[key]).filter(numeric)),
    previous: previous ? metrics(previous.entity)[key] : null,
  }));
  const seriesReading = (key: string, label: string, value: number[], definition: string): Reading => ({
    key, entity_id: e.entity_id, label, value: value.length ? value : null, unit: key === 'commit_series' ? 'commits' : key === 'dependents_series' ? 'packages' : 'citing works',
    date, source: source(key), definition, median: null, n: value.length, delta4: null, delta26: null, range: span(value), previous: null,
  });
  readings.splice(3, 0, { key: 'daily', entity_id: e.entity_id, label: 'Daily dependents (unscored)',
    value: ctx.daily?.value ?? null, unit: 'packages', date: ctx.dailySeries.at(-1)?.period ?? date, source: source('daily'),
    definition: 'deps.dev REST dependents count, unscored; separate from the weekly package-union axis.', median: null, n: ctx.dailySeries.length,
    delta4: null, delta26: null, range: span(ctx.dailySeries.map(p => p.value)), previous: previous?.daily?.value ?? null });
  readings.push(seriesReading('commit_series', '52-week commit series', ctx.commits, 'GitHub commit_activity weekly totals, captured as one series.'),
    seriesReading('citation_series', 'Completed calendar years', years.map(y => y.value), 'OpenAlex citing works by completed calendar year.'),
    seriesReading('dependents_series', 'Direct dependents history', history.map(p => metrics(p.entity).dependents).filter(numeric), 'deps.dev direct dependents from captured snapshots.'));
  const changes = (Object.keys(own) as MetricKey[]).map(key => ({ key, label: labels[key], previous: previous ? metrics(previous.entity)[key] : null,
    current: own[key], delta: difference(own[key], previous ? metrics(previous.entity)[key] : null),
    previous_snapshot_id: previous?.snapshot.snapshot_id ?? null, snapshot_id: snap.snapshot_id }));
  const missing = readings.filter(r => r.value === null && !r.key.endsWith('_series')).map(r => ({ key: r.key, label: r.label,
    reason: r.key === 'citations' ? e.openalex_work_ids.length ? 'no reading captured for the linked work' : 'not linked' : r.key === 'dependents' ? dd?.status === 'out_of_panel' ? 'outside panel' : 'no partition' : 'no reading captured' }));
  const peers = summary.peers;
  const commitBand = summary.commitBand.slice(0, ctx.commits.length);
  const display = { template: 'B', release_id: release, entity_id: e.entity_id, answer,
    tiles: readings.filter(r => ['commits', 'citations', 'dependents', 'stars'].includes(r.key))
      .map(r => ({ key: r.key, value: r.value, unit: r.unit, median: r.median, n: r.n, source: r.source, date: r.date })),
    answer_claims: [facets.code.claim_id, facets.citations.claim_id, facets.dependents.claim_id, facets.standing.claim_id],
    answer_comparison: primaryKey ? { key: primaryKey, median: medians[primaryKey].value, n: medians[primaryKey].n, rendered_value: fmt(own[primaryKey]) } : null,
    paper_ref: paper, paper_works: ctx.paperWorks ?? [], cohort: cohortLabel, cohort_n: cohort.length, date, urn,
  };
  const texts = {
    average: text('code_average'), code: text(ruler.lastCommitWeek ? (ruler.zeroWeeks > 0 ? 'code_last' : 'code_last_active') : 'code_none'),
    citations_difference: text('citations_difference'), citations_report: text('citations_report'), citation_scope: text('citation_scope'),
    readings: text('readings'), niche: text('niche', { median: fmt(medians.commits.value) }),
    changes: previous ? text('changes', { count: changes.filter(c => c.previous !== c.current).length, previous: previous.snapshot.snapshot_id, current: snap.snapshot_id }) : text('no_previous'),
    citation: text('citation'), exports: text('exports'), teams: text('teams'), links: text('links'), missing: text('missing'),
    gate_eta: text('gate_eta'), detail: text('detail'), reconstructed: text('reconstructed'),
  };
  const result = { display, facets, readings, changes, texts, entity: { id: e.entity_id, name, type: e.entity_type },
    release, path, url, urn, date, snapshot_id: snap.snapshot_id, methodology: snap.methodology_version, superseded: record.recordStatus === 'superseded',
    cohortLabel, peers, medians, ruler, years, commitBand, missing, paper,
    repoLabel: ctx.repoLabel, repoUrl: ctx.repoUrl, homepage: ctx.homepage, workIds: e.openalex_work_ids,
    history, dailySeries: ctx.dailySeries, backfill: ctx.backfill, daily: ctx.daily,
    deps: dd ?? null, state, phrases, valuesUrl: `${path}values-${release}.csv`, historyUrl: `${path}history-${release}.csv`,
    nicheCsv: `/ai/cohorts/${e.sub_niche}/values-${release}.csv`, feedUrl: `${path}feed.atom`, jsonUrl: `/e/${e.entity_id}.json`,
  };
  // Raw archive rows stay private to the generator; only explicit projections
  // cross the person-free boundary. This also validates links before rendering.
  assertPublicText(JSON.stringify({ display, facets, readings, changes, texts, peers, repo: ctx.repoLabel, repoUrl: ctx.repoUrl, homepage: ctx.homepage }), name, ctx.bannedOwners);
  return result;
}
export type CardBModel = ReturnType<typeof buildCardB>;
