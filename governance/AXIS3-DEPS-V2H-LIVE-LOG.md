# m3-v2h live-quarantine log (append-only)

> Dated keeper journal of the forward (live) phase of the m3-v2h dependents-axis
> candidate. Governed by `AXIS3-DEPS-V2-HYBRID-SUPERSESSION-2026-07-16.md`.
> Baseline (14 pre-record snapshots, ending 2026-07-06; non-gating) is frozen and
> immutable — see `data/observations/backfill/axis3-deps-v2/baseline_manifest.json`
> and its evaluation artifact. This file records each NEW distinct upstream
> `SnapshotAt` captured after the record, its cutoff evaluation, and keeper
> decisions. Append only; never rewrite prior blocks (drift-never-amends).

## Live floor status

- Promotion needs ALL of: **≥4 new distinct SnapshotAt** captured after the record
  (2026-07-16 17:33:29) via `collectors/t2_deps_package_collect.py`; **≥28 days**
  from the first live capture commit; criteria #1,#2,#4,#5,#6 PASS at EVERY cutoff;
  criterion #3 (flip) PASS on all ≥3 fully-forward transitions (S1→S2,S2→S3,S3→S4).
- Captures so far: **1 / ≥4**. 28-day clock start: 2026-07-21 → earliest verdict
  window ≈ **2026-08-18**.

---

## Cutoff #1 — SnapshotAt 2026-07-13 (captured 2026-07-21)

**Capture.** `t2_deps_package_collect.py --snapshot 2026-07-13`, project
`evidaxis-analytics` (person-free job ids). 31 matched / 10 not-in-snapshot / 96
unpinned repos over the frozen 41-pin panel. Dry-run preflight: 550.96 GB
processed (PRECISE), ~$3.44 billed, under the 600 GB circuit breaker.
- observations: `data/observations/2026-07-21/deps_v2.jsonl`
  (observations_sha256 `d0dcf6645acbf115…`)
- BigQuery job `bqjob_r479b9120fee7c11_0000019f844e5f9e_1`
- query_sha256 `ae33e49ac6c84a58…`

