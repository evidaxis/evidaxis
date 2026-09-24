# Template B change during the observation window: medals and citation wording (2026-09-24)

> status: FIXED 2026-09-24, recorded before the change reaches production.
> Relates to: FOUNDATION-RETROFIT-CARDS-PREREG-2026-09-23.md, its addendum, and
> TEMPLATE-B-CHANGE-2026-09-24-readme-badge-link.md.
> Run: second-brain `lab/team-log/work/2026-09-24-team-160-evidaxis-medals/` (decisions in `05_ledger.md`).

## What changes

- Arm B cards, a factual correction: the citation total was described as covering
  completed calendar years, but it includes the current partial year (vLLM: 776 of
  1,547 citing works are from 2026). The tile, the readings table, the yearly table
  total row and two facet sentences now say "indexed to date, including the current
  year". The per-year chart still shows completed years only. No number changes.
- Badge files and builder pages (not cards): a niche medal (bronze from 2x, silver from
  10x, gold from 100x the niche median shown on card B; niche of at least 5 systems with
  a reading and a median of at least 3), a growth badge for the last closed year, Rising
  as a live status or a month-range award without "since", and a builder that shows one
  main badge plus at most two optional ones. A comparison below 1x is never rendered.
- Dependents badges use only packages with a verified identity pin; 31 of 65 systems
  with a dependents reading have none (example: an unrelated npm package named
  `builtin` gives one system 124,656 dependents). The cards themselves are unchanged
  here; the axis is a separate open issue.

## What does not change

- Arm A output and the 48 headline-experiment shells: byte-identical (clean build
  compared before deploy). Dated badge URLs unchanged.
- Assignment, baseline, outcome definitions, strata and readings of the pre-registration.

## Effect on the reading

- The wording correction sits in the citations tile and section of template B; it is a
  factual fix, not a design variant. Readers of T+7 and T+30 treat 2026-09-24 as a dated
  change inside the window, as with the earlier badge-link change.
