/**
 * Niche hubs, field hubs and the home page read one projection of the latest
 * snapshot. Every number comes from the functions the system cards use:
 * metrics() for readings, the card's cohort summary for niche medians,
 * badgeData(record, 'medal') for medals, the measurement state for Rising and
 * verifiedPin() for dependents. Nothing here ranks systems: rows are A to Z.
 */
import { archiveEntityById } from './archive';
import type { ArchivedEntity } from './archive';
import { badgeData, ratioText, verifiedPin } from './badges';
import type { Tier } from './badges';
import { fmt, metrics } from './cardB/build';
import { contextFor } from './cardB/context';
import { csv } from './cardB/exports';
import { entities, entitiesInCohort, industries, snapshot, SNAP_DATE } from './data';
import type { Entity } from './data';
import { CITATION_AXIS, DEPENDENTS_AXIS, measurementStateFor } from './measurement';

export const SITE = 'https://evidaxis.org';
export const UNASSIGNED = 'unassigned-v1';
export const UNASSIGNED_LABEL = 'Not yet assigned';
export const CC0_URL = 'https://creativecommons.org/publicdomain/zero/1.0/';

export type ReadingState = 'scored' | 'count_only' | 'not_measured';
export type Medal = { tier: Exclude<Tier, null>; ratio: number; metric: 'citations' | 'dependents' };
export type MedianValue = { value: number | null; n: number };
export type HubRow = {
  id: string; name: string; url: string;
  commits: number | null; citations: number | null; citationState: ReadingState;
  /** Shown only when the package identity is verified (verifiedPin). */
  dependents: number | null; dependentsState: ReadingState;
  /** The metrics() reading that enters the niche median, verified or not. */
  dependentsReading: number | null;
  stars: number | null; medal: Medal | null; rising: boolean;
  measuredLine: string; status: string;
};
export type NicheSummary = {
  key: string; slug: string; label: string; assigned: boolean;
  field: { slug: string; label: string };
  n: number; rows: HubRow[];
  medians: { commits: MedianValue; citations: MedianValue; dependents: MedianValue } | null;
  /** Measures on which the badge rules can compare (n >= 5 and median >= 3). */
  comparable: ('citations' | 'dependents')[];
  atTwoX: number; medals: { gold: number; silver: number; bronze: number };
  rising: { id: string; name: string }[];
};

const int = (n: number) => Math.round(n).toLocaleString('en-US');
const plural = (n: number, one: string, many: string) => `${n.toLocaleString('en-US')} ${n === 1 ? one : many}`;

/** Integers print as they are; a non-integer median carries the ≈ marker. */
export const medianText = (value: number) => Number.isInteger(value) ? value.toLocaleString('en-US') : `≈${fmt(value)}`;

/** Lower-case a niche label for running text, keeping acronyms such as AI and GUI. */
export const lowerLabel = (label: string) => label.split(' ')
  .map((word) => word.split('-').map((part) => /^[A-Z][a-z]/.test(part) ? part[0].toLowerCase() + part.slice(1) : part).join('-'))
  .join(' ');

export const nicheLabel = (key: string, label: string) => key === UNASSIGNED ? UNASSIGNED_LABEL : label;

export function commitsPhrase(value: number | null): string {
  return value === null ? 'commits not measured' : `${fmt(value)} commits/week`;
}
export function citationPhrase(value: number | null, state: ReadingState): string {
  if (value === null || state === 'not_measured') return 'citations not measured';
  return `${int(value)} citations to date${state === 'count_only' ? ' (count only)' : ''}`;
}
export function dependentsPhrase(value: number | null, state: ReadingState): string {
  if (value === null || state === 'not_measured') return 'verified dependents not measured';
  return `${int(value)} verified direct dependents${state === 'count_only' ? ' (count only)' : ''}`;
}
export function measuredLine(row: Pick<HubRow, 'commits' | 'citations' | 'citationState' | 'dependents' | 'dependentsState'>): string {
  const line = `${commitsPhrase(row.commits)}, ${citationPhrase(row.citations, row.citationState)}, ${dependentsPhrase(row.dependents, row.dependentsState)}.`;
  return line[0].toUpperCase() + line.slice(1);
}
/** Status cell text: the multiple and the measure, and/or Rising. No tier words. */
export function statusText(medal: Medal | null, rising: boolean): string {
  return [
    ...(medal ? [`${ratioText(medal.ratio)} ${medal.metric}`] : []),
    ...(rising ? ['Rising'] : []),
  ].join(' · ');
}

