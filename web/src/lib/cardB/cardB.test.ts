import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { archiveEntityById } from '../archive';
import { deriveMeasurementState } from '../measurement';
import { buildCardB, commitRuler, median, metrics, paperRef, type Context } from './build';
import { contextFor } from './context';
import { selectClasses, assertPublicText, interpolate } from './facets';
import { FACETS } from '../../data/card-b-facets';
import { isIndexable, isTemplateB, HEADLINE_EXPERIMENT, CROCKFORD } from './policy.mjs';
import { valuesCSV, historyCSV, systemFeed, systemAtom } from './exports';
import { chartsFor } from './charts';
import { CARD_B_CLIENT } from './client';

const ids = ['e_S7DQ1QJCCMT', 'e_88YAM3PXK4S', 'e_X33782S1M13', 'e_97SYW64PA3G', 'e_03QFRGK7VQX', 'e_093XKS44M6Q', 'e_Y3HMWAG1BQZ', 'e_7ZJR0NT1B6H', 'e_9SWWW2SWASG', 'e_KR3M8ESKAEW', 'e_H6PPP8CA9RR', 'e_QTVWFV6FJ2V'];
const render = (id: string) => { const r = archiveEntityById.get(id)!; return buildCardB(r, contextFor(r)); };
const input = { commits: 10, zeroWeeks: 0, commitWeeks: 52, axes: 1, citations: null, paperLinked: false, years: 0, registryMedian: 20, dependents: null, depsStatus: 'out_of_panel', points: null, rising: false, incumbent: false, observations: 4 };

describe('Card B assignment and facet predicates', () => {
  it('uses Crockford ordinals and excludes every headline URL, including alternate URL spellings', () => {
    for (const [i, char] of [...CROCKFORD].entries()) expect(isTemplateB(`e_0000000000${char}`)).toBe(i % 2 === 0);
    for (const url of HEADLINE_EXPERIMENT) {
      const id = new URL(url).pathname.split('/')[2];
      expect(isTemplateB(id, url)).toBe(false);
      expect(isTemplateB(id, `/e/${id}`)).toBe(false);
      expect(isTemplateB(id, '/unrelated/')).toBe(false);
    }
    expect(() => isTemplateB('e_invalid!')).toThrow();
  });
  it('keeps a measured zero separate from a missing partition reading', () => {
    expect(selectClasses({ ...input, depsStatus: 'below_floor', dependents: 0 }).dependents).toBe('C13');
    expect(selectClasses({ ...input, depsStatus: 'below_floor', dependents: null }).dependents).toBe('C13b');
    expect(selectClasses({ ...input, depsStatus: 'out_of_panel', dependents: 0 }).dependents).toBe('C11');
    expect(selectClasses({ ...input, depsStatus: 'below_floor', dependents: 2 }).dependents).toBe('C12');
    expect(selectClasses({ ...input, depsStatus: 'held', dependents: 8 }).dependents).toBe('C14');
    expect(selectClasses({ ...input, depsStatus: 'scored', dependents: 8 }).dependents).toBe('C10a');
  });
  it('chooses exactly one ordered class per facet, including conflicts', () => {
    expect(selectClasses({ ...input, commits: 0, zeroWeeks: 52 }).code).toBe('C06');
    expect(selectClasses({ ...input, commits: 0, zeroWeeks: 12 }).code).toBe('C15c');
    expect(selectClasses({ ...input, commits: null }).code).toBe('C00');
    expect(selectClasses({ ...input, commits: .5 }).code).toBe('C15b');
    expect(selectClasses(input).code).toBe('C15a');
    expect(selectClasses({ ...input, axes: 2 }).code).toBe('C16');
    expect(selectClasses({ ...input, citations: 0, years: 1 }).citations).toBe('C07');
    expect(selectClasses({ ...input, paperLinked: true }).citations).toBe('C_NO_CITATION');
    expect(selectClasses({ ...input, citations: 20, years: 3 }).citations).toBe('C08');
    expect(selectClasses({ ...input, citations: 19, years: 3 }).citations).toBe('C09');
    expect(selectClasses({ ...input, rising: true, incumbent: true, observations: 1 }).standing).toBe('C01');
    expect(selectClasses({ ...input, incumbent: true, observations: 1 }).standing).toBe('C02');
    expect(selectClasses({ ...input, observations: 1 }).standing).toBe('C03');
  });
  it('fails closed on undefined predicate inputs, even for a later rule', () => {
    for (const key of Object.keys(input)) expect(() => selectClasses({ ...input, [key]: undefined } as any)).toThrow(/Undefined/);
    const r = structuredClone(archiveEntityById.get(ids[0])!);
    delete (r.entity.axes.github_commit_velocity as any).stars_not_scored;
    expect(() => metrics(r.entity)).toThrow(/Undefined/);
  });
});

