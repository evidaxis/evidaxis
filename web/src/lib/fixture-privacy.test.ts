import { expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { fixtureAnonymizer } from '../../scripts/fixture-privacy.mjs';
import { buildHandleIndex, classifyRegistry, dependencyFieldHits } from './personFree.mjs';

const dependencyCase = JSON.parse(readFileSync(new URL('../../../tests/fixtures/person-free-conformance.json', import.meta.url), 'utf8'))
  .cases.find((c: any) => c.id === 'dependency-package-token-boundaries');

it.each(dependencyCase.packages)('anonymizes dependency tokens on an organization row: $system/$package', (probe) => {
  const pkg = probe.package;
  const row = { github_repo: dependencyCase.publicPaths[0], name: 'widget-zzdrillfern-plugin',
    description: 'widget-zz-drill-person-plugin',
    deps: { system: probe.system, package: pkg, nested: [{ alias: pkg }, pkg] } };
  const before = structuredClone(row);
  const anonymize = fixtureAnonymizer([row], { repos: dependencyCase.registry }, {});
  const output = anonymize(row);
  expect(output.github_repo).toBe(row.github_repo);
  expect(output.name).toBe(row.name);
  expect(output.description).toBe(row.description);
  for (const value of [output.deps.package, output.deps.nested[0].alias, output.deps.nested[1]]) {
    if (probe.masked) expect(value).not.toBe(pkg);
    else expect(value).toBe(pkg);
  }
  if (probe.systemMasked) expect(output.deps.system).not.toBe(probe.system);
  else expect(output.deps.system).toBe(probe.system);
  const index = buildHandleIndex(classifyRegistry(dependencyCase.registry).handles);
  expect(dependencyFieldHits(output, index)).toEqual([]);
  expect(output).toEqual(anonymize(row));
  expect(row).toEqual(before);
});

it('replaces personal locators consistently, including encoded package URLs, without changing organizations', () => {
  const owner = 'zz-fixture-person', repo = `${owner}/private-project`, pkg = `@${owner}/private-package`;
  const org = 'zz-fixture-org/public-project';
  const registry = { repos: {
    [repo]: { owner_type: 'User', full_name: repo },
    [org]: { owner_type: 'Organization', full_name: org },
  } };
  const snapshot = { entities: [{ entity_id: 'synthetic-entity', github_repo: repo, homepage: 'https://personal-fixture.invalid/site', name: owner }] };
  const rows = [{ entity_id: 'synthetic-entity', signals: { deps: { package: pkg } }, url: `https://api.deps.dev/packages/${encodeURIComponent(pkg)}` }];
  const provenance = { github_repos: [repo, org], note: `see https://github.com/${repo} and @${owner}` };
  const documents = [snapshot, registry, rows, provenance];
  const transform = fixtureAnonymizer(documents, registry, {});
  const outputs = documents.map(transform);
  expect(outputs).toEqual(documents.map(fixtureAnonymizer([...documents].reverse(), registry, {})));
  const entity = outputs[0].entities[0];
  expect(entity.github_repo).toMatch(/^fixture-user-[a-f0-9]+\/fixture-repo-[a-f0-9]+$/);
  expect(outputs[1].repos[entity.github_repo].full_name).toBe(entity.github_repo);
  expect(outputs[2][0].url).toBe(`https://api.deps.dev/packages/${encodeURIComponent(outputs[2][0].signals.deps.package)}`);
  expect(outputs[3].github_repos).toEqual([entity.github_repo, org]);
  expect(outputs[3].note).toContain(`https://github.com/${entity.github_repo}`);
  expect(entity.homepage).toMatch(/^https:\/\/fixture-home-[a-f0-9]+\.invalid\/$/);
  for (const original of [owner, repo, pkg, snapshot.entities[0].homepage]) expect(JSON.stringify(outputs)).not.toContain(original);
  expect(snapshot.entities[0].github_repo).toBe(repo);
});

it('keeps an organisation that handed one repository to a person', () => {
  const registry = { repos: {
    'zz-fixture-org/kept': { owner_type: 'Organization', full_name: 'zz-fixture-org/kept' },
    'zz-fixture-org/given': { owner_type: 'User', full_name: 'zz-fixture-person/given' },
  } };
  const provenance = {
    github_repos: ['zz-fixture-org/kept', 'zz-fixture-org/given'],
    note: 'zz-fixture-org%2Fgiven zz-fixture-org%252Fgiven zz-fixture-org%25252Fgiven',
  };
  const output = fixtureAnonymizer([provenance, registry], registry, {})(provenance);
  expect(output.github_repos[0]).toBe('zz-fixture-org/kept');
  expect(output.github_repos[1]).toMatch(/^fixture-user-[a-f0-9]+\/fixture-repo-[a-f0-9]+$/);
  // The old path is a locator of a personal repository in every encoding the guards decode.
  expect(output.note.toLowerCase()).not.toContain('zz-fixture-org');
});