export function hubRow(record: ArchivedEntity): HubRow {
  const e = record.entity;
  const own = metrics(e);
  const assigned = e.cohort !== UNASSIGNED;
  const state = measurementStateFor(e, record.snapshot);
  const citationState: ReadingState = own.citations === null ? 'not_measured'
    : state.axis_coverage.axes[CITATION_AXIS] === 'measurable' ? 'scored' : 'count_only';
  const verified = verifiedPin(record);
  const dependents = verified ? own.dependents : null;
  const dependentsState: ReadingState = dependents === null ? 'not_measured'
    : state.axis_coverage.axes[DEPENDENTS_AXIS] === 'measurable' ? 'scored' : 'count_only';
  let medal: Medal | null = null;
  if (assigned) {
    const data = badgeData(record, 'medal');
    if (data.tier && data.ratio !== undefined && data.metric) medal = { tier: data.tier, ratio: data.ratio, metric: data.metric };
  }
  const rising = assigned && state.positive_signal.state === 'published';
  const row = {
    id: e.entity_id, name: e.name, url: `/e/${e.entity_id}/`,
    commits: own.commits, citations: own.citations, citationState,
    dependents, dependentsState, dependentsReading: own.dependents,
    stars: own.stars, medal, rising,
  };
  return { ...row, measuredLine: measuredLine(row), status: statusText(medal, rising) };
}

const recordFor = (e: Entity): ArchivedEntity => {
  const record = archiveEntityById.get(e.entity_id);
  if (!record || record.snapshot.snapshot_date !== SNAP_DATE) throw new Error(`No current archive record for ${e.entity_id}`);
  return record;
};

type NicheRef = { key: string; slug: string; label: string; field: { slug: string; label: string } };
export function nicheRefs(): NicheRef[] {
  const out: NicheRef[] = [];
  for (const f of industries().values())
    for (const c of f.subniches.values()) out.push({ key: c.cohortKey, slug: c.slug, label: c.label, field: { slug: f.slug, label: f.label } });
  return out;
}

const summaries = new Map<string, NicheSummary>();
export function nicheSummary(cohortKey: string): NicheSummary {
  const cached = summaries.get(cohortKey);
  if (cached) return cached;
  const ref = nicheRefs().find((r) => r.key === cohortKey);
  if (!ref) throw new Error(`Unknown niche ${cohortKey}`);
  const members = entitiesInCohort(cohortKey);
  const records = members.map(recordFor);
  const rows = records.map(hubRow);
  const assigned = cohortKey !== UNASSIGNED;
  // The card's own cohort summary (cached per snapshot and cohort) supplies the medians.
  const medians = assigned && records.length ? (() => {
    const m = contextFor(records[0]).cohortSummary!.medians;
    return { commits: m.commits, citations: m.citations, dependents: m.dependents };
  })() : null;
  const comparable = medians ? (['citations', 'dependents'] as const)
    .filter((key) => medians[key].value !== null && medians[key].n >= 5 && (medians[key].value as number) >= 3) : [];
  const medals = { gold: 0, silver: 0, bronze: 0 };
  for (const row of rows) if (row.medal) medals[row.medal.tier] += 1;
  const summary: NicheSummary = {
    key: cohortKey, slug: ref.slug, label: nicheLabel(cohortKey, ref.label), assigned, field: ref.field,
    n: rows.length, rows, medians, comparable: [...comparable],
    atTwoX: rows.filter((row) => row.medal).length, medals,
    rising: rows.filter((row) => row.rising).map((row) => ({ id: row.id, name: row.name })),
  };
  summaries.set(cohortKey, summary);
  return summary;
}

const byName = (a: { label: string }, b: { label: string }) => a.label.localeCompare(b.label, 'en', { sensitivity: 'base' });
/** Real niches, name order A to Z. The not-yet-assigned group is never among them. */
export const assignedNiches = () => nicheRefs().filter((r) => r.key !== UNASSIGNED).map((r) => nicheSummary(r.key)).sort(byName);
export const unassignedSummary = () => nicheRefs().some((r) => r.key === UNASSIGNED) ? nicheSummary(UNASSIGNED) : null;

