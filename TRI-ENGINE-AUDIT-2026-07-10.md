# Tri-Engine Audit — Evidaxis (2026-07-10)

> Independent review by three separate AI coding vendors, each on its strength, then
> reconciled and cross-verified by Claude against the real repo + live site.
> · **Gemini 3.1 Pro** (1M-window whole-repo audit) → foundation/architecture
> · **Codex / gpt-5.6-sol** (deep read of `web/` + snapshot data) → code + SEO/GEO implementation
> · **Grok 4.5** (live web + X search) → GEO reality, live-site + competitive
>
> `[✓verified]` = Claude confirmed the claim against the actual code/data (not relayed on faith).
> `[3×]/[2×]` = how many independent engines flagged it (convergence = high signal).
> Every finding here is admissible under CONSTITUTION.md (no author bylines, no winner-lists,
> no predictions, no paid inclusion, no rename).

---

## TIER 0 — FOUNDATION / STRATEGIC (the moat is at risk here)

### F1 · The namesake product is empty by construction — axis-2 (OpenAlex) linkage is broken `[✓verified]` (Grok)
**Where:** entity records / `collectors` OpenAlex resolution; live `rising: 0`, `spine_complete: false`.
**Verified:** vLLM (`vllm-project/vllm`) and AlphaFold3 (`google-deepmind/alphafold3`) both ship
`openalex_work_ids: []`, `axis2: absent` — despite each having thousands of live OpenAlex citations.
**105 / 135 entities (78%) have empty `openalex_work_ids`.** The two-axis convergence gate therefore
almost never fires, so "observatory of *rising* systems" currently records ~zero rising systems.
**Why it matters:** This is measurement *incorrectness*, not "coverage later." Incumbents without axis-2
poison cohort z-scores and make the gate look stricter than reality. The 10–15yr moat is a trustworthy
record of *rising* — right now it's a velocity-only pilot with an unfireable gate. An LLM that trusts the
methodology correctly concludes "nothing is rising," then has little durable fact to re-cite.
**Fix:** One-shot OpenAlex resolution pass for all entities (title/repo → work-id, human-reviewed
allowlist), incumbents first; re-emit a **new** snapshot (no silent rewrite); publish a coverage ledger
(linked / insufficient / absent / no-paper); surface axis-2 coverage % on homepage + every snapshot.
Do **not** weaken the gate to manufacture "Rising."

