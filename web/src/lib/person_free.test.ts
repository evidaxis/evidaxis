import { describe, expect, it } from 'vitest';
import {
  publicEntity, publicHomepage, publicName, publicRepoLabel, publicRepoUrl, revealsHandle, type OwnerTypes,
} from './person_free';

const registry: OwnerTypes = {
  schema_version: 'owner_types_1',
  repos: {
    'vllm-project/vllm': { owner_type: 'Organization', repo_id: 1, full_name: 'vllm-project/vllm' },
    'paul-gauthier/aider': { owner_type: 'Organization', repo_id: 2, full_name: 'Aider-AI/aider' },
    'fixture-user-alpha/sample-alpha': { owner_type: 'User', repo_id: 3, full_name: 'fixture-user-alpha/sample-alpha' },
    'fixture-user-beta/sample-beta': { owner_type: 'User', repo_id: 4, full_name: 'fixture-user-beta/sample-beta' },
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

  it('publishes a User-owned repository name without its owner or GitHub URL', () => {
    const e = { github_repo: 'fixture-user-alpha/sample-alpha', homepage: 'https://github.com/fixture-user-alpha/sample-alpha' };
    expect(publicRepoLabel(e, registry)).toBe('sample-alpha');
    expect(publicRepoUrl(e, registry)).toBeNull();
    expect(publicHomepage(e, registry)).toBeNull();
    const projected = publicEntity(e, registry);
    expect(projected).not.toHaveProperty('github_repo');
    expect(JSON.stringify(projected)).not.toContain('fixture-user-alpha');
    expect(projected.repository).toEqual({ repo_name: 'sample-alpha', owner_type: 'user', repo_ref: 'gh:3' });
  });

  it.each([
    'https://github.com/fixture-user-beta/sample-beta',
    'https://www.GitHub.com/fixture-user-beta/sample-beta/',
    'https://github.com/fixture-user-beta/sample-beta?tab=readme#top',
  ])('filters every GitHub homepage form for User ownership: %s', (homepage) => {
    expect(publicRepoUrl({ github_repo: 'fixture-user-beta/sample-beta', homepage }, registry)).toBeNull();
  });

  it('keeps a safe external homepage for User ownership', () => {
    expect(publicRepoUrl({ github_repo: 'fixture-user-beta/sample-beta', homepage: 'https://project.example/' }, registry))
      .toBe('https://project.example/');
  });

  it('filters an external homepage that embeds the User owner handle', () => {
    expect(publicRepoUrl({ github_repo: 'fixture-user-beta/sample-beta', homepage: 'https://models.example/fixture-user-beta/sample-beta' }, registry))
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
