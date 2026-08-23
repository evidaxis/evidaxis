import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  evaluateArchiveFreshness,
  evaluateFeedFreshness,
  evaluateFreshness,
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

test('archive snapshot younger than the capture budget is fresh', () => {
  const r = evaluateArchiveFreshness({
    snapshotDate: '2026-08-15',
    nowIso: '2026-08-22T06:16:59Z',
  });
  assert.equal(r.status, 'ok');
  assert.equal(r.alert, false);
});

test('archive snapshot older than the capture budget alerts', () => {
  const r = evaluateArchiveFreshness({
    snapshotDate: '2026-08-15',
    nowIso: '2026-08-22T12:17:01Z',
  });
  assert.equal(r.status, 'stale');
  assert.equal(r.alert, true);
  assert.match(r.message, /CAPTURE не состоялся/);
  assert.match(r.message, /174 ч \(7\.3 дн\.\)/);
});

test('archive age exactly at the budget boundary is fresh', () => {
  const r = evaluateArchiveFreshness({
    snapshotDate: '2026-08-15',
    nowIso: '2026-08-22T12:17:00Z',
  });
  assert.equal(r.status, 'ok');
  assert.equal(r.alert, false);
});

test('malformed archive snapshot date alerts fail-closed', () => {
  const r = evaluateArchiveFreshness({
    snapshotDate: '2026-02-30',
    nowIso: '2026-08-22T12:17:00Z',
  });
  assert.equal(r.status, 'stale');
  assert.equal(r.alert, true);
});
