# Card B implementation and acceptance record

Date: 2026-09-23. Snapshot: 2026-09-19, `fcfd3a7ccdcb`.
Baseline: main at `7f00f9908a0e8ce1012ce3f00394c7b5070422ea`.

Status: implementation available in the working tree; full acceptance is not complete.
No push or deployment was performed. No commits were created.

## Repository limitation

`git switch -c foundation-retrofit-cards main` failed because the environment
allows read access only to `.git`: `Unable to create .git/index.lock: Operation
not permitted`. The working tree therefore remains on `main`. The requested
branch comparison and commit list cannot be produced in this environment.
`git diff --stat -- etl/ governance/` and `git status --porcelain --untracked-files=all
-- etl/ governance/` both return no changes. Dated release governance records
remain a release-owner task, as required by the requested empty governance diff.

## Verified

- `cd web && npm run verify`: PASS, 22 test files, 193 tests, build, check-dist.
- `node --test scripts/*.test.mjs`: PASS, 32 tests.
- `git diff --check`: PASS.
- 134 A/protected HTML pages and their 134 JSON twins are byte-identical to main.
  These include all 48 headline experiment URLs. See `main.sha256`,
  `after.sha256`, and the empty `a-half.diff`.
- Two complete builds: 6,462 identical files, zero differences (`determinism.json`).
- Main wall-clock build: 4.087 seconds. Final wall-clock build: 5.541 seconds.
  Timings use the same `npm run build` command; see `main-build.json` and
  `after-build.json`. This does not predict the September 26 admission batch.
- Current output: 917 HTML pages, including 80 B cards. All 80 have a numeric
  first paragraph with a median comparator, a citation block, and sufficient
  content for FR-1. All 80 contain zero U+2014 and zero `n/a` placeholders.
- 1,493 CSV files are rectangular; 3,337 chart SVGs and 80 Atom feeds parse as
  XML. Every B reading has an entity ID, source and date. `acceptance.json`
  records zero data/artifact audit problems.
- Twelve specified fixtures are rendered through the actual Astro component,
  twice each, without changing production assignment. Their answers differ;
  the niche-removal test leaves at least three sourced own-system values.
  Preview fragments are under `fixtures/`, outside production `dist/`.
- The largest identical answer pattern after removing numbers AND the entity
  name is 28.75%, below the 60% limit.
- Pure tests cover null versus zero, undefined predicate inputs, measured
  citations without a scored trend, a repository without a paper or dependents,
  a citation-only synthetic record, an entirely unmeasured record, current
  snapshot medians, history/feed changes, copying, numeric sorting and both
  optional analytics sinks. The interaction script remains below 1,024 bytes.

## Open acceptance items

1. **Text subtraction is not a pass.** The mechanical diagnostic removes
   script/style/SVG content, data nodes and answer/claim paragraphs from the B
   article and counts the remaining text. The remainder is 67.99-73.34%, above
   the requested 40%. Instrument labels, definitions, table structure and
   retained Measurement detail contribute to that remainder. See
   `subtraction.json`. No test was weakened or labelled green for this metric.
2. **Global zero U+2014 conflicts with the pinned baseline.** Main already
   contains 3,281 occurrences, including protected experiment titles and gate
   phrases explicitly allowed by the existing guard. Final dist contains 2,879,
   all outside B. Making the global grep zero would change protected A bytes.
3. **Boldness strict is not a pass.** The external linter finds six code lines:
   five existing lines in Base/minutes/private charttest, and the explicitly
   requested `X-Robots-Tag: noindex` feed header in `web/vercel.json`. The log
   is `boldness.log`. The Vercel JSON was not distorted to hide a required header
   from a line-oriented linter.
