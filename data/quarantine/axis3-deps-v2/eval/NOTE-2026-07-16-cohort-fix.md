# Dated note: evaluator cohort-resolution bug fix (2026-07-16, same day as baseline)

The first baseline artifact (`baseline-2026-07-16-c282c7b74bd8.json`) was computed with
every entity collapsed into cohort "unknown": `cohort_map()` read seeds.json, which does
not carry entity-level cohorts (the taxonomy authority is the project snapshot). This is
a code bug in the evaluator, not a criteria change: within-cohort z was always the fixed
semantics (PREREG §1). Fix: cohorts resolve from the newest project snapshot <= --as-of.

Per the supersession's change discipline this note records the repair. The live floor
had NOT started (zero live captures), so the "restart live floor" clause is a no-op.
The flawed artifact is retained in git history; the corrected artifact supersedes it.
