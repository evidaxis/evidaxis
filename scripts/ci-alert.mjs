// Keeper alert when web-ci or python-ci turns red on main.
// One message on a green→red transition. While the check stays red, one reminder per UTC day.
// Quiet only after a keeper step that actually exited 0. A failed send does not count.
import { pathToFileURL } from 'node:url';
import { failedStepName } from './rehearsal-alert.mjs';
import { sendTelegram } from './telegram.mjs';

// GitHub marks a completed run with these conclusions. Anything else is not "still red".
const STILL_RED = new Set(['failure', 'timed_out']);

/** UTC calendar day of an ISO timestamp, or ''. */
export function utcDay(iso) {
  const time = Date.parse(iso ?? '');
  if (Number.isNaN(time)) return '';
  return new Date(time).toISOString().slice(0, 10);
}

const MAIN_EVENTS = new Set(['push', 'workflow_run']);

/** True for a push or workflow_run on this repository's main. Pull requests are never included. */
export function isOwnMainRun(run, repo) {
  if (!run || !repo) return false;
  if (!MAIN_EVENTS.has(run.event)) return false;
  const branch = run.head_branch ?? run.headBranch;
  if (branch !== 'main') return false;
  const head = run.head_repository?.full_name
    || (typeof run.head_repository === 'string' ? run.head_repository : '')
    || run.headRepo
    || '';
  return head === repo;
}

/** A keeper step with conclusion success counts as delivery. Failure does not. */
export function alertStepSent(jobsBody) {
  const jobs = Array.isArray(jobsBody?.jobs) ? jobsBody.jobs : [];
  return jobs.some((job) => (job.steps || []).some((step) =>
    typeof step.name === 'string'
    && step.name.startsWith('Tell the keeper')
    && step.conclusion === 'success'));
}

function completedAt(run) {
  return run?.completed_at || run?.completedAt || run?.updated_at || '';
}

function stamp(run) {
  return Date.parse(completedAt(run)) || 0;
}

/**
 * @param {object|object[]|null|undefined} previous one run, or the history newest-first is not required
 * @param {string} nowIso
 * @returns {{ send: boolean, kind: 'transition'|'reminder'|'unknown'|'quiet' }}
 */
export function decideAlert(previous, nowIso) {
  // No previous completed run on main, or the API could not be read: send.
  // A missed first failure is the outage this alert exists to stop.
  if (previous == null) return { send: true, kind: 'unknown' };
  const history = (Array.isArray(previous) ? previous : [previous]).filter(Boolean);
  const ranked = [...history].sort((a, b) => stamp(b) - stamp(a));
  const latest = ranked[0];
  if (!latest || !latest.conclusion) return { send: true, kind: 'unknown' };
  if (latest.conclusion === 'success') return { send: true, kind: 'transition' };
  if (!STILL_RED.has(latest.conclusion)) return { send: true, kind: 'unknown' };
  const delivery = ranked.find((run) => run.alertSent === true);
  if (!delivery) return { send: true, kind: 'transition' };
  const delivered = utcDay(completedAt(delivery));
  const today = utcDay(nowIso);
  if (!delivered || !today) return { send: true, kind: 'unknown' };
  if (delivered === today) return { send: false, kind: 'quiet' };
  if (delivered < today) return { send: true, kind: 'reminder' };
  return { send: true, kind: 'unknown' };
}

/** push and workflow_run on this repo's main. Earlier attempts of the current run stay. */
export function selectHistory(runs, { repo, currentRunId, currentAttempt = 1 } = {}) {
  const limit = Number(currentAttempt) || 1;
  return (runs || []).filter((run) => {
    if (!run || !isOwnMainRun(run, repo)) return false;
    if (String(run.id) === String(currentRunId)) {
      const attempt = Number(run.attempt ?? run.run_attempt ?? 1);
      return attempt < limit;
    }
    return true;
  });
}

/**
 * Latest earlier run. An earlier attempt of this same run counts.
 * When repo is set, only push and workflow_run on that repo's main remain.
 */
export function pickPrevious(runs, currentRunId, currentAttempt = 1, repo = null) {
  const limit = Number(currentAttempt) || 1;
  const pool = repo
    ? selectHistory(runs, { repo, currentRunId, currentAttempt })
    : (runs || []).filter((run) => {
      if (!run) return false;
      if (String(run.id) === String(currentRunId)) {
        const attempt = Number(run.attempt ?? run.run_attempt ?? 1);
        return attempt < limit;
      }
      return true;
    });
  const ranked = pool.sort((a, b) => {
    const left = Date.parse(a.updated_at || a.completed_at || a.created_at || '') || 0;
    const right = Date.parse(b.updated_at || b.completed_at || b.created_at || '') || 0;
    return right - left;
  });
  return ranked[0] ?? null;
}

/**
 * @param {{ workflow: string, step: string, runUrl: string, kind: string }} input
 * @returns {string}
 */
export function ciAlertText(input) {
  const step = input.step || 'неизвестен';
  if (input.kind === 'reminder') {
    return (
      `Проверка ${input.workflow} на main всё ещё красная на шаге «${step}». ` +
      `Напоминание за этот день. ${input.runUrl}`
    );
  }
  return `Проверка ${input.workflow} на main упала на шаге «${step}». ${input.runUrl}`;
}

