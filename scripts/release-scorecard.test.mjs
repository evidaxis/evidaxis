import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  actorKind,
  buildScorecard,
  releaseSaturday,
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

test('a dispatch inside a clock tick window is the clock, not a person', async () => {
  const { clockTicks, clockDispatch } = await import('./release-scorecard.mjs');
  const { readFileSync } = await import('node:fs');
  const list = clockTicks(readFileSync(new URL('../infra/clock/wrangler.toml', import.meta.url), 'utf8'));
  assert.deepEqual(list.map(t => `${t.day} ${t.hour}:${t.min}`), ['SAT 2:17', 'SAT 4:17', 'SAT 6:47', 'WED 2:17']);
  assert.equal(clockDispatch('2026-10-24T02:19:05Z', list), true);
  assert.equal(clockDispatch('2026-10-24T06:50:00Z', list), true);
  assert.equal(clockDispatch('2026-10-24T03:30:00Z', list), false);
  assert.equal(clockDispatch('2026-10-22T02:19:00Z', list), false);
  assert.equal(clockDispatch('2026-10-21T02:20:00Z', list), true);
});
