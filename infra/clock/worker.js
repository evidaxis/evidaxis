import { findRuns, needsDispatch, tick } from './logic.mjs';

export async function runTick(controller, env, fetcher = fetch, pause = ms => new Promise(resolve => setTimeout(resolve, ms))) {
  const inputs = tick(controller.cron, controller.scheduledTime);
  if (!env.GH_DISPATCH_TOKEN) throw new Error('GH_DISPATCH_TOKEN missing');
  if (inputs.mode === 'release' && env.GH_REF !== 'main') throw new Error('release requires main');
  const base = `https://api.github.com/repos/${env.GH_REPOSITORY}/actions/workflows/weekly-snapshot.yml`;
  async function request(path, body) {
    const response = await fetcher(`${base}/${path}`, {
      method: body ? 'POST' : 'GET',
      headers: { Authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`, 'User-Agent': 'evidaxis-release-clock',
        Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
      body: body ? JSON.stringify(body) : undefined,
      // Bound each request so failed API access cannot consume the whole cron window.
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) throw new Error(`GitHub ${body ? 'dispatch' : 'runs'} HTTP ${response.status}`);
    return body ? null : response.json();
  }
  async function listRuns() {
    const runs = [];
    for (let page = 1; ; page++) {
      // A manual rehearsal may predate Wednesday, so never infer its creation date from its label.
      const query = new URLSearchParams({ branch: env.GH_REF, per_page: '100', page: String(page) });
      const body = await request(`runs?${query}`);
      if (!Array.isArray(body.workflow_runs) || !Number.isInteger(body.total_count)) throw new Error('invalid GitHub runs response');
      runs.push(...body.workflow_runs);
      if (runs.length >= body.total_count) return runs;
      // GitHub caps filtered history at 1,000 results; incomplete evidence is unsafe.
      if (!body.workflow_runs.length || runs.length >= 1000) throw new Error('GitHub run history incomplete');
    }
  }
  const before = await listRuns();
  if (!needsDispatch(before, inputs, env.GH_REF)) {
    console.log(JSON.stringify({ ...inputs, outcome: 'already_present' }));
    return;
  }
  let dispatchError;
  try {
    await request('dispatches', { ref: env.GH_REF, inputs });
  } catch (error) {
    // A lost response can still have created a run. Observe; never resend this tick.
    dispatchError = error;
  }
  const oldIds = new Set(before.map(run => run.id));
  // Three observations over 20 seconds allow for GitHub's asynchronous dispatch indexing.
  for (let attempt = 0; attempt < 3; attempt++) {
    if (attempt) await pause(10000);
    const appeared = findRuns(await listRuns(), inputs, env.GH_REF).find(run => !oldIds.has(run.id));
    if (appeared) {
      console.log(JSON.stringify({ ...inputs, outcome: 'run_observed', run_id: appeared.id, status: appeared.status }));
      return;
    }
  }
  throw dispatchError || new Error('dispatch accepted but no new run observed');
}

export default {
  async scheduled(controller, env) {
    try {
      await runTick(controller, env);
    } catch (error) {
      console.error(JSON.stringify({ outcome: 'clock_error', message: error.message }));
      throw error;
    }
  },
};
