import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readWeeklyFacts } from './freshness-check.mjs';
import { evaluateWorkflowHealth } from './workflow-watchdog.mjs';
import { attachReleaseJobs, COLLECT_STEP, compareAttempts, effectiveRun, releaseRunDate, releaseRunKind } from './weekly-release.mjs';
import {
  decideFeedPush,
  decideWeeklyPush,
  evaluateFeedFreshness,
  evaluateFreshness,
  evaluateWeeklyRelease,
  gateFreshnessAlerts,
  parseReleaseKey,
  pickFailedStep,
  releaseKeyToPrint,
} from './freshness.mjs';

const base = { site: 'https://evidaxis.org', snapshotDate: '2026-08-08' };
const long_after = new Date('2026-08-10T09:00:00Z');   // two days later
const same_morning = new Date('2026-08-08T09:00:00Z'); // minutes after the run

test('prod serves the newest committed snapshot → ok, no alert', () => {
  const r = evaluateFreshness({ ...base, reached: true, status: 200, now: long_after });
  assert.equal(r.status, 'ok');
  assert.equal(r.alert, false);
});

test('snapshot missing on prod, publication window still open → quiet', () => {
  const r = evaluateFreshness({ ...base, reached: true, status: 404, now: same_morning });
  assert.equal(r.status, 'publishing');
  assert.equal(r.alert, false);
});

test('snapshot missing on prod past the window → stale, ALERT', () => {
  // The 2026-08-10 regression: main held 08-08, prod still served 08-01, and
  // every existing check was green.
  const r = evaluateFreshness({ ...base, reached: true, status: 404, now: long_after });
  assert.equal(r.status, 'stale');
  assert.equal(r.alert, true);
  assert.match(r.message, /2026-08-08/);
});

test('site unreachable → unknown, no alert (that is the liveness sensor fact)', () => {
  const r = evaluateFreshness({ ...base, reached: false, status: 0, now: long_after });
  assert.equal(r.status, 'unknown');
  assert.equal(r.alert, false);
});

test('unparseable snapshot date cannot buy silence', () => {
  const r = evaluateFreshness({
    ...base, snapshotDate: 'not-a-date', reached: true, status: 404, now: long_after,
  });
  assert.equal(r.status, 'stale');
  assert.equal(r.alert, true);
});

test('grace window is configurable and respected', () => {
  const r = evaluateFreshness({
    ...base, reached: true, status: 404, now: long_after, graceHours: 96,
  });
  assert.equal(r.status, 'publishing');
  assert.equal(r.alert, false);
});

test('feed entry age at eight days is accepted', () => {
  const r = evaluateFeedFreshness({
    site: base.site,
    reached: true,
    status: 200,
    latestEntryAt: '2026-08-12T09:00:00Z',
    now: new Date('2026-08-20T09:00:00Z'),
  });
  assert.equal(r.status, 'ok');
  assert.equal(r.alert, false);
});

test('feed entry older than eight days alerts', () => {
  const r = evaluateFeedFreshness({
    site: base.site,
    reached: true,
    status: 200,
    latestEntryAt: '2026-08-11T08:59:59Z',
    now: new Date('2026-08-20T09:00:00Z'),
  });
  assert.equal(r.status, 'stale');
  assert.equal(r.alert, true);
});

test('feed with an invalid latest-entry date cannot report fresh', () => {
  const r = evaluateFeedFreshness({
    site: base.site,
    reached: true,
    status: 200,
    latestEntryAt: null,
    now: long_after,
  });
  assert.equal(r.status, 'stale');
  assert.equal(r.alert, true);
});

/** @param {object} over */
function run(over) {
  return {
    id: 1,
    status: 'completed',
    conclusion: 'success',
    created_at: '2026-10-17T10:54:30Z',
    run_started_at: '2026-10-17T10:54:30Z',
    updated_at: '2026-10-17T13:36:25Z',
    html_url: 'https://github.com/evidaxis/evidaxis/actions/runs/39026676364',
    event: 'schedule',
    display_title: 'weekly-snapshot',
    head_branch: 'main',
    jobs: [{ name: 'snapshot', conclusion: 'success', steps: [{
      name: 'Collect snapshot (keyed OpenAlex; capture pass + completeness gate)', conclusion: 'success',
    }] }],
    ...over,
  };
}

const liveWeekly = run({
  id: 39026676364,
  status: 'in_progress',
  conclusion: null,
  created_at: '2026-10-17T10:54:30Z',
  run_started_at: '2026-10-17T10:54:30Z',
  updated_at: '2026-10-17T13:33:00Z',
});

function assertNoCapture(message) {
  assert.doesNotMatch(message, /CAPTURE/);
}

test('17 Oct 13:33 UTC in-progress weekly run is late, not a missed capture', () => {
  // File age at this minute is past the old 174 h budget. The run is alive.
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:33:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [liveWeekly],
    deployRuns: [],
  });
  assert.equal(r.status, 'running');
  assert.equal(r.alert, true);
  assert.equal(r.key, '2026-10-17:running');
  assert.match(r.message, /опаздывает, но идёт/);
  assert.match(r.message, /Нужен человек: нет/);
  assert.match(r.message, /4 ч 37 мин/);
  assert.match(r.message, /39026676364/);
  assertNoCapture(r.message);
});

test('17 Oct 10:00 UTC in-progress run is running and still quiet', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T10:00:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [run({
      status: 'in_progress',
      conclusion: null,
      created_at: '2026-10-17T09:00:00Z',
      run_started_at: '2026-10-17T09:00:00Z',
      updated_at: '2026-10-17T10:00:00Z',
    })],
    deployRuns: [],
  });
  assert.equal(r.status, 'running');
  assert.equal(r.alert, false);
  assert.equal(r.message, '');
  assertNoCapture(r.message);
});

test('noon UTC is the moment a running release becomes late', () => {
  const weeklyRuns = [run({
    status: 'in_progress',
    conclusion: null,
    created_at: '2026-10-17T11:00:00Z',
    run_started_at: '2026-10-17T11:00:00Z',
    event: 'schedule',
  })];
  const before = evaluateWeeklyRelease({
    nowIso: '2026-10-17T11:59:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns,
    deployRuns: [],
  });
  const noon = evaluateWeeklyRelease({
    nowIso: '2026-10-17T12:00:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns,
    deployRuns: [],
  });
  assert.equal(before.alert, false);
  assert.equal(noon.status, 'running');
  assert.equal(noon.alert, true);
});

