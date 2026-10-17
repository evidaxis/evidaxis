# Weekly release schedule, effective after operational acceptance

Recorded 2026-10-18. This is an operational change only. Methodology, axis
definitions, thresholds, sampling rules and the methodology freeze are unchanged.

The primary start is Saturday **02:17 UTC**, requested by the external
Cloudflare clock. Saturday 04:17 and 06:47 UTC ticks retry only when there is no
queued, active or successful attempt for the release date. GitHub's Saturday
**06:17 UTC** schedule remains a backup entrance to the same guarded workflow.
The date is the UTC Saturday being released, fixed before collection. Earlier
observation within Saturday can change source responses; capture timestamps
continue to record the real observation time.

Wednesday **02:17 UTC** runs a full rehearsal for the next Saturday through the
same collection and transformation path. The disposable candidate undergoes the
website checks and HF publication guard. Rehearsal performs no production
commit, push, HF upload, deployment, external timestamp or archival request.
Its artifact reports system counts against the previous snapshot, declared
departures against the existing max(25, 1%) ceiling, methodology version and
step durations. A green rehearsal is readiness evidence, not a release.

Release-chain changes merge by **Thursday 23:59 UTC** or wait a week. This
includes collection and publication code, workflow configuration, web build and
checks, registry activations and input-data activations. After the cutoff, only
necessary corrections identified by rehearsal may proceed, followed by another
full rehearsal for the intended date. Unverified late changes do not establish
readiness. No methodology change is authorized by this schedule.

**Released** means the production site at evidaxis.org and the public Hugging
Face dataset both serve the intended dated snapshot. A successful dispatch,
collection, git commit or CLI upload alone is not a release. Site verification
checks snapshot_date and methodology_version from the dated public JSON;
HF verification reads back the uploaded publication projection and CSV.
Partial delivery remains incomplete and must not be announced as released.

**12:00 UTC Saturday** is the internal release target, not a platform guarantee.
Late completion stays late. Four unattended on-time Saturdays, 2026-10-24,
2026-10-31, 2026-11-07 and 2026-11-14, plus the agreed failure checks are required
before claiming sustained reliability. Until then report the observed count.

Activation requires a successful full rehearsal and the external clock's own
observed tick. If acceptance is incomplete by Thursday 2026-10-22 23:59 UTC,
keep the previously accepted GitHub schedule for 2026-10-24 and do not count
that Saturday toward the new schedule's acceptance.
