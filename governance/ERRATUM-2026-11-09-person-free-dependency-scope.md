# Person-free dependency matching scope, 2026-11-09

This corrects the scope of the earlier dependency-token erratum. PR 36's
`benign_all` caught an organization path hidden by the revision 3 matcher.
Splitting every hyphenated word made a package-specific privacy rule affect
ordinary prose and repository names.

## Correction

General `handle_hits` / `handleHits` restore the exact pre-revision-3 word
expression and whole-word comparison. Internal hyphens stay inside the word.
Mentions, GitHub contexts, percent decoding and exact stale paths retain their
existing behavior. The shared classification and rules a-f are unchanged.

`dependency_handle_hits` / `dependencyHandleHits` keep the stronger matching
only for dependency values. Both use the classified handle index, preserve
internal login hyphens and require non-alphanumeric boundaries. Current and
former personal handles are covered. Organization and project accounts remain
public. Template words retain rule f's GitHub-context restriction; exact short
field values retain their mask.

The website and HF projections apply this matcher to every string value below
`deps`, including `system`, `package`, nested objects and arrays. Package labels
and the two Card B checks of dependency labels/source URLs use the same matcher.
An unrelated `package` field outside `deps` retains its earlier whole-word mask.
No name, slug, description, repository path or other prose receives dependency
token splitting merely because it contains hyphens.

The website and HF byte guards parse JSON and recursively select `deps` values
through `dependencyFieldHits` / `dependency_field_hits`. These findings use
`rule=g` with the existing salted diagnostic. General byte scanning still
applies to all text and artifact paths, including non-JSON input. It does not
split hyphenated prose. No identifier index is persisted.

All eight classifier consumers from review section 1.4 remain connected:

1. Python `load_handle_index`, HF projection and guard.
2. JS `personalOwnerHandles` and `personalStalePaths`.
3. `person_free.ts` website and archive projection.
4. `check-dist.mjs` byte and provenance checks.
5. `public_dropped.ts` repository/text maps.
6. `public_dropped.data.test.ts` archive assertions.
7. `person_index_build.py` adapters.
8. `fixture-privacy.mjs` anonymization inputs.

The single-source guard, classifier exceptions, frozen fixture, raw archive,
`etl/`, methodology, thresholds, schedules and canary semantics are unchanged.

## Verification

The common vectors now distinguish general prose from dependency tokens. They
pin a hyphenated public organization path whose repository name contains a
personal token. Both projections preserve that path, name, slug and homepage.
Current/former personal packages are masked, organization packages remain, and
template words require GitHub context. Projection tests cover nested strings,
arrays, `deps.system`, package labels, unrelated prose/package fields and input
immutability. HF tests inspect staged bytes; a real `check-dist` subprocess
checks dependency findings and absence of prose/path false positives.

The live project-account test restores the pre-revision-3 counts, 12 neutralized
names with project accounts and 22 without them. It explicitly checks that the
six formerly over-masked hyphenated names, slugs and repository names survive.
This follows the requested scope correction, without removing assertions.

- Required Python trio: 127 passed.
- Complete Python `tests/`: 7,599 passed, one skipped because the gitignored
  census working data is absent.
- JS conformance: 50 passed. Web unit suite: 417 passed in 34 files.
- Actual website guard data test: passed, including package/system/nested
  dependency leaks, salted diagnostics and harmless hyphenated prose.
- HF dry-run on 2026-11-07: 6,682 entities, 18 neutralized names, 3,028 redacted
  fields, zero guard findings. No upload.

## Projection audit and expected dist changes

An in-memory comparison uses the same live archive with local `main`
`0547b1a3c2478b2059fe5593ff3e00b45a48da7e` and this revision. It prints only
dates, entity ids and field names. Previously masked fields do not become
public on those inputs. Relative to main:

| Surface | Entity | Additional mask | Dates |
| --- | --- | --- | --- |
| Website and HF | `e_RYZNSTS8RB1` | Name and slug | Seven weekly snapshots, 2026-09-26 through 2026-11-07 |
| Website | `e_YCSQMCVD2PT` | Name, slug, repository name | Five weekly snapshots, 2026-10-10 through 2026-11-07 |

There are 12 changed website entity rows and seven changed HF rows. The extra
57 rows from revision 3's overly broad matcher are no longer expected. The
live archive adds no dependency-field differences; the shared synthetic
vectors cover the class-j package introduced by rehearsal.

Expected affected dist surfaces relative to main are the two entities'
`e/<id>/index.html` and `e/<id>.json`, dated `snapshot.json` for those seven
dates, `search-index.json`, `llms.txt`, and unassigned-cohort JSON/CSV exports.
Names also propagate to badge outputs, Card B exports, chart labels and feeds
where those systems are included. Snapshot/cohort/coverage pagination can move
neighboring rows when neutral names change alphabetical order. Dependency
fixtures affect their entity JSON, dated snapshots, rendered package labels
and dependency source links, without changing their names or repository paths.

The exact dist hash comparison, full `npm run verify` and PR `benign_all` replay
remain the orchestrator's acceptance work. This is a projection audit, not a
claim that those runs passed.
