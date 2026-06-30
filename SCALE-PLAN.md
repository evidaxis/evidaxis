# Evidaxis — SCALE-PLAN v2 (post spar-23)

> created: 2026-06-30 · v1 built via deep-reasoning · **v2 = hardened by spar-23** (MiniMax M3 + Kimi K2.6,
> blind dyad, $0.057). Synthesis: `AI Second Brain/lab/consilium-log/work/2026-06-30-spar-23-evidaxis-scale-plan/`.
> status: proposed, awaiting Igor go to execute.
> Igor strategic input: a 19-system site looks trivial; coverage pace must exceed the market birth-rate.

## What the spar changed (v1 → v2)

The spar **broke v1's frame** on five convergent points (both models, blind, agreed). v1 is superseded:

1. **No "thin vs full spine" split.** Identity-correction-events carry hidden valence; in append-only git you
   cannot back-fill it → "zombie IDs." Build the spine ONCE (COLLECT-V3-SPEC was right). [v1 thesis 1 killed]
2. **Bulk catalog ingest poisons ONTOLOGICALLY.** ~30% of catalog "systems" are datasets / weight-mirrors /
   redirects; raw-custody-hash does not guard mutation INSIDE the catalog. Minting permanent IDs for them
   poisons the baseline forever. [v1 thesis 2 killed]
3. **Inclusion IS ranking.** There is no neutral coverage layer; field/source/identity/ID choices are
   value-choices frozen into the DOI. The "survey telescope = neutral census" framing was false. [frame killed]
4. **No static gate threshold in the DOI.** `cohort≥5` kills the pre-fame signal that IS the product; `z≥1`
   on heterogeneous cohorts badges big LLMs and never niche tools → the DOI documents LLM dominance. [v1 thesis 3 killed]
5. **No raw public 40k survey.** Two-class public system + vanity ("re-indexed someone's catalog, found
   nothing") + spam incentive ("digital ghetto"). [v1 order killed]

**Igor's instinct survives, refined:** you DO need WIDE observation to catch pre-fame risers, but it lives in
the PRIVATE discovery-frontier (watch many cheaply), and the PUBLIC surface shows only fully-cycled systems.
"Pace > birth-rate" applies to OBSERVATION, not to the public count. The site stops looking trivial via
"N fully-observed systems across M cohorts, as of DATE, growing weekly", not via a raw dump.

## The revised plan (v2)

| Phase | What | Owner |
|---|---|---|
| **C — Cohort definition** | Define the cohort as explicit strata (model-type × domain × era). The gate computes z against cohorts, so "average" must be defined before "above average". Output: versioned cohort taxonomy. | Claude |
| **G — Gate as protocol** | Freeze the gate's VALIDATION PROTOCOL in the DOI, not a threshold. Gate is versioned v1/v2/v3, each referencing the protocol (kills citation-hazard, allows tightening back). Rising stays POSSIBLE in small cohorts behind a higher evidentiary bar / human-confirm (do not kill the pre-fame signal). Stratified percentiles, not mixed-cohort median. Public coverage-bias report per stratum. | Claude |
| **U — Universe (dated-snapshot service)** | NOT a one-time phase. Freeze `universe.md` v0 BEFORE any ingest >19: sources + inclusion rules + per-release snapshot DATE + invalidation-events (past snapshots immutable; correction → new dated snapshot) + **maintenance budget** (cost ceiling + FTE/automation). Denominator always published "as of DATE". | Claude + research |
| **S — Full spine v3** | The WHOLE COLLECT-V3-SPEC (not split). New mechanisms from the spar: **prospect-id (TTL ~30d) + cross-catalog fuzzy dedup BEFORE minting a permanent opaque-ID** (this is what lets us observe widely without poisoning the ID space); **coverage stores the minimal set only** (id, observed_at, source, type, custody_hash) with mutable metadata as scoring adapters (explicit re-sync cadence + upstream-schema version); **reserved `valence_stub` + `instrument_ref` (nullable) on identity-correction-events** for forward-compat. | Claude (TDD) |
| **PR — Proving-run on pilot n=200** | Full cycle on a 200-system pilot cohort (not 10/19): accession → instrument → observation → edge → outcome → manifest, green repro-CI, frozen baseline. PLUS mandatory **COST/QUALITY + anti-gaming report** (% derivative, % dupes, % noise, annual $ + FTE, fork-explosion collision test on synthetic 1k forks). Fail → stop, S-scaling does not start. (10-system smoke-test stays as the cheap dev gate during build.) | Claude, gated |
| **SC — Pipeline scaling** | Scale system-by-system / batch through the full cycle. PUBLIC surface shows only systems that passed ≥1 full cycle (incl. honest "no signal"), killing the vanity ghetto + spam incentive. WIDE observation lives in the private discovery-frontier (where "pace > birth-rate" applies). | Claude, auto |
| **V — Signals (ongoing)** | Signal-inventory depressearch runs PARALLEL as research → queue to add axes through the convergence gate. "Replenish models" lives here. | Claude dispatches, Igor nods |

## Heartbeat (parallel, non-blocking)
`.github/workflows/weekly-snapshot.yml` written. Cloud GitHub Action, laptop-independent. Interim: weekly
provisional re-snapshot (reclass_pre_spine.py). Activates on push to GitHub. Re-pointed at the full-cycle
refresh once S/PR land.

## Open for Igor
- Go to execute (start at Phase C). I run it; research-heavy phases (U, V) use ultracode fan-out.
- Optional: a third independent break (manual ChatGPT 5.5 + Grok Heavy on the v1 position) before locking v2.
  Recommendation: skip; the dyad's kills were convergent and append-only-git-grounded, not opinion.
- Maintenance budget is now an explicit plan input (the spar insisted): at scale, who/what pays for
  compute + reconciliation. Default: automation with a hard cost ceiling + degradation policy. Confirm later.
