# Erratum: axis-3 cohort z in two-member cohorts was rounding residue (2026-10-05)

> status: FIXED forward 2026-10-05; published snapshots are not rewritten.
> Relates to: METHODOLOGY-VERSIONING.md (errata), governance/AXIS3-DEPS-V2H-LIVE-LOG.md (tact 2026-10-05),
> governance/METHODOLOGY-M4-2026-10-04.md.

## What was found
`collectors/score_m3.py --verify` reported DRIFT for the 2026-10-03 snapshot on a Mac (Python 3.12
and 3.14, clean clone, TZ=UTC, any hash seed) and "files match" on the CI runner (Ubuntu, Python
3.12) at the same commit 97c957148. One value differed: Kokoro-82M (`e_MB6DQ5PDDKH`), axis-3
`cohort_z` -0.674 published, 0.0 on the Mac.

## Cause
Axis 3 residualizes each system's slope on log1p(latest dependents) within the cohort, then takes a
robust z (median, 1.4826 x MAD). In a cohort with exactly two scored systems the line passes
through both points, so both residuals are zero in exact arithmetic and the z of both is 0
(`scale == 0`). In floating point the residuals are zero or differ by about one unit in the last
place, depending on the platform's `log1p`. A one-ulp difference makes the MAD equal to that
difference, and the lower system gets exactly -1/1.4826 = -0.674. Reproduced by moving one input
by one ulp (`math.nextafter`): the result is the published pair (-0.674, 0.0).

## Published values affected (m3 snapshots)
| snapshot | system | axis-3 z published -> exact | momentum published -> exact |
|---|---|---|---|
| 2026-09-19 | Kokoro-82M `e_MB6DQ5PDDKH` | -0.674 -> 0.0 | 46.0 -> 50.2 |
| 2026-09-26 | Diffusers `e_9VRK70WNP96` | -0.674 -> 0.0 | 61.9 -> 66.2 |
| 2026-09-26 | Browser Use `e_1GSH6ZQHW7B` | -0.674 -> 0.0 | 36.1 -> 40.3 |
| 2026-10-03 | Kokoro-82M `e_MB6DQ5PDDKH` | -0.674 -> 0.0 | 46.6 -> 50.8 |
| 2026-10-03 | Browser Use `e_1GSH6ZQHW7B` | -0.674 -> 0.0 | 34.5 -> 38.7 |

Within-cohort percentiles of these systems and of their media-generation neighbours shift
accordingly (for example FLUX.1 on 2026-10-03: 36 -> 29). No `rising` flag, status or Rising list
changes: an artifact z is never positive, and axis 3 rises only at z >= 1. Cohorts with three or
more scored systems are not affected: on the 2026-10-03 inputs the fix changes one record of 48
(Browser Use), and every other record is identical.

## Fix
`evaluate_axis3_v2h1._robust_z(..., snap_residue=True)` counts a residual within 1e-9 of the
largest slope magnitude as zero (rounding residue is about 1e-16; a real spread of slopes is
1e-6 or more). `score_m3.axis3_records` turns it on for snapshots dated on or after 2026-10-10,
the first m4 snapshot. Earlier snapshots keep the arithmetic they were published with, so CI
verification of them still reproduces the published bytes on the CI platform; on other platforms
the 2026-10-03 snapshot keeps showing this known drift until 2026-10-10 becomes the latest.
Regression test: `tests/test_evaluate_axis3_v2h1.py::test_two_member_cohort_rounding_residue_is_zero`
(red with the tolerance set to 0).

## Not changed
The m4 estimand and formula text; thresholds; the published 2026-09-19, 2026-09-26 and
2026-10-03 snapshots, cards and history rows.
