# Canary analytic set for the 2026-09-19 clock reset, and what the baseline window revealed

> status: FILED 2026-09-21, two days after the clock start it belongs to · class: experiment
> bookkeeping plus a dated limitation on causal reading · no published value, score, snapshot
> or identifier changes · positive-only: internal methodology governance, no signal about any
> measured system.

## What the amendment required

`CANARY-PROTOCOL-AMENDMENT-2026-09-14.md` fixed the analytic-set rule and said the list "is
computed by code at the reset and committed". The 2026-09-15 addendum in
`AXIS3-DEPS-V2H-LIVE-LOG.md` made it concrete: pull weekly Google Search Console impressions
for the 48 canary URLs over the baseline window, keep pairs where both pages averaged at least
one impression per week, and commit the list before any post-reset impressions are read.

## Clock start, established from the deployment record

**2026-09-19T11:23:39Z**, the `deploy-web` run on commit `17a3513b` (conclusion: success). That
is the first production deploy rendering the 2026-09-19 snapshot, so it is the moment both arms
began to be served by the same site version. The six-week verdict date is **2026-10-31**.

## The list

`web/src/data/canary-analytic-set-2026-09-19.json`. Window 2026-08-20 to 2026-09-18 inclusive,
30 days, 4.2857 weeks, so the per-page threshold is 5 impressions. Source: property
`sc-domain:evidaxis.org`, `searchAnalytics` by page, type web. No data after the clock start was
requested when building the list.

**Analytic set: 6 pairs of 24** (pairs 0, 2, 7, 10, 11, 19). The remaining 18 pairs stay live and
are reported as non-analytic, per the amendment.

The list was computed two days late. The window it uses is closed and lies entirely before the
clock start, so lateness did not let outcome data influence the selection. The delay is recorded
here rather than smoothed over.

## Two facts the pull surfaced

**1. The analytic set collapsed between the assignment window and the baseline window.** Under
the same threshold, all 24 pairs would have qualified on the assignment window
(2026-07-22 to 2026-08-18). Six qualify now. Site-wide the baseline window holds 991 impressions
across 142 pages. Six pairs are six units of analysis; further weeks add precision, not
independent pairs.

**2. The treatment arm drifted down relative to control.** Arm totals, treatment against control:
1.32 on the assignment window, 0.89 on the baseline window. Excluding pair 0, whose treatment page
fell from 221 impressions to 99: 0.95, then 0.63. The pairwise view is weaker than the totals. The
treatment share of pair impressions fell in 17 of 24 pairs, two-sided sign test p = 0.064, median
share 0.500 to 0.333.

## Whether that drift is the shell or regression to the mean

Assignment sorted pages by impressions and alternated arms, so the first-listed page of each
adjacent pair went to treatment on even pair indices. Regression to the mean therefore predicts
the initially higher page weakening whichever arm it sits in. Splitting all 24 pairs by who led at
assignment:

| group | n | T/C at assignment | T/C at baseline | shift |
|---|---|---|---|---|
| treatment led | 6 | 2.07 | 1.54 | 0.74 |
| control led | 7 | 0.85 | 0.30 | 0.35 |
| tied | 11 | 1.00 | 0.71 | 0.71 |

Regression to the mean predicts a shift below 1 where treatment led and above 1 where control led.
The observed shift is below 1 in every group, which does not fit it. But the tied group is the one
where regression predicts nothing, and there the pairwise signal disappears: treatment is lower in
7 of 11 pairs, p = 0.549. The group totals are carried by two control pages (12 and 28
impressions) out of eleven pairs.

**Reading, stated as a limit rather than a result: these data cannot separate a shell effect from
regression to the mean.** The whole-set sign test sits at p = 0.064 and the regression-free
subgroup does not reproduce it. Alternating assignment is not randomisation, so neither reading is
causal. Nothing here is grounds to revert or to scale the shell.

## The structural defect this exposes, named and not patched

The baseline window used for normalisation lies entirely inside the period when the treatment was
already live (since 2026-08-20). A stable multiplicative effect of the shell therefore cancels:
normalising each page by its own mean over a window that already contains the effect leaves
`kY/kB = Y/B`. The primary metric measures post-reset relative dynamics, not the shell's level
effect. A null result at the verdict is consistent with a steady benefit and with a steady harm.

Compounding it, the analytic set is selected on impressions measured after the treatment went
live, so pages the shell may have depressed are the ones most likely to fall below the threshold.
Selecting on a post-treatment variable is a known bias, and pre-registering the rule does not
remove it.

**The protocol is not being changed here.** It was already amended once, and amending it again
after seeing baseline data is how experiments stop meaning anything. The list is committed exactly
as the fixed rule computes it. What changes is the reading: the 2026-10-31 verdict is hereby
limited to relative post-reset dynamics on six pairs, may return "indeterminate", and is not
evidence of the shell's safety or benefit. A level-effect analysis needs a true pre-treatment
baseline (before 2026-08-20) and, if run, is a separate retrospective record, not this verdict.

*Named and rejected: (i) relaxing the threshold to recover pairs, which is choosing a rule after
seeing which pairs it admits; (ii) re-baselining on the pre-2026-08-20 window inside this verdict,
which swaps the registered metric post hoc; (iii) calling the experiment now on a p = 0.064 that
the regression-free subgroup does not reproduce.*

*Second opinion: Codex (consult, blind to the position above) returned REVISE at 0.96, naming
post-treatment selection bias and supplying the group split reproduced here. Its recommendation to
commit the list exactly as computed, keep the verdict date, and bound the causal reading with a
dated note is what this record does.*
