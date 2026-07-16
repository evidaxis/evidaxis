# Pre-registration: candidate axis m3-v2 — unique direct dependent packages (deps.dev, BigQuery)

> status: FIXED 2026-07-16, BEFORE any v2 data capture; post-hoc edits forbidden
> (a correction is a dated superseding record, never an edit).
> Successor to m3-v1, terminated the same day as construct-invalid:
> `AXIS3-DEPS-V1-TERMINATION-2026-07-16.md`. Criteria thresholds are carried over
> from `QUARANTINE-m3-preregistered-criteria.md` for comparability; the measurand,
> capture mechanics, and eligibility rules are new and fixed here.
> The v2 clock has NOT started: it starts at the first committed capture run,
> which is permitted only after this file is merged and the BigQuery access
> question (keeper action, below) is resolved.

## 1. Measurand (fixed)

**Adoption breadth of a tracked system's package line:** the number of UNIQUE direct
dependent packages, deduplicated by dependent identity `(System, Name)`, across ALL
versions of ALL linkage-verified packages of the system, evaluated on ONE coherent
deps.dev BigQuery snapshot (`SnapshotAt`).

Reference query shape (BigQuery `bigquery-public-data.deps_dev_v1.Dependents`):

```sql
SELECT COUNT(DISTINCT CONCAT(Dependent.System, '/', Dependent.Name))
WHERE SnapshotAt = @snapshot            -- one coherent snapshot, never mixed
  AND MinimumDepth = 1                  -- direct only (primary signal)
  AND DependentIsHighestReleaseWithResolution = TRUE
GROUP BY <target system's package set>  -- union over its verified packages, all versions
```

- **Direct-only is the primary signal** (explicit integration; less amplification
  through popular transitives). Any-depth (`MinimumDepth >= 1`) is captured alongside
  as a DIAGNOSTIC field, never scored.
- **Project-level package set:** a system's estimand covers ALL its linkage-verified
  packages (monorepos publish several); the DISTINCT over downstream identities makes
  the union well-defined (a downstream depending on two of the system's packages
  counts once). Each package enters the set only through the existing pin discipline:
  name-variant match + declared-link verification back to the system's repository
  (`data/deps_id_map.json`, append-only, `pinned_at` recorded).
- Momentum readout mirrors m2 semantics: least-squares slope of `log(1 + unique_direct)`
  over capture points, within-cohort robust-z (median / 1.4826*MAD, clamp +/-3),
  residualized on `log(1 + latest unique_direct)` as the size proxy.
- Vote floors: `>= 5` latest unique direct dependents (DEPS_FLOOR analog) AND the
  point-count floor of §3.

## 2. Capture mechanics (fixed)

- Source: deps.dev public BigQuery dataset (CC-BY 4.0; rights position recorded in
  `RIGHTS-BASIS.md`, post-genesis appends). REST `v3alpha` is NOT used for scoring
  (per-version counts only; experimental surface).
- One capture = one `SnapshotAt`, recorded with: the snapshot timestamp, the exact
  query text hash, the BigQuery job id, and the result row set hash. Mixed-snapshot
  aggregates are forbidden.
- Capture cadence: one capture per distinct upstream `SnapshotAt` (dedup by snapshot,
  not by wall-clock day). Re-reading the same snapshot is idempotent, never a new point.
- Store: `data/observations/<date>/deps_v2.jsonl` (+ per-entity history namespace),
  coverage classes mirror v1 (`matched` / `no_package_match` / `fetch_error`), plus
  `not_in_snapshot` when a pinned package is absent from the snapshot.
- Scorer: a NEW `collectors/shadow_axis3_deps_v2.py` with a REQUIRED `--as-of` argument
  (both the observation cut-off and the cohort snapshot are pinned to it; the v1
  scorer's latest-snapshot default and its retroactive pin-map application are the
  named defects being corrected).
- Criteria evaluation: a NEW `collectors/evaluate_axis3_quarantine.py` computes ALL
  criteria (§3) mechanically and writes a content-addressed run artifact into the repo
  (not a gitignored scratch file). Ad-hoc session arithmetic does not count.

## 3. Promotion criteria (fixed; thresholds carried from v1 for comparability)

A promotion proposal may be brought to the keeper ONLY when BOTH floors hold:
**>= 28 calendar days of v2 capture** AND **>= 14 distinct upstream `SnapshotAt`
points accumulated** (if the upstream cadence is slower than daily, the clock simply
runs longer; no adaptive shortcut), and >= 2 consecutive weekly evaluation runs pass
ALL of:

1. **Coverage:** gate-capable entities (>= 2 axes present) >= 30.
2. **Independence:** pooled within-cohort |pearson(z3, z1)| < 0.5 over cohorts with
   n >= 5 (record r(z3, z2) where axis-2 exists — informative). The evaluation
   artifact additionally reports a Fisher 95% interval and leave-one-cohort-out
   sensitivity (informative, not gating — fixed here to prevent later cherry-picking).
3. **Stability:** rising-vote flip-rate between consecutive weekly runs < 30% of
   voting entities.
4. **Non-degeneracy:** rising-vote share in every voting cohort within (0%, 40%).
5. **Honesty floors:** a vote exists only at >= 14 distinct-snapshot points for the
   entity AND latest unique_direct >= 5 — enforced in code.
6. **No look-ahead:** an evaluation at time t uses only observations with
   `SnapshotAt <= t` AND only entities whose `pinned_at <= t` (pin-map growth never
   retroactively changes an earlier evaluation's sample).

## 4. Eligibility and identity (fixed)

- An entity enters the v2 sample at its `pinned_at` (first verified pin), never
  retroactively. Pin-map growth during quarantine is allowed — discovery follows the
  fixed procedure (name variants + link verification), which is independent of z1/z3
  values, so it cannot select on the outcome.
- Anti-squat hygiene (carried from v1): link verification is mandatory; additionally,
  a new pin whose repository postdates the package's earliest release by > 30 days is
  flagged for manual identity review before entering the sample.

## 5. Known gaming vectors (recorded at fixing time)

- Registry-Sybil: an attacker publishes N thin wrapper packages depending on the
  target. Cost: real published packages with real manifests; mitigations: direct-only
  + DEPS_FLOOR + the cross-correlation monitor; dependent-weighting (PageRank-style)
  is a possible FUTURE candidate, deliberately NOT part of v2 (recorded so adding it
  later is a new version, not a silent patch).
- Monorepo self-dependencies: packages of the same system depending on each other are
  excluded from the unique-direct count (same-system dependents filtered out).

## 6. Keeper actions required before the clock starts

1. **BigQuery access:** a GCP project with billing enabled (public-dataset queries are
   free up to 1 TB/month; expected usage well under that with `SnapshotAt` partition
   filters). Service-account credentials for the collector.
2. Optional recall window: this pre-registration is recallable by a dated keeper note
   until the first capture commit; after that, changes = superseding record only.

*Positive-only note: internal methodology governance; no negative signal about any
measured system is published or implied.*
