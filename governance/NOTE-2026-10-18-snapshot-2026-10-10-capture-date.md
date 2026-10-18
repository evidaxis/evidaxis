# Capture date of the snapshot labelled 2026-10-10

Recorded on 2026-10-18. This note clarifies the weekly label; it does not
change methodology, measurements, archived bytes or snapshot identity.

`2026-10-10` identifies the weekly release scheduled for Saturday 10 October.
It is not a claim that collection happened on that Saturday. The Saturday
attempt (weekly-snapshot run 38052906586) failed because the preflight found
11 seeded repositories unavailable on GitHub (REST 404/410/451), as recorded
in `governance/AXIS3-DEPS-V2H-LIVE-LOG.md`.

The successful recovery collection ran on Monday 12 October 2026:

- [weekly-snapshot run 38238844886](https://github.com/evidaxis/evidaxis/actions/runs/38238844886)
  started at 10:50:35 UTC and was last updated at 14:03:27 UTC, with conclusion
  `success`.
- Both `data/snapshots/2026-10-10/snapshot.json` and its `provenance.json`
  record `captured_at: 2026-10-12T12:11:36+00:00`. This is the recorded capture
  timestamp, not a claim that every source request occurred at one instant.
- Snapshot commit `805733af2d67673662475e9fb1d91e0bc195d75c`
  (`snapshot: weekly heartbeat (provisional, automated)`) has author time
  2026-10-12 14:02:46 UTC and commit time 2026-10-12 14:02:50 UTC.

The weekly label and directory stay `2026-10-10`. No data is changed, relabelled
or recollected, and the old snapshot is not recomputed. Its original files,
checksums and identity remain addressable under that date (Constitution
invariants 4 and 6). The actual recorded collection time remains visible in
the two `captured_at` fields above; the workflow run records the execution
window, and git records when the snapshot entered the archive.
