# Template B change during the observation window: README badge link (2026-09-24)

> status: FIXED 2026-09-24, recorded before the change reaches production.
> Relates to: FOUNDATION-RETROFIT-CARDS-PREREG-2026-09-23.md and its addendum.
> Run: second-brain `lab/team-log/work/2026-09-24-team-155-evidaxis-badge/` (decisions in `05_ledger.md`).

## What changes

- Arm B cards: the Rising-only button "Copy Rising badge" and the Rising-only badge image
  are replaced by one text link "README badge" to `/badge/{entity_id}/`, shown when the
  system has at least one badge to offer. Nothing else in template B changes.
- New pages `/badge/{entity_id}/` (badge builder, all systems, both arms): `noindex`,
  outside the sitemap.
- New stable badge files per system: `citations`, `dependents`, `rising` (three styles
  each), `rising-card`, and shields endpoint JSON. The dated badge URLs
  `/badge/{entity_id}/{period}.svg` keep their output unchanged.

## What does not change

- Arm A output and the 48 headline-experiment shells: byte-identical (checked in a clean
  build before deploy).
- Assignment, baseline, outcome definitions, strata and readings of the pre-registration.

## Effect on the reading

- The change sits below the first screen of template B, in the actions area. The
  pre-registration already says a verdict may not claim the effect of any single block.
- Descriptive event `fnd_cite_copy` no longer includes Rising badge copies. Before this
  change such copies could only come from the two Rising systems in arm B. Badge copies
  are now `fnd_badge_copy` on the builder page, and opening it from a card is
  `fnd_badge_open`. Both are new descriptive events, not outcomes.
- Readers of T+7 and T+30 treat 2026-09-24 as a dated change inside the window.
