# Evidaxis — Design Port Plan (approved redesign → production Astro site)

> Status: PLAN ONLY. Build + preview locally. **Do NOT deploy to production until the keeper approves the preview URL.**
> Source of truth for design: `projects/bonsai/evidaxis/proto/{v-final.html, charts.js, data.js, cards/final-card.html}` (in the AI-Second-Brain repo).
> Source of truth for data: `Evidaxis/web/src/lib/data.ts` reading `Evidaxis/data/snapshots/<date>/snapshot.json` + `provenance.json` + `manifest.json`.
> Branch: `redesign/v-final`. Production (evidaxis.org) stays on the current deploy throughout.

Real snapshot (2026-06-27, id `90e607b982fa`, methodology `m1`): **19 entities, 3 cohorts, counts = {rising 0, watch 5, tracked 12, calibration 2, axis2_present 9}**. Cohorts: `robotics-embodied` (Robotics & Embodied AI), `ai-drug-discovery` (AI for Science — Molecular & Drug Discovery), `ai-coding-agents` (AI Agents for Software Engineering). **All "N rising / N watch / %convergence" UI MUST read `snapshot.counts` live — never hardcode the prototype's fictional numbers.**

---

## 1. Architecture — how the approved design maps to Astro

### The one key decision (non-negotiable, PRIORITY #1)
**Every chart in the redesign is rendered as build-time, server-side SVG by an Astro component that reads real data from `data.ts`. Zero chart content is injected by client JS.** The prototype's `charts.js` / `final-card.js` paint SVG at runtime onto empty `[data-ev]` nodes against `window.EVIDAXIS_DATA` — that geometry is invisible to Google's first-pass index and to non-JS AI crawlers (GPTBot, ClaudeBot, PerplexityBot, CCBot). We therefore:

1. **Port the chart geometry math** (scales, paths, jitter, gauge arcs, ring dash math) out of `charts.js`/`final-card.js` into a TypeScript helper module `web/src/lib/charts.ts` (pure functions: `scaleLinear`, `linePath`, `areaPath`, `arcPath`, `beeswarmLayout`, `donutDash`, `gaugeNeedle`, `heatmapCells`, etc.). Pure, deterministic, unit-testable, no DOM.
2. **Build one Astro component per chart primitive** (`.astro` in `web/src/components/charts/`). Each takes typed props, calls `charts.ts`, and emits a complete `<svg>` with all `<path>`, `<rect>`, `<circle>`, **and `<text>` labels/values** at build time. This is exactly the proven pattern of the existing `Sparkline.astro` and the inline convergence SVG in `index.astro`.
3. **Every chart is wrapped in `<figure>` with a real `<figcaption>` AND a parallel machine-readable `<table>` or `<dl>` carrying the same numbers with units** (visually-hidden or inside `<details>` where it would clutter). This is the single biggest GEO lever (audit GAP 1): an LLM reading the raw HTML must be able to read every momentum, z-score, weekly-commit count, and citation-by-year value as text, not infer it from path geometry.
4. **Client JS is optional progressive enhancement only**: hover tooltips, ranking-table sort, entrance reveal. One small deferred ES module (`web/src/scripts/enhance.ts`, target < 10 KB gzip), no framework, no hydration. It layers on top of already-complete static SVG/tables. All entrance animation gated behind `prefers-reduced-motion`. If JS never runs, the page is 100% complete and readable.

### Derived signals (the largest data-gap — decision taken here)
The prototype's "DERIVED SIGNALS" band shows 6 second-order metrics that have **no backing fields** in the snapshot and in the prototype are **seeded-PRNG fakes that cannot ship**. **Decision REVISED by adversarial spar (MiniMax M3 + GLM 5.2, 2026-06-29 — `lab/consilium-log/work/2026-06-29-spar-evidaxis-design-port/`): only signals statistically defensible at the real N may ship; the rest RESERVE with an honest, machine-readable reason — never a number-shaped hole.** Real N per entity: ~52 weekly commit points, ~5 yearly citation points, and only 9/19 entities have a citation axis at all.

