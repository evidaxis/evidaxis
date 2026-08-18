# Supersession: m3-v2h.1 → m3-v2h.2 (criterion #4 re-specification; promotion adjudication)

> status: FIXED 2026-08-18, committed BEFORE any post-record capture (the next
> weekly tact, 2026-08-24, captures the 2026-08-17 upstream partition — unseen
> at fixing time; sealed-envelope property preserved).
> Supersedes **only** the criterion-#4 definition carried into the promotion
> gate of `AXIS3-DEPS-V2H1-SUPERSESSION-2026-07-21.md` (not edited — dated
> superseding record, drift-never-amends). Measurand, frozen panel
> (`026eaa45377a…`, 90 systems / 628 packages), estimator, sanity gate, canary
> and fragility veto are **UNCHANGED**.
> The keeper may recall this record by a dated note until the first
> post-record capture commit.

## 1. Promotion adjudication as of 2026-08-18 — NOT PROMOTED

Gate clause-by-clause against committed artifacts:

1. **Live partitions.** Confirmed-clean partitions captured forward of the
   v2h.1 record: 2026-07-20, 2026-07-27, 2026-08-03 — **three of the four
   required** (2026-08-10 captured, PROVISIONAL until its successor lands at
   the 2026-08-24 tact). **Accounting correction:** 2026-07-13 was captured
   inside the v2h.1 **baseline** run (commit `aaeefa43`, 17 pre-record
   partitions) and had been counted toward the live floor in the live log from
   the 2026-08-03 entry onward, culminating in the 2026-08-17 ritual line
   "gate met (4/4)". The record forbids the baseline from promoting ("it can
   terminate early, it cannot promote"); the partition is struck from the live
   count and remains a backtest point.
2. **28-day live quarantine** from the first v2h.1 capture commit
   (2026-07-21 18:02 UTC+1) matures **today, 2026-08-18**. Met.
3. **Criteria 1,2,4,5,6 at every confirmed-clean live cutoff.** c1/c2/c5/c6
   PASS at all four evaluated cutoffs; **c4 FAIL at all four**
   (`v2h1-live-2026-07-13-406d06d7e660`, `…-07-20-a801727c8d6b`,
   `…-07-27-302bfb08cef9`, `…-08-03-ef7b1b3a402d`). Gate not met.
4. **c3 on ≥3 fully-forward transitions:** three such transitions exist, PASS.
5. Promotion artifact (five separated sections) not produced — moot while
   clause 3 fails.

Verdict: **the axis remains in live quarantine.** No published claim, registry
entry, or cohort verdict changes. Termination is NOT triggered: the failure is
criterion-construct, not axis death (5/6 at four consecutive cutoffs, canary
agreement 0.94–1.0, zero HOLDs, zero fragility vetoes).

## 2. The defect in criterion #4

Criterion #4 (carried from `QUARANTINE-m3-preregistered-criteria.md` via the
v2 pre-registration §3.4): *rising-vote share in every voting cohort within
(0%, 40%)*; the evaluator enforces the bounds strictly
(`evaluate_axis3_v2h1.py`, `rising_share_lo/hi`, `lo < s < hi`). Two distinct
problems, deliberately separated because one is data-blind and the other is
not:

**(a) Unattainability (provable without any observation).** A cohort of size n
admits only the shares k/n. For n=1 the attainable set is {0, 1}; for n=2 it
is {0, 0.5, 1}. Neither contains a value inside the open interval (0, 0.40);
the smallest attaining cohort size is n=3 (1/3 ≈ 0.333). Six of the ten panel
cohorts are of size 1–2, so criterion #4 is **unsatisfiable by construction**
for them, independent of what the data show. This is the same class of defect
as the pre-expansion c1 under-power repaired in v2h.1: a defective
pre-registration, not an inconvenient result.

**(b) Level of assessment (construct question, outcome-relevant).** Criterion
#4 assesses non-degeneracy per cohort. Its stated purpose — the axis must
declare neither "nobody rises" nor "everybody rises" — is a statement about
the panel. Measured panel-wide, the rising share is **0.146 / 0.188 / 0.188 /
0.146** at the four live cutoffs (0.191 at baseline): in band at every
evaluation the axis has ever produced. Because this re-specification would
decide the promotion, it is fixed here **forward-only** (§4).

## 3. Criterion #4′ (operative from this record)

- **c4′.a (gating).** Rising share over ALL voting entities strictly inside
  (0%, 40%).
- **c4′.b (gating).** Risers occur in **≥2 distinct cohorts** — the minimum
  expressible plurality, chosen as the definitional boundary of "more than
  one" and not from the grid of passable thresholds. *Declared openly: the
  current series sits exactly at this floor (agent-frameworks +
  coding-agents at the 07-13 and 08-03 cutoffs). A single-cohort series
  fails.*
- **c4′.c (diagnostic, never gating).** Per-cohort shares are reported with
  cohort size and an attainability flag (attainable iff n ≥ 3); a zero in a
  cohort of n ≤ 2 carries no gating weight, being unattainable by
  construction. Cohort-level excursions are reported, not gated.
- Canary HOLD and fragility INDETERMINATE keep their one-way property: they
  can withhold a PASS, never manufacture one.

Implementation: evaluator criteria version bumped (`axis3_v2h1_eval_1` →
`axis3_v2h1_eval_2`); every evaluation artifact names its criteria version and
this record. A promotion claim citing an artifact whose criteria version does
not match the record under which promotion is claimed is invalid on its face.

## 4. Effectivity — forward only

Promotion requires criteria 1, 2, 4′, 5, 6 PASS and the clause-4 flip
condition at **≥3 confirmed-clean cutoffs whose partitions were captured
strictly after this record** (upstream partitions 2026-08-17, 2026-08-24,
2026-08-31; captured at the weekly tacts of 2026-08-24, 2026-08-31,
2026-09-07; each confirmed clean by its successor). Promotion window:
**~2026-09-14**. Cost: 4 weekly captures ≈ $14.

Re-evaluating the four existing cutoffs under c4′ is permitted and
**publishable as diagnostics only**, never as gate evidence. Disclosed here so
the forward window is not read as waiting for a different answer: under c4′
all four existing cutoffs would pass — that is precisely why the change may
not be applied to them.

*Named and rejected: (i) promoting today on "5/6 with a known c4 limitation" —
waiving a pre-registered criterion at the moment it binds is the failure the
quarantine exists to prevent; (ii) a cohort-size floor (n≥7 or n≥10) — the
smallest floor that clears the current data sits exactly above the cohorts
that fail (`inference-serving` n=5 at 0.0 at every cutoff,
`robotics-embodied` n=6 at 0.0 at two), i.e. fitted to the outcome;
(iii) retroactive application of c4′; (iv) terminating the axis on c4.
Positive-only note: internal methodology governance; no negative signal about
any measured system.*
