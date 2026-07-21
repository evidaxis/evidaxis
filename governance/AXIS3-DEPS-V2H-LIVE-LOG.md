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