- Build `web/src/lib/derived.ts` (pure, deterministic, unit-tested, person-free). Per-signal verdict (converged):
  - **SHIP — recency-weighted swing** (commit axis): descriptive ratio of recent (trailing 13w) vs prior (39w) slope; declare the window explicitly (reproducible, falsifiable, not predictive). No citation axis needed.
  - **SHIP-WITH-CAVEAT — commit-axis Sharpe** (slope / residual-noise on the ~52-week log-linear fit): emit the value **plus a ±CI band** and `measurementTechnique` (HAC/Newey-West, half-life). **Sufficiency gate: require ≥26 non-zero commit weeks, else RESERVE.** (Citation-axis / "dual" Sharpe → RESERVE: 5 yearly points ≈ 3 dof, unstable.)
  - **SHIP-WITH-CAVEAT — commit-axis changepoint date** (CUSUM/PELT on the ~52 weekly points, **k_max = 1**): only render a date when **|Δslope| > ~2× residual-std**, else "no significant changepoint detected". (Runs on the COMMIT series, not citations.)
  - **RESERVE — code-leads-citation lag**: ~5 yearly citation points → lag SE spans years; the "lag" is a publish→cite-pipeline artifact, not a property of the system; undefined for 10/19 with no citation axis.
  - **RESERVE — axis alpha vs cohort**: cross-entity regression within cohorts of ≤12 (only 9 dual-axis) → statistical power ≈ 0; CIs wider than the effect.
  - **RESERVE — gate-ETA**: needs snapshot history (only one snapshot exists).
