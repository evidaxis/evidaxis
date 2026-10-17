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

## Fix 1

This revision addresses the review and conductor acceptance findings on top of
`af7efc3274` and the three imported freshness commits. The evidence below
supersedes the original dependency pins and the original license-coverage claim.
No Git index operations, commits, pushes, workflow runs, Telegram messages or
deployments were performed in this revision. The conductor will commit the files.

Changed files:

| Files | Change |
| --- | --- |
| `infra/clock/logic.mjs`, `worker.js`, `logic.test.mjs` | Validate a nonempty ASCII token alphabet before fetch; reject whitespace, control characters and non-ASCII. Log only `GH_DISPATCH_TOKEN has invalid format` for invalid tokens. |
| `scripts/weekly-release.mjs` (new) | Shared release identity and complete Jobs API evidence for both sensors. |
| `scripts/release_guard.py`, `infra/clock/README.md` | Document how a successful guard skip is distinguished from collection through Jobs API. |
| `scripts/workflow-watchdog.mjs`, `workflow-watchdog-check.mjs`, `workflow-watchdog.test.mjs` | Select real release attempts before judging health. A successful skip/router cannot replace an earlier failure. Unreadable required job evidence gives `unknown`. |
| `scripts/freshness.mjs`, `freshness-check.mjs`, `freshness.test.mjs` | Explicit state table; independent Saturday public-content probe; no inference of Saturday publication from `latest.json`; unknown API/content facts remain unknown. Importable observation function permits network-free runner tests. |
| `tests/test_release_guard.py` | Assert the workflow name contract for default manual inputs and schedule. |
| `.github/workflows/weekly-snapshot.yml`, `.github/workflows/hf-mirror.yml` | Pin HF to 2.2.0 with the requested rationale. |
| `scripts/vercel-deploy.mjs`, `scripts/deploy-receipt.test.mjs` | Pin the invoked CLI to 64.5.0 with the requested rationale; keep transport retry/output suppression. |
| `REUSE.toml` | Apache annotations for all `infra/clock/**`, this report and the new release-schedule record. Existing `scripts/**` and `tests/**` annotations already cover the other P2 files. |
| This report | Review regressions, truth table, validation, mutation evidence and remaining limits. |

The initial license test failure was reproduced on tracked files: `logic.mjs`,
`logic.test.mjs` and `worker.js` lacked a matching annotation. Markdown had been
exempted by that test; this revision explicitly annotates the requested report
and governance record too, without editing the immutable governance file.

The guard still exits successfully on an existing date. REST does not expose
step outputs, so both sensors inspect the existing Jobs API conclusions: a
skipped `snapshot` job identifies the first guard; a skipped
`Collect snapshot (keyed OpenAlex; capture pass + completeness gate)` step in a
successful run identifies the guard after queueing. A real successful collection
has that step marked `success`. Missing or incomplete job evidence is unknown.
Failed guard/preflight attempts remain failures. Routers, rehearsals, PRs and
non-main branches cannot recover release health.

The current workflow already has the required run-name expression. Empty manual
inputs and the fallback schedule resolve to `weekly release resolve-date`; the
dated child gets `weekly release D`. Bare `weekly-snapshot` is supported only as
the legacy title. The new workflow-contract test goes red when the expression is
replaced by that old title. No live workflow was started to check GitHub rendering.

The Sunday regression now has both a pure state test and a mocked runner test:
on 2026-10-18, a newer latest pointer and a failed Sunday deploy do not override
the separately confirmed `https://evidaxis.org/snapshots/2026-10-17/snapshot.json`.
At Saturday 14:00, successful collection plus an unknown Contents API result
(timeout, HTTP 403 or 500) produces `unknown`, not `ok`. Four focused regression
tests were observed red before their fixes, in addition to the license failure.

Truth table: first matching row wins. D is the last Saturday UTC. A is the
snapshot D on current main; S is JSON from `/snapshots/D/snapshot.json` whose
`snapshot_date` equals D. `+` means present, `-` means absent, `?` means unknown.
W contains real release attempts for D; P contains main-branch deployments since
D. The existing deadline is 12:00 UTC. `released` is a site receipt; HF delivery
remains checked by the weekly/mirror readback and is not inferred from this state.

| Row | A / S | Other required facts | State | Alert / human needed |
| --- | --- | --- | --- | --- |
| U0 | any | Invalid observation time | unknown | yes / no |
| R1 | + / + | Site publication proved, regardless of later workflow failures | released | once / no |
| U1 | any | Required workflow history or release/skip identity unknown | unknown | yes / no |
| R2 | any | W active | running | at/after noon / no |
| F1 | any | W failed, no newer real retry or success | failed | yes / yes |
| U2 | ? / any, or any / ? | Publication fact required by subsequent rows unknown | unknown | yes / no |
| U3 | - / + | Contradictory main/site observations | unknown | yes / no |
| P1 | + / - | No active/failed W; P active | publishing | at/after noon / no |
| F2 | + / - | No active/failed W; P failed without recovery | failed | yes / yes |
| P2 | + / - | No active/failed W; no active/failed P; before noon | publishing | no / no |
| F3 | + / - | Same facts at/after noon: site publication missing | failed | yes / yes |
| N1 | - / - | No W | not_started | at/after noon / yes when late |
| O1 | - / - | W successful, before noon | ok | no / no |
| F4 | - / - | W successful at/after noon: archive missing | failed | yes / yes |
| U4 | remaining | Unsupported result or incomplete required facts | unknown | yes / no |

