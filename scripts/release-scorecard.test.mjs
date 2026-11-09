import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  actorKind,
  buildScorecard,
  REPAIR_ACTORS,
  releaseSaturday,
  saturdayKind,
  snapshotSkipped,
  toMarkdown,
} from './release-scorecard.mjs';

function load(name) {
  return JSON.parse(readFileSync(new URL(`./fixtures/release-scorecard/${name}.json`, import.meta.url), 'utf8'));
}

function row(card, saturday) {
  const found = card.rows.find(item => item.saturday === saturday);
  assert.ok(found, saturday);
  return found;
}

test('17 Oct finishes after 12:00 with no person, so it is late and not ok', () => {
  const facts = load('week-2026-10-17');
  const card = buildScorecard(facts);
  const week = row(card, '2026-10-17');
  assert.equal(week.human, false);
  assert.equal(week.on_time, false);
  assert.equal(week.ok, false);
  assert.equal(week.hf, 'нет записи');
  assert.equal(week.capture_start, '2026-10-17T10:54:30Z');
  assert.equal(week.capture_end, '2026-10-17T13:36:25Z');
  assert.equal(week.deploy_end, '2026-10-17T14:00:21Z');
  assert.equal(card.score, '0 из 4');
  const text = toMarkdown(card);
  assert.match(text, /10:54 success/);
  assert.match(text, /13:36 success/);
  assert.match(text, /13:36→14:00 success/);
  assert.equal(text.includes('http'), false);

  const early = structuredClone(facts);
  early.weekly[0].completed_at = '2026-10-17T11:59:59Z';
  early.deploys[0].started_at = '2026-10-17T11:59:59Z';
  early.deploys[0].completed_at = '2026-10-17T11:59:59Z';
  assert.equal(row(buildScorecard(early), '2026-10-17').on_time, true);

  const noon = structuredClone(facts);
  noon.weekly[0].completed_at = '2026-10-17T12:00:00Z';
  noon.deploys[0].completed_at = '2026-10-17T12:00:00Z';
  assert.equal(row(buildScorecard(noon), '2026-10-17').on_time, false);

  const rerun = structuredClone(facts);
  rerun.weekly[0].run_attempt = 2;
  rerun.weekly[0].completed_at = '2026-10-17T11:30:00Z';
  rerun.deploys[0].completed_at = '2026-10-17T11:40:00Z';
  assert.equal(row(buildScorecard(rerun), '2026-10-17').human, true);
  assert.equal(actorKind({ login: 'secret-login', type: 'User' }), 'human');
  const leaked = buildScorecard({
    ...facts,
    weekly: [{ ...facts.weekly[0], actor: { login: 'secret-login', type: 'User' }, html_url: 'https://secret.example/deploy' }],
  });
  assert.equal(JSON.stringify(leaked).includes('secret'), false);
  assert.equal(toMarkdown(leaked).includes('secret'), false);

  const rehearsal = structuredClone(facts);
  rehearsal.weekly.push({
    saturday: null,
    started_at: '2026-10-18T13:13:38Z',
    completed_at: '2026-10-18T16:02:17Z',
    status: 'completed',
    conclusion: 'failure',
    event: 'workflow_dispatch',
    actor: 'human',
    branch: 'main',
    collected: true,
    run_attempt: 1,
  });
  assert.equal(row(buildScorecard(rehearsal), '2026-10-17').attempts.length, 1);
});

