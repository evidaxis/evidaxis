# Gate ETA is not published (2026-09-23)

> status: FIXED 2026-09-23. Clarifies the reserved derived signal "Gate ETA".

The derived signal "Gate ETA" was described as a "reserved estimate of time-to-
convergence under current slopes", and its reserve reason on cards read "needs
snapshot history (1 snapshot exists)". That wording implies the signal will be
published once enough history accumulates. It will not: an estimate of when a
system crosses the convergence gate is a forward-looking public prediction, which
Invariant 5 rules out ("Evidaxis makes no public actionable prediction").

From this date: template B cards state "Gate ETA: never published; Evidaxis makes no
public actionable prediction." The current methodology page (m3) says the same.
Frozen methodology versions (v1, m2) and template A cards are not rewritten; this
record supersedes their wording. Any internal estimate of this kind is a private,
pre-registered commit-reveal record under Invariant 5.
