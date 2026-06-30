# Evidaxis — LAYER-B-PLAN v2 (HARDENING SPRINT, post spar-24)

> v1 (6 parallel research workstreams) SUPERSEDED by spar-24 (MiniMax M3 + Kimi K2.6, blind, convergent):
> it was Big Design Up Front. Layer B is a **hardening sprint to a frozen n=200 baseline**, NOT a research
> campus. The big signal research comes AFTER the freeze, where it enriches instead of blocking.
> Synthesis: `AI Second Brain/lab/consilium-log/work/2026-06-30-spar-24-evidaxis-layer-b-plan/`.

## What spar-24 changed (v1 -> v2)
1. Facts/judgment split was false + single-model fan-out is a monoculture echo chamber -> judgments
   (gameability, independence, leading-vs-lagging, China coverage) go to a DIVERSE council (>=2 model families).
2. Order inverted: universe + STRATA (the denominator) come FIRST, not parallel to signal-inventory.
3. The spine may not be signal-agnostic (scalar assumption) -> verify against the real spec before freezing.
4. Missing critical-path work: Entity Resolution at scale + a pre-fame falsifiability backtest.
5. 6 research workstreams = over-engineering -> shrink to a hardening sprint; defer the 100-signal survey.

## Phase order (cheap-correct first -> build -> enrich)

### PRE-BUILD (cheap; each GATES the build)
- **#0 Falsifiability backtest** (GO/NO-GO, first, cheapest): on ~50-100 now-famous systems (2020-2023), did
  velocity-of-change actually LEAD fame? If not, the pre-fame thesis is unfalsifiable -> rethink before building.
- **#1 Universe + STRATA**: catalogs (HF/OpenAlex/PwC/ecosyste.ms/deps.dev/CN), inclusion rules, the
  denominator, and strata (model-type x domain x **geography incl. China**). This is the denominator everything
  else needs. China assessed via diverse council, not single-model autopilot.
- **#2 Entity-Resolution test**: fuzzy ER on 500 mixed-catalog raw records; report precision/recall BEFORE
  freezing opaque-IDs. Architectural gate on the irreversible spine (echoes spar-23 prospect-id/dedup).
- **#3 Signal topology check (top-10, NOT 100)**: only enough to (a) confirm the spine is signal-agnostic for
  the topology classes that matter (scalar / graph / discrete-event / sampled-stream), (b) avoid adding a
  known-bad axis. Judgment parts (gameability/independence) via diverse council.

### BUILD (gated by the above)
Cohort definition (from strata) -> Spine v3 (with ER / prospect-id) -> gate fix (gate-as-protocol, stratified)
-> **Proving-Run on n=200** (SPEC: selection rules, falsification criteria, success metrics, operating-cost
model at n=200/1000/10000) -> **FREEZE DOI baseline**.

### AFTER FREEZE (background, non-blocking enrichment)
Full signal depressearch (the 100-signal survey, now empirically anchored), signal-combination science,
metrology. These enrich; they do NOT block scaling.

## Method fixes
- FACTS (existence / cost / rate-limit / schema) -> autopilot fan-out. JUDGMENTS (gameability / independence /
  leading-vs-lagging / China) -> DIVERSE council (>=2 model families). No single-model "adversarial self-verify."
- Igor's hour: spent at the council judgments (one bundled ChatGPT 5.5 + Grok Heavy paste set). Zero before that.

## Open verification (before committing v2 execution)
spar-24 claim (б) "spine not signal-agnostic" -> VERIFY against the actual COLLECT-V3-SPEC. Note: one partner
mis-modeled the temporal scheme as introduced/peak/decline; the real scheme is bitemporal
(observed/collected/effective/recorded) and score-as-portfolio is already a vector, so part of (б) is moot.
The real check = are graph + discrete-event signal topologies reservable on the locked primitives.