describe('readings, sources and text boundaries', () => {
  it('derives the ruler from all 52 raw points, including trailing zero weeks', () => {
    const values = Array.from({ length: 52 }, (_, i) => i < 49 ? i + 1 : 0);
    const r = commitRuler(values, '2026-09-19T12:00:00Z');
    expect(r.zeroWeeks).toBe(3);
    expect(r.lastCommitWeek).toBe('2026-08-23');
    expect(r.delta4).toBe(-48); expect(r.delta26).toBe(-26); expect(r.range).toEqual([0, 49]);
    expect(commitRuler(Array(52).fill(0), '2026-09-19').lastCommitWeek).toBeNull();
    expect(commitRuler([], '2026-09-19').range).toBeNull();
  });
  it('does not invent an average delta from different rounding or a missing comparison date', () => {
    const r = structuredClone(archiveEntityById.get(ids[0])!), ctx = contextFor(r);
    r.entity.axes.github_commit_velocity.recent_weekly_commits = .3;
    const commits = Array.from({ length: 52 }, (_, i) => i % 3 === 0 ? 1 : 0);
    const m = buildCardB(r, { ...ctx, commits, history: [] });
    expect(m.readings.find(r => r.key === 'commits')!.delta4).toBe(0);
    expect(m.readings.find(r => r.key === 'stars')!.delta4).toBeNull();
  });
  it('computes actual medians and never includes missing citation placeholders as zeroes', () => {
    expect(median([1, 3, 10, 20])).toBe(6.5); expect(median([])).toBeNull();
    const r = archiveEntityById.get(ids[0])!, c = contextFor(r);
    const low = structuredClone(r.entity), high = structuredClone(r.entity);
    low.axes.github_commit_velocity.recent_weekly_commits = 10; high.axes.github_commit_velocity.recent_weekly_commits = 30;
    const m = buildCardB(r, { ...c, cohort: [low, high] });
    expect(m.medians.commits).toEqual({ value: 20, n: 2 });
    expect(metrics(archiveEntityById.get('e_093XKS44M6Q')!.entity).citations).toBeNull();
    expect(m.readings.find(x => x.key === 'citations')!.value).toBe(5);
  });
  it('extracts only a structured paper reference; arbitrary note prose never leaks', () => {
    expect(paperRef('paper_ref: 2410.07864; private note')).toBe('2410.07864');
    expect(paperRef('arXiv:2410.07864v2')).toBe('2410.07864v2');
    expect(paperRef('paper_ref: arXiv:2410.07864; text')).toBe('2410.07864');
    expect(paperRef('No reference')).toBeNull();
    const r = structuredClone(archiveEntityById.get(ids[0])!); r.entity.note += '; NEVER_PRINT_THIS';
    const m = buildCardB(r, contextFor(r));
    expect(JSON.stringify({ display: m.display, facets: m.facets, readings: m.readings })).not.toContain('NEVER_PRINT_THIS');
  });
  it('checks every facet template and every substituted sentence before rendering', () => {
    for (const entry of Object.values(FACETS)) {
      expect(entry.claim_id).toMatch(/^urn:evidaxis:claim:class:/);
      expect(() => assertPublicText(entry.text, 'Example')).not.toThrow();
      expect(() => assertPublicText(entry.answer, 'Example')).not.toThrow();
    }
    expect(() => interpolate('{missing}', {}, 'Example')).toThrow();
    expect(() => assertPublicText('Example is abandoned.', 'Example')).toThrow();
    expect(() => assertPublicText('Value, then a verdict elsewhere.', 'Example')).toThrow();
    expect(() => assertPublicText('https://github.com/%70rivateowner/x', 'Example', ['privateowner'])).toThrow(/person_free/);
    expect(() => assertPublicText('{"@type":"Person"}', 'Example')).toThrow(/person_free/);
  });
});

