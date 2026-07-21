# DRAFT v2 — Data-sanity gate + evaluation state machine (NOT in force)

> status: DRAFT v2, 2026-07-21 — rewritten after a 7-model adversarial council
> review of DRAFT v1 (the council REJECTED v1's hand-set constants and drop-only
> direction; this v2 is the agreed replacement). Becomes operative only as part
> of the next dated superseding record.
> Trigger incident: 2026-06-11 / 2026-06-15 corrupt partitions (see
> AXIS3-DEPS-V2H-LIVE-LOG.md; retraction: eval/RETRACTION-2026-07-21.md).
> Reference implementation: `collectors/data_sanity_gate.py` (kill-bar PASS
> 2026-07-21: flags exactly the two challenge partitions, zero clean ones).

## Council verdict on DRAFT v1 (recorded honestly)

- Hand-set constants (30%/20/50%/80%/90%) — rejected: "optically fatal";
  unanswerable to a hostile reviewer.
- Drop-only detection — rejected as **positive-momentum laundering risk**: in a
  positive-only institute, a filter that preferentially excludes value dips is
  indistinguishable from deleting inconvenient declines. All shape rules must be
  direction-neutral (dip-and-recover AND spike-and-revert).
- "Physically impossible" language — rejected as overclaim: a panel-wide
  transition is evidence of source inconsistency, not proof of its cause.
  Quarantine language: "unfit for inference," never "proven corruption."
- Survivor-bias: entities that VANISH from a partition are a stronger signal
  than entities with collapsed values; coverage must be a first-class contract,
  not a footnote.

## The agreed design (two-stage gate + typed state machine)

**Evaluation state machine** (no criterion may be computed on non-eligible input):

```
captured → integrity-eligible → confirmed-clean → computable → PASS/FAIL
```

- A verdict computed on input later shown unfit is retagged INVALID_INPUT (not
  FAIL) by a dated retraction note; quarantined snapshots never count toward
  the live floor (>=4 means >=4 CONFIRMED-CLEAN snapshots).

**Stage 1 — hard contracts (fire immediately, single partition):**
- Coverage contract: `matched < 30` → INVALID_COVERAGE. The constant 30 is the
  PRE-EXISTING pre-registered promotion-criterion floor (PREREG c1), fixed
  2026-07-16 before the incident was known — zero post-incident numbers. Both
  incident partitions (22, 25) fail it.
- Row-count fingerprint (free, INFORMATION_SCHEMA): partition total_rows
  deviating >15% from the local (±10-partition) median → SUSPECT flag. Catches
  the truncated-partition class (which HAS occurred upstream: 2024-02..03 series
  at ratio 0.4, spikes 2-3x in 2023-11/2024-08). Note: the 2026-06 incident had
  NORMAL row counts (ratio 1.039) — this layer alone is insufficient, which is
  why panel-level rules are load-bearing.
- Identity-set: the matched-entity roster is diffed against the previous clean
  partition; disappearances are listed in the artifact (survivor-bias guard).

**Stage 2 — symmetric shape rules (need successor(s)):**
- Reversal rule: an eligible entity (pre-move value >= 5, the existing
  DEPS_FLOOR) counts as a reversal at partition p if |log(v_p/v_prev)| > bound
  AND it returns to within bound/2 of the pre-move level within the next
  RECOVERY_WINDOW=2 partitions (2 covers a consecutive corrupt pair — the
  actual incident shape — while staying too short to absorb a real regime
  change). Direction-neutral by construction.
- Panel threshold: partition p → SUSPECT_CORRUPT when reversal-share among
  eligible entities exceeds the calibrated threshold (>=10 eligible required).
- The LAST partition of a series is at most PROVISIONAL (shape rules need
  successors). Promotion/termination verdicts are computed ONLY on the
  confirmed-clean prefix (official cutoff = t−1); the newest point is published
  as UNCONFIRMED diagnostics.

**Threshold derivation (procedure pre-registered, constants computed):**
- Calibration corpus (frozen, declared): every clean transition in all of the
  institute's series — deps_v2 partitions minus the two DECLARED challenge
  partitions, t2 watchers + open_issues (137 systems, daily), terminated v1
  dependents (88). 71 clean transitions as of 2026-07-21.
- Bounds = max clean observation × declared safety margin (3×), floored at
  physical minimums (move bound never below 2×; panel threshold never below
  10% so one entity cannot quarantine a partition). Computed 2026-07-21:
  move bound 3.0× (max clean single move was exactly 3.0×), panel threshold
  0.214 (max clean big-move share 0.071 × 3).
- Plateau argument (stated, per council): the incident partitions sit at
  reversal-share 1.0 — nearly 5× above the threshold; any margin in [2, 10]
  separates them from clean history. The exact margin is policy, not a fit.
- The two known-bad partitions are CHALLENGE CASES: excluded from calibration,
  used only to verify firing. They cannot validate a detector designed after
  seeing them (challenge ≠ holdout); validation is the ZERO false positives on
  71 clean transitions across three independent series.
- **Kill-bar (pre-registered, verified PASS 2026-07-21):** the gate must flag
  exactly {2026-06-11, 2026-06-15} and zero clean partitions. Any other outcome
  = the rule is wrong, the superseding record must not be committed.

**Verdict-layer canary (council: the cheapest universal defense):**
- Alongside the primary estimator (slope of log1p), every evaluation computes
  the naive endpoint-sign fraction per cohort. Disagreement beyond a declared
  band forces HOLD — never an operator-authored explanation. (This check,
  performed manually, is what actually caught the incident.)

**Meta-monitor (Grok):** gate fire-rate tracked; a gate that suddenly fires
often or never is itself suspect.