async function githubGet(url, token) {
  const res = await fetch(url, {
    headers: {
      accept: 'application/vnd.github+json',
      authorization: `Bearer ${token}`,
      'user-agent': 'evidaxis-ci-alert/1',
      'x-github-api-version': '2022-11-28',
    },
    signal: AbortSignal.timeout(10_000),
  });
  if (!res.ok) return null;
  return res.json();
}

function historyRecord(run, jobsBody) {
  return {
    id: run.id,
    attempt: Number(run.run_attempt ?? run.attempt ?? 1),
    event: run.event,
    head_branch: run.head_branch,
    head_repository: run.head_repository,
    conclusion: run.conclusion ?? null,
    completed_at: run.updated_at || '',
    updated_at: run.updated_at || '',
    alertSent: jobsBody == null ? false : alertStepSent(jobsBody),
  };
}

/** Earlier main-branch runs of this workflow, with alert delivery taken from the keeper step. */
export async function previousMainRun() {
  const token = process.env.GH_TOKEN;
  const repo = process.env.GITHUB_REPOSITORY;
  const runId = process.env.GITHUB_RUN_ID;
  const currentAttempt = Number(process.env.GITHUB_RUN_ATTEMPT || '1') || 1;
  if (!token || !repo || !runId) return null;
  try {
    const api = `https://api.github.com/repos/${repo}/actions`;
    const run = await githubGet(`${api}/runs/${runId}`, token);
    if (!run || !run.workflow_id) return null;
    // updated_at is the completion time: the run object has no completed_at field.
    // per_page=20 stays. exclude_pull_requests drops fork runs before the page fills.
    const list = await githubGet(
      `${api}/workflows/${run.workflow_id}/runs?branch=main&status=completed&exclude_pull_requests=true&per_page=20`,
      token,
    );
    if (!list || !Array.isArray(list.workflow_runs)) return null;
    const earlier = [];
    for (let attempt = 1; attempt < currentAttempt; attempt += 1) {
      const past = await githubGet(`${api}/runs/${runId}/attempts/${attempt}`, token);
      if (!past) return null;
      past.id = past.id || Number(runId);
      past.run_attempt = past.run_attempt || attempt;
      earlier.push(past);
    }
    const selected = selectHistory([...earlier, ...list.workflow_runs], {
      repo,
      currentRunId: runId,
      currentAttempt,
    });
    const unique = [];
    const seen = new Set();
    for (const item of selected) {
      const key = `${item.id}:${item.run_attempt ?? item.attempt ?? 1}`;
      if (seen.has(key)) continue;
      seen.add(key);
      unique.push(item);
    }
    unique.sort((a, b) => (Date.parse(b.updated_at || '') || 0) - (Date.parse(a.updated_at || '') || 0));
    const today = utcDay(new Date().toISOString());
    const records = [];
    for (const item of unique) {
      const red = STILL_RED.has(item.conclusion);
      let jobs = null;
      if (red) {
        const attempt = item.run_attempt || item.attempt || 1;
        jobs = await githubGet(
          `${api}/runs/${item.id}/attempts/${attempt}/jobs?per_page=100`,
          token,
        );
        if (!jobs) return null;
      }
      const record = historyRecord(item, jobs);
      records.push(record);
      // The newest success is a green→red transition. An older green run is not.
      if (records.length === 1 && item.conclusion === 'success') break;
      if (record.alertSent && utcDay(record.completed_at) === today) break;
      const day = utcDay(item.updated_at || '');
      if (day && day < today) break;
    }
    return records;
  } catch {
    return null;
  }
}

async function loadJobs() {
  const token = process.env.GH_TOKEN;
  const repo = process.env.GITHUB_REPOSITORY;
  const runId = process.env.GITHUB_RUN_ID;
  const attempt = process.env.GITHUB_RUN_ATTEMPT || '1';
  if (!token || !repo || !runId) return null;
  return githubGet(
    `https://api.github.com/repos/${repo}/actions/runs/${runId}/attempts/${attempt}/jobs?per_page=100`,
    token,
  );
}

async function main() {
  const workflow = process.env.GITHUB_WORKFLOW || 'проверка';
  const server = process.env.GITHUB_SERVER_URL || 'https://github.com';
  const repo = process.env.GITHUB_REPOSITORY || '';
  const runId = process.env.GITHUB_RUN_ID || '';
  const runUrl = `${server}/${repo}/actions/runs/${runId}`;
  const decision = decideAlert(await previousMainRun(), new Date().toISOString());
  if (!decision.send) {
    console.log(`проверка ${workflow} всё ещё красная; сообщение за этот день уже было`);
    return;
  }
  let jobs = null;
  try {
    jobs = await loadJobs();
  } catch {
    jobs = null;
  }
  const text = ciAlertText({
    workflow,
    step: failedStepName(jobs) || 'неизвестен',
    runUrl,
    kind: decision.kind,
  });
  console.log(text);
  const sent = await sendTelegram(text, 'ci');
  if (!sent && process.env.TELEGRAM_BOT_TOKEN && process.env.ALERT_CHAT_ID) process.exit(1);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
