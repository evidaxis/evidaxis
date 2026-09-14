# Verdict: m3-deps axis (v2h.2) — promotion gate MET; the axis leaves live quarantine

> status: FIXED 2026-09-14, the verdict date named by `METHODOLOGY-FREEZE-2026-08-20.md`
> (no slip). Adjudicates the promotion gate of
> `AXIS3-DEPS-V2H1-SUPERSESSION-2026-07-21.md` as modified by
> `AXIS3-DEPS-V2H2-SUPERSESSION-2026-08-18.md` (c4 → c4′, forward-only effectivity).
> Neither record is edited. Measurand, frozen panel, estimator, sanity gate, canary and
> fragility veto are **UNCHANGED** by this record.
> Evidence = committed artifacts only. The running accounting in
> `AXIS3-DEPS-V2H-LIVE-LOG.md` is re-derived here, not inherited (it overcounts, §2.1).
> Second opinion: blind Codex consult; SLIP on first review, PROMOTE (0.94) after the
> closure evidence (§6).
> Keeper: this record exercises the standing keeper CONFIRM of 2026-07-11
> (`DRAFT-m3-quarantine-adjudication.md`: promotion approved contingent on the
> pre-registered criteria passing; enters as methodology m3, never mutating m2 rows).
> The keeper may recall this record by a dated note until the m3 implementation record
> is committed.

## 1. Verdict

**PROMOTION GATE MET.** All five clauses hold on committed artifacts (§2). Three
findings are disclosed (§3.4). None changes any gating PASS/FAIL outcome; for the most
serious one (panel drift in the collector) an exact equivalence replay, backed by a
read-only BigQuery pull, reproduces every vote and every criterion outcome (§3.4, A).

What this commit changes: the axis status (live quarantine → promoted, implementation
pending) and the end of the methodology freeze (§5).
What it does **not** change: no published snapshot, scored field, registry row, cohort
verdict or site string. The axis enters scoring only through a separate dated forward
record (methodology **m3**) that carries the obligations of §4; m2 rows are never
mutated.

## 2. Gate, clause by clause

Commit anchors: v2h.1 record `0e2271a5` (2026-07-21 14:46 +01:00) · first v2h.1 capture
`aaeefa43` (2026-07-21 18:02 +01:00) · v2h.2 record `b69bbf28` (2026-08-18 09:21:29 +02:00).

### 2.1 Forward partitions — MET, at the floor: 3 of 3

Confirmed-clean cutoffs whose partitions were captured strictly after `b69bbf28`:

| partition | captured in | confirmed CLEAN by its successor | evaluation |
|---|---|---|---|
| 2026-08-17 | `715f105c` (2026-08-24) | `sanity-check-98bab4ff31d3` (`5dcd29e0`, 2026-09-01) | `v2h1-live-2026-08-17-2da01f9e926f` |
| 2026-08-24 | `5dcd29e0` (2026-09-01) | `sanity-check-9ec385dfa6be` (`5344e700`, 2026-09-07) | `v2h1-live-2026-08-24-4cd020c1add4` |
| 2026-08-31 | `5344e700` (2026-09-07) | `sanity-check-3ce743562e36` (`13742753`, 2026-09-14) | `v2h1-live-2026-08-31-e34f80ae4f53` |

