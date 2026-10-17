import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readWeeklyFacts } from './freshness-check.mjs';
import { evaluate as watchdog } from './workflow-watchdog-check.mjs';
import { readReleaseFacts, githubJson, snapshotCommit } from './release-record.mjs';
import { evaluateWeeklyRelease } from './weekly-release.mjs';
import { mirrorSnapshot, releaseTarget, stageResult, writeReleaseStatus } from './release-status.mjs';

const date = '2026-10-17';
const nowIso = `${date}T13:33:00Z`;
const sha = 'a'.repeat(40);
const older = 'b'.repeat(40);
const weekly = { id: 1, status: 'in_progress', head_branch: 'main', event: 'workflow_dispatch',
  display_title: `weekly release ${date}` };
const deploy = { ...weekly, display_title: 'deploy-web', event: 'push', head_sha: sha };
const status = (stage, state = 'success') => ({ context: `evidaxis/release-${stage}`, state,
  description: stage === 'captured' && state === 'success' ? date : `Verify ${stage}` });
const complete = [status('captured'), status('deployed'), status('hf')];
function api({ commit = sha, statuses = complete, weeklies = [], deploys = [], tree = sha, override } = {}) {
  const calls = [];
  const get = async path => {
    calls.push(path);
    if (override) {
      const value = await override(path);
      if (value !== undefined) return value;
    }
    if (path.startsWith('commits?')) {
      const ref = new URLSearchParams(path.split('?')[1]).get('sha');
      const value = ref === 'main' ? commit : tree;
      return value ? [{ sha: value }] : [];
    }
    if (path === `commits/${sha}/status?per_page=100`) return { sha, statuses, total_count: statuses.length };
    if (path.startsWith('actions/workflows/')) {
      assert.doesNotMatch(path, /attempts|jobs|completed/);
      const query = new URLSearchParams(path.split('?')[1]);
      assert.equal(query.get('per_page'), '100');
      assert.equal(query.get('branch'), 'main');
      assert.ok(['queued', 'in_progress'].includes(query.get('status')));
      const list = path.includes('weekly-snapshot') ? weeklies : deploys;
      const workflow_runs = list.filter(run => run.status === query.get('status'));
      return { workflow_runs, total_count: workflow_runs.length };
    }
    assert.fail(`Unexpected API call: ${path}`);
  };
  return { calls, get };
}
async function verdict(options, time = nowIso) {
  const mock = api(options);
  const facts = await readReleaseFacts(time, mock.get);
  return { ...mock, facts, result: evaluateWeeklyRelease(facts) };
}

test('reader locates Saturday commit and reads combined latest statuses, without history or site probes', async () => {
  const { calls, result } = await verdict({}, '2026-10-18T15:00:00Z');
  assert.equal(result.status, 'released');
  assert.deepEqual(calls, [`commits?path=data/snapshots/${date}/snapshot.json&per_page=1&sha=main`,
    `commits/${sha}/status?per_page=100`]);
});

test('17 Oct 13:33 collection in progress uses only active dated weekly identity', async () => {
  for (const activity of ['queued', 'in_progress']) {
    const { calls, result } = await verdict({ commit: null, weeklies: [{ ...weekly, status: activity }] });
    assert.equal(result.status, 'running');
    assert.equal(result.remind, false);
    assert.ok(calls.every(path => !path.includes('deploy-web') && !path.includes('/status?')));
  }
});

test('rehearsal, resolver, other date, other branch and completed skips never create activity', async () => {
  const changes = [
    { display_title: `weekly rehearsal ${date}` }, { display_title: 'weekly release resolve-date' },
    { display_title: 'weekly release 2026-10-10' }, { head_branch: 'test' },
    { event: 'pull_request' }, { status: 'completed', conclusion: 'success', run_attempt: 9 },
    { status: 'completed', conclusion: 'skipped' },
  ];
  for (const change of changes) {
    const { result } = await verdict({ commit: null, weeklies: [{ ...weekly, ...change }] });
    assert.equal(result.status, 'not_started');
  }
});

