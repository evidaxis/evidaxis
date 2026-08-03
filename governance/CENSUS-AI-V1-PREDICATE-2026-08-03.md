# Governance act: AI-v1 predicate (census wave 1)

> status: **v2 DRAFT** — rewritten 2026-08-03 after an adversarial review that
> broke v1 in eleven places. Pending: the census run itself, then hash freeze.
> Subordinate to REGISTRY-GROWTH-POLICY-2026-07-21.md; closes its three open
> questions (dedup unit, licence allowlist, blocklist + AI-scope signals).
> Predicate amendments = a new dated version re-run retroactively against the
> whole universe; never a case decision.
>
> **Review that produced v2** (every claim below measured live, not asserted):
> ChatGPT 5.6 Sol via Codex CLI (15 findings, 8 blockers) · an independent
> agent that measured every alternative sensor and both error rates on live
> GitHub (31 findings) · a 7-voice council on the licence question
> (lab/consilium-log/2026-08-03-consilium-65-evidaxis-license-leg.md).
> Grok's lane DNF'd twice on a headless watchdog and is recorded as missing,
> not silently absorbed.

## 0. What v1 got wrong (kept, because a frozen act must show its scars)

| v1 claim | What measurement showed |
|---|---|
| regex `…\|molecul\|fine.?tun…)\b` | The trailing `\b` made **"fine tuning", "voice cloning", "image generation", "molecular docking" all fail** — the exact words the stems existed for. `.?` also accepted "deepXlearning". |
| blocklist over name+description+topics | Killed **367 of 2,592 AI-scope repos (14.2%)** on 16,860 live rows, including `huggingface/pytorch-image-models` (timm) via "largest **collection of** PyTorch image encoders" and `catboost` (9.1k★) via the topic `tutorial`. timm is not among the 137, so the v1 fixture passed green while excluding it. |
| topics `ai`, `inference`, `agents` admit alone | Admitted `dbeaver` (51.3k★ database GUI, topic `ai`), `ts-pattern` (15.1k★) and `io-ts` (6.8k★) where `inference` means **type** inference. |
| membership joined on `full_name` | **8 of 137 members had stale names** (aider, OpenHands, SWE-agent, goose, Genesis, LLaMA-Factory, AReaL, ComfyUI all moved org) → 8 duplicate cards on day one. |
| "primary language is not Markdown/HTML/TeX" | Cannot establish "first-party code outside examples"; left MDX, Vue, Dockerfile, CSS unclassified. |
| fixture = "blocklist must hit 0 of the 137" | A fixture of curated members cannot detect defects outside its own taste (timm proves it). Fitting to 137/137 is fitting. |
| date slicing at day granularity | A dense same-day slice bisected onto itself: **unbounded hang**, plus a hardcoded 2027 horizon. |
| `emit()` reads whatever exists | Would hash-anchor a manifest built from a **partial sweep** and label it complete. |
| nulled GraphQL node = repo missing | A 502 (measured: `dependencyGraphManifests` 502s at batch size 3) became a **permanent exclusion** that resume never revisited. |
| §3(b) "publish 50 named blocked repos" | Is itself a per-repo negative judgment — contradicts positive-only discipline. |
| `≥1 registry package (deps.dev)` leg | Was in the act, absent from the code: the executed predicate was narrower than the frozen one. |

## 1. Dedup unit and identity

**Unit = one GitHub repository. Identity = the numeric repository id.**

- Monorepo with several products → ONE system (commit and star series are
  repo-level observables anyway). Org families → N systems; org aggregation is
  a VIEW over the `owner` field, never a membership decision.
- The numeric id is the anchor: it survives rename and transfer, `full_name` is
  a mutable label. `data/registry_ids.json` pins every existing member's id;
  membership tests compare ids. Names in `etl/seeds.json` may be stale and that
  must never create a second card.