test('17 Oct 13:50 UTC archive is out and deploy is still running → publishing', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:50:00Z',
    snapshotOnMain: 'present',
    snapshotOnSite: 'absent',
    weeklyRuns: [run({
      status: 'completed',
      conclusion: 'success',
      updated_at: '2026-10-17T13:36:25Z',
    })],
    deployRuns: [run({
      id: 9,
      status: 'in_progress',
      conclusion: null,
      created_at: '2026-10-17T13:36:40Z',
      run_started_at: '2026-10-17T13:36:40Z',
      updated_at: '2026-10-17T13:50:00Z',
      html_url: 'https://github.com/evidaxis/evidaxis/actions/runs/39027000000',
      event: 'workflow_run',
    })],
  });
  assert.equal(r.status, 'publishing');
  assert.equal(r.alert, true);
  assert.match(r.message, /идёт выкладка с 13:36 UTC/);
  assert.match(r.message, /Нужен человек: нет/);
  assert.match(r.message, /39027000000/);
  assertNoCapture(r.message);
});

test('17 Oct 14:05 UTC both dates are the Saturday → one receipt with times', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T14:05:00Z',
    snapshotOnMain: 'present',
    snapshotOnSite: 'present',
    weeklyRuns: [liveWeekly, run({
      status: 'completed',
      conclusion: 'success',
      updated_at: '2026-10-17T13:36:25Z',
    })],
    deployRuns: [run({
      id: 11,
      status: 'completed',
      conclusion: 'success',
      created_at: '2026-10-17T13:36:30Z',
      run_started_at: '2026-10-17T13:36:40Z',
      updated_at: '2026-10-17T14:00:10Z',
      html_url: 'https://github.com/evidaxis/evidaxis/actions/runs/39028000000',
      event: 'workflow_run',
    })],
  });
  assert.equal(r.status, 'released');
  assert.equal(r.alert, true);
  assert.equal(r.key, '2026-10-17:released');
  assert.match(r.message, /✅ Срез 2026-10-17 на сайте/);
  assert.match(r.message, /Сбор шёл 10:54–13:36 UTC, выкладка закончилась в 14:00 UTC/);
  assert.match(r.message, /Нужен человек: нет/);
  assertNoCapture(r.message);
});

test('10 Oct 12:57 UTC failed weekly run names the step and asks for a human', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-10T12:57:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [run({
      id: 10,
      status: 'completed',
      conclusion: 'failure',
      created_at: '2026-10-10T06:40:00Z',
      run_started_at: '2026-10-10T06:40:00Z',
      updated_at: '2026-10-10T12:57:00Z',
      failedStep: 'Pin the snapshot date',
      html_url: 'https://github.com/evidaxis/evidaxis/actions/runs/10',
    })],
    deployRuns: [],
  });
  assert.equal(r.status, 'failed');
  assert.equal(r.alert, true);
  assert.match(r.message, /не вышел/);
  assert.match(r.message, /Pin the snapshot date/);
  assert.match(r.message, /12:57 UTC/);
  assert.match(r.message, /Нужен человек: да/);
  assert.match(r.message, /actions\/runs\/10/);
  assertNoCapture(r.message);
});

test('a failed Saturday run alerts before the noon deadline', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-10T08:00:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [run({
      status: 'completed',
      conclusion: 'failure',
      created_at: '2026-10-10T06:20:00Z',
      run_started_at: '2026-10-10T06:20:00Z',
      updated_at: '2026-10-10T08:00:00Z',
      failedStep: 'Collect',
    })],
    deployRuns: [],
  });
  assert.equal(r.status, 'failed');
  assert.equal(r.alert, true);
  assert.match(r.message, /Collect/);
});

test('03 Oct 15:13 UTC failed weekly run is a failed release', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-03T15:13:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [run({
      id: 3,
      status: 'completed',
      conclusion: 'failure',
      created_at: '2026-10-03T07:02:00Z',
      run_started_at: '2026-10-03T07:02:00Z',
      updated_at: '2026-10-03T15:13:00Z',
      html_url: 'https://github.com/evidaxis/evidaxis/actions/runs/3',
    })],
    deployRuns: [],
  });
  assert.equal(r.status, 'failed');
  assert.equal(r.alert, true);
  assert.match(r.message, /Срез 2026-10-03 не вышел/);
  assert.match(r.message, /15:13 UTC/);
  assert.match(r.message, /Нужен человек: да/);
  assertNoCapture(r.message);
});

test('cancelled and timed_out count as a failed release', () => {
  for (const conclusion of ['cancelled', 'timed_out']) {
    const r = evaluateWeeklyRelease({
      nowIso: '2026-10-17T13:00:00Z',
      snapshotOnMain: 'absent',
      snapshotOnSite: 'absent',
      weeklyRuns: [run({
        status: 'completed',
        conclusion,
        created_at: '2026-10-17T09:00:00Z',
        updated_at: '2026-10-17T12:40:00Z',
        failedStep: 'Collect',
      })],
      deployRuns: [],
    });
    assert.equal(r.status, 'failed', conclusion);
    assert.equal(r.alert, true);
  }
});

test('Saturday 13:00 a rehearsal is not the release and does not clear a failure', () => {
  const failure = run({
    id: 1,
    conclusion: 'failure',
    status: 'completed',
    created_at: '2026-10-17T06:30:00Z',
    updated_at: '2026-10-17T08:00:00Z',
    failedStep: 'Collect',
  });
  const rehearsal = run({
    id: 2,
    conclusion: 'success',
    status: 'completed',
    created_at: '2026-10-17T09:00:00Z',
    updated_at: '2026-10-17T12:00:00Z',
    display_title: 'weekly rehearsal 2026-10-17',
  });
  const stillFailed = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:00:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [failure, rehearsal],
    deployRuns: [],
  });
  assert.equal(stillFailed.status, 'failed');
  assert.match(stillFailed.message, /Collect/);
  assert.doesNotMatch(stillFailed.message, /в архиве нет/);

  const base = {
    nowIso: '2026-10-17T13:00:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    deployRuns: [],
  };
  for (const weeklyRuns of [
    [rehearsal],
    [run({
      conclusion: 'failure',
      status: 'completed',
      display_title: 'weekly rehearsal 2026-10-17',
      failedStep: 'Collect',
    })],
  ]) {
    const r = evaluateWeeklyRelease({ ...base, weeklyRuns });
    assert.notEqual(r.status, 'ok');
    assert.equal(r.status, 'not_started');
  }

  const running = evaluateWeeklyRelease({
    ...base,
    weeklyRuns: [liveWeekly, rehearsal],
  });
  assert.equal(running.status, 'running');
});

