# Release clock P2: local acceptance, 2026-10-17

P2 is implemented in the `ops/release-clock` working tree. No push, merge,
workflow dispatch, Worker deployment or production publication was performed.
Live acceptance is still required. No other agent or model generated this work.

Local commits could not be created: this worktree's Git administrative directory
is outside the writable sandbox. `git add` failed with `index.lock: Operation
not permitted`. No index entries were staged. The intended commit author is
`Evidaxis <git@evidaxis.org>` and the suggested message is
`ops: guard weekly releases and add external clock and rehearsal receipts`.

Changed files:

| Files | Result |
| --- | --- |
| `.github/workflows/weekly-snapshot.yml` | Dated entry, guard before admission and after queueing, full rehearsal, candidate web/HF checks, report, strict dated HF upload |
| `.github/workflows/deploy-web.yml` | Serialized production deployment, rehearsal/router exclusion, private CLI streams, content receipt |
| `.github/workflows/t2-daily-snapshot.yml` | Only `queue: max`, preserving pending daily writes |
| `.github/workflows/hf-mirror.yml` | Same pinned HF dependency as weekly |
| `infra/clock/worker.js`, `logic.mjs`, `logic.test.mjs`, `wrangler.toml`, `.gitignore`, `README.md` | Four scheduled ticks, exact run matching, post-dispatch observation, safe error handling, tests and operator commands |
| `scripts/release_guard.py`, `tests/test_release_guard.py` | UTC Saturday validation and archive/success guard |
| `scripts/rehearsal_report.py`, `tests/test_rehearsal_report.py` | Aggregate system/departure comparison, existing cap, methodology and step durations |
| `scripts/deploy-receipt.mjs`, `scripts/deploy-receipt.test.mjs`, `scripts/vercel-deploy.mjs` | Pure receipt validation, network reader, transport-only retry and output suppression |
| `scripts/hf_upload_snapshot.py`, `tests/test_hf_upload_snapshot.py` | Read back both projected files; failures stay nonzero |
| `scripts/zenodo_publish_version.py`, `scripts/zenodo_quarterly_stage.py` | Remove two pre-existing unused `noqa: E402` comments so the requested full Ruff command passes; no behavior change |
| `governance/RELEASE-SCHEDULE-2026-10-18.md` | Start, fallback, rehearsal, cutoff, release definition, internal deadline |
| This report | Local evidence, operator prerequisites and remaining limits |

The implementation does not edit `etl/`, `collectors/`, `methodology/`,
`web/src`, canary data/guards, historical governance records, freshness sensors
or `liveness-check.yml`. The web verification command regenerates tracked
foundation fixtures; those local verification outputs are restored before handoff.

Local validation:

```text
PYTHONPATH=. .venv/bin/pytest tests/ -q
exit 0; 6,937 collected cases, one expected skip
SKIPPED tests/test_recall_fixture.py:49: census working data absent (gitignored)

.venv/bin/ruff check etl tests collectors scripts
All checks passed!

node --test scripts/*.test.mjs infra/clock/*.test.mjs
tests 53; pass 53; fail 0; skipped 0

python3 -c "import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]" \
  .github/workflows/weekly-snapshot.yml .github/workflows/deploy-web.yml
exit 0

Additional YAML parsing: hf-mirror.yml, t2-daily-snapshot.yml
31 embedded shell steps: bash -n passed
git diff --check: passed

MODE=release INPUT_DATE=2026-10-17 GITHUB_OUTPUT=/tmp/release-clock-guard-output \
  .venv/bin/python scripts/release_guard.py
already exists (уже есть): 2026-10-17; no collection or commit
date=2026-10-17; mode=release; skip=true
```

There was no `.venv` initially. Network package installation was unavailable.
A local environment was created from the existing installed package set, then
`pip install --no-index -r requirements-dev.txt` confirmed every pinned dependency
was satisfied. Local runtimes: Python 3.14.7 and Node 25.2.1; workflow runtimes
remain Python 3.12 and Node 22. No runtime dependency was added to scripts or
collectors. HF is pinned to `2.1.1`; Vercel CLI is pinned to `48.2.9`.

