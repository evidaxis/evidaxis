// Thin GitHub reader shared by freshness and the watchdog. No jobs or attempt
// history is needed: the release chain writes its own receipts on the commit.
import { isInFlight, isWeeklyRelease, RELEASE_CONTEXTS, releaseStatuses, weeklyReleaseDay } from './weekly-release.mjs';

export async function githubJson(path, body) {
  const { GH_TOKEN, GITHUB_REPOSITORY } = process.env;
  if (!GH_TOKEN || !GITHUB_REPOSITORY) throw new Error('GH_TOKEN or GITHUB_REPOSITORY missing');
  const response = await fetch(`https://api.github.com/repos/${GITHUB_REPOSITORY}/${path}`, {
    method: body ? 'POST' : 'GET',
    headers: { accept: 'application/vnd.github+json', authorization: `Bearer ${GH_TOKEN}`,
      'content-type': 'application/json', 'user-agent': 'freshness-sensor/1', 'x-github-api-version': '2022-11-28' },
    ...(body ? { body: JSON.stringify(body) } : {}),
    signal: AbortSignal.timeout(10_000),
  });
  if (!response.ok) throw new Error(`GitHub HTTP ${response.status}`);
  return response.json();
}

export async function snapshotCommit(date, get = githubJson, ref = 'main') {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new Error('Invalid snapshot date');
  const commits = await get(`commits?path=data/snapshots/${date}/snapshot.json&per_page=1&sha=${encodeURIComponent(ref)}`);
  if (!Array.isArray(commits) || commits.length > 1 ||
      (commits.length && !/^[a-f0-9]{40}$/.test(commits[0]?.sha))) throw new Error('Invalid snapshot commit response');
  return commits[0]?.sha ?? null;
}

async function activeRuns(workflow, get) {
  const groups = await Promise.all(['queued', 'in_progress'].map(async status => {
    const body = await get(`actions/workflows/${workflow}.yml/runs?per_page=100&branch=main&status=${status}`);
    if (!Array.isArray(body?.workflow_runs) || !Number.isInteger(body.total_count) ||
        body.total_count !== body.workflow_runs.length) throw new Error('Incomplete active runs');
    if (body.workflow_runs.some(run => !run || typeof run.status !== 'string' ||
        typeof run.head_branch !== 'string' || typeof run.display_title !== 'string')) {
      throw new Error('Invalid active run');
    }
    return body.workflow_runs.filter(run => isInFlight(run) && run.head_branch === 'main' && run.event !== 'pull_request');
  }));
  return groups.flat();
}

export async function readReleaseFacts(nowIso, get = githubJson) {
  try {
    const date = weeklyReleaseDay(nowIso);
    const sha = await snapshotCommit(date, get);
    const body = sha ? await get(`commits/${sha}/status?per_page=100`) : { statuses: [], total_count: 0 };
    if (sha && body.sha !== sha) throw new Error('Status commit mismatch');
    const record = { ...body, date, sha };
    const statuses = releaseStatuses(record, date);
    const missing = RELEASE_CONTEXTS.filter(stage => statuses[stage]?.state !== 'success');
    if (!missing.length || Object.values(statuses).some(status => ['failure', 'error'].includes(status.state))) {
      return { nowIso, record };
    }
    // Only read activity for stages without receipts. An unrelated API outage
    // cannot undo a fully recorded release, and completed runs never enter here.
    const capturing = missing.includes('captured');
    const [weekly, deploys] = await Promise.all([
      capturing || missing.includes('hf') ? activeRuns('weekly-snapshot', get) : [],
      !capturing && missing.includes('deployed') ? activeRuns('deploy-web', get) : [],
    ]);
    let active = weekly.some(run => isWeeklyRelease(run, date));
    for (const run of deploys) {
      // deploy-web publishes the whole archive. workflow_run checks out main;
      // push/manual uses head_sha. Require D in that tree, never a start time.
      const ref = run.event === 'workflow_run' ? 'main' : run.head_sha;
      if (!ref) throw new Error('Missing deployment tree');
      if (await snapshotCommit(date, get, ref) === sha) active = true;
    }
    return { nowIso, record, active };
  } catch (error) {
    return { nowIso, apiError: error.message };
  }
}
