# Methodology m5: exact axis-3 normalization for pairs, effective 2026-10-17

> Status: FIXED 2026-10-16. Class: PATCH. Parent: m4.
> Effective for snapshots dated 2026-10-17 and later, independently of capture or run time.
> Implements `ERRATUM-2026-10-05-axis3-two-member-rounding.md` forward only.
> Earlier snapshots, methodology specifications and governance records remain unchanged.
> The implementation commit and canonical formula fingerprint are pinned by the m5
> row in `web/src/lib/methodology-registry.json`.

## 1. Correction

The scoring entrypoint `collectors/score_m3.py` passes `exact_pair=True` to
`evaluate_axis3_v2h1.votes_at_cutoff`, and hence `_robust_z`, from the activation
snapshot date. With exactly two eligible systems of different log(1 + latest)
sizes, the fitted line passes through both points: both residuals and both z are
exactly zero. No tolerance or near-zero threshold is introduced. The old arithmetic
could turn a one-ulp residual difference into z = -0.674.

Equal-size pairs and cohorts with three or more eligible systems retain the old
arithmetic. The default evaluator flag remains off for historical evaluations.
The m3/m4 scoring paths retain their date ranges, including late captures of an
earlier snapshot. A dated regression test checks the flag through to `_robust_z`.

## 2. Unchanged

The m4 own-package measurand, package admission, unverified-package treatment,
fixed self-name exclusion list, exact history derivation and restart rule are
unchanged. Axes 1 and 2, cohorts, floors, canary hold, fragility veto, staleness,
gate, momentum formula, percentile formula, confidence and status rules are
unchanged. This corrects arithmetic rather than changing the measured quantity.

Forward captures still follow METHODOLOGY-M4-2026-10-04 section 4: their mapping
switch follows the partition date. This patch adds no packages, panel catch-up,
BigQuery replay or source request.

## 3. Effect on the published 2026-10-10 m4 snapshot

Computed from the committed inputs at snapshot capture
`2026-10-12T12:11:36+00:00`. `score_m3.py --date 2026-10-10 --verify` with the
historical flag off reports **files match recomputation**. Forcing only the
evaluator's `exact_pair=True` in a read-only verification reports **DRIFT in 8
files**: the snapshot, five entity cards and two history files. No files are
rewritten. The following table gives published values followed by the exact-pair
counterfactual; it is not a replacement snapshot.

| System | Entity | Axis-3 z | Momentum | Percentile |
|---|---|---|---|---|
| Kokoro-82M | `e_MB6DQ5PDDKH` | -0.674 -> 0.0 | 44.5 -> 48.7 | 29 -> 50 |
| Browser Use | `e_1GSH6ZQHW7B` | -0.674 -> 0.0 | 32.0 -> 36.2 | unchanged |
| Qwen-Image | `e_5R5PKZN9WTY` | unchanged | unchanged | 43 -> 36 |
| LTX-Video | `e_QFECGB8X9W5` | unchanged | unchanged | 50 -> 43 |
| SkyReels-V2 | `e_20N3FEGPDR2` | unchanged | unchanged | 36 -> 29 |

The only two eligible pairs are:

| Cohort | Members (latest direct dependents) | Axis-3 z, published -> exact |
|---|---|---|
| media-generation | Kokoro-82M (125), Diffusers (383), `e_9VRK70WNP96` | (-0.674, 0.0) -> (0.0, 0.0) |
| gui-agents | Browser Use (94), UI-TARS Desktop (76), `e_A4CCB1NFPZB` | (-0.674, 0.0) -> (0.0, 0.0) |

Every other entity value is identical. No rising vote, Rising membership, status,
confidence, coverage count or published axis-correlation diagnostic changes.
Historical arithmetic remains platform-dependent as documented in the erratum;
the table uses the committed published snapshot, which matches the local legacy
recomputation for this date.

## 4. Publication surfaces and acceptance

`methodology/m5.json` and its canonical SHA256 pin the correction. The registry
adds m5 and marks m4 superseded from 2026-10-17 without changing older formula or
code pins. Public current status and `/methodology/current/` follow the latest
published snapshot, not the stale top-level `current` field in the source registry.
The versioned `/methodology/m5/` page is available before activation.

Shared web descriptions, glossary, coverage states, card exports and axis links
carry the own-package definition for m4 and m5. The citation example follows the
snapshot version. A separate m5 control-shell baseline extends the frozen canary
baselines without rewriting their JSON, assignment or hash algorithm. Publication
paths use the same `npm run verify` gate, including Card B consistency and badges.

Acceptance includes full Python and web suites, date-boundary and publication
tests, m5 rendering and exports, formula fingerprint checks, and a deliberate
disabled-flag mutation that must fail the regression tests. Deployment and the
first real m5 weekly capture are separate operational checks.
