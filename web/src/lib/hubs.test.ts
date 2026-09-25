import { describe, expect, it } from 'vitest';
import { experimental_AstroContainer as AstroContainer } from 'astro/container';
import { archiveEntityById } from './archive';
import { badgeData, verifiedPin } from './badges';
import { metrics, summarizeCohort } from './cardB/build';
import { contextFor } from './cardB/context';
import { snapshot } from './data';
import { ALL_TERMS, COMPUTED_TERMS, PLAIN_TERMS } from './glossary';
import {
  assignedNiches, citationPhrase, commitsPhrase, dependentsPhrase, measuredLine, medianText, nicheAnswer, nicheCSV,
  nicheJSON, nicheSummary, searchIndex, snapshotMedals, statusText, unassignedSummary, UNASSIGNED,
} from './hubs';
import { CITATION_AXIS, measurementStateFor } from './measurement';

const allNiches = () => [...assignedNiches(), ...(unassignedSummary() ? [unassignedSummary()!] : [])];

describe('measured line', () => {
  it('prints the three forms for citations and verified dependents', () => {
    expect(citationPhrase(1547, 'scored')).toBe('1,547 citations to date');
    expect(citationPhrase(12, 'count_only')).toBe('12 citations to date (count only)');
    expect(citationPhrase(null, 'not_measured')).toBe('citations not measured');
    expect(dependentsPhrase(20, 'scored')).toBe('20 verified direct dependents');
    expect(dependentsPhrase(8, 'count_only')).toBe('8 verified direct dependents (count only)');
    expect(dependentsPhrase(null, 'not_measured')).toBe('verified dependents not measured');
    expect(commitsPhrase(null)).toBe('commits not measured');
    expect(measuredLine({ commits: 42.4, citations: 9, citationState: 'count_only', dependents: null, dependentsState: 'not_measured' }))
      .toBe('42.4 commits/week, 9 citations to date (count only), verified dependents not measured.');
  });

  it('derives every row from the card readings, verified dependents only', () => {
    for (const s of allNiches()) for (const row of s.rows) {
      const record = archiveEntityById.get(row.id)!;
      const own = metrics(record.entity);
      expect(row.commits).toBe(own.commits);
      expect(row.citations).toBe(own.citations);
      expect(row.dependentsReading).toBe(own.dependents);
      expect(row.dependents).toBe(verifiedPin(record) ? own.dependents : null);
      if (row.dependents === null) expect(row.measuredLine).toContain('verified dependents not measured');
      const scored = measurementStateFor(record.entity, record.snapshot).axis_coverage.axes[CITATION_AXIS] === 'measurable';
      if (own.citations !== null && !scored) expect(row.measuredLine).toContain('citations to date (count only)');
      if (own.citations === null) expect(row.measuredLine).toContain('citations not measured');
    }
  });
});

describe('status cell', () => {
  it('shows the multiple and the measure, never a tier word', () => {
    expect(statusText({ tier: 'gold', ratio: 140.7, metric: 'citations' }, false)).toBe('140× citations');
    expect(statusText({ tier: 'bronze', ratio: 2.26, metric: 'dependents' }, true)).toBe('2.2× dependents · Rising');
    expect(statusText(null, true)).toBe('Rising');
    expect(statusText(null, false)).toBe('');
    for (const s of allNiches()) for (const row of s.rows) {
      expect(row.status).not.toMatch(/gold|silver|bronze/i);
      const record = archiveEntityById.get(row.id)!;
      if (s.assigned) {
        const medal = badgeData(record, 'medal');
        expect(row.medal?.tier ?? null).toBe(medal.tier ?? null);
        expect(row.rising).toBe(measurementStateFor(record.entity, record.snapshot).positive_signal.state === 'published');
      } else {
        expect(row.medal).toBeNull();
        expect(row.rising).toBe(false);
        expect(row.status).toBe('');
      }
    }
  });
});

