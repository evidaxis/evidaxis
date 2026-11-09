import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { expect, it } from 'vitest';
import { classifyRegistry, buildHandleIndex, handleHitsDecoded, privacyDiagnostic, applyProjectAccounts, revealsHandleText } from './personFree.mjs';
import { publicEntity, publicHomepage, publicPackageLabel, publicName, revealsHandle } from './person_free';
import { publicDropped } from './public_dropped';
import { fixtureAnonymizer } from '../../scripts/fixture-privacy.mjs';

const vectors = JSON.parse(readFileSync(new URL('../../../tests/fixtures/person-free-conformance.json', import.meta.url), 'utf8')).cases;

it.each(vectors)('shared rules: $id', (c) => {
  const before = JSON.stringify(c);
  const classified = classifyRegistry(c.registry, c.accounts ?? {}, c.floor ?? []);
  expect({ handles: [...classified.handles].sort(), stalePaths: [...classified.stalePaths].sort(), publicRepos: [...classified.publicRepos].sort() }).toEqual(c.expected);
  const index = buildHandleIndex(classified.handles, new Set(c.templateWords ?? []));
  for (const probe of c.probes ?? []) expect(handleHitsDecoded(probe.text, index).sort()).toEqual(probe.hits);
  expect(JSON.stringify(c)).toBe(before);
});

it.each(vectors.filter((c: any) => c.projection))('publication experiment: $id', (c) => {
  const registry = { schema_version: 'owner_types_1', repos: structuredClone(c.registry) } as any;
  applyProjectAccounts(registry.repos, c.accounts ?? {});
  const p = c.projection;
  const e = { entity_id: 'e_DRILL', github_repo: p.repo, homepage: p.homepage };
  expect(publicHomepage(e, registry)).toBe(p.expectedHomepage);
  expect(publicEntity(e, registry).homepage).toBe(p.expectedHomepage);
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
