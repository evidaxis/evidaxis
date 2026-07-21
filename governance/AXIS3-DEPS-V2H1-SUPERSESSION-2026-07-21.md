# Supersession: m3-v2h → m3-v2h.1 (data-sanity contract + expanded frozen panel)

> status: FIXED 2026-07-21, committed BEFORE any value-bearing v2h.1 query.
> Supersedes the live-floor mechanics of
> `AXIS3-DEPS-V2-HYBRID-SUPERSESSION-2026-07-16.md` (not edited — dated
> superseding record, drift-never-amends).
> Grounds: (a) the 2026-06-11/15 corrupt-partition incident
> (`AXIS3-DEPS-V2H-LIVE-LOG.md`; both prior evaluations retracted as
> INVALID_INPUT — `data/quarantine/axis3-deps-v2/eval/RETRACTION-2026-07-21.md`);
> (b) an 8-voice adversarial council review (7-model consilium + a manually-run
> ChatGPT Pro voice) whose full verdict is incorporated via
> `DRAFT-data-sanity-gate.md` v2 (that draft's mechanics become OPERATIVE with
> this record); (c) pre-existing structural under-power of the 41-pin panel
> (clean voting ceiling ≈24 < the pre-registered coverage floor 30) —
> independent of the incident (dual rationale; the expansion is a repair of a
> defective pre-registration, not outcome-shopping).
> The keeper may recall this record by a dated note until the first v2h.1
> capture commit.

## Operative components (all implemented and committed before this record)