test('10 Oct fails on Saturday and a person recovers it on Monday', () => {
  const facts = load('week-2026-10-10');
  const week = row(buildScorecard(facts), '2026-10-10');
  assert.equal(week.human, true);
  assert.equal(week.on_time, false);
  assert.equal(week.ok, false);
  assert.equal(week.attempts[0].started_at, '2026-10-10T12:41:50Z');
  assert.equal(week.attempts[1].completed_at, '2026-10-12T14:03:27Z');
  assert.equal(week.deploy.started_at, '2026-10-12T14:27:59Z');
  assert.equal(week.deploy_end, '2026-10-12T14:51:59Z');
  assert.equal(week.deploy_failure.completed_at, '2026-10-12T14:11:27Z');
  const text = toMarkdown(buildScorecard(facts));
  for (const token of ['12:41 failure', '10-12 10:50 success', '10-12 14:03', '14:27→14:51']) {
    assert.match(text, new RegExp(token));
  }

  const mondayMorning = structuredClone(facts);
  mondayMorning.weekly[1].completed_at = '2026-10-12T11:00:00Z';
  mondayMorning.deploys = [{
    ...facts.deploys[2],
    started_at: '2026-10-12T11:00:01Z',
    completed_at: '2026-10-12T11:05:00Z',
    event: 'workflow_run',
  }];
  assert.equal(row(buildScorecard(mondayMorning), '2026-10-10').on_time, false);

  const clock = structuredClone(facts);
  clock.weekly[1].event = 'schedule';
  clock.deploys[2].event = 'workflow_run';
  assert.equal(row(buildScorecard(clock), '2026-10-10').human, false);

  const pushed = structuredClone(facts);
  pushed.weekly[1].actor = 'bot';
  assert.equal(row(buildScorecard(pushed), '2026-10-10').human, true);

  assert.equal(releaseSaturday('weekly-snapshot', '2026-10-13T23:59:00Z'), '2026-10-10');
  assert.equal(releaseSaturday('weekly-snapshot', '2026-10-14T00:00:00Z'), null);
  assert.equal(releaseSaturday('weekly rehearsal 2026-10-24', '2026-10-21T02:17:00Z'), null);
  assert.equal(releaseSaturday('weekly release resolve-date', '2026-10-24T06:17:00Z'), null);
  assert.equal(releaseSaturday('weekly release 2026-10-24', '2026-10-21T02:17:00Z'), '2026-10-24');
});

test('03 Oct fails in eight minutes, then three manual failures, then a Sunday success', () => {
  const facts = load('week-2026-10-03');
  const week = row(buildScorecard(facts), '2026-10-03');
  assert.equal(week.human, true);
  assert.equal(week.on_time, false);
  const first = week.attempts[0];
  const minutes = (Date.parse(first.completed_at) - Date.parse(first.started_at)) / 60000;
  assert.ok(minutes > 7 && minutes < 9);
  assert.equal(week.attempts.filter(attempt => attempt.event === 'workflow_dispatch' && attempt.conclusion === 'failure').length, 3);
  assert.equal(week.attempts.at(-1).started_at, '2026-10-04T01:55:45Z');
  assert.equal(week.capture_end, '2026-10-04T03:10:33Z');

  const clockRetries = structuredClone(facts);
  for (const attempt of clockRetries.weekly) {
    attempt.event = 'schedule';
    attempt.actor = 'human';
  }
  clockRetries.deploys[1].event = 'workflow_run';
  clockRetries.deploys[1].actor = 'bot';
  assert.equal(row(buildScorecard(clockRetries), '2026-10-03').human, false);
  clockRetries.edits = { '2026-10-03': [{ at: '2026-10-03T18:00:00Z', actor: 'human' }] };
  assert.equal(row(buildScorecard(clockRetries), '2026-10-03').human, true);
  clockRetries.edits = { '2026-10-03': [{ at: '2026-10-03T18:00:00Z', actor: 'bot' }] };
  assert.equal(row(buildScorecard(clockRetries), '2026-10-03').human, false);
});