4. **Browser and HTTP checks were blocked.** Browser discovery returned no
   available browser. `astro preview --host 127.0.0.1 --port 4325` failed with
   `listen EPERM`. Viewport checks, screenshots, five-second/30-card visual
   review, real user feedback, `curl -A`/HTTP 200 probes and the preview
   `seo-crawl`/`seo-audit` cannot be reported as passed. Static artifact existence,
   XML parsing, real Astro rendering and interaction unit tests did run.
5. **The repository verify command has no astro check step.** The existing
   package command runs Vitest, Astro build and check-dist. `@astrojs/check` is
   not installed. A separate `tsc --noEmit` reports errors in existing code
   (notably the JSON-LD tests); see `typescript.log`. The new renderer tests
   use Astro's container component-factory type for `.astro` imports; no
   Card B errors remain in that check.

## Implementation map

- `src/lib/cardB/policy.mjs`: shared assignment and content indexability;
  HTML, sitemap and check-dist use the same function.
- `src/lib/cardB/build.ts`, `context.ts`, `facets.ts`: deterministic data
  projection, cached snapshot/cohort aggregates, parsed paper references,
  source/date readings, source-aware history and pre-render text guards.
- `src/data/card-b-facets.ts`: versioned class texts and claim URNs. A linked
  OpenAlex work without a reading has its own class, not a false absence claim.
- `src/components/cardB/`: B card, raw HTML readings, figures and existing
  instruments in Measurement detail. Old A markup remains in the route.
- `src/lib/cardB/exports.ts`, `charts.ts`: release-qualified CSVs, accessible
  SVGs and per-system feeds from archived numeric changes.
- `src/lib/cardB/config.ts`: `CHARTS_INLINE` defaults to false. The inline path
  has a renderer test; old SVG release URLs remain addressable after a switch.
- Vercel feed headers and the mirrored redirect map exempt new entity assets
  from the legacy slug redirect.

Week labels are reconstructed from the capture Sunday's weekly alignment:
the frozen provenance retains 52 counts but not GitHub's original week
timestamps. This limitation is stated in the HTML and CSV. Means and their
comparisons use the collector's 12-week window and one-decimal rounding.

## 33-element trace

| Element | B location / disposition |
| --- | --- |
| name | Hero h1 |
| entity_type | Identity line |
| cohort_label | Identity line, niche block |
| cohort_n | Identity line, niche block |
| gate_glyph_and_phrase | Measurement detail |
| percentile_in_cohort | Measurement detail |
| momentum_score | Measurement detail |
| velocity_gauge | Measurement detail |
| citation_gauge | Measurement detail |
| dependents_gauge_m3 | Measurement detail |
| readout_weekly_commits | Hero, code block, readings table; explicitly averaged |
| commit_heatmap_26w | Code block and retained instrument |
| reconstructed_history_sparkline | Measurement detail, labelled reconstructed |
| daily_dependents_unscored | Dependents block, readings table, history |
| axis3_details_table | Measurement detail |
| derived_swing | Measurement detail |
| derived_sharpe | Measurement detail |
| derived_changepoint | Measurement detail |
| derived_lag_reserved | Measurement detail, reason retained |
| derived_alpha_reserved | Measurement detail, reason retained |
| derived_gate_eta_reserved | Coverage block: never published; old reason omitted in B |
| signal_quality_footnote | Measurement detail |
| sources_block | Paper and links, per-reading provenance |
| claim_urn_receipt | Citation, exports, Measurement detail |
| badge_embed | Rising only: copy action and Measurement detail image |
| total_citations_raw | Hero/citation/readings, including insufficient trend |
| citation_by_year_bars | Citation block, including insufficient trend |
| github_stars_raw | Muted tile, readings, unscored label |
| editorial_note_raw | Never published; build-time paper reference extraction only |
| paper_ref_from_note | Structured display field, paper block |
| deps_ecosystem_composition | Coverage reason: field absent from snapshot |
| zero_commit_weeks_explicit_flag | Answer and code ruler |
| peer_momentum_values | Alphabetical table inside Measurement detail |
