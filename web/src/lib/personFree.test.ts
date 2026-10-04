import { describe, expect, it } from 'vitest';
import { buildHandleIndex, handleHits, handleHitsDecoded } from './personFree.mjs';

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

describe('review fixes 2026-10-04: GitHub contexts, encoding', () => {
  const index = buildHandleIndex(['q7', 'synthuser', '78', 'f']);
  it.each([
    'https://github.com/q7',
    'see github.com/q7?tab=repositories',
    'https://q7.github.io/site',
    'https://raw.githubusercontent.com/q7/tool/main/a.png',
  ])('catches a handle in an explicit GitHub context: %s', (text) => {
    expect(handleHits(text, index)).toContain('q7');
  });
  it('catches a percent-encoded handle', () => {
    expect(handleHitsDecoded('github.com%2Fsynthuser%2Frepo', index)).toContain('synthuser');
  });
  it.each(['growth of 78% in q7 terms', 'f is a letter', 'github.com/some-org-name'])('keeps ordinary text clean: %s', (text) => {
    expect(handleHits(text, buildHandleIndex(['78', 'f']))).toEqual([]);
  });
});