test('four unattended Saturdays from 24 Oct score 4 of 4, and a miss on the third resets', () => {
  const four = buildScorecard(load('streak-four'));
  assert.equal(four.score, '4 из 4');
  assert.equal(four.rows.filter(item => item.ok).length, 4);

  const withEarly = load('streak-four');
  withEarly.weekly.unshift({
    ...withEarly.weekly[0],
    saturday: '2026-10-17',
    started_at: '2026-10-17T10:00:00Z',
    completed_at: '2026-10-17T11:00:00Z',
  });
  withEarly.deploys.unshift({
    ...withEarly.deploys[0],
    started_at: '2026-10-17T11:00:01Z',
    completed_at: '2026-10-17T11:10:00Z',
  });
  withEarly.statuses['2026-10-17'] = withEarly.statuses['2026-10-24'].map(status => ({
    ...status, updated_at: '2026-10-17T11:00:00Z',
  }));
  assert.equal(buildScorecard(withEarly).score, '4 из 4');

  const clockKey = load('streak-four');
  clockKey.weekly.forEach(run => { run.actor = 'human'; }); // the clock dispatches with the steward's key
  assert.equal(buildScorecard(clockKey).score, '4 из 4');

  const humanWeek = load('streak-four');
  humanWeek.weekly[1].actor = 'human';
  humanWeek.weekly[1].started_at = '2026-10-31T09:30:00Z'; // a hand dispatch outside every clock tick
  assert.equal(buildScorecard(humanWeek).score, '2 из 4');

  const lateReceipt = load('streak-four');
  lateReceipt.statuses['2026-10-24'].find(status => status.context === 'evidaxis/release-hf').updated_at = '2026-10-24T12:00:00Z';
  assert.equal(row(buildScorecard(lateReceipt), '2026-10-24').on_time, false);
  assert.notEqual(buildScorecard(lateReceipt).score, '4 из 4');

  const reset = load('streak-reset');
  assert.equal(buildScorecard(reset).score, '1 из 4');
  assert.equal(buildScorecard({ ...reset, now: '2026-11-07T18:00:00Z' }).score, '0 из 4');

  const open = load('streak-four');
  open.now = '2026-10-31T09:00:00Z';
  open.weekly = open.weekly.filter(attempt => attempt.saturday === '2026-10-24');
  open.deploys = open.deploys.filter(attempt => attempt.started_at.startsWith('2026-10-24'));
  open.statuses = { '2026-10-24': open.statuses['2026-10-24'] };
  assert.equal(buildScorecard(open).score, '1 из 4');

  assert.equal(snapshotSkipped({ jobs: [{ name: 'snapshot', conclusion: 'skipped', steps: [] }] }), true);
  assert.equal(snapshotSkipped({ jobs: [{ name: 'snapshot', conclusion: 'success', steps: [
    { name: 'Collect snapshot (keyed OpenAlex; capture pass + completeness gate)', conclusion: 'skipped' },
  ] }] }), true);
  assert.equal(snapshotSkipped({ jobs: [{ name: 'snapshot', conclusion: 'success', steps: [
    { name: 'Collect snapshot (keyed OpenAlex; capture pass + completeness gate)', conclusion: 'success' },
  ] }] }), false);
});

function cleanWeek(saturday, deploy = {}) {
  return {
    weekly: {
      saturday,
      started_at: `${saturday}T02:17:00Z`,
      completed_at: `${saturday}T11:00:00Z`,
      status: 'completed',
      conclusion: 'success',
      event: 'workflow_dispatch',
      actor: 'bot',
      branch: 'main',
      collected: true,
      run_attempt: 1,
    },
    deploy: {
      started_at: `${saturday}T11:00:01Z`,
      completed_at: `${saturday}T11:10:00Z`,
      status: 'completed',
      conclusion: 'success',
      event: 'workflow_run',
      actor: 'bot',
      branch: 'main',
      ...deploy,
    },
    statuses: ['captured', 'deployed', 'hf'].map(stage => ({
      context: `evidaxis/release-${stage}`,
      state: 'success',
      updated_at: `${saturday}T11:00:00Z`,
    })),
  };
}

function releaseFacts(weeks, extra = {}) {
  const weekly = [];
  const deploys = [];
  const statuses = {};
  for (const week of weeks) {
    weekly.push(week.weekly);
    deploys.push(week.deploy);
    statuses[week.weekly.saturday] = week.statuses;
  }
  return {
    now: `${weeks.at(-1).weekly.saturday}T18:00:00Z`,
    weekly,
    deploys,
    statuses,
    edits: {},
    ...extra,
  };
}

test('a human-launched deploy is a person and the clean series stays at 0', () => {
  const card = buildScorecard(releaseFacts([
    cleanWeek('2026-10-24', { event: 'workflow_dispatch', actor: 'human' }),
  ]));
  assert.equal(saturdayKind(row(card, '2026-10-24')), 'человек');
  assert.equal(card.series, '0 из 4 подряд чисто');
  assert.equal(card.claim.includes('починено'), false);
});