describe('twelve forced B fixtures and content indexability', () => {
  it('renders twelve distinct, reproducible answers without changing production assignment', () => {
    const answers = new Set<string>();
    for (const id of ids) {
      const first = render(id), second = render(id);
      answers.add(first.display.answer);
      expect(JSON.stringify(first.display)).toBe(JSON.stringify(second.display));
      expect(JSON.stringify(chartsFor(first))).toBe(JSON.stringify(chartsFor(second)));
      expect(valuesCSV(first)).toBe(valuesCSV(second));
      expect(first.display.answer).toMatch(/^\d/);
      if (first.nicheAssigned) expect(first.display.answer).toContain('median');
      else {
        expect(first.display.answer).not.toContain('niche median');
        expect(first.display.answer_comparison).toBeNull();
        expect(first.commitBand).toEqual([]);
      }
      expect(first.display.answer.split(/\s+/).length).toBeGreaterThanOrEqual(40);
      expect(first.display.answer.split(/\s+/).length).toBeLessThanOrEqual(60);
      expect(first.readings.filter(r => r.value !== null && r.source && r.date).length).toBeGreaterThanOrEqual(3);
    }
    expect(answers.size).toBe(12);
    expect(isTemplateB(ids[0])).toBe(false);
  });
  it('indexes RDT-1B in the B test projection, including its insufficient citation axis', () => {
    const m = render(ids[0]);
    expect(m.facets.citations.id).toBe('C07'); expect(m.years).toEqual([{ year: 2025, value: 5 }]);
    expect(isIndexable({ entity: { entity_id: ids[0] }, display: m.display, readings: m.readings })).toBe(true);
  });
  it('indexes a repository without a paper or dependents on its first observation', () => {
    const r = structuredClone(archiveEntityById.get('e_093XKS44M6Q')!), c = contextFor(r);
    c.state = deriveMeasurementState(r.entity, r.snapshot, 1);
    const m = buildCardB(r, c);
    expect(m.readings.find(x => x.key === 'citations')!.value).toBeNull();
    expect(isIndexable({ entity: r.entity, display: m.display, readings: m.readings })).toBe(true);
  });
  it('withholds an entirely unmeasured synthetic record and rejects another system\'s values', () => {
    const r = structuredClone(archiveEntityById.get('e_093XKS44M6Q')!);
    Object.assign(r.entity.axes.github_commit_velocity, { recent_weekly_commits: null, stars_not_scored: null, slope: null, cohort_z: null });
    r.entity.github_repo = ''; r.entity.axes_present = []; r.entity.convergent_axes = [];
    const base = contextFor(archiveEntityById.get('e_093XKS44M6Q')!);
    const ctx: Context = { ...base, state: deriveMeasurementState(r.entity, r.snapshot, 1), commits: [], history: [], daily: null, repoApi: null, repoUrl: null, repoLabel: 'not linked' };
    const m = buildCardB(r, ctx);
    expect(isIndexable({ entity: r.entity, display: m.display, readings: m.readings })).toBe(false);
    const measured = render(ids[0]);
    expect(isIndexable({ entity: { entity_id: 'e_WRONG00000X' }, display: measured.display, readings: measured.readings })).toBe(false);
  });
  it('uses history sufficiency unchanged for A and the headline experiment', () => {
    for (const state of ['sufficient', 'insufficient']) expect(isIndexable({ entity: { entity_id: ids[0] }, measurement_state: { history_sufficiency: { state } } })).toBe(state === 'sufficient');
  });
  it('indexes a linked citation count and annual series even without a repository', () => {
    const r = structuredClone(archiveEntityById.get(ids[0])!), ctx = contextFor(r);
    Object.assign(r.entity.axes.github_commit_velocity, { recent_weekly_commits: null, stars_not_scored: null, slope: null, cohort_z: null });
    r.entity.github_repo = ''; r.entity.axes_present = []; r.entity.convergent_axes = [];
    const m = buildCardB(r, { ...ctx, commits: [], repoApi: null, repoUrl: null, repoLabel: 'not linked', state: deriveMeasurementState(r.entity, r.snapshot, 1) });
    expect(m.display.answer).toMatch(/^5 OpenAlex citing works/);
    expect(isIndexable({ entity: r.entity, display: m.display, readings: m.readings })).toBe(true);
  });
});