1. **Data-sanity gate** — `collectors/data_sanity_gate.py`.
   Two-stage, direction-neutral (dip-and-recover AND spike-and-revert;
   drop-only rejected as positive-momentum laundering). Stage-1 hard
   contracts: matched < 30 (the PRE-EXISTING pre-registered c1 floor — zero
   post-incident constants) → INVALID_COVERAGE; row-count fingerprint
   (free INFORMATION_SCHEMA sentinel) → SUSPECT. Stage-2 shape rule with
   RECOVERY_WINDOW=2 (consecutive corrupt pairs). Thresholds derived by a
   frozen procedure from SAME-SOURCE clean history only (11 clean deps_v2
   transitions; floors 2.0x move / 0.10 panel share); the institute's other
   series are NEGATIVE CONTROLS (zero firings verified), never pooled.
   The two incident partitions are the DISCOVERY/CHALLENGE SET — the detector
   is not claimed to have independently validated them (challenge ≠ holdout).
   **Kill-bar (pre-registered, PASS 2026-07-21):** flags exactly
   {2026-06-11, 2026-06-15}, zero clean partitions.
   Calibration artifact: `sanity-calibration-3e51319d9817.json` (committed
   before any v2h.1 capture = sealed-envelope property).
   Language: quarantines mark data UNFIT FOR INFERENCE ("source-health
   anomaly") — never "proven corruption" / "physically impossible".
   Meta-monitor: gate fire-rate reported in every check artifact.
2. **Typed evaluation state machine** — `collectors/evaluate_axis3_v2h1.py`.
   captured → integrity-eligible → confirmed-clean → computable → PASS/FAIL.
   Verdicts computed ONLY on the confirmed-clean prefix; INVALID input →
   NOT_EVALUABLE (never "0% rising", never FAIL); fail-closed on partitions
   the gate has not classified. The newest partition is at most PROVISIONAL
   (official cutoff = newest FINAL-CLEAN, ordinarily t−1); promotion AND
   termination verdicts never rest on a provisional point.
3. **Verdict-layer canary**: per-cohort agreement between fitted slope sign
   and endpoint direction; below the declared floor 0.8 (provisional
   governance constant, to be empirically re-derived at the first live cutoff
   and then frozen) → cohort verdicts HELD with an anomaly packet (numbers
   only, no narrative labels).
4. **One-way fragility veto**: leave-one-partition-out slope-sign flips or
   Theil-Sen/OLS sign disagreement mark an entity UNSTABLE — it never counts
   as rising. The veto can only withhold a positive. The registered primary
   estimator (OLS on log1p) is NOT replaced (post-incident estimator
   replacement = outcome-restorative optics).
5. **Frozen expanded panel** — `expansion-manifest-DRAFT.json`
   (sha256 `026eaa45377a5b39481f5e4421846d0e7e62befffca9143f18ff96b2ecb80c6b`)
   UNION the 41 v2h pins carried verbatim: **90 systems / 628 packages**.
   Selection was VALUE-BLIND (declared-in-own-repo-tree at HEAD + exists on
   deps.dev; third-party project-linkage rejected as Sybil-permeable; no
   dependents value read during selection). Later pin growth NEVER changes
   this panel (next change = next superseding record).
   **Measured unit = the SYSTEM**: unique direct dependents over the UNION of
   the system's packages, dedup by (Dependent.System, Dependent.Name),
   intra-panel self-dependents excluded; a monorepo is one panel row.
6. **Sentinel canaries** (declared here, never scored): numpy, requests,
   click, rich (PyPI) · express, lodash, axios (npm) · serde, tokio, rand
   (Cargo) · spf13/cobra, stretchr/testify (Go) — captured in the SAME
   partition scan (marginal cost ~0) to separate "source is sick" from
   "systems moved". Canary aggregates are recorded in every capture manifest.
7. **Collector** — `collectors/t2_deps_v2h1_collect.py` (one scan per
   partition; ~$3.44 verified PRECISE for the full expanded panel — predicate
   count does not affect billed bytes; 600 GB circuit breaker; person-free
   job ids; idempotent per SnapshotAt). An optional row-level dependent-edge
   audit capture exists as a PAID on-demand mode (a second scan) — not part
   of the weekly cadence.
8. **Epistemic typing** (journal/memory discipline): entries are
   measured | derived | operator-hypothesis; causal labels about external
   data without an attached machine artifact are not journalable; hypotheses
   are never inherited as premises.
9. **Annual re-idempotence spot-check** (calendar ritual, ~$3.44/yr): re-read
   one historical partition, compare observation hashes — monitors upstream
   retroactive mutation. First due 2027-07.

## Baseline (non-gating, unchanged power)

- Candidates: the **16** most recent partitions strictly before this record's
  commit time (buffer over 14 because two known-unfit partitions and one
  necessarily-provisional newest partition fall inside the window).
- The baseline series = the **14 most recent CONFIRMED-CLEAN** of these per
  the gate (reaching deeper in history when unfit partitions fall inside —
  fixes the v2h wording that broke on corrupt partitions inside the window).
- Baseline remains non-gating: it can terminate early, it cannot promote.
- Cost note (keeper-approved 2026-07-21): 16 × $3.44 ≈ $55 one-time; weekly
  live captures ≈ $3.44 each thereafter.

## Promotion gate (live-only, v2h structure preserved)

1. ≥ 4 NEW distinct upstream SnapshotAt captured after this record via the
   real capture path AND classified CONFIRMED-CLEAN by the gate (quarantined
   or provisional snapshots do not count; quarantines extend the floor).
2. ≥ 28 calendar days of live quarantine from the first v2h.1 capture commit.
3. Criteria #1, #2, #4, #5, #6 PASS at EVERY confirmed-clean live cutoff;
   canary HOLD or fragility INDETERMINATE at a cutoff blocks a PASS at that
   cutoff (one-way: HOLDs can delay promotion, never manufacture it).
4. Criterion #3 (flip) on all ≥ 3 fully-forward confirmed-clean transitions.
5. The promotion artifact separates: frozen backtest · historical
   diagnostics · forward holdout · operational integrity · gate/canary/
   fragility reports. Collapsed columns = reject.

## Estimand honesty (unchanged framing, new panel date)

The evaluation object is the frozen-panel trajectory of the package set
selected and linkage-verified as of 2026-07-21. Residual survivorship beyond
the frozen universe is disclosed, not denied. All published claims carry this.

*Named and rejected: (i) clean-only restart on the 41-pin panel — 8/8 council
voices: a predetermined non-promotion ("credibility theater"); (ii) estimator
replacement alongside this record — outcome-restorative; (iii) pooled
cross-series calibration — different sources, different anomaly
distributions (Pro voice; implemented as negative controls instead).
Positive-only note: internal methodology governance; no negative signal about
any measured system.*

## Dated addendum — capture enrichment (2026-07-21, later; recall-right exercised BEFORE first capture)

No v2h.1 value-bearing capture had been committed when this addendum was fixed
(the first baseline run was stopped before its first partition completed; $0
billed). A second 8-voice council (consilium-03 + manual Pro voice) reviewed
"use the paid scan fully" and this addendum adopts its portfolio. The AXIS
semantics (measurand, panel, criteria, gate, floors) are UNCHANGED; this
addendum only enriches captured outputs and adds near-free companions:

1. **Enriched Dependents scan (same 551 GB, $0 marginal):** per system AND per
   package (GROUPING SETS, one scan): xor_fp_direct (order-independent
   fingerprint of the direct-dependent identity set — tamper evidence against
   count-stable content substitution), sketch64 (deterministic bottom-64
   fingerprint sketch — approximate retention/Jaccard forever without storing
   identity sets), eco_top (dependent-ecosystem composition). Package-level
   breakdowns are INTERNAL diagnostics, never published.
2. **Weekly sidecar (~$0.08/week ceiling-governed):** PackageVersionToProject
   slice for the panel (linkage corroboration + drift alarm; SECOND factor —
   repo-tree evidence remains the root of trust; never auto-modifies the
   panel; ceiling 16 GB) + Projects narrow slice for panel repos (unscored
   canary/diagnostics; cross-source discriminator for corrupt partitions;
   ceiling 2 GB) + retention tripwire (partition metadata, $0 — alarms if
   upstream starts pruning/replacing history).
3. **One-time purchases:** Projects full-history hoard for panel repos
   (pruning insurance; ceiling 100 GB = $0.625). PV2P history explicitly NOT
   purchased (~$14) — historical linkage state did not determine the frozen
   panel; backfill only if the current audit shows material disagreement.
4. **Declared non-captures:** Advisories standing series (ad-hoc incident
   queries only), PackageVersions weekly (backfillable; on-demand at a future
   release-cadence-v2 pre-registration), Dependencies/DependencyGraphEdges/
   Requirements/PackageVersionHashes (event-triggered forensic class:
   Dependencies at partition-quarantine events, ~$2.92/event).
5. **Ceilings-as-fail:** every sub-query carries maximum_bytes_billed; exceeding
   a ceiling stops the collector, never silently expands the commitment.
