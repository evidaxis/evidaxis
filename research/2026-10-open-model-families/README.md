# Technical reports and repository activity of ten open model families

*Evidaxis research note · OpenAlex pull 2026-10-18 · snapshot 2026-10-17 · data and code CC0-1.0*

Downloads and citations rank these families differently. The ATOM Report shows Qwen passing Llama on Hugging Face downloads in September 2025. On the OpenAlex pull of 18 October 2026, Llama's linked technical reports still drew 2,239 citations in 2025 against Qwen's 251, of 3,916 for all ten families; Llama 3 is excluded (see below), so Llama's lead is understated. DeepSeek's reports have drawn 1,046 citations in 2026 to date, already more than their full 2025 (539). Partial-year counts can only grow; 2026 is not otherwise compared.

![Share of citations to linked technical reports, 2023–2025](chart.svg)

| Family | Reports in the sum | 2023 | 2024 | 2025 | 2026 partial | Share 2023 | Share 2024 | Share 2025 | Org repos | Median commits/week | Sum of commits/week |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen | 23 of 23 | 1 | 131 | 251 | 325 | 0.1% | 3.3% | 6.4% | 10 | 0.75 | 513.6 |
| DeepSeek | 4 of 4 | 0 | 25 | 539 | 1046 | 0.0% | 0.6% | 13.8% | 4 | 0 | 1334 |
| Llama | 2 of 3 | 1205 | 3296 | 2239 | 376 | 91.1% | 82.5% | 57.2% | 1 | 0 | 0 |
| Gemma | 4 of 4 | 0 | 108 | 274 | 129 | 0.0% | 2.7% | 7.0% | 3 | 0 | 0.8 |
| OLMo | 2 of 2 | 0 | 16 | 32 | 23 | 0.0% | 0.4% | 0.8% | 1 | 0 | 0 |
| GLM | 4 of 4 | 85 | 168 | 188 | 21 | 6.4% | 4.2% | 4.8% | 3 | 0.1 | 0.6 |
| Kimi | 3 of 3 | 0 | 0 | 12 | 8 | 0.0% | 0.0% | 0.3% | 1 | 0 | 0 |
| InternLM | 1 of 1 | 0 | 3 | 22 | 4 | 0.0% | 0.1% | 0.6% | 7 | 0 | 22.3 |
| Mistral | 2 of 2 | 8 | 127 | 184 | 143 | 0.6% | 3.2% | 4.7% | not found | not found | not found |
| Phi | 7 of 7 | 23 | 119 | 175 | 74 | 1.7% | 3.0% | 4.5% | 1 | 1.8 | 1.8 |

A zero in a citation column is a measured zero on a linked report. `not found` is a gap.
The share is that family's citations divided by `denominator_{year}` in `families.csv`.
For 2025 the denominator is 3916. Share columns for 2026 are in the CSV and are not used above.

## What was counted

Ten families named in the ATOM Report's regional list (Section 2.2) and kept as this
package's set: Qwen, DeepSeek, Llama, Gemma, OLMo, GLM, Kimi, InternLM, Mistral, and Phi.
ATOM measures model weights on Hugging Face. This note measures citations of the families'
technical reports, and commit activity of organization repositories in one Evidaxis snapshot.

**Reports.** Each family has a fixed list of generation reports (arXiv ids in `build.py`)
plus every arXiv hit whose title leads with the family name and says "technical report"
within the first six words. Derivative titles that only contain the name later, such as
Lawyer LLaMA and the FoundationAI Llama reports, stay in `reports.csv` as
`title_search_excluded` and are not in the sums. 5 titles are excluded that way.
Qwen-Image is arXiv `2508.02324`, from the Qwen title search.

**OpenAlex link.** Each report is looked up at `https://api.openalex.org/works/doi:10.48550/arXiv.<id>`.
When a preprint and a version of record are separate OpenAlex works, the higher `cited_by_count` is kept and the two are not added.
A work that carries the arXiv DOI together with any other publisher DOI is a contaminated merge: its count is not used, and a same-title work with 0 citations is not entered as zero.
The journal DOI named on the arXiv record is the version of record. DeepSeek-R1 names `10.1038/s41586-025-09422-z`.
On a linked work, OpenAlex omits a year that has no citations. Those years are 0 in the sum.
`counts_by_year` has a year and a count. It has no month. 2026 is therefore not compared with the same months of 2025.

**Reports outside the sum.** Every canonical or title-search report that is not in the sum has a `why` cell in `reports.csv`.

- `2407.21783` (Llama, The Llama 3 Herd of Models). OpenAlex merges doi:10.48550/arXiv.2407.21783 with unrelated DOI(s): 10.4230/lipics.giscience.2025.3, 10.4230/oasics.dx.2024.25. That count is not used. A same-title work with 0 citations is not entered as zero.

Rows that stay in the sum, with a note:

- `2501.12948` (DeepSeek). OpenAlex display_name does not match the arXiv title. The only publisher DOI on the kept work is 10.1038/s41586-025-09422-z, so the count is kept.
- `2307.09288` (Llama). OpenAlex display_name does not match the arXiv title. The only publisher DOI on the kept work is 10.48550/arxiv.2307.09288, so the count is kept.
- `2402.00838` (OLMo). Preprint and version of record are separate OpenAlex works. The higher cited_by_count is kept and the two are not added.

**Repositories.** From `data/snapshots/2026-10-17/snapshot.json`, organization owners only
(`etl/owner_types.json`). The owner login must be the lab: `QwenLM`, `QwenAudio`,
`deepseek-ai`, `meta-llama`, `InternLM`, `mistralai`. Gemma, OLMo, GLM, Kimi, and Phi use
the company login and a name test (`gemma`, `olmo`, `glm`, `kimi`, `phi`). Personal
accounts are not listed. `recent_weekly_commits` is the mean of the last 12 weeks of
GitHub `commit_activity` on the default branch. The slope is the log-slope of the last
26 weeks. A median of 0 can sit next to a large sum: DeepSeek's 4 repositories sum to
1334 commits/week.

## Limits

- OpenAlex's citation graph is the source. Counts were not scaled to any other index.
- 2026 runs through the pull on 2026-10-18 and is not a finished year.
- The archive is the Evidaxis registry of code systems, not a full list of each lab's
  repositories. Llama's only match is `meta-llama/prompt-ops`.
- Default branch only. Work on other branches is outside this snapshot.
- The old DOI filter responses remain in `raw/openalex/doi-*.json` and `title-*.json`.
  The sums read `bydoi-*.json`, `sametitle-*.json`, and `vordoi-*.json`.

## Reproduce

```
python3 build.py --offline
```

`--offline` reads `raw/` and the snapshot. It does not use the network. It rewrites
`reports.csv`, `repos.csv`, `families.csv`, `chart.svg`, and this README.

`build.py --fetch` writes `raw/` from the arXiv API and OpenAlex. It needs
`OPENALEX_API_KEY` in the environment. Three tries are used so one dropped connection
does not turn a report into `not_found`. arXiv asks for 3 seconds between requests.

Standard library only.

## Cite

Evidaxis (2026). *Technical reports and repository activity of ten open model families.*
Research note, OpenAlex pull 2026-10-18, snapshot 2026-10-17.
https://github.com/evidaxis/evidaxis/tree/main/research/2026-10-open-model-families

Questions and corrections: hello@evidaxis.org
