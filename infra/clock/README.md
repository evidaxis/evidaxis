# Release clock

Dependency-free Cloudflare Worker on the Free plan. Four UTC cron triggers:
Saturday 02:17 (release), 04:17 and 06:47 (retry if no active or successful run),
Wednesday 02:17 (rehearsal for the next Saturday). The GitHub 06:17 Saturday
cron remains the fallback. No HTTP dispatch endpoint, KV, or durable state.

Every tick lists all matching weekly runs on the configured branch. Queued,
pending, waiting, in-progress and successful attempts prevent dispatch. A failed
or cancelled attempt permits another attempt. A failed or incomplete API read
stops the tick. A dispatch response is only an acknowledgement: the Worker
observes a new matching run ID before recording `run_observed`. A lost POST
response is checked the same way, without another POST. Logs contain date,
mode, run ID and outcome, never API response bodies or credentials.

`weekly release YYYY-MM-DD` and `weekly rehearsal YYYY-MM-DD` identify actual
dated runs. GitHub expressions cannot calculate calendar dates in `run-name`.
The backup schedule and empty-date manual entry therefore create a short
`weekly release resolve-date` (or rehearsal) routing run. It resolves the last
Saturday UTC, checks the archive and dispatches a dated child. The routing run
cannot collect or deploy. Only the dated child's result represents collection.
Observers must ignore `resolve-date` when identifying a release attempt.

The workflow serializes both modes by date, rechecks the archive after waiting
for `data-commits`, and refuses a new release outside main. Rehearsal uses the
same collectors and seed retirement in a disposable checkout. It never commits,
pushes, uploads to HF, stamps OTS, requests SWH archival, or triggers deployment.
The existing web reader and guards use `EVIDAXIS_DATA_DIR` pointing to that
checkout's candidate data. Reports and candidate snapshots retain the existing
14-day artifact policy; they are not resumable release manifests.

## Configure and deploy (operator only)

Create a fine-grained GitHub token for **evidaxis/evidaxis only**, with
**Actions: Read and write**. Store it only as the Worker secret, not in this
repository or command arguments. Record its expiry outside the public repo.
Authenticate Wrangler to the Cloudflare account, then:

```sh
cd infra/clock
wrangler secret put GH_DISPATCH_TOKEN
wrangler deploy
wrangler tail
```

Do not enable the production triggers until the full rehearsal has passed.
`wrangler deploy` installs the schedules in `wrangler.toml`; deploying this
Worker is an operator action, separate from committing its code.

## Test the scheduled handler (operator only)

The workflow with the new inputs must already exist on the default branch.
Put the test token in the ignored `infra/clock/.dev.vars`, using a local editor:
`GH_DISPATCH_TOKEN=...`. Never commit or print this file. Test on the acceptance
branch with a Wednesday tick, which can only request rehearsal:

```sh
cd infra/clock
wrangler dev --test-scheduled --var GH_REF:ops/release-clock
```

In another terminal:

```sh
curl 'http://localhost:8787/__scheduled?cron=17+2+*+*+WED&time=1792549020000'
```

This represents 2026-10-21 02:17 UTC and requests `weekly rehearsal 2026-10-24`.
Check `run_observed` and its run ID in the Worker log. Repeat the same tick while
that run is queued/running: expect `already_present`, with no second dispatch.
An HTTP response alone is not acceptance. After activation, observe a real
Cloudflare cron invocation as well; the local test does not prove scheduling.
Remove the local secret file after the probe.

Required existing GitHub secrets: `COLLECT_APP_ID`, `COLLECT_APP_KEY`,
`OPENALEX_API_KEY`; releases also need `HF_TOKEN`, `VERCEL_TOKEN`,
`VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`. GitHub supplies `GITHUB_TOKEN`.
No publication credentials are passed to the rehearsal's HF/web steps.

Manual operator checks after merge:

```sh
gh workflow run weekly-snapshot.yml --ref main -f mode=release -f release_date=2026-10-17
gh workflow run weekly-snapshot.yml --ref main -f mode=rehearsal -f release_date=2026-10-24
```

The first must say `already exists` without collection or commits. The second
must produce the candidate site checks, HF dry-run and `rehearsal-report.json`.
Neither command was run during local implementation.

If git already contains a date but HF delivery failed, the guard deliberately
prevents recapture. The operator can run the existing `hf-mirror.yml` for that
date and then `deploy-web.yml`. Automated continuation is outside this package.

Platform references: [Cron testing](https://developers.cloudflare.com/workers/configuration/cron-triggers/),
[GitHub concurrency queues](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).
`queue: max` is set for weekly, T2 and production deployment to preserve pending
writes. The actual acceptance branch must validate platform scheduling/queueing.
