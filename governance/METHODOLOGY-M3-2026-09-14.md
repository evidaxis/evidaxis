# Methodology m3 — a third scored axis (deps.dev direct-dependents momentum), effective 2026-09-19

> status: FIXED 2026-09-14. The implementation record required by
> `AXIS3-DEPS-V2H2-VERDICT-2026-09-14.md` §1 ("the axis enters scoring only through a
> separate dated forward record"); its commit closes the keeper's recall window on that
> verdict. m1 and m2 rows, pages and snapshots are unchanged and nothing is recomputed.
> Design reviewed by a five-engine council with an independent first round, arbitrated by
> the conductor; implementation reviewed by other engines than its writer. Minority
> positions are named in §10.

## 1. What m3 is

- **Axes:** development velocity (GitHub commits) · citation momentum (OpenAlex) ·
  **direct-dependents momentum (deps.dev)**. Axes 1 and 2 are computed exactly as under m2.
- **Gate (form unchanged):** Rising = not incumbent ∧ cohort ≥ 5 ∧ at least two axes
  present ∧ at least two axes rising. No threshold changed.
- **Axis 3:** unique direct dependents over the union of each frozen-panel system's
  linkage-verified packages (deps.dev BigQuery `Dependents`, weekly partitions,
  intra-panel self-dependents excluded); OLS slope of log(1 + dependents) over
  confirmed-clean points; slope residualized on log(1 + latest dependents), then robust z
  within cohort; a vote needs ≥ 14 confirmed-clean points and ≥ 5 latest dependents; rising
  needs slope > 0 and z ≥ 1; a one-way fragility veto withholds a rising vote; a cohort whose
  slope-sign vs endpoint agreement is below 0.80 (n ≥ 3) is held. The math is the frozen
  v2h.1 evaluator (`collectors/evaluate_axis3_v2h1.py`); its added capture-time filter is
  inert for historical calls (the committed 2026-08-17 and 2026-08-31 artifacts reproduce
  byte-identically).
- **Cohort for axis-3 z:** the cohort of the snapshot being scored (after taxonomy v2), so
  all three axes and the gate use one cohort label per system.
- **Momentum, percentile, confidence, status:** the m2 formulas over the axes present.
  Invariant test: with axis 3 absent for every system, all 199 committed 2026-09-12 records
  are reproduced exactly.

## 2. Identity

- Registry row `m3`: `formula_fingerprint` =
  `sha256:1aaae89952f8cea163e22caf25c17668a4d13ec8f60699e0b85bd3841d60d324` (canonical
  serialization of `methodology/m3.json`, `collectors/methodology_fingerprint.py`, pinned by
  a test); `code_commit` = `128df50bf1f6466d06f3df1fa2fdd825d774b42d`; `effective_at` 2026-09-19; `parent_version` m2; page
  `/methodology/m3/`.
- m1 and m2 fingerprints are not recomputable from code in the repository; they are
  disclosed as such, not reconstructed.
- The served registry presents each row's status relative to the latest published snapshot
  (`current` / `scheduled` / stored), so m3 reads as scheduled until the first m3 snapshot.

## 3. Verdict §4 obligations, closed

1. **Panel:** the frozen 90 systems / 628 packages
   (`ERRATUM-2026-09-14-v2h1-collector-panel-drift.md`). Re-freezing an expanded panel is
   not part of m3.
2. **Canary floor** (`collectors/axis3_canary_floor.py`, rule-first):
   `coding-agents: p = 0.909, n = 11` →
   `0.909 − sqrt(0.909 × 0.091 / 11) = 0.909 − 0.086717409 = 0.822282591` ≥ 0.80 →
   **0.80 confirmed and frozen**. Contamination disclosed: the live agreements
   (0.929–0.941) had been seen; the rule tests the pre-live baseline and can only confirm or
   escalate, never tune the floor upward.
3. **Forward accounting by code** (`collectors/axis3_forward_count.py --record
   governance/AXIS3-DEPS-V2H2-SUPERSESSION-2026-08-18.md --as-of <verdict commit time>`):
   record first added 2026-08-18T09:21:29+02:00 (`b69bbf28`); forward CLEAN partitions
   **2026-08-17, 2026-08-24, 2026-08-31 = 3**; 2026-08-10 captured before the record
   (`eb918a11`, 09:10:26); 2026-09-07 provisional. A test pins this table at the verdict's
   commit time, so later captures cannot change it.
4. **Estimand honesty:** the estimand sentence, the history-origin note (with each record's
   `points_reconstructable`) and the attribution appear on `/methodology/m3/`, on every
   entity page where axis 3 is scored, in JSON-LD, and in the entity cards.
5. **Entity-adjacent language:** check-dist lexicon guard green on both an m2 build and an
   m3 dry-run build.

## 4. Timing and look-ahead

A snapshot uses the newest partition that is (a) dated on or before the snapshot date,
(b) classified CLEAN by a sanity-check artifact committed before the snapshot's capture
time, and (c) backed by observation rows captured before that time. Provisional
partitions are never scored. Each record carries `as_of_partition`. An axis whose cutoff is
more than 28 days older than the snapshot is `stale` and not scored. Expected lag: about
two to three weeks (2026-09-19 will use 2026-08-31).

## 5. Coverage states

`scored` · `below_floor` · `held` · `stale` · `out_of_panel`. Only `scored` counts toward the
gate; no state is ever rendered as zero.

## 6. Rights

Dated append to `RIGHTS-BASIS.md` (2026-09-14): the licence is CC-BY 4.0 and does not
restrict historical partitions; point-in-time files remain the live captures; reconstructed
history stays in the shadow-backfill namespace; the score may use both origins and each
record reports `points_reconstructable`. Closes the pre-registered checkbox "BigQuery
history bridge".

## 7. Cross-correlation monitor

Every m3 snapshot publishes `diagnostics.axis_correlations`: pooled within-cohort Pearson
(cohorts with n ≥ 5) for the pairs 3-1, 3-2 and 1-2, with pair counts and per-cohort values.
Published from the first m3 snapshot, not earlier. Closes the pre-registered checkbox
"cross-correlation monitor". Bound: |r| < 0.5.

## 8. Canary experiment

`CANARY-PROTOCOL-AMENDMENT-2026-09-14.md`: primary metric changed to the paired
impressions ratio, clock reset at the first m3 render, verdict six weeks later; the
control-shell baseline is keyed by methodology version (all 24 m2 hashes preserved; m3
hashes generated from a dry-run build whose shells differ from m2 only in the
methodology-version text).

## 9. Activation, first snapshot, first Rising

- The scoring step is a no-op before 2026-09-19 (exit 0, files untouched), so a manual weekly
  run cannot fail an m2 publication; from 2026-09-19 it runs between the redirect restore
  and the content-addressed snapshot id; `score_m3.py --verify` runs in archive integrity.
- First m3 snapshot: the weekly run of 2026-09-19.
- If that snapshot contains Rising systems, a dated disclosure record lists each riser's
  evidence (points, reconstructed points, latest dependents, slope, z, veto checks,
  dependent-ecosystem composition) at the next weekly tact (2026-09-21).

## 10. Council and named-and-rejected

- **Canary pages held on m2 until 2026-10-02** (three voices): rejected; it would publish
  entity pages on a different method from the rest of the site and from the snapshot, and
  the registered CTR metric could not converge. Replaced by the protocol amendment (§8).
- **Canary floor = baseline minimum (0.909) or 0.85:** rejected as fitted to seen data.
- **Percentile stratified by number of axes; baseline points retired at 14 live points;
  richer monitor tripwires:** queued for a future version, not in m3.
- **Removing the daily REST dependents count from pages:** rejected; kept and labelled
  "Daily dependents count (unscored)".
- **An anti-gaming gate before the first Rising:** rejected as a gate added at bind time;
  replaced by disclosure (§3.4, §9) and a methodology note that dependents can be inflated
  by packages outside the panel.

## 11. Diagnostic dry run (never published as a score)

The 2026-09-12 inputs scored as m3 in a temporary directory (the published 2026-09-12
snapshot stays m2): cutoff 2026-08-24 (2026-08-31 was confirmed only on 2026-09-14);
axis-3 states scored 47 · below_floor 42 · out_of_panel 110 · held 0 · stale 0; 8 positive
axis-3 votes; 2 systems would be Rising, both on development plus direct dependents, each
with 21 clean points of which 15 reconstructed; pooled within-cohort r(axis 3, axis 1) =
0.071 over 39 pairs. Recorded to show the size of the change before activation.

*Positive-only note: internal methodology governance; no negative signal about any measured
system.*
