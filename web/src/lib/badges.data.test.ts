import { expect, it } from 'vitest';
import { badgeData, badgeRecords, endpointJson, nicheCandidates, ratioText, verifiedPin } from './badges';
import { metrics } from './cardB/build';
import { contextFor } from './cardB/context';
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
    const median = record.entity.cohort === 'unassigned-v1'
      ? { citations: { value: null, n: 0 }, dependents: { value: null, n: 0 } }
      : contextFor(record).cohortSummary!.medians;
    const best = nicheCandidates(own, median, verifiedPin(record), record.entity.cohort)[0];
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