**Blindness clarification (doctrinal):** blindness binds THRESHOLDS AND
VERDICTS (no tuning on seen data). It does NOT bind data sanitation. Raw-series
inspection after capture is mandatory hygiene, not peeking.

**Epistemic typing (journal/memory):** entries are typed
measured | derived | operator-hypothesis; a causal label about external data
without an attached machine artifact is not journalable; a later session may
not consume an operator-hypothesis as a premise without re-derivation.

## Restart plan (council: option B, 7/7)

One restart, one superseding record, with **dual rationale** (two independently
justified changes, each standing on its own):
1. Sanity gate + state machine (grounds: the incident + upstream's own history
   of unstable partitions).
2. Panel expansion across ecosystems — conda / HF-hub / Go / monorepo
   sub-packages (grounds: PRE-EXISTING structural under-power, independent of
   the incident: voting ceiling ≈24 < 30 after DEPS_FLOOR on the 41-pin panel;
   independence pairs confined to one dense cohort). Expansion manifest is
   VALUE-BLIND: pins selected by metadata/semantic eligibility rules frozen
   before any value-bearing query; no hand-picking against criteria.
   Cost note: expansion does NOT raise the per-partition read cost (the query
   scans the whole day-partition regardless of pin count, ~$3.45).

Clean-only restart (option A) was rejected 7/7 as a predetermined negative
("credibility theater" — the coverage criterion is structurally unreachable on
the 41-pin panel).

Baseline rule fix (gap found in synthesis): the new baseline = the 14 most
recent CONFIRMED-CLEAN partitions before the record (reaching deeper than 14
calendar-weekly partitions if corrupt ones fall in the window) — the old
"14 most recent" wording breaks when corrupt partitions land inside it.

## Addendum — 8th council voice (ChatGPT Pro, manual; 2026-07-21 later)

The manually-run Pro voice (same Prompt A, clean A/B vs the CLI voice) added
seven mechanisms adopted into this draft:

1. **Influence/fragility veto (one-way).** Alongside the registered primary
   estimator, compute leave-one-partition-out and a robust-slope comparator.
   If a single partition or the estimator choice materially flips a cohort
   conclusion → verdict `INDETERMINATE`. Strictly one-way: the comparator can
   never turn a failure into a promotion. Do NOT replace OLS itself now —
   post-incident estimator replacement would look outcome-restorative.
2. **Same-source calibration + negative controls.** Thresholds calibrate ONLY
   on deps_v2's own clean transitions (different sources have different anomaly
   distributions — pooling is illegitimate). The other institute series (t2
   watchers/issues, v1) are NEGATIVE-CONTROL falsification: the derived rule
   must fire zero times on them. *(Implemented 2026-07-21: same-source
   calibration over 11 clean transitions → move bound 2.0x floor, panel
   threshold 0.10 floor; negative control PASS — zero firings across 3 control
   series; kill-bar re-verified PASS.)*
3. **Coverage corroboration.** A coverage undershoot alone does not
   auto-quarantine: without independent evidence the source itself was unwell
   (identity-set diff vs neighbors, fingerprints, reversal signals nearby), a
   coverage failure is a SUBSTANTIVE miss — auto-excluding it would censor
   genuine metric unavailability. (For the incident partitions the
   corroboration exists: neighbors are 31/31 and the reversal rule fires.)
4. **Duplicate/stale-partition detection** (identical content under different
   SnapshotAt) in the deterministic layer.
5. **Mutation testing of the detector** (CI): inject synthetic dips, spikes,
   partial cohort loss, stale copies, gradual scaling, identity remaps,
   full-coverage unit shifts. The likely next failure is plausible partial
   corruption with full coverage — not another 99% panel-wide dip.
6. **Non-gating factorial audit at restart:** old panel + sanitation vs
   expanded panel + sanitation, published as diagnostics.
7. **Family-wise false-hold budget** declared from governance risk tolerance
   before calibration runs (not chosen by watching where the incident lands).

Language discipline (Pro, matching the CLI voice): the gate detects
**source-health anomalies** — never claim "physically impossible" or "proven
corruption."

## Expansion manifest — BUILT and frozen as DRAFT (2026-07-21)

`collectors/expansion_manifest.py` executed over all 137 tracked repos
(0 errors): 1264 packages declared in the systems' own repo trees, **614
deps.dev-eligible new candidates** (npm 329 · cargo 142 · pypi 135 · go 8),
raising panel coverage from 41 pinned repos to **80 systems with >= 1 pin**.
Manifest: `data/quarantine/axis3-deps-v2/expansion-manifest-DRAFT.json`,
sha256 `026eaa45377a5b39…`. No dependents value was read during selection.

**Dominance rule (per PREREG v2 semantics, restated):** the measured unit is
the SYSTEM, not the package — unique direct dependents are counted over the
UNION of all the system's eligible packages, dedup by (Dependent.System,
Dependent.Name), excluding intra-system dependents. A monorepo with 148
packages (mastra) is therefore ONE panel row, same as a single-package system;
package-count dominance cannot skew cohort statistics. Per-partition read cost
is unchanged (whole-partition scan regardless of predicate count).

## Open questions for the superseding record

- Sentinel control panel (non-ranked packages watched only for source health):
  adopt only if marginal cost is truly ~0 (same-partition reads) — verify.
- Annual re-idempotence spot-check (re-read one historical partition, compare
  observation sha256; ~$3.44/yr) — adopt as calendar ritual?
- Gate gaming analysis (can adversarial upstream noise force quarantines of
  honest signal?) — deferred to the next review cycle, documented as residual.
- Slow monotonic drift remains the known-uncovered class (no cheap automated
  defense); documented as residual risk per council.
