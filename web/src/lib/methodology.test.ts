import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { snapshot } from './data';
import type { Entity } from './data';
import { entityGraph, snapshotDataset } from './jsonld';
import { deriveMeasurementState, measurementPhrases } from './measurement';
import { computePowerFunnel, computeSensitivity } from './power';
import { CITATION_AXIS as C, DEVELOPMENT_AXIS as D, DEPENDENTS_AXIS as A, axis3Estimand, methodologyAxes } from './methodology';
import { GET } from '../pages/methodology-registry.json';

const repoRoot = fileURLToPath(new URL('../../..', import.meta.url));

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
    expect(methodologyAxes('m4')).toEqual([D, C, A]);
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
    expect(axis3Estimand('m3')).toBe(spec.estimand);
    expect(AXIS3_ATTRIBUTION).toBe(spec.attribution);
    const m3Page = readFileSync(new URL('../components/MethodologyM3.astro', import.meta.url), 'utf8');
    expect(m3Page).toContain('linkage-verified packages');
    expect(m3Page).toContain('{AXIS3_ESTIMAND}');
  });

  it('publishes the m4 permalink, registry row, and an estimand without linkage-verified', () => {
    expect(existsSync(resolve(repoRoot, 'web/src/pages/methodology/m4/index.astro'))).toBe(true);
    const page = readFileSync(resolve(repoRoot, 'web/src/pages/methodology/m4/index.astro'), 'utf8');
    expect(page).toContain('This is the m4 permalink. It supersedes');
    expect(page).toContain('for new snapshots from 2026-10-10.');
    const body = readFileSync(resolve(repoRoot, 'web/src/components/MethodologyBody.astro'), 'utf8');
    expect(body).toContain("version === 'm4'");
    const component = readFileSync(resolve(repoRoot, 'web/src/components/MethodologyM4.astro'), 'utf8');
    expect(component).not.toContain('linkage-verified');
    expect(component).toContain('own packages');
    expect(component).toContain('published under that name');
    expect(component).toContain('not attributed by deps.dev to another repository');
    expect(component).toContain('Packages without repository metadata are counted as unverified');
    expect(component).toContain('fixed list');
    expect(component).toContain('stored per-package weekly rows');
    expect(component).toContain('14 usable points of the new quantity');
    expect(component).toContain('2026-10-04');
    expect(component).toContain('governance/METHODOLOGY-M4-2026-10-04.md');
    expect(component).toContain('METHODOLOGY-VERSIONING.md#errata');
    expect(component).toContain('methodology/m4.json');

    const registry = JSON.parse(readFileSync(resolve(repoRoot, 'web/src/lib/methodology-registry.json'), 'utf8'));
    const m3 = registry.versions.find((row: { version: string }) => row.version === 'm3');
    const m4 = registry.versions.find((row: { version: string }) => row.version === 'm4');
    expect(m3).toMatchObject({ status: 'superseded', superseded_at: '2026-10-10' });
    const fingerprint = execFileSync(
      resolve(repoRoot, '.venv/bin/python'),
      ['collectors/methodology_fingerprint.py', 'methodology/m4.json'],
      { cwd: repoRoot, encoding: 'utf8' },
    ).trim();
    const codeCommit = execFileSync('git', ['log', '-1', '--format=%H', '--', 'methodology/m4.json'], { cwd: repoRoot, encoding: 'utf8' }).trim();
    expect(m4).toMatchObject({
      version: 'm4',
      status: 'current',
      formula_fingerprint: fingerprint,
      code_commit: codeCommit,
      effective_at: '2026-10-10',
      parent_version: 'm3',
      page: '/methodology/m4/',
    });
    expect(m4.changelog).toContain('MAJOR');
    expect(m4.changelog).toContain("axis 3 counts only a system's own packages");
    expect(m4.changelog).toContain('exactly derived');
    expect(m4.changelog).toContain('restarts');
    expect(m4.changelog).toContain('self-name exclusion list is fixed');
    expect(m4.changelog).toContain('m3 snapshots are never recomputed');
    expect(m4.changelog).toContain('governance/METHODOLOGY-M4-2026-10-04.md');
    expect(m4.changelog).toContain('METHODOLOGY-VERSIONING.md#errata');

    const spec = JSON.parse(readFileSync(resolve(repoRoot, 'methodology/m4.json'), 'utf8'));
    expect(axis3Estimand('m4')).toBe(spec.estimand);
    expect(axis3Estimand('m4')).not.toContain('linkage-verified');
    const m4Fixture = { ...fixture, methodology_version: 'm4' };
    const m4Graph = entityGraph(candidate, m4Fixture)['@graph'];
    const m4Dataset = m4Graph.find(node => node['@type'] === 'Dataset');
    const m4Description = m4Dataset.variableMeasured.find((v: { name: string }) => v.name === 'Direct-dependents momentum (deps.dev)').description;
    expect(m4Description).toContain(spec.estimand);
    expect(m4Description).not.toContain('linkage-verified');
    const m3Description = entityGraph(candidate, fixture)['@graph']
      .find(node => node['@type'] === 'Dataset')
      .variableMeasured.find((v: { name: string }) => v.name === 'Direct-dependents momentum (deps.dev)').description;
    expect(m3Description).toContain('linkage-verified');
  });
});
