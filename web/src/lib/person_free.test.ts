import { describe, expect, it } from 'vitest';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  publicEntity, publicHomepage, publicName, publicRepoLabel, publicRepoUrl, revealsHandle, type OwnerTypes,
} from './person_free';

const registry: OwnerTypes = {
  schema_version: 'owner_types_1',
  repos: {
    'vllm-project/vllm': { owner_type: 'Organization', repo_id: 1, full_name: 'vllm-project/vllm' },
    'paul-gauthier/aider': { owner_type: 'Organization', repo_id: 2, full_name: 'Aider-AI/aider' },
    'jwohlwend/boltz': { owner_type: 'User', repo_id: 3, full_name: 'jwohlwend/boltz' },
    'gcorso/DiffDock': { owner_type: 'User', repo_id: 4, full_name: 'gcorso/DiffDock' },
    'mensfeld/code-on-incus': { owner_type: 'Organization', repo_id: 1129585228, full_name: 'coipond/coi' },
  },
};

describe('person-free repository publication', () => {
  it('keeps canonical organization labels and repository URLs', () => {
    const e = { github_repo: 'vllm-project/vllm', homepage: null };
    expect(publicRepoLabel(e, registry)).toBe('vllm-project/vllm');
    expect(publicRepoUrl(e, registry)).toBe('https://github.com/vllm-project/vllm');
  });

  it('publishes the canonical organization after a repository move', () => {
    const e = { github_repo: 'paul-gauthier/aider', homepage: 'https://aider.chat/' };
    expect(publicRepoLabel(e, registry)).toBe('Aider-AI/aider');
    expect(publicRepoUrl(e, registry)).toBe('https://github.com/Aider-AI/aider');
    expect(publicEntity(e, registry)).toMatchObject({ github_repo: 'Aider-AI/aider', homepage: 'https://aider.chat/' });
  });

  it.each([
    'https://github.com/mensfeld/code-on-incus',
    'https://www.GitHub.com/mensfeld/code-on-incus?tab=readme#top',
  ])('canonicalizes a confirmed transfer without changing its internal identity: %s', (homepage) => {
    const e = { entity_id: 'e_WJWEQY59YG9', github_repo: 'mensfeld/code-on-incus', homepage };
    expect(publicRepoLabel(e, registry)).toBe('coipond/coi');
    expect(publicRepoUrl(e, registry)).toBe('https://github.com/coipond/coi');
    expect(publicHomepage(e, registry)).toBe('https://github.com/coipond/coi');
    const projected = publicEntity(e, registry);
    expect(projected).toEqual({ ...e, github_repo: 'coipond/coi', homepage: 'https://github.com/coipond/coi' });
    expect(JSON.stringify(projected)).not.toContain('mensfeld');
    expect(e.github_repo).toBe('mensfeld/code-on-incus');
    expect(e.homepage).toBe(homepage);
  });

  it.each(['mensfeld', 'MENSFELD', '@mensfeld', 'https://github.com/mensfeld/code-on-incus'])(
    'keeps a confirmed former personal owner banned: %s', (text) => {
      expect(revealsHandle(text, registry)).toBe(true);
      expect(revealsHandle(text, { schema_version: 'owner_types_1', repos: {} })).toBe(true);
      expect(publicName({ name: text, entity_id: 'e_WJWEQY59YG9' }, registry)).toBe('System e_WJWEQY59YG9');
      expect(revealsHandle('coipond/coi', registry)).toBe(false);
    },
  );

  it('uses the durable former-owner ban and canonical URLs in Card B context', async () => {
    const { entityUniverse } = await import('./archive');
    const { contextFor } = await import('./cardB/context');
    const record = entityUniverse.find(r => r.entity.entity_id === 'e_WJWEQY59YG9')!;
    const context = contextFor(record);
    expect(context.bannedOwners).toContain('mensfeld');
    expect(context.repoLabel).toBe('coipond/coi');
    expect(context.repoUrl).toBe('https://github.com/coipond/coi');
    expect(context.repoApi).toBe('https://api.github.com/repos/coipond/coi');
    expect(context.homepage).toBe('https://github.com/coipond/coi');
  });

  it('keeps the dist guard strict for a former personal owner outside GitHub paths', () => {
    const fixture = mkdtempSync(join(tmpdir(), 'evx-owner-transfer-'));
    try {
      const dist = join(fixture, 'dist');
      const data = join(fixture, 'data');
      mkdirSync(dist);
      mkdirSync(join(data, 'snapshots'), { recursive: true });
      writeFileSync(join(data, 'latest.json'), JSON.stringify({ snapshot_date: '2026-10-03' }));
      writeFileSync(join(dist, 'leak.json'), JSON.stringify({ text: 'mensfeld' }));
      writeFileSync(join(dist, 'safe.json'), JSON.stringify({ github_repo: 'coipond/coi' }));
      const result = spawnSync(process.execPath, ['scripts/check-dist.mjs'], {
        encoding: 'utf8', env: { ...process.env, EVIDAXIS_DIST: dist, EVIDAXIS_DATA_DIR: data },
      });
      // The tiny fixture omits site routes; assert the specific privacy failure.
      expect(result.error).toBeUndefined();
      expect(result.status).toBe(1);
      expect(result.stderr).toContain('leak.json: contains private repository owner mensfeld');
      expect(result.stderr).not.toContain('safe.json:');
    } finally {
      rmSync(fixture, { recursive: true, force: true });
    }
  });

  it('publishes a User-owned repository name without its owner or GitHub URL', () => {
    const e = { github_repo: 'jwohlwend/boltz', homepage: 'https://github.com/jwohlwend/boltz' };
    expect(publicRepoLabel(e, registry)).toBe('boltz');
    expect(publicRepoUrl(e, registry)).toBeNull();
    expect(publicHomepage(e, registry)).toBeNull();
    const projected = publicEntity(e, registry);
    expect(projected).not.toHaveProperty('github_repo');
    expect(JSON.stringify(projected)).not.toContain('jwohlwend');
    expect(projected.repository).toEqual({ repo_name: 'boltz', owner_type: 'user', repo_ref: 'gh:3' });
  });

  it.each([
    'https://github.com/gcorso/DiffDock',
    'https://www.GitHub.com/gcorso/DiffDock/',
    'https://github.com/gcorso/DiffDock?tab=readme#top',
  ])('filters every GitHub homepage form for User ownership: %s', (homepage) => {
    expect(publicRepoUrl({ github_repo: 'gcorso/DiffDock', homepage }, registry)).toBeNull();
  });

  it('keeps a safe external homepage for User ownership', () => {
    expect(publicRepoUrl({ github_repo: 'gcorso/DiffDock', homepage: 'https://diffdock.example/' }, registry))
      .toBe('https://diffdock.example/');
  });

  it('filters an external homepage that embeds the User owner handle', () => {
    expect(publicRepoUrl({ github_repo: 'gcorso/DiffDock', homepage: 'https://models.example/gcorso/DiffDock' }, registry))
      .toBeNull();
  });

  it('fails closed when classification is unavailable', () => {
    expect(() => publicRepoLabel({ github_repo: 'new/repo' }, registry)).toThrow(/classification/);
  });
});

describe('publicPackageLabel', () => {
  it('hides a deps.dev package named like its personal owner and keeps others', async () => {
    const { publicPackageLabel } = await import('./person_free');
    const registry = { schema_version: 'owner_types_1', repos: {
      'some-person/some-person': { owner_type: 'User', repo_id: 11, full_name: 'some-person/some-person' },
    } } as never;
    expect(publicPackageLabel('pypi', 'some-person', registry)).toBe('package not shown');
    expect(publicPackageLabel('pypi', 'torch', registry)).toBe('pypi/torch');
  });
});