**Keeper decision — 2026-07-13 is LIVE #1, not a late-arriving baseline point
(decided BLIND, before any value was read).** The 2026-07-13 partition's nominal
`SnapshotAt` (≈2026-07-13 21:00) precedes the record commit (2026-07-16 17:33),
but the partition had NOT landed in `bigquery-public-data.deps_dev_v1.Dependents`
at record time (the latest available partition on 2026-07-16 was 2026-07-06 — the
baseline's last point). Grounds for classifying it live:
1. The supersession's estimand is explicitly capture-availability based —
   the frozen baseline "reproduces the state a **pure-forward candidate** would
   have at **first eligibility**." Such a candidate, eligible at the record, could
   only observe through 2026-07-06; it captures 2026-07-13 as its first NEW point
   when the partition appears — which is exactly what happened here.
2. The baseline sample is immutable ("Later pin growth NEVER changes the baseline
   sample"; any amendment ⇒ a new superseding record + live-floor restart). It
   cannot absorb 2026-07-13 retroactively.
3. Promotion gate item 1 reads literally: a NEW distinct upstream `SnapshotAt`
   **captured after this record, through the real capture path** — 2026-07-13 is
   distinct from all 14 baseline snapshots and was captured 2026-07-21 via the
   live path. Both readings converge.
This classification does not change the promotion verdict (c1 fails structurally
regardless — see below); it only sets the live-floor counter to 1/4. Recallable
by a dated note if later judged wrong; the data point itself is immutable and
reconstructable from the public dataset.

**Evaluation at cutoff #1** — `evaluate_axis3_v2.py --as-of 2026-07-13 --label live`
(series = 14 baseline + 1 live = 15 distinct snapshots; 22 voting / 1 rising).
Artifact: `data/quarantine/axis3-deps-v2/eval/live-2026-07-13-40a4b825f5d2.json`
(sha256 `40a4b825f5d2…`), axes snapshot pinned `2026-07-11`.

| Criterion | Verdict | Value | vs baseline |
|---|---|---|---|
| c1 coverage (≥30 gate-capable) | **FAIL** | 22 | ~same (was 20); structural to the 41-pin panel |
| c2 independence (\|r(z3,z1)\|<0.5) | **PASS** | r=0.4854, 8 pairs | flipped from FAIL (+0.614) — but fragile (barely under 0.5; all pairs in agent-frameworks) |
| c3 flip (<0.30) | **PASS (preliminary)** | 07-06→07-13 flip=0.0455, churn=0.091 | not yet the gate condition (needs 3 fully-forward live→live transitions) |
| c4 non-degeneracy ((0%,40%) per cohort) | **FAIL** | agent-frameworks 0.125; other 6 cohorts 0.0 | ~same; panel-wide negative-slope regime persists |
| c5 floors / c6 no-look-ahead | **PASS** | structural | — |

**Read.** Promotion is NOT earnable on the current frozen panel: c1 (gate-capable
22 < 30) is structurally unreachable at 41 pins, and c4 stays degenerate (unique-
direct dependents flat/declining for ~all systems). c2 improved to a fragile PASS.
The axis is **NOT killed** — no construct failure surfaced; c2/c3 moved the right
way. It remains in live quarantine. The known lever (pin expansion: conda / HF-hub
/ Go / monorepo packages, to lift c1 and add c2 pairs outside the one dense cohort)
would be a query/identity change ⇒ a NEW superseding record + live-floor restart,
so it is deliberately NOT applied mid-floor. Continue capturing new snapshots as
they land (next expected ≈ weekly; 2026-07-20 partition not yet in BigQuery as of
2026-07-21).

### Data-integrity finding — 2026-07-21 (dated correction; supersedes the c4 read above)

A free diagnostic over the committed 15-snapshot series (no new BigQuery reads)
found that **the c4 verdict — and in fact the entire cutoff-1 scoring — is
contaminated by two corrupt upstream partitions: 2026-06-11 and 2026-06-15.**

Evidence (raw `unique_direct` trajectories):
- langgraph: …06-01=1313 → **06-11=16 → 06-15=12** → 06-23=1361…
- crewAI: …241 → **1 → 4** → 250… · ollama: …967 → **15 → 6** → 977… · vllm: …151 → **3 → 2** → 151…

A package's direct-dependent count cannot fall ~99% in one week and fully recover
the next; these two snapshots are partial/mid-recompute (matched coverage 22 and
25 of 31 vs 31 on every clean partition; both off the ~weekly cadence — 06-11 at
22:24, off-cycle). The evaluator's `votes_at_cutoff` has no anomaly guard, so it
fits `slope(log1p)` across these two deep mid-series dips, which sit right of the
series centre and drag the least-squares slope negative for nearly every entity.
Result: **only 2/22 voting entities show positive slope** even though **26/31
matched packages are rising endpoint-to-endpoint** (langgraph 1008→1451, ollama
847→1021, crewAI 168→278). "0% rising per cohort" is therefore an artifact of the
two bad weeks, NOT a property of the systems, and NOT a strict-gate effect.

**Corrections to prior notes (append-only; earlier text left intact):**
- The cutoff-1 table above ("c4 … panel-wide negative-slope regime persists";
  "unique-direct flat/declining for ~all systems") is a MIS-DIAGNOSIS. The metric
  is healthy and near-monotonically rising; the failure is contaminated slopes.
- Because c2 and c3 are computed on the same poisoned slopes/z-scores, the
  cutoff-1 verdicts for c2 (r=0.4854) and c3 are also **not trustworthy**. No
  criterion verdict from this cutoff should be relied on.
- The 2026-07-16 baseline note's "panel-wide negative slope regime / unique-direct
  падает у ВСЕХ" carries the same error.

**Implication.** Capturing further live snapshots on top of this contaminated
baseline is pointless. The disciplined fix is a NEW superseding record that
(1) adds a PRE-REGISTERED anomalous-partition guard (exclude partitions whose
panel-wide value collapses and recovers — a physically-impossible-drop rule,
fixed on principle, not tuned to results; disclosed) and, since the floor
restarts anyway, (2) expands the pin panel (conda / HF-hub / Go / monorepo + more
systems) to lift c1. Per the change-discipline this restarts the live floor
(new baseline backfill ≈ $48, + live). Because it alters a pre-registered scoring
+ panel on seen data, it goes through an adversarial spar (external review) BEFORE
commit — not a unilateral edit. A clean re-score is deliberately NOT computed here
to keep the exclusion rule blind to its own effect until pre-registered. Live
floor is HELD pending the keeper's decision on the restart.

### Council review + retraction + gate implementation — 2026-07-21 (same day, later)

**7-model adversarial council** reviewed the incident, the keeper post-mortem and
DRAFT v1 (roster: ChatGPT 5.6 Sol xhigh · GLM 5.2 · Kimi K3 · Grok 4.5 ·
MiniMax M3 · Claude Opus 4.8 · DeepSeek V4 Pro; synthesis judged in the keeper's
planning layer). Verdict highlights: DRAFT v1's hand-set constants and drop-only
direction REJECTED (a drop-only filter in a positive-only institute =
positive-momentum laundering risk); replacement = typed evaluation state machine
+ two-stage direction-neutral gate + verdict-layer canary + provisional-last-point
policy + procedure-derived thresholds with the two bad partitions as challenge
cases (challenge != holdout); restart fork = clean+expand in one cycle, 7/7, with
a value-blind expansion manifest and dual-rationale record. Operative rewrite:
`DRAFT-data-sanity-gate.md` v2.

**Executed same day:**
- **Retraction:** both evaluation artifacts (baseline + cutoff #1) retagged
  INVALID_INPUT — `eval/RETRACTION-2026-07-21.md`. No m3-v2h criteria verdict
  stands; the "1/4 live floor" state above is void with them.
- **Gate implemented:** `collectors/data_sanity_gate.py` (two-stage, symmetric,
  corpus-calibrated: 71 clean transitions across 3 series; move bound 3.0x,
  panel threshold 0.214). **Kill-bar PASS:** flags exactly {2026-06-11,
  2026-06-15}, zero clean partitions. 06-11 fires BOTH stages (coverage 22<30
  pre-registered floor + reversal-share 1.0 vs 0.214 threshold); 06-15 fires the
  stage-1 contract (25<30; the second partition of a consecutive corrupt pair is
  invisible to a 1-step shape rule — RECOVERY_WINDOW=2 now covers the pair class).
- **Free row-count sentinel measured** (INFORMATION_SCHEMA, $0, 169 partitions
  2023-04..2026-07): the 2026-06 incident had NORMAL total_rows (ratio 1.039) —
  content corruption at normal cardinality; row counts alone are insufficient,
  panel contracts are load-bearing. Upstream history DOES contain
  truncated/inflated partitions (2024-02..03 at ratio ~0.4; 2023-11 / 2024-08
  spikes 2-3x) — the sentinel catches that other class for free.

**Next (in order):** value-blind expansion manifest (metadata-only pin
eligibility, frozen before any value query) → superseding record v2h.1 (state
machine + gate + canary + provisional-last-point + expansion, dual-rationale)
→ new baseline backfill (14 most recent CONFIRMED-CLEAN partitions, ~$48) →
live floor restarts. Earliest promotion verdict shifts to ~late September 2026
(4 confirmed-clean live snapshots + 28 days from restart).

### v2h.1 baseline EXECUTED on the expanded panel — 2026-07-21 (evening)

**Burn:** 17 partitions (2026-03-16 … 2026-07-13) with the ENRICHED scan
(fingerprints + sketch64 + per-package + eco_top + canaries in the same
$3.44/partition). Two incidents during the burn, both caught by design:
(1) a GROUPING-SETS alias-shadowing bug produced zero parsed canaries on the
first partition — the canary fail-fast principle stopped the series at $3.44
of waste; fixed (pkg_out alias), smoke-verified, resumed; (2) the pre-existing
"<30" coverage contract is panel-relative and would have missed 06-15 on the
90-system panel (50 matched > 30) — the council-approved relative-coverage
layer (matched < threshold x series median, threshold calibration-derived,
floor 0.90) was implemented and calibrated.

**Gate on the new series (17 partitions): KILL-BAR PASS** — flags exactly
{2026-06-11 (SUSPECT_CORRUPT share=1.0 + coverage 46 < 0.9x63),
2026-06-15 (INVALID_COVERAGE 50 < 0.9x63)}, zero false positives on 14 clean;
negative controls (t2 x2, v1): zero firings. Check artifact
`sanity-check-631597ae6555.json`, calibration `sanity-calibration-e8580af09a18.json`.

**First honest evaluation (baseline, non-gating), evaluator v2h.1:**
confirmed-clean prefix = 14 partitions (03-16…07-06, corrupt pair excluded),
official cutoff 2026-07-06, 07-13 PROVISIONAL (diagnostics only).
47 voting / 9 rising / 1 unstable-vetoed (LOO). **c1 PASS 46>=30** (expansion
repaired the structural under-power) · **c2 PASS r=+0.2985 on 38 pooled pairs**
(was +0.61 poisoned / 0.49 fragile — now far from the bound and multi-cohort) ·
c3 PASS (last clean transition flip 0.19) · **c4 FAIL** — but the failure mode
CHANGED CLASS: agent-frameworks 23.5% and coding-agents 27.3% are alive and
in-band; the fail comes from small cohorts (n=1-5) at 0% and robotics-embodied
at exactly 0.40 (boundary). This is small-cohort granularity, not the poisoned
panel-wide-zero regime. Verdict-layer canary: agreement 0.91-1.0 across all
cohorts, zero HOLDs. c5/c6 PASS.

**Read:** the axis is alive on the expanded panel; 4/6 criteria pass at
baseline with a healthy verdict layer. c4's small-cohort behavior is a known
structural property to watch at live cutoffs (baseline is non-gating either
way). Live floor: first live capture = the next upstream partition (~2026-07-20,
expected in BigQuery within days); promotion window ≈ late August 2026
(4 confirmed-clean live snapshots + 28 days + successor confirmation lag).

## 2026-07-27 — FIRST LIVE CAPTURE (weekly cadence, ritual A13)

**Capture.** `t2_deps_v2h1_collect.py --snapshot 2026-07-20` — the first live partition
under the v2h.1 record. 63/90 systems matched, 10/12 canaries, job
`bqjob_r418517b49bb53e9e_0000019fa2d20c34_1`. Coverage 63 is **the clean-series median**
(`coverage_series_median_clean: 63` in the sanity calibration), not a shortfall: the panel
declares 90 systems, but only those with dependents present in a given partition are
measurable. Reading 63/90 as "coverage drop" would have been exactly the m3-class error
the sanity gate exists to prevent — the gate, not the operator, classifies partitions.

**Sidecar** (`--sidecar 2026-07-20`): PV2P 1131 rows, Projects 119 rows, retention tripwire
`earliest 2023-04-10 · latest 2026-07-20 · n=170 · rows_total 987,298,245,180` — upstream
history is not being rewritten or pruned at this observation.

**Sanity gate** (`--check sanity-calibration-e8580af09a18.json --series v2h1`):
17 partitions classified. **KILL-BAR PASS** — flagged exactly the two known-bad partitions
(`2026-06-11 SUSPECT_CORRUPT cov=46 share=1.0`, `2026-06-15 INVALID_COVERAGE cov=50`),
no false positives, negative control intact. **2026-07-13 promoted PROVISIONAL → CLEAN**
(the 07-20 capture is its successor confirmation); **2026-07-20 is PROVISIONAL** as the
newest partition, per the record's necessarily-provisional rule.
Artifact: `data/quarantine/axis3-deps-v2/sanity-check-0e3e9a2d8420.json`.

**Evaluation** (`evaluate_axis3_v2h1.py --as-of 2026-07-13 --label live`):
status EVALUATED, official cutoff **2026-07-13**, 48 voting / 7 rising, 0 unstable-vetoed.
**c1 PASS · c2 PASS · c3 PASS · c4 FAIL · c5 PASS · c6 PASS** — 5/6, and the c4 failure is
the same small-cohort granularity already characterised at baseline (n=1-5 cohorts at 0%,
robotics-embodied at the 0.40 boundary), not the poisoned panel-wide-zero regime.
Artifact: `eval/v2h1-live-2026-07-13-406d06d7e660.json` (sha256 406d06d7e660…).

**Promotion accounting.** Gate requires ≥4 NEW confirmed-clean partitions captured via the
live path after the record, plus ≥28 days of live quarantine. This week contributes **one**
capture (2026-07-20), still PROVISIONAL until its successor lands (~2026-07-27, next ritual).
Nothing about the axis verdict changes today; promotion window remains late August 2026.
Cost this week: $3.44 capture + ~$0.08 sidecar.

## Live capture 2026-07-27 (ritual 2026-08-03, recovered late)

**Capture.** `t2_deps_v2h1_collect.py --snapshot 2026-07-27` — 63/90 matched, 10 canaries,
job `bqjob_r3c3b9046b980c837_0000019fc769416c_1`, snapshot_at `2026-07-27 21:01:02`.
Panel manifest `026eaa45377a…` unchanged from the previous week, so coverage is comparable
by construction. 63 is the clean-series median (`coverage_series_median_clean: 63`), i.e.
the expected panel size, not a shortfall.

**Sidecar** (`--sidecar 2026-07-27`): PV2P 1132 rows, Projects 122 rows, retention tripwire
`{earliest: 20230410, latest: 20260727, n: 171}` — no history attrition detected.

**Sanity gate** (`--check sanity-calibration-e8580af09a18.json --series v2h1`): 19 partitions
checked, **KILL-BAR PASS** — flagged exactly `['2026-06-11', '2026-06-15']`, the two known
corrupt partitions, and nothing else. 2026-07-20 **promoted CLEAN**; 2026-07-27 PROVISIONAL
per the necessarily-provisional rule for the newest partition.
Artifact: `data/quarantine/axis3-deps-v2/sanity-check-9698fea08fe1.json`.

**Evaluation** (`evaluate_axis3_v2h1.py --as-of 2026-07-20 --label live`): status EVALUATED,
official cutoff **2026-07-20**, 48 voting / 9 rising (was 7 at the 07-13 cutoff),
0 unstable-vetoed.
**c1 PASS · c2 PASS · c3 PASS · c4 FAIL · c5 PASS · c6 PASS** — 5/6, and c4 is again the
small-cohort granularity characterised at baseline, not the poisoned panel-wide-zero regime.
Artifact: `eval/v2h1-live-2026-07-20-a801727c8d6b.json` (sha256 a801727c8d6b…).

**Promotion accounting.** Two confirmed-clean live partitions (2026-07-13, 2026-07-20) of the
four required; 2026-07-27 stays provisional until its successor lands (~2026-08-03, next
ritual). Promotion window remains late August 2026.
Cost this week: $3.44 capture + ~$0.08 sidecar.

**Process note — why this is dated 08-03 and not 07-27.** The 2026-08-03 weekly ritual did
not run component A13 at all; the gap surfaced only when the whole ritual was audited against
its artifacts afterwards. The repo's own staleness check (`.github/workflows/
axis-staleness-check.yml`, fires above 8 days) had not yet triggered — it would have caught
this on 08-04, after the fact rather than before. The capture itself is unaffected: deps.dev
partitions are addressable by snapshot day, so a late capture recovers the same data. What a
miss actually costs is calendar time in the 28-day live-quarantine clock, not data.

## Live capture 2026-08-03 (ritual 2026-08-10)

**Capture.** `t2_deps_v2h1_collect.py --snapshot 2026-08-03` — 63/90 matched (clean-series
median), 10 canaries, job `bqjob_r33a035eade0e1c47_0000019feae67b03_1`. Panel manifest
`026eaa45377a…` unchanged — coverage comparable by construction.

**Sidecar** (`--sidecar 2026-08-03`): PV2P 1133 rows, Projects 122 rows, retention tripwire
`{earliest: 20230410, latest: 20260803, n: 172}` — no history attrition.

**Same-day capture attempt (process note).** A `--snapshot 2026-08-10` call was also made and
was aborted by the canary-absence guard ("zero canaries parsed — query/parse broken; aborting
before burning more partitions"). That is the guard working as designed: the deps.dev partition
for the current Monday has not landed yet. The weekly tact captures the PREVIOUS Monday's
partition; no partitions were burned.

**Sanity gate** (`--check sanity-calibration-…9817.json --series v2h1`): KILL-BAR PASS —
flagged exactly `['2026-06-11', '2026-06-15']` and nothing else. **2026-07-27 promoted CLEAN**;
2026-08-03 PROVISIONAL per the necessarily-provisional rule.
Artifact: `data/quarantine/axis3-deps-v2/sanity-check-e4ee7a2d62ab.json`.

**Evaluation** (`--as-of 2026-07-27 --label live`): status EVALUATED, official cutoff
**2026-07-27**, 48 voting / 9 rising, 0 unstable-vetoed.
**c1 PASS · c2 PASS · c3 PASS · c4 FAIL · c5 PASS · c6 PASS** — 5/6; c4 is again the
small-cohort granularity characterised at baseline, not the poisoned panel-wide-zero regime.
Artifact: `data/quarantine/axis3-deps-v2/eval/v2h1-live-2026-07-27-302bfb08cef9.json`
(sha256 302bfb08cef9329d…).

**Promotion accounting.** Three confirmed-clean live partitions (2026-07-13, 2026-07-20,
2026-07-27) of the four required; 2026-08-03 stays provisional until its successor lands
(~2026-08-17, next ritual). Promotion window remains late August 2026.
Cost this week: $3.44 capture + ~$0.08 sidecar.

**Weekly card activation (policy REGISTRY-GROWTH-POLICY-2026-07-21, first tranche).** NOT run
in the ritual chat: no activation pipeline exists yet (policy defines the formula, no script or
publish path). Per the ritual's own rule, non-routine goes to a dedicated Evidaxis chat — the
first tranche is a build task (manifest → live cards → deploy), routed there.

## Live capture 2026-08-10 (ritual 2026-08-17)

**Capture.** `t2_deps_v2h1_collect.py --snapshot 2026-08-10` — 66/93 matched, 10 canaries
(panel 93 systems / 631 packages, manifest 026eaa45377a…, job bqjob_r1605ef5733587e07…).

**Sidecar** (`--sidecar 2026-08-10`): PV2P 1141 rows, Projects 132 rows, retention tripwire
{earliest 20230410 · latest 20260810 · n 173}.

**Sanity gate** (`--check sanity-calibration-3e51319d9817.json --series v2h1`): KILL-BAR PASS —
flagged exactly `['2026-06-11', '2026-06-15']` and nothing else. **2026-08-03 promoted CLEAN**
(cov=63, share=0.0); 2026-08-10 PROVISIONAL per the necessarily-provisional rule (cov=66).
Artifact: `data/quarantine/axis3-deps-v2/sanity-check-961a42fc06f2.json`.

**Evaluation** (`--as-of 2026-08-03 --label live --gate-check sanity-check-961a42fc06f2.json`):
status EVALUATED, official cutoff **2026-08-03**, 48 voting / 7 rising, 0 unstable-vetoed.
**c1 PASS · c2 PASS · c3 PASS · c4 FAIL · c5 PASS · c6 PASS** — 5/6; c4 is again the
small-cohort granularity characterised at baseline.
Artifact: `data/quarantine/axis3-deps-v2/eval/v2h1-live-2026-08-03-ef7b1b3a402d.json`
(sha256 ef7b1b3a402df736…).

**Promotion accounting — GATE MET.** Four confirmed-clean live partitions
(2026-07-13, 2026-07-20, 2026-07-27, 2026-08-03) of the four required. The promotion act
itself (supersession record + panel verdict) is a governance step, not a ritual step —
routed to a dedicated Evidaxis chat per the non-routine rule.
Cost this week: $3.44 capture + ~$0.08 sidecar.

## 2026-08-18 — Promotion adjudication: NOT promoted; c4 re-specified forward-only (v2h.2)

**Correction to the 2026-08-17 entry.** "Promotion accounting — GATE MET (4/4)" was wrong
in two ways. (1) The count included 2026-07-13, a partition captured inside the v2h.1
BASELINE run; the record forbids the baseline from promoting. Forward-captured
confirmed-clean partitions are **three** (07-20, 07-27, 08-03); 08-10 becomes clean at the
2026-08-24 tact. (2) The count was never the whole gate: clause 3 requires c1/c2/c4/c5/c6
PASS at EVERY confirmed-clean live cutoff, and **c4 has FAILED at all four cutoffs** — the
"5/6" reported weekly was itself the gate not being met.

**Adjudication:** NOT PROMOTED; axis remains in live quarantine. Termination not
triggered (criterion-construct failure, not axis death). Full record:
`AXIS3-DEPS-V2H2-SUPERSESSION-2026-08-18.md` — c4 was unsatisfiable by construction for
6 of 10 cohorts (n<=2 admits no share inside the open band (0, 0.40); smallest attaining
n is 3), and re-specified as c4′: panel-level share in (0, 40%) + risers in >=2 cohorts,
per-cohort shares demoted to diagnostics with an attainability flag. Evaluator bumped to
`axis3_v2h1_eval_2`; artifacts name the governing record.

**Forward window:** partitions 2026-08-17 / 08-24 / 08-31, captured at the 08-24 / 08-31 /
09-07 tacts, each confirmed clean by its successor → promotion window **~2026-09-14**.

**Diagnostics (disclosed, never gate evidence):** under c4′ all four existing cutoffs
evaluate 6/6 (`v2h1-diagnostic-2026-07-13-9cffdd563740` · `…-07-20-6212857b0a3a` ·
`…-07-27-d6307865ce42` · `…-08-03-e3debb70249a`; panel shares 0.146/0.188/0.188/0.146,
rising cohorts 2/3/3/2). Recorded so the forward window is not read as waiting for a
different answer — the change is forward-only precisely because it would decide the
outcome retroactively.

## Live capture 2026-08-17 (ritual 2026-08-24)

**Capture.** `t2_deps_v2h1_collect.py --snapshot 2026-08-17` — 71/97 matched, 10 canaries
(panel 97 systems / 635 packages, manifest 026eaa45377a…, job bqjob_r543478b297e0f773…).

**Sidecar** (`--sidecar 2026-08-17`): PV2P 1147 rows, Projects 151 rows, retention tripwire
{earliest 20230410 · latest 20260817 · n 174}.

**Sanity gate** (`--check sanity-calibration-3e51319d9817.json --series v2h1`): KILL-BAR PASS —
flagged exactly `['2026-06-11', '2026-06-15']` and nothing else. **2026-08-10 promoted CLEAN**
(cov=66, share=0.0); 2026-08-17 PROVISIONAL per the necessarily-provisional rule (cov=71).
Artifact: `data/quarantine/axis3-deps-v2/sanity-check-5c9212a1ea6e.json`.

**Evaluation** (`--as-of 2026-08-10 --label live --gate-check sanity-check-5c9212a1ea6e.json`,
evaluator `axis3_v2h1_eval_2` per the v2h.2 record): status EVALUATED, official cutoff
**2026-08-10**, 48 voting / 8 rising, 0 unstable-vetoed.
**c1 PASS · c2 PASS · c3 PASS · c4′ PASS · c5 PASS · c6 PASS — 6/6**, the first live cutoff
evaluated fully green under the re-specified panel-level c4′ (gating, not diagnostic).
Artifact: `data/quarantine/axis3-deps-v2/eval/v2h1-live-2026-08-10-6ce2bdea386e.json`
(sha256 6ce2bdea386e5983…).

**Promotion accounting (v2h.2 forward window).** Forward-captured confirmed-clean partitions
toward the window: **2026-08-10 is the first of the three** (08-17 and 08-24 follow, each
confirmed clean by its successor at the 08-31 / 09-07 tacts) → promotion window **~2026-09-14**
unchanged. Nothing published, no registry change.
Cost this week: ~$3.44 capture + ~$0.08 sidecar.