function medianClause(m: MedianValue, unit: string, among: string, total: number, alwaysN: boolean): string {
  if (m.value === null || m.n === 0) return `no ${unit} median (no system has ${among})`;
  const nText = alwaysN || m.n !== total ? ` (on the ${plural(m.n, `system with ${among}`, `systems with ${among}`)})` : '';
  return `${medianText(m.value)} ${unit}${nText}`;
}

/** The first-screen answer of a niche hub, generated from the snapshot. */
export function nicheAnswer(s: NicheSummary): string {
  if (!s.assigned) {
    return 'These systems are measured every week but have no niche yet, so there is no niche median, no medal and no niche Rising comparison.';
  }
  const m = s.medians!;
  const commits = m.commits.value === null
    ? 'no commit median (no system has a commit reading)'
    : `${medianText(m.commits.value)} commits per week${m.commits.n !== s.n ? ` (on the ${plural(m.commits.n, 'system with a commit reading', 'systems with a commit reading')})` : ''}`;
  const citations = m.citations.value === null
    ? 'no citation median (no system has a citation count)'
    : `${medianText(m.citations.value)} citations to date (on the ${plural(m.citations.n, 'system with a citation count', 'systems with a citation count')})`;
  const dependents = m.dependents.value === null
    ? 'no dependents median (no system has a dependents reading)'
    : `${medianText(m.dependents.value)} direct dependents (on the ${plural(m.dependents.n, 'system with a dependents reading', 'systems with a dependents reading')})`;
  const floors = s.comparable.length === 2 ? ''
    : s.comparable.length === 1
      ? ` Medals here compare ${s.comparable[0] === 'citations' ? 'citations' : 'verified dependents'} only: a medal needs at least 5 systems in the niche with that figure and a median of 3 or more.`
      : ' No medals this week: a medal needs at least 5 systems in the niche with the figure and a median of 3 or more.';
  // "19 systems in Coding Agents" reads right for every niche label ("coding agents systems" did not).
  return `Evidaxis measures ${plural(s.n, 'system', 'systems')} in ${s.label} every week. `
    + `In snapshot ${snapshot.period} (${snapshot.snapshot_date}) the niche median is ${commits}, ${citations} and ${dependents}. `
    + `Systems at 2× the niche median or more: ${s.atTwoX.toLocaleString('en-US')}.${floors} `
    + `Rising: ${s.rising.length ? s.rising.map((r) => r.name).join(', ') : 'none'}.`;
}

/** Meta description: the answer, shortened to fit a snippet. */
export function nicheDescription(s: NicheSummary): string {
  if (!s.assigned) return `${plural(s.n, 'open AI system', 'open AI systems')} measured weekly with no niche yet: commits, citations and dependents per system, snapshot ${snapshot.snapshot_date}. CC0.`;
  const m = s.medians!;
  const part = (v: MedianValue, unit: string) => v.value === null ? `no ${unit} median` : `${medianText(v.value)} ${unit} (n = ${v.n})`;
  const full = `${plural(s.n, `${s.label} system`, `${s.label} systems`)} measured weekly. Niche median ${part(m.commits, 'commits/week')}, ${part(m.citations, 'citations')}, ${part(m.dependents, 'direct dependents')}; snapshot ${snapshot.snapshot_date}.`;
  return full.length <= 165 ? full : `${plural(s.n, `${s.label} system`, `${s.label} systems`)} measured weekly: commits, citations and dependents, niche medians and medals, snapshot ${snapshot.snapshot_date}.`;
}

export function nicheReportHref(s: NicheSummary): string {
  return `mailto:hello@evidaxis.org?subject=${encodeURIComponent(`Measurement correction: niche ${s.slug} / ${snapshot.snapshot_id}`)}`;
}

export const nicheCsvPath = (s: { slug: string }) => `/ai/cohorts/${s.slug}/systems.csv`;
export const nicheJsonPath = (s: { slug: string }) => `/ai/cohorts/${s.slug}/systems.json`;

