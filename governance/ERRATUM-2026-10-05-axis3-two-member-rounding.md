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
`evaluate_axis3_v2h1._robust_z(..., exact_pair=True)` returns z = 0 for both members of a
two-member cohort whose sizes differ — the exact result, with no tolerance. Cohorts of three or
more and two members of the same size are untouched (a review on 2026-10-05 showed that a
residual tolerance would also zero real, nearly collinear residuals in larger cohorts).
Regression tests: `tests/test_evaluate_axis3_v2h1.py::test_two_member_cohort_rounding_residue_is_zero`
(red when the flag is ignored) and `::test_exact_pair_leaves_larger_and_same_size_cohorts_alone`.

The flag is off in scoring. Methodology m4 (effective 2026-10-10) is pinned to code commit
514beb6c0, which carries the old arithmetic, and a published registry row is frozen
(METHODOLOGY-VERSIONING.md, rules 2 and 4). The corrected arithmetic therefore ships as its own
PATCH version, planned from the 2026-10-17 snapshot; until then two-member cohorts keep the
platform-dependent value, and the m4 snapshots it touches will be listed in that version's
record. On a platform other than the one that built a snapshot, `score_m3.py --verify` can show
this drift for such a cohort.

## Not changed
The m4 estimand and formula text; thresholds; the published 2026-09-19, 2026-09-26 and
2026-10-03 snapshots, cards and history rows.
