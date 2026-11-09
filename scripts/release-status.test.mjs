import { test } from 'node:test';
import assert from 'node:assert/strict';
import { githubJson } from './release-record.mjs';
import { deploymentSkipped, dispatchDeployment, mirrorSnapshot, prepareDeployment,
  writeReleaseStatus } from './release-status.mjs';

const release = { sha: 'a'.repeat(40), date: '2026-11-07' };
const captured = { context: 'evidaxis/release-captured', state: 'success', description: release.date };
const deployed = { context: 'evidaxis/release-deployed', state: 'success', description: 'Site receipt' };
const hfFailed = { context: 'evidaxis/release-hf', state: 'failure', description: 'HF receipt failed' };
// Recorded API shapes are synthetic and independent of the archive and clock.
const notYet = { sha: release.sha, total_count: 2, statuses: [captured, hfFailed] };
const already = { sha: release.sha, total_count: 3, statuses: [captured, deployed, hfFailed] };
const dated = { GITHUB_EVENT_NAME: 'workflow_dispatch', INPUT_DATE: release.date };
const fallback = { GITHUB_EVENT_NAME: 'workflow_run' };

function statusApi(initial) {
  const record = structuredClone(initial);
  const dispatches = [];
  const writes = [];
  const request = async (path, body) => {
    if (!body) {
      assert.equal(path, `commits/${release.sha}/status?per_page=100`);
      return record;
    }
    if (path === 'actions/workflows/deploy-web.yml/dispatches') {
      dispatches.push(body);
      return null;
    }
    assert.equal(path, `statuses/${release.sha}`);
    writes.push(body);
    record.statuses = record.statuses.filter(row => row.context !== body.context).concat(body);
    record.total_count = record.statuses.length;
    return body;
  };
  return { request, dispatches, writes, record };
}

test('not yet deployed: HF failure cannot prevent dated dispatch or fallback publication', async () => {
  const api = statusApi(notYet);
  assert.equal(await dispatchDeployment(release, api.request, {}), true);
  assert.deepEqual(api.dispatches, [{ ref: 'main', inputs: { release_date: release.date } }]);
  for (const env of [dated, fallback]) {
    assert.equal(await prepareDeployment(release, env, api.request), false);
  }
});

test('already deployed: both triggers skip even while HF is red, without rewriting receipts', async () => {
  const api = statusApi(already);
  assert.equal(await dispatchDeployment(release, api.request, {}), false);
  for (const env of [dated, fallback]) {
    assert.equal(await prepareDeployment(release, env, api.request), true);
  }
  assert.deepEqual(api.dispatches, []);
  assert.deepEqual(api.writes, []);
});

test('HF fails after dispatch; first deployment writes its receipt and the queued duplicate skips', async () => {
  const api = statusApi({ sha: release.sha, total_count: 1, statuses: [captured] });
  assert.equal(await dispatchDeployment(release, api.request, {}), true);
  await assert.rejects(mirrorSnapshot(release.date, {
    target: async () => release,
    run: () => { assert.equal(api.dispatches.length, 1); return { status: 1 }; },
    write: payload => writeReleaseStatus(payload, api.request, {}),
  }), /HF publication failed/);
  assert.equal(api.record.statuses.find(row => row.context === hfFailed.context).state, 'failure');
  assert.equal(await prepareDeployment(release, dated, api.request), false);
  await writeReleaseStatus({ ...release, stage: 'deployed', state: 'success',
    description: 'Site receipt' }, api.request, {});
  assert.equal(await prepareDeployment(release, fallback, api.request), true);
  assert.equal(await prepareDeployment(release, dated, api.request), true);
  assert.equal(await dispatchDeployment(release, api.request, {}), false);
  assert.equal(api.dispatches.length, 1);
});

test('failed or pending site receipts remain retryable regardless of HF success', async () => {
  for (const state of ['failure', 'error', 'pending']) {
    const api = statusApi({ ...already, statuses: [captured, { ...deployed, state },
      { ...hfFailed, state: 'success' }] });
    assert.equal(await prepareDeployment(release, fallback, api.request), false);
    assert.equal(await dispatchDeployment(release, api.request, {}), true);
  }
});

test('ordinary code pushes and undated manual deploys still rebuild an already released snapshot', async () => {
  const request = async () => assert.fail('undated deploy must not depend on release receipts');
  for (const env of [{ GITHUB_EVENT_NAME: 'push' },
    { GITHUB_EVENT_NAME: 'workflow_dispatch', INPUT_DATE: '' }]) {
    assert.equal(await prepareDeployment(release, env, request), false);
  }
});

test('fallback and automatic dispatch cannot publish a missing or mismatched captured receipt', async () => {
  for (const statuses of [[], [deployed], [{ ...captured, state: 'failure' }],
    [{ ...captured, description: '2026-10-31' }]]) {
    const api = statusApi({ sha: release.sha, statuses, total_count: statuses.length });
    await assert.rejects(dispatchDeployment(release, api.request, {}), /Captured/);
    await assert.rejects(prepareDeployment(release, fallback, api.request), /Captured/);
    assert.equal(api.dispatches.length, 0);
  }
});

test('unknown status state fails closed instead of admitting publication or claiming a skip', async () => {
  for (const record of [{ ...already, sha: 'b'.repeat(40) },
    { ...already, total_count: 4 }, { ...already, statuses: null }]) {
    await assert.rejects(deploymentSkipped(release, {}, async () => record));
  }
  await assert.rejects(prepareDeployment(release, fallback, async () => {
    throw new Error('GitHub HTTP 503');
  }), /503/);
});

test('rehearsal never dispatches and dispatch errors stay red for the fallback to recover', async () => {
  await assert.rejects(dispatchDeployment(release, async () => assert.fail('no API in rehearsal'),
    { MODE: 'rehearsal' }), /Rehearsal/);
  await assert.rejects(dispatchDeployment(release, async (path, body) => {
    if (!body) return notYet;
    throw new Error('GitHub HTTP 403');
  }, {}), /403/);
});

test('real GitHub adapter accepts the empty 204 dispatch response and propagates HTTP failure', async t => {
  const saved = { GH_TOKEN: process.env.GH_TOKEN, GITHUB_REPOSITORY: process.env.GITHUB_REPOSITORY };
  process.env.GH_TOKEN = 'test-token';
  process.env.GITHUB_REPOSITORY = 'example/archive';
  t.after(() => { for (const [key, value] of Object.entries(saved)) {
    if (value === undefined) delete process.env[key]; else process.env[key] = value;
  } });
  let responseCode = 204;
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(options.headers.authorization, 'Bearer test-token');
    if (options.method === 'GET') return Response.json(notYet);
    assert.equal(url, 'https://api.github.com/repos/example/archive/actions/workflows/deploy-web.yml/dispatches');
    assert.deepEqual(JSON.parse(options.body), { ref: 'main', inputs: { release_date: release.date } });
    return new Response(null, { status: responseCode });
  });
  assert.equal(await dispatchDeployment(release, githubJson, {}), true);
  responseCode = 403;
  await assert.rejects(dispatchDeployment(release, githubJson, {}), /GitHub HTTP 403/);
});
