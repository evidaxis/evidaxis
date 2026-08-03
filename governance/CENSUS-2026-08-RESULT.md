# Census result: 2026-08 (AI-v1, wave 1)

> status: **FINAL** — executed 2026-08-03 under the two-tier scope classifier.
> Predicate: governance/CENSUS-AI-V1-PREDICATE-2026-08-03.md
> Artifacts: `data/census/2026-08/census-run.json` (sha256 in
> `census-run.sha256`), `data/census/2026-08/pending-manifest.json`
> (sha256 `fde491f16ba1d4fd1bda870f9b65ee2aab0a2dcaf67aefc0ed60e28d2a2c326f`).

## Enumeration

The sweep observed **121,044** repositories at >=500 stars against a
universe count of **121,050** taken at sweep end:
delta **-6**, band shortfall **4**,
band surplus **2**, across **179** bands and
**1,142** requests.

A multi-hour collection cannot be compared to a single-instant count without a
gap, and the sweep descends stars, so a repository gaining stars mid-run
migrates into a band already closed. The institute therefore claims
**"these 121,044 repositories were observed"**, never "nothing was missed".

## Aggregate

| outcome | count |
|---|---|
| universe at >=500 stars | 121,044 |
| **admitted** | **5,522** |
| not AI-scope | 64,494 |
| blocked as non-system | 5,620 |
| excluded by licence | 3,119 |
| no code language | 401 |
| no activity | 3,668 (of which 406 entered via the rescue clause) |
| fork or archived | 724 |
| gone since the sweep | 1 |
| legacy members encountered | 130 |

Exclusions are aggregate by construction: the institute publishes admitted
members and counts, never a per-repository negative judgment.

## Channels and strata

Admitted by channel: {"storefront": 5342, "corroborated": 180, "readme": 0, "manifest": 0, "weak-topic+second": 0}

The `corroborated` channel is the weak tier — two independent supporting
registers, one of which must be construction evidence (a declared ML
framework). Its share is the instrument's own erosion sensor: if declaration
inflation is real it appears here years before it distorts the census.

Strata: {}

"Momentum in open AI" must never be published as a single scalar over this
population; the union and the strata appear together.

## Legacy reconciliation

AI-v1 was evaluated against the members admitted under the discretionary method
this policy abolished. **39 of 130** would not be admitted today.
They remain members under the no-removal rule. The roster is a falsifier, never
a target: no token was added to make a failing member match. An institute that
publishes where its own predicate disagrees with its own history is not
curating.

## Blocklist remainder audit

Aggregate token histogram, no repository names (positive-only discipline):

- `awesome` — 3,324
- `tutorial` — 318
- `book` — 289
- `interview` — 279
- `course` — 221
- `roadmap` — 180
- `cheatsheet` — 141
- `books` — 132
- `tutorials` — 126
- `handbook` — 69
- `workshop` — 69
- `cheat-sheet` — 62

## Activation

Cards activate weekly: `n_t = min(P_t, max(10, ceil(0.06 x L_t)))`, forward
crossings before backlog, current stars descending, tie-break repository id.
At 5,522 pending members and 137 live cards the first tranche is 10.
Order of publication is a marketing schedule, never a measurement verdict.
