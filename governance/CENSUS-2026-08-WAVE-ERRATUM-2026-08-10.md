# Erratum: the 2026-08 stock census was published with the wrong queue

> status: **CORRECTED** — issued 2026-08-10, applies to `data/census/2026-08/`
> Policy: governance/REGISTRY-GROWTH-POLICY-2026-07-21.md
> Predicate: governance/CENSUS-AI-V1-PREDICATE-2026-08-03.md
> Result record: governance/CENSUS-2026-08-RESULT.md (unaffected: no admission changed)

## What was wrong

Every one of the 5,523 members admitted by the first census carried
`wave: "forward"`. They are the stock enumeration of the pre-existing universe,
so all of them are `backlog`, and that is what the census emitted at 14:46 UTC
on 2026-08-03: 5,522 members stamped `backlog`, which is the state the first
activation tranche recorded an hour later and the state its published artifact
still shows.

A re-emit at 19:24 UTC the same day, run for an unrelated scope fix, rewrote the
stamp. `finalize_census_run()` took stock intent from a command-line flag and
wrote the resulting wave over every member; the re-run omitted the flag, so the
default silently re-filed the entire stock census as `forward`.

Nothing failed. No test covered the field, no gate compared the manifest against
the tranche that had already been published from it, and the institute's own
result page continued to describe a two-queue policy the manifest no longer
implemented.

## Why it mattered

The two queues exist so that a repository crossing 500 stars in September is
activated before the stock backlog rather than behind it: "forward crossings
take priority so new coverage debt never accumulates". The weekly tranche reads
`wave` to build them.

With the whole stock wearing the `forward` label, September's genuine crossings
would have been merged into a pool of 5,513 stock members and sorted by stars.
A fresh 501-star crossing would have queued behind thousands of older, larger
systems, and the priority rule would have been inverted in production for as
long as the backlog took to drain. The August tranches are unaffected: with one
label on the whole population the ordering within it is identical either way,
which is precisely why the defect was invisible on the only runs that had
happened when it was introduced.

An adversarial review had already found this inversion by a different route on
2026-08-03 (finding #15) and the fix shipped in the tranche selector. The
re-emit reopened it in the data instead of the code.

## What was corrected

In `data/census/2026-08/`:

| artifact | field | published | corrected |
|---|---|---|---|
| `pending-manifest.json` | `wave` (all 5,523 members) | `forward` | `backlog` |
| `pending-manifest.json` | `wave` (run level) | `forward` | `backlog` |
| `pending-manifest.json` | `stock_census` | `false` | `true` |
| `census-run.json` | `stock_census` | `false` | `true` |
| `census-run.json` | `activation_wave` | `forward` | `backlog` |

Hashes before the correction, so the superseded bytes stay identifiable:

- `pending-manifest.json` — `80000493a27c6b17840704c2bcb08332145b9c4e5b9c32432a227be20ed4a44e`
- `census-run.json` — `08076087ea63ec6e2435ed1e51d5b92d1b7ddafaa7d62ce6825655117d22dc56`

After the correction:

- `pending-manifest.json` — `3821ea368192c5ccff943c41ebc1f6e7a1d1019f55b55c23453bc314ae4e9497`
- `census-run.json` — `484c2a124831cef80793c6776393b6fda173c0b9e830b5025b407c31a843d528`

**No admission, exclusion, count, or activation changed.** Membership is exactly
as published on 2026-08-03: 5,523 admitted, of which ten are activated. This
erratum touches queue placement only, and the git history holds both states.

## What prevents the recurrence

1. **Stock intent is derived, not typed.** `is_stock_census()` reads it off the
   archive: the stock census is the earliest census month the registry holds.
   The `--stock-census` flag is refused outright rather than left as a no-op,
   because its absence, not its presence, is what published the wrong queue.
2. **A published placement is sticky.** `previous_wave()` carries each member's
   first stamp across every re-emit, the sibling of the `previous_activation()`
   guard written the same day for the same class of defect: emit() regenerates
   the manifest, and whatever regeneration does not carry forward is rewritten
   in silence.
3. **`finalize_census_run()` may only fill blanks.** It records run-level intent
   and fills a missing wave; it can no longer overwrite one.
4. **Tests hold all four claims** (`tests/test_census_ai_v1.py`), including a
   later census deriving `forward` with nobody saying so, and a carried
   `backlog` member surviving a forward census.

## The pattern worth naming

Both defects of 2026-08-03 have the same shape: a regenerating emitter, a field
it does not carry forward, and no sensor comparing the regenerated artifact
against what was already published from it. The activation guard was written
for `status`. Nobody asked what else the same re-emit rewrites. The general
remedy is not another field-specific guard but the question itself — asked of
every field the emitter writes — and, where the cost is low, a check that
compares a re-emitted manifest against the tranches already drawn from it.
