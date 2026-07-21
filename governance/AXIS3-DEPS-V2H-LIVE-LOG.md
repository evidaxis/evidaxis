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
