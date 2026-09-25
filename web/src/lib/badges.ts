import { readFileSync } from 'node:fs';
import { makeBadge } from 'badge-maker';
import { entityUniverse, snapshots, type ArchivedEntity } from './archive';
import { metrics } from './cardB/build';
import { contextFor } from './cardB/context';
import { dataPath } from './data-path';
import { measurementStateFor } from './measurement';

export const BADGE_KEYS = ['medal', 'growth', 'citations', 'dependents', 'rising'] as const;
export type BadgeKey = typeof BADGE_KEYS[number];
export type BadgeStyle = 'flat' | 'flat-square' | 'for-the-badge';
export type Tier = 'gold' | 'silver' | 'bronze' | null;
const icons = {
  medal: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#fff" d="M7.5 2h3.2v5.4L12 6l1.3 1.4V2h3.2v7.6L12 13.5 7.5 9.6V2z"/><circle fill="#fff" cx="12" cy="16.8" r="5.2"/><circle fill="#C9A227" cx="12" cy="16.8" r="2.1"/></svg>',
  rising: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#fff" d="M13.2 3.5l6.8 6.8-1.7 1.7-3.7-3.7V20h-2.4V8.4l-3.7 3.7-1.7-1.7 6.4-6.9z"/></svg>',
  growth: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#fff" d="M4 18h3v-5H4v5zm6.5 0h3V8h-3v10zm6.5 0h3V4h-3v14z"/></svg>',
  count: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#fff" d="M8.5 4L7.8 8H4v2h3.4l-.9 4H3v2h3.1l-.7 4h2.4l.7-4h4l-.7 4h2.4l.7-4H20v-2h-3.5l.9-4H21V8h-4l.7-4h-2.4l-.7 4h-4l.7-4H8.5zm1.5 8h4l-.9 4h-4l.9-4z"/></svg>',
} as const;
export const LOGO_SVG = icons.count;

// Variant B (owner's choice 2026-09-24): a small medal in the tier's metal on a white ribbon.
const METAL = { gold: ['#f2c230', '#8a6508'], silver: ['#c9d1d9', '#6e7781'], bronze: ['#cd8a4f', '#7a4a24'] } as const;
export const medalIcon = (tier: Exclude<Tier, null>) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M6.5 1h4.2l1.8 6.2H8.3z" fill="#e8e8e8"/><path d="M17.5 1h-4.2l-1.8 6.2h4.2z" fill="#ffffff"/><circle cx="12" cy="15.6" r="7.4" fill="${METAL[tier][0]}"/><circle cx="12" cy="15.6" r="7.4" fill="none" stroke="${METAL[tier][1]}" stroke-width="1.2"/><circle cx="12" cy="15.6" r="4.4" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1.1"/></svg>`;

