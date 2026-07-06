import { test } from 'node:test';
import assert from 'node:assert/strict';
import { evaluateLiveness } from './liveness.mjs';

const base = { url: 'https://site', marker: 'MARK' };

test('200 + marker → ok, no alert', () => {
  const r = evaluateLiveness({ ...base, reached: true, status: 200, hasMarker: true });
  assert.equal(r.status, 'ok');
  assert.equal(r.alert, false);
});

test('200 but marker missing → degraded, ALERT', () => {
  const r = evaluateLiveness({ ...base, reached: true, status: 200, hasMarker: false });
  assert.equal(r.status, 'degraded');
  assert.equal(r.alert, true);
});

test('non-200 (503) → down, ALERT', () => {
  const r = evaluateLiveness({ ...base, reached: true, status: 503, hasMarker: false });
  assert.equal(r.status, 'down');
  assert.equal(r.alert, true);
});

test('unreachable (no response) → down, ALERT', () => {
  const r = evaluateLiveness({ ...base, reached: false, status: 0, hasMarker: false });
  assert.equal(r.status, 'down');
  assert.equal(r.alert, true);
});
