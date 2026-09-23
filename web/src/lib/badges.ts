import { makeBadge } from 'badge-maker';
import { entityUniverse, snapshots, type ArchivedEntity } from './archive';
import { metrics } from './cardB/build';
import { measurementStateFor } from './measurement';

export const LOGO_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"><path d="M1 23 L12 12 L23 2"/><path d="M1 23 L12 12 L23 21"/></g><circle cx="12" cy="12" r="2.8" fill="#fff"/></svg>';
export const BADGE_KEYS = ['citations', 'dependents', 'rising'] as const;
export type BadgeKey = typeof BADGE_KEYS[number];
export type BadgeStyle = 'flat' | 'flat-square' | 'for-the-badge';
const logoBase64 = `data:image/svg+xml;base64,${Buffer.from(LOGO_SVG).toString('base64')}`;
const xml = (s: string) => s.replace(/[<>&'"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[c]!));

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

export function badgeData(record: ArchivedEntity, key: BadgeKey) {
  const { entity: e, snapshot: snap } = record;
  const own = metrics(e);
  const run = latestRisingRun(record);
  const range = run ? run.live ? `since ${run.start}` : `${run.start}–${run.end}` : null;
  const niche = (snap.cohorts[e.cohort]?.label ?? e.sub_niche).replace(/\u2014/g, ',');
  const count = key === 'citations' ? own.citations : key === 'dependents' ? own.dependents : null;
  if (count !== null && !Number.isInteger(count)) throw new Error(`${key} count is not an integer for ${e.entity_id}`);
  const message = key === 'rising' ? range ?? 'not published' : count === null ? 'not measured' : Math.round(count).toLocaleString('en-US');
  const color = key === 'rising' ? '#b0641c' : count === null ? '#9f9f9f' : '#0c6e63';
  const reason = key === 'citations' ? e.openalex_work_ids.length ? 'No reading was captured for the linked paper.' : 'No paper is linked in OpenAlex.'
    : e.axes?.deps_direct_dependents_momentum?.status === 'out_of_panel' ? 'The system is outside the deps.dev panel.' : 'No deps.dev partition reading was captured.';
  const title = key === 'rising'
    ? `${e.name}: Rising signal in ${niche} ${range}. A system is Rising only when its cohort has at least 5 members, at least two axes are present, and at least two are rising at once. Recorded ${snap.snapshot_date}. Evidaxis.`
    : count === null ? `${e.name}: no ${key} reading in the latest weekly record (${snap.snapshot_date}). ${reason}`
    : key === 'citations' ? `${e.name}: ${message} citing works in OpenAlex over published completed calendar years. Recorded ${snap.snapshot_date} by Evidaxis, updated weekly.`
    : `${e.name}: ${message} packages depend on it directly (deps.dev, partition ${e.axes?.deps_direct_dependents_momentum?.as_of_partition ?? snap.snapshot_date}). Recorded weekly by Evidaxis.`;
  return { label: key, message, color, title, range, niche, count, offered: key === 'rising' ? !!run : count !== null && count > 0 };
}

export function rowSvg(record: ArchivedEntity, key: BadgeKey, style: BadgeStyle): string {
  const data = badgeData(record, key);
  const rendered = makeBadge({ label: key, message: data.message, color: data.color, labelColor: '#555', style, logoBase64 });
  return rendered.replace(/aria-label="[^"]*"/, `aria-label="${xml(data.title)}"`)
    .replace(/<title>[^<]*<\/title>/, `<title>${xml(data.title)}</title>`);
}

export function endpointJson(record: ArchivedEntity, key: BadgeKey) {
  const data = badgeData(record, key);
  return { schemaVersion: 1, label: key, message: data.message, color: data.color.slice(1), labelColor: '555', logoSvg: LOGO_SVG, cacheSeconds: 21600 };
}

export function risingCardSvg(record: ArchivedEntity): string {
  const data = badgeData(record, 'rising');
  if (!data.range) throw new Error(`No Rising run for ${record.entity.entity_id}`);
  const maxChars = Math.max(5, 31 - data.range.length); // about 34 characters fit in 190px at 10px, minus " · "
  const niche = data.niche.length > maxChars ? `${data.niche.slice(0, maxChars - 1).trimEnd()}…` : data.niche;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="250" height="54" viewBox="0 0 250 54" role="img" aria-label="${xml(data.title)}"><title>${xml(data.title)}</title><style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}.bg{fill:#fff}.border{stroke:#d0d7de}.main{fill:#1f2328}.sub{fill:#59636e}@media (prefers-color-scheme:dark){.bg{fill:#0d1117}.border{stroke:#3d444d}.main{fill:#f0f6fc}.sub{fill:#9198a1}}</style><rect class="bg border" x=".5" y=".5" width="249" height="53" rx="6"/><path d="M4 1v52" stroke="#b0641c" stroke-width="4"/><g transform="translate(13 13)" fill="none" stroke-linecap="round"><path d="M0 24 12 12 24 2" stroke="#b0641c" stroke-width="2"/><path d="M0 24 12 12 24 22" stroke="#0c6e63" stroke-width="2"/><circle class="main" cx="12" cy="12" r="2.8" stroke="none"/></g><text class="main" x="49" y="25" font-size="14" font-weight="700">RISING</text><text class="sub" x="49" y="42" font-size="10">${xml(niche)} · ${xml(data.range)}</text><text class="sub" x="239" y="13" text-anchor="end" font-size="8">evidaxis.org</text></svg>`;
}

export const badgeRecords = entityUniverse;
export const risingRecords = entityUniverse.filter(record => latestRisingRun(record));
const stableSvgNames = new Set(['citations', 'citations-flat-square', 'citations-for-the-badge', 'dependents', 'dependents-flat-square', 'dependents-for-the-badge', 'rising', 'rising-flat-square', 'rising-for-the-badge', 'rising-card']);
for (const record of entityUniverse) {
  if (stableSvgNames.has(record.snapshot.period)) throw new Error(`Dated badge path collides with stable badge path: ${record.entity.entity_id}/${record.snapshot.period}.svg`);
}
export function badgePaths(records = badgeRecords) {
  return records.map(record => ({ params: { id: record.entity.entity_id }, props: { record } }));
}
