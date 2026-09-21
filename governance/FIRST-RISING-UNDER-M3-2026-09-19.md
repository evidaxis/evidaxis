# First Rising systems under methodology m3 (snapshot 2026-09-19)

> status: FILED 2026-09-21 at the 2026-09-21 tact, as the m3 implementation record required
> ("if the 2026-09-19 snapshot has Rising systems, write the first-Rising disclosure record") ·
> class: disclosure of evidence behind a published status · positive-only: this records why two
> systems met a published threshold; it is not a comparison against, or a claim about, any other
> system.

## What the snapshot published

Snapshot `fcfd3a7ccdcb`, methodology **m3**, 212 entities, first snapshot scored with the third
axis. **Two systems carry `status: rising`.** The dry run on 2026-09-12 data named the same two,
so the outcome is the one the implementation record predicted, not a surprise.

Under m3, Rising requires convergence on any two axes of three. Both systems converge on the same
two: GitHub commit velocity and direct-dependents momentum. Neither has a citation signal.

## Evidence per system

### Qwen Code · `e_X33782S1M13` · `QwenLM/qwen-code` · cohort coding-agents

| field | value |
|---|---|
| momentum | 73.7, percentile 100, confidence high |
| commit velocity | slope 0.0538, cohort z **2.209**, 264.6 recent weekly commits |
| citation momentum | absent, 0 total citations |
| dependents momentum | scored, slope 0.06939, Theil-Sen 0.068318, cohort z **1.575** |
| dependents, latest | 20, as of partition 2026-08-31 |
| points / reconstructable | 22 / 15 |
| veto checks | `unstable: false`, not vetoed; `rising_vote: true` |
| dependent ecosystem (`eco_top`) | all 20 direct dependents in **NPM**, single ecosystem |

Stars, 27,986, are recorded and **not scored**.

### AgentScope · `e_97SYW64PA3G` · `agentscope-ai/agentscope` · cohort agent-frameworks

| field | value |
|---|---|
| momentum | 78.2, percentile 100, confidence high |
| commit velocity | slope 0.0830, cohort z **2.354**, 20.2 recent weekly commits |
| citation momentum | insufficient, 9 total citations (2024: 2, 2025: 4, 2026: 3) |
| dependents momentum | scored, slope 0.058761, Theil-Sen 0.051667, cohort z **2.158** |
| dependents, latest | 30, as of partition 2026-08-31 |
| points / reconstructable | 22 / 15 |
| veto checks | `unstable: false`, not vetoed; `rising_vote: true` |
| dependent ecosystem (`eco_top`) | all 29 direct dependents in **PyPI**, single ecosystem |

Stars, 31,959, are recorded and not scored.

## Limits a reader should carry

**The dependents axis rests on small counts.** Twenty and thirty direct dependents. The slope is
fitted on 22 points of which 15 are reconstructed from BigQuery history under the dated
`RIGHTS-BASIS` append, and both systems clear the cohort z threshold on a cohort that is itself
small. A handful of dependents added or removed moves these numbers.

**Both are single-ecosystem.** Every direct dependent of Qwen Code is an NPM package, every direct
dependent of AgentScope a PyPI package. The axis measures adoption inside one packaging ecosystem
per system, not adoption across the field. Composition shift is exactly what `eco_top` exists to
expose, and here there is nothing to shift.

**Neither has a citation signal.** One is absent, one insufficient at 9 citations. Convergence is
carried by two axes that both read developer activity, so they are less independent of each other
than the two-of-three rule implies.

**The partition captured after the cutoff moves one of them down.** The 2026-09-14 capture, taken
2026-09-21 and not part of this evaluation, records 20 direct dependents for Qwen Code, unchanged,
and 29 for AgentScope, one fewer than the 30 that scored. Nothing is restated on that basis; it is
noted so the next tact is read against it.

## Provenance

Evaluation artifact `data/quarantine/axis3-deps-v2/eval/v2h1-live-2026-09-07-e31a124a6157.json`
(cutoff 2026-09-07, 47 voting, 6 rising in the axis evaluation, 0 unstable-vetoed, criteria
6 of 6 PASS). Snapshot entity records in `data/snapshots/2026-09-19/snapshot.json`. Dependent
observations in `data/observations/2026-09-21/deps_v2h1-2026-09-14.jsonl`, panel manifest
`026eaa45377a…`, source deps.dev via BigQuery `bigquery-public-data.deps_dev_v1`, CC-BY 4.0.
