import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { expect, it } from 'vitest';
import { classifyRegistry, buildHandleIndex, handleHitsDecoded, privacyDiagnostic, applyProjectAccounts, revealsHandleText, decimalEntitiesDecoded } from './personFree.mjs';
import { publicEntity, publicHomepage, publicPackageLabel, publicName, revealsHandle, registryClassification } from './person_free';
import { publicDropped } from './public_dropped';
import { fixtureAnonymizer } from '../../scripts/fixture-privacy.mjs';
import { enumerateSnapshots } from './archive';
import { ownerTypes } from './data';
import { etlPath } from './data-path';

const vectors = JSON.parse(readFileSync(new URL('../../../tests/fixtures/person-free-conformance.json', import.meta.url), 'utf8')).cases;

const summary = (classified: ReturnType<typeof classifyRegistry>) => ({
  handles: [...classified.handles].sort(), stalePaths: [...classified.stalePaths].sort(), publicRepos: [...classified.publicRepos].sort(),
});
const registryFor = (c: any) => {
  const registry = { schema_version: 'owner_types_1', repos: structuredClone(c.registry), projectAccounts: c.accounts ?? {} } as any;
  applyProjectAccounts(registry.repos, registry.projectAccounts);
  return registry;
};

it.each(vectors)('shared rules: $id', (c) => {
  const before = JSON.stringify(c);
  const classified = classifyRegistry(c.registry, c.accounts ?? {}, c.floor ?? []);
  expect(summary(classified)).toEqual(c.expected);
  const index = buildHandleIndex(classified.handles, new Set(c.templateWords ?? []));
  for (const probe of c.probes ?? []) expect(handleHitsDecoded(probe.text, index).sort()).toEqual(probe.hits);
  expect(JSON.stringify(c)).toBe(before);
});

it.each(vectors.filter((c: any) => c.strictExpected))('loaded classification: $id', (c) => {
  const registry = registryFor(c);
  const actual = registryClassification(registry);
  // The production floor is additive; compare the vector's fictional handles.
  expect([...actual.handles].filter(h => h.startsWith('zz-drill-')).sort()).toEqual(c.expected.handles);
  expect([...actual.stalePaths].sort()).toEqual(c.expected.stalePaths);
  expect([...actual.publicRepos].sort()).toEqual(c.expected.publicRepos);
  if (c.strictExpected) {
    const strict = registryClassification({ ...registry, projectAccounts: {} });
    expect([...strict.handles].filter(h => h.startsWith('zz-drill-')).sort()).toEqual(c.strictExpected.handles);
    expect([...strict.stalePaths].sort()).toEqual(c.strictExpected.stalePaths);
  }
});

it.each(vectors.filter((c: any) => c.projection))('publication experiment: $id', (c) => {
  const registry = registryFor(c);
  const p = c.projection;
  const e = { entity_id: 'e_DRILL', github_repo: p.repo, homepage: p.homepage };
  expect(publicHomepage(e, registry)).toBe(p.expectedHomepage);
  expect(publicEntity(e, registry).homepage).toBe(p.expectedHomepage);
});

it.each(vectors.filter((c: any) => c.diagnostics))('diagnostic path uses full classification: $id', (c) => {
  const classified = classifyRegistry(c.registry, c.accounts ?? {}, c.floor ?? []);
  const index = buildHandleIndex(classified.handles, new Set(c.templateWords ?? []));
  for (const probe of c.diagnostics) {
    const line = privacyDiagnostic(probe.path, probe.rule, probe.value, index, classified);
    if (probe.privatePath) expect(line).toMatch(/^\[path:[0-9a-f]{8}\]: rule=[fd] hash=[0-9a-f]{8}$/);
    else expect(line.startsWith(probe.path + ':')).toBe(true);
  }
});

it.each(vectors.filter((c: any) => c.decimalEntities))('HTML decimal scanning: $id', (c) => {
  const index = buildHandleIndex(classifyRegistry(c.registry).handles);
  for (const probe of c.decimalEntities) {
    const decoded = decimalEntitiesDecoded(probe.text);
    expect(decoded).toBe(probe.decoded);
    expect(handleHitsDecoded(probe.text + '\n' + decoded, index).sort()).toEqual(probe.hits);
  }
});

