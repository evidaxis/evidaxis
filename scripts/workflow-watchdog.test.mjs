import { test } from 'node:test';
import assert from 'node:assert/strict';
import { evaluateWorkflowHealth } from './workflow-watchdog.mjs';

const actionsUrl = 'https://github.com/evidaxis/evidaxis/actions';
const nowIso = '2026-08-23T12:00:00Z';
const scheduled = [{ name: 'weekly-snapshot', kind: 'scheduled', budgetHours: 204 }];

test('red latest run alerts and keeps the actions link at the end', () => {
  const [result] = evaluateWorkflowHealth({
    roster: scheduled,
    latestCompleted: {
      'weekly-snapshot': { conclusion: 'failure', created_at: '2026-08-23T06:00:00Z' },
    },
    latestSuccess: {
      'weekly-snapshot': { conclusion: 'success', created_at: '2026-08-16T06:00:00Z' },
    },
    nowIso,
  });
  assert.equal(result.status, 'red');
  assert.equal(result.alert, true);
  assert.ok(result.message.endsWith(actionsUrl));
});

test('scheduled workflow alerts when the latest success exceeds its budget', () => {
  const [result] = evaluateWorkflowHealth({
    roster: scheduled,
    latestCompleted: {
      'weekly-snapshot': { conclusion: 'success', created_at: '2026-08-23T06:00:00Z' },
    },
    latestSuccess: {
      'weekly-snapshot': { conclusion: 'success', created_at: '2026-08-14T23:59:59Z' },
    },
    nowIso,
  });
  assert.equal(result.status, 'stale');
  assert.equal(result.alert, true);
});

test('recent successful scheduled workflow is quiet', () => {
  const [result] = evaluateWorkflowHealth({
    roster: scheduled,
    latestCompleted: {
      'weekly-snapshot': { conclusion: 'success', created_at: '2026-08-23T06:00:00Z' },
    },
    latestSuccess: {
      'weekly-snapshot': { conclusion: 'success', created_at: '2026-08-23T06:00:00Z' },
    },
    nowIso,
  });
  assert.equal(result.status, 'ok');
  assert.equal(result.alert, false);
});

test('event-driven workflow ignores the age of its latest completed run', () => {
  const [result] = evaluateWorkflowHealth({
    roster: [{ name: 'deploy-web', kind: 'event' }],
    latestCompleted: {
      'deploy-web': { conclusion: 'success', created_at: '2025-01-01T00:00:00Z' },
    },
    latestSuccess: {},
    nowIso,
  });
  assert.equal(result.status, 'ok');
  assert.equal(result.alert, false);
});

test('roster entry without a completed run fails closed', () => {
  const [result] = evaluateWorkflowHealth({
    roster: [{ name: 'unseen-schedule', kind: 'scheduled', budgetHours: 36 }],
    latestCompleted: {},
    latestSuccess: {},
    nowIso,
  });
  assert.equal(result.status, 'missing');
  assert.equal(result.alert, true);
  assert.match(result.message, /воркфлоу вне надзора/);
});
