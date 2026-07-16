# Supersession: m3-v2 → m3-v2h (frozen-panel baseline + live-gated promotion)

> status: FIXED 2026-07-16, committed BEFORE any value-bearing v2 query (blindness
> intact: as of this commit no unique-direct value has ever been read by the project).
> Supersedes the floor mechanics of `QUARANTINE-m3-deps-axis-v2-PREREG.md` (that file
> is NOT edited — this is a dated superseding record, drift-never-amends).
> Grounds: (a) post-commit discovery that upstream snapshots are ~WEEKLY (217 total,
> back to 2022-05-08), making the mechanically-carried daily floor "14 distinct
> snapshots" mean ~14 weeks — a calibration error, not a design intent; (b) a
> three-vendor adversarial spar round 2 (Codex gpt-5.6 xhigh · Grok 4.5 · MiniMax M3,
> all MODIFIED verdicts) on whether historical snapshots are admissible.
> The keeper may recall this record by a dated note until the first capture commit.

## Estimand (honest name — narrower than the PREREG's implicit claim)

The evaluation object is a **frozen-panel trajectory**: "the historical and forward
unique-direct-dependents series of the package set selected and linkage-verified as of
2026-07-16" — NOT a reconstruction of what a contemporaneous observer would have
measured (pins resolve through TODAY's identity graph; systems/packages had to survive
to 2026-07 to be in the panel). All published claims must carry this framing.
Residual survivorship beyond the frozen universe (renames, deletions, mid-history
linkage changes) is disclosed, not denied.

## Baseline series (backtest, non-gating)

- The starting series = exactly the **14 most recent distinct upstream `SnapshotAt`
  values strictly preceding this record's commit timestamp**. 14 is the one
  pre-registered temporal count (no new free parameter); this reproduces the state a
  pure-forward candidate would have at first eligibility.
- Sample = the frozen panel: `data/quarantine/axis3-deps-v2/frozen-sample-2026-07-16.json`
  (137 systems, 41 pins with linkage evidence — the 10 pins missing the evidence field
  were live re-verified 2026-07-16, 10/10 linked — plus content hashes of seeds,
  id_map, pin map, and the collector's query template). Later pin growth NEVER changes
  the baseline sample.
- Power of the baseline: it CAN terminate the candidate early (a construct failure
  visible in history kills v2h without waiting) and it seeds criteria trajectories.
  It CANNOT satisfy any promotion criterion by itself.
- Diagnostics reported alongside (labeled `diagnostic/backtest, non-gating`):
  rolling-14 replay over the full 217-snapshot history; era strata (pre-2023 /
  2023-2024 / 2025+) for criteria 2 and 4; historical flip-rate distribution.

## Promotion gate (live-only)

Promotion may be proposed ONLY when ALL hold:

1. **>= 4 NEW distinct upstream `SnapshotAt`** captured after this record, through the
   real capture path (`collectors/t2_deps_package_collect.py`).
2. **>= 28 calendar days** of live quarantine from the first capture commit
   (ADJUDICATION-2026-07-11 §6b unchanged).
3. Criteria **#1, #2, #4, #5, #6 PASS at EVERY live cutoff** (each new snapshot is a
   cutoff; evaluation uses baseline+live series up to that cutoff).
4. Criterion **#3 (flip-rate) PASSES on all >= 3 fully-forward transitions**
   (S1→S2, S2→S3, S3→S4), computed per the formula below.
5. The promotion artifact separates four sections: frozen backtest · historical
   diagnostics · forward holdout · operational integrity. Collapsed columns = reject.

## Flip-rate and eligibility churn (fixed formulas)

For consecutive distinct snapshots j-1, j: let `E_j` = vote-eligible entities,
`R_j ⊆ E_j` = rising entities.

- `flip_j = |R_j Δ R_{j-1}| / |E_j ∪ E_{j-1}|` (symmetric difference; entities
  entering/leaving eligibility stay in the denominator).
- `churn_j = |E_j Δ E_{j-1}| / |E_j ∪ E_{j-1}|` — reported alongside, informative.
- A schema/fetch failure at either endpoint INVALIDATES the transition (never coded as
  "not rising"). If the denominator is too small the criterion is `UNEVALUABLE`,
  never an automatic PASS.

## Zero vs absent (fixed)

`not_in_snapshot` is never a zero. A zero value is admissible only when the package's
existence is confirmed in the SAME `SnapshotAt`. Before a package's first confirmed
existence, the entity has NO observation point.

## Change discipline

Any change to the query, identity rules, or scoring logic after the first baseline
evaluation output = a NEW superseding record AND a restart of the live floor (items
1-2 above). No post-result identity repairs.

*Named and rejected (round-2 spar): (i) my own hybrid v1 — history satisfying
criteria 1/2/4 directly — rejected as the adaptive shortcut the PREREG itself forbids;
(ii) pure-forward-only (~14 weeks) — rejected because the baseline is deterministic
over immutable third-party data, the protocol structure predates any value being seen,
and the live gate above retains full promotion authority. Positive-only note: internal
methodology governance; no negative signal about any measured system.*
