# Retraction-by-tag: both m3-v2h evaluation artifacts are INVALID_INPUT

> Dated keeper note, 2026-07-21. Artifacts are retained verbatim (immutability:
> retraction-by-tag, never deletion). Council-reviewed decision (7-model
> consilium 2026-07-21; synthesis in the keeper's planning layer).

**Retracted as INVALID_INPUT — not as FAIL:**

1. `baseline-2026-07-06-*.json` (baseline evaluation, computed 2026-07-16)
2. `live-2026-07-13-40a4b825f5d2.json` (live cutoff #1 evaluation, computed 2026-07-21)

**Grounds.** Both evaluations computed slopes/z-scores/criteria across two
upstream partitions now established as corrupt (2026-06-11, 2026-06-15:
panel-wide value collapse with recovery, coverage 22/25 vs 31 on every clean
partition — see the data-integrity finding in
`governance/AXIS3-DEPS-V2H-LIVE-LOG.md`). The observations were captured
correctly and remain valid archive records; their FITNESS FOR INFERENCE was
never established. Criteria verdicts computed on unfit input are not
"failed criteria" — they are void. No m3-v2h criteria verdict currently stands.

The mechanical detection basis: `collectors/data_sanity_gate.py --check`
flags exactly these two partitions (stage-1 coverage contract: matched 22 and
25 < 30, the PRE-REGISTERED c1 floor — no post-incident constant involved;
stage-2 symmetric reversal rule additionally fires on 2026-06-11 with
reversal-share 1.0 against a corpus-calibrated threshold of 0.21).
Check artifact: `../sanity-check-ada7ae0bbb9b.json`.

**What this does NOT assert:** no claim about deps.dev's internal cause; the
partitions are quarantined as unfit-for-inference, not adjudicated as
"proven corruption" (council language discipline).

**Consequences.** The live floor state ("1/4 captures") recorded in the live
log is void along with the verdicts; the restart plan (superseding record with
the two-stage sanity gate + panel expansion) supersedes it. This note is
append-only history; it does not modify the retracted files.
