# Erratum 2026-10-04: a false-zero commit_activity was recorded as a real zero

> status: FIXED 2026-10-04 · class: correctness defect: input integrity
> (METHODOLOGY-FREEZE-2026-08-20, "Not frozen: correctness defects … fixed via
> dated errata") · found in the weekly capture of 2026-10-03. No committed
> snapshot, score, or history row is rewritten.

## What the record says

Development velocity is the weekly totals from GitHub `stats/commit_activity`
(`methodology/m3.json`, axis `github_commit_velocity`). A rising vote on that
axis also requires an average of at least 5 commits over the last 12 weeks.
When that endpoint does not resolve (HTTP 202 through the retries), the
repository is absent from the snapshot. `collectors/completeness_gate.py`
records the absence as a declared gap. An unresolved response is not a zero.

## What the code did

`etl/collect.py` turned every HTTP 200 list into the recorded weekly series
(`weekly = [w["total"] for w in act]`) and into `recent_weekly_commits`. An
all-zero list was stored as a real zero. That zero fails the activity floor,
so the repository cannot be Rising on this axis. `collectors/shadow_backfill.py`
did the same with its own copy of the request: a non-empty all-zero list was
treated as genuine inactivity (`no nonzero weeks`), not as an unresolved
response. The weekly fetch layer cached the 200 body and served it back.
`collectors/t2_collect.py` does not read this endpoint. The census does not
record these weekly totals. `collectors/capacity_dry_run.py` counts the HTTP
call and does not store weekly totals.

## Evidence

Observed 2026-10-04, organisation-owned repository only:

- Snapshot 2026-10-03 records `NousResearch/hermes-agent` (`e_TEXN6TK2CRK`)
  with `recent_weekly_commits` 0.0, 52 weekly totals of 0, and
  `stars_not_scored` 250991.
- `GET /repos/NousResearch/hermes-agent/commits?since=2026-07-11T00:00:00Z&per_page=1`
  returns 1 commit. The same request with `per_page=100` returns 100 commits,
  a full page.
- A same-day audit of zero-activity repositories: 79 of 80 in a random sample
  were true zeros, and 1 was false; 127 of 128 zero-activity repositories
  with at least 10k stars were true zeros, and 1 was false.

## Effect on committed results: none rewritten

Snapshots through 2026-10-03 stay as captured, including the false zero above.
Nothing in `data/` is rewritten by this erratum. Effective from the next
capture.

## Fix (applied with this erratum)

One helper, `collectors/commit_activity_integrity.py`, screens the body in
the fetch layer: `collectors/openalex_keyed_fetch.py` (installed as the frozen
collector's `_get_json` in the weekly pipeline) and `collectors/shadow_backfill.py`.
`etl/collect.py` stays byte-frozen; a refused body reaches it as the same `None`
an unresolved 202 produces. If the last 12 weeks are all zero, it makes
one `GET /repos/{repo}/commits?since=<start of that window>&per_page=1` with
the same auth as the stats call.

- One or more commits: the body is not trustworthy. The repository follows
  the existing unresolved path (absent from the snapshot; the completeness
  gate already records that gap). Weekly counts are not synthesised from the
  commits API. The methodology still measures `commit_activity`.
- An empty commit list: the zeros are kept.
- The probe fails: the zeros are kept, and the run counts the failure.

Each refusal is stored as repository plus run date in the fetch layer's run
summary (`summary-<pass>.json`: `commit_activity_false_zero_refused`,
`commit_activity_probe_failed`) and on the backfill manifest; the summary line
prints both counters. The commits response
itself is not stored.

Consequences, disclosed before they are observed:

- Some refusals may persist week after week (the stats endpoint can keep
  answering zeros for an active repository). Recording such repositories from
  `GET /repos/{repo}/commits` week by week measures the same quantity
  (default-branch commits per week) from another endpoint; that is a source
  change for the next methodology record, not part of this correction.

- A refused repository is a declared gap for that capture, on the same terms
  as a stats 202 that did not resolve. It is not a published zero, and it
  does not vote.
- A later capture that receives a non-zero `commit_activity` body records
  that body. The probe is not used.
- A probe that fails does not open a gap. The zero stands, and the counter
  shows that the confirmation did not run.

*Positive-only note: internal methodology governance; no negative signal about
any measured system.*
