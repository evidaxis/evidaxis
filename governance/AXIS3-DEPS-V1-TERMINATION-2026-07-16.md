# Termination: candidate axis m3-v1 (deps.dev default-version dependents momentum)

> status: TERMINATED 2026-07-16, quarantine stage 3 (shadow-run), before any promotion.
> Grounds: construct invalidity discovered in the measurand — not a statistical failure.
> The keeper may recall this act by a dated note (ADJUDICATION-2026-07-11 procedure).
> Pre-registered criteria: `QUARANTINE-m3-preregistered-criteria.md` (unchanged, historical).
> Adversarial review: three-vendor spar 2026-07-16 (Codex gpt-5.6 · Grok 4.5 · MiniMax M3),
> synthesis held in the keeper's planning layer; verdicts summarized below.

## What was discovered (verified live, 2026-07-16)

1. **deps.dev `:dependents` is per-version and no package-level endpoint exists.** The
   v1 collector sampled "dependents of whatever version is default today". Live probe:
   vllm's eight consecutive versions carry dependentCount = 1, 3, 3, 13, 1, 43, 5, 3.
   Adjacent daily points therefore measure DIFFERENT stocks whenever the default flips —
   for fast-releasing systems the series is release-cadence sawtooth, not adoption
   momentum. The sawtooth enters the formula twice: in the log-slope AND in
   `latest_dependents` used as both the vote floor and the residualization size proxy.
2. **Missingness is not random.** A freshly published default version has no computed
   dependents yet (404) → the collector recorded a false `pin_broken` and dropped the
   day's point. False breaks grew 2 → 10/day over six days, concentrated exactly on the
   most active systems (vllm, cline, sglang, pydantic-ai, browser-use). Data loss is
   monotone in release activity — the axis was structurally biased AGAINST the systems
   it exists to measure.
3. Day-16 shadow numbers, recorded for the archive (not the grounds for termination):
   criterion 1 projected PASS (gate-capable 23 → 47, threshold >= 30); criterion 2
   marginal fail (pooled within-cohort r(z3, z1) = +0.526, threshold < 0.5, 15 pairs);
   criterion 4 failing (7 of 8 voting cohorts at 0% rising share).

## Decision

- Candidate axis m3-v1 is **terminated as construct-invalid**. The quarantine funnel is
  designed to reject candidates whose measurand is broken BEFORE the statistical finish;
  running out the clock on a known-invalid construct would be rigor theatre.
- **No score, vote, or publication ever derived from v1.** Nothing public changes.
- The 16-day daily series (2026-07-01 → 2026-07-16) is **retained as diagnostic data**
  (`data/observations/*/deps.jsonl`), never scored, tagged by this act. Retention is
  consistent with I5 (capture is append-only insurance either way).
- The identity pin registry (`data/deps_id_map.json`, 41 verified linkage pins) and the
  squatter-purge discipline (21/81 day-1 name-matches were squats) carry forward — they
  are identity infrastructure, not part of the invalid measurand.
- The sensor's false-classification bug (`pin_broken` for "dependents not yet computed
  for a live default version") is fixed as ordinary sensor hygiene: reclassified to
  `version_pending`, no substitute value is ever recorded. Version-substitution
  fallbacks were considered and REJECTED as a silent redefinition of the measurand
  (unanimous three-vendor verdict).

## Named and rejected alternative

*Let v1 run to its pre-registered finish (~2026-07-29) and fail on its own criteria*
(one vendor's position: terminating early "for drama" spends the funnel's procedural
credibility). Rejected because: the grounds here are semantic, not statistical — the
measurand itself changed identity between observations; discovering this and continuing
to accumulate would itself be a form of theatre, and a marginal accidental PASS
(measurement error can push r below 0.5 without improving validity) would be worse than
a clean termination. Revisit trigger: none — a per-version signal may re-enter the
funnel only as an explicitly different candidate (e.g. release-diffusion velocity:
dependents at fixed release age), never as "v1 resumed".

## Successor

A package-level candidate (**m3-v2: unique direct dependent packages across all
versions, single BigQuery `SnapshotAt`**) enters the funnel as a NEW candidate with its
own pre-registration and its own full clock: see
`QUARANTINE-m3-deps-axis-v2-PREREG.md`. Capture for v2 begins only AFTER its protocol
is committed (pre-registration precedes data, per the provenance-quarantine rule).

*Positive-only note: this act concerns internal methodology governance; no negative
signal about any measured system is published or implied.*
