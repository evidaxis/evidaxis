# Erratum 2026-09-14: the v2h.1 collector admitted post-freeze pins (frozen-panel drift)

> status: FIXED 2026-09-14 · class: correctness defect, the code did not implement its
> record (METHODOLOGY-FREEZE-2026-08-20, "Not frozen: correctness defects … fixed via
> dated errata") · found during the axis-3 verdict adjudication
> (`AXIS3-DEPS-V2H2-VERDICT-2026-09-14.md` §3.4, Finding A; effect 2 below was identified
> by the verdict's blind second opinion). No committed verdict, evaluation or published
> value is rewritten.

## What the record fixes

`AXIS3-DEPS-V2H1-SUPERSESSION-2026-07-21.md`, component 5: the frozen expanded panel is
the expansion manifest (sha256 `026eaa45377a…`) UNION the 41 v2h pins carried verbatim,
**90 systems / 628 packages**. "Later pin growth NEVER changes this panel (next change =
next superseding record)."

## What the code did

`collectors/t2_deps_v2h1_collect.py::load_panel()` read the manifest (sha-pinned,
correct), then **every** pin in `data/deps_id_map.json` (append-only, grown by the daily
snapshot) resolved through `etl/id_map.json`. Captured panel: 90 systems (baseline through
partition 2026-08-03) → 93 (08-10) → 97 (08-17, 08-24) → 99 (08-31) → 100 (09-07). Two
effects:

1. **Rows** for post-freeze systems (ten in capture files, the first three from partition
   2026-08-10). Such a system cannot vote before 14 confirmed-clean points.
2. **Exclusion.** Their package names joined `self_names`, the query's panel-wide
   self-dependent exclusion list, so a post-freeze package was removed from the dependent
   counts of FROZEN systems from the partition it entered. This effect is immediate and
   cannot be undone by filtering output.

None of the 90 frozen systems changed its package set; the manifest hash at HEAD equals
the hash at `aaeefa43`.

## Effect on committed results: no gating PASS/FAIL outcome changes

`collectors/replay_axis3_v2h1_frozen_panel.py` →
`data/quarantine/axis3-deps-v2/verdict-2026-09-14/replay-results.json`, built on a
read-only BigQuery pull of the excluded dependents at partitions 08-10 … 08-31 (same
folder; job `bqjob_r4b89e09caf3b99ec_000001a09fbe2911_1`, ≈ $12.9):

- The only excluded pair that touched a frozen system while it sat in the capture panel:
  `PYPI/langchain` as a direct dependent of the frozen `PYPI/langgraph`, partitions
  08-10 … 08-31, one dependent out of ~1,700.
- With that pair restored (EXACT), the sanity gate reproduces all 25 classifications, and
  the 08-17 / 08-24 / 08-31 evaluations reproduce every criterion PASS/FAIL outcome,
  rising set, vote, fragility flag, canary block and c3 flip. Values move slightly: c2
  0.2907 → 0.2908 at 08-17 and −0.0684 → −0.0683 at 08-31; largest z shift 0.002. An UPPER
  sensitivity scenario (every post-freeze package restored at every partition) gives the
  same outcomes (largest z shift 0.054).

## Fix (applied with this erratum)

`load_panel()` admits a legacy pin only if its `pinned_at` is at or before
`2026-07-21T17:02:25Z`, the first v2h.1 capture commit (`aaeefa43`) in UTC; a pin without
`pinned_at` is not admitted, since it cannot be shown to predate the freeze. At HEAD this
reproduces the frozen panel exactly, package sets included (90 systems / 628 packages, the
same 41 pins), pinned by a content hash in `tests/test_t2_deps_v2h1_frozen_panel.py`.
Effective from the next capture (tact 2026-09-21, partition 2026-09-14).

Consequences, disclosed before they are observed:

- Matched coverage returns to ~64 systems: the post-freeze systems leave, the frozen 90
  stay. Above both coverage contracts (floor 30; 0.90 × clean-series median 63).
- From partition 2026-09-14, `langgraph` is counted without the drift exclusion: one
  dependent more than the drifted query would have returned on the same partition. Its
  week-over-week change is not predicted here.
- Partitions 2026-08-10 … 2026-09-07 stay as captured (append-only). 09-07 was not
  reconstructed; its exclusion effect remains unquantified.
- The post-freeze systems stop receiving v2h1 points. Re-freezing an expanded panel is a
  choice for the m3 record; upstream history is retained, so a backfill stays possible.

*Positive-only note: internal methodology governance; no negative signal about any
measured system.*
