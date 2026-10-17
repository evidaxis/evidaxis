import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
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
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
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
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
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
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
    weeklyRuns,
    deployRuns: [],
  });
  const noon = evaluateWeeklyRelease({
    nowIso: '2026-10-17T12:00:00Z',
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
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
    archiveDate: '2026-10-17',
    prodDate: '2026-10-10',
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
    archiveDate: '2026-10-17',
    prodDate: '2026-10-17',
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
    archiveDate: '2026-10-03',
    prodDate: '2026-10-03',
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
    archiveDate: '2026-10-03',
    prodDate: '2026-10-03',
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
    archiveDate: '2026-09-26',
    prodDate: '2026-09-26',
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
      archiveDate: '2026-10-10',
      prodDate: '2026-10-10',
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

test('Saturday 13:00 rehearsal or dry-run is not the release and does not clear a failure', () => {
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
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
    weeklyRuns: [failure, rehearsal],
    deployRuns: [],
  });
  assert.equal(stillFailed.status, 'failed');
  assert.match(stillFailed.message, /Collect/);
  assert.doesNotMatch(stillFailed.message, /в архиве нет/);

  const base = {
    nowIso: '2026-10-17T13:00:00Z',
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
    deployRuns: [],
  };
  for (const weeklyRuns of [
    [rehearsal],
    [run({ conclusion: 'success', status: 'completed', dry_run: true, display_title: 'weekly-snapshot' })],
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

test('Saturday 13:00 a successful release with last week still in the archive has failed', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:00:00Z',
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
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

test('a newer success clears an earlier failure', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:10:00Z',
    archiveDate: '2026-10-17',
    prodDate: '2026-10-10',
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
    deployRuns: [],
  });
  assert.notEqual(r.status, 'failed');
  assert.equal(r.alert, false);
});

test('Saturday 13:00 UTC with no run for that Saturday has not started', () => {
  const r = evaluateWeeklyRelease({
    nowIso: '2026-10-17T13:00:00Z',
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
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
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
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
    archiveDate: '2026-10-17',
    prodDate: '2026-10-10',
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
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
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
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
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
    archiveDate: '2026-10-17',
    prodDate: '2026-10-17',
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
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
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
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
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
    archiveDate: '2026-10-17',
    prodDate: '2026-10-10',
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
    archiveDate: '2026-10-10',
    prodDate: null,
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
    archiveDate: '2026-10-17',
    prodDate: '2026-10-17',
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
    archiveDate: '2026-10-10',
    prodDate: '2026-10-10',
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