- **Forks never enter**, with no exception. v1's "a fork that becomes the
  canonical home may enter" required judging canonicality; archiving an
  upstream does not clear GitHub's `isFork` anyway.
- Deleted repositories: absence is recorded only from a CLEAN API response.
- **Accepted, declared limitation:** clone-Sybil multiplication (the same code
  pushed as N independent non-forks) is not detected. Mechanical code-similarity
  at 121k scale is out of reach for a solo operator; AI-v2 may add it. Stated
  here so it is a known coverage limit, not a surprise.

## 2. Licence

**Leg: `licenseInfo.spdxId`, normalised by stripping `-only`/`-or-later`, is in
the frozen allowlist below.** Eligibility is fixed at the ADMISSION snapshot:
a later relicence never removes a member, and is recorded as an observation in
that member's series.

```
MIT · Apache-2.0 · BSD-3-Clause · BSD-2-Clause · BSD-3-Clause-Clear
GPL-2.0 · GPL-3.0 · AGPL-3.0 · LGPL-2.1 · LGPL-3.0
MPL-2.0 · ISC · Unlicense · CC0-1.0 · 0BSD · Zlib · EPL-2.0 · Artistic-2.0
```

`NOASSERTION` means **"the required positive evidence was not produced"**, not
"this repository is not open source". The institute never converts that
ambiguity into a published verdict about anyone.

**Every admitted member carries `license_observed` and `commit_oid`** (the exact
default-branch commit the legs were evaluated against), so any third party can
re-derive a stricter or looser classification from the CC0 record without the
institute adjudicating anything.

**Known consequence, stated before the freeze:** the leg excludes
`langgenius/dify` (151k★), `open-webui/open-webui` (147k★) and
`meta-llama/llama` (59.5k★), all `NOASSERTION`. Measured on 16,860 live rows,
**23.2% of all AI-scope repositories fail this leg** — this is a large,
structural share and the census report must state it prominently rather than
let a reader discover it. The council split 4–2 on whether the leg should gate
at all; the dissent and the conditions that would flip this decision are
recorded in the synthesis and are **not** settled by this act beyond wave 1.

**No named exclusion annex.** All six council voices converged: naming the
repositories that failed this leg is the highest-salience per-repo negative
judgment the institute could issue, and it takes a public side in a live
definitional dispute. v1's §3(b) named-sample audit is withdrawn for the same
reason and replaced by an aggregate token histogram (§3).

## 3. Non-system filter (narrow by design)

Two tiers, because the same word is a non-system marker in a repository NAME
and an ordinary word in a description:

- **Name only:** `curated · collection-of · list-of · interview · book ·
  course · tutorial · mirror · weights · checkpoint`
- **Anywhere (name, description, topics):** `awesome · roadmap · cheatsheet ·
  reading-list · paper-list · question-bank · study-guide`

List-shaped repositories that slip through are removed by the code-language leg
instead (an awesome-list is Markdown-only) — a structural property rather than a
word match. Measured effect of the narrowing: the filter now removes **8.2%** of
storefront-AI repos instead of 14.2%, and timm and catboost survive.

**Remainder audit, positive-only compliant:** each census publishes the
*histogram of matched blocklist tokens* (token → count) with no repository
names, so over-blocking is visible in aggregate without a negative judgment
about any identifiable project.

## 4. AI-scope: three declaration channels

Implemented once in `collectors/ai_scope.py`; this act quotes it and the
module's sha256 is recorded in every census artifact. The classifier reads only
what a project **declares about itself**, never third-party inference.

| channel | source | role |
|---|---|---|
| ch-1 storefront | name + description + topics | admits alone (strong topics / regex) |
| ch-2 README | **first 2000 characters** of README.md | admits alone |
| ch-3 manifest | direct RUNTIME dependencies, framework tier | admits alone |
| weak topics | `ai · agents · inference · diffusion · transformer · tts · robotics · embedding` | never alone — requires ch-2 or ch-3 |