describe('niche hub answer', () => {
  it('uses the card medians and prints n for Coding Agents', () => {
    const s = nicheSummary('coding-agents');
    const members = snapshot.entities.filter((e) => e.cohort === 'coding-agents');
    expect(s.n).toBe(members.length);
    const card = contextFor(archiveEntityById.get(s.rows[0].id)!).cohortSummary!.medians;
    const independent = summarizeCohort(members, {}).medians;
    expect(s.medians).toEqual({ commits: card.commits, citations: card.citations, dependents: card.dependents });
    expect(independent.citations).toEqual(card.citations);
    const answer = nicheAnswer(s);
    expect(answer.startsWith(`Evidaxis measures ${s.n} systems in Coding Agents every week. In snapshot ${snapshot.period} (${snapshot.snapshot_date}) the niche median is `)).toBe(true);
    const plural = (n: number) => (n === 1 ? 'system' : 'systems');
    expect(answer).toContain(`${medianText(card.commits.value!)} commits per week`);
    expect(answer).toContain(`${medianText(card.citations.value!)} citations to date (on the ${card.citations.n} ${plural(card.citations.n)} with a citation count)`);
    expect(answer).toContain(`${medianText(card.dependents.value!)} direct dependents (on the ${card.dependents.n} ${plural(card.dependents.n)} with a dependents reading)`);
    expect(answer).toContain(`Systems at 2× the niche median or more: ${s.rows.filter((r) => r.medal).length}.`);
    const rising = s.rows.filter((r) => r.rising).map((r) => r.name);
    expect(answer).toContain(`Rising: ${rising.length ? rising.join(', ') : 'none'}.`);
    expect(answer).not.toMatch(/—/);
  });

  it('marks only non-integer medians with ≈', () => {
    expect(medianText(79)).toBe('79');
    expect(medianText(42.4)).toBe('≈42.4');
    expect(medianText(1234)).toBe('1,234');
  });

  it('keeps the not-yet-assigned group out of niche comparisons', () => {
    const u = unassignedSummary();
    if (!u) return;
    expect(u.key).toBe(UNASSIGNED);
    expect(u.medians).toBeNull();
    expect(nicheAnswer(u)).toBe('These systems are measured every week but have no niche yet, so there is no niche median, no medal and no niche Rising comparison.');
    expect(assignedNiches().some((s) => s.key === UNASSIGNED)).toBe(false);
    const { medals, rising } = snapshotMedals();
    expect(medals.gold + medals.silver + medals.bronze).toBe(assignedNiches().reduce((n, s) => n + s.atTwoX, 0));
    expect(rising.every((r) => archiveEntityById.get(r.id)!.entity.cohort !== UNASSIGNED)).toBe(true);
  });

  it('lists every niche A to Z', () => {
    const labels = assignedNiches().map((s) => s.label);
    expect(labels).toEqual([...labels].sort((a, b) => a.localeCompare(b, 'en', { sensitivity: 'base' })));
  });
});

describe('niche downloads', () => {
  it('writes one CSV row and one JSON row per system', () => {
    for (const s of allNiches()) {
      const lines = nicheCSV(s).split('\r\n').filter(Boolean);
      expect(lines).toHaveLength(s.n + 1);
      expect(lines[0].startsWith('entity_id,name,url,niche,measured_line,commits_per_week,citations_to_date')).toBe(true);
      expect(new Set(lines.slice(1).map((l) => l.split(',')[0]))).toEqual(new Set(s.rows.map((r) => r.id)));
      const json = nicheJSON(s);
      expect(json.systems).toHaveLength(s.n);
      expect(json.license).toBe('CC0-1.0');
    }
  });
});

describe('home search index', () => {
  it('covers every system in the latest snapshot', () => {
    const index = searchIndex();
    expect(index).toHaveLength(snapshot.entities.length);
    expect(new Set(index.map((r) => r.id))).toEqual(new Set(snapshot.entities.map((e) => e.entity_id)));
    for (const r of index) expect(Object.keys(r)).toEqual(['name', 'id']);
  });
});

describe('glossary', () => {
  it('adds the plain terms first with stable anchors and keeps the computed terms', () => {
    for (const id of ['system', 'niche', 'field', 'not-yet-assigned', 'weekly-snapshot', 'commits-per-week', 'citation',
      'verified-direct-dependent', 'star', 'not-measured-count-only', 'niche-median', 'niche-medal', 'niche-rising']) {
      expect(PLAIN_TERMS.map((t) => t.id)).toContain(id);
    }
    expect(new Set(ALL_TERMS.map((t) => t.id)).size).toBe(ALL_TERMS.length);
    expect(COMPUTED_TERMS).toHaveLength(16);
    expect(COMPUTED_TERMS.map((t) => t.id)).toEqual(['momentum', 'momentum-score', 'development-velocity', 'citation-momentum',
      'direct-dependents-momentum', 'within-cohort-robust-z', 'residualization', 'convergence-gate', 'rising', 'watch', 'tracked',
      'single-axis', 'calibration', 'cohort', 'snapshot', 'score-receipt']);
    const def = (id: string) => PLAIN_TERMS.find((t) => t.id === id)!.def;
    expect(def('niche-median')).toBe('The middle value of one measure among the systems in a niche that have that measure. Systems without the measure are left out, not counted as zero.');
    expect(def('niche-medal')).toBe('A medal for a system whose citations or verified dependents reach 2×, 10× or 100× its niche median: bronze, silver or gold. The badge shows the multiple and the measure; it is a threshold, not a place.');
    expect(def('niche-rising')).toBe('At least two of the three measures (commits per week, citations, verified dependents) are rising together in the system’s niche on this snapshot. It describes the recorded series; it is not a forecast.');
    for (const t of ALL_TERMS) expect(t.def).not.toMatch(/—/);
  });

  it('renders every anchor on the glossary page', async () => {
    const { default: Glossary } = await import('../pages/glossary/index.astro');
    const container = await AstroContainer.create();
    const html = await container.renderToString(Glossary);
    expect(html.indexOf('id="terms-on-every-page"')).toBeLessThan(html.indexOf('id="how-a-figure-is-computed"'));
    for (const t of ALL_TERMS) expect(html).toContain(`id="${t.id}"`);
    expect(html).toContain('"@type":"DefinedTermSet"');
    expect((html.match(/"@type":"DefinedTerm"/g) ?? []).length).toBe(ALL_TERMS.length);
  });
});
