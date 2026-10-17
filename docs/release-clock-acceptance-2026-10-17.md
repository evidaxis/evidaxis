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
