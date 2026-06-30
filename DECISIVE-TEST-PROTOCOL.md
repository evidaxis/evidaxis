# Evidaxis — DECISIVE TEST PROTOCOL (v1, hardened by red-team + spar-26)

> The draft v0 retrospective backtest was adversarially red-teamed (9-agent workflow across design-flaw classes,
> grounded in live API checks + the actual repo) and spar-26 (MiniMax + Kimi, blind). Both CONVERGED decisively.
> This v1 records the verdict. status: design-locked conclusion.

## VERDICT: a clean RETROSPECTIVE decisive test is INFEASIBLE (not fixable by windowing math)

This is the THIRD confirmation (n=25 WEAK, n=160 INCONCLUSIVE, and now the design red-team). Root causes, verified:

1. **DATA PROVENANCE (test-invalidating).** The promising R0 predictors (HF derivative/fine-tune-tree, deps.dev
   dependents, downloads) exist ONLY as live 2026 snapshots. deps.dev `GetDependents` has NO point-in-time
   parameter; HF exposes only rolling-30d / cumulative-to-today downloads (no daily history) and rebuilds the
   model tree against the CURRENT population; the HF `base_model` edge has no trustworthy created-at. Confirmed
   against the repo: `etl/collect.py` wires GitHub / OpenAlex / Wayback / Software-Heritage only — NONE of the
   R0 predictor sources are even built, and all snapshots are forward-only/immutable. So a "+90d predictor" read
   off 2026 state IS the outcome (look-ahead with extra steps). No guard fixes this.
2. **SURVIVORSHIP at the sampling frame.** A 2026 query returns survivors; deleted/gated systems 404 with zero
   trace. Outcome (durable-to-2026) and sampling frame (queryable-in-2026) gated on the SAME survival.
3. **CONSTRUCT CIRCULARITY (= autoregression).** R0 predictor and the primary outcome are the SAME measurand on
   a monotone-accreting graph, two timepoints → PPV clears BY CONSTRUCTION. Time-disjoint windows are necessary
   but provably insufficient; construct-disjointness is the missing half.
4. **The "hard-to-game" anchors are the CHEAPEST to forge.** HF `base_model` edges + deps.dev dependents +
   "distinct orgs" are all SELF-DECLARED metadata (one email mints an org; Hub does no weight-provenance check).
   Evidaxis publishes its rule by mission → adversarial 2026 deployment → the test passes on a benign 2022
   cohort exactly where it INVERTS in production → a false GO.
5. Plus: outcomes are attention/ratchet not structure; underpowered (~4-15 true positives, free knobs);
   timeliness unfalsifiable (lead = calendar arithmetic); ER corrupts both sides; CN stratum = structural-zero.

## THE HONEST DECISIVE TEST: FORWARD-ONLY (pre-registered prospective)

Both streams: freeze predictors/outcomes/bars as a timestamped pre-registration NOW, collect predictors
POINT-IN-TIME going forward (the only regime where "as-of DATE" is genuinely captured at observation, per
SCALE-PLAN Phase U), and let the ARCHIVE itself forward-test the prediction over 12-24 months. **The archive IS
the test.** This is exactly the HYBRID posture from consilium-44: continue the archive, treat prediction as a
forward-testable hypothesis, do not make it a public claim. There is no cheap retrospective shortcut.

Hardened forward design (the surviving fixes): construct-disjoint (PREDICTOR = model-derivation graph / builders;
OUTCOME = software-integration + market / integrators-benchmarkers-acquirers); a measured-CONSUMPTION anchor
(unique pullers/orgs, not raw downloads); a Sybil + cost-to-attack layer (org credible only if account predates
entry + has independent prior activity; two DETECT sensors on DISJOINT identity sets); the 5-point ER-FINDINGS
guard (default-deny, prospect-id+TTL, absent-attribute=non-match, ~⅓ human-review band, cluster cap), GO must
survive BOTH ER policies; per-stratum verdicts (CN gets a native-predictor mapping or is reported
INCONCLUSIVE-NO-DATA, claim scoped to Western open-weights); lead-time vs an EXOGENOUS visibility clock; a
sponsorship/raw-org-activity confounder baseline (R0 must beat it, else "transmission" = "a funded org is alive");
full-sample AUC + calibration with ≥25 expected positives + global FDR (BH q=0.10); entry-time on the earliest
IMMUTABLE externally-witnessed timestamp.

## THE CHEAP TEST THAT CAN DECIDE *TODAY* (NO-GO direction only)

A **cost-to-attack / forgery probe**, run now, is legitimately decisive on one sub-question: estimate the real
cost ($ / accounts / GPU-hours / anti-abuse friction, using actual HF/npm/GitHub/ModelScope mechanics) to push
each predictor from median to top-decile. **If the cheapest forgery is below the watchlist's economic value →
NO-GO the public predictive layer IMMEDIATELY on robustness grounds, without waiting for any backtest** — a
public adversarial signal forgeable below its prize is negative-value the day it ships. Given the R0 anchors are
self-declared metadata, this probe will very likely return NO-GO for a PUBLIC predictive product.

## STRATEGIC IMPLICATION (the clarity this produced)

- The **ARCHIVE** is the real, defensible, already-honest product (integrity + longitudinal momentum; site
  already frames it as method-not-prediction). It is sound and shipped.
- The **PREDICTIVE layer** is (a) un-validatable retrospectively, (b) likely gameable as a PUBLIC signal,
  (c) only forward-testable over years. So it must NOT be a public product claim — it lives as an internal
  forward hypothesis the archive tests. This is already the site framing; the red-team confirms it is the only
  honest stance.
- Recommended immediate move: run the cheap cost-to-attack probe (today, low cost) → almost certainly NO-GO the
  public predictive product → lock the archive as THE product, prediction as a labeled forward hypothesis with a
  pre-registered prospective test running on the live archive. No more retrospective backtests.