const CSV_HEADER = ['entity_id', 'name', 'url', 'niche', 'measured_line', 'commits_per_week', 'citations_to_date', 'citations_state',
  'verified_direct_dependents', 'verified_dependents_state', 'direct_dependents_reading', 'stars_recorded_not_scored',
  'medal_multiple', 'medal_measure', 'medal_tier', 'rising', 'snapshot_id', 'snapshot_date'] as const;

const multipleValue = (ratio: number) => Number(ratioText(ratio).replace(/[×,]/g, ''));

function tableRecord(s: NicheSummary, row: HubRow) {
  return {
    entity_id: row.id, name: row.name, url: `${SITE}${row.url}`, niche: s.label, measured_line: row.measuredLine,
    commits_per_week: row.commits, citations_to_date: row.citations, citations_state: row.citationState,
    verified_direct_dependents: row.dependents, verified_dependents_state: row.dependentsState,
    direct_dependents_reading: row.dependentsReading, stars_recorded_not_scored: row.stars,
    medal_multiple: row.medal ? multipleValue(row.medal.ratio) : null, medal_measure: row.medal?.metric ?? null,
    medal_tier: row.medal?.tier ?? null, rising: s.assigned ? row.rising : null,
    snapshot_id: snapshot.snapshot_id, snapshot_date: snapshot.snapshot_date,
  };
}

/** All rows of a niche (never paginated), one CSV row per system. */
export function nicheCSV(s: NicheSummary): string {
  return csv([[...CSV_HEADER], ...s.rows.map((row) => { const r = tableRecord(s, row); return CSV_HEADER.map((key) => r[key]); })]);
}

export function nicheJSON(s: NicheSummary) {
  return {
    title: `${s.label}: systems measured by Evidaxis, snapshot ${snapshot.snapshot_date}`,
    license: 'CC0-1.0', license_url: CC0_URL,
    note: 'Released to the public domain under CC0 1.0. Same rows and columns as the niche table on the hub page, all systems, alphabetical by name. Order is not a rank.',
    niche: { key: s.key, slug: s.slug, label: s.label, assigned: s.assigned, field: s.field, url: `${SITE}/ai/cohorts/${s.slug}/` },
    snapshot: { snapshot_id: snapshot.snapshot_id, snapshot_date: snapshot.snapshot_date, period: snapshot.period, methodology_version: snapshot.methodology_version },
    n_systems: s.n,
    niche_medians: s.medians,
    answer: nicheAnswer(s),
    columns: {
      measured_line: 'The measured line shown in the table, generated from the readings.',
      commits_per_week: 'GitHub commits per week averaged over the trailing 12 weeks.',
      citations_to_date: 'OpenAlex citing works indexed to date, all years including the current one.',
      citations_state: 'scored, count_only (a count without a scored trend) or not_measured.',
      verified_direct_dependents: 'deps.dev direct dependents, shown only when the package identity is verified.',
      verified_dependents_state: 'scored, count_only or not_measured (not_measured when no verified package).',
      direct_dependents_reading: 'The deps.dev direct dependents reading used for the niche median, whether or not the package identity is verified.',
      stars_recorded_not_scored: 'GitHub stargazers; recorded, not scored.',
      medal_multiple: 'Multiple of the niche median (2, 10 and 100 are the bronze, silver and gold thresholds); blank without a medal.',
      medal_measure: 'citations or dependents.',
      rising: 'true when at least two of the three measures are rising together in this niche on this snapshot; blank for systems without a niche.',
    },
    systems: s.rows.map((row) => tableRecord(s, row)),
  };
}

/** Small static search index for the home page: every system in the latest snapshot. */
export function searchIndex(): { name: string; id: string }[] {
  return [...entities].sort((a, b) => a.name.localeCompare(b.name, 'en', { sensitivity: 'base' }) || a.entity_id.localeCompare(b.entity_id))
    .map((e) => ({ name: e.name, id: e.entity_id }));
}

/** Medal and Rising counts across the real niches of the latest snapshot. */
export function snapshotMedals() {
  const niches = assignedNiches();
  const medals = { gold: 0, silver: 0, bronze: 0 };
  for (const s of niches) { medals.gold += s.medals.gold; medals.silver += s.medals.silver; medals.bronze += s.medals.bronze; }
  const rising = niches.flatMap((s) => s.rising).sort((a, b) => a.name.localeCompare(b.name, 'en', { sensitivity: 'base' }));
  return { medals, rising };
}

