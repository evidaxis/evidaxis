import { describe, expect, it } from 'vitest';
import { buildHandleIndex, handleHits } from './personFree.mjs';

const index = buildHandleIndex(['f', 'av', '78', '100', 'e', 'rohitg00', 'paul-gauthier', 'hexgrad', 'Q00']);

describe('person-free handle matching at registry scale', () => {
  it('ignores short or numeric handles inside ordinary words, numbers and site paths', () => {
    expect(handleHits('A free weekly archive of 100 systems, 78 of them with a figure; av. commits', index)).toEqual([]);
    expect(handleHits('<a href="/e/e_ZZZKJHG7Q9A/">agentmemory</a> /ai/cohorts/x/page/100/', index)).toEqual([]);
  });
  it('catches a handle in repository slugs, GitHub URLs and API paths', () => {
    expect(handleHits('rohitg00/agentmemory', index)).toEqual(['rohitg00']);
    expect(handleHits('https://github.com/rohitg00/agentmemory', index)).toEqual(['rohitg00']);
    expect(handleHits('https://api.github.com/repos/rohitg00/agentmemory', index)).toEqual(['rohitg00']);
    expect(handleHits('see https://github.com/f/repo and https://github.com/100/x', index).sort()).toEqual(['100', 'f']);
  });
  it('catches mentions and distinctive standalone handles, case-insensitively', () => {
    expect(handleHits('thanks @AV', index)).toEqual(['av']);
    expect(handleHits('Built by Paul-Gauthier.', index)).toEqual(['paul-gauthier']);
    expect(handleHits('HEXGRAD model', index)).toEqual(['hexgrad']);
  });
  it('does not match a distinctive handle inside a longer token', () => {
    expect(handleHits('hexgrading and paul-gauthier-fan', index)).toEqual([]);
  });
});

describe('public projection of names that are handles', async () => {
  const { publicName, publicRepoLabel, revealsHandle } = await import('./person_free');
  const registry = { schema_version: 'owner_types_1', repos: {
    'AlphaAvatar/AlphaAvatar': { owner_type: 'User', repo_id: 1, full_name: 'AlphaAvatar/AlphaAvatar' },
    'vllm-project/vllm': { owner_type: 'Organization', repo_id: 2, full_name: 'vllm-project/vllm' },
  } } as any;
  it('masks a system whose name is a personal handle and keeps organisation names', () => {
    expect(revealsHandle('AlphaAvatar', registry)).toBe(true);
    expect(publicName({ name: 'AlphaAvatar', entity_id: 'e_33CWR7PEWV8' }, registry)).toBe('System e_33CWR7PEWV8');
    expect(publicName({ name: 'vLLM', entity_id: 'e_R372CCSVG44' }, registry)).toBe('vLLM');
    expect(publicRepoLabel({ github_repo: 'AlphaAvatar/AlphaAvatar' } as any, registry)).toBe('repository not shown');
    expect(publicRepoLabel({ github_repo: 'vllm-project/vllm' } as any, registry)).toBe('vllm-project/vllm');
  });
});
