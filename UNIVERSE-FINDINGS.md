# Evidaxis — Universe + Strata findings (sprint job #1, 2026-06-30)

> Source: ultracode workflow `evidaxis-universe-strata` (7 agents over 6 catalogs + synthesis).
> Full raw output in the run task file. This is the digest feeding Phase U + the discovery-frontier-manifest.
> Judgment points (China/geography boundary, what-counts-as-a-system) are FLAGGED for a diverse council.

## Universe size (as-of 2026-06-30)
- RAW catalog rows: ~10^6-10^7 (HF ~2.87M model repos, ModelScope ~219k, Gitee AI ~22k, GitHub topic:ML ~212k, OpenAlex ~19.4M AI/ML works) — dominated by derivative/long-tail inflation.
- DISTINCT BASE systems (after collapsing fine-tunes/LoRA/quant/merges): ~10^5.
- NOTABLE / ADMISSIBLE public universe (per-stratum floor + full-cycle gate): **~10^3-10^4** (convergent across surveys).
- Frontier/flagship: ~10^2 (the ~100 base families carrying ~half of all downloads).
- **Plan budget**: dedup/ETL/maintenance around ~10^3-10^4 PUBLIC systems on top of a ~10^5 base-system PRIVATE discovery-frontier, weekly, always "as of DATE", snapshots immutable.

## Inclusion rules (v0, to version in universe.md)
1. **Entity-type whitelist**: a System is one of {org, repo, model, product, lab}. person never scored. Datasets/benchmarks/methods/papers/packages are evidence/edges, NOT Systems.
2. **Base-not-derivative**: count a weight-repo only if it has NO base_model parent. Fine-tunes/adapters/quant(GGUF/AWQ/GPTQ)/merges collapse into the parent as evidence (Qwen alone = 113k+ derivatives).
3. **One full cycle before public**: a System is public only after ≥1 full accession→…→manifest cycle (incl. honest "no signal"). Raw rows stay in the PRIVATE frontier. Kills the vanity-dump.
4. **Inclusion IS ranking**: every field/source/ID/threshold choice is a value-choice frozen in the DOI. Versioned, published "as of DATE", with per-stratum coverage-bias report. No "neutral census".
5. **Drop non-System rows BEFORE a permanent ID**: ~30% of catalog "systems" are datasets/mirrors/redirects → filtered at prospect-id, never get a permanent opaque-ID (minting one = irreversible baseline poison).
6. **Sibling-node code vs weights**: GitHub code repo and the weights hub (HF/ModelScope) are SIBLING nodes of one System, not parent/derivative. For CN labs: GitHub=code, ModelScope=native weights; do not treat GitHub as canonical.
7. **Closed/commercial in-scope via evidence path**: GPT/Claude/Gemini/ERNIE/Spark etc. enter as product/model via paper/announcement/registry evidence, flagged low-coverage (so the universe is not silently open-weights-only).
8. **Positive-only firewall on admission**: per-system exclusion reasons internal; only AGGREGATE per-stratum coverage_pct + exclusion counts publish.
9. **Activity-floor is per-stratum protocol, not a global star threshold**: stratified percentiles within each cell (global stars>=N badges big LLMs, buries niche/non-English). Floor protocol versioned in the DOI.

## Strata (the gate normalizes WITHIN a cell)
- **model-type** × **domain** × **geography** (3 declared) + **era/cohort-window** (4th, bitemporal frozen_as_of).
- model-type: {foundation/base · fine-tune-family-head · multimodal · embedding/retrieval · agent/framework · ML-library · application-product · lab/org}.
- domain: {NLP/LLM · vision · audio/speech · multimodal · robotics/embodied · RL/decision · tabular · code-gen · science/bio · agents/tooling}.
- **geography (LOAD-BEARING, 4 buckets)**: {NA+EU(Western) · China(CN-native) · rest-of-Asia · Other}. CN is its own stratum because DeepSeek/Qwen/GLM/Yi/Kimi/MiniMax publish NATIVELY to ModelScope (often before/without an HF mirror); a Western-only crawl under-sees the CN cell. Origin derived from lab-org + native-hub provenance, NOT from mirror presence.
- Asymmetry guard: cells need not be equal-size; gate normalizes within each non-empty cell; thin cells publish coverage='weak/absent' as aggregate, never a per-system gap.

## Dedup strategy (two-stage, feeds spine prospect-id)
- STAGE 1 — **prospect-id** (TTL ~30d), BEFORE any permanent ID: every catalog row is a transient prospect; cross-catalog fuzzy dedup here so non-Systems/duplicates never get a permanent hash-ID.
- STAGE 2 — **permanent opaque accession-ID** (hash-based) minted only after entity-type + base-not-derivative + dedup clear; later merge/split = signed identity_correction_event with tombstone.
- **JOIN-KEY precedence (strong→weak)**: (1) weights content-hash (HF blob-sha ↔ ModelScope safetensor.sha256) — best cross-HUB key, catches native dual-publish; (2) Gitee mirrorUrl/mirrorNamespace (free provenance pointer: non-null⇒rehost, null⇒native); (3) arXiv ID (best cross-CATALOG anchor); (4) DOI (academic bridge); (5) PURL→normalized host/owner/repo (package layer).

## Judgment points flagged for the diverse council (the keeper's hour)
- The geography bucket boundaries + what "CN-native" means (freezes into DOI strata).
- "What counts as a System" edge cases (agent-framework vs product; closed-model evidence path).
- The per-stratum activity-floor protocol (before it freezes in the DOI).
Note: the spar dyad MiniMax M3 + Kimi K2.6 are themselves CN-corpus models = exactly the China-aware diversity spar-24 demanded.