**Topic normalisation (one mechanical rule, not a token list):** lowercase,
strip non-alphanumerics, then match a frozen entry as a substring. This picks up
`multi-modal`, `gpt-4`, `gpt-4o`, `gpt-35-turbo`, `chatgpt` without naming a
single repository.

**Manifest channel rules** (each closes a measured false positive): parse per
format, never regex raw text (`tch` matches *patch/fetch/watch*; `ort` matches
*sort/report*); PEP 503 normalisation; **direct runtime dependencies only** — no
dev groups, no lockfiles; **reject `path` / `git` / `workspace` / `file:` /
`link:` entries** — `zed-industries/zed`, a text editor, declares
`anthropic = { path = "crates/anthropic" }`, its own internal crate; `setup.py`
excluded (arbitrary Python, unparseable without executing it).

**Framework tier only.** `openai`, `anthropic`, `langchain`, `tiktoken` and the
npm package `ai` are deliberately absent: they mark software that CALLS a model,
a different population (measured: `home-assistant/core` carries
`openai`+`anthropic`). Admitting them is worth a 3–10× population swing and
needs its own dated act, not a quiet allowlist edit.

**Measured trade-off (recall fixture of 31 known AI systems the storefront misses;
precision sample of 180 drawn at random from live rows the storefront called
non-AI):**

| rule | recall (31) | false (180) |
|---|---|---|
| ch-3 manifest only | 16 · 51.6% | 1 · 0.6% |
| ch-2 README[:2000] | 20 · 64.5% | 11 · 6.1% |
| **ch-2 OR ch-3 — FROZEN** | **23 · 74.2%** | **12 · 6.7%** |
| ch-2 README[:20000] | 25 · 80.6% | 27 · 15.0% |
| ch-2[:20000] OR ch-3 | 27 · 87.1% | 28 · 15.6% |

The 2000-character cut is a rule about **where a self-declaration lives** — a
project that IS an AI system says so in its opening pitch; one that merely uses
a model mentions it further down. No repository name entered the rule. Reading
the full README buys 4 more fixture members at 2.3× the false rate.

**Rejected sensors, each measured, so they are not re-proposed:** the SBOM
endpoint has its own **100 requests/hour** bucket (700 h at this scale) and
returns a flattened transitive graph that would admit `home-assistant/core`;
`dependencyGraphManifests` **502s at batch size 3** and does not parse PEP-621
`pyproject.toml` (measured: `hexgrad/kokoro` → 0 manifests while the blob lists
torch/transformers); code search is **10 requests/minute**; `github/explore`
topic corpus contains only 10 of the 42 frozen topics and recovers 0 of the 31.

**Open scope question, stated rather than hidden.** Seven of the 31 fixture
members (`zed`, `cline`, `aider`, `opencode`, `codex`, `qwen-code`,
`openinterpreter`) are editors and coding tools — software that calls models.
The legacy roster contains a whole 20-member `ai-coding-agents` vertical, so the
former curators took the inclusive side, and AI-v1 has never said which side it
takes. **Wave 1 decision: they are in scope when a declaration channel fires on
their own storefront/README, and are NOT pulled in wholesale by API-client
dependencies** (§4 framework tier). This keeps the population defined by
self-declaration rather than by implementation detail.

## 5. Predicate AI-v1 (assembled)

public repo · **not a fork** · not archived · licence ∈ §2 · AI-scope per §4 ·
not blocked by §3 · primary language ∈ the frozen **code-language allowlist**
(membership, not exclusion — `collectors/census_ai_v1.py:CODE_LANGS`) ·
**activity:** ( ≥1 release OR ≥50 commits in the trailing 365 days OR
**RESCUE** ( ≥10 commits in the trailing 90 days AND ≥3 distinct commit authors
among the last 100 commits of the trailing 365 days ) ).

