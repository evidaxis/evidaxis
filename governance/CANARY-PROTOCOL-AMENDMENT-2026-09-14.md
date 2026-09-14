# Canary protocol amendment — metric change and clock reset at the first m3 render (2026-09-14)

> status: FIXED 2026-09-14, before the first m3 snapshot (2026-09-19) and before any
> post-reset observation exists. Applies to the matched-pair display canary launched
> 2026-08-20 (`web/src/data/canary-assignment.json`, 24 pairs; guard
> `web/scripts/check-dist.mjs`). Pair assignment and shell semantics are unchanged
> (AGENTS.md canary rule).

## Why

1. **The registered primary metric cannot converge.** Non-brand CTR (treatment ≥ 0.5 %
   against control by 2026-10-02) needs clicks; the whole site recorded 4 clicks per
   2,254 impressions in 90 days, and the first readout (2026-08-29) found 0 clicks in
   both arms after 9 days. This follows from the site's baseline alone, without looking
   at the experiment's outcome. That readout already recommended a dated metric change
   with a clock reset; it was never filed.
2. **Methodology m3 changes every entity page** from the first m3 snapshot (third axis
   row, axis count, JSON-LD). Keeping the old window would put pre-change and
   post-change pages inside one comparison.

## Amendment

- **Primary metric:** per pair, the difference between arms of weekly Google Search
  Console impressions, each page normalised by its own mean weekly impressions over the
  baseline window. Analysed per pair, never by arm.
- **Analytic set:** pairs in which both pages averaged at least one impression per week
  over the baseline window. The rule is fixed here; the list is computed by code at the
  reset and committed. The remaining pairs stay live and are reported as non-analytic.
- **Baseline window:** 2026-08-20 to the day before the clock start. Data from that
  window is baseline only, never outcome.
- **Clock start:** the first production deploy that renders the 2026-09-19 m3 snapshot.
  From that moment both arms are served by the same site version.
- **Verdict:** six weeks after the clock start. Scaling the treatment beyond the 24 pairs
  waits for this verdict.
- **Control baseline:** regenerated for the m3 render in the commit that ships m3
  rendering, keyed by methodology version; the m2 hashes are retained.
- **Unchanged:** pair assignment, treatment content, control title, isolation of controls
  from treatment-only blocks.
- **Secondary, reported but not gating:** non-brand CTR as originally registered.

*Named and rejected: (i) holding the 48 canary entity pages on the m2 rendering until
2026-10-02: those pages would show a different method from the rest of the site and
from the published snapshot, and a CTR verdict on 2026-10-02 would carry no information;
(ii) keeping the original clock across the m3 change: a pre/post mixture inside one
comparison. Positive-only note: internal methodology governance; no negative signal about
any measured system.*