test('Saturday 13:00 a successful release with no snapshot file for that Saturday has failed', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:00:00Z',
    snapshotOnSite: 'absent',
    snapshotOnMain: 'absent',
    weeklyRuns: [run({
      conclusion: 'success',
      status: 'completed',
      display_title: 'weekly release 2026-10-17',
      updated_at: '2026-10-17T12:40:00Z',
    })],
    deployRuns: [],
  });
  assert.equal(r.status, 'failed');
  assert.equal(r.alert, true);
  assert.match(r.message, /Срез 2026-10-17 не вышел: сбор завершился в 12:40 UTC, но среза 2026-10-17 в архиве нет/);
  assert.match(r.message, /Нужен человек: да/);
});

test('a newer real success clears a collection failure while publication is active', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:10:00Z',
    snapshotOnMain: 'present',
    snapshotOnSite: 'absent',
    weeklyRuns: [
      run({
        id: 1,
        conclusion: 'failure',
        status: 'completed',
        created_at: '2026-10-17T06:30:00Z',
        updated_at: '2026-10-17T08:00:00Z',
        failedStep: 'Collect',
      }),
      run({
        id: 2,
        conclusion: 'success',
        status: 'completed',
        created_at: '2026-10-17T09:00:00Z',
        updated_at: '2026-10-17T13:00:00Z',
      }),
    ],
    deployRuns: [run({ status: 'queued', conclusion: null })],
  });
  assert.notEqual(r.status, 'failed');
  assert.equal(r.status, 'publishing');
});

test('Saturday 13:00 UTC with no run for that Saturday has not started', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:00:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [run({
      id: 2,
      created_at: '2026-10-10T10:00:00Z',
      run_started_at: '2026-10-10T10:00:00Z',
      updated_at: '2026-10-10T13:00:00Z',
      html_url: 'https://github.com/evidaxis/evidaxis/actions/runs/2',
    })],
    deployRuns: [],
  });
  assert.equal(r.status, 'not_started');
  assert.equal(r.alert, true);
  assert.match(r.message, /не стартовал к 12:00 UTC/);
  assert.match(r.message, /Нужен человек: да/);
  assert.match(r.message, /actions\/workflows\/weekly-snapshot\.yml/);
  assertNoCapture(r.message);
});

test('an API error is unknown, not a missed or failed release', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:00:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [],
    deployRuns: [],
    apiError: 'HTTP 502',
  });
  assert.equal(r.status, 'unknown');
  assert.equal(r.alert, true);
  assert.match(r.message, /Не могу проверить выпуск 2026-10-17/);
  assert.match(r.message, /HTTP 502/);
  assert.match(r.message, /Нужен человек: нет/);
  assert.doesNotMatch(r.message, /не стартовал/);
  assert.doesNotMatch(r.message, /не вышел/);
  assertNoCapture(r.message);
});

test('a failed deploy names the step and asks for a human', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T14:20:00Z',
    snapshotOnMain: 'present',
    snapshotOnSite: 'absent',
    weeklyRuns: [run({ conclusion: 'success', status: 'completed' })],
    deployRuns: [run({
      id: 8,
      conclusion: 'failure',
      status: 'completed',
      created_at: '2026-10-17T13:40:00Z',
      run_started_at: '2026-10-17T13:40:00Z',
      updated_at: '2026-10-17T14:10:00Z',
      event: 'workflow_run',
      failedStep: 'Deploy',
      html_url: 'https://github.com/evidaxis/evidaxis/actions/runs/88',
    })],
  });
  assert.equal(r.status, 'failed');
  assert.match(r.message, /выкладка упала на шаге «Deploy»/);
  assert.match(r.message, /14:10 UTC/);
  assert.match(r.message, /Нужен человек: да/);
  assertNoCapture(r.message);
});

test('the failed step is the first step concluded failure', () => {
  const name = pickFailedStep([
    { steps: [
      { name: 'Checkout', conclusion: 'success' },
      { name: 'Pin the snapshot date', conclusion: 'failure' },
      { name: 'Later', conclusion: 'failure' },
    ] },
    { steps: [{ name: 'Other job', conclusion: 'failure' }] },
  ]);
  assert.equal(name, 'Pin the snapshot date');
  assert.equal(pickFailedStep([]), undefined);
});

test('the release key is the last RELEASE_KEY line in the job log', () => {
  const log = [
    'noise',
    '2026-10-17T14:05:01.1234567Z RELEASE_KEY 2026-10-10:released',
    '2026-10-17T14:05:02.1234567Z RELEASE_KEY 2026-10-17:running',
  ].join('\n');
  assert.equal(parseReleaseKey(log), '2026-10-17:running');
  assert.equal(parseReleaseKey('RELEASE_KEY -\n'), null);
  assert.equal(parseReleaseKey(''), null);
});

