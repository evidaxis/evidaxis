import { test } from 'node:test';
import assert from 'node:assert/strict';
import { evaluateWorkflowHealth } from './workflow-watchdog.mjs';
import { weeklyReleaseDay } from './weekly-release.mjs';
import {
  decideFeedPush,
  decideWeeklyPush,
  evaluateFeedFreshness,
  evaluateFreshness,
  evaluateWeeklyRelease,
  gateFreshnessAlerts,
  parseReleaseKey,
  parseReceiptWeek,
  parseActiveWeek,
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


const date = '2026-10-17';
const sha = 'a'.repeat(40);
const early = `${date}T11:59:59Z`;
const noon = `${date}T12:00:00Z`;
const late = `${date}T13:33:00Z`;
const stages = ['captured', 'deployed', 'hf'];
function record(states = ['success', 'success', 'success'], commit = sha) {
  const statuses = states.flatMap((state, n) => state ? [{ context: `evidaxis/release-${stages[n]}`, state,
    description: n === 0 && state === 'success' ? date : `Verify ${stages[n]}`,
    updated_at: `${date}T09:00:00Z` }] : []);
  return { date, sha: commit, statuses, total_count: statuses.length };
}
function health(facts) {
  return evaluateWorkflowHealth({ nowIso: facts.nowIso, releaseFacts: facts,
    roster: [{ name: 'weekly-snapshot', kind: 'scheduled', critical: true, budgetHours: 204 }],
    latestCompleted: { 'weekly-snapshot': { conclusion: 'success' } },
    latestSuccess: { 'weekly-snapshot': { conclusion: 'success' } } })[0];
}

// Every combination of three context states, activity, deadline and API errors.
// Explicit expectations are attached to the table rows, shared by both sensors.
const rows = [
  ['SSS', ['success', 'success', 'success'], 'released', 'released', 'released'],
  ['SS-', ['success', 'success', null], 'publishing', 'publishing', 'failed'],
  ['S-S', ['success', null, 'success'], 'publishing', 'publishing', 'failed'],
  ['S--', ['success', null, null], 'publishing', 'publishing', 'failed'],
  ['-SS', [null, 'success', 'success'], 'running', 'running', 'failed'],
  ['-S-', [null, 'success', null], 'running', 'running', 'failed'],
  ['--S', [null, null, 'success'], 'running', 'running', 'failed'],
  ['---', [null, null, null], 'running', 'running', 'failed'],
];
for (const captured of [null, 'success', 'failure']) {
  for (const deployed of [null, 'success', 'failure']) {
    for (const hf of [null, 'success', 'failure']) {
      const states = [captured, deployed, hf];
      if (states.includes('failure')) rows.push([states.join('/'), states, 'failed', 'failed', 'failed']);
    }
  }
}
for (const [label, states, before, moving, stopped] of rows) {
  for (const active of [false, true]) for (const nowIso of [early, noon]) for (const apiError of ['', 'HTTP 503']) {
    const expected = apiError ? 'unknown' : nowIso === early ? before : active ? moving : stopped;
    const alert = ['unknown', 'failed', 'released'].includes(expected) || nowIso === noon;
    test(`truth ${label} active=${active} ${nowIso.slice(11)} API=${apiError || 'ok'} -> ${expected}`, () => {
      const facts = { record: record(states), active, nowIso, apiError };
      const result = evaluateWeeklyRelease(facts);
      assert.equal(result.status, expected);
      assert.equal(result.alert, alert);
      assert.equal(result.remind, ['unknown', 'failed'].includes(expected));
      if (result.alert) assert.match(result.message, new RegExp(`Нужен человек: ${expected === 'failed' ? 'да' : 'нет'}`));
      if (states.includes('failure') && !apiError) assert.match(result.message, /шаг «Verify /);
      if (expected === 'failed' && !states.includes('failure')) assert.match(result.message, /не дошло до этапа/);
      const watched = health(facts);
      assert.equal(watched.releaseStatus, expected);
      assert.equal(watched.alert, result.alert && result.remind);
    });
  }
}
for (const active of [false, true]) for (const nowIso of [early, noon]) for (const apiError of ['', 'HTTP 503']) {
  test(`truth no commit active=${active} ${nowIso.slice(11)} API=${apiError || 'ok'}`, () => {
    const facts = { record: record([null, null, null], null), active, nowIso, apiError };
    const result = evaluateWeeklyRelease(facts);
    assert.equal(result.status, apiError ? 'unknown' : active ? 'running' : 'not_started');
    assert.equal(result.alert, Boolean(apiError) || nowIso === noon);
    assert.equal(result.remind, Boolean(apiError) || (!active && nowIso === noon));
    assert.equal(health(facts).releaseStatus, result.status);
  });
}

test('invalid time, date, record, unknown activity and malformed statuses cannot buy ok', () => {
  const good = { record: record(), nowIso: late };
  for (const patch of [
    { nowIso: 'bad' }, { record: undefined }, { record: { ...record(), date: '2026-10-18' } },
    { record: { ...record(), total_count: 99 } }, { record: { ...record(), sha: null } },
    { record: record(['success', null, null]), active: undefined },
    { record: record(['success', 'neutral', 'success']) },
    { record: { ...record(), statuses: [{ context: 'evidaxis/release-hf', state: 'failure' }], total_count: 1 } },
    { record: { ...record(), statuses: [record().statuses[0], record().statuses[0]], total_count: 2 } },
    { record: { ...record(), statuses: [{ context: 'evidaxis/release-captured', state: 'success', description: '2026-10-18' }], total_count: 1 } },
  ]) assert.equal(evaluateWeeklyRelease({ ...good, ...patch }).status, 'unknown');
  assert.equal(health({ nowIso: late }).status, 'unknown', 'watchdog cannot fall back to completed/success');
});

test('pending is an unfinished stage and an error status is a failure', () => {
  assert.equal(evaluateWeeklyRelease({ nowIso: late, record: record(['success', 'pending', 'success']), active: true }).status, 'publishing');
  assert.equal(evaluateWeeklyRelease({ nowIso: early, record: record(['success', 'error', 'success']) }).status, 'failed');
});

test('Sunday latest and Sunday failure cannot undo the Saturday record', () => {
  const facts = { nowIso: '2026-10-18T15:00:00Z', record: record(), archiveDate: '2026-10-18',
    weeklyRuns: [{ conclusion: 'failure' }], deployRuns: [{ conclusion: 'failure' }] };
  assert.equal(weeklyReleaseDay(facts.nowIso), date);
  assert.equal(evaluateWeeklyRelease(facts).status, 'released');
  assert.equal(health(facts).status, 'ok');
});

test('HF failure survives any number of skipped or successful runs until HF writes success', () => {
  const facts = { nowIso: late, record: record(['success', 'success', 'failure']), active: true,
    weeklyRuns: [{ conclusion: 'success', run_attempt: 5, jobs: [{ conclusion: 'skipped' }] }] };
  assert.equal(evaluateWeeklyRelease(facts).status, 'failed');
  assert.equal(health(facts).status, 'red');
  // A new run, a rerun, or hf-mirror all repair the same context without recapture.
  facts.record = record();
  assert.equal(evaluateWeeklyRelease(facts).status, 'released');
  assert.equal(health(facts).status, 'ok');
});

test('the release key is the last RELEASE_KEY line in the job log', () => {
  assert.equal(parseReleaseKey('RELEASE_KEY 2026-10-10:released\n2026-10-17T14:00:00Z RELEASE_KEY 2026-10-17:running\n'), `${date}:running`);
  assert.equal(parseReleaseKey('RELEASE_KEY -\n'), null);
  assert.equal(parseReleaseKey(''), null);
  assert.equal(parseReceiptWeek('RELEASE_RECEIPT 2026-10-17\nRELEASE_KEY 2026-10-17:unknown'), date);
  assert.equal(parseReceiptWeek('RELEASE_RECEIPT -'), null);
  assert.equal(parseActiveWeek('RELEASE_ACTIVE 2026-10-17'), date);
});

test('17 Oct 13:33 running is late; quiet checks preserve keys; late and released never reach Telegram', () => {
  const facts = { record: record([null, null, null], null), active: true };
  const quiet = evaluateWeeklyRelease({ ...facts, nowIso: early });
  const previousKey = '2026-10-10:released';
  assert.deepEqual(decideWeeklyPush({ release: quiet, previousKey, nowIso: early }),
    { push: false, exitCode: 0, notifiedKey: previousKey });
  const running = evaluateWeeklyRelease({ ...facts, nowIso: late });
  assert.equal(running.status, 'running');
  assert.match(running.message, /опаздывает, но идёт/);
  assert.match(running.message, /Нужен человек: нет/);
  const released = evaluateWeeklyRelease({ nowIso: late, record: record() });
  for (const release of [running, released]) {
    // 29 Oct 16:48 UTC the receipt reached the keeper after a failed week; lost keys must not send it either.
    for (const lost of [previousKey, null, `${date}:failed`]) {
      assert.deepEqual(decideWeeklyPush({ release, previousKey: lost, previousConclusion: 'failure', nowIso: late }),
        { push: false, exitCode: 0, notifiedKey: release.key });
    }
    for (const nowIso of [late, '2026-10-18T06:10:00Z']) {
      assert.deepEqual(decideWeeklyPush({ release, previousKey: release.key, nowIso }),
        { push: false, exitCode: 0, notifiedKey: release.key });
    }
  }
});

test('failed delivery does not consume a key, unknown uses the existing daily reminder', () => {
  const release = evaluateWeeklyRelease({ nowIso: late, apiError: 'HTTP 503' });
  const decision = decideWeeklyPush({ release, previousKey: null, previousConclusion: 'failure', nowIso: late });
  assert.equal(decision.push, true);
  assert.equal(decision.exitCode, 1);
  assert.equal(releaseKeyToPrint({ ...decision, sent: false }), '');
  assert.equal(releaseKeyToPrint({ ...decision, sent: true }), release.key);
  assert.equal(decideWeeklyPush({ release, previousKey: release.key, previousConclusion: 'failure', nowIso: late }).push, false);
  assert.equal(decideWeeklyPush({ release, previousKey: release.key, previousConclusion: 'failure', nowIso: '2026-10-18T06:10:00Z' }).push, true);
});

test('release alerts own only same-date snapshot and age-only feed alarms', () => {
  const gate = (release, reason = 'age', archiveDate = date) => gateFreshnessAlerts({
    archiveDate, release, snapshot: { alert: true }, feed: { alert: true, reason },
  });
  const running = evaluateWeeklyRelease({ nowIso: late, record: record([null, null, null], null), active: true });
  assert.deepEqual(gate(running), { snapshot: false, feed: false });
  assert.equal(gate(running, 'http').feed, true);
  assert.equal(gate(running, 'invalid-date').feed, true);
  assert.equal(gate(running, 'age', '2026-10-10').snapshot, true);
  for (const release of [evaluateWeeklyRelease({ nowIso: late, apiError: 'HTTP 503' }),
    evaluateWeeklyRelease({ nowIso: late, record: record() })]) {
    assert.deepEqual(gate(release), { snapshot: true, feed: true });
  }
});

test('one late message spans capture and publication; both notices survive intervening unknown', () => {
  const running = evaluateWeeklyRelease({ nowIso: late, record: record([null, null, null], null), active: true });
  const publishing = evaluateWeeklyRelease({ nowIso: late, record: record(['success', null, null]), active: true });
  assert.equal(running.key, publishing.key);
  assert.equal(decideWeeklyPush({ release: publishing, previousKey: `${date}:unknown`, previousActiveWeek: date, nowIso: late }).push, false);
  assert.equal(decideWeeklyPush({ release: publishing, previousKey: running.key, nowIso: late }).push, false);
  const released = evaluateWeeklyRelease({ nowIso: late, record: record() });
  assert.equal(decideWeeklyPush({ release: released, previousKey: `${date}:unknown`, previousReceiptWeek: date, nowIso: late }).push, false);
});
