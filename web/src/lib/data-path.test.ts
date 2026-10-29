import { afterEach, expect, it, vi } from 'vitest';
import { mkdtempSync, readFileSync, rmSync, symlinkSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join, relative } from 'node:path';
import { pathToFileURL } from 'node:url';
import { DATA_DIR, ETL_DIR, REPO_ROOT, assertUnitPath, dataPath, etlPath } from './data-path';
import { assertProductionPaths, FIXTURE_ROOT } from './path-policy.mjs';

const forbidden = /Hermetic unit test: live data\/ or etl\/ access forbidden/;
afterEach(() => vi.unstubAllEnvs());

it('loads the frozen snapshot and registry without consulting live paths', () => {
  expect(DATA_DIR).toBe(join(FIXTURE_ROOT, '2026-10-17/data'));
  expect(ETL_DIR).toBe(join(FIXTURE_ROOT, '2026-10-17/etl'));
  expect(JSON.parse(readFileSync(dataPath('latest.json'), 'utf8')).snapshot_date).toBe('2026-10-17');
  expect(JSON.parse(readFileSync(etlPath('owner_types.json'), 'utf8')).schema_version).toBe('owner_types_1');
});

it.each(['data/latest.json', 'etl/owner_types.json'])('rejects live paths through helpers and native fs: %s', async (path) => {
  const live = join(REPO_ROOT, path);
  expect(() => assertUnitPath(live)).toThrow(forbidden);
  expect(() => dataPath(relative(DATA_DIR, live))).toThrow(forbidden);
  expect(() => etlPath(relative(ETL_DIR, live))).toThrow(forbidden);
  expect(() => readFileSync(pathToFileURL(live))).toThrow(forbidden);
  expect(() => createRequire(import.meta.url)('fs').readFileSync(Buffer.from(live))).toThrow(forbidden);
  await expect(async () => readFile(live)).rejects.toThrow(forbidden);
});

it.each(['data', 'etl'])('rejects symlink aliases of live %s, including missing files', (dir) => {
  const temp = mkdtempSync(join(tmpdir(), 'evx-path-guard-'));
  try {
    symlinkSync(join(REPO_ROOT, dir), join(temp, 'alias'));
    expect(() => assertUnitPath(join(temp, 'alias', 'not-present.json'))).toThrow(forbidden);
  } finally { rmSync(temp, { recursive: true, force: true }); }
});

it.each(['EVIDAXIS_DATA_DIR', 'EVIDAXIS_ETL_DIR'])('rejects fixture paths in production: %s', (key) => {
  vi.stubEnv('EVIDAXIS_DATA_DIR', join(REPO_ROOT, 'data'));
  vi.stubEnv('EVIDAXIS_ETL_DIR', join(REPO_ROOT, 'etl'));
  vi.stubEnv(key, FIXTURE_ROOT);
  expect(() => assertProductionPaths()).toThrow(`Production fixture guard: ${key}`);
});