test('a quiet run does not consume the key, and late then released each send once', () => {
  const early = evaluateWeeklyRelease({
    nowIso: '2026-10-17T10:00:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [run({
      status: 'in_progress',
      conclusion: null,
      created_at: '2026-10-17T09:00:00Z',
      run_started_at: '2026-10-17T09:00:00Z',
    })],
    deployRuns: [],
  });
  const kept = decideWeeklyPush({
    release: early,
    previousKey: '2026-10-10:released',
    previousConclusion: 'success',
    nowIso: '2026-10-17T10:00:00Z',
  });
  assert.equal(kept.push, false);
  assert.equal(kept.notifiedKey, '2026-10-10:released');

  const late = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:33:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [liveWeekly],
    deployRuns: [],
  });
  const firstLate = decideWeeklyPush({
    release: late,
    previousKey: kept.notifiedKey,
    previousConclusion: 'success',
    nowIso: '2026-10-17T13:33:00Z',
  });
  assert.equal(firstLate.push, true);
  assert.equal(firstLate.exitCode, 0);
  const repeatLate = decideWeeklyPush({
    release: late,
    previousKey: firstLate.notifiedKey,
    previousConclusion: 'success',
    nowIso: '2026-10-17T14:00:00Z',
  });
  assert.equal(repeatLate.push, false);

  const done = evaluateWeeklyRelease({
    nowIso: '2026-10-17T14:05:00Z',
    snapshotOnMain: 'present',
    snapshotOnSite: 'present',
    weeklyRuns: [run({ conclusion: 'success', status: 'completed' })],
    deployRuns: [run({
      id: 11,
      conclusion: 'success',
      status: 'completed',
      created_at: '2026-10-17T13:36:30Z',
      updated_at: '2026-10-17T14:00:10Z',
      event: 'workflow_run',
    })],
  });
  const receipt = decideWeeklyPush({
    release: done,
    previousKey: late.key,
    previousConclusion: 'success',
    nowIso: '2026-10-17T14:05:00Z',
  });
  assert.equal(receipt.push, true);
  assert.notEqual(late.key, done.key);
  const weekday = decideWeeklyPush({
    release: done,
    previousKey: done.key,
    previousConclusion: 'success',
    nowIso: '2026-10-21T09:00:00Z',
  });
  assert.equal(weekday.push, false);
  assert.equal(weekday.exitCode, 0);
});

test('an unreadable previous key still sends, and the key is stored only after the send', () => {
  const release = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:00:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [],
    deployRuns: [],
  });
  const decision = decideWeeklyPush({
    release,
    previousKey: null,
    previousConclusion: 'failure',
    nowIso: '2026-10-17T13:00:00Z',
  });
  assert.equal(decision.push, true);
  assert.equal(releaseKeyToPrint({
    push: decision.push,
    notifiedKey: decision.notifiedKey,
    previousKey: null,
    sent: false,
  }), '');
  assert.equal(releaseKeyToPrint({
    push: decision.push,
    notifiedKey: decision.notifiedKey,
    previousKey: null,
    sent: true,
  }), release.key);
});

test('unknown repeats through the daily gate, not on every check', () => {
  const release = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:00:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [],
    deployRuns: [],
    apiError: 'HTTP 502',
  });
  const first = decideWeeklyPush({
    release,
    previousKey: null,
    previousConclusion: 'success',
    nowIso: '2026-10-17T13:00:00Z',
  });
  assert.equal(first.push, true);
  assert.equal(first.exitCode, 1);
  const afternoon = decideWeeklyPush({
    release,
    previousKey: release.key,
    previousConclusion: 'failure',
    nowIso: '2026-10-17T15:00:00Z',
  });
  assert.equal(afternoon.push, false);
  const morning = decideWeeklyPush({
    release,
    previousKey: release.key,
    previousConclusion: 'failure',
    nowIso: '2026-10-18T06:10:00Z',
  });
  assert.equal(morning.push, true);
});

test('the weekly-release alert replaces the same-Saturday snapshot and feed alarms', () => {
  const release = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:50:00Z',
    snapshotOnMain: 'present',
    snapshotOnSite: 'absent',
    weeklyRuns: [run({ conclusion: 'success', status: 'completed' })],
    deployRuns: [run({
      id: 9,
      status: 'in_progress',
      conclusion: null,
      created_at: '2026-10-17T13:36:40Z',
      run_started_at: '2026-10-17T13:36:40Z',
      event: 'workflow_run',
    })],
  });
  const agedFeed = evaluateFeedFreshness({
    site: 'https://evidaxis.org',
    reached: true,
    status: 200,
    latestEntryAt: '2026-10-01T00:00:00Z',
    now: new Date('2026-10-17T13:50:00Z'),
  });
  const gated = gateFreshnessAlerts({
    archiveDate: '2026-10-17',
    release,
    snapshot: { alert: true },
    feed: agedFeed,
  });
  assert.equal(gated.snapshot, false);
  assert.equal(gated.feed, false);

  const unknown = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:00:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'unknown',
    weeklyRuns: [],
    deployRuns: [],
    apiError: 'HTTP 502',
  });
  const kept = gateFreshnessAlerts({
    archiveDate: '2026-10-10',
    release: unknown,
    snapshot: { alert: true },
    feed: { alert: true },
  });
  assert.equal(kept.snapshot, true);
  assert.equal(kept.feed, true);

  const released = evaluateWeeklyRelease({
    nowIso: '2026-10-21T09:00:00Z',
    snapshotOnMain: 'present',
    snapshotOnSite: 'present',
    weeklyRuns: [],
    deployRuns: [],
  });
  const feed = gateFreshnessAlerts({
    archiveDate: '2026-10-17',
    release: released,
    snapshot: { alert: false },
    feed: { alert: true },
  });
  assert.equal(feed.feed, true);
});

test('a running release still sends a feed 404 or a broken feed', () => {
  const release = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:33:00Z',
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [liveWeekly],
    deployRuns: [],
  });
  assert.equal(release.status, 'running');
  const now = new Date('2026-10-17T13:33:00Z');
  const missing = evaluateFeedFreshness({
    site: 'https://evidaxis.org', reached: true, status: 404, latestEntryAt: null, now,
  });
  const broken = evaluateFeedFreshness({
    site: 'https://evidaxis.org', reached: true, status: 200, latestEntryAt: 'not-a-date', now,
  });
  const aged = evaluateFeedFreshness({
    site: 'https://evidaxis.org', reached: true, status: 200, latestEntryAt: '2026-10-01T00:00:00Z', now,
  });
  const gate = (feed) => gateFreshnessAlerts({
    archiveDate: '2026-10-10', release, snapshot: { alert: false }, feed,
  });
  assert.equal(gate(missing).feed, true);
  assert.equal(gate(broken).feed, true);
  assert.equal(gate(aged).feed, false);
});

test('a weekly release titled for another date is not this Saturday release', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:00:00Z',
    snapshotOnSite: 'absent',
    snapshotOnMain: 'absent',
    weeklyRuns: [run({
      conclusion: 'success',
      status: 'completed',
      display_title: 'weekly release 2026-10-24',
      created_at: '2026-10-17T09:00:00Z',
      updated_at: '2026-10-17T12:00:00Z',
    })],
    deployRuns: [],
  });
  assert.equal(r.status, 'not_started');
});