There are 22 table cases, including both sides of the deadline and separate
unknown facts. Running/failure describe a known attempt even if a publication
probe is unknown. No unknown fact required for an `ok` verdict can buy silence.
The Telegram state messages retain Russian wording and `Нужен человек: да/нет`;
existing reminder windows and deduplication keys are unchanged.

Validation after restoring all deliberate defects:

```text
PYTHONPATH=. .venv/bin/pytest tests/ -q
exit 0; 6,938 collected cases, 6,937 passed, one expected skip
SKIPPED tests/test_recall_fixture.py:49: census working data absent (gitignored)

.venv/bin/ruff check etl tests collectors scripts
All checks passed!

node --test scripts/*.test.mjs infra/clock/*.test.mjs
tests 116; pass 116; fail 0; skipped 0

node --test scripts/liveness.test.mjs scripts/freshness.test.mjs scripts/workflow-watchdog.test.mjs scripts/alert-gate.test.mjs
tests 102; pass 102; fail 0; skipped 0

python3 -c 'import pathlib,yaml; files=sorted(pathlib.Path(".github/workflows").glob("*.yml"))+sorted(pathlib.Path(".github/workflows").glob("*.yaml")); [yaml.safe_load(f.read_text()) for f in files]; print(f"YAML: {len(files)} workflows parsed")'
YAML: 14 workflows parsed

PYTHONPATH=. .venv/bin/pytest tests/test_hf_upload_snapshot.py -q -o addopts=''
38 passed in 13.12s

PYTHONPATH=. .venv/bin/pytest tests/test_license_coverage.py::test_every_tracked_file_has_a_license_annotation -q -o addopts=''
1 passed in 8.39s

.venv/bin/python -c 'import huggingface_hub; print(huggingface_hub.__version__)'
2.2.0
.venv/bin/hf --version
2.2.0
.venv/bin/hf upload --help
exit 0; upload positional arguments and --repo-type remain supported
.venv/bin/python -m pip check
No broken requirements found.

git diff --check
exit 0
```

The network pip attempt failed at DNS resolution. The actual HF 2.2.0 package
and required dependencies were installed offline into this checkout's existing
`.venv` from the local package cache. No package source or dependency lockfile
was changed. HF tests ran with that version installed; they mock upload/network
operations. CLI help/version checks also ran against the installed 2.2.0 CLI.

All 17 deliberate defects below caused assertion failures, not syntax/import
errors. Each source file was restored in a `finally` block. All **41 new Node
tests**, **two revised/renamed Node tests**, and the **one new pytest case** went
red under at least one mutation. The existing license and Vercel tests also
caught the regressions. The final unmodified acceptance commands passed again.

| Deliberate defect | Evidence |
| --- | --- |
| Accept malformed tokens | Both new token tests failed, including no-fetch/log assertions |
| Collapse release verdicts to `ok` | 37 new/revised Node tests failed |
| Fail a known successful pre-deadline observation | O1 failed |
| Treat dated skips as real successes | Five new/revised tests failed, including watchdog health |
| Ignore Jobs enrichment | Two new tests failed |
| Accept incomplete Jobs evidence | Jobs response test failed |
| Treat resolve-date routers as releases | Three new tests failed |
| Probe Sunday instead of Saturday | Sunday runner regression failed |
| Interpret unknown Contents API evidence as absent | Timeout, 403 and 500 cases all failed |
| Accept the wrong public snapshot date | Public-content comparison test failed |
| Accept malformed public JSON content | Both missing-date/null tests failed |
| Treat public HTTP failure as publication | HTTP 503 case failed |
| Treat truncated workflow history as empty | Truncated-history case failed |
| Treat invalid workflow metadata as empty | Invalid-history case failed |
| Restore Vercel 48.2.9 | Existing deployment test failed |
| Restore the bare weekly workflow title | New pytest workflow-contract case failed |
| Remove infrastructure license mapping | Existing tracked-file license test failed |

No existing timeouts, retry counts, schedules, reminder windows or history page
sizes were changed. The requested version comments next to the pins are:

- `64.5.0 deployed production on 2026-10-17 (run 39037255164); 48.2.9 would roll back a year.`
- `2.2.0 was released on 2026-10-08 and used by the unpinned 2026-10-17 release.`

For live acceptance, use the existing Worker commands and secrets in the
[clock README](../infra/clock/README.md). Sensors require GitHub Actions read
access, including Jobs API; their existing GitHub token supplies it. Confirm a
real guard skip has the job/step conclusions described above and cannot clear a
failed release. Check the Saturday URL independently from latest, then verify the
HF public files. No additional secret is introduced by Fix 1.

Not checked live: GitHub event titles/Jobs responses after rollout, dispatches,
Cloudflare ticks, Telegram delivery, Vercel 64.5.0 deployment or HF 2.2.0 upload.
Local runtimes remain Python 3.14 and Node 25; CI uses 3.12/22. Web verification
was not repeated because no web input or source changed in Fix 1.
Known limits and risks: skip identification depends on the existing job/step
names; missing evidence gives an alerting `unknown`. The existing bounded run
history may be insufficient during a burst, which now fails closed. A site
`released` receipt does not independently certify HF; weekly/HF readback and the
watchdog retain that failure. Recovery after a committed snapshot still uses
manual HF mirror/deploy workflows; no-op reruns cannot clear the failed weekly
attempt. The coordinator and automatic recovery remain outside P2.
