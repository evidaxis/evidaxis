import { test } from 'node:test';
import assert from 'node:assert/strict';
import { alertStepSent, ciAlertText, decideAlert, pickPrevious } from './ci-alert.mjs';

const runUrl = 'https://github.com/evidaxis/evidaxis/actions/runs/99';
const step = 'Verify web publication (tests, build, dist, Card B, badges)';

test('a green previous run on main sends the transition at once', () => {
  assert.deepEqual(
    decideAlert({ conclusion: 'success', completed_at: '2026-10-24T01:00:00Z' }, '2026-10-24T18:00:00Z'),
    { send: true, kind: 'transition' },
  );
});

test('an unknown previous run sends, so the first red day is not silent', () => {
  assert.equal(decideAlert(null, '2026-10-24T18:00:00Z').send, true);
  assert.equal(decideAlert({ conclusion: 'cancelled', completed_at: '2026-10-24T18:00:00Z' }, '2026-10-24T19:00:00Z').kind, 'unknown');
});

test('a check that stays red sends at most one reminder per UTC day', () => {
  const sameDay = decideAlert(
    { conclusion: 'failure', completed_at: '2026-10-24T23:50:00Z', alertSent: true },
    '2026-10-24T23:59:00Z',
  );
  assert.deepEqual(sameDay, { send: false, kind: 'quiet' });
  const nextDay = decideAlert(
    { conclusion: 'timed_out', completed_at: '2026-10-24T23:50:00Z', alertSent: true },
    '2026-10-25T00:01:00Z',
  );
  assert.deepEqual(nextDay, { send: true, kind: 'reminder' });
  assert.equal(
    decideAlert({ conclusion: 'failure', completed_at: '', alertSent: true }, '2026-10-25T00:01:00Z').send,
    true,
  );
});

test('the keeper line names the failed step and the run, in Russian', () => {
  const transition = ciAlertText({ workflow: 'web-ci', step, runUrl, kind: 'transition' });
  assert.equal(
    transition,
    `Проверка web-ci на main упала на шаге «${step}». ${runUrl}`,
  );
  const reminder = ciAlertText({ workflow: 'python-ci', step, runUrl, kind: 'reminder' });
  assert.equal(reminder.includes('Напоминание за этот день'), true);
  assert.equal(reminder.includes(step), true);
  assert.equal(reminder.includes(runUrl), true);
  for (const host of ['vercel.com', 'huggingface.co', 'evidaxis.org', 'zenodo.org']) {
    assert.equal(transition.includes(host), false, host);
    assert.equal(reminder.includes(host), false, host);
  }
});

test('pickPrevious skips the current run and keeps the latest completion', () => {
  const previous = pickPrevious([{ id: 7, conclusion: 'failure' }, { id: 6, conclusion: 'success' }], '7');
  assert.equal(previous.id, 6);
  assert.equal(pickPrevious([{ id: 7 }], 7), null);
  const latest = pickPrevious([
    { id: 5, conclusion: 'success', updated_at: '2026-10-24T01:00:00Z' },
    { id: 9, conclusion: 'failure', updated_at: '2026-10-24T18:00:00Z' },
    { id: 8, conclusion: 'failure', updated_at: '2026-10-25T03:00:00Z' },
  ], '8');
  assert.equal(latest.id, 9);
});

test('a failed send does not silence the next red run the same UTC day', () => {
  const decision = decideAlert(
    { conclusion: 'failure', completed_at: '2026-10-24T12:00:00Z', alertSent: false },
    '2026-10-24T18:00:00Z',
  );
  assert.equal(decision.send, true);
  const afterDelivery = decideAlert([
    { conclusion: 'failure', completed_at: '2026-10-24T16:00:00Z', alertSent: false },
    { conclusion: 'failure', completed_at: '2026-10-24T12:00:00Z', alertSent: true },
  ], '2026-10-24T18:00:00Z');
  assert.equal(afterDelivery.send, false);
  assert.equal(alertStepSent({
    jobs: [{ steps: [{ name: 'Tell the keeper the check went red', conclusion: 'failure' }] }],
  }), false);
  assert.equal(alertStepSent({
    jobs: [{ steps: [{ name: 'Tell the keeper the automatic replay failed', conclusion: 'success' }] }],
  }), true);
});

test('a rerun stays quiet when an earlier attempt of this run already delivered', () => {
  const chosen = pickPrevious([
    {
      id: 9,
      attempt: 1,
      conclusion: 'failure',
      completed_at: '2026-10-24T12:00:00Z',
      updated_at: '2026-10-24T12:00:00Z',
      alertSent: true,
    },
    {
      id: 8,
      conclusion: 'success',
      completed_at: '2026-10-24T08:00:00Z',
      updated_at: '2026-10-24T08:00:00Z',
      alertSent: false,
    },
  ], 9, 2);
  const decision = decideAlert(chosen, '2026-10-24T12:30:00Z');
  assert.equal(decision.send, false);
  assert.equal(decision.kind, 'quiet');
});

test('green to red after a delivery yesterday sends', () => {
  const decision = decideAlert([
    { conclusion: 'success', completed_at: '2026-10-25T09:00:00Z', alertSent: false },
    { conclusion: 'failure', completed_at: '2026-10-24T12:00:00Z', alertSent: true },
  ], '2026-10-25T18:00:00Z');
  assert.deepEqual(decision, { send: true, kind: 'transition' });
});

test('history is only push and workflow_run on this repository main', () => {
  const repo = 'evidaxis/evidaxis';
  const chosen = pickPrevious([
    {
      id: 4,
      event: 'pull_request',
      head_branch: 'main',
      head_repository: { full_name: 'stranger/evidaxis' },
      repository: { full_name: repo },
      conclusion: 'failure',
      updated_at: '2026-10-24T12:00:00Z',
      alertSent: true,
    },
    {
      id: 6,
      event: 'pull_request',
      head_branch: 'main',
      head_repository: { full_name: repo },
      conclusion: 'failure',
      updated_at: '2026-10-24T11:00:00Z',
      alertSent: true,
    },
    {
      id: 5,
      event: 'workflow_run',
      head_branch: 'main',
      head_repository: { full_name: repo },
      conclusion: 'success',
      updated_at: '2026-10-24T10:00:00Z',
    },
    {
      id: 3,
      event: 'push',
      head_branch: 'main',
      head_repository: { full_name: repo },
      conclusion: 'success',
      updated_at: '2026-10-24T09:00:00Z',
    },
  ], 99, 1, repo);
  assert.equal(chosen.id, 5);
  assert.equal(chosen.event, 'workflow_run');
  const decision = decideAlert(chosen, '2026-10-24T13:00:00Z');
  assert.equal(decision.send, true);
  assert.equal(decision.kind, 'transition');
});
