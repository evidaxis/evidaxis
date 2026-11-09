# Person-free classifier review corrections, 2026-11-09

This supplements `ERRATUM-2026-11-09-person-free-classifier.md` after review
`codex-20261109T142836-8684` of commit `904ed6f103`. The earlier record remains
unchanged. These are publication correctness fixes under invariant 1; methodology,
project-account decisions, frozen inputs, canary behavior and schedules are unchanged.

## Corrections

1. Rule h: HF and website guard findings pass the complete classification to
   their diagnostic formatter. Artifact paths are checked for personal handles
   and stale personal paths regardless of the finding's rule. A private artifact
   path is represented only by its salted eight-character digest, including when
   a rule-f finding occurs inside a rule-d path. Safe public paths remain readable.
2. Rule g: a known personal current or former owner's homepage is masked even
   when that login is a template word. The rule-f exemption still applies to
   ordinary prose. Shared vectors exercise both current and former fictional
   owners on a non-GitHub host.
3. Rules a-c: the Python classification loader passes the complete project-account
   map separately from registry rows. The website's data and archive loaders retain
   the same map in memory and pass it through `registryClassification`. A listed
   account stays public after its last tracked repository transfers away. HF uses
   the loaded classification directly instead of rebuilding it without this map.
   Python's strict mode still omits project-account exceptions. Dropped/provenance
   data assertions use the same website accessor, preserving its account input.
4. HF decimal HTML decoding follows the existing JavaScript guard's
   `String.fromCharCode(Number(...))` coercion. Out-of-range numeric references no
   longer raise `ValueError`; raw and decoded text are still scanned. The shared
   vectors include an invalid reference alone, beside a plain mention, beside an
   encoded mention, and an integer beyond exact double precision. JavaScript's
   decoding behavior is unchanged.

The shared vectors are synthetic. No personal identifier store is added. All
eight consumers listed in the earlier record still use the two shared classifier
functions. The single-source guard and its exemptions have not been relaxed.

## Verification

Before production fixes, the new tests reproduced all four defects: eight Python
failures and five JS failures. The HTML decoder failure was Python-only; the JS
behavior is the compatibility reference.

After the fixes:

- Required Python trio: 107 tests passed. The final combined run, including
  project-account, index-builder and Zenodo tests, passed all 121 tests.
- JS conformance: 31 tests passed.
- `npm run test:run`: 397 tests passed in 34 files.
- Three data-test files covering person-free, dropped and provenance output:
  seven tests passed, including actual `check-dist` child processes.
- HF dry-run for 2026-11-07: 6,682 entities, 18 neutralized names, 3,028 redacted
  fields, zero guard findings. No upload was performed.

The extended Python run exposed two old exact-count assertions for the 2026-10-03
snapshot. Comparing the main and working-tree HF projections identified the
additional neutralized system as `e_RYZNSTS8RB1` (rule c). The assertions now
require 12 and 22 neutralized names instead of 11 and 21, respectively, and also
pin that entity's neutral name and slug. This records the stronger mask.

Four intentional source mutations were run and restored byte-for-byte:

| Mutation | Observed failure |
| --- | --- |
| Wrong shared-vector expectation | Python and JS conformance, exit 1 |
| Raw owner-type decision in `hubs.ts` | Single-source guard identifies that file, exit 1 |
| Website index containing current owners only | Former-owner homepage publication experiment, exit 1 |
| Former live organization counted as personal | Both language suites and live-organization publication experiment, exit 1 |

The required Python tests and JS conformance passed again after restoration.
These mutations exercise the shared vectors and publication functions locally.
The orchestrator owns full candidate `benign_all`, leak drills, `npm run verify`
and the built-dist hash comparison; none is claimed here as completed.

## Additional masking relative to main

Both main and working-tree projection functions were evaluated in memory against
the same complete live archive. The audit reported only entity ids, dates and
field names. It found no previously masked field restored on these inputs.

| Surface | Entity | Additional masking | Snapshot rows |
| --- | --- | --- | --- |
| Website | `e_RYZNSTS8RB1` | Name and slug | 7, 2026-09-26 through 2026-11-07 |
| Website | `e_YCSQMCVD2PT` | Name, slug, repository name and label | 5, 2026-10-10 through 2026-11-07 |
| HF | `e_RYZNSTS8RB1` | Name and slug | 7, 2026-09-26 through 2026-11-07 |

The four review fixes introduce no additional entity-projection differences on
this archive beyond those recorded for F1-1. They cover regressions in diagnostic
paths, template-word homepages, former project accounts and malformed input.

The expected published dist changes therefore remain the earlier record's set:
the two entities' `e/<id>/index.html` and `e/<id>.json`, their badge outputs,
`search-index.json`, `llms.txt`, unassigned-cohort JSON/CSV tables, and the seven
affected dated `snapshot.json` files. Any Card B exports, feeds or chart text
materializing the changed names must reflect the same mask. Names changing sort
position also change the snapshot, cohort and coverage pagination listed in the
earlier record's route/page table, including neighboring rows shifted between
pages. Scores and captured measurements do not change. The exact built file list
must be reconciled by the orchestrator's dist comparison.
