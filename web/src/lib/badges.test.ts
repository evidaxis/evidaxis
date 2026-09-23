import { describe, expect, it } from 'vitest';
import { badgeData, badgeRecords, endpointJson, latestRisingRun, risingCardSvg, risingRecords, rowSvg } from './badges';
import { metrics } from './cardB/build';

describe('README badges', () => {
  it('uses the same readings as card B across the archived entity universe', () => {
    for (const record of badgeRecords) {
      const own = metrics(record.entity);
      for (const key of ['citations', 'dependents'] as const) {
        const data = badgeData(record, key);
        expect(data.count).toBe(own[key]);
        expect(data.message).toBe(own[key] === null ? 'not measured' : Math.round(own[key]).toLocaleString('en-US'));
        expect(data.title).toContain(key === 'dependents' && own[key] !== null ? record.entity.axes?.deps_direct_dependents_momentum?.as_of_partition ?? record.snapshot.snapshot_date : record.snapshot.snapshot_date);
        const endpoint = endpointJson(record, key);
        expect(endpoint).toEqual({ schemaVersion: 1, label: key, message: data.message,
          color: data.color.slice(1), labelColor: '555', logoSvg: expect.stringContaining('<svg'), cacheSeconds: 21600 });
      }
    }
  });

  it('renders shields dimensions and accessible measured text', () => {
    for (const record of badgeRecords) for (const key of ['citations', 'dependents'] as const) {
      for (const style of ['flat', 'flat-square', 'for-the-badge'] as const) {
        const svg = rowSvg(record, key, style);
        expect(svg).toContain(`height="${style === 'for-the-badge' ? 28 : 20}"`);
        expect(svg).toContain('<title>');
        expect(svg).toContain(record.entity.name.replaceAll('&', '&amp;'));
        expect(svg.toLowerCase()).toContain(badgeData(record, key).message.toLowerCase().replace('not measured', 'no ' + key + ' reading'));
        expect(svg).not.toContain('\u2014');
      }
    }
  });

  it('offers Rising only when a published weekly run exists', () => {
    for (const record of badgeRecords) {
      const run = latestRisingRun(record);
      expect(risingRecords.includes(record)).toBe(!!run);
      if (run) {
        const data = badgeData(record, 'rising');
        expect(data.message).toBe(run.live ? `since ${run.start}` : `${run.start}–${run.end}`);
        expect(risingCardSvg(record)).toContain('width="250" height="54"');
      }
    }
  });
});
