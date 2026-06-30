# Evidaxis — pre-fame backtest findings (sprint job #0, GO/NO-GO, 2026-06-30)

> Source: ultracode workflow `evidaxis-backtest-prefame` (28 agents: survivorship-safe sample → real
> GitHub+OpenAlex history per system → adversarial bias audit → verdict). n=25 systems as-of-2021.
> **VERDICT: WEAK-GO.** High confidence in the WEAK-GO call; LOW-moderate confidence the thesis is TRUE.

## What it found
On its face: 64% (16/25) showed early commit-velocity LEADING the fame inflection, leads ~6-52 months. But the
adversarial audit guts the predictive claim and reproduces on independent recomputation:

1. **Survivorship — fatal.** ZERO true negatives. All 6 "faded" systems (AllenNLP, Trax, Acme, Dopamine,
   wav2letter, BytePS) were famous at their 2019-21 peak and only later declined. The population that actually
   tests the thesis (fast-building, NEVER-noticed repos) was filtered out before the test ran. False-positive
   rate unmeasurable. (The survivorship-safe design partially failed: "faded" is not "never noticed".)
2. **Citation-lag confound — 75% of LEADs.** 12/16 LEAD verdicts anchor "fame" to a citation inflection, but
   citations mechanically lag the work 1-3 years. The measured "lead" is largely the citation-lag CONSTANT, not
   predictive velocity. On a non-citation anchor the lead collapses (Jina 5-7mo) or rides an exogenous late-2022
   ChatGPT/RAG wave (Haystack, DeepSpeed), not the repo's velocity.
3. **Fame proxy floats / circular.** Winners dated by first citation jump, faders re-pegged or downgraded;
   7 paperless systems dated by post-hoc web knowledge.
4. **Near-zero lift over base rate.** 76% of the sample is already famous → LEAD precision 81% = only ~+5pt over
   "always say famous." LEAD false-alarms on 50% of faders. Odds ratio 2.17, Fisher one-sided p=0.36 —
   indistinguishable from chance at n=25. And 6/19 famous were "born famous by pedigree" (corporate big-bang,
   flat velocity) — direct counterexamples.

Net: the thesis is NOT refuted (clean builder cases NeMo/DeepSpeed/SpeechBrain/Haystack are genuine), but this
backtest CANNOT establish it as a reliable predictive signal.

## What WEAK-GO means
- The pre-fame PREDICTION claim is **not yet established** empirically. Do not freeze a DOI / public framing that
  asserts proven pre-fame foresight.
- It is consistent with the c-23 / spar-22 repositioning: the moat is the longitudinal momentum + integrity
  ARCHIVE, not a proven prediction. The current honest site framing ("we record momentum, baseline before the
  flare") is on the right side of this.
- To convert WEAK-GO toward a real GO later: a VELOCITY-defined cohort followed forward (includes obscure
  faders), a single PRE-REGISTERED non-citation fame clock (stars/downloads time-series or a fixed adoption
  event), inflection rule frozen before outcomes, n in the hundreds.

## Open strategic fork (-> spar-25)
Given WEAK-GO: proceed-as-archive (claim only what is true, foresight as a forward-testable hypothesis the
archive itself tests) vs pause-and-prove-first vs a better cheap retrospective test before building.

---

## Validation retest (pre-registered, n=160) — 2026-06-30 · verdict: NO clean GO

Ran the improved test (velocity-defined cohort across star bands, non-citation star clock, frozen criteria).
The adversarial verify caught a DESIGN FLAW in my workflow + applied the frozen rule strictly:
- **No clean GO.** Frozen §6: n=160 < 200 -> INCONCLUSIVE-INSUFFICIENT-N (explicitly does NOT default to WEAK-GO;
  declaring GO is itself a goalpost move).
- **My circularity flaw:** I stratified the SAMPLE by star bands, then defined "famous" = stars>=1000 = exactly
  band D. So all 40 famous == band D; the fame proxy became collinear with the sampling band. The frozen PRIMARY
  sampling-weight-corrected analysis was never run; the reported p=0.00085 is the pooled-UNWEIGHTED Fisher, which
  caps the verdict at WEAK-GO at best. (Bias scorecard: survivorship FIXED — 51 true negatives present;
  citation-lag FIXED — star clock; look-ahead FIXED — commits strictly first-365d; fame-proxy NON-circular NOT
  FIXED — my sampling reintroduced it.)
- **New substantive finding (robust):** even directionally, velocity is a LOW-PRECISION predictor. FPR =
  P(not-famous | fast) = 0.64 unweighted (0.64-0.98 reweighted). 2x2: fast&famous 29, fast&not 51, notfast&famous
  11, notfast&not 69. The fast-vs-notfast separation is REAL (risk ratio 2.6x, up to ~15x under natural skew) but
  the precision is low: most fast builders never get famous.

## Net across both tests
Two tests (n=25 WEAK-GO, n=160 INCONCLUSIVE/WEAK) say: velocity-of-change is **real but a weak, noisy,
low-precision** predictor of fame. Neither establishes a reliable predictive signal. **Did NOT resolve the
PAUSE-vs-REFRAME fork.** Per the stated criterion (WEAK again -> consilium), the fork now goes to a consilium.
The genesis DOI is unaffected (it already claims method-baseline, not prediction — verified).