**Accounting correction.** The live log counts four (2026-09-14 entry: "2026-08-10, 08-17,
08-24, 08-31 (four; three were required)"); its 2026-09-07 entry already claimed "three of
the three" with 08-10 included, one week early. Partition 2026-08-10 was captured in
`eb918a11` at 2026-08-18 09:10:25 +02:00, **eleven minutes before** the v2h.2 record,
which names the window explicitly as upstream partitions 08-17 / 08-24 / 08-31. It is
struck from the forward count and remains a historical diagnostic (§3.2).
This is the second miscount of one class (the first, corrected 2026-08-18, counted a
baseline partition): a partition captured before the governing record was counted toward
that record's forward floor. Outcome-neutral here, since the correct count meets the
floor; the remedy is mechanical accounting (§4.3).

### 2.2 28-day live quarantine — MET

Matured 2026-08-18, counted from `aaeefa43`; unchanged since the v2h.2 adjudication.

### 2.3 Criteria 1, 2, 4′, 5, 6 at every forward cutoff; no canary HOLD, no fragility INDETERMINATE — MET

Every artifact names `axis3_v2h1_eval_2` and `AXIS3-DEPS-V2H2-SUPERSESSION-2026-08-18.md`:
the criteria version matches the record under which promotion is claimed (v2h.2 §3
validity condition).

| cutoff | voting / rising | c1 (≥ 30) | c2 r (pairs; \|r\| < 0.5) | c4′.a panel share | c4′.b rising cohorts | c5 · c6 | canary HOLDs · min agreement (n ≥ 3) | fragility vetoes |
|---|---|---|---|---|---|---|---|---|
| 2026-08-17 | 48 / 8 | 43 | 0.2907 (32) | 0.1667 | 4 | PASS · PASS | 0 · 0.929 | 0 |
| 2026-08-24 | 47 / 6 | 45 | 0.1066 (38) | 0.1277 | 2 | PASS · PASS | 0 · 0.938 | 0 |
| 2026-08-31 | 47 / 6 | 46 | −0.0684 (38) | 0.1277 | 3 | PASS · PASS | 0 · 0.941 | 0 |

c4′.b sits at its floor (2) at 2026-08-24, as v2h.2 §3 declared it might.

*Reading named and rejected:* that v2h.1 clause 3 ("at EVERY confirmed-clean live
cutoff") still binds the pre-v2h.2 live cutoffs 07-20 / 07-27 / 08-03 under the retired
per-cohort c4. v2h.2 §4 fixes the operative cutoff set explicitly; the retired definition
is no longer a criterion; applying c4′ to those cutoffs is forbidden as gate evidence.
At the three forward cutoffs nothing fails under the operative criteria. The historical
c4 FAILs at 07-13 … 08-03 stay on record as diagnostics (§3.2); c1/c2/c5/c6 passed at
every live cutoff.

### 2.4 Clause-4 flip condition — MET

c3 PASS at each of the three forward cutoffs. At the official cutoff 2026-08-31 the
fully-forward transitions (both endpoints captured by the live path after the v2h.1
record, which defines "fully-forward"; v2h.2 does not touch c3) number six, all under the
0.30 bound: 07-20→07-27 0.0417 · 07-27→08-03 0.0625 · 08-03→08-10 0.0 · 08-10→08-17 0.0 ·
08-17→08-24 0.0 · 08-24→08-31 0.0638.

*Reading named and rejected:* re-basing "fully-forward" on the v2h.2 record, which leaves
two transitions (0.0 and 0.0638). v2h.2 supersedes only c4; importing a stricter
transition floor at the moment the gate binds is the mirror image of waiving a criterion
when it binds. Disclosed so the choice is visible.

### 2.5 Promotion artifact with five separated sections — MET by §3

## 3. Promotion artifact (five separated sections; collapsed columns = reject)

### 3.1 Frozen backtest (non-gating by construction)

`v2h1-baseline-2026-07-21-0c0af7876879` (eval_1; official cutoff 2026-07-06; 14
confirmed-clean partitions, corrupt pair 06-11 / 06-15 excluded): 47 voting / 9 rising /
1 leave-one-out veto; c1 46 PASS · c2 0.2985 PASS · c3 PASS · c4 (retired per-cohort form)
FAIL · c5 / c6 PASS. The baseline can terminate, never promote; it was used for neither.

### 3.2 Historical diagnostics (never gate evidence)

- Live cutoffs 2026-07-13 (baseline-captured, struck from the live count 2026-08-18),
  07-20, 07-27, 08-03 under eval_1: 5/6, c4 FAIL (small-cohort unattainability, v2h.2 §2).
- The same four under c4′: 6/6 (`v2h1-diagnostic-*`; panel shares 0.146 / 0.188 / 0.188 /
  0.146).
- 2026-08-10 under eval_2: 6/6 (`v2h1-live-2026-08-10-6ce2bdea386e`); captured before the
  v2h.2 record (§2.1), therefore diagnostic.

### 3.3 Forward holdout

The three cutoffs of §2.1, the criteria table of §2.3 and the transitions of §2.4.
Sealed-envelope property: none of the three partitions had been captured when c4′ was
fixed.

### 3.4 Operational integrity

- **Sanity gate.** Calibration `3e51319d9817` unchanged since before the first capture.
  Every forward check flags exactly the challenge set {2026-06-11, 2026-06-15}; fire-rate
  at the latest check 2 of 25 partitions, both of them the declared challenge set;
  kill-bar PASS each week.
- **Capture path.** One scan per SnapshotAt via `t2_deps_v2h1_collect.py`; panel manifest
  sha256 `026eaa45377a…` identical at `aaeefa43` and at HEAD; retention tripwire earliest
  partition 2023-04-10 at every forward sidecar (no upstream pruning observed). Cost of
  the forward window ≈ $14 (four captures), as estimated in v2h.2 §4. The 2026-09-14 tact
  was executed by Claude after the delegated Codex sandbox could not reach gcloud
  credentials: transport, not methodology.
- **Finding A: panel drift in the collector.** `load_panel()` built the panel as the
  sha-pinned manifest UNION the live `data/deps_id_map.json`, so pins added after the
  freeze entered the captures: 90 systems (through partition 08-03) → 93 (08-10) → 97
  (08-17, 08-24) → 99 (08-31) → 100 (09-07). The v2h.1 record says later pin growth NEVER
  changes this panel. The drift has two effects. (1) Rows for post-freeze systems: undone
  by filtering to the frozen 90; such a system cannot vote before 14 clean points. (2) Their
  package names joined the query's self-dependent exclusion list, which is panel-wide, so
  a post-freeze package was silently dropped from the dependent counts of FROZEN systems.
  Filtering output cannot undo (2); the blind second opinion identified this (§6). The
  equivalence replay is therefore built on a read-only BigQuery pull of every direct,
  highest-release dependent at the four drift partitions that is a post-freeze package
  (job `bqjob_r4b89e09caf3b99ec_000001a09fbe2911_1`, 2.06 TiB ≈ $12.9, 615 rows; query,
  job and rows in `data/quarantine/axis3-deps-v2/verdict-2026-09-14/`). Replay:
  `collectors/replay_axis3_v2h1_frozen_panel.py` → `verdict-2026-09-14/replay-results.json`,
  running the committed gate and evaluator code with only their loaders swapped. The
  reconstruction of each capture's panel is proven, not assumed: the SQL rebuilt from it
  hashes to the `query_sha256` recorded in every capture manifest from 08-03 (pre-drift
  control) to 09-07, and the pull covers every post-freeze package name. Exactly one
  excluded dependent touched a frozen system while it sat in the capture panel:
  `langchain` as a direct dependent of the frozen `langgraph` package, partitions
  08-10 … 08-31 (one dependent out of ~1,700). With it restored (EXACT), the sanity gate
  reproduces all 25 classifications, and at 08-17 / 08-24 / 08-31 every criterion
  PASS/FAIL outcome, rising set, vote, fragility flag, canary block and c3 flip is
  identical. Values move slightly: c2 0.2907 → 0.2908 (08-17) and −0.0684 → −0.0683
  (08-31); largest z shift 0.002. An UPPER sensitivity scenario (every post-freeze package
  restored at every partition, adding `freetoken` → `gguf`) gives the same outcomes
  (largest z shift 0.054); it is a scenario, not a bound over intermediate cases, and the
  verdict rests on EXACT. **Non-material to this verdict.** The collector is brought back
  into conformance by `ERRATUM-2026-09-14-v2h1-collector-panel-drift.md` (§4.1).
- **Finding B: forward-count miscount** (§2.1).
- **Finding C: canary floor never re-derived.** The v2h.1 record declared
  `CANARY_AGREEMENT_FLOOR = 0.8` "provisional … to be empirically re-derived at the first
  live cutoff and then frozen"; no re-derivation was recorded, and the freeze forbids
  doing it now. This verdict uses the unchanged 0.8. Sensitivity: a HOLD at any forward
  cutoff needs a floor above 13/14 ≈ 0.9286 (the lowest agreement among cohorts with
  n ≥ 3 across the three forward cutoffs), while any floor derived from clean history that
  does not HOLD the clean history itself sits at or below 10/11 ≈ 0.9091 (the lowest
  clean-history agreement, baseline). The canary is one-way: it withholds, never grants.
  An acknowledged procedural deviation; the sensitivity does not replace the calibration,
  which moves to the m3 record (§4.2).

### 3.5 Gate, canary and fragility reports

Across all 13 v2h.1 evaluation artifacts (1 baseline, 4 diagnostic, 8 live): status
EVALUATED at every one; canary HOLDs 0; fragility vetoes 1 (baseline, leave-one-out) and
0 at every live and diagnostic evaluation. Minimum per-cohort agreement (n ≥ 3): 0.909 at
baseline; 0.938–0.941 at the pre-record live cutoffs; 0.929 / 0.938 / 0.941 at the
forward cutoffs.

## 4. Obligations carried into the m3 implementation record (not effective here)

1. **Panel.** The conformance fix (pins admitted only if pinned before the first v2h.1
   capture) is applied by the erratum, effective from the next capture. Partitions
   2026-08-10 … 2026-09-07 keep their drift, append-only; 08-10 … 08-31 are quantified in
   `replay-results.json`, 09-07 was not reconstructed and its exclusion effect remains
   unquantified. It cannot overturn the CLEAN status of 08-31: the largest move at 08-31
   among systems with ≥ 5 dependents is |log| 0.2231, a third of the calibrated reversal
   bound 0.6931, so no reversal can complete at 09-07. Re-freezing an expanded panel, if wanted, is a choice
   for the m3 record; upstream history is retained, so a backfill stays possible.
2. **Canary floor.** Derive and freeze it by a stated procedure from confirmed-clean
   history.
3. **Promotion accounting by code.** Any forward floor is counted mechanically from
   capture-commit timestamps against the governing record's commit, never in prose.
4. **Estimand honesty.** Every published m3 claim carries the frozen-panel estimand of
   the v2h.1 record (trajectory of the package set selected and linkage-verified as of
   2026-07-21; residual survivorship disclosed, not denied).
5. **Entity-adjacent language.** m3 strings next to system names pass the entity-lexicon
   guard (`LEXICON-SEMANTICS-2026-08-20.md`); promoting an axis is not a statement about
   any system.

## 5. Methodology freeze

`METHODOLOGY-FREEZE-2026-08-20.md` ends at this record's commit; its slip protocol is not
triggered. Proposals from the dated public queue become admissible for the m3 record.
Weekly captures continue; the series stays append-only.

## 6. Second opinion

Blind Codex consult (`codex-run --profile consult`, companion `evidaxis-axis3-verdict`,
2026-09-14), given the gate question, the sources and the raw session findings, not this
record's position.

**First review: SLIP THE VERDICT, confidence 0.88.** Agreed with this record: the forward
count is three (08-10 excluded by capture-commit time); the old c4 failures are not a
standing veto; "fully-forward" keeps the v2h.1 live→live meaning (six transitions, max
flip 0.0638); no fresh keeper decision is needed for a conforming promotion; promotion
must not rewrite m2 or history, nor change panel, thresholds, admission, activation or
canary semantics. Grounds for the slip, and their disposition:
1. No five-section promotion artifact at HEAD → §3 of this record.
2. An output-filter replay cannot recover dependents removed inside the query by the
   panel-wide self-name exclusion → correct, and the decisive catch of the review. Closed
   by the BigQuery-backed replay, committed with its script (§3.4, A).
3. The missed canary re-derivation needs an explicit disposition → §3.4 C and §4.2.
4. A dated erratum and a committed replay → the erratum and `verdict-2026-09-14/`.

**Follow-up on the closure evidence: PROMOTE, confidence 0.94**, no new observation
required. It independently rebuilt each capture's SQL from the observation rows and
package sets and matched `query_sha256` for all five affected captures, recomputed the
single EXACT correction (`langchain` → `langgraph`, four partitions) and confirmed that
no PASS/FAIL outcome, rising set, fragility flag, canary or flip block changes; judged
the collector fix correct (full panel match at `aaeefa43`, 90/628) and right to ship with
the erratum as restoration of an established contract; found no blocker. Its wording
corrections are applied above: outcomes rather than values are invariant (c2 moves by
0.0001); the historical c4 FAILs are not erased; 09-07 is unquantified; the canary
sensitivity is stated on the unrounded 13/14; UPPER is a scenario, not a bound. Its two
hardening suggestions are applied: the replay checks query hashes and name coverage, and
the collector test pins the panel's content hash, not only its size.

*Named and rejected: (i) promotion on "four clean forward partitions": the count is three,
and a verdict must not rest on the overcount class the 2026-08-18 record corrected;
(ii) slipping the verdict on the second opinion's first-review grounds once each was
closed with exact, committed evidence: the replay re-reads the same partitions and touches
no criterion, threshold or outcome-bearing choice, so a slip would wait for no new
information; (iii) re-deriving the canary floor before the verdict: a threshold changed at
the moment it binds; (iv) the two stricter re-readings of clauses 3 and 4 (§2.3, §2.4).
Positive-only note: internal methodology governance; no negative signal about any
measured system.*