Additional web verification used the unchanged lockfile and locally installed
dependencies, with `EVIDAXIS_DATA_DIR` explicitly pointing to this checkout's
current data. `npm run verify` exited 0: 27 test files / 250 tests passed,
26,161 pages built and checked, `check-dist: PASS`, Card B consistency checked
3,181 cards with 0 discrepancies, and badge checks parsed 102,301 SVG files with
0 discrepancies. Eleven meta-description length warnings remain in the
unchanged site. This does not substitute for collecting the 2026-10-24 rehearsal
candidate. Generated foundation fixtures were restored; there is no web diff.

Mutation evidence: actual implementation files were changed temporarily, the
tests were run, and original source was restored in a `finally` block. Every
mutation exited nonzero with assertion failures, not collection/import errors.
All **30 new test cases** (18 pytest cases, 12 Node tests) failed under at least
one of **20 deliberate defects**. The final unmodified suites passed again.

| Deliberate defect | Newly added cases that failed |
| --- | ---: |
| Remove date validation/resolution | 7 |
| Corrupt the returned explicit date | 1 |
| Remove archive/success guard | 3 |
| Remove success-history pagination | 1 |
| Remove date-routing dispatch | 1 |
| Report candidate as previous snapshot | 2 |
| Make incomplete rehearsal report green | 1 |
| Stop comparing HF public bytes | 1 |
| Turn HF upload failure into success | 1 |
| Accept stale site content unconditionally | 1 |
| Return an empty valid receipt | 1 |
| Remove Vercel transport retry | 2 |
| Use the wrong Worker release date | 3 |
| Ignore branch when matching runs | 1 |
| Dispatch despite an active run | 2 |
| Ignore GitHub HTTP failure | 1 |
| Treat dispatch acknowledgement as observed start | 1 |
| Fail to observe a lost POST response | 1 |
| Stop Worker pagination after the first page | 1 |
| Hide an early manual rehearsal with a creation-date filter | 1 |

Some cases kill several defects; the table is not additive. New tests cover
malformed/impossible/non-Saturday/future dates, UTC boundaries, exact mode/date/
branch identity, queued and successful runs, paginated history, API failure,
lost acknowledgements, both receipt fields, invalid JSON, retry limits,
redaction, report artifacts and step summaries.

