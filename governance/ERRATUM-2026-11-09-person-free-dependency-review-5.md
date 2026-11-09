# Person-free dependency encoding and fixture hygiene, 2026-11-09

This corrects both findings in review `codex-20261109T203337-64fc` against
revision 4 (`db00ffb0f3`). It supplements the
[dependency scope erratum](ERRATUM-2026-11-09-person-free-dependency-scope.md).

## Correction

`dependency_handle_hits` and `dependencyHandleHits` now split dependency
tokens in both raw and percent-decoded strings. Decoding can erase a boundary:
the fictional package `widget-zz-drill-person%61` becomes a word ending in
`persona`. The raw spelling must still match the indexed personal handle.
Both representations use the same classified index and rule f exceptions.
Existing decoded matches remain; the change only adds raw dependency matches.

The website mask, HF projection, both JSON byte guards, package labels and
Card B dependency source links already call these shared matchers. They all
receive the correction without a new classification rule at their call sites.
General prose, names, slugs and repository paths retain whole-word matching,
including internal hyphens. The eight classifier consumers listed in the
scope erratum retain their shared classification paths.

`fixtureAnonymizer` carries dependency context through objects and arrays.
Strings under `deps` with a shared matcher finding receive a deterministic
synthetic replacement, reusing existing locator replacements when available.
These additional replacements stay local to dependency fields so identical
organization prose and repository paths remain public. The returned callback
does not accept an array index as dependency context when used with `map`.

Fixture hygiene parses JSON and each JSONL row, then calls
`dependencyFieldHits`. Its general text and path scan remains in place.
The synthetic JSON/JSONL regressions exercise the same scanning helper as
the real fixture scan. The existing frozen fixture passes the stronger
hygiene check and does not require regeneration.

## Regression evidence

Tests were added and run before implementation changes:

- Python conformance: five failures covering raw encoded package/system
  projection and the real HF byte guard.
- JS conformance, fixture anonymization and Card B: 17 failures, 81 passes.
- Synthetic fixture hygiene: both JSON and JSONL cases failed.
- Actual `check-dist` subprocess: failed the new raw encoded package assertion.

With the correction:

- Required Python trio: 131 passed.
- Complete Python suite: 7,603 passed; one census test skipped because its
  gitignored working data is absent.
- JS conformance: 53 passed; fixture anonymization: 22 passed.
- Complete web unit suite: 441 passed in 34 files.
- Complete fixture hygiene: four passed.
- Actual website guard probation test: passed, including encoded dependency
  findings, salted diagnostics and public prose/path preservation.
- HF dry-run on 2026-11-07: 6,682 entities, 18 neutralized names, 3,028
  redacted fields, zero guard findings. No upload.

Five deliberate mutations were rejected: an incorrect vector expectation
(both languages), an owner-type decision in `hubs.ts` (single-source guard),
current-owner-only publication indexes (both languages), treating a live
organization as personal (both languages), and removing dependency masking
(both projections). All mutated files were restored byte-for-byte.

## Publication scope

Relative to revision 4, only dependency strings whose raw spelling reveals a
personal token gain a publication mask. This includes nested `deps` values,
`deps.system`, package labels and Card B dependency source links. It can affect
`e/<id>.json`, dated `snapshots/<date>/snapshot.json`, package labels and source
links in `e/<id>/index.html`, and any export using those dependency values.
Fixture anonymization and hygiene are development-only surfaces.

The prior main comparison in the scope erratum remains the baseline forecast:
additional name/slug masking for `e_RYZNSTS8RB1` and additional name/slug/repo
name masking for `e_YCSQMCVD2PT`, propagated to entity pages, snapshots, search,
cohort exports and feeds. This revision does not alter those rules or narrow
their masks. No new dist hash comparison is claimed here.

Full `npm run verify`, dist comparison and PR candidate rehearsal remain the
orchestrator's acceptance checks. The local mutation tests do not replace
the independent rehearsal oracle. No methodology, threshold, timeout,
schedule, canary assignment or frozen input was changed.
