import { test } from 'node:test';
import assert from 'node:assert/strict';
import { inReminderWindow, shouldPush } from './alert-gate.mjs';

test('a new problem (previous run green) is pushed at once', () => {
  assert.equal(shouldPush({ previousConclusion: 'success', nowIso: '2026-09-26T14:00:00Z' }), true);
});

test('unknown previous outcome fails closed: push', () => {
  assert.equal(shouldPush({ previousConclusion: null, nowIso: '2026-09-26T14:00:00Z' }), true);
});

test('the same problem (previous run red) stays quiet outside the morning window', () => {
  assert.equal(shouldPush({ previousConclusion: 'failure', nowIso: '2026-09-26T14:00:00Z' }), false);
  assert.equal(shouldPush({ previousConclusion: 'failure', nowIso: '2026-09-26T06:30:00Z' }), false);
});

test('the same problem repeats once a day in the morning window', () => {
  assert.equal(shouldPush({ previousConclusion: 'failure', nowIso: '2026-09-26T06:00:00Z' }), true);
  assert.equal(shouldPush({ previousConclusion: 'failure', nowIso: '2026-09-26T06:23:00Z' }), true);
});

test('a 30-minute cron gets exactly one reminder slot a day', () => {
  let slots = 0;
  for (let m = 0; m < 24 * 60; m += 30) {
    const iso = new Date(Date.UTC(2026, 8, 26, 0, m)).toISOString();
    if (inReminderWindow(iso)) slots += 1;
  }
  assert.equal(slots, 1);
});