- **Publication rule (moat-critical):** emit a `schema.org PropertyValue` in the entity Dataset `variableMeasured` ONLY for SHIP signals (each with value + unitText + `measurementTechnique` URL#anchor + **`measurementMethod` = versioned method id, e.g. "EvidaxisMethodology v0.3.0"** + snapshot timestamp). Reserved signals emit **no value** OR an explicit `Text "insufficient data — reserved"` — never a fabricated number, "0" sentinel, or silent missing field (silence reads as a bug; an explicit reserved state reads as methodology).
- **Render the band as a COMPLETE 3-state component** (Ship = value+CI · Caveat = value+CI+N · Reserved = "reserved — needs X"), never a "coming soon" stub. The visible reserved rows ARE the rigor story.
- **Per-entity `signalQuality` disclosure** (`{commit_weeks, citation_years, derived_shipped[], derived_reserved[]}`) rendered as a visible "methodology gate" footnote = show-your-work.
- **Single-snapshot honesty:** surface **"snapshot 1 of N"** as a first-class VISIBLE fact on every derived signal (the observatory has observed once; momentum/derived must not imply more longitudinal evidence than exists). Base-rates only once history accrues.

### Skin / layout
Restyle, not re-architecture. The existing routes, JSON-LD graph, robots, sitemap, llms.txt, JSON twins, and person-free posture are mature and stay. We change tokens + add sections + add charts + richer card:
- `web/src/styles/global.css`: cool palette tokens (`--paper #f7f7f5`, `--surface #fff`, `--ink #191814`, `--ink-mute #5f584a`, `--teal #0c6e63`, `--amber #b0641c`, `--slate #4b5d8f`, plus `--paper-2`, `--grid`, `--rise-wash`, `--shadow-card`, `--shadow-float`, dark-band retheme vars). 12px-radius shadowed card panels, browser-chrome panel-bar framing, `sec-num` section numbering. Familjen Grotesk (display) + IBM Plex Sans (body) + IBM Plex Mono (data); Spectral kept only for italic accents.
- `web/src/layouts/Base.astro`: new glyph (rounded-square + diagonal + 2 dots), cool theme-color, font preloads, keep all meta/JSON-LD discipline.

---

## 2. Component-by-component port list (with the REAL Entity fields each consumes)

### Chart primitives → Astro components (all SSR, in `web/src/components/charts/`)
| Component | Real fields consumed | Notes |
|---|---|---|
| `Scatter.astro` | all entities: `axes.github_commit_velocity.cohort_z` (x), `axes.openalex_citation_momentum.cohort_z` (y, null-safe), `momentum` (radius), `status` (ring if rising), `cohort`→color, `name` | rising quadrant wash; **0 rising → no riser rings, render gracefully**; null citation_z → plot at axis or omit dot, documented in figcaption |
| `Beeswarm.astro` | grouped by `cohort`: `momentum`, `status`; per-cohort median line | deterministic index-based jitter (ports directly) |
| `Sparkline.astro` (extend existing) | `commitSeries(id)` (provenance weekly), or `citationSeries(e)` | already SSR; add `<title>`/`<desc>` + numeric range to figcaption |
| `CitBars.astro` | `citationSeries(e)` / `axes.openalex_citation_momentum.by_year` | fallback markup "no citation axis" when `a2.status !== 'present'` |
| `CitArea.astro` | `citationSeries(e)` | twin-contrast passing-axis area |
| `CommitFlat.astro` | `commitSeries(e)` + flat-avg line | "flat trend" label only when velocity not convergent |
| `CommitHeatmap.astro` (+ mini) | **real** `commitSeries(id)` weekly array → cell intensity | **kills the PRNG fake path** |
| `Donut.astro` | `counts.rising/counts.entities` (convergence %), `counts.axis2_present/counts.entities` (coverage %) | static arc + % text SSR; stroke animation optional JS only |
| `Gauge.astro` (+ mini) | `a1.cohort_z` / `a2.cohort_z` | null-state when citation absent |
| `Quadrant.astro` | self `a1/a2.cohort_z`; **peers = real `entitiesInCohort(key)` z-pairs** | replaces prototype's hardcoded fake peer cloud |
| `MomentumRing.astro` | `momentum` | null-safe |
| `GateGlyph.astro` | `convergent_axes` membership per axis (vPass/cPass) + verdict text | |
| `PercentileStrip.astro` (+ mini) | `percentile` | p25/p50/p75 ticks |
| `LagSignal.astro` | `derived.lag()` from real series | honest `N/A` if no lead |
| `AlphaSignal.astro` | `derived.alpha()` | reserved if not computable |
| `SharpeSignal.astro` | `derived.sharpe()` | from series std |
| `SwingSignal.astro` | `derived.swing()` | recency-weighted |
| `ChangepointSignal.astro` | `derived.changepoint()` | inflection date |
| `GateEtaSignal.astro` | — | **reserved** (needs snapshot history) |

Each chart component emits the parallel `<table>`/`<dl>` + `<figcaption>`.

### Homepage sections (rewrite `web/src/pages/index.astro` onto the new skin)
- **Masthead / Footer**: static routes + new glyph; CTA → `/snapshots/{SNAP_DATE}/snapshot.json`. No per-entity data.
- **Hero**: `snapshot.snapshot_id`, `period`, `methodology_version`, `counts.entities`, cohort count; browser-chrome mockup highlights **top-by-momentum entity** (real, since 0 rising) → its `CitBars` + `MomentumRing` + two `Gauge`. The "both axes check = rising" label derives from real `status`.
- **Instrument "Two axes. One gate."**: prose from `snapshot.axes` + `snapshot.gate`; `Scatter` over all entities. Panel tag shows `counts.rising` (= 0).
- **Dark signature band**: `Scatter` (convergence) + `Beeswarm` (momentum by cohort) on midnight theme; legend = real `snapshot.cohorts` labels + colors; both with how-to-read captions.
- **State of snapshot**: 3 stat cards (Rising/Watch/Tracked) from `counts`, each with a representative `Sparkline`; then the **RankTable** (sortable, static rows).
- **Coverage "Three frontiers"**: 3 cohort cards (`snapshot.cohorts` label + authored desc + member count via `entitiesInCohort`); `Beeswarm` (all); donut-pair (convergence %, coverage %); `CitBars` for one citation-axis entity. Cards link to cohort pages.

### Entity card (rewrite `web/src/pages/e/[id]/index.astro`) → `EntityCard.astro` composing the primitives
Zones and real fields: **Bezel** (`name`, `entity_type`, `cohort`→label+color, `entitiesInCohort` size, `confidence`, `status`; "first seen" has no field → **drop**). **Hero** (`MomentumRing` ← `momentum`; `GateGlyph` ← `convergent_axes`; `PercentileStrip` ← `percentile`; rank = index in `entitiesInCohort`; "move/prev" needs history → **omit/"hold"**). **Dial row** (`Gauge` ← `a1.cohort_z` + `fmtSlope(a1.slope)`; `Quadrant` ← self + real cohort peers; `Gauge` ← `a2.cohort_z`, null-safe). **Readout** (rank, `a1.recent_weekly_commits`, `a2.total_citations`+`a2.status`, `momentum`, `percentile`). **Bullet bars** (`a1/a2.cohort_z`; cohort-median tick computed as true median of cohort z's, ~0). **Series row** (`CommitHeatmap` ← real weekly; `CitBars` ← real by-year). **Twin contrast** (watch-only, when exactly one axis convergent: pick passing axis from `convergent_axes`). **Derived signals band** (`derived.ts`, 5 computed + gate-ETA reserved). **Note** (`e.note` + status sentence; reuse existing verdict/path-to-Rising prose). **Trust footer** (`github_repo`, `openalex_work_ids[0]`, `stars_not_scored` struck, `confidence`, `manifest.manifest_hash` for repro, snapshot/period/methodology line).

### Compact row variant → `EntityRow.astro` (used in RankTable + cohort/industry pages)
`name`, `cohort`, `status`, `momentum`, `percentile` (`PercentileStrip` mini), `a1/a2.cohort_z` (mini `Gauge`), real `commitSeries` (`miniHeat`), lag (`derived`, may be N/A). Each row is a real `<a>` to `/e/{id}/`.

### RankTable → `RankTable.astro`
Static `<tbody>` rendered at build from `entities` sorted by `momentum` desc (columns: #, System, Cohort, Velocity z, Citation z, Momentum, Status, Commits-spark). Sort/keyboard interaction is a thin progressive-enhancement script over the complete static table. **`single-axis` and `calibration` statuses get color/badge mappings** (extend `StatusBadge.astro` + `STATUS_LABEL`).

`EntityTable.astro` is extended/superseded by `RankTable.astro` + `EntityRow.astro`; `StatusBadge.astro`, `Sparkline.astro`, `MethodologyBody.astro` reused.

---

## 3. GEO + SEO measures (consultant checklist, concrete for this repo)

Preserve the mature layer (jsonld.ts `@graph`, robots allowlist, sitemap lastmod, llms.txt, JSON twins, og.png, person-free disambiguation) and add:

1. **Charts as build-time SVG + text** (§1, the only real regression risk). CI asserts no `data-ev` or empty chart container survives into `dist/`.
2. **Chart machine-readability (REVISED by spar — no hidden duplicate tables).** Four complementary surfaces in authority order: (a) server-rendered SVG with `<title>/<desc>/<text>` carrying the real values; (b) **JSON-LD `Dataset` (`variableMeasured`) = the CANONICAL machine surface** (LLMs/Google extract structured JSON-LD more reliably than DOM tables); (c) a VISIBLE `<figcaption>` carrying a **structured `<dl>` of the headline numbers with `<data value>` attributes** (NOT prose — prose is the worst format for machine extraction); (d) `<details><summary>Full data</summary><table>…</table></details>` collapsed-but-crawlable (NOT `display:none`). Do **not** ship visually-hidden duplicate tables on every chart (HTML/CWV bloat for no marginal retrievability once (b) exists).
3. **Each derived signal as `variableMeasured` PropertyValue** (name+value+unitText+measurementTechnique); add convergence-gate state as a PropertyValue (`value N, maxValue 2`). **Do not rename existing v1 frozen property names** (jsonld.ts header declares them a frozen external contract).
4. **Preserve full `@graph` integrity**: every page passes `jsonLd` + breadcrumb; keep Organization+WebSite+DataCatalog on home, Dataset per entity/snapshot/cohort, TechArticle+DefinedTermSet methodology, DefinedTermSet glossary, BreadcrumbList deep pages; every creator/publisher resolves to `{@id: #org}`.
5. **Per-page unique title/description + canonical + OG/Twitter**; add `og:image:width/height`, `twitter:title`, `twitter:description`; regenerate **og.png to cool palette + new glyph** (person-free).
6. **Semantic landmarks + one `<h1>`, no skipped heading levels**; every chart SVG `role="img"` + `aria-label` + `<title>`/`<desc>`; focus-visible; AA contrast on teal/amber/slate; `prefers-reduced-motion` guards.
7. **How-to-read captions + glossary-linked terms as real prose** (not tooltip-only); link momentum / convergence gate / development velocity / citation momentum to `/glossary/#anchor`; keep "Cite as:" line on entity pages.
8. **Citable numbers with units + cohort qualifier** ("z +1.42 within N-system cohort"); `<time datetime>` for snapshot_date/period; `<data value>` where displayed text differs from machine value.
9. **Internal link graph**: no orphan `/e/` pages; every entity links to its cohort + `/methodology/`; coverage cards link to cohorts; ranking rows are real `<a>`.
10. **robots/sitemap/canonical coherence** preserved; JSON twins + llms.txt not blocked; `<link rel=alternate type=application/json>` on entity AND snapshot pages.
11. **llms.txt completeness** (GAP 6): add enumerated entity list (name → `/e/{id}/` + `.json`) and live snapshot URL; optionally an `llms-full.txt` (methodology + glossary + snapshot summary).
12. **Core Web Vitals**: latin-subset fonts (~6 woff2, < 120 KB; drop Spectral CDN, self-host Familjen Grotesk via @fontsource), `font-display:swap` + size-adjust fallback + preload exactly 2 LCP faces; explicit width/height/viewBox on every SVG (no CLS); immutable cache on hashed assets via vercel.json.
13. **Person-free invariant**: no Person node, no `author`/founder/byline/team; all creator/publisher = Organization `@id`. CI greps `dist/` for Person schema / founder strings / the keeper's name → must be 0.

---

## 4. Test strategy (plain-language)

### AUTOMATED (run in CI + locally)
| Test | What it checks (one sentence) | Tool |
|---|---|---|
| **Helper unit tests** | The chart-math and derived-signal functions return correct, deterministic numbers for known inputs. | Vitest |
| **Build passes** | `astro build` from repo root (with `../data` present) completes with no errors. | astro / npm |
| **CRITICAL GEO: data-in-static-HTML** | With JavaScript switched off, every chart's numbers (momentum, both z-scores, weekly commits, citations-by-year) already exist as text in the built `dist/` HTML, and no empty `data-ev` placeholder survives. | grep + node DOM (cheerio) over `dist/` |
| **em-dash budget = 0** | No "—" character appears anywhere in built HTML (brand rule). | grep |
| **HTML validity** | The generated HTML is well-formed and standards-valid. | html-validate / vnu |
| **Internal link check** | No internal link or redirect on the site leads to a missing page. | linkinator |
| **Accessibility (WCAG AA)** | Every page passes automated accessibility rules (contrast, labels, heading order, focus) with zero serious violations. | pa11y-ci / axe-core over sitemap |
| **Lighthouse** | Each page scores well for speed, SEO, accessibility, and best practices. Targets: **Performance ≥ 90 (mobile)**, **SEO = 100**, **Accessibility ≥ 95**, **Best-Practices ≥ 95**; LCP < 2.5s, CLS < 0.1, INP < 200ms. | @lhci/cli |
| **JSON-LD validation** | The structured-data blocks on every page parse, validate against schema.org, keep the frozen v1 property names, and their values match the snapshot. | node ajv + schema check |
| **Unique meta** | Every page has a distinct title and description within length limits and a self-referential canonical. | node script |
| **Person-free gate** | No Person schema, founder name, byline, or personal identifier appears anywhere in `dist/`. | grep |
| **Responsive screenshots** | Capture each key page at 375 / 768 / 1280 / 1920 px for visual review. | Playwright headless |

### MANUAL (what a human eyeballs on the preview URL)
- **View Source (not DevTools)**: confirm full chart SVGs, real entity/axis text, and card data are in the HTML before any JS runs; then disable JS in the browser and confirm the page is still complete and readable.
- **Breakpoint visual review** at 375 (phone), 768 (tablet), 1280 + 1920 (desktop): hero, dark signature band, ranking table, entity card, derived-signals band, coverage grid all lay out cleanly with no overflow/overlap; charts reserve space (no jump).
- **Design fidelity**: preview matches `proto/v-final.html` + `proto/cards/final-card.html` (momentum ring, convergence-gate, twin axis dials, velocity×citation quadrant, bullet bars, commit heatmap, citation bars, derived-signals band, ranking-row mini-dials) but driven by REAL data — spot-check 2-3 entities against `snapshot.json`.
- **Accessibility by hand**: keyboard-tab through a page (visible focus order), enable OS "reduce motion" and confirm the glowing-dots/entrance animations stop, eyeball teal/amber/slate contrast on the cool canvas.
- **Derived-signals sanity**: confirm the 5 computed signals look plausible vs the raw series and that gate-ETA shows the honest "reserved" state, not a fabricated number.

---

## 5. CI + Vercel build/preview + safe cutover

### CI — new workflow `Evidaxis/.github/workflows/web-ci.yml`
Additive and path-scoped (`web/**`, `data/**`, `taxonomy/**`) so it does not collide with the existing `proving-run-gate.yml` data gate. It builds from **repo root** (so `../data` + `taxonomy/` resolve, same as Vercel), then runs: build → static-HTML data assertion (entity names + inline `<svg>` present, em-dash = 0, no `data-ev` survivors) → serve `web/dist` → pa11y WCAG2AA over sitemap → linkinator internal links → Lighthouse (SEO=1.0 + a11y=1.0 hard, performance soft `|| true` for the first runs, then ≥0.9 hard) → person-free grep gate → Vitest unit tests. **It does NOT deploy.** Branch protection requires `web-ci` AND `proving-run-gate` green on `main`.

### Vercel config (fixes D8 fast-follow)
Root cause: `data.ts` resolves `ROOT` to the repo root and reads `data/`, `taxonomy/`; a Vercel project rooted at `web/` can't see `../data`. Fix:
- **Dashboard (project `evidaxis`)**: Framework = Other; Root Directory = `./` (repo root); Build = `npm ci --prefix web && npm run build --prefix web`; Install = `npm ci --prefix web`; Output = `web/dist`; Node = 22.x.
- **New `Evidaxis/vercel.json` at repo root** (authoritative once root = repo root): `framework:null`, the build/install/output commands, `trailingSlash:true`, `cleanUrls:false`, the 3 redirects (`/e/:id/:slug→/e/:id`, `/methodology→/methodology/current`, `/rankings/:taxon/:period→/cohorts/:taxon/:period`), and headers (immutable cache on `/_astro/*`, `X-Content-Type-Options:nosniff`, `Referrer-Policy`). **Delete the now-dead `web/vercel.json`.** Add `"engines": { "node": "22.x" }` to `web/package.json`.
- **No runtime env vars** (pure static build). Keep production alias PUBLIC; keep **Preview** deployments behind Vercel protection so the unreleased redesign is not crawled/indexed pre-cutover.

### Safe cutover checklist (never touch prod until approved)
1. All redesign work on `redesign/v-final`; prod untouched.
2. Add root `vercel.json` + `engines` pin; delete `web/vercel.json`; set the Vercel dashboard fields; commit to branch.
3. Push branch → Vercel auto-builds a **preview URL** from repo root (proves `../data` resolves in Vercel's container — the D8 blocker).
4. Open PR → `web-ci` must be GREEN.
5. On the preview: View Source confirms static charts + data; disable JS, page still complete.
6. On the preview: person-free grep clean; confirm `DECISIONS.md`/`ROADMAP.md`/`MINT-STEPS.md`/`BRAND-KIT.md`/`spine/` are gitignored and absent from the built tree.
7. Design-fidelity + responsive + a11y + reduced-motion manual passes.
8. **GET EXPLICIT APPROVAL from the keeper on the preview URL.** (Non-negotiable gate.)
9. Cutover: merge to `main` (protection requires both gates green) → Vercel deploys prod. Or `vercel promote <validated-preview-url>` for the exact build with no rebuild.
10. Post-cutover verify on evidaxis.org: redesign live, redirects fire, sitemap lastmod = snapshot_date, no `_astro` 404s.
11. Trigger IndexNow / resubmit sitemap.
12. Rollback ready: `vercel rollback` re-points prod instantly; keep `deploy.sh`+`deploy.env` one release as escape hatch, then decommission.

---

## 6. Milestones (ordered)

- **M0 — Decisions + scaffold.** Lock the derived-signals decision (compute 5, reserve gate-ETA), branch `redesign/v-final`, add Vitest + `web/src/lib/charts.ts` + `web/src/lib/derived.ts` skeletons. *Exit: Vitest runs; charts.ts/derived.ts export typed pure functions with passing unit tests on fixture data.*
- **M1 — Skin + tokens + fonts + Base.** Cool palette tokens in `global.css`, Familjen Grotesk via @fontsource (latin subset), new glyph, font preloads, regenerated cool og.png. *Exit: `astro build` green; Lighthouse perf ≥ 90; woff2 count ~6 latin-only; em-dash = 0; existing pages still render with new skin.*
- **M2 — Chart component library (SSR).** All primitives in `web/src/components/charts/` emitting SVG + parallel table/figcaption from real data. *Exit: GEO assertion passes on a test page (numbers in static HTML, no `data-ev` survivors, JS-off complete); helper unit tests green.*
- **M3 — Homepage port.** `index.astro` rebuilt with sec-num sections + hero mockup + instrument scatter + dark signature band + stat cards + RankTable + coverage grid, all bound to `snapshot.counts`. *Exit: home renders real data; 0-rising handled gracefully; pa11y AA clean; JSON-LD intact; responsive screenshots clean at 4 widths.*
- **M4 — Entity card + compact row.** `EntityCard.astro` + `EntityRow.astro` wired into `/e/[id]/` and cohort/industry pages; derived-signals band (5 computed + reserved gate-ETA); JSON twin + variableMeasured extended. *Exit: spot-checked entities match snapshot; every chart has backing table; derived signals reproducible; person-free gate clean; JSON-LD validates with frozen v1 names.*
- **M5 — GEO/SEO + a11y hardening.** Captions, glossary links, units, `<time>`/`<data>`, llms.txt entity list, meta uniqueness, FAQPage on methodology/about, reduced-motion guards. *Exit: full automated suite green (Lighthouse SEO=100, a11y≥95, perf≥90; link-check clean; JSON-LD valid; unique meta).*
- **M6 — CI + Vercel config + preview.** Add `web-ci.yml`, root `vercel.json`, Node pin; push branch; produce preview URL. *Exit: CI green on PR; Vercel preview builds from repo root and serves the redesign; manual View-Source + JS-off + person-free checks pass on preview.*
- **M7 — Approval + cutover.** Present preview to the keeper. *Exit: explicit approval, then merge/promote; post-cutover verification green; rollback path confirmed.*

---

## 7. Risks + person-free guardrails

- **Client-only charts regress GEO (highest risk).** Mitigation: §1 build-time SVG rule + the CRITICAL GEO automated assertion as a hard CI gate; no `data-ev` placeholder may survive into `dist/`.
- **Fabricated derived metrics.** The prototype's PRNG fakes must be deleted, not ported. Only deterministic-from-published-series values ship; gate-ETA stays "reserved". Each derived value is reproducible and JSON-LD-stated.
- **Data-shape mismatch (0 rising, real cohorts, statuses single-axis/calibration, missing first-seen/move/repro-hash).** Bind everything to live `snapshot.counts`/fields; degrade gracefully (drop or "reserved"), never invent. Real `tracked`=12 etc. — read counts live.
- **Frozen v1 JSON-LD contract churn.** Add new PropertyValues; never rename existing property names.
- **CLS / CWV from fonts + charts.** Latin subset + preload 2 faces + size-adjust fallback; explicit SVG dimensions.
- **Vercel `../data` resolution (D8).** Root = repo root + prefixed build command; preview build is the proof.
- **Person-free invariant.** No Person node / author / founder / byline / team anywhere; creator+publisher = Organization `@id`; CI grep gate fails the build on any personal string; private files (`DECISIONS.md` etc., `spine/`) remain gitignored and absent from the built tree.
- **Premature indexing.** Preview deployments stay behind Vercel protection until cutover.
