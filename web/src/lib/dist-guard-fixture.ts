import { spawnSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import type { OwnerTypes } from './person_free';
import registry from './dist-guard-fixture.json';

// Invented owners live in the JSON file. A .ts source would teach the template
// word list those logins, and a bare login would then stop counting as private.
// id_map keys match the registry, so check-dist does not open live snapshots.
export const guardRegistry = registry as OwnerTypes;

export function writeGuardDirs(root: string, snapshotDate: string) {
  const dist = join(root, 'dist');
  const data = join(root, 'data');
  const etl = join(root, 'etl');
  mkdirSync(dist, { recursive: true });
  mkdirSync(join(data, 'snapshots'), { recursive: true });
  mkdirSync(etl, { recursive: true });
  writeFileSync(join(data, 'latest.json'), JSON.stringify({ snapshot_date: snapshotDate }));
  const repos = guardRegistry.repos;
  writeFileSync(join(etl, 'owner_types.json'), JSON.stringify({ schema_version: guardRegistry.schema_version, repos }));
  writeFileSync(join(etl, 'id_map.json'), JSON.stringify(Object.fromEntries(Object.keys(repos).map((repo) => [repo, repo]))));
  writeFileSync(join(etl, 'project_accounts.json'), JSON.stringify({ accounts: {} }));
  return { dist, data, etl };
}

export function runCheckDist(dist: string, data: string, etl: string) {
  return spawnSync(process.execPath, ['scripts/check-dist.mjs'], {
    encoding: 'utf8',
    env: { ...process.env, EVIDAXIS_DIST: dist, EVIDAXIS_DATA_DIR: data, EVIDAXIS_ETL_DIR: etl },
  });
}
