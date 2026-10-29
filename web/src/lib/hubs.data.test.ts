import { describe, expect, it } from 'vitest';
import { archiveEntityById } from './archive';
import { verifiedPin } from './badges';
import { metrics } from './cardB/build';
import { snapshot } from './data';
import { assignedNiches, unassignedSummary, nicheCSV, nicheJSON, searchIndex } from './hubs';
import { CITATION_AXIS, measurementStateFor } from './measurement';
const allNiches = () => [...assignedNiches(), ...(unassignedSummary() ? [unassignedSummary()!] : [])];
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
