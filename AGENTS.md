# Evidaxis — build/test facts for delegated agents

## Commands
- Python: `PYTHONPATH=. .venv/bin/pytest tests/` (CI mirrors with requirements-dev.txt).
- Web: `cd web && npm run verify` = vitest run + astro build + astro check + `node scripts/check-dist.mjs` against dist/.
- Prod sensors are dependency-free Node: `node --test scripts/*.test.mjs`.

## Hard rules (CI fails loudly on each)
- NO em-dash (U+2014) anywhere in rendered HTML.
- `etl/` is FROZEN - never edit anything under it.
- `governance/` records are dated and immutable - new dated files only, never rewrite.
- Methodology freeze until the AXIS3 verdict: no methodology/threshold/axis changes
  (correctness defects go via dated errata; see METHODOLOGY-FREEZE-2026-08-20).
- Canary experiment: `web/src/data/canary-*.json` + the control-shell check in
  `web/scripts/check-dist.mjs`. Do not alter canary assignment or shell semantics.
- Entity-adjacent language: no verdict-class strings near system names
  (enforced by entity-lexicon guard in check-dist).

## Person-free (invariant 1)
- Never write by hand a repository address, URL or package name of a personal account
  into a tracked file, commit message, issue or pull request; use the entity id or
  `gh:<repo_id>`. Automated data commits keep their format until the switch set by
  `governance/AMENDMENT-PROPOSAL-2026-10-19-invariant-1.md`; from then privacy-gate fails
  on any new published byte that contains one. No store of such identifiers is kept:
  collectors resolve them from public ids within a run and keep nothing afterwards.
- Install the local commit hooks with `git config core.hooksPath scripts/hooks`.

## Tests
- A web unit test (`web/src/**/*.test.ts`) pins concrete values to the frozen fixture `web/test-fixtures/2026-10-17`; the unit harness refuses live `data/` and `etl/`. A check over the whole live archive is a data test (`*.data.test.ts`) that states an invariant for every system. Four Saturday releases broke when unit tests read the newest data.
- Regenerate the fixture only on purpose, with `node web/scripts/make-test-fixture.mjs`: byte-identical on rerun, personal-account identifiers replaced.

## Style
- Comments explain WHY, in English, matching the density of the file you edit.
- Collectors and scripts/ are pure stdlib (no new deps). Web deps only in web/.
