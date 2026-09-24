import { describe, expect, it } from 'vitest';
import { badgeData, badgeRecords, builderSelection, chooseBadges, endpointJson, growthPercent, latestRisingRun, nicheCandidates, ratioText, risingCardSvg, risingRange, risingRecords, rowSvg, tierFor, verifiedPin } from './badges';
import { metrics } from './cardB/build';
import { contextFor } from './cardB/context';

const named = (name: string) => badgeRecords.find(record => record.entity.name === name)!;

describe('README badges', () => {
  it('uses card B readings and medians for every archived system', () => {
    for (const record of badgeRecords) {
      const own = metrics(record.entity);
      for (const key of ['citations', 'dependents'] as const) {
        const data = badgeData(record, key);
        expect(data.count).toBe(own[key]);
        expect(data.message).toBe(key === 'dependents' && own[key] !== null && !verifiedPin(record) ? 'unverified'
          : own[key] === null ? 'not measured' : Math.round(own[key]).toLocaleString('en-US'));
        const endpoint = endpointJson(record, key);
        expect(endpoint).toEqual({ schemaVersion: 1, label: key, message: data.message,
          color: data.color.slice(1), labelColor: '555', logoSvg: expect.stringContaining('<svg'), cacheSeconds: 21600 });
      }
      const median = contextFor(record).cohortSummary!.medians;
      const best = nicheCandidates(own, median, verifiedPin(record))[0];
      const medal = badgeData(record, 'medal');
      if (best && best.ratio >= 1) {
        expect(medal.metric).toBe(best.metric);
        expect(medal.ratio).toBe(best.ratio);
        expect(medal.count).toBe(best.value);
        expect(medal.message).toContain(ratioText(best.ratio));
        expect(medal.title).toContain(`(${Math.round(best.median).toLocaleString('en-US')}; n = ${best.n})`);
      } else expect(medal.message).not.toContain('niche median');
    }
  });

  it('honors tier boundaries and formatting', () => {
    expect([1.99, 2, 9.99, 10, 99.9, 100].map(tierFor)).toEqual([null, 'bronze', 'bronze', 'silver', 'silver', 'gold']);
    expect([1.6, 8.8, 10, 140, 1120].map(ratioText)).toEqual(['1.6×', '8.8×', '10×', '140×', '1,120×']);
    const medians = { citations: { value: 10, n: 5 }, dependents: { value: 3, n: 5 } };
    expect(nicheCandidates({ citations: 9, dependents: 300 }, medians, false)[0].metric).toBe('citations');
    expect(nicheCandidates({ citations: 9, dependents: 300 }, medians, true)[0].metric).toBe('dependents');
    expect(nicheCandidates({ citations: 9, dependents: null }, { ...medians, citations: { value: 10, n: 4 } }, true)).toEqual([]);
    expect(nicheCandidates({ citations: 9, dependents: null }, { ...medians, citations: { value: 2, n: 5 } }, true)).toEqual([]);
  });

  it('offers completed-year growth only above the gates', () => {
    expect(growthPercent(100, 124)).toBeNull();
    expect(growthPercent(100, 125)).toBe(25);
    expect(growthPercent(0, 20)).toBeNull();
    expect(growthPercent(8, 9)).toBeNull();
    expect(growthPercent(100, 20)).toBeNull();
    for (const record of badgeRecords) expect(badgeData(record, 'growth').message).not.toMatch(/^-\d+%/);
  });

  it('formats Rising runs from snapshot dates and switches live text', () => {
    expect(risingRange('2026-09-05', '2026-09-19')).toBe('Sept 2026');
    expect(risingRange('2026-09-05', '2026-11-19')).toBe('Sept–Nov 2026');
    expect(risingRange('2026-12-19', '2027-01-05')).toBe('Dec 2026–Jan 2027');
    for (const record of badgeRecords) {
      const run = latestRisingRun(record);
      expect(risingRecords.includes(record)).toBe(!!run);
      if (run) {
        const data = badgeData(record, 'rising');
        expect(data.message).toBe(run.live ? data.niche : risingRange(run.start, run.end));
        expect(data.message).not.toContain('since');
        expect(risingCardSvg(record)).toContain('width="250" height="54"');
      }
    }
  });

  it('chooses one main medal and at most two relevant extras', () => {
    const vllm = named('vLLM');
    expect(badgeData(vllm, 'medal')).toMatchObject({ metric: 'citations', tier: 'gold', message: 'gold · 140× niche median' });
    expect(badgeData(named('SGLang'), 'medal')).toMatchObject({ metric: 'citations', tier: 'bronze', message: '8.8× niche median' });
    expect(badgeData(named('MuJoCo'), 'medal').tier).toBe('gold');
    expect(builderSelection(vllm).main).toBe('medal');
    expect(builderSelection(named('SGLang')).main).toBe('medal');
    expect(builderSelection(named('AgentScope')).main).toBe('rising');
    expect(chooseBadges({ rising: 'ended', medal: false, growth: true, count: 'citations' })).toEqual({ main: 'rising', extras: ['growth', 'citations'] });
    expect(chooseBadges({ rising: 'live', medal: true, growth: true, count: 'citations' })).toEqual({ main: 'rising', extras: ['medal', 'growth'] });
    const noMedal = badgeRecords.find(record => builderSelection(record).main === null);
    expect(noMedal).toBeDefined();
    expect(builderSelection(noMedal!)).toEqual({ main: null, extras: [] });
    for (const record of badgeRecords) {
      const selection = builderSelection(record);
      expect(selection.extras.length).toBeLessThanOrEqual(2);
      expect(new Set([selection.main, ...selection.extras].filter(Boolean)).size).toBe([selection.main, ...selection.extras].filter(Boolean).length);
      if (selection.main === null) expect(selection.extras).toEqual([]);
    }
    const voidRecord = badgeRecords.find(record => record.entity.github_repo === 'voideditor/void')!;
    expect(verifiedPin(voidRecord)).toBe(false);
    expect(badgeData(voidRecord, 'medal').metric).not.toBe('dependents');
  });

  it('renders accessible SVGs in every style', () => {
    for (const record of badgeRecords.slice(0, 10)) for (const key of ['medal', 'growth', 'citations', 'dependents'] as const) {
      for (const style of ['flat', 'flat-square', 'for-the-badge'] as const) {
        const svg = rowSvg(record, key, style);
        expect(svg).toContain(`height="${style === 'for-the-badge' ? 28 : 20}"`);
        expect(svg).toContain('<title>');
        expect(svg).not.toContain('\u2014');
      }
    }
  });
});