test('a repair-app deploy is not clean, and the series does not grow', () => {
  REPAIR_ACTORS.push('repair-app[bot]');
  try {
    const prior = buildScorecard(releaseFacts([
      cleanWeek('2026-11-07'),
      cleanWeek('2026-11-14'),
    ]));
    assert.equal(prior.series, '2 из 4 подряд чисто');
    const repaired = buildScorecard(releaseFacts([
      cleanWeek('2026-11-07'),
      cleanWeek('2026-11-14', {
        event: 'workflow_dispatch',
        actor: { type: 'Bot', login: 'repair-app[bot]' },
      }),
    ]));
    assert.equal(saturdayKind(row(repaired, '2026-11-14')), 'авторемонт');
    assert.equal(repaired.series, '0 из 4 подряд чисто');
    assert.equal(JSON.stringify(repaired).includes('repair-app'), false);
    const stranger = buildScorecard(releaseFacts([
      cleanWeek('2026-11-14', { actor: { type: 'Bot', login: 'not-the-repair-app' } }),
    ]));
    assert.equal(saturdayKind(row(stranger, '2026-11-14')), 'чисто');
    assert.equal(JSON.stringify(stranger).includes('not-the-repair-app'), false);
    const viaPr = buildScorecard(releaseFacts([cleanWeek('2026-11-14')], {
      repairPrs: { '2026-11-14': [{ labels: ['auto-repair'], merged_at: '2026-11-16T12:00:00Z' }] },
    }));
    assert.equal(saturdayKind(row(viaPr, '2026-11-14')), 'авторемонт');
    assert.equal(viaPr.series, '0 из 4 подряд чисто');
  } finally {
    REPAIR_ACTORS.length = 0;
  }
});

test('four clean Saturdays can be claimed only when every class is closed', () => {
  const allClosed = [
    { class: 'масштаб и лимиты сбора', first_seen: '2026-09-26', closed_by: 'drill' },
    { class: 'лицензионная карта', first_seen: '2026-09-24', closed_by: 'pr-check' },
  ];
  const claimed = buildScorecard(load('streak-four'), { classes: allClosed });
  assert.equal(claimed.series, '4 из 4 подряд чисто');
  assert.equal(claimed.claim, 'можно говорить: «четыре субботы подряд вышли сами вовремя»');
  const text = toMarkdown(claimed);
  assert.equal(text.endsWith(claimed.claim), true);
  assert.equal(text.includes('починено'), false);
  for (const row of claimed.rows.filter(item => item.saturday >= '2026-10-24')) {
    assert.equal(saturdayKind(row), 'чисто');
  }

  const oneOpen = [
    { class: 'масштаб и лимиты сбора', first_seen: '2026-09-26', closed_by: 'drill' },
    { class: 'страж по слову на масштабе', first_seen: '2026-09-26', closed_by: 'none' },
  ];
  const held = buildScorecard(load('streak-four'), { classes: oneOpen });
  assert.equal(held.series, '4 из 4 подряд чисто');
  assert.equal(held.claim.includes('четыре субботы подряд вышли сами вовремя'), false);
  assert.equal(held.claim, 'можно говорить: «4 из 4 подряд; классов закрыто 1 из 2»');
  assert.equal(toMarkdown(held).includes('починено'), false);

  const seeded = buildScorecard(load('streak-four'));
  assert.equal(seeded.classesClosed, 5);
  assert.equal(seeded.classesTotal, 10);
  assert.equal(seeded.score, '4 из 4');
  assert.equal(seeded.claim.includes('четыре субботы подряд вышли сами вовремя'), false);

  const history = buildScorecard(load('streak-four'));
  assert.equal(toMarkdown(history).startsWith('4 из 4\n'), true);
  assert.ok(history.rows.some(item => item.saturday === '2026-08-29'));
  const rolled = buildScorecard(load('streak-four'), { since: '2026-11-07' });
  assert.deepEqual(rolled.rows.map(item => item.saturday), ['2026-11-07', '2026-11-14']);
  assert.equal(rolled.series, '2 из 4 подряд чисто');
  assert.equal(rolled.score, '4 из 4');
  assert.equal(toMarkdown(rolled).startsWith('2 из 4 подряд чисто\n'), true);
  assert.throws(() => buildScorecard(load('streak-four'), { since: '2026-02-31' }), /Invalid --since/);
  assert.throws(
    () => buildScorecard(load('streak-four'), { since: '2026-08-28' }),
    /--since must be on or after 2026-08-29/,
  );
  assert.equal(buildScorecard(load('streak-four'), { since: '2026-08-29' }).rows[0].saturday, '2026-08-29');
});