test('a stale checkout is not a failed release when main already has this Saturday snapshot', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:00:00Z',
    snapshotOnSite: 'present',
    snapshotOnMain: 'present',
    weeklyRuns: [run({
      conclusion: 'success',
      status: 'completed',
      display_title: 'weekly release 2026-10-17',
      updated_at: '2026-10-17T12:40:00Z',
    })],
    deployRuns: [],
  });
  assert.notEqual(r.status, 'failed');
});

test('Sunday latest and a failed Sunday deploy cannot undo the Saturday publication', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-18T15:00:00Z',
    archiveDate: '2026-10-18', // Deliberately ignored: latest.json is not the Saturday fact.
    snapshotOnSite: 'present',
    snapshotOnMain: 'present',
    weeklyRuns: [run({
      conclusion: 'success',
      status: 'completed',
      display_title: 'weekly release 2026-10-17',
      created_at: '2026-10-17T06:20:00Z',
      updated_at: '2026-10-17T12:40:00Z',
    })],
    deployRuns: [run({ id: 9, conclusion: 'failure', created_at: '2026-10-18T14:00:00Z' })],
  });
  assert.equal(r.status, 'released');
});

test('a new feed failure still sends after a run that failed on the GitHub API', () => {
  const nowIso = '2026-10-17T15:00:00Z';
  const release = evaluateWeeklyRelease({
    nowIso,
    snapshotOnMain: 'absent',
    snapshotOnSite: 'absent',
    weeklyRuns: [],
    deployRuns: [],
    apiError: 'HTTP 502',
  });
  const feed = evaluateFeedFreshness({
    site: 'https://evidaxis.org',
    reached: true,
    status: 404,
    latestEntryAt: null,
    now: new Date(nowIso),
  });
  const gated = gateFreshnessAlerts({
    archiveDate: '2026-10-10',
    release,
    snapshot: { alert: false },
    feed,
  });
  assert.equal(gated.feed, true);
  const decision = decideFeedPush({
    alert: gated.feed,
    key: `feed:${feed.reason}`,
    previousKey: null,
    previousConclusion: 'failure',
    nowIso,
  });
  assert.equal(decision.push, true);
  const repeat = decideFeedPush({
    alert: true,
    key: `feed:${feed.reason}`,
    previousKey: decision.notifiedKey,
    previousConclusion: 'failure',
    nowIso,
  });
  assert.equal(repeat.push, false);
});

test('a successful release with an unknown main snapshot cannot be ok', () => {
  const r = evaluateWeeklyRelease({ nowIso: '2026-10-17T14:00:00Z',
    snapshotOnSite: 'absent', snapshotOnMain: 'unknown',
    weeklyRuns: [run({})], deployRuns: [] });
  assert.equal(r.status, 'unknown');
  assert.equal(r.alert, true);
});

test('a successful date router does not replace a failed release', () => {
  const r = evaluateWeeklyRelease({ nowIso: '2026-10-17T14:00:00Z',
    snapshotOnMain: 'present', snapshotOnSite: 'absent',
    weeklyRuns: [run({ conclusion: 'failure' }), run({ id: 2,
      created_at: '2026-10-17T12:00:00Z', display_title: 'weekly release resolve-date' })],
    deployRuns: [] });
  assert.equal(r.status, 'failed');
  assert.match(r.message, /weekly-snapshot упал/);
});

const completed = run({ display_title: 'weekly release 2026-10-17', created_at: '2026-10-17T02:17:00Z' });
const active = { ...completed, status: 'in_progress', conclusion: null };
const failed = { ...completed, conclusion: 'failure' };
const truthBase = { nowIso: '2026-10-17T14:00:00Z', snapshotOnMain: 'absent', snapshotOnSite: 'absent',
  weeklyRuns: [completed], deployRuns: [] };
const early = '2026-10-17T11:00:00Z';
const truthTable = [
  ['U0', { nowIso: 'invalid' }, 'unknown', true, true],
  ['R1', { snapshotOnMain: 'present', snapshotOnSite: 'present', deployRuns: [failed] }, 'released', true, false],
  ['U1-api', { apiError: 'HTTP 503' }, 'unknown', true, true],
  ['U1-jobs', { weeklyRuns: [{ ...completed, jobs: undefined }] }, 'unknown', true, true],
  ['U1-history', { weeklyRuns: undefined }, 'unknown', true, true],
  ['R2-early', { weeklyRuns: [active], nowIso: early }, 'running', false, false],
  ['R2-late', { weeklyRuns: [active] }, 'running', true, false],
  ['F1', { weeklyRuns: [failed] }, 'failed', true, true],
  ['U2-main', { snapshotOnMain: 'unknown' }, 'unknown', true, true],
  ['U2-site', { snapshotOnSite: 'unknown' }, 'unknown', true, true],
  ['U3', { snapshotOnSite: 'present' }, 'unknown', true, true],
  ['P1-early', { snapshotOnMain: 'present', deployRuns: [active], nowIso: early }, 'publishing', false, false],
  ['P1-late', { snapshotOnMain: 'present', deployRuns: [active] }, 'publishing', true, false],
  ['F2', { snapshotOnMain: 'present', deployRuns: [failed] }, 'failed', true, true],
  ['P2', { snapshotOnMain: 'present', nowIso: early }, 'publishing', false, false],
  ['F3', { snapshotOnMain: 'present' }, 'failed', true, true],
  ['N1-early', { weeklyRuns: [], nowIso: early }, 'not_started', false, false],
  ['N1-late', { weeklyRuns: [] }, 'not_started', true, true],
  ['O1', { nowIso: early }, 'ok', false, false],
  ['F4', {}, 'failed', true, true],
  ['U4', { weeklyRuns: [{ ...completed, conclusion: 'neutral' }] }, 'unknown', true, true],
  ['U4-deploy', { snapshotOnMain: 'present', deployRuns: [{ ...completed, conclusion: 'neutral' }] }, 'unknown', true, true],
];
for (const [row, facts, status, alert, remind] of truthTable) {
  test(`release truth table ${row}: ${status}`, () => {
    const result = evaluateWeeklyRelease({ ...truthBase, ...facts });
    assert.deepEqual([result.status, result.alert, result.remind], [status, alert, remind]);
    if (alert) assert.match(result.message, /Нужен человек: (да|нет)/);
  });
}

