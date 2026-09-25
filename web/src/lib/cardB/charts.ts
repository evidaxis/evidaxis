import { fmt, numeric, metrics, type CardBModel } from './build';
import { xml } from './exports';
import { CHART_COPY } from './chart-copy';
import { assertPublicText, interpolate } from './facets';

export type Chart = { block: string; title: string; description: string; alt: string; source: string; date: string; claim: string; svg: string; url: string };
export function chartsFor(m: CardBModel): Record<string, Chart> {
  const charts: Record<string, Chart> = {};
  const reading = (key: string) => m.readings.find(r => r.key === key)!;
  const conclusion = (key: keyof typeof CHART_COPY, vars: Record<string, string | number>) =>
    interpolate(CHART_COPY[key], { name: m.entity.name, date: m.date, ...vars }, m.entity.name);
  const make = (block: string, type: string, title: string, metric: string, value: string, comparator: string | null, period: string, source: string, body: string, detail = '') => {
    const alt = `${type} chart: ${m.entity.name}, ${metric}, ${value}${comparator === null ? '' : ` vs niche median ${comparator}`}, ${period}`;
    const description = `${alt}. ${detail} Source: ${source}; captured ${m.date}.`;
    for (const s of [title, alt, description]) assertPublicText(s, m.entity.name);
    const claim = `urn:evidaxis:claim:class:chart_${block}:b1`;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 200" width="640" height="200" role="img" data-entity="${xml(m.entity.id)}" data-release="${xml(m.release)}" aria-labelledby="${block}-title ${block}-desc"><title id="${block}-title">${xml(title)}</title><desc id="${block}-desc">${xml(description)}</desc><rect width="640" height="200" fill="#fbfcfa"/>${body}</svg>`;
    charts[block] = { block, title, description, alt, source, date: m.date, claim, svg, url: `/charts/e/${m.entity.id}/${block}-${m.release}.svg` };
  };
  const text = (x: number, y: number, value: string, anchor = 'start', attrs = '') => `<text x="${x}" y="${y}" text-anchor="${anchor}" fill="#465552" font-family="sans-serif" font-size="11"${attrs}>${xml(value)}</text>`;
  const x = (i: number, length: number) => 40 + i * 410 / Math.max(length - 1, 1);
  const y = (v: number, max: number) => 165 - v / Math.max(max, 1) * 130;
  const axis = (max: number, left: string, right: string) => `<path d="M40 28V165H450" fill="none" stroke="#c9d4cf"/>${text(34, 169, '0', 'end')}${text(34, 37, fmt(max), 'end')}${text(40, 188, left)}${text(450, 188, right, 'end')}`;
  const line = (values: number[], max: number, color = '#0c6e63') => `<polyline points="${values.map((v, i) => `${x(i, values.length)},${y(v, max)}`).join(' ')}" fill="none" stroke="${color}" stroke-width="2.5"/>`;
  const labels = (values: number[], max: number, med: number | null, metric: string, period: string, unit: string) => {
    const value = values.at(-1)!, endX = x(values.length - 1, values.length), endY = y(value, max);
    let medY = med === null ? 0 : y(med, max);
    if (Math.abs(medY - endY) < 17) medY += medY > 145 ? -19 : 19;
    return `<circle cx="${endX}" cy="${endY}" r="3" fill="#0c6e63"/>`
      + text(endX + 9, endY + 4, `${fmt(value)} ${unit}`, 'start', ` data-chart-latest="${metric}" data-value="${value}" data-period="${xml(period)}"`)
      + (med === null ? '' : text(endX + 9, medY + 4, `niche median ${fmt(med)}`, 'start', ` data-chart-median="${metric}" data-value="${med}"`));
  };
  const commits = m.ruler.weeks.map(p => p.value);
  if (commits.length) {
    const max = Math.max(1, ...commits, ...(m.nicheAssigned ? m.commitBand.map(p => p.p75 ?? 0) : []));
    const band = m.commitBand;
    const upper = band.map((p, i) => `${x(i, commits.length)},${y(p.p75 ?? 0, max)}`);
    const lower = band.map((p, i) => `${x(i, commits.length)},${y(p.p25 ?? 0, max)}`).reverse();
    const rwc = reading('commits').value as number | null, med = m.medians.commits.value, last = m.ruler.weeks.at(-1)!;
    const key = rwc === null ? 'commits_missing' : rwc === 0 ? 'commits_zero' : med !== null && med > 0 ? 'commits_ratio' : 'commits';
    const ratio = rwc !== null && med ? rwc / med : null;
    const title = m.nicheAssigned
      ? conclusion(key, { value: fmt(rwc), median: fmt(med), ratio: ratio === null ? '' : ratio < 10 ? ratio.toFixed(1) : String(Math.round(ratio)), zero_weeks: m.ruler.zeroWeeks })
      : rwc === null ? `No commit reading for ${m.entity.name}.` : `${m.entity.name} averaged ${fmt(rwc)} commits a week.`;
    // The line and band compare raw weeks. The headline compares trailing
    // means; using that mean as a raw-week median would mix observations.
    const medians = band.map(p => p.median);
    const medianLine = medians.every(numeric) ? line(medians, max, '#bd783e') : '';
    make('commits', 'line', title, 'weekly commits', `${fmt(last.value)} in latest week`, m.nicheAssigned ? fmt(band.at(-1)?.median ?? null) : null, `${m.ruler.firstWeek} to ${last.date}`, 'GitHub commit_activity',
      axis(max, m.ruler.firstWeek!, last.date)
      + (m.nicheAssigned ? `<polygon points="${[...upper, ...lower].join(' ')}" fill="#dfece5"/>${medianLine}` : '') + line(commits, max)
      + labels(commits, max, m.nicheAssigned ? band.at(-1)?.median ?? null : null, 'weekly_commits', last.date, 'commits')
      + text(40, 16, m.nicheAssigned ? 'Raw weekly totals; niche P25-P75 band and weekly median' : 'Raw weekly totals'),
      'Week dates reconstructed from capture Sunday; the headline uses the trailing average.');
    const recent = commits.slice(-26), heatMax = Math.max(1, ...recent), active = recent.filter(v => v > 0).length;
    make('heatmap', 'heatmap', conclusion('heatmap', { active, weeks: recent.length }), 'weeks with commits', `${active} of ${recent.length}`, null,
      `${m.ruler.weeks.at(-recent.length)!.date} to ${last.date}`, 'GitHub commit_activity',
      recent.map((v, i) => `<rect x="${30 + i % 13 * 46}" y="${30 + Math.floor(i / 13) * 64}" width="40" height="40" rx="4" fill="#0c6e63" opacity="${.1 + .9 * v / heatMax}"/>${text(50 + i % 13 * 46, 85 + Math.floor(i / 13) * 64, fmt(v), 'middle')}`).join(''));
  }
  if (m.years.length) {
    const max = Math.max(1, ...m.years.map(p => p.value)), width = 398 / m.years.length, total = reading('citations').value as number | null;
    make('citations', 'bar', m.nicheAssigned ? conclusion('citations', { value: fmt(total), median: fmt(m.medians.citations.value) }) : `${fmt(total)} OpenAlex citing works for ${m.entity.name}.`, 'citing works', fmt(total), m.nicheAssigned ? fmt(m.medians.citations.value) : null,
      `${m.years[0].year}-${m.years.at(-1)!.year} completed years`, 'OpenAlex', axis(max, '', '')
      + m.years.map((p, i) => { const left = 52 + i * width, barWidth = Math.max(2, width - 12); return `<rect x="${left}" y="${y(p.value, max)}" width="${barWidth}" height="${165 - y(p.value, max)}" fill="#bd783e"/>${text(left, 188, String(p.year))}`
        + (i === m.years.length - 1 ? text(left + barWidth / 2, y(p.value, max) - 7, fmt(p.value), 'middle', ` data-chart-latest="yearly_citing_works" data-value="${p.value}" data-period="${p.year}"`) : ''); }).join(''));
  }
  const byPartition = new Map<string, number>();
  for (const p of m.history) {
    const axis = p.entity.axes.deps_direct_dependents_momentum, value = metrics(p.entity).dependents;
    if (axis?.as_of_partition && value !== null) byPartition.set(axis.as_of_partition, value);
  }
  if (byPartition.size) {
    const points = [...byPartition].sort(([a], [b]) => a.localeCompare(b)), values = points.map(([, v]) => v), med = m.medians.dependents.value;
    const max = Math.max(1, ...values, m.nicheAssigned ? med ?? 0 : 0), last = points.at(-1)!;
    const single = points.length === 1;
    make('dependents', 'sparkline', m.nicheAssigned ? conclusion('dependents', { value: fmt(last[1]), median: fmt(med) }) : `${fmt(last[1])} direct dependents on deps.dev for ${m.entity.name}.`, 'direct dependents', fmt(last[1]), m.nicheAssigned ? fmt(med) : null,
      single ? last[0] : `${points[0][0]} to ${last[0]}`, 'deps.dev weekly package union', single
        ? text(40, 100, `${fmt(last[1])} dependents · ${last[0]}`, 'start', ` data-chart-latest="dependents" data-value="${last[1]}" data-period="${xml(last[0])}"`)
        : axis(max, points[0][0], last[0])
          + (!m.nicheAssigned || med === null ? '' : `<path d="M40 ${y(med, max)}H450" stroke="#bd783e" stroke-dasharray="3 3"/>`) + line(values, max)
          + labels(values, max, m.nicheAssigned ? med : null, 'dependents', last[0], 'dependents'), m.nicheAssigned ? 'Repeated partitions appear once; the median is the current niche reading.' : 'Repeated partitions appear once.');
  }
  for (const [block, points, source, unit] of [
    ['daily', m.dailySeries, 'deps.dev REST (unscored)', 'daily dependents'],
    ['backfill', m.backfill, 'Git history reconstruction', 'reconstructed commits'],
  ] as const) {
    if (points.length < 2) continue;
    const values = points.map(p => p.value), max = Math.max(1, ...values), last = points.at(-1)!;
    make(block, 'sparkline', m.nicheAssigned ? conclusion(block, { value: fmt(last.value) }) : `${m.entity.name} recorded ${fmt(last.value)} ${unit}.`, unit, fmt(last.value), null,
      `${points[0].period} to ${last.period}`, source, axis(max, points[0].period, last.period) + line(values, max) + labels(values, max, null, block, last.period, ''));
  }
  const positions = m.nicheAssigned ? m.peers.filter(p => p.commits !== null) : [];
  if (m.nicheAssigned && positions.length) {
    const max = Math.max(1, ...positions.map(p => p.commits!)), med = m.medians.commits.value!, own = reading('commits').value as number | null;
    const px = (v: number) => 40 + v / max * 540;
    make('niche', 'dot plot', conclusion('niche', { value: fmt(own), systems: m.peers.length, median: fmt(med) }), 'averaged commits per week', fmt(own), fmt(med), m.date, 'GitHub, current cohort',
      `<path d="M40 165H580M${px(med)} 30V165" fill="none" stroke="#bd783e"/>`
      + positions.map((p, i) => `<circle cx="${px(p.commits!)}" cy="${72 + i % 5 * 14}" r="${p.id === m.entity.id ? 6 : 3}" fill="${p.id === m.entity.id ? '#0c6e63' : '#9dada5'}"/>${p.id === m.entity.id ? text(Math.min(500, Math.max(130, px(p.commits!))), 20, `${p.name}: ${fmt(p.commits)}`, 'middle') : ''}`).join('')
      + text(40, 188, '0 commits/wk') + text(580, 188, `${fmt(max)} commits/wk`, 'end') + text(Math.min(470, Math.max(110, px(med))), 153, `niche median ${fmt(med)}`, 'middle'));
  }
  const changes = m.changes.filter(p => numeric(p.current) && numeric(p.previous) && p.current !== p.previous);
  const previous = m.history.filter(p => p.snapshot.snapshot_date < m.date).at(-1)?.snapshot.snapshot_date;
  const count = changes.length;
  const firstCount = m.changes.filter(p => numeric(p.current)).length;
  const changeTitle = previous ? conclusion(count ? 'changes' : 'no_numeric_change', { count, previous }) : conclusion('first', { count: firstCount });
  make('changes', 'slope', changeTitle, previous ? 'changed published values' : 'measured values', String(previous ? count : firstCount), null,
    previous ? `${previous} to ${m.date}` : m.date, 'Evidaxis snapshots', changes.length ? changes.map((p, i) => {
      const row = 30 + i * 36;
      return text(24, row, p.label) + text(230, row, fmt(p.previous)) + `<path d="M310 ${row - 4}H440l-8 -4m8 4l-8 4" fill="none" stroke="#0c6e63"/>` + text(470, row, fmt(p.current));
    }).join('') : text(40, 100, previous ? `No numeric change since ${previous}` : `First observation ${m.date}`));
  return charts;
}