const xml = (s: string) => s.replace(/[<>&'"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[c]!));
const integer = (n: number) => Math.round(n).toLocaleString('en-US');
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'June', 'July', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'];
const dateForPeriod = new Map(snapshots.map(s => [s.period, s.snapshot_date]));

const pins = (JSON.parse(readFileSync(dataPath('deps_id_map.json'), 'utf8')) as { pins: Record<string, { linkage?: string }> }).pins;
export const verifiedPin = (record: ArchivedEntity) => pins[record.entity.github_repo]?.linkage === 'verified';
export const tierFor = (ratio: number): Tier => ratio >= 100 ? 'gold' : ratio >= 10 ? 'silver' : ratio >= 2 ? 'bronze' : null;
// Round DOWN so the printed multiple never reaches a tier the ratio has not reached (1.96 -> 1.9, 9.96 -> 9.9).
export const ratioText = (ratio: number) => ratio >= 10 ? `${Math.floor(ratio).toLocaleString('en-US')}×` : `${(Math.floor(ratio * 10) / 10).toFixed(1)}×`;
export const growthPercent = (a: number | undefined, b: number | undefined): number | null =>
  a !== undefined && b !== undefined && a >= 1 && b >= 10 && b / a - 1 >= .25 ? Math.round((b / a - 1) * 100) : null;
export function nicheCandidates(own: { citations: number | null; dependents: number | null },
  medians: Record<'citations' | 'dependents', { value: number | null; n: number }>, verified: boolean, cohort = '') {
  if (cohort === 'unassigned-v1') return [];
  return (['citations', 'dependents'] as const).flatMap(metric => {
    const value = own[metric], { value: median, n } = medians[metric];
    return value !== null && median !== null && n >= 5 && median >= 3 && (metric !== 'dependents' || verified)
      ? [{ metric, value, median, n, ratio: value / median }] : [];
  }).sort((a, b) => b.ratio - a.ratio);
}

// A missing entity in an intervening snapshot breaks a consecutive run.
export function latestRisingRun(record: ArchivedEntity): { start: string; end: string; live: boolean } | null {
  let run: { start: string; end: string } | null = null;
  let last: { start: string; end: string } | null = null;
  for (const snap of snapshots) {
    const entity = snap.entities.find(e => e.entity_id === record.entity.entity_id);
    if (entity && measurementStateFor(entity, snap).positive_signal.state === 'published') {
      run = { start: run?.start ?? snap.period, end: snap.period };
      last = run;
    } else run = null;
  }
  return last && { ...last, live: run !== null };
}

export function risingRange(start: string, end: string): string {
  const a = dateForPeriod.get(start) ?? start;
  const b = dateForPeriod.get(end) ?? end;
  const first = `${months[+a.slice(5, 7) - 1]} ${a.slice(0, 4)}`;
  if (a.slice(0, 7) === b.slice(0, 7)) return first;
  return a.slice(0, 4) === b.slice(0, 4)
    ? `${months[+a.slice(5, 7) - 1]}–${months[+b.slice(5, 7) - 1]} ${b.slice(0, 4)}`
    : `${first}–${months[+b.slice(5, 7) - 1]} ${b.slice(0, 4)}`;
}

type BadgeData = { label: string; message: string; color: string; title: string; count: number | null; offered: boolean; tier?: Tier; ratio?: number; metric?: 'citations' | 'dependents'; range?: string | null; niche?: string; logoSvg: string };
const cache = new WeakMap<ArchivedEntity, Map<BadgeKey, BadgeData>>();
export function badgeData(record: ArchivedEntity, key: BadgeKey): BadgeData {
  let byKey = cache.get(record);
  if (!byKey) { byKey = new Map(); cache.set(record, byKey); }
  const cached = byKey.get(key);
  if (cached) return cached;
  const { entity: e, snapshot: snap } = record;
  const own = metrics(e), verified = verifiedPin(record);
  const niche = (snap.cohorts[e.cohort]?.label ?? e.sub_niche).replace(/\u2014/g, ',');
  const measured = 'Measured weekly by Evidaxis.';
  let data: BadgeData;
  if (key === 'medal') {
    const medians = e.cohort === 'unassigned-v1'
      ? { citations: { value: null, n: 0 }, dependents: { value: null, n: 0 } }
      : contextFor(record).cohortSummary!.medians;
    const candidates = nicheCandidates(own, medians, verified, e.cohort);
    const best = candidates[0]?.ratio >= 1 ? candidates[0] : undefined;
    const fallback = (['citations', 'dependents'] as const).filter(metric => metric === 'citations' || verified)
      .sort((a, b) => (own[b] ?? -1) - (own[a] ?? -1))[0];
    const metric = best?.metric ?? fallback;
    const count = own[metric];
    const ratio = best?.ratio;
    const comparison = best && ratio !== undefined;
    const tier = comparison ? tierFor(ratio) : null;
    const color = tier === 'gold' ? '#b8860b' : tier === 'silver' ? '#8a9299' : tier === 'bronze' ? '#a86b3c' : '#57606a';
    const message = comparison ? `${ratioText(ratio)} niche median` : count === null ? 'not measured' : integer(count);
    const title = comparison
      ? `${e.name} has ${ratioText(ratio).replace('×', ' times more')} ${metric === 'citations' ? 'OpenAlex citations' : 'direct dependents'} (${integer(best.value)}) than the median system in its niche, ${niche} (${integer(best.median)}; n = ${best.n}). ${tier ? `${tier[0].toUpperCase()}${tier.slice(1)} tier. ` : ''}Gold is awarded at 100× or more, silver at 10×, bronze at 2×. ${measured}`
      : `${e.name}: ${count === null ? `no ${metric} reading` : `${integer(count)} ${metric}`} in the latest weekly record (${snap.snapshot_date}). ${measured}`;
    data = { label: metric, message, color: count === null ? '#9f9f9f' : color, title, count, offered: !!tier, tier, ratio, metric, niche, logoSvg: tier ? medalIcon(tier) : icons.medal.replace('#C9A227', color) };
  } else if (key === 'growth') {
    const year = +snap.snapshot_date.slice(0, 4) - 1;
    const years = e.axes.openalex_citation_momentum.by_year ?? {};
    const a = years[String(year - 1)], b = years[String(year)];
    const percent = growthPercent(a, b);
    const hasReading = own.citations !== null;
    const message = percent !== null ? `+${percent}%` : b !== undefined && hasReading ? integer(b) : 'not measured';
    data = { label: `citations ${year}`, message, color: percent !== null ? '#0e7c86' : message === 'not measured' ? '#9f9f9f' : '#57606a',
      title: percent !== null ? `${e.name}: ${integer(b)} citing works in ${year}, up ${percent}% from ${integer(a)} in ${year - 1} (OpenAlex). ${measured}` : `${e.name}: ${message} citing works in ${year} (OpenAlex). ${measured}`,
      count: b ?? null, offered: percent !== null, logoSvg: icons.growth };
  } else if (key === 'rising') {
    const run = latestRisingRun(record);
    const range = run ? risingRange(run.start, run.end) : null;
    const message = run?.live ? niche : range ?? 'not published';
    data = { label: 'rising', message, color: run?.live ? '#2da44e' : run ? '#6e7b8b' : '#9f9f9f',
      title: run ? `${e.name}: Rising signal in ${niche}, ${run.live ? 'published in the latest snapshot' : `recorded ${range}`}. A system is Rising only when its cohort has at least 5 members, at least two axes are present, and at least two are rising at once. Recorded ${snap.snapshot_date}. Evidaxis.` : `${e.name}: no published Rising signal.`,
      count: null, offered: !!run, range, niche, logoSvg: icons.rising };
  } else {
    const count = own[key];
    if (count !== null && !Number.isInteger(count)) throw new Error(`${key} count is not an integer for ${e.entity_id}`);
    const unverified = key === 'dependents' && count !== null && !verified;
    const message = unverified ? 'unverified' : count === null ? 'not measured' : integer(count);
    const reason = key === 'citations' ? e.openalex_work_ids.length ? 'No reading was captured for the linked paper.' : 'No paper is linked in OpenAlex.'
      : e.axes?.deps_direct_dependents_momentum?.status === 'out_of_panel' ? 'The system is outside the deps.dev panel.' : 'No deps.dev partition reading was captured.';
    const title = unverified ? `${e.name}: ${integer(count!)} dependents are measured, but the package identity is not verified. Recorded ${snap.snapshot_date} by Evidaxis.`
      : count === null ? `${e.name}: no ${key} reading in the latest weekly record (${snap.snapshot_date}). ${reason}`
      : key === 'citations' ? `${e.name}: ${message} citing works in OpenAlex indexed to date, including the current year. Recorded ${snap.snapshot_date} by Evidaxis, updated weekly.`
      : `${e.name}: ${message} packages depend on it directly (deps.dev, partition ${e.axes?.deps_direct_dependents_momentum?.as_of_partition ?? snap.snapshot_date}). Recorded weekly by Evidaxis.`;
    data = { label: key, message, color: unverified || count === null ? '#9f9f9f' : '#57606a', title, count,
      offered: key === 'citations' ? count !== null && count >= 20 : verified && count !== null && count >= 10, logoSvg: icons.count };
  }
  byKey.set(key, data);
  return data;
}

export function chooseBadges(input: { rising: 'live' | 'ended' | null; medal: boolean; growth: boolean; count: 'citations' | 'dependents' | null }): { main: BadgeKey | null; extras: BadgeKey[] } {
  const main = input.rising === 'live' ? 'rising' : input.medal ? 'medal' : input.rising === 'ended' ? 'rising'
    : input.growth ? 'growth' : input.count;
  const options: BadgeKey[] = [
    ...(input.medal ? ['medal' as const] : []),
    ...(input.rising === 'ended' ? ['rising' as const] : []),
    ...(input.growth ? ['growth' as const] : []),
    ...(input.count ? [input.count] : []),
  ];
  return { main, extras: options.filter(key => key !== main).slice(0, 2) };
}
export function builderSelection(record: ArchivedEntity): { main: BadgeKey | null; extras: BadgeKey[] } {
  const rising = badgeData(record, 'rising');
  const medal = badgeData(record, 'medal');
  const growth = badgeData(record, 'growth');
  const counts = (['citations', 'dependents'] as const).filter(key => badgeData(record, key).offered)
    .sort((a, b) => (badgeData(record, b).count ?? 0) - (badgeData(record, a).count ?? 0));
  const count = counts[0];
  const run = latestRisingRun(record);
  return chooseBadges({ rising: rising.offered ? run?.live ? 'live' : 'ended' : null,
    medal: medal.offered, growth: growth.offered, count: count ?? null });
}

export function rowSvg(record: ArchivedEntity, key: BadgeKey, style: BadgeStyle): string {
  const data = badgeData(record, key);
  const rendered = makeBadge({ label: data.label, message: data.message, color: data.color, labelColor: '#555', style,
    logoBase64: `data:image/svg+xml;base64,${Buffer.from(data.logoSvg).toString('base64')}` });
  return rendered.replace(/aria-label="[^"]*"/, `aria-label="${xml(data.title)}"`)
    .replace(/<title>[^<]*<\/title>/, `<title>${xml(data.title)}</title>`);
}

export function endpointJson(record: ArchivedEntity, key: BadgeKey) {
  const data = badgeData(record, key);
  return { schemaVersion: 1, label: data.label, message: data.message, color: data.color.slice(1), labelColor: '555', logoSvg: data.logoSvg, cacheSeconds: 21600 };
}

export function risingCardSvg(record: ArchivedEntity): string {
  const data = badgeData(record, 'rising');
  if (!data.range) throw new Error(`No Rising run for ${record.entity.entity_id}`);
  const sub = latestRisingRun(record)?.live ? data.niche! : data.range;
  const visible = sub.length > 33 ? `${sub.slice(0, 32).trimEnd()}…` : sub;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="250" height="54" viewBox="0 0 250 54" role="img" aria-label="${xml(data.title)}"><title>${xml(data.title)}</title><style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}.bg{fill:#fff}.border{stroke:#d0d7de}.main{fill:#1f2328}.sub{fill:#59636e}@media (prefers-color-scheme:dark){.bg{fill:#0d1117}.border{stroke:#3d444d}.main{fill:#f0f6fc}.sub{fill:#9198a1}}</style><rect class="bg border" x=".5" y=".5" width="249" height="53" rx="6"/><path d="M4 1v52" stroke="${data.color}" stroke-width="4"/><g transform="translate(13 13)">${icons.rising.replace('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">', '').replace('fill="#fff"', `fill="${data.color}"`).replace('</svg>', '')}</g><text class="main" x="49" y="25" font-size="14" font-weight="700">RISING</text><text class="sub" x="49" y="42" font-size="10">${xml(visible)}</text><text class="sub" x="239" y="13" text-anchor="end" font-size="8">evidaxis.org</text></svg>`;
}

export const badgeRecords = entityUniverse;
export const risingRecords = entityUniverse.filter(record => latestRisingRun(record));
const stableSvgNames = new Set(['medal', 'medal-flat-square', 'medal-for-the-badge', 'growth', 'growth-flat-square', 'growth-for-the-badge', 'citations', 'citations-flat-square', 'citations-for-the-badge', 'dependents', 'dependents-flat-square', 'dependents-for-the-badge', 'rising', 'rising-flat-square', 'rising-for-the-badge', 'rising-card']);
for (const record of entityUniverse) {
  if (stableSvgNames.has(record.snapshot.period)) throw new Error(`Dated badge path collides with stable badge path: ${record.entity.entity_id}/${record.snapshot.period}.svg`);
}
export function badgePaths(records = badgeRecords) {
  return records.map(record => ({ params: { id: record.entity.entity_id }, props: { record } }));
}
