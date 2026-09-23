import { fmt, numeric, metrics, type CardBModel } from './build';
import { xml } from './exports';

export type Chart = { block: string; title: string; description: string; svg: string; url: string };
export function chartsFor(m: CardBModel): Record<string, Chart> {
  const charts: Record<string, Chart> = {};
  const rd = (key: string) => (m.readings as Array<{ key: string; value: unknown; median: number | null }>).find(r => r.key === key);
  const vs = (key: string, unit: string): string => {
    const r = rd(key);
    if (!r || typeof r.value !== 'number') return '';
    return `Latest ${fmt(r.value)} ${unit}${r.median === null ? '' : `, niche median ${fmt(r.median)}`}. `;
  };
  const lead: Record<string, string> = { commits: vs('commits', 'commits per week averaged'), citations: vs('citations', 'citing works'), dependents: vs('dependents', 'direct dependents') };
  const make = (block: string, title: string, description0: string, body: string) => {
    const description = `${lead[block] ?? ''}${description0}`;
    const label = `${m.entity.name}: ${title}`;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 200" width="640" height="200" role="img" aria-labelledby="${block}-title ${block}-desc"><title id="${block}-title">${xml(label)}</title><desc id="${block}-desc">${xml(description)}</desc><rect width="640" height="200" fill="#fbfcfa"/>${body}</svg>`;
    charts[block] = { block, title: label, description, svg, url: `/charts/e/${m.entity.id}/${block}-${m.release}.svg` };
  };
  const text = (x: number, y: number, value: string, anchor = 'start') => `<text x="${x}" y="${y}" text-anchor="${anchor}" fill="#465552" font-family="sans-serif" font-size="11">${xml(value)}</text>`;
  const axis = (max: number, left: string, right: string) => `<path d="M40 22V165H612" fill="none" stroke="#c9d4cf"/>${text(34, 169, '0', 'end')}${text(34, 26, fmt(max), 'end')}${text(40, 188, left)}${text(612, 188, right, 'end')}`;
  const line = (values: number[], max: number, color = '#0c6e63') => `<polyline points="${values.map((v, i) => `${40 + i * 572 / Math.max(values.length - 1, 1)},${165 - v / Math.max(max, 1) * 140}`).join(' ')}" fill="none" stroke="${color}" stroke-width="2.5"/>`;
  const commits = m.ruler.weeks.map(p => p.value);
  if (commits.length) {
    const max = Math.max(1, ...commits, ...m.commitBand.map(p => p.p75 ?? 0));
    const upper = m.commitBand.map((p, i) => `${40 + i * 572 / Math.max(commits.length - 1, 1)},${165 - (p.p75 ?? 0) / max * 140}`);
    const lower = m.commitBand.map((p, i) => `${40 + i * 572 / Math.max(commits.length - 1, 1)},${165 - (p.p25 ?? 0) / max * 140}`).reverse();
    make('commits', 'Weekly commits and niche P25-P75', `${commits.length} captured weekly totals, ${m.ruler.firstWeek} to ${m.ruler.weeks.at(-1)!.date}. Shading is the niche interquartile band. Week dates reconstructed from capture Sunday.`,
      axis(max, m.ruler.firstWeek!, m.ruler.weeks.at(-1)!.date) + `<polygon points="${[...upper, ...lower].join(' ')}" fill="#dfece5"/>` + line(commits, max));
    const recent = commits.slice(-26), heatMax = Math.max(1, ...recent);
    make('heatmap', 'Commit heatmap, last 26 weeks', `${recent.length} weekly counts; darker squares mean more commits.`,
      recent.map((v, i) => `<rect x="${30 + (i % 13) * 46}" y="${30 + Math.floor(i / 13) * 64}" width="40" height="40" rx="4" fill="#0c6e63" opacity="${.1 + .9 * v / heatMax}"/>${text(50 + i % 13 * 46, 85 + Math.floor(i / 13) * 64, fmt(v), 'middle')}`).join(''));
  }
  if (m.years.length) {
    const max = Math.max(1, ...m.years.map(p => p.value)), width = 550 / m.years.length;
    make('citations', 'Citing works by completed calendar year', 'OpenAlex citing works; bars start at zero. See the adjacent annual table and source work IDs.',
      axis(max, '', '') + m.years.map((p, i) => `<rect x="${52 + i * width}" y="${165 - p.value / max * 140}" width="${Math.max(2, width - 12)}" height="${p.value / max * 140}" fill="#bd783e"/>${text(52 + i * width, 188, String(p.year))}`).join(''));
  }
  const byPartition = new Map<string, number>();
  for (const p of m.history) {
    const axis = p.entity.axes.deps_direct_dependents_momentum, value = metrics(p.entity).dependents;
    if (axis?.as_of_partition && value !== null) byPartition.set(axis.as_of_partition, value);
  }
  if (byPartition.size) {
    const points = [...byPartition].sort(([a], [b]) => a.localeCompare(b)), values = points.map(([, v]) => v), max = Math.max(1, ...values);
    make('dependents', 'Weekly direct dependents', 'deps.dev package-union readings by partition; repeated partitions appear once.', axis(max, points[0][0], points.at(-1)![0]) + line(values, max));
  }
  for (const [block, points, title, description] of [
    ['daily', m.dailySeries, 'Daily dependents (unscored)', 'Captured deps.dev REST readings. This series is not the scored weekly package-union axis.'],
    ['backfill', m.backfill, 'Reconstructed commit history', 'Reconstructed from git history, not a point-in-time capture.'],
  ] as const) {
    if (points.length < 2) continue;
    const values = points.map(p => p.value), max = Math.max(1, ...values);
    make(block, title, description, axis(max, points[0].period, points.at(-1)!.period) + line(values, max));
  }
  const positions = m.peers.filter(p => p.commits !== null);
  if (positions.length) {
    const max = Math.max(1, ...positions.map(p => p.commits!)), median = m.medians.commits.value!;
    make('niche', 'Commits per week across the niche', 'Each point is one system; the focal system is labelled. The vertical line is the niche median.',
      axis(max, '0 commits/wk', `${fmt(max)} commits/wk`) + `<path d="M${40 + median / max * 572} 30V160" stroke="#bd783e" stroke-width="2"/>`
      + positions.map((p, i) => `<circle cx="${40 + p.commits! / max * 572}" cy="${72 + (i % 5) * 14}" r="${p.id === m.entity.id ? 6 : 3}" fill="${p.id === m.entity.id ? '#0c6e63' : '#9dada5'}"/>${p.id === m.entity.id ? text(Math.min(570, Math.max(75, 40 + p.commits! / max * 572)), 53, p.name, 'middle') : ''}`).join('')
      + text(40, 18, `${m.entity.name}: ${fmt(positions.find(p => p.id === m.entity.id)?.commits ?? null)}; niche median ${fmt(median)}`));
  }
  const changes = m.changes.filter(p => numeric(p.current) && numeric(p.previous));
  if (changes.length) {
    make('changes', 'Changes since the previous snapshot', 'Each row has its own scale and unit. Read the paired values and deltas in the table.',
      changes.map((p, i) => { const y = 30 + i * 36; return text(24, y, p.label) + text(230, y, fmt(p.previous)) + `<path d="M310 ${y - 4}H440l-8 -4m8 4l-8 4" fill="none" stroke="#0c6e63"/>` + text(470, y, fmt(p.current)); }).join(''));
  }
  return charts;
}
