import { describe, expect, it } from 'vitest';
import {
  publicEntity, publicHomepage, publicRepoLabel, publicRepoUrl, type OwnerTypes,
} from './person_free';

const registry: OwnerTypes = {
  schema_version: 'owner_types_1',
  repos: {
    'vllm-project/vllm': { owner_type: 'Organization', repo_id: 1, full_name: 'vllm-project/vllm' },
    'paul-gauthier/aider': { owner_type: 'Organization', repo_id: 2, full_name: 'Aider-AI/aider' },
    'jwohlwend/boltz': { owner_type: 'User', repo_id: 3, full_name: 'jwohlwend/boltz' },
    'gcorso/DiffDock': { owner_type: 'User', repo_id: 4, full_name: 'gcorso/DiffDock' },
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