test('both guard skip locations and rehearsals are excluded from release identity', () => {
  for (const run of [
    { ...completed, display_title: 'weekly release resolve-date' },
    { ...completed, display_title: 'weekly rehearsal 2026-10-17' },
    { ...completed, head_branch: 'test' },
    { ...completed, event: 'pull_request' },
    { ...completed, jobs: [{ name: 'snapshot', conclusion: 'skipped' }] },
    { ...completed, jobs: [{ name: 'snapshot', steps: [{ name: COLLECT_STEP, conclusion: 'skipped' }] }] },
  ]) {
    assert.equal(releaseRunKind(run), 'ignore');
    const result = evaluateWeeklyRelease({ ...truthBase, weeklyRuns: [failed, { ...run, id: 2,
      created_at: '2026-10-17T06:17:00Z' }] });
    assert.equal(result.status, 'failed');
    assert.match(result.message, /weekly-snapshot упал/);
  }
  assert.equal(releaseRunDate(run({})), '2026-10-17', 'old bare weekly-snapshot titles remain readable');
  assert.equal(releaseRunDate({ ...completed, display_title: 'unrelated workflow' }), null);
});

test('Jobs API enrichment accepts only a complete response and leaves failures unknown', async () => {
  for (const body of [null, {}, { total_count: 2, jobs: completed.jobs }, { total_count: 0, jobs: [] }]) {
    const candidate = { ...completed, jobs: undefined };
    await attachReleaseJobs([candidate], async () => {
      if (body === null) throw new Error('timeout');
      return body;
    });
    assert.equal(releaseRunKind(candidate), 'unknown');
  }
  const candidate = { ...completed, jobs: undefined };
  const calls = [];
  await attachReleaseJobs([candidate, failed], async id => {
    calls.push(id);
    return { total_count: 1, jobs: completed.jobs };
  });
  assert.deepEqual(calls, [completed.id]);
  assert.equal(releaseRunKind(candidate), 'release');
});

function mockWeeklyApi(t, { mainStatus = 200, mainTimeout = false, siteStatus = 200,
  siteBody = { snapshot_date: '2026-10-17' }, deployRuns = [], weeklyBody } = {}) {
  const oldToken = process.env.GH_TOKEN;
  const oldRepo = process.env.GITHUB_REPOSITORY;
  process.env.GH_TOKEN = 'test_token';
  process.env.GITHUB_REPOSITORY = 'evidaxis/evidaxis';
  t.after(() => {
    if (oldToken === undefined) delete process.env.GH_TOKEN; else process.env.GH_TOKEN = oldToken;
    if (oldRepo === undefined) delete process.env.GITHUB_REPOSITORY; else process.env.GITHUB_REPOSITORY = oldRepo;
  });
  const requests = [];
  t.mock.method(globalThis, 'fetch', async url => {
    requests.push(String(url));
    const parsed = new URL(url);
    if (parsed.hostname === 'evidaxis.org') {
      assert.equal(parsed.pathname, '/snapshots/2026-10-17/snapshot.json');
      return Response.json(siteBody, { status: siteStatus });
    }
    if (parsed.pathname.includes('/contents/')) {
      assert.equal(parsed.pathname, '/repos/evidaxis/evidaxis/contents/data/snapshots/2026-10-17/snapshot.json');
      assert.equal(parsed.searchParams.get('ref'), 'main');
      if (mainTimeout) throw new DOMException('timeout', 'TimeoutError');
      return Response.json({}, { status: mainStatus });
    }
    if (parsed.pathname.includes('/workflows/')) {
      assert.equal(parsed.searchParams.get('branch'), 'main');
      if (parsed.pathname.includes('weekly-snapshot')) return Response.json(weeklyBody ?? { total_count: 1, workflow_runs: [completed] });
      return Response.json({ total_count: deployRuns.length, workflow_runs: deployRuns });
    }
    if (parsed.pathname.endsWith('/jobs')) return Response.json({ total_count: 1, jobs: completed.jobs });
    throw new Error('unexpected request');
  });
  return requests;
}

test('Sunday runner probes Saturday content independently of latest and Sunday deploy failure', async (t) => {
  const requests = mockWeeklyApi(t, { deployRuns: [{ ...failed, id: 9, created_at: '2026-10-18T14:00:00Z' }] });
  const facts = await readWeeklyFacts('https://evidaxis.org', '2026-10-18T15:00:00Z');
  const result = evaluateWeeklyRelease({ ...facts, archiveDate: '2026-10-18', prodDate: '2026-10-18' });
  assert.equal(result.status, 'released');
  assert.equal(requests.filter(url => url === 'https://evidaxis.org/snapshots/2026-10-17/snapshot.json').length, 1);
});

for (const failure of [{ mainTimeout: true }, { mainStatus: 403 }, { mainStatus: 500 }]) {
  test(`main API ${failure.mainStatus ?? 'timeout'} after successful collection stays unknown`, async (t) => {
    mockWeeklyApi(t, { ...failure, siteStatus: 404 });
    const facts = await readWeeklyFacts('https://evidaxis.org', '2026-10-17T14:00:00Z');
    assert.equal(facts.snapshotOnMain, 'unknown');
    const result = evaluateWeeklyRelease(facts);
    assert.equal(result.status, 'unknown');
    assert.equal(result.alert, true);
  });
}

for (const [label, options] of [['HTTP 503', { siteStatus: 503 }], ['no date', { siteBody: {} }], ['null', { siteBody: null }]]) {
  test(`public ${label} cannot confirm publication`, async (t) => {
    mockWeeklyApi(t, options);
    const facts = await readWeeklyFacts('https://evidaxis.org', '2026-10-17T14:00:00Z');
    assert.equal(facts.snapshotOnSite, 'unknown');
    assert.equal(evaluateWeeklyRelease(facts).status, 'unknown');
  });
}

