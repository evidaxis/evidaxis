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

## Style
- Comments explain WHY, in English, matching the density of the file you edit.
- Collectors and scripts/ are pure stdlib (no new deps). Web deps only in web/.
