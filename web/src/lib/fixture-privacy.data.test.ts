import { expect, it } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join, relative } from 'node:path';
import { REPO_ROOT, FIXTURE_ROOT } from './path-policy.mjs';
import { applyProjectAccounts, buildHandleIndex, handleHitsDecoded, FLOOR_HANDLES } from './personFree.mjs';

it('stores no live personal owner in any generated fixture file', () => {
  const registry = JSON.parse(readFileSync(join(REPO_ROOT, 'etl/owner_types.json'), 'utf8'));
  const accounts = JSON.parse(readFileSync(join(REPO_ROOT, 'etl/project_accounts.json'), 'utf8')).accounts;
  applyProjectAccounts(registry.repos, accounts);
  const owners = Object.entries(registry.repos).flatMap(([key, entry]: [string, any]) => entry.owner_type === 'User'
    ? [key.split('/')[0], entry.full_name.split('/')[0]] : []);
  const index = buildHandleIndex([...owners, ...FLOOR_HANDLES]);
  const failures: string[] = [];
  function scan(dir: string) {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) scan(path);
      else if (handleHitsDecoded(readFileSync(path, 'utf8') + '\n' + relative(FIXTURE_ROOT, path), index).length) {
        // Report paths only; failures must not create another personal-identifier log.
        failures.push(relative(FIXTURE_ROOT, path));
      }
    }
  }
  scan(FIXTURE_ROOT);
  expect(failures).toEqual([]);
});

it('keeps personal repository, homepage and package locators synthetic across the frozen joins', () => {
  const base = join(FIXTURE_ROOT, '2026-10-17');
  const read = (path: string) => JSON.parse(readFileSync(path, 'utf8'));
  const live = read(join(REPO_ROOT, 'etl/owner_types.json'));
  applyProjectAccounts(live.repos, read(join(REPO_ROOT, 'etl/project_accounts.json')).accounts);
  const frozen = read(join(base, 'etl/owner_types.json'));
  const pins = read(join(base, 'data/deps_id_map.json')).pins;
  const failures: string[] = [];
  for (const date of readdirSync(join(base, 'data/snapshots'))) {
    const source = new Map(read(join(REPO_ROOT, 'data/snapshots', date, 'snapshot.json')).entities.map((entity: any) => [entity.entity_id, entity]));
    const provenance = read(join(base, 'data/snapshots', date, 'provenance.json')).source_manifest.github_repos;
    for (const entity of read(join(base, 'data/snapshots', date, 'snapshot.json')).entities) {
      const original = source.get(entity.entity_id) as any;
      if (live.repos[original.github_repo]?.owner_type !== 'User') continue;
      const path = `${date}/${entity.entity_id}`;
      if (!entity.github_repo.startsWith('fixture-user-') || entity.github_repo === original.github_repo
        || !frozen.repos[entity.github_repo]?.full_name.startsWith('fixture-user-')
        || !provenance.includes(entity.github_repo)) failures.push(`${path}: repository join`);
      if (original.homepage && entity.homepage === original.homepage) failures.push(`${path}: homepage`);
      if (pins[entity.github_repo]?.package && !pins[entity.github_repo].package.startsWith('fixture-')) failures.push(`${path}: package`);
    }
  }
  expect(failures).toEqual([]);
});
