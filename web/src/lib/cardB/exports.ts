import { metrics, type CardBModel } from './build';

const csvCell = (v: unknown) => {
  const text = v === null || v === undefined ? '' : String(v);
  // Spreadsheet formula prefixes are escaped only in textual cells; a negative
  // measured number must retain its numeric meaning in a CC0 download.
  const safe = typeof v === 'string' && /^[=+@-]/.test(text) ? `'${text}` : text;
  return /[",\r\n]/.test(safe) ? `"${safe.replaceAll('"', '""')}"` : safe;
};
export const csv = (rows: unknown[][]) => rows.map(row => row.map(csvCell).join(',')).join('\r\n') + '\r\n';
export const xml = (v: string) => v.replace(/[<>&"']/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&apos;' }[c]!));

export function valuesCSV(m: CardBModel) {
  return csv([
    ['entity_id', 'release_id', 'metric', 'period', 'value', 'unit', 'source', 'captured_date', 'definition', 'niche_median', 'n', 'delta_4w', 'delta_26w', 'range_52w_min', 'range_52w_max', 'previous_reading', 'niche_p25', 'niche_p75'],
    ...m.readings.filter(r => !Array.isArray(r.value)).map(r => [m.entity.id, m.release, r.key, r.date, r.value, r.unit, r.source, m.date, r.definition, r.median, r.n, r.delta4, r.delta26, r.range?.[0], r.range?.[1], r.previous, '', '']),
    ...m.ruler.weeks.map((p, i) => [m.entity.id, m.release, 'weekly_commits', p.date, p.value, 'commits', m.readings.find(r => r.key === 'commit_series')!.source, m.date, 'Week start reconstructed from capture Sunday; original timestamps not retained', m.commitBand[i]?.median, m.commitBand[i]?.n, '', '', '', '', '', m.commitBand[i]?.p25, m.commitBand[i]?.p75]),
    ...m.years.map(p => [m.entity.id, m.release, 'yearly_citing_works', p.year, p.value, 'citing works', m.readings.find(r => r.key === 'citation_series')!.source, m.date, 'Completed calendar year', '', '', '', '', '', '', '', '', '']),
  ]);
}
export function historyCSV(m: CardBModel) {
  return csv([['entity_id', 'snapshot_id', 'snapshot_date', 'captured_at', 'commits_per_week', 'citing_works', 'direct_dependents', 'dependents_partition', 'daily_dependents_unscored', 'stars'],
    ...m.history.map(p => { const v = metrics(p.entity); return [m.entity.id, p.snapshot.snapshot_id, p.snapshot.snapshot_date, p.snapshot.captured_at,
      v.commits, v.citations, v.dependents, p.entity.axes.deps_direct_dependents_momentum?.as_of_partition ?? null, p.daily?.value ?? null, v.stars]; }),
  ]);
}
export function cohortCSV(m: CardBModel) {
  return csv([['entity_id', 'name', 'commits_per_week', 'citing_works', 'direct_dependents', 'stars', 'snapshot_id', 'snapshot_date', 'momentum', 'percentile'],
    ...m.peers.map(p => [p.id, p.name, p.commits, p.citations, p.dependents, p.stars, m.snapshot_id, m.date, p.momentum, p.percentile]),
  ]);
}

export function systemFeed(m: CardBModel) {
  let previous: string | null = null;
  const items: { id: string; url: string; title: string; date_published: string; content_text: string; _evidaxis: object }[] = [];
  for (const p of m.history) {
    const values = { ...metrics(p.entity), weekly_commits: p.commits, citations_by_year: p.entity.axes?.openalex_citation_momentum?.by_year ?? null, daily_dependents: p.daily?.value ?? null };
    const signature = JSON.stringify(values);
    if (signature === previous) continue;
    previous = signature;
    const release = `${p.snapshot.snapshot_id}-b1`;
    items.push({ id: `${m.url}#reading-${release}`, url: `${m.url}values-${release}.csv`,
      title: `${m.entity.name}: published readings, ${p.snapshot.snapshot_date}`, date_published: p.snapshot.captured_at,
      content_text: `${m.entity.name}, snapshot ${p.snapshot.snapshot_date}: ${Object.entries(metrics(p.entity)).filter(([, v]) => v !== null).map(([k, v]) => `${k} ${v}`).join('; ')}.`,
      _evidaxis: { entity_id: m.entity.id, release_id: release, values },
    });
  }
  return { version: 'https://jsonfeed.org/version/1.1', title: `${m.entity.name}: Evidaxis readings`,
    home_page_url: m.url, feed_url: `${m.url}feed.json`, authors: [{ name: 'Evidaxis' }], items: items.reverse() };
}
export function systemAtom(m: CardBModel) {
  const feed = systemFeed(m);
  const entries = feed.items.map(i => `<entry><id>${xml(i.id)}</id><title>${xml(i.title)}</title><link href="${xml(i.url)}"/><updated>${xml(i.date_published)}</updated><content type="text">${xml(i.content_text)}</content></entry>`).join('');
  return `<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom"><id>${xml(m.url)}feed.atom</id><title>${xml(feed.title)}</title><author><name>Evidaxis</name></author><updated>${xml(feed.items[0]?.date_published ?? `${m.date}T00:00:00Z`)}</updated><link rel="self" href="${xml(m.url)}feed.atom"/><link rel="alternate" href="${xml(m.url)}"/>${entries}</feed>\n`;
}
