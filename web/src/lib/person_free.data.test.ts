import { expect, it } from 'vitest';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { ownerTypes } from './data';
import { FLOOR_HANDLES } from './personFree.mjs';
it('keeps the dist guard strict for a former personal owner outside GitHub paths', () => {
  const banned = FLOOR_HANDLES[0];
  const safeRepo = Object.values(ownerTypes.repos).find(entry => entry.owner_type === 'Organization'
    && !FLOOR_HANDLES.includes(entry.full_name.split('/')[0].toLowerCase()))!.full_name;
  const fixture = mkdtempSync(join(tmpdir(), 'evx-owner-transfer-'));
  try {
    const dist = join(fixture, 'dist');
    const data = join(fixture, 'data');
    mkdirSync(dist);
    mkdirSync(join(data, 'snapshots'), { recursive: true });
    writeFileSync(join(data, 'latest.json'), JSON.stringify({ snapshot_date: '2026-10-03' }));
    writeFileSync(join(dist, 'leak.json'), JSON.stringify({ text: banned }));
    writeFileSync(join(dist, 'safe.json'), JSON.stringify({ github_repo: safeRepo }));
    const result = spawnSync(process.execPath, ['scripts/check-dist.mjs'], {
      encoding: 'utf8', env: { ...process.env, EVIDAXIS_DIST: dist, EVIDAXIS_DATA_DIR: data },
    });
    // The tiny fixture omits site routes; assert the specific privacy failure.
    expect(result.error).toBeUndefined();
    expect(result.status).toBe(1);
    expect(result.stderr).toContain(`leak.json: contains private repository owner ${banned.toLowerCase()}`);
    expect(result.stderr).not.toContain('safe.json:');
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});