test('active API race returning a completed/skipped deployment contributes no work', async () => {
  const { result } = await verdict({ statuses: [status('captured'), status('hf')],
    override: path => path.includes('deploy-web') ? { total_count: 1,
      workflow_runs: [{ ...deploy, status: 'completed', conclusion: 'skipped' }] } : undefined });
  assert.equal(result.status, 'failed');
  assert.match(result.message, /не дошло до этапа deployed/);
  const absent = await verdict({ commit: null, deploys: [{ ...deploy, status: 'completed', conclusion: 'skipped' }] });
  assert.equal(absent.result.status, 'not_started');
});

test('publication activity is scoped to the missing stage and snapshot tree, never attempt time', async () => {
  for (const event of ['push', 'workflow_dispatch', 'workflow_run']) {
    const { result, calls } = await verdict({ statuses: [status('captured'), status('hf')],
      deploys: [{ ...deploy, event, head_sha: older, run_attempt: 4, created_at: '2020-01-01T00:00:00Z' }] });
    assert.equal(result.status, 'publishing');
    assert.ok(calls.includes(`commits?path=data/snapshots/${date}/snapshot.json&per_page=1&sha=${event === 'workflow_run' ? 'main' : older}`));
    assert.ok(calls.every(path => !path.includes('weekly-snapshot')));
  }
  assert.equal((await verdict({ statuses: [status('captured'), status('hf')], deploys: [deploy], tree: null })).result.status, 'failed');
  assert.equal((await verdict({ statuses: [status('captured'), status('hf')], deploys: [deploy], tree: older })).result.status, 'failed');
  const hf = await verdict({ statuses: [status('captured'), status('deployed')], weeklies: [weekly] });
  assert.equal(hf.result.status, 'publishing');
  assert.ok(hf.calls.every(path => !path.includes('deploy-web')));
  assert.equal((await verdict({ statuses: [status('captured'), status('deployed')], deploys: [deploy] })).result.status, 'failed');
  assert.equal((await verdict({ statuses: [status('deployed'), status('hf')], deploys: [deploy] })).result.status, 'failed');
});

test('rerun after HF failure and repair by another workflow use only the last HF context', async () => {
  const failed = await verdict({ statuses: [status('captured'), status('deployed'), status('hf', 'failure')],
    override: path => { if (path.startsWith('actions/')) throw new Error('HTTP 503 history'); } });
  assert.equal(failed.result.status, 'failed');
  assert.match(failed.result.message, /Verify hf/);
  const fixed = await verdict({ override: path => { if (path.startsWith('actions/')) throw new Error('HTTP 503 history'); } });
  assert.equal(fixed.result.status, 'released');
  assert.equal(fixed.calls.length, 2);
});

test('503 for every required read is unknown, including with active work or apparent receipts', async () => {
  for (const failing of ['commits?', '/status?', 'weekly-snapshot', 'deploy-web', `sha=${older}`]) {
    const { result } = await verdict({ statuses: [status('captured')], weeklies: [weekly],
      deploys: [{ ...deploy, head_sha: older }],
      override: path => { if (path.includes(failing)) throw new Error('HTTP 503'); } });
    assert.equal(result.status, 'unknown', failing);
    assert.match(result.message, /503/);
  }
});

test('incomplete or malformed API responses fail closed', async () => {
  const overrides = [
    path => path.startsWith('commits?') ? {} : undefined,
    path => path.startsWith('commits?') ? [{ sha: 'bad' }] : undefined,
    path => path.includes('/status?') ? { sha: older, statuses: complete, total_count: 3 } : undefined,
    path => path.includes('/status?') ? { sha, statuses: complete, total_count: 4 } : undefined,
    path => path.includes('weekly-snapshot') ? { workflow_runs: [weekly], total_count: 2 } : undefined,
    path => path.includes('weekly-snapshot') ? { workflow_runs: [{}], total_count: 1 } : undefined,
    path => path.includes('deploy-web') ? { workflow_runs: [{ ...deploy, head_sha: undefined }], total_count: 1 } : undefined,
  ];
  for (const override of overrides) assert.equal((await verdict({ statuses: [status('captured')], override })).result.status, 'unknown');
  await assert.rejects(snapshotCommit('../bad', async () => assert.fail('invalid date must not reach API')));
});