for (const [label, weeklyBody] of [['missing', {}], ['truncated', { total_count: 2, workflow_runs: [completed] }],
  ['invalid', { total_count: 1, workflow_runs: [{ ...completed, created_at: null }] }]]) {
  test(`${label} workflow history is unknown rather than an empty successful history`, async (t) => {
    mockWeeklyApi(t, { weeklyBody, mainStatus: 404, siteStatus: 404 });
    const facts = await readWeeklyFacts('https://evidaxis.org', '2026-10-17T14:00:00Z');
    assert.equal(evaluateWeeklyRelease(facts).status, 'unknown');
  });
}

test('a confirmed main 404 and public content for a different date mean absent, not unknown', async (t) => {
  mockWeeklyApi(t, { mainStatus: 404, siteBody: { snapshot_date: '2026-10-10' } });
  const facts = await readWeeklyFacts('https://evidaxis.org', '2026-10-17T14:00:00Z');
  assert.equal(facts.snapshotOnMain, 'absent');
  assert.equal(facts.snapshotOnSite, 'absent');
  assert.equal(evaluateWeeklyRelease(facts).status, 'failed');
});

const hfStep = 'Mirror the dated snapshot to HF and verify public contents';
function attempt(number, conclusion, steps, over = {}) {
  const hour = number === 1 ? '02:17' : '09:00';
  return { ...completed, id: 101, run_attempt: number, status: 'completed', conclusion,
    created_at: '2026-10-17T02:17:00Z', run_started_at: `2026-10-17T${hour}:00Z`,
    updated_at: `2026-10-17T${number === 1 ? '04:00' : '11:00'}:00Z`,
    jobs: [{ name: 'snapshot', conclusion, steps }], ...over };
}
const hfFailure = attempt(1, 'failure', [
  { name: COLLECT_STEP, conclusion: 'success' }, { name: hfStep, conclusion: 'failure' },
]);
const skippedRetry = attempt(2, 'success', [
  { name: COLLECT_STEP, conclusion: 'skipped' }, { name: hfStep, conclusion: 'skipped' },
]);
function watchdogFor(weeklyRuns) {
  return evaluateWorkflowHealth({ roster: [{ name: 'weekly-snapshot', kind: 'scheduled', budgetHours: 204 }],
    weeklyRuns, latestCompleted: {}, latestSuccess: {}, nowIso: '2026-10-17T13:00:00Z' })[0];
}

test('a successful no-op rerun retains the same run ID HF failure in both sensors', async () => {
  const retry = { ...skippedRetry };
  const history = [hfFailure, skippedRetry];
  await attachReleaseJobs([retry], async (id, number = 2) => ({ total_count: 1, jobs: history[number - 1].jobs }),
    async (id, number) => history[number - 1]);
  const olderSuccess = { ...completed, id: 99, created_at: '2026-10-17T01:00:00Z', run_started_at: '2026-10-17T01:00:00Z' };
  const health = watchdogFor([retry, olderSuccess]);
  assert.equal(health.status, 'red');
  assert.equal(health.alert, true);
  const release = evaluateWeeklyRelease({ ...truthBase, weeklyRuns: [retry],
    snapshotOnMain: 'present', snapshotOnSite: 'present' });
  assert.equal(release.status, 'failed');
  assert.match(release.message, /Mirror the dated snapshot to HF/);
  assert.match(release.message, /попытка 1/);
});

test('a skipped deployment is absent work, so an unstarted Saturday stays not_started', () => {
  const release = evaluateWeeklyRelease({ ...truthBase, nowIso: '2026-10-17T13:00:00Z', weeklyRuns: [],
    deployRuns: [{ ...completed, conclusion: 'skipped' }] });
  assert.equal(release.status, 'not_started');
  assert.equal(release.alert, true);
});

test('a successful 09:00 rerun of A supersedes the failed 04:17 B despite the original ID and creation time', async () => {
  const success = attempt(2, 'success', [
    { name: COLLECT_STEP, conclusion: 'success' }, { name: hfStep, conclusion: 'success' },
  ]);
  await attachReleaseJobs([success], async (id, number = 2) => ({ total_count: 1, jobs: [hfFailure, success][number - 1].jobs }),
    async () => hfFailure);
  const b = { ...failed, id: 102, created_at: '2026-10-17T04:17:00Z', run_started_at: '2026-10-17T04:17:00Z' };
  const release = evaluateWeeklyRelease({ ...truthBase, nowIso: '2026-10-17T11:30:00Z',
    snapshotOnMain: 'present', weeklyRuns: [b, success],
    deployRuns: [{ ...active, id: 103, run_started_at: '2026-10-17T11:10:00Z' }] });
  assert.equal(release.status, 'publishing');
  assert.equal(release.alert, false);
  assert.equal(watchdogFor([b, success]).alert, false);
});

async function withAttempts(history) {
  const latest = { ...history.at(-1) };
  await attachReleaseJobs([latest], async (id, number) => ({ total_count: 1, jobs: history[number - 1].jobs }),
    async (id, number) => history[number - 1]);
  return latest;
}

test('collection success cannot recover HF; only the same failed step in the same job can', async () => {
  for (const jobs of [
    [{ name: 'snapshot', conclusion: 'success', steps: [{ name: COLLECT_STEP, conclusion: 'success' }] }],
    [{ name: 'other job', conclusion: 'success', steps: [{ name: hfStep, conclusion: 'success' }] }],
  ]) {
    const latest = await withAttempts([hfFailure, { ...skippedRetry, jobs }]);
    assert.equal(watchdogFor([latest]).status, 'red');
    assert.equal(evaluateWeeklyRelease({ ...truthBase, weeklyRuns: [latest],
      snapshotOnMain: 'present', snapshotOnSite: 'present' }).status, 'failed');
  }
  const recovered = await withAttempts([hfFailure, attempt(2, 'success', [
    { name: COLLECT_STEP, conclusion: 'skipped' }, { name: hfStep, conclusion: 'success' },
  ])]);
  assert.equal(watchdogFor([recovered]).alert, false);
  assert.equal(evaluateWeeklyRelease({ ...truthBase, weeklyRuns: [recovered],
    snapshotOnMain: 'present', snapshotOnSite: 'present' }).status, 'released');
});

