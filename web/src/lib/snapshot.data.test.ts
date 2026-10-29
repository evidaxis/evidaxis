import { describe, expect, it } from 'vitest';
import { snapshot, entities, SNAP_DATE } from './data';
describe('snapshot integrity (loaded from the canonical git artifact)', () => {
  it('counts.entities matches the entities array length', () => {
    expect(snapshot.counts.entities).toBe(entities.length);
  });
  it('exposes the selected snapshot date', () => {
    expect(SNAP_DATE).toBe(snapshot.snapshot_date);
    expect(snapshot.snapshot_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