test('a clean Saturday that already published before noon stays in the series', () => {
  const early = load('streak-four');
  early.now = '2026-11-14T11:59:59Z';
  const card = buildScorecard(early);
  assert.equal(saturdayKind(row(card, '2026-11-14')), 'чисто');
  assert.equal(card.series, '4 из 4 подряд чисто');

  const unfinished = load('streak-four');
  unfinished.now = '2026-11-14T11:59:59Z';
  unfinished.weekly = unfinished.weekly.filter(attempt => attempt.saturday !== '2026-11-14');
  unfinished.deploys = unfinished.deploys.filter(attempt => !attempt.started_at.startsWith('2026-11-14'));
  unfinished.statuses['2026-11-14'] = [];
  assert.equal(buildScorecard(unfinished).series, '3 из 4 подряд чисто');

  const failed = load('streak-four');
  failed.now = '2026-11-14T11:59:59Z';
  failed.weekly = failed.weekly.filter(attempt => attempt.saturday !== '2026-11-14');
  failed.deploys = failed.deploys.filter(attempt => !attempt.started_at.startsWith('2026-11-14'));
  failed.statuses['2026-11-14'] = [];
  failed.weekly.push({
    saturday: '2026-11-14',
    started_at: '2026-11-14T02:17:00Z',
    completed_at: '2026-11-14T02:25:00Z',
    status: 'completed',
    conclusion: 'failure',
    event: 'workflow_dispatch',
    actor: 'bot',
    branch: 'main',
    collected: true,
    run_attempt: 1,
  });
  assert.equal(buildScorecard(failed).series, '0 из 4 подряд чисто');
});

test('an unmerged auto-repair pull request does not mark the Saturday', () => {
  const open = load('streak-four');
  open.repairPrs = { '2026-11-14': [{ labels: ['auto-repair'], state: 'open', merged_at: null }] };
  const card = buildScorecard(open);
  assert.equal(saturdayKind(row(card, '2026-11-14')), 'чисто');
  assert.equal(card.series, '4 из 4 подряд чисто');

  const closed = load('streak-four');
  closed.repairPrs = { '2026-11-14': [{ labels: ['auto-repair'], state: 'closed', merged_at: null }] };
  assert.equal(saturdayKind(row(buildScorecard(closed), '2026-11-14')), 'чисто');

  const afterTuesday = load('streak-four');
  afterTuesday.repairPrs = {
    '2026-11-14': [{ labels: ['auto-repair'], state: 'closed', merged_at: '2026-11-18T00:00:00Z' }],
  };
  assert.equal(saturdayKind(row(buildScorecard(afterTuesday), '2026-11-14')), 'чисто');

  const onTuesday = load('streak-four');
  onTuesday.repairPrs = {
    '2026-11-14': [{ labels: [{ name: 'auto-repair' }], state: 'closed', merged_at: '2026-11-17T23:59:59Z' }],
  };
  assert.equal(saturdayKind(row(buildScorecard(onTuesday), '2026-11-14')), 'авторемонт');
  assert.equal(buildScorecard(onTuesday).series, '0 из 4 подряд чисто');
});

test('a dispatch inside a clock tick window is the clock, not a person', async () => {
  const { clockTicks, clockDispatch } = await import('./release-scorecard.mjs');
  const { readFileSync } = await import('node:fs');
  const list = clockTicks(readFileSync(new URL('../infra/clock/wrangler.toml', import.meta.url), 'utf8'));
  assert.deepEqual(list.map(t => `${t.day} ${t.hour}:${t.min}`), ['SAT 2:17', 'SAT 4:17', 'SAT 6:47', 'WED 2:17', 'FRI 2:17']);
  assert.equal(clockDispatch('2026-10-24T02:19:05Z', list), true);
  assert.equal(clockDispatch('2026-10-24T06:50:00Z', list), true);
  assert.equal(clockDispatch('2026-10-24T03:30:00Z', list), false);
  assert.equal(clockDispatch('2026-10-22T02:19:00Z', list), false);
  assert.equal(clockDispatch('2026-10-21T02:20:00Z', list), true);
  assert.equal(clockDispatch('2026-11-13T02:19:00Z', list), true);
});