test('several skipped attempts preserve failure until recovery and do not refresh success time', async () => {
  const thirdSkip = { ...skippedRetry, run_attempt: 3, run_started_at: '2026-10-17T11:10:00Z' };
  const skipped = await withAttempts([hfFailure, skippedRetry, thirdSkip]);
  assert.equal(watchdogFor([skipped]).status, 'red');
  const recovery = attempt(2, 'success', [{ name: hfStep, conclusion: 'success' }]);
  const recovered = await withAttempts([hfFailure, recovery, thirdSkip]);
  assert.equal(watchdogFor([recovered]).alert, false);
  assert.equal(effectiveRun(recovered).run_attempt, 2);
  assert.equal(effectiveRun(recovered).run_started_at, '2026-10-17T09:00:00Z');
});

test('a different run must actually repair the retained failed stage before clearing it', async () => {
  const retry = await withAttempts([hfFailure, skippedRetry]);
  const newer = { ...completed, id: 102, run_started_at: '2026-10-17T11:00:00Z' };
  for (const candidate of [{ ...newer, status: 'in_progress', conclusion: null }, newer]) {
    const weeklyRuns = [retry, candidate];
    assert.equal(watchdogFor(weeklyRuns).status, 'red');
    assert.equal(evaluateWeeklyRelease({ ...truthBase, weeklyRuns, snapshotOnMain: 'present',
      snapshotOnSite: 'present' }).status, 'failed');
  }
  const repaired = { ...newer, jobs: [{ name: 'snapshot', steps: [{ name: hfStep, conclusion: 'success' },
    { name: COLLECT_STEP, conclusion: 'success' }] }] };
  assert.equal(watchdogFor([retry, repaired]).alert, false);
  assert.equal(evaluateWeeklyRelease({ ...truthBase, weeklyRuns: [retry, repaired],
    snapshotOnMain: 'present', snapshotOnSite: 'present' }).status, 'released');
});

test('a skipped deploy rerun preserves its earlier failed deployment step', async () => {
  const first = { ...hfFailure, display_title: 'deploy-web', jobs: [{ name: 'deploy', conclusion: 'failure',
    steps: [{ name: 'Deploy prebuilt dist to Vercel production', conclusion: 'failure' }] }] };
  const latest = { ...skippedRetry, display_title: 'deploy-web', conclusion: 'skipped',
    jobs: [{ name: 'deploy', conclusion: 'skipped', steps: [] }] };
  const run = await withAttempts([first, latest]);
  const release = evaluateWeeklyRelease({ ...truthBase, weeklyRuns: [completed],
    snapshotOnMain: 'present', snapshotOnSite: 'present', deployRuns: [run] });
  assert.equal(release.status, 'failed');
  assert.match(release.message, /Deploy prebuilt dist to Vercel production/);
  const [health] = evaluateWorkflowHealth({ roster: [{ name: 'deploy-web', kind: 'event' }],
    latestCompleted: { 'deploy-web': effectiveRun(run) }, latestSuccess: {}, nowIso: truthBase.nowIso });
  assert.equal(health.status, 'red');
  const repaired = await withAttempts([first, { ...latest, conclusion: 'success', jobs: [{ name: 'deploy',
    conclusion: 'success', steps: [{ name: 'Deploy prebuilt dist to Vercel production', conclusion: 'success' }] }] }]);
  assert.equal(evaluateWeeklyRelease({ ...truthBase, snapshotOnMain: 'present', snapshotOnSite: 'present',
    deployRuns: [repaired] }).status, 'released');
});

for (const fault of ['timeout', 'incomplete jobs', 'wrong attempt', 'reused jobs', 'missing start']) {
  test(`rerun evidence ${fault} is unknown even when the site has the snapshot`, async () => {
    const latest = { ...skippedRetry, ...(fault === 'missing start' ? { run_started_at: undefined } : {}) };
    await attachReleaseJobs([latest], async (id, number) => {
      const jobs = [hfFailure, skippedRetry][number - 1].jobs;
      return { total_count: fault === 'incomplete jobs' ? 2 : 1,
        jobs: fault === 'reused jobs' ? jobs.map(job => ({ ...job, run_attempt: 99 })) : jobs };
    }, async () => {
      if (fault === 'timeout') throw new Error('timeout');
      return fault === 'wrong attempt' ? { ...hfFailure, run_attempt: 2 } : hfFailure;
    });
    assert.equal(watchdogFor([latest]).status, 'unknown');
    assert.equal(evaluateWeeklyRelease({ ...truthBase, weeklyRuns: [latest],
      snapshotOnMain: 'present', snapshotOnSite: 'present' }).status, 'unknown');
  });
}

test('equal attempt start times use run_attempt before the stable run ID', () => {
  const retry = { ...skippedRetry, id: 1 };
  const original = { ...completed, id: 9, run_attempt: 1, run_started_at: retry.run_started_at };
  assert.ok(compareAttempts(retry, original) < 0);
  assert.deepEqual([original, retry].sort(compareAttempts), [retry, original]);
});

test('runner fetches explicit attempt summaries and jobs rather than losing HF failure to latest success', async (t) => {
  const requests = mockWeeklyApi(t, { weeklyBody: { total_count: 1, workflow_runs: [skippedRetry] } });
  const baseFetch = globalThis.fetch;
  t.mock.method(globalThis, 'fetch', async url => {
    const path = new URL(url).pathname;
    if (path.includes('/actions/runs/')) {
      requests.push(String(url));
      const match = /\/runs\/101\/attempts\/(1|2)(\/jobs)?$/.exec(path);
      assert.ok(match, 'attempt endpoints are required');
      const run = [hfFailure, skippedRetry][Number(match[1]) - 1];
      return Response.json(match[2] ? { total_count: 1, jobs: run.jobs } : run);
    }
    return baseFetch(url);
  });
  const facts = await readWeeklyFacts('https://evidaxis.org', truthBase.nowIso);
  assert.equal(evaluateWeeklyRelease(facts).status, 'failed');
  assert.ok(requests.some(url => url.endsWith('/attempts/1')));
  assert.ok(requests.some(url => url.includes('/attempts/1/jobs?per_page=100')));
  assert.ok(requests.some(url => url.includes('/attempts/2/jobs?per_page=100')));
});

test('a site receipt cannot certify recovery when run history is unavailable', () => {
  const release = evaluateWeeklyRelease({ ...truthBase, snapshotOnMain: 'present', snapshotOnSite: 'present',
    weeklyRuns: [], apiError: 'HTTP 503' });
  assert.equal(release.status, 'unknown');
  assert.equal(release.alert, true);
});
