# Release gates, effective 2026-11-10

Recorded 2026-11-10. This is an operational rule for the weekly release chain.
Methodology, axis definitions, thresholds and the methodology freeze are unchanged.
It extends `governance/RELEASE-SCHEDULE-2026-10-18.md` and does not rewrite that record.

## Friday rehearsal

Friday **02:17 UTC** (`17 2 * * FRI` on the release clock) runs a second full
rehearsal. The dispatch is `mode=rehearsal` with `release_date` set to the next
Saturday, one day ahead. Wednesday **02:17 UTC** stays the first full rehearsal,
three days ahead. Saturday **02:17 UTC** stays the release.

The Friday rehearsal checks exactly the code Saturday will run, and the world
as it stands from Thursday through Friday. Wednesday still runs before the
Thursday cutoff, so it does not see later chain changes.

Both rehearsals keep the title `weekly rehearsal <Saturday>`. Observers that
read that title, including the release scoreboard, are unchanged. Wednesday
and the Saturday ticks still treat any active or successful run with that
title as the attempt, including a manual rehearsal created earlier in the week.
Friday counts only runs whose `created_at` is at or after 00:00 UTC on Friday.
A matching run with no parseable `created_at` is incomplete data. The tick
stops. It does not skip the run and it does not dispatch.

## Check changes

Monday and Tuesday are for merging changes to the release chain. Wednesday
02:17 UTC is the first full rehearsal. Thursday 23:59 UTC is the cutoff. After
the cutoff, changes to protected checks wait until the next week. Friday
02:17 UTC rehearses the post-cutoff code. Saturday 02:17 UTC is the release.

Protected checks change only through a pull request.
`scripts/gate_change_guard.py` rejects a direct push to main that changes a
path in `scripts/gate-paths.json` unless that commit belongs to a pull request
merged into main. The authenticated `github-actions[bot]` push sender stays
exempt. Privacy-check changes also require Codex review. On the pull request,
the replay runs the benign-drift drill and the leak drills against the latest
full candidate, then site `verify` on that candidate.

## Probation

A new data check that has not yet passed on a full candidate lives in
`*.probation.test.ts` until the first full rehearsal after it is added.
On a pull request the file blocks. In deployment it runs without the right
to block publication. A red result opens a repair task and leaves the site
release to the checks that already have that right. Promotion is renaming
the file after a green rehearsal. Age does not promote it. A check still in
probation after 14 days is to be listed by the release scoreboard; that listing
is not implemented yet and is tracked in the release plan.
