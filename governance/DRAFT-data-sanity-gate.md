# DRAFT — Data-sanity gate for external data seams (NOT in force)

> status: DRAFT 2026-07-21 — spar material for the next superseding record.
> NOT operative until adversarially reviewed and committed as a dated record.
> Trigger incident: the 2026-06-11 / 2026-06-15 deps.dev partitions (see
> AXIS3-DEPS-V2H-LIVE-LOG.md, data-integrity finding 2026-07-21).

## Problem class

Every integrity mechanism in this repo defends against OUR OWN dishonesty
(pre-registration, blindness, frozen panels, content-addressed artifacts,
look-ahead guards). Nothing defended against UPSTREAM data corruption. A
mechanical evaluator amplifies bad input into confident false verdicts — twice
(baseline 2026-07-16, cutoff-1 2026-07-21) an artifact of two partial upstream
partitions was recorded as "panel-wide decline" without a raw-data look.

## Proposed rule (to be fixed on principle, then validated — never tuned)

A snapshot/partition is quarantined as `suspect_corrupt` when EITHER:

1. **Physically-impossible transition**: for >= K% of matched entities with
   prior value >= V_min, the value drops by more than D% at this snapshot AND
   recovers to more than R% of the pre-drop value at the next snapshot.
   (Straw-man numbers for the spar: K=30%, V_min=20, D=50%, R=80%. The rule
   fires on a PANEL-WIDE dip-and-recover — a single entity collapsing is a
   legitimate observation; half the panel collapsing and recovering is not.)
2. **Coverage collapse**: matched-entity count < M% of the series median
   (straw-man: M=90%; the incident partitions were 22 and 25 vs a median of 31).

Quarantined partitions: excluded from slope/z/criteria computation; retained in
the archive verbatim (never deleted — retraction-by-tag, not erasure); listed in
every evaluation artifact under `excluded_partitions` with the firing rule.
The LAST point of a series can only be `provisionally_clean` (rule 1 needs a
successor point) — verdicts at such a cutoff must carry that caveat.

## Blindness clarification (doctrinal, needs the spar's eyes)

Blindness discipline binds THRESHOLDS AND VERDICTS (no tuning on seen data).
It does NOT bind data sanitation. Raw-series inspection (sparkline/dump after
every capture) is mandatory hygiene, not peeking. Conflating the two is what
let two corrupt partitions poison two evaluation rounds.

## Open questions for the spar

- Are K/V_min/D/R/M defensible a priori, or tuned to the known-bad partitions?
  (They were written after seeing 06-11/06-15 — the spar must attack this.)
- Should rule 1 require BOTH panel-wide dip-and-recover AND coverage drop, or
  is either alone sufficient?
- Retroactivity: applying the gate to the existing baseline restarts the live
  floor per change-discipline. Bundle with panel expansion or run clean-only?
- Does the gate itself need a gaming analysis (can upstream manipulation of
  one partition force us to discard an honest signal)?
