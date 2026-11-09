# Person-free dependency tokens, 2026-11-09

This supplements the two earlier F1-1 errata after PR 36's `benign_all`
class-j oracle found two website leaks and one HF leak. The package label
embedded a fictional personal login between hyphens. The matcher treated the
entire hyphenated label as one word, so the publication masks missed it.

## Correction

The shared Python and JS matchers now recognize distinctive personal handles
bounded by characters other than ASCII letters or digits. Hyphens can be both
token boundaries and part of a handle. Candidate windows retain internal
hyphens and stop at the longest handle in the input index; this adds no fixed
limit. Leading/trailing and repeated separator hyphens are covered too.

The handle sets still come from `classify_registry` / `classifyRegistry`.
Current and former personal owners receive the same treatment. Organization
and project-account exceptions remain in the classifier. Rule f still exempts
template words outside GitHub context and short/numeric tokens in ordinary
text; exact short field values retain their existing mask.

Both publication projections mask every revealing string value within `deps`,
including nested objects and arrays. Existing package fields elsewhere are
also masked. Package labels check both the ecosystem and the package component.
Measurements retain their values. The common matcher also strengthens existing
name, slug, repository, homepage and free-text masks and both byte scanners.

The shared fixture includes current and former handles, an alphanumeric handle
after an organization-to-person transfer, organization negatives, template-word
negatives and explicit GitHub context, percent encoding, case, punctuation,
repeated hyphens, and adjacent letter/digit negatives. Both suites exercise the
website/HF projection with those same package expectations and preserve input
objects. HF tests scan the resulting bytes and the deliberately unmasked input.

## Single-source consumers

All eight consumers from review section 1.4 continue to use the shared
classification, directly or through its accessor:

1. `scripts/person_free.py`: the loaded index, HF projection and HF scanner.
2. `web/src/lib/personFree.mjs`: `personalOwnerHandles` / `personalStalePaths`.
3. `web/src/lib/person_free.ts`: website masks and archive text projection.
4. `web/scripts/check-dist.mjs`: website byte scanner and provenance checks.
5. `web/src/lib/public_dropped.ts`: dropped-record projection.
6. `web/src/lib/public_dropped.data.test.ts`: live archive privacy assertions.
7. `scripts/person_index_build.py`: registry and current-owner adapters.
8. `web/scripts/fixture-privacy.mjs`: fixture anonymization inputs.

The single-source guard and its exceptions were not relaxed. This revision
changes consumers 1-3 and the HF projection, with no additional owner-type rule
in consumers. The frozen fixture and `etl/` are unchanged.

## Verification

- Before the fix, the new shared-vector/projection cases failed seven tests
  in each language.
- Required Python trio: 125 tests passed.
- Full `tests/` run on the final code: 7,597 passed, one skipped. The existing
  recall test skips when its gitignored census working data is absent.
- Additional index, hook, new-byte, project-account and Zenodo tests: 31 passed.
- JS conformance: 48 passed. `npm run test:run`: 414 passed in 34 files.
- Live person-free, dropped and provenance data tests: seven passed, including
  actual `check-dist` child processes and diagnostic privacy assertions.
- HF dry-run for 2026-11-07: 6,682 entities, 25 neutralized names, 3,044 redacted
  fields, zero guard findings. No upload was performed.
- A mechanical set of 2,000 synthetic token strings matched an independent
  per-handle regular-expression oracle for the specified boundaries.

The full Python run initially found two expected-count assertions for the
2026-10-03 snapshot that predated this stronger mask. The precise counts are now
18 with project-account exceptions and 28 without them, previously 12 and 22.
The test also pins the six additional entities' neutral names/slugs and hidden
repository names. The separate archive identity test initially lacked its
tracked `data/observations/errata_snapshot_id.json` in this sparse checkout.
That file was restored byte-for-byte from HEAD, without changing tracked data.

All five intentional source mutations failed and were restored byte-for-byte:

| Mutation | Observed failure |
| --- | --- |
| Wrong shared-vector expectation | Python and JS conformance, exit 1 |
| Raw owner-type branch in `hubs.ts` | Single-source guard, exit 1 |
| Website index containing only current owners | Former-owner homepage experiment, exit 1 |
| Former live organization treated as personal | Both language suites, exit 1 |
| Remove package masks from labels and projections | Both language suites, exit 1 |

The package mutation was repeated after the final separator-boundary cases were
added. The final green runs followed restoration.

## Additional masking and expected dist changes

In-memory projection comparisons used the same complete live archive for local
`main` (`0547b1a3c2478b2059fe5593ff3e00b45a48da7e`) and the working tree. They
recorded only dates, entity ids and field names. Previously hidden names,
repository names/addresses and homepages did not become public on these inputs.
The source-vocabulary change did not add or remove any known personal handle
from the template-word exemption.

This revision adds 57 changed entity rows on each surface relative to branch
HEAD. The additional changes are identical for website and HF:

| Entities | Newly masked fields | Dates |
| --- | --- | --- |
| `e_C7XBRXBQQ1A`, `e_SZKD4NSDYWH`, `e_P8DR6F4BC0K`, `e_R60YV8ENRHB`, `e_25NRZ6KAYTE`, `e_34ZSW4G3AHD` | Name, slug, repository name | Seven weekly snapshots, 2026-09-26 through 2026-11-07 |
| `e_JQ5QGB77PQV` | Name, slug, repository name | 2026-11-07 |
| `e_5BH7JNQ3YEN`, `e_BJJZC7FYMKN` | Repository address and homepage; repository replaced by a reference with its name hidden | Seven weekly snapshots, 2026-09-26 through 2026-11-07 |

Including the previous F1-1 revisions, the comparison to main changes 69 website
rows and 64 HF rows. The earlier changes for `e_RYZNSTS8RB1` (both surfaces,
seven snapshots) and `e_YCSQMCVD2PT` (website, five snapshots from 2026-10-10)
remain. All affected systems are in `unassigned-v1` on the latest snapshot.
The live archive comparison adds no dependency-field differences: the synthetic
vectors cover the class-j package that the rehearsal introduces.

Expected dist differences follow the stronger publication mask:

- Affected `e/<id>/index.html` and `e/<id>.json`: neutral names/slugs and hidden
  repository/homepage values.
- `snapshots/<date>/snapshot.json` for 2026-09-26, 2026-10-03, 2026-10-10,
  2026-10-17, 2026-10-24, 2026-10-31 and 2026-11-07.
- `search-index.json`, `llms.txt`, and
  `ai/cohorts/unassigned-v1/systems.json` / `systems.csv`: neutral names.
- Snapshot, unassigned-cohort and coverage HTML pagination: renamed systems
  change alphabetical positions, including neighboring rows shifted between pages.
- Badge outputs, Card B JSON/CSV, SVG chart labels, per-system/global feeds and
  signal pages wherever they materialize the affected names or links. Peer charts
  can change for other systems in the same cohort because they include peer names.

This is a source/projection audit, not a built-dist hash comparison. The
orchestrator owns full `npm run verify`, candidate `benign_all`, PR leak drills
and the exact before/after dist file comparison. No result for those runs is
claimed here. Methodology, configured limits, schedules and canary assignment
were not changed.
