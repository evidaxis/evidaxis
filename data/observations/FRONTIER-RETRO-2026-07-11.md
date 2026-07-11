# Frontier retro-note — the 19→103→137 expansions ran without a denominator

> created: 2026-07-11 · reconstructable: false · status: honest record of a permanent gap

## What is missing and why it matters

SCALE-PLAN.md:35 required "Freeze universe.md v0 BEFORE any ingest >19". The expansions
of 2026-07-01 (19→81→108) and the subsequent batches to 137 ran WITHOUT a discovery
manifest: no candidates_returned / examined / admitted / excluded counts, no source
queries or cursors were recorded. That denominator is un-backfillable: the discovery
frontier of those dates no longer exists anywhere.

## Consequence (stated plainly, forever)

Any future back-test or foresight claim over cohort composition must treat the
2026-06-27 → 2026-07-10 accession window as **selection-opaque**: we know WHO was
admitted, not who was seen and passed over. Survivorship analyses over this window
carry an unquantifiable admission bias.

## What is known (prose reconstruction, not a manifest)

Sources used across those batches (per UNIVERSE-FINDINGS.md and session records):
GitHub topic/star searches per cohort, curated ecosystem lists, HF trending, prior
seeds. Admission judgment was manual-curatorial against cohort definitions. No
numerical funnel survives.

## Closure

collectors/frontier_manifest.py + the archive-integrity CI rule (seeds.json diff
requires a paired manifest) are live since 2026-07-03: **every expansion from now on
records its denominator**. The gap is bounded to the window above and documented here;
this note is the permanent tombstone of the missing frontier.
