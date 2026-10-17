import test from 'node:test';
import assert from 'node:assert/strict';
import { tick, findRuns, needsDispatch } from './logic.mjs';
import { runTick } from './worker.js';

const release = { mode: 'release', release_date: '2026-10-24' };
const run = { id: 1, display_title: 'weekly release 2026-10-24', head_branch: 'main', status: 'queued', conclusion: null };
const controller = { cron: '17 2 * * SAT', scheduledTime: Date.parse('2026-10-24T02:17:00Z') };
const env = { GH_DISPATCH_TOKEN: 'test-token', GH_REPOSITORY: 'evidaxis/evidaxis', GH_REF: 'main' };

test('all Saturday ticks keep the scheduled UTC date; Wednesday targets next Saturday', () => {
  for (const cron of ['17 2 * * SAT', '17 4 * * SAT', '47 6 * * SAT']) {
    assert.deepEqual(tick(cron, controller.scheduledTime), release);
  }
  assert.deepEqual(tick('17 2 * * WED', Date.parse('2026-12-30T02:17:00Z')),
    { mode: 'rehearsal', release_date: '2027-01-02' });
  assert.throws(() => tick('unknown', controller.scheduledTime));
  assert.throws(() => tick('17 2 * * WED', controller.scheduledTime));
});

test('matching uses exact date, mode and branch', () => {
  const runs = [run, { ...run, head_branch: 'test' }, { ...run, display_title: 'weekly rehearsal 2026-10-24' },
    { ...run, display_title: 'weekly release 2026-10-17' }];
  assert.deepEqual(findRuns(runs, release, 'main'), [run]);
  assert.equal(needsDispatch(runs.slice(1), release, 'main'), true);
});

test('active and successful runs block dispatch; terminal failures permit retry', () => {
  for (const status of ['queued', 'in_progress', 'pending', 'waiting', 'requested']) {
    assert.equal(needsDispatch([{ ...run, status }], release, 'main'), false);
  }
  assert.equal(needsDispatch([{ ...run, status: 'completed', conclusion: 'success' }], release, 'main'), false);
  assert.equal(needsDispatch([{ ...run, status: 'completed', conclusion: 'failure' }], release, 'main'), true);
  assert.equal(needsDispatch([], release, 'main'), true);
  assert.throws(() => needsDispatch(null, release, 'main'));
});

test('API failure never dispatches blindly', async () => {
  const methods = [];
  await assert.rejects(runTick(controller, env, async (url, options) => {
    methods.push(options.method);
    return new Response('{}', { status: 503 });
  }), /HTTP 503/);
  assert.deepEqual(methods, ['GET']);
});

test('dispatch acknowledgement must be followed by a new observed run, not an old failure', async () => {
  let posts = 0;
  await assert.rejects(runTick(controller, env, async (url, options) => {
    if (options.method === 'POST') { posts++; return new Response(null, { status: 204 }); }
    return Response.json({ total_count: 1, workflow_runs: [{ ...run, status: 'completed', conclusion: 'failure' }] });
  }, async () => {}), /no new run observed/);
  assert.equal(posts, 1);
});

test('lost dispatch response is observed without a second POST', async () => {
  let posts = 0;
  await runTick(controller, env, async (url, options) => {
    if (options.method === 'POST') { posts++; throw new Error('response lost'); }
    return Response.json({ total_count: posts, workflow_runs: posts ? [run] : [] });
  }, async () => {});
  assert.equal(posts, 1);
});

test('pagination finds a queued run beyond the first page', async () => {
  let calls = 0;
  await runTick(controller, env, async (url, options) => {
    assert.equal(options.method, 'GET');
    calls++;
    return Response.json({ total_count: 2, workflow_runs: new URL(url).searchParams.get('page') === '1'
      ? [{ ...run, display_title: 'weekly release 2026-10-17' }] : [run] });
  });
  assert.equal(calls, 2);
});

test('a manual rehearsal before Wednesday still prevents another dispatch', async () => {
  let posts = 0;
  const earlier = { ...run, display_title: 'weekly rehearsal 2026-10-24',
    created_at: '2026-10-19T02:17:00Z', status: 'completed', conclusion: 'success' };
  await runTick({ cron: '17 2 * * WED', scheduledTime: Date.parse('2026-10-21T02:17:00Z') }, env,
    async (url, options) => {
      if (options.method === 'POST') { posts++; return new Response(null, { status: 204 }); }
      const since = new URL(url).searchParams.get('created')?.replace('>=', '');
      const found = !since || Date.parse(earlier.created_at) >= Date.parse(since);
      return Response.json({ total_count: found ? 1 : 0, workflow_runs: found ? [earlier] : [] });
    }, async () => {});
  assert.equal(posts, 0);
});
