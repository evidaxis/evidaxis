import { expect, it } from 'vitest';
import { fixtureAnonymizer } from '../../scripts/fixture-privacy.mjs';

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
