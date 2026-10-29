import { describe, expect, it } from 'vitest';
import { publicProvenance } from './public_provenance';
import { ownerTypes } from './data';

// Real personal handles come from the data at run time; none is written in this file.
const [userRepo] = Object.entries(ownerTypes.repos).find(([, entry]) => entry.owner_type === 'User')!;
const userLogin = userRepo.split('/')[0];

describe('archived public provenance', () => {
  it('omits personal repository names, titles, authors and unknown capture fields', () => {
    const raw = Buffer.from(JSON.stringify({
      source_manifest: { github_repos: [userRepo], openalex_works: ['W1'] },
      author: userLogin,
      openalex_raw: { e_TEST: { by_year: { '2026': 3 }, raw: {
        W1: { title: userLogin, authors: [userLogin], counts_by_year: [{ year: 2026, cited_by_count: 3 }] },
      } } },
    }));
    const projected = publicProvenance(raw, ownerTypes);
    expect(JSON.stringify(projected)).not.toContain(userLogin);
    expect(projected.openalex_raw.e_TEST.raw.W1.counts_by_year).toEqual([{ year: 2026, cited_by_count: 3 }]);
    const unclassified = publicProvenance(raw, { schema_version: 'owner_types_1', repos: {} });
    expect(new Set(unclassified.source_manifest.github_repo_refs)).toEqual(new Set(['gh:unclassified']));
    expect(JSON.stringify(unclassified)).not.toMatch(/"[A-Za-z0-9-]+\/[A-Za-z0-9._-]+"/);
  });
});
