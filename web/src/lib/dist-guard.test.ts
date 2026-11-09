import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { expect, it } from 'vitest';
import handles from '../data/person-free-handles.json';
import { FLOOR_HANDLES } from './personFree.mjs';
import { registryClassification } from './person_free';
import { publicDropped } from './public_dropped';
import { publicProvenance } from './public_provenance';
import { guardRegistry, runCheckDist, writeGuardDirs } from './dist-guard-fixture';

const bannedHandle = (handles as string[])[0];
const [userRepo] = Object.entries(guardRegistry.repos).find(([, entry]) => entry.owner_type === 'User')!;
const userLogin = userRepo.split('/')[0];
const stalePaths = [...registryClassification(guardRegistry).stalePaths];

function provenanceRaw() {
  return Buffer.from(JSON.stringify({
    snapshot_id: 'fixture-snapshot',
    methodology_version: 'm-fixture',
    fetcher_version: 'f-fixture',
    captured_at: '2026-01-01T00:00:00Z',
    manifest_hash: 'fixture-manifest',
    source_manifest: { github_repos: Object.keys(guardRegistry.repos), openalex_works: [] },
    github_weekly_raw: {},
    openalex_raw: {},
    provisional: false,
    spine_complete: true,
  }));
}

it('keeps the dist guard strict for a former personal owner outside GitHub paths', () => {
  const banned = FLOOR_HANDLES[0];
  const safeRepo = Object.values(guardRegistry.repos).find(entry => entry.owner_type === 'Organization'
    && !FLOOR_HANDLES.includes(entry.full_name.split('/')[0].toLowerCase()))!.full_name;
  const fixture = mkdtempSync(join(tmpdir(), 'evx-owner-transfer-'));
  try {
    const { dist, data, etl } = writeGuardDirs(fixture, '2026-10-03');
    writeFileSync(join(dist, 'leak.json'), JSON.stringify({ text: banned }));
    writeFileSync(join(dist, 'safe.json'), JSON.stringify({ github_repo: safeRepo }));
    const result = runCheckDist(dist, data, etl);
    // The tiny fixture omits site routes; assert the specific privacy failure.
    expect(result.error).toBeUndefined();
    expect(result.status).toBe(1);
    expect(result.stderr).toMatch(/leak\.json: rule=f hash=[0-9a-f]{8} contains private repository owner/);
    expect(result.stderr.toLowerCase()).not.toContain(banned.toLowerCase());
    expect(result.stderr).not.toContain('safe.json:');
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});

it.each([['ban-list handle', bannedHandle], ['registry personal owner', userLogin]])(
  'check-dist rejects a %s in archived provenance', (_kind, owner) => {
    const fixture = mkdtempSync(join(tmpdir(), 'evx-archive-provenance-'));
    try {
      const date = '2026-09-26';
      const { dist, data, etl } = writeGuardDirs(fixture, date);
      const archive = join(dist, 'snapshots', date);
      mkdirSync(archive, { recursive: true });
      const path = join(archive, 'provenance.json');
      const raw = provenanceRaw();
      const projected = publicProvenance(raw, guardRegistry);
      writeFileSync(path, JSON.stringify({ ...projected, injected: owner }));
      const run = () => runCheckDist(dist, data, etl);
      const broken = run();
      expect(broken.error).toBeUndefined();
      expect(broken.status).toBe(1);
      expect(broken.stderr).toMatch(new RegExp(`snapshots/${date}/provenance\\.json: rule=f hash=[0-9a-f]{8} contains private repository owner`));
      expect(broken.stderr.toLowerCase()).not.toContain(owner.toLowerCase());
      // The minimal fixture omits site routes; isolate the privacy failure from those.
      writeFileSync(path, JSON.stringify(projected));
      const repaired = run();
      expect(repaired.stderr).not.toContain(`snapshots/${date}/provenance.json:`);
      expect(readFileSync(path, 'utf8').toLowerCase()).not.toContain(owner.toLowerCase());
    } finally {
      rmSync(fixture, { recursive: true, force: true });
    }
  },
);

it('check-dist rejects the old path of every repository a person owns today', () => {
  expect(stalePaths.length).toBeGreaterThan(0);
  const fixture = mkdtempSync(join(tmpdir(), 'evx-stale-provenance-'));
  try {
    const date = '2026-09-26';
    const { dist, data, etl } = writeGuardDirs(fixture, date);
    const archive = join(dist, 'snapshots', date);
    mkdirSync(archive, { recursive: true });
    const path = join(archive, 'provenance.json');
    const projected = publicProvenance(provenanceRaw(), guardRegistry);
    const twice = (value: string) => encodeURIComponent(encodeURIComponent(value));
    writeFileSync(path, JSON.stringify({ ...projected, injected: stalePaths, injected_twice: stalePaths.map(twice) }));
    const run = runCheckDist(dist, data, etl);
    expect(run.status).toBe(1);
    // Count, not paths: a failing run must not print personal locators into the CI log.
    const hits = run.stderr.split('\n').filter((line) => line.includes(`snapshots/${date}/provenance.json: rule=d hash=`));
    expect(hits.length).toBe(stalePaths.length);
    for (const path of stalePaths) expect(run.stderr.toLowerCase()).not.toContain(path);
    writeFileSync(path, JSON.stringify({ ...projected, injected_twice: stalePaths.map(twice) }));
    const encodedOnly = runCheckDist(dist, data, etl);
    expect(encodedOnly.stderr.split('\n').filter((line) => line.includes('contains stale repository path')).length).toBe(stalePaths.length);
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});

const FAKE_OWNER = 'zzdroppedfixture';
const FAKE_REPO = `${FAKE_OWNER}/zznotarepo`;

it('check-dist rejects a raw dropped.json that still carries an invented User handle', () => {
  const fixture = mkdtempSync(join(tmpdir(), 'evx-archive-dropped-'));
  try {
    const date = '2026-09-26';
    const { dist, data, etl } = writeGuardDirs(fixture, date);
    const archive = join(dist, 'snapshots', date);
    mkdirSync(archive, { recursive: true });
    const diskRegistry = JSON.parse(readFileSync(join(etl, 'owner_types.json'), 'utf8'));
    expect(JSON.stringify(diskRegistry).toLowerCase()).not.toContain(FAKE_OWNER);
    const path = join(archive, 'dropped.json');
    const raw = Buffer.from(JSON.stringify({
      v: 'dropped_1',
      snapshot_date: date,
      note: 'synthetic fixture',
      dropped: [{
        entity_id: 'e_FIXTURE',
        github_repo: FAKE_REPO,
        previously_tracked: true,
        reason: `no record for ${FAKE_REPO}`,
      }],
    }));
    writeFileSync(path, raw);
    const run = () => runCheckDist(dist, data, etl);
    const broken = run();
    expect(broken.error).toBeUndefined();
    expect(broken.status).toBe(1);
    expect(broken.stderr).toContain(`snapshots/${date}/dropped.json: missing projection person_free_dropped_1`);
    expect(broken.stderr).toContain(`snapshots/${date}/dropped.json: contains github_repo`);
    expect(readFileSync(path, 'utf8').toLowerCase()).toContain(FAKE_OWNER);
    writeFileSync(path, JSON.stringify(publicDropped(raw, guardRegistry)));
    const repaired = run();
    expect(repaired.stderr).not.toContain(`snapshots/${date}/dropped.json:`);
    expect(readFileSync(path, 'utf8').toLowerCase()).not.toContain('"github_repo"');
    expect(readFileSync(path, 'utf8')).toContain('person_free_dropped_1');
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});
