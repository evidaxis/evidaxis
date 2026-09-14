import { describe, expect, it } from 'vitest';
import { snapshot } from './data';
import type { Entity } from './data';
import { entityGraph, snapshotDataset } from './jsonld';
import { deriveMeasurementState, measurementPhrases } from './measurement';
import { computePowerFunnel, computeSensitivity } from './power';
import { CITATION_AXIS as C, DEVELOPMENT_AXIS as D, DEPENDENTS_AXIS as A, methodologyAxes } from './methodology';
import { GET } from '../pages/methodology-registry.json';

const candidate = {
  ...snapshot.entities[0],
  cohort: 'fixture', incumbent: false, rising: true, openalex_work_ids: [],
  axes_present: [D, A], convergent_axes: [D, A],
  axes: {
    github_commit_velocity: { slope: 0.1, cohort_z: 1.2, recent_weekly_commits: 8, stars_not_scored: 100 },
    openalex_citation_momentum: { status: 'absent' as const, slope: null, cohort_z: null, total_citations: 0, by_year: null, proxy: null },
    deps_direct_dependents_momentum: { status: 'scored' as const, slope: 0.2, cohort_z: 1.4, theil_sen: 0.2,
      latest: 30, points: 20, points_reconstructable: 14, as_of_partition: '2026-08-24', unstable: false, rising_vote: true },
  },
};
const fixture = { ...snapshot, methodology_version: 'm3', entities: Array.from({ length: 5 }, (_, i) => ({ ...candidate, entity_id: `e_FIXTURE${i}` })) };

describe('methodology-specific axes', () => {
  it('resolves historical and new definitions, rejecting unknown versions', () => {
    expect(methodologyAxes('m1')).toEqual([D, C]);
    expect(methodologyAxes('m2')).toEqual([D, C]);
    expect(methodologyAxes('m3')).toEqual([D, C, A]);
    expect(() => methodologyAxes('m999')).toThrow('not in registry');
    expect(() => entityGraph(candidate, { ...fixture, methodology_version: 'm999' })).toThrow('not in registry');
  });

  it('allows development plus direct dependents to converge without citations', () => {
    const state = deriveMeasurementState(candidate, fixture, 8);
    expect(state.axis_coverage.measurable_axis_count).toBe(2);
    expect(state.axes[A]?.history_sufficiency.required).toBe(14);
    expect(state.positive_signal.state).toBe('published');
    const resolve = (entity: Entity) => deriveMeasurementState(entity, fixture, 8);
    expect(computePowerFunnel(fixture, resolve)).toMatchObject({ two_axis_measurable: 5, three_axis_measurable: 0, rising_published: 5 });
    expect(computeSensitivity(fixture, [1, 1.5], 5, resolve).map(row => row.convergence_signals)).toEqual([5, 0]);
  });

  it.each(['below_floor', 'held', 'stale', 'out_of_panel'] as const)('preserves the %s state and excludes it from coverage', status => {
    const entity = { ...candidate, rising: false, axes_present: [D], convergent_axes: [D], axes: {
      ...candidate.axes, [A]: { ...candidate.axes[A], status, slope: null, cohort_z: null, rising_vote: false },
    } };
    const state = deriveMeasurementState(entity, fixture, 8);
    expect(state.axis_coverage.axes[A]).toBe(status);
    expect(state.axis_coverage.measurable_axis_count).toBe(1);
    expect(measurementPhrases(state).gate).toContain('1 of 3 axes measurable');
    expect(measurementPhrases(state).dependents_axis).toBeTruthy();
    expect(computeSensitivity({ ...fixture, entities: [entity] }, [1], 5, e => deriveMeasurementState(e, fixture, 8))[0].convergence_signals).toBe(0);
  });

  it('rejects a published unstable vote and unknown coverage states', () => {
    expect(() => deriveMeasurementState({ ...candidate, axes: { ...candidate.axes, [A]: { ...candidate.axes[A], unstable: true } } }, fixture, 8)).toThrow('inconsistent_positive_signal');
    expect(() => deriveMeasurementState({ ...candidate, axes: { ...candidate.axes, [A]: { ...candidate.axes[A], status: 'mystery' } } }, fixture, 8)).toThrow('unknown_dependents_status');
  });

  it('renders 3-axis JSON-LD with the estimand while older records stay at 2', () => {
    const graph = entityGraph(candidate, fixture)['@graph'];
    const dataset = graph.find(node => node['@type'] === 'Dataset');
    expect(dataset.variableMeasured.find((v: any) => v.name === 'Measurable axis count').maxValue).toBe(3);
    expect(dataset.variableMeasured.find((v: any) => v.name === 'Direct-dependents momentum (deps.dev)').description).toContain('Residual survivorship beyond the frozen universe is disclosed, not denied.');
    const old = { ...candidate, rising: false, axes_present: [D], convergent_axes: [] };
    const oldGraph = entityGraph(old, { ...fixture, methodology_version: 'm2' })['@graph'].find(node => node['@type'] === 'Dataset');
    expect(oldGraph.variableMeasured.find((v: any) => v.name === 'Measurable axis count').maxValue).toBe(2);
    expect(oldGraph.variableMeasured.some((v: any) => v.name === 'Direct-dependents momentum (deps.dev)')).toBe(false);
    const snapshotNode = snapshotDataset(fixture)['@graph'].find(node => node['@type'] === 'Dataset')!;
    expect('variableMeasured' in snapshotNode && snapshotNode.variableMeasured).toHaveLength(4);
  });

  it('publishes current from the latest snapshot, including before m3 activation', async () => {
    const response = await GET({} as any) as Response;
    expect((await response.json()).current).toBe(snapshot.methodology_version);
  });

  it('never serves a version as current before a snapshot uses it', async () => {
    const body = await (await GET({} as any) as Response).json();
    for (const row of body.versions) {
      if (row.version === body.current) expect(row.status).toBe('current');
      else if (row.effective_at > snapshot.snapshot_date) expect(row.status).toBe('scheduled');
      else expect(row.status).not.toBe('current');
    }
  });

  it('keeps the page copy of the axis-3 estimand and attribution identical to methodology/m3.json', async () => {
    // The strings are duplicated for the static build; this pin stops them drifting apart.
    const { readFileSync } = await import('node:fs');
    const { AXIS3_ESTIMAND, AXIS3_ATTRIBUTION } = await import('./methodology');
    const spec = JSON.parse(readFileSync(new URL('../../../methodology/m3.json', import.meta.url), 'utf8'));
    expect(AXIS3_ESTIMAND).toBe(spec.estimand);
    expect(AXIS3_ATTRIBUTION).toBe(spec.attribution);
  });
});
