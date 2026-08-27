import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  applyDroughtGate,
  applyFactGates,
  evaluateWorkflowHealth,
} from './workflow-watchdog.mjs';

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

// --- Gate 1: the watchdog never judges itself by its own outcome ------------
// Regression for the 2026-08-27 latch: an alert exits non-zero → the run is red →
// the next run reads its own red as a failure → alerts → exits non-zero. The only
// escape (a green run) required the previous run to be green already.

const selfRoster = [{ name: 'workflow-watchdog', kind: 'scheduled', budgetHours: 13, self: true }];

test('the watchdog stays quiet about its own red run (no self-latch)', () => {
  const [result] = evaluateWorkflowHealth({
    roster: selfRoster,
    latestCompleted: {
      'workflow-watchdog': { conclusion: 'failure', created_at: '2026-08-23T06:00:00Z' },
    },
    latestSuccess: {
      'workflow-watchdog': { conclusion: 'success', created_at: '2026-08-23T00:00:00Z' },
    },
    nowIso,
  });
  assert.equal(result.alert, false);
  assert.equal(result.quiet, 'self');
});

test('the watchdog stays quiet about its own missed cron slots', () => {
  const [result] = evaluateWorkflowHealth({
    roster: selfRoster,
    latestCompleted: {
      'workflow-watchdog': { conclusion: 'success', created_at: '2026-08-22T06:00:00Z' },
    },
    latestSuccess: {
      'workflow-watchdog': { conclusion: 'success', created_at: '2026-08-22T06:00:00Z' },
    },
    nowIso,
  });
  assert.equal(result.alert, false);
  assert.equal(result.quiet, 'self');
});

test('a red run of a NON-self workflow still alerts', () => {
  const [result] = evaluateWorkflowHealth({
    roster: [{ name: 'liveness-check', kind: 'scheduled', budgetHours: 3 }],
    latestCompleted: {
      'liveness-check': { conclusion: 'failure', created_at: '2026-08-23T11:00:00Z' },
    },
    latestSuccess: {
      'liveness-check': { conclusion: 'success', created_at: '2026-08-23T10:00:00Z' },
    },
    nowIso,
  });
  assert.equal(result.status, 'red');
  assert.equal(result.alert, true);
});

// --- Gate 2: alert on the fact, not on the sensor's schedule ----------------

const staleLiveness = [
  {
    name: 'liveness-check',
    kind: 'scheduled',
    status: 'stale',
    alert: true,
    factGate: 'site',
    budgetHours: 3,
    message: 'liveness-check: просрочен.',
  },
];

test('a stale sensor goes quiet when the site itself is verified up', () => {
  const [result] = applyFactGates(staleLiveness, {
    'liveness-check': { ok: true, detail: 'https://evidaxis.org жив (200 + контент-маркер).' },
  });
  assert.equal(result.alert, false);
  assert.equal(result.quiet, 'fact-ok');
  assert.equal(result.factVerdict, 'ok');
});

test('a stale sensor stays loud when the site is actually down', () => {
  const [result] = applyFactGates(staleLiveness, {
    'liveness-check': { ok: false, detail: 'https://evidaxis.org отдаёт HTTP 503.' },
  });
  assert.equal(result.alert, true);
  assert.equal(result.factVerdict, 'bad');
  assert.match(result.message, /HTTP 503/);
});

test('an unobtainable fact keeps the alert loud (fail closed)', () => {
  const [result] = applyFactGates(staleLiveness, {});
  assert.equal(result.alert, true);
  assert.equal(result.factVerdict, 'unknown');
});

// --- Gate 3: a repo-wide cron drought is one platform line ------------------

const droughtRoster = [
  { name: 'liveness-check', kind: 'scheduled', budgetHours: 3 },
  { name: 't2-daily-snapshot', kind: 'scheduled', budgetHours: 36, dataLoss: true },
  { name: 'workflow-watchdog', kind: 'scheduled', budgetHours: 13, self: true },
];

const droughtRows = [
  {
    name: 'liveness-check',
    kind: 'scheduled',
    status: 'stale',
    alert: true,
    budgetHours: 3,
    message: 'liveness-check: просрочен.',
  },
];

test('drought quiets schedule-only staleness and adds one platform line', () => {
  const results = applyDroughtGate(droughtRows, {
    roster: droughtRoster,
    latestAnyRun: {
      'liveness-check': { created_at: '2026-08-23T02:30:00Z' },
      't2-daily-snapshot': { created_at: '2026-08-23T00:10:00Z' },
      'workflow-watchdog': { created_at: '2026-08-23T11:59:00Z' },
    },
    nowIso,
  });
  const liveness = results.find((r) => r.name === 'liveness-check');
  const platform = results.find((r) => r.name === 'github-scheduler');
  assert.equal(liveness.alert, false);
  assert.equal(liveness.quiet, 'drought');
  assert.equal(platform.status, 'drought');
  assert.equal(platform.alert, false, 'a quiet drought never wakes anyone on its own');
  assert.equal(platform.droughtSince, '2026-08-23T02:30:00.000Z');
});

test('drought never quiets a workflow whose miss costs un-backfillable capture', () => {
  const rows = [
    ...droughtRows,
    {
      name: 't2-daily-snapshot',
      kind: 'scheduled',
      status: 'stale',
      alert: true,
      budgetHours: 36,
      dataLoss: true,
      message: 't2-daily-snapshot: просрочен.',
    },
  ];
  const results = applyDroughtGate(rows, {
    roster: droughtRoster,
    latestAnyRun: {
      'liveness-check': { created_at: '2026-08-21T02:30:00Z' },
      't2-daily-snapshot': { created_at: '2026-08-21T00:10:00Z' },
    },
    nowIso,
  });
  const capture = results.find((r) => r.name === 't2-daily-snapshot');
  const platform = results.find((r) => r.name === 'github-scheduler');
  assert.equal(capture.alert, true);
  assert.equal(platform.alert, true, 'the platform line rides along with a real alarm');
});

test('drought never quiets a row whose fact check came back bad', () => {
  const rows = [{ ...droughtRows[0], factGate: 'site', factVerdict: 'bad' }];
  const results = applyDroughtGate(rows, {
    roster: droughtRoster,
    latestAnyRun: { 'liveness-check': { created_at: '2026-08-23T02:30:00Z' } },
    nowIso,
  });
  assert.equal(results.find((r) => r.name === 'liveness-check').alert, true);
});

test('one stale workflow while the scheduler keeps dispatching is NOT a drought', () => {
  const results = applyDroughtGate(droughtRows, {
    roster: droughtRoster,
    latestAnyRun: {
      'liveness-check': { created_at: '2026-08-23T02:30:00Z' },
      't2-daily-snapshot': { created_at: '2026-08-23T11:40:00Z' },
    },
    nowIso,
  });
  assert.equal(results.length, 1, 'no platform line');
  assert.equal(results[0].alert, true);
});