The rescue clause is **inside the activity leg only** — it never waives licence,
scope, fork or blocklist. The v1 "≥1 registry package (deps.dev)" alternative is
**struck**: it was never implemented, and a frozen act that does not match the
code is worse than either.

Star bar: **≥500** public registry · **200–499** shadow layer (ids and star
counts only, stored outside the public repository, never published).

## 6. Census procedure

1. **Enumerate** the full universe `stars:lo..hi fork:false is:public`, sorted
   `stars desc`, partitioned geometrically on stars and then on creation
   TIMESTAMP down to one second whenever a band exceeds the 1000-result cap.
   `incomplete_results=true` is retried, never accepted. A band is recorded
   `done` only when **distinct ids collected == reported total**; otherwise it is
   requeued. Terminal partition still over the cap → **fail closed**, recorded.
2. **Sentinel.** The sweep writes `raw-500plus-complete.json` only when the
   partition stack empties. `emit()` refuses to run without it, so a partial
   universe can never be hash-anchored as complete.
3. **Deep legs** via batched GraphQL: licence, primary language, releases,
   365/90-day commit counts, default-branch `oid`, README prefix, manifests.
   A nulled node is treated as "gone" only inside a CLEAN response; anything
   else is retried, and residual failures abort the emit.
4. **Emit** `census-run.json` (aggregates + the full band ledger inline +
   sweep sentinel + `legacy_reconciliation`) and `pending-manifest.json`
   (admitted members with `repo_id`, `commit_oid`, `license_observed`,
   `admitted_by` channel and the `signal` that fired). Both hashed;
   `census-run.sha256` written alongside. Only these two files are committed;
   raw sweep rows and deep-check evidence are gitignored.
5. Any `etl/seeds.json` change is paired with a dated frontier manifest, as CI
   already enforces.

**Timestamps are honest:** the census is stamped with its actual run time. The
policy's 2026-07-31 stock date is an intent, and is not backdated.

## 7. Legacy reconciliation (replaces the v1 fixture gate)

The 137 existing members were admitted under the discretionary method this
policy abolished, and the no-removal rule secures them independently. **AI-v1
therefore owes them nothing, and matching 137/137 would be fitting.**

- The roster is a **falsifier, never a target**: a known-true system failing a
  leg may trigger *removal of an over-broad rule* (that direction only makes
  the predicate more permissive, as a stated rule) but may **never** justify
  adding tokens that match the failing rows.
- Every census publishes `legacy_reconciliation`: how many legacy members AI-v1
  would admit today and, for those it would not, **which leg they fail**. This
  is a negative statement about the institute's OWN roster, so positive-only
  discipline is untouched — and an institute that publishes where its predicate
  disagrees with its own history is demonstrably not curating.
- Recall figures are always published with their precision denominator (§4).

## 8. Weekly activation (the tranche)

`n_t = min(P_t, max(10, ceil(0.06 × L_t)))`, where `L_t` = live cards and
`P_t` = pending queue, both read at a UTC cutoff taken before the run.
Order: **FORWARD crossings first, then BACKLOG**; within each queue, current
stars descending, tie-break repository id ascending. Sorting one merged queue
would bury a fresh 501-star crossing behind the entire backlog and silently
invert the policy's forward priority. (The parent policy's "137 → +8/wk"
illustration predates the floor of 10; at 137 live cards the correct tranche
is 10.) Tool: `collectors/activation_tranche.py`.

## Changelog

- **2026-08-03 v2** — rewritten after adversarial review; eleven v1 defects
  listed in §0, each with the measurement that found it. Licence leg kept for
  wave 1 with the council's split recorded; named annex withdrawn; blocklist
  narrowed to two tiers; AI-scope rebuilt as three declaration channels with
  published per-member evidence; identity anchored on repository id;
  enumeration made coverage-asserting and fail-closed; deps.dev activity
  alternative struck.
- **2026-08-03 v1** — first draft (superseded the same day).