function mockTransport(t, get) {
  const saved = { GH_TOKEN: process.env.GH_TOKEN, GITHUB_REPOSITORY: process.env.GITHUB_REPOSITORY };
  process.env.GH_TOKEN = 'test-token';
  process.env.GITHUB_REPOSITORY = 'example/archive';
  t.after(() => { for (const [key, value] of Object.entries(saved)) {
    if (value === undefined) delete process.env[key]; else process.env[key] = value;
  } });
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(options.headers.authorization, 'Bearer test-token');
    assert.equal(options.headers['x-github-api-version'], '2022-11-28');
    assert.ok(options.signal instanceof AbortSignal);
    assert.ok(url.startsWith('https://api.github.com/repos/example/archive/'));
    return get(url.split('/example/archive/')[1], options);
  });
}

test('freshness runner uses the shared network boundary and never reads site/latest for release', async t => {
  const mock = api();
  mockTransport(t, async path => new Response(JSON.stringify(await mock.get(path))));
  assert.equal(evaluateWeeklyRelease(await readWeeklyFacts(nowIso)).status, 'released');
  assert.equal(mock.calls.length, 2);
});

test('watchdog runner uses the same receipt despite a green latest weekly and failed HF', async t => {
  const mock = api({ statuses: [status('captured'), status('deployed'), status('hf', 'failure')] });
  mockTransport(t, async path => {
    if (path === 'actions/workflows?per_page=100') return Response.json({ workflows: [
      { id: 1, name: 'weekly-snapshot', path: '.github/workflows/weekly-snapshot.yml' },
    ] });
    return Response.json(await mock.get(path));
  });
  // The runner uses the real observation date; the fixture's date is taken from
  // its commit query so this wiring check is independent of the calendar.
  const actualGet = globalThis.fetch;
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url.includes('commits?')) return Response.json([{ sha }]);
    if (url.includes('/status?')) return Response.json({ sha, statuses: [status('hf', 'failure')], total_count: 1 });
    return actualGet(url, options);
  });
  const results = await watchdog();
  const weeklyResult = results.find(row => row.name === 'weekly-snapshot');
  assert.equal(weeklyResult.releaseStatus, 'failed');
  assert.equal(weeklyResult.status, 'red');
  assert.match(weeklyResult.message, /Verify hf/);
});

test('HTTP errors and JSON/network errors stay unknown through the actual fetch adapter', async t => {
  mockTransport(t, () => new Response('', { status: 503 }));
  assert.equal(evaluateWeeklyRelease(await readWeeklyFacts(nowIso)).status, 'unknown');
  t.mock.method(globalThis, 'fetch', async () => { throw new Error('network'); });
  assert.equal(evaluateWeeklyRelease(await readWeeklyFacts(nowIso)).status, 'unknown');
  t.mock.method(globalThis, 'fetch', async () => new Response('not json'));
  assert.equal(evaluateWeeklyRelease(await readWeeklyFacts(nowIso)).status, 'unknown');
});

test('writer POSTs only the named context on the snapshot commit and preserves failure on a skip', async t => {
  const calls = [];
  mockTransport(t, async (path, options) => {
    calls.push({ path, method: options.method, body: JSON.parse(options.body) });
    return Response.json({});
  });
  const env = { GITHUB_REPOSITORY: 'example/archive', GITHUB_RUN_ID: '123' };
  for (const state of ['failure', 'success']) await writeReleaseStatus({ sha, date, stage: 'hf', state, description: 'HF receipt' }, githubJson, env);
  assert.deepEqual(calls.map(call => [call.path, call.method, call.body.context, call.body.state]), [
    [`statuses/${sha}`, 'POST', 'evidaxis/release-hf', 'failure'],
    [`statuses/${sha}`, 'POST', 'evidaxis/release-hf', 'success'],
  ]);
  assert.equal(calls[0].body.target_url, 'https://github.com/example/archive/actions/runs/123');
  assert.equal(stageResult('hf', { hf: { outcome: 'skipped' } }), null);
});

