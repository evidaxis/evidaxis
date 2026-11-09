import { expect, it } from 'vitest';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { ownerTypes } from './data';
import { registryClassification, userHandleIndex } from './person_free';

it('limits dependency-token scanning to deps in published JSON', () => {
  const banned = [...userHandleIndex(ownerTypes).words][0];
  const publicRepo = [...registryClassification(ownerTypes).canonicalPaths][0];
  expect(banned).toBeTruthy();
  expect(publicRepo).toBeTruthy();
  const fixture = mkdtempSync(join(tmpdir(), 'evx-dependency-scope-'));
  try {
    const dist = join(fixture, 'dist');
    const data = join(fixture, 'data');
    mkdirSync(dist);
    mkdirSync(join(data, 'snapshots'), { recursive: true });
    writeFileSync(join(data, 'latest.json'), JSON.stringify({ snapshot_date: '2026-10-03' }));
    const pkg = `widget-${banned}-plugin`;
    writeFileSync(join(dist, 'deps-package.json'), JSON.stringify({ deps: { package: pkg } }));
    writeFileSync(join(dist, 'deps-system.json'), JSON.stringify({ deps: { system: pkg } }));
    writeFileSync(join(dist, 'deps-nested.json'), JSON.stringify({ records: [{ deps: { nested: [{ alias: pkg }, pkg] } }] }));
    writeFileSync(join(dist, 'safe-prose.json'), JSON.stringify({ description: pkg, signals: [{ package: pkg }], github_repo: `${publicRepo}-${pkg}` }));
    const result = spawnSync(process.execPath, ['scripts/check-dist.mjs'], {
      encoding: 'utf8', env: { ...process.env, EVIDAXIS_DIST: dist, EVIDAXIS_DATA_DIR: data },
    });
    // Missing routes are unrelated; pin the privacy diagnostics from the real guard.
    expect(result.error).toBeUndefined();
    expect(result.status).toBe(1);
    expect(result.stderr.toLowerCase()).not.toContain(banned.toLowerCase());
    expect(result.stderr).not.toContain('safe-prose.json:');
    for (const suffix of ['package', 'system', 'nested']) {
      expect(result.stderr).toMatch(new RegExp(`deps-${suffix}\\.json: rule=g hash=[0-9a-f]{8} contains private dependency owner`));
      expect(result.stderr).not.toContain(`deps-${suffix}.json: rule=f`);
    }
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});