Existing settings are preserved: GitHub backup `17 6 * * 6`, collection job
350 minutes, three push attempts, 14-day artifacts, twelve site observations
with 15-second intervals, collector budgets and the existing departure cap.
Queueing changes are explicitly required to preserve waiting writes. The
[GitHub queue contract](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
documents `queue: max`; the live acceptance must exercise it on the repository.
The code comments explaining new bounds/retries are:

- `Bound API waits so an unknown state fails before collection, never admits it.`
- `Bound each request so failed API access cannot consume the whole cron window.`
- `Three observations over 20 seconds allow for GitHub's asynchronous dispatch indexing.`
- `GitHub caps filtered history at 1,000 results; incomplete evidence is unsafe.`
- `Bound a new receipt read; an unavailable mirror is a failed delivery.`
- `One transport retry is allowed; configuration and build failures stop immediately.`

For live acceptance, follow [the clock README](../infra/clock/README.md). It
contains `wrangler secret put GH_DISPATCH_TOKEN`, `wrangler deploy`,
`wrangler dev --test-scheduled`, the exact Wednesday test tick, duplicate-tick
check and manual guard/rehearsal commands. Required secrets are the Worker
Actions read/write token and the existing collection/HF/Vercel secrets listed
there. Keep them out of public files and logs. The workflow with the new inputs
must exist on the default branch before testing dispatch from an acceptance
branch. Observe a real Cloudflare cron invocation before activation.

The full coordinator, candidate manifest, resume-after-capture, automatic HF
recovery and incident drills remain outside P2, as requested. P1 owns release
notifications and the combined site/HF observation. A green weekly collection
is not itself an announcement that the release is complete.

Known workaround: GitHub `run-name` cannot calculate dates. Schedule and
empty-date entries use a short `resolve-date` routing run and an explicitly
dated child. Only the child collects; the router cannot deploy. Observers must
match the exact dated child. This adds one dispatch dependency to the backup
schedule. The Worker itself always supplies an explicit date.

Not checked live: Cloudflare CPU/free-plan behavior and cron delivery, GitHub
queue races and dispatch indexing, runner 3.12/22 execution, complete fresh
collection, pinned CLI uploads, or real site/HF receipts. No claim of operational
acceptance is made. Risks: a temporary HF readback failure now correctly makes
the run red; once git holds a date, recovery uses `hf-mirror.yml` and a separate
deployment rather than recapture. Rehearsal still shares the existing 350-minute
job budget with its new web checks and holds the data-write queue for that job.
Simultaneous clock deliveries can race between listing and dispatching; the
dated workflow lock and archive guard prevent a second capture even if both
requests create queued runs. The Worker has no distributed lock or durable state.

## Fix 2

This revision closes the three findings against `b64ecaaf61` and replaces the
Fix 1 section with current acceptance evidence. The earlier token, license and
dependency corrections remain in place. No Git index operations, commits,
pushes, workflow dispatches, Telegram messages or production writes were made.
The conductor will commit the changes.

Changed files:

| Files | Change |
| --- | --- |
| `scripts/weekly-release.mjs` | Shared attempt ordering, attempt history, failed-step recovery and selection of the effective attempt. |
| `scripts/freshness-check.mjs` | Preserve `run_attempt`; read explicit attempt summaries and jobs for weekly and deploy reruns. |
| `scripts/freshness.mjs` | Preserve unrecovered attempt failures before considering the site receipt; exclude known skipped deploys; order retries by their actual start; update the truth table. |
| `scripts/workflow-watchdog-check.mjs`, `scripts/workflow-watchdog.mjs` | Use the same attempt evidence and recovery rule for weekly/deploy health. |
| `scripts/freshness.test.mjs` | Fifteen new cases, including both sensors, the network-free runner and all three reported regressions. |
| This report | Updated state table, acceptance, deliberate defects and limits. |

All three requested regressions were observed red on the original code:

```text
Successful no-op rerun after HF failure: watchdog ok, expected red
No weekly run plus a skipped deploy at 13:00: unknown, expected not_started
A rerun at 09:00 after B failed at 04:17: failed, expected publishing
tests 3; pass 0; fail 3
```

They pass after the fixes. A related regression was also reproduced: a site
receipt with unavailable workflow history returned `released`; it now returns
`unknown`, because the receipt cannot establish whether an earlier failed step
was repaired.

For reruns, both sensors read each previous
[workflow run attempt](https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run-attempt)
and [jobs for that attempt](https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run-attempt).
The latest attempt metadata comes from the run listing; its jobs are also read
through the explicit attempt endpoint. The code does not combine a previous
attempt with the default latest-jobs response.

The pure shared resolver tracks failed `(job name, step name)` pairs across
attempts. A later `success` for the same step clears that failure; a skipped
step, a green guard/job, or collection alone cannot clear an HF/deploy failure.
Several successive skips retain the original failure and its time. Actual HF
recovery can succeed without collecting again. A subsequent no-op preserves the
time of that recovery, so it cannot refresh the watchdog's success age. Another
run must also supply actual successful-step evidence to clear a retained failure.
Alerts identify the failed step and original attempt number.

Absent, incomplete or mismatched attempt evidence produces `unknown`, including
when main and the public site already have the snapshot. A failed attempt with
no identifiable failed step also remains unknown, since recovery cannot be
verified. `run_started_at` orders attempts; `run_attempt` and ID break ties. The
original `created_at` remains the date label for legacy weekly runs, not their
retry ordering. Only a first attempt may fall back to `created_at` if its start
time is absent.

A completed deploy with `conclusion: skipped` means no deployment occurred. It
is removed before evaluating the state table, after resolving any earlier
attempts. Thus an ordinary skipped deploy cannot create `unknown` or replace a
real deployment, while a skipped rerun cannot erase its earlier failed stage.

Truth table, first matching row wins. D is the last Saturday UTC. A is snapshot
D on current main; S is JSON at `/snapshots/D/snapshot.json` with snapshot_date D.
`+` means present, `-` absent and `?` unknown. W is the effective release attempts
for D; P is effective non-skipped deploy attempts started since D. Attempts are
resolved before filtering skips and before applying the table. The deadline
remains 12:00 UTC.

| Row | A / S | Required facts | State | Alert / human needed |
| --- | --- | --- | --- | --- |
| U0 | any | Invalid observation time | unknown | yes / no |
| U5 | any | Required attempt history or recovery evidence unavailable | unknown | yes / no |
| F0 | any | Retained failed step in W/P, no verified repair | failed | yes / yes |
| U1 | any | Required workflow history or release/skip identity unknown | unknown | yes / no |
| R1 | + / + | No retained failure or unknown evidence from the preceding rows | released | once / no |
| R2 | any | W active | running | at/after noon / no |
| F1 | any | W failed, no newer real retry or success | failed | yes / yes |
| U2 | ? / any, or any / ? | Publication fact needed by later rows unknown | unknown | yes / no |
| U3 | - / + | Contradictory main/site observations | unknown | yes / no |
| P1 | + / - | No active/failed W; P active | publishing | at/after noon / no |
| F2 | + / - | No active/failed W; P failed without recovery | failed | yes / yes |
| P2 | + / - | No active/failed W or P; before noon | publishing | no / no |
| F3 | + / - | Same facts at/after noon: site publication missing | failed | yes / yes |
| N1 | - / - | No W; an ordinary skipped deploy contributes no P | not_started | at/after noon / yes when late |
| O1 | - / - | W successful, before noon | ok | no / no |
| F4 | - / - | W successful at/after noon: archive missing | failed | yes / yes |
| U4 | remaining | Unsupported result or incomplete required facts | unknown | yes / no |

The original 22 table cases still pass. New cases cover U5/F0, the skipped-deploy
N1 row, actual HF/deploy recovery, several successive skips, job identity,
attempt ordering, incomplete/mismatched responses and explicit API endpoint
wiring. Messages remain Russian and keep `Нужен человек: да/нет`.

Acceptance after restoring deliberate defects:

```text
PYTHONPATH=. .venv/bin/pytest tests/ -q
exit 0; 6,938 collected cases, 6,937 passed, one expected skip
SKIPPED tests/test_recall_fixture.py:49: census working data absent (gitignored)

.venv/bin/ruff check etl tests collectors scripts
All checks passed!

node --test scripts/*.test.mjs infra/clock/*.test.mjs
tests 131; pass 131; fail 0; skipped 0

python3 -c 'import pathlib,yaml; files=sorted(pathlib.Path(".github/workflows").glob("*.yml"))+sorted(pathlib.Path(".github/workflows").glob("*.yaml")); [yaml.safe_load(f.read_text()) for f in files]; print(f"YAML: {len(files)} workflows parsed")'
YAML: 14 workflows parsed

git diff --check
exit 0
```

Mutation evidence: implementation files were temporarily changed and restored
in `finally` blocks. Every one of the **15 new tests** failed under at least one
of **10 deliberate defects**. Failures were assertions, not syntax/import errors.

| Deliberate defect | New cases that failed |
| --- | ---: |
| Ignore attempt history | 11 |
| Treat skipped deployments as unknown work | 1 |
| Restore ordering by original created_at and ID | 2 |
| Never clear a genuinely recovered step | 4 |
| Accept the same step name in the wrong job | 1 |
| Read only the latest attempt | 6 |
| Let a site receipt hide retained HF failure | 4 |
| Read latest-run endpoints instead of explicit attempts | 1 |
| Let another run clear failure without successful-stage evidence | 1 |
| Ignore unavailable run history when the site is published | 1 |

Some tests detect multiple defects; the counts are not additive. The three
reported defects were reproduced before implementation, independently of these
mutation checks.

No dependency, workflow, collection logic, methodology or web file changed.
No existing timeout, retry count, schedule, reminder window, threshold or page
size changed. Attempt reads reuse the existing GitHub request timeouts and
100-job page size. No coordinator, persistence or automatic recovery was added.

For live acceptance, the existing sensor GitHub token needs Actions read access
to attempt summaries and jobs; there are no new secrets. The conductor should
inspect a controlled failed HF/deploy attempt followed by a skipped rerun and
confirm both sensors retain the failure. Then verify that successful execution
of the failed step clears it, and that an ordinary skipped deployment does not
change an otherwise unstarted release. The local tests performed no live calls
to GitHub, HF, Vercel or Telegram.

Not checked live: actual GitHub rerun/job payloads, queue races, notifications,
HF repair or deployment; local tests use Python 3.14/Node 25, not CI 3.12/22.
Risks and limits: recovery relies on stable job/step names and complete attempt
evidence. Missing evidence alerts as unknown. The existing bounded run listing
can omit older runs; its page sizes were deliberately preserved. Repair through
a separate workflow such as hf-mirror is not inferred as success of a failed
weekly step, so the retained alert can remain after an external repair. Observing
that recovery independently and automatic continuation remain outside P2.

## Fix 3

This follow-up closes both findings against `29e1e8b6ec` on
`ops/release-followup`. No Git index operations, commits, pushes, workflow
dispatches or production writes were made. The conductor will commit the changes.

Changed files:

| File | Change |
| --- | --- |
| `scripts/weekly-release.mjs` | Fetch jobs for successful first attempts, including deploys that can repair another run; share the predicate for attempts wholly before a cutoff. |
| `scripts/freshness-check.mjs` | Exclude wholly previous-week deploy runs before requesting their attempt history. |
| `scripts/freshness.mjs` | Apply the same scope in the pure evaluator and update the state table comments. |
| `scripts/freshness.test.mjs` | Two mocked-API regression tests through `readWeeklyFacts()`, with negative recovery and unknown-history checks. |
| This report | Fix 3 behavior, state table, acceptance and mutation evidence. |

The shared jobs loader now supplies successful first-attempt step evidence to
both freshness and the watchdog. Deploy A's retained failure clears when newer
deploy B actually succeeded at the same failed job/step. A green job with that
step skipped still leaves A failed. Existing stage matching and attempt ordering
are unchanged.

For freshness, the latest known attempt start bounds all previous attempt starts.
If it is before Saturday D at 00:00 UTC, the deploy is outside D's evaluation:
neither its attempt summaries nor its jobs are requested. The pure evaluator
also excludes it before resolving attempts. Missing or invalid rerun start times
cannot exclude a run using its unchanged creation date. Current-week or unknown
start times with unavailable attempt history still produce `unknown`.

Updated truth table: first matching row wins. D is the last Saturday UTC; A is
snapshot D on main; S is `/snapshots/D/snapshot.json` with snapshot_date D.
`+` means present, `-` absent and `?` unknown. W is effective release attempts for
D; P is effective non-skipped deploy attempts started since D. Wholly older
deploys are excluded before history reads and resolution. Skips are filtered
after resolution so they cannot hide an earlier failed attempt. Repair requires
successful execution of every retained failed job/step, including when the repair
is a different run's first attempt. The deadline remains 12:00 UTC.

| Row | A / S | Required facts | State | Alert / human needed |
| --- | --- | --- | --- | --- |
| U0 | any | Invalid observation time | unknown | yes / no |
| U5 | any | Required in-scope attempt history unavailable; wholly old history is irrelevant | unknown | yes / no |
| F0 | any | Retained failed step in W/P without verified repair | failed | yes / yes |
| U1 | any | Required workflow history or release/skip identity unknown | unknown | yes / no |
| R1 | + / + | No retained failure or unknown evidence after scope and repair checks | released | once / no |
| R2 | any | W active | running | at/after noon / no |
| F1 | any | W failed, no newer real retry or success | failed | yes / yes |
| U2 | ? / any, or any / ? | Publication fact needed by later rows unknown | unknown | yes / no |
| U3 | - / + | Contradictory main/site observations | unknown | yes / no |
| P1 | + / - | No active/failed W; P active | publishing | at/after noon / no |
| F2 | + / - | No active/failed W; P failed without recovery | failed | yes / yes |
| P2 | + / - | No active/failed W or P; before noon | publishing | no / no |
| F3 | + / - | Same facts at/after noon: site publication missing | failed | yes / yes |
| N1 | - / - | No W; an ordinary skipped deploy contributes no P | not_started | at/after noon / yes when late |
| O1 | - / - | W successful, before noon | ok | no / no |
| F4 | - / - | W successful at/after noon: archive missing | failed | yes / yes |
| U4 | remaining | Unsupported result or incomplete required facts | unknown | yes / no |

Both new regressions failed on the original implementation:

```text
Deploy A failed twice, deploy B repaired the step: failed, expected released
Only previous-week deploy rerun, history HTTP 503: unknown, expected released
tests 2; pass 0; fail 2
```

The repaired cases reach R1. The first test also checks that B's skipped step
leaves F0. The second asserts no history request for the old run, checks the pure
model independently, and checks U5 for current-week and missing start times.

Five deliberate implementation defects were applied separately and restored in
`finally` blocks. Both new tests failed under deliberate defects, with assertion
failures rather than syntax or import errors:

| Deliberate defect | Regression test that failed |
| --- | --- |
| Restore the omission of successful first-attempt deploy jobs | New-run repair |
| Request old history in the reader | Old-run exclusion: unexpected API request |
| Include old unknown attempts in the pure model | Old-run exclusion: unknown instead of released |
| Exclude current/unknown attempts as well as old ones | Both tests; unknown evidence must remain in scope |
| Accept a skipped repair step | New-run repair: false recovery |

Acceptance after restoring all deliberate defects:

```text
node --test scripts/*.test.mjs infra/clock/*.test.mjs
tests 133; pass 133; fail 0; skipped 0

PYTHONPATH=. .venv/bin/pytest tests/ -q
exit 0; 6,938 cases, 6,937 passed, one expected skip
SKIPPED tests/test_recall_fixture.py:49: census working data absent (gitignored)

.venv/bin/ruff check etl tests collectors scripts
All checks passed!

git diff --check
exit 0
```

No dependencies, workflow settings, timeouts, retry counts, schedules, thresholds
or page sizes changed. No collection, methodology, web or governance files changed.
Successful first attempts now incur a jobs read even when no retained failure
ultimately needs repair. This keeps recovery evidence in the shared path used by
both sensors; wholly old deploys avoid those reads in freshness.

For live acceptance, use the existing Actions-read token; no new secrets are
needed. Check a deploy that failed twice followed by a new successful deploy of
the same failed stage. Both sensors should clear the retained failure. Confirm
that an already published current release stays released when only an old rerun's
attempt endpoint is unavailable. Local regression tests mock all such requests.

Not checked live: GitHub attempt payloads, sensor notifications or production
deployment recovery; local validation uses Python 3.14/Node 25, not CI 3.12/22.
Risks and limits: extra jobs reads consume API quota; stage recovery still relies
on stable job/step names and complete evidence within the existing bounded run
listing. An external repair through another workflow is not inferred. No automatic
recovery or workaround for missing required evidence was added; such evidence
continues to block a confirmed release verdict.