test('writer refuses rehearsal, invalid identity and false captured receipts before the API', async () => {
  const write = async () => assert.fail('must not write a status');
  const input = { sha, date, stage: 'captured', state: 'success', description: date };
  await assert.rejects(writeReleaseStatus(input, write, { MODE: 'rehearsal' }), /Rehearsal/);
  for (const patch of [{ sha: '' }, { date: '../bad' }, { stage: 'other' }, { state: 'pending' },
    { description: '' }, { description: 'another date' }, { state: 'failure' }]) {
    await assert.rejects(writeReleaseStatus({ ...input, ...patch }, write, {}));
  }
  let saved;
  await writeReleaseStatus(input, async (path, body) => { saved = { path, body }; }, {});
  assert.equal(saved.path, `statuses/${sha}`);
  assert.equal(saved.body.description, date);
});

test('publication status is success only after its receipt, otherwise it names the actual failed step', () => {
  for (const stage of ['deployed', 'hf']) {
    const receipt = stage === 'hf' ? 'hf' : 'receipt';
    assert.equal(stageResult(stage, { [receipt]: { outcome: 'success' } })?.state, 'success');
    assert.equal(stageResult(stage, { [receipt]: { outcome: 'skipped' } }), null);
    assert.equal(stageResult(stage, { [receipt]: { outcome: 'cancelled' } })?.state, 'failure');
  }
  for (const id of ['secrets', 'node', 'build', 'deploy', 'receipt']) {
    const result = stageResult('deployed', { [id]: { outcome: 'failure' } });
    assert.equal(result?.state, 'failure');
    assert.ok(result.description.length > 5);
  }
  assert.match(stageResult('deployed', { build: { outcome: 'failure' } }).description, /Build the static site/);
  assert.equal(stageResult('deployed', { deploy: { outcome: 'success' }, receipt: { outcome: 'skipped' } }), null);
});

test('manual HF repair records success only after uploader readback; failures are recorded and propagated', async () => {
  for (const code of [0, 3, 4, 5, null]) {
    const order = [];
    const invoke = () => mirrorSnapshot(date, {
      target: async input => { assert.equal(input, date); order.push('target'); return { sha, date }; },
      run: (command, args) => { assert.equal(command, 'python3'); assert.deepEqual(args, ['scripts/hf_upload_snapshot.py', '--date', date]); order.push('upload/readback'); return { status: code }; },
      write: async payload => { order.push('status'); assert.equal(payload.sha, sha); assert.equal(payload.stage, 'hf'); assert.equal(payload.state, code === 0 ? 'success' : 'failure'); },
    });
    if (code === 0) await invoke(); else await assert.rejects(invoke(), /HF publication failed/);
    assert.deepEqual(order, ['target', 'upload/readback', 'status']);
  }
  await assert.rejects(mirrorSnapshot(date, { target: async () => ({ sha, date }), run: () => ({ status: 0 }),
    write: async () => { throw new Error('status API 503'); } }), /503/);
});

test('writer resolves the snapshot commit at the checked-out tree, not current main or workflow head', async () => {
  const calls = [];
  const target = await releaseTarget(date, async path => { calls.push(path); return [{ sha }]; });
  assert.deepEqual(target, { sha, date });
  assert.equal(calls.length, 1);
  assert.match(calls[0], /&sha=[a-f0-9]{40}$/);
  assert.ok(calls[0].includes(`path=data/snapshots/${date}/snapshot.json&per_page=1`));
});

test('unrelated failing commit contexts do not veto three release receipts', async () => {
  const { result } = await verdict({ override: path => path.includes('/status?') ? { sha, state: 'failure',
    statuses: [...complete, { context: 'other-ci', state: 'failure' }], total_count: 4 } : undefined });
  assert.equal(result.status, 'released');
});