describe('reproducible artifacts and optional event sinks', () => {
  it('keeps archive output at or before the requested snapshot and names releases immutably', () => {
    const m = render(ids[0]);
    expect(historyCSV(m)).toContain('captured_at'); expect(valuesCSV(m)).toContain(m.release);
    expect(m.history.every(p => p.snapshot.snapshot_date <= m.date)).toBe(true);
    for (const chart of Object.values(chartsFor(m))) {
      expect(chart.url).toContain(`${m.release}.svg`); expect(chart.svg).toContain('<title'); expect(chart.svg).toContain('<desc');
    }
  });
  it('emits feed entries for changed published numbers, not a new date alone', () => {
    const m = render(ids[0]), p = m.history.at(-1)!;
    const duplicate = { ...p, snapshot: { ...p.snapshot, snapshot_date: '2026-09-20', snapshot_id: 'duplicate', captured_at: '2026-09-20T00:00:00Z' } };
    const changed = structuredClone(duplicate); changed.snapshot.snapshot_date = '2026-09-21'; changed.snapshot.snapshot_id = 'changed'; changed.entity.axes.github_commit_velocity.stars_not_scored! += 1;
    const feed = systemFeed({ ...m, history: [p, duplicate, changed] });
    expect(feed.items).toHaveLength(2); expect(feed.items[0].id).toContain('changed-b1');
    expect(systemAtom({ ...m, history: [p] })).toContain('<author><name>Evidaxis</name></author>');
  });
  it('keeps the interaction payload under 1 KB and reports both available sinks', async () => {
    expect(Buffer.byteLength(CARD_B_CLIENT)).toBeLessThanOrEqual(1024);
    const root: any = { dataset: { entity: ids[0] } }, events: unknown[][] = [], copied: string[] = [];
    runInNewContext(CARD_B_CLIENT, { document: { querySelector: () => root }, navigator: { clipboard: { writeText: async (s: string) => copied.push(s) } }, window: { gtag: (...a: unknown[]) => events.push(a), posthog: { capture: (...a: unknown[]) => events.push(a) } } });
    const target = { dataset: { fnd: 'fnd_cite_copy', copy: 'Cite this', block: '2a' }, closest: () => root };
    await root.onclick({ target: { closest: () => target } });
    expect(copied).toEqual(['Cite this']); expect(events).toHaveLength(2);
    expect(events[0]).toEqual(['event', 'fnd_cite_copy', { entity_id: ids[0], block: '2a', template: 'B' }]);
    runInNewContext(CARD_B_CLIENT, { document: { querySelector: () => root }, window: {} });
    await expect(root.onclick({ target: { closest: () => ({ dataset: { fnd: 'fnd_follow' }, closest: () => root }) } })).resolves.not.toThrow();
  });
  it('sorts numbers numerically, keeps missing values last and reverses direction', async () => {
    const root: any = { dataset: { entity: ids[0] } }, rows = ['10', '2', '', '0'].map(v => ({ cells: [{ dataset: { value: 'name' } }, { dataset: { value: v } }] }));
    const body = { rows, append(row: any) { this.rows.splice(this.rows.indexOf(row), 1); this.rows.push(row); } };
    const head = { sort: '', removeAttribute() {}, setAttribute(key: string, value: string) { this.sort = value; } };
    const table = { tBodies: [body], querySelectorAll: () => [head] };
    const target = { dataset: { fnd: 'fnd_tool_run', sort: '2', dir: '' }, closest: (s: string) => s === 'table' ? table : s === 'th' ? head : root };
    runInNewContext(CARD_B_CLIENT, { document: { querySelector: () => root }, window: {} });
    await root.onclick({ target: { closest: () => target } });
    expect(body.rows.map(r => r.cells[1].dataset.value)).toEqual(['0', '2', '10', '']);
    await root.onclick({ target: { closest: () => target } });
    expect(body.rows.map(r => r.cells[1].dataset.value)).toEqual(['10', '2', '0', '']);
    expect(head.sort).toBe('descending');
  });
  it('allows CSV/feed assets through the host redirect while keeping legacy slugs', () => {
    const vercel = JSON.parse(readFileSync(new URL('../../../vercel.json', import.meta.url), 'utf8'));
    const rule = vercel.redirects.find((r: any) => r.source.startsWith('/e/'));
    const pattern = new RegExp('^' + rule.source.replace(':entity_id', '[^/]+').replace(':slug', '') + '$');
    expect(pattern.test('/e/e_00000000000/old-name')).toBe(true);
    for (const file of ['feed.atom', 'feed.json', 'values-fcfd3a7ccdcb-b1.csv', 'history-fcfd3a7ccdcb-b1.csv']) expect(pattern.test(`/e/e_00000000000/${file}`)).toBe(false);
    expect(vercel.headers[0].headers).toContainEqual({ key: 'X-Robots-Tag', value: 'noindex' });
  });
});