### F2 · Claim-URN / snapshot_id collide across distinct published snapshots `[✓verified]` (Codex)
**Where:** `web/src/lib/claim_urn.ts:43-45`, `data/snapshots/2026-07-03` vs `2026-07-04`.
**Verified:** Jul-3 and Jul-4 **share the identical** `snapshot_id: f1f2495d518d`, `period: 2026-w27`,
`methodology: m2` — but hold **133 vs 135 entities** and changed scores (LeRobot 51.4 → 54.0). The URN is
built from (period, methodology), so the *same URN names two different assertions*, and `snapshot_id` is
clearly **not** content-addressed.
**Why it matters:** This is the single deepest technical breach of the core promise ("a URN names one
dated assertion under one method"). Every citation baked by an LLM this week is ambiguous.
**Fix:** Mint URNs with the `snapshot_date` epoch (already in the data), not `period`; make `snapshot_id`
a content hash of the canonical snapshot; publish an erratum mapping existing collisions; fail the
build when either identifier maps to >1 payload hash.

### F3 · Historical snapshots & retired systems are not built → "permanent" URLs 404 `[3×] [✓verified]` (Codex + Grok + Gemini)
**Where:** `web/src/pages/snapshots/[date]/*`, `web/src/pages/e/[id]/*`.
**Verified:** `data/snapshots/` has 4 dates (06-27, 07-01, 07-03, 07-04); `dist/snapshots/` has **only
2026-07-03**. The build generates only the *latest* snapshot + latest entity set. Grok confirmed live:
the indexed genesis URL `/snapshots/2026-06-27/` is a **live 404** while still in Google; `/snapshots/`
index 404s. Systems present Jul-3 but absent Jul-4 (ComfyUI, TensorRT-LLM) lose their "stable" pages.
**Why it matters:** Directly contradicts Invariant 4 (append-only, never-rewritten, addressable). Soft-404s
on frozen URLs attack the whole trust story and strand LLM citations that stored the old URL.
**Fix:** Parameterized archive loader: build a route for every `data/snapshots/*`; build entity routes
from the **union** of all historical IDs; render retired systems as preserved `superseded` records, never
delete their URLs; add a `/snapshots/` index listing every frozen date + hash. Every published snapshot
must stay `200` forever (or 301 to its Zenodo deposit).

### F4 · Person handles leak into the CC0 archive (irreversible Invariant-1 breach) `[✓verified]` (Codex)
**Where:** `github_repo` field flowing into `web/src/lib/data.ts`, JSON twins, JSON-LD `sameAs`, HTML.
**Verified present on the public surface:** `paul-gauthier/aider`, `gcorso/DiffDock`, `jwohlwend/boltz`,
`PeterGriffinJin/Search-R1` — all **personal** GitHub accounts. The person-free CI (`field_policy.py` +
`tests/test_field_policy.py`) scans provenance objects for `login`/`avatar_url` keys, but the whitelisted
`github_repo` *slug itself* carries a natural-person handle and is published verbatim.
**Why it matters:** Invariant 1 is fail-closed precisely because "the first leak into a CC0 DOI is
irreversible." This is that leak, and the existing guard does not catch it.
**Fix:** Classify repo ownership (org vs individual) before publication; on public surfaces replace
personal `owner/repo` with a stable numeric repo ID (or the system's display name only); extend the build
guard to scan every generated HTML/JSON slug against an approved-organization registry, not just Person nodes.

### F5 · Momentum ranking = "ranking of winners" — collides with positive-only / no-ranking `[2×]` (Codex + Grok)
**Where:** `web/src/components/RankTable.astro`, `web/src/pages/index.astro:193`, `web/src/pages/llms.txt.ts` (list "ranked by momentum").
**Problem:** The site assigns ordinal ranks to *every* tracked/single-axis/calibration system and ships a
momentum-ranked machine list. The Constitution says Evidaxis "publishes… **no ranking of winners**" and is
positive-only ("nobody is ranked last").
**Why it matters:** A momentum leaderboard as the primary human + machine surface is, in substance, a
winners' ranking — the thing the anti-roadmap forbids. Two engines flagged it independently. (Two-sided
read: you may argue momentum ≠ winner-prediction — but the *ordinal* rank of all systems is the exposure.)
**Fix:** Drop ordinal `rank` columns/props; default lists ordered alphabetically or by cohort, not by a
global momentum ladder; a separate **unranked** positive-recognition section for systems that clear the
gate; `llms.txt` leads with status counts (`rising:0, watch:N`), not a momentum ladder. **Adjudicate this
one first** — it's a constitutional question, not a code nit.

### F6 · Zero external entity graph → LLMs have no reason to retrieve/cite Evidaxis `[✓verified]` (Grok)
**Where:** off-site grounding surface.
**Verified live:** Wikidata "Evidaxis" = **no item**; HF `huggingface.co/evidaxis` = **0 datasets/0 models**;
Zenodo DOI ≈ **2 views / 1 download**; GitHub `evidaxis/evidaxis` = **0★**; X `@evidaxis` = **0 followers**;
category queries ("rising open-source AI systems", "AI momentum tracker") surface OSSInsight / Star History /
Epoch / GitHub-Trending — **never Evidaxis**.
**Why it matters:** Excellent on-site `llms.txt`/JSON-LD/crawl-openness only help *after* something decides
to fetch you. In 2026 generative engines ground institutions via Wikidata/Wikipedia KG, training-adjacent
repos (HF datasets, Zenodo, arXiv), and third-party "according to X" mentions. Evidaxis has ~none.
**Fix (constraint-safe, highest GEO leverage):** (1) Wikidata item — type = data catalog / research project,
official site, DOI, GitHub, HF, CC0, **no person claims**; (2) publish `evidaxis/momentum-snapshots` on HF
(weekly parquet/JSON of the CC0 data); (3) deposit the current m2/133 corpus as a new Zenodo **version**
(not only the 19-system genesis zip); (4) methodology technical note (institutional author "Evidaxis");
(5) PRs into 2–3 public-**dataset** hubs (awesome-public-datasets, research-data lists) as a dataset, not a
"best tools" list. This is the biggest single GEO win and it's all off-site.

### F7 · Canonical DOI points to the wrong corpus `[2×] [✓verified]` (Codex + Grok)
**Where:** `web/src/pages/snapshots/[date]/index.astro:27`, `about/index.astro:41`, `web/src/lib/jsonld.ts`.
**Verified:** DOI `10.5281/zenodo.21076012` resolves to the **genesis 19-system m1 seed**; the live site is
**m2 / 133 / 2026-07-03**; yet snapshot pages say "cite this deposit" pointing at the genesis DOI.
**Why it matters:** Anyone (or any LLM) following "how to cite" gets the wrong epoch, wrong N, wrong method —
which destroys the long-horizon citability the DOI exists to provide.
**Fix:** Version Zenodo per published snapshot (concept DOI + version-per-week); About/snapshot footers say
"genesis DOI = seed coverage map; current snapshot DOI = this week's bundle"; put both in JSON-LD `identifier`.

### F8 · The advertised verification chain isn't actually downloadable (Codex)
**Where:** `web/src/pages/snapshots/[date]/*`, `web/src/lib/jsonld.ts:277`.
**Problem:** Snapshot surface ships only `index.html` + `snapshot.json`. No `manifest.json`, `provenance.json`,
`SHA256SUMS`, or archive-root is downloadable or exposed as a Dataset `distribution`.
**Why it matters:** "Every score checkable against hash-pinned inputs" is unfollowable by an auditor or LLM.
**Fix:** Emit immutable routes for each snapshot's manifest/provenance/checksums/integrity-root; link them
from the page + `llms.txt`; describe each as a named `DataDownload` in the snapshot JSON-LD.

### F9 · Point-in-time leakage: future observations bleed into past snapshots `[2×]` (Codex + Grok)
**Where:** `web/src/lib/data.ts:155-165,196-208`; also 26 live entities still carry `not-yet-deployed` notes.
**Problem:** Adoption fallback + history series select observations *after* the snapshot being rendered
(a Jul-4 snapshot can show week-28 data captured Jul-6; Diffusers deps 412 → 416).
**Why it matters:** The entire product claim is *non-reconstructable point-in-time* fidelity; leaking future
data into a past snapshot is the one thing the archive must never do.
**Fix:** Filter every fallback/trend row by `captured_at <= snapshot.captured_at`; add a regression test where
future history exists but must not move an older snapshot; replace free-text `not-yet-deployed` notes with a
structured `provisional`/`batch_id` flag.

---

## TIER 1 — SEO / GEO

### G1 · `llms.txt` optimizes the wrong ranking (Grok) — the main AI entrypoint
Leads with a full **momentum-ranked** list (Cosmos 90.1, Sana 86…), all `single-axis`, with no upfront
"rising: 0." AI agents fetching it treat the ladder as "what's rising." **Fix:** status counts first
(`rising:0, watch:N, axis2_present:13`) → "Rising this period" (empty + why) → catalog (alphabetical/cohort),
not a global momentum ladder. (Also resolves the machine half of F5.)

### G2 · JSON-LD identity + schema-type errors (Codex) `[✓ schema.org]`
(a) A changing weekly measurement reuses the permanent `@id` `/e/{id}/#dataset` → KG consumers merge
different dates/scores/URNs into one node. **Fix:** date-qualified `@id` `/e/{id}/snapshots/{date}/#dataset`,
keep `/e/{id}/#entity` for stable identity, list every snapshot Dataset from the DataCatalog.
(b) `codeRepository` is attached to `SoftwareApplication`/`Organization` (it's a `SoftwareSourceCode`
property) and `hasDefinedTerm` to a `TechArticle` (belongs on `DefinedTermSet`). **Fix:** model the repo as a
`SoftwareSourceCode` node; replace `hasDefinedTerm` with `hasPart`/`about`/`mentions`.
(c) Grok: claim-URN is only in `identifier` PropertyValue, not the `@id` — the shipped "URN as @id" intent is
half-done. Decide whether the URN or the URL is the primary graph key and be consistent.

### G3 · Sitemap & IndexNow gaps `[2×] [✓verified]` (Grok + Gemini)
Sitemap (155 URLs) is missing `/llms.txt`, `/methodology/current/`, the JSON twins, and all snapshot history;
`etl/indexnow.py:12` hardcodes `sitemap-0.xml`, so once the sitemap paginates, later URLs are never pinged.
**Fix:** add the AI/stable entrypoints + all snapshots to the sitemap; make IndexNow read `sitemap-index.xml`
and iterate every child sitemap.

### G4 · `Organization.sameAs` under-linked (Grok)
Live homepage JSON-LD `sameAs` = **only** `github.com/evidaxis`, though X/HF/Zenodo handles exist. GitHub org
`blog`/`twitter_username` are null. **Fix:** expand `sameAs` to X, HF, Zenodo, LinkedIn (if real), + Wikidata
once created; set the GitHub org `blog=evidaxis.org`; add DOI `identifier` on Organization/DataCatalog.

### G5 · Duplicate field/cohort titles cannibalize (Codex)
`/ai/fields/robotics-embodied/` and `/ai/cohorts/robotics-embodied/` both title "Robotics & Embodied AI,
Evidaxis" and share breadcrumb labels; field pages are ~583 chars of extractable text (thin). **Fix:**
disambiguate titles ("…field coverage" vs "…cohort momentum"), qualify breadcrumbs, and either fatten field
pages with dual-axis stats or `noindex` them + drop from breadcrumbs.

---

## TIER 2 — CODE / ARCHITECTURE

- **C1 · Derived signals publish undersampled results as valid `[2×] [✓verified]` (Codex + Gemini).**
  `recencySwing()` reports a hardcoded `priorWindow: 39` (`derived.ts:41,133,159`) even when only ~15 weeks
  exist; `commitChangepoint([])` returns "no significant changepoint" marked *shipped* not *insufficient*.
  **Fix:** return `priorWindow: prior.length`; return `Reserved` for changepoint inputs < 8 points; add
  15-point and empty-series tests.
- **C2 · Shadow axis-3 slope compresses time (Gemini).** `shadow_axis3_deps.py _slope` uses `range(n)` over
  *captured* points, ignoring date gaps → artificially steepened slope. Low blast radius (shadow A/B only),
  but corrupts the candidate-axis test. **Fix:** index x by real ISO-day delta, not `range(n)`.
- **C3 · `counts` vocabulary is internally inconsistent (Grok).** `counts.tracked=114` vs status histogram
  (`single-axis:106, tracked:8, watch:7, calibration:12`) — "tracked" means two things in one file. **Fix:**
  publish a closed status enum in methodology; make `counts` a pure `Counter(status)` + separate `axis2_present`.
- **C4 · Per-collector retry/backoff duplication (Gemini).** Each collector hand-rolls rate-limit/backoff.
  **Fix:** one shared `HttpClient` (`requests.Session` + `urllib3 Retry` for 429/5xx) injected into all.
  *(Lower priority — architecture hygiene, not a live defect.)*
- **C5 · "Frozen" methodology pages are partly dynamic (Codex).** `/methodology/v1/` interpolates the latest
  period; 133 entity pages link to a nonexistent `/methodology/current/#derived`. **Fix:** remove
  current-snapshot imports from frozen pages; add versioned anchors for each derived signal.

---

## TIER 3 — VISUAL / PERFORMANCE / A11Y

- **V1 · Homepage weight is a real Core-Web-Vitals + crawl risk `[2×] [✓verified]` (Codex + Grok).**
  `dist/index.html` ≈ **594 KB / ~7,570 elements / 145 inline `<svg>`**; every page also loads a ~274 KB
  Sentry tracing+replay bundle + GA4 + Clarity + PostHog + 2 Vercel scripts. Hurts LCP/INP and bot
  time-to-content on the one page that should rank for the brand. **Fix:** one summary chart + one compact
  table on `/`, move full rows to coverage/JSON twins, lazy-load below-fold charts; Sentry = error-capture
  only (no tracing/replay); keep at most one deferred analytics provider. (Cross-listed: this is also SEO.)
- **V2 · Charts mislabel/mis-plot the gate `[2×]` (Codex + Gemini).** Scatter/Quadrant label `z ≥ 0` as the
  "RISING" region though m2 requires `z ≥ 1` + positive slope + cohort ≥ 5 + commit floor; null z-scores are
  plotted at 0 (median), implying "average" for absent data. **Fix:** drive thresholds/labels from the
  snapshot methodology (shade only from `(1,1)`); exclude null-z entities instead of `?? 0`.
- **V3 · `--citation` token fails WCAG AA (Codex).** ~4.48:1 on white, used for 8–13 px text. **Fix:** reserve
  `--citation` for lines/large text; use `--citation-ink` for normal-size labels.
- **V4 · Data tables lack `<caption>` / `scope` (Codex).** Screen readers + semantic extractors can't bind
  purpose/headers. **Fix:** add captions, `scope="col"`/`scope="row"`; drop tables that only duplicate a JSON twin.

---

## Reconciliation notes (what I dropped or downgraded)
- **Gemini "OTS anchoring is theater" — REJECTED.** `ots stamp` *is* wired in `t2-daily-snapshot.yml` and
  `weekly-snapshot.yml`. Gemini only saw `merkle_root.py` (my file-scope excluded `.github/workflows/` — my miss).
- **Gemini "person-free not mechanically enforced (fix at TS serialization)" — DOWNGRADED.** It *is* enforced
  in the Python pipeline (`field_policy.py` + CI). The real leak is narrower and different (F4, via repo slug).
- **Gemini "entity-id rename orphans history" — kept as a latent risk, not a live bug.** `mint_entity_id` is a
  deterministic SHA-256 of `github_repo`; there's an `id_map.json` indirection, but no rename/alias mechanism,
  so a transfer/rename will orphan history. Add `spine/aliases.json` when it first happens.

## Suggested execution order (highest leverage first)
1. **F1** — fix OpenAlex linkage, re-publish a snapshot (makes the gate real; unblocks the entire product).
2. **F6** — Wikidata + HF dataset + Zenodo version (off-site grounding; biggest GEO win).
3. **F2 + F3** — content-address snapshot_id, mint URNs on date, build all snapshots + retired entities.
4. **F4** — stop leaking person handles (irreversible if left).
5. **F5** — adjudicate the momentum-ranking / positive-only question, then de-rank surfaces + G1 `llms.txt`.
6. **F7 / G2 / G3 / G4** — DOI + JSON-LD identity + sitemap/IndexNow + sameAs.
7. Tier 2/3 as fill-in.