it('passes the complete project account map through both website loaders', () => {
  expect(ownerTypes.projectAccounts).toEqual(JSON.parse(readFileSync(etlPath('project_accounts.json'), 'utf8')).accounts);
  const c = vectors.find((c: any) => c.id === 'project-account-transfers-last-repository');
  const root = mkdtempSync(join(tmpdir(), 'evx-project-transfer-'));
  try {
    const date = '2026-10-17';
    const dir = join(root, 'data/snapshots', date);
    mkdirSync(dir, { recursive: true });
    mkdirSync(join(root, 'etl'));
    writeFileSync(join(root, 'etl/owner_types.json'), JSON.stringify({ repos: c.registry }));
    writeFileSync(join(root, 'etl/project_accounts.json'), JSON.stringify({ accounts: c.accounts }));
    const entity = { entity_id: 'e_DRILL', name: 'zz-drill-project', slug: 'zz-drill-project', github_repo: c.projection.repo };
    writeFileSync(join(dir, 'snapshot.json'), JSON.stringify({ snapshot_date: date, entities: [entity] }));
    expect(enumerateSnapshots(root)[0].entities[0]).toEqual(entity);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

it('masks former handles in every published field and dropped free text', () => {
  const registry = { schema_version: 'owner_types_1', repos: vectors[1].registry } as any;
  const former = 'zz-drill-former';
  const e = { entity_id: 'e_DRILL', name: former, slug: former, github_repo: `${former}/tool`, description: `by ${former}`, note: `by ${former}`, deps: { package: former } };
  const out = publicEntity(e, registry);
  expect(out.name).toBe('System e_DRILL');
  expect(out.slug).toBe('e_drill');
  expect(out.description).toBeNull();
  expect(out).not.toHaveProperty('note');
  expect(out.deps).toEqual({ package: 'package not shown' });
  expect(publicName(e, registry)).toBe('System e_DRILL');
  expect(publicPackageLabel('pypi', former, registry)).toBe('package not shown');
  const raw = Buffer.from(JSON.stringify({ note: `by ${former}`, dropped: [{ github_repo: e.github_repo, reason: `by ${former}` }] }));
  expect(JSON.stringify(publicDropped(raw, registry))).not.toContain(former);
});

it('keeps a live organization public while anonymizing its transferred path', () => {
  const c = vectors[0];
  const registry = { repos: c.registry };
  const source = { github_repo: 'zz-drill-lab/given', note: 'zz-drill-lab remains public' };
  const project = fixtureAnonymizer([source], registry, {}, ['zz-drill-lab']);
  expect(project(source).github_repo).not.toBe(source.github_repo);
  expect(project(source).note).toBe(source.note);
});

it('uses template words only in GitHub contexts in the mask', () => {
  const registry = { repos: vectors[6].registry } as any;
  expect(revealsHandle('System', registry)).toBe(false);
  expect(revealsHandle('https://system.github.io', registry)).toBe(true);
});

it('diagnostics omit the identifier and change salt between processes', () => {
  const index = buildHandleIndex(['zz-drill-secret']);
  const line = privacyDiagnostic('zz-drill-secret/page.json', 'f', 'zz-drill-secret', index);
  expect(line).toMatch(/^\[path:[0-9a-f]{8}\]: rule=f hash=[0-9a-f]{8}$/);
  expect(line).not.toContain('zz-drill-secret');
  expect(line).toBe(privacyDiagnostic('zz-drill-secret/page.json', 'f', 'zz-drill-secret', index));
  const script = "import {privacyDiagnostic} from './src/lib/personFree.mjs'; console.log(privacyDiagnostic('page.json', 'f', 'zz-drill-secret'))";
  const run = () => execFileSync(process.execPath, ['--input-type=module', '-e', script], { encoding: 'utf8' });
  expect(run()).not.toBe(run());
  expect(privacyDiagnostic('zz-drill-lab/given/page.json', 'd', 'zz-drill-lab/given', index))
    .toMatch(/^\[path:[0-9a-f]{8}\]: rule=d hash=[0-9a-f]{8}$/);
});

it('masks exact short field values even when present in source', () => {
  const index = buildHandleIndex(['f', '78', 'system'], new Set(['f', '78', 'system']));
  expect(revealsHandleText(' F ', index)).toBe(true);
  expect(revealsHandleText('78', index)).toBe(true);
  expect(revealsHandleText('System', index)).toBe(false);
});

it('masks stale paths in free text without banning the live organization', () => {
  const registry = { repos: vectors[0].registry } as any;
  const path = 'zz-drill-lab/given';
  const entity = { entity_id: 'e_DRILL', github_repo: path, description: path, deps: { package: path } };
  const projected = publicEntity(entity, registry);
  expect(projected.description).toBeNull();
  expect(projected.deps).toEqual({ package: 'package not shown' });
  expect(revealsHandle('zz-drill-lab is public', registry)).toBe(false);
  const note = 'HTTP example: https://example.invalid/%20';
  expect(publicDropped(Buffer.from(JSON.stringify({ note, dropped: [] })), registry).note).toBe(note);
});
