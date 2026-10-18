// Saturday release score. Four unattended on-time Saturdays are required before
// the release is called repaired. This file counts them from Actions runs and
// commit receipts. It prints no logins, deploy URLs, or commit messages.
//
// Pure scoring is everything below loadScorecard. loadScorecard is the only
// network path.

import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

export const FIRST_SATURDAY = '2026-08-29';
// The acceptance window named in the 2026-10-18 release schedule.
export const SCORE_SATURDAYS = ['2026-10-24', '2026-10-31', '2026-11-07', '2026-11-14'];
const RELEASE_CONTEXTS = ['captured', 'deployed', 'hf'];
const DAY_MS = 86400000;
// Five seconds covers a workflow_run recorded in the same second as the capture.
const DEPLOY_SKEW_MS = 5000;

/** @param {{ type?: string } | string | null | undefined} actor */
export function actorKind(actor) {
  if (actor === 'bot' || actor === 'human' || actor === 'unknown') return actor;
  if (actor?.type === 'Bot') return 'bot';
  if (actor?.type === 'User') return 'human';
  return 'unknown';
}

/**
 * Dated titles win. Legacy runs have no date in the name: Saturday through
 * Tuesday (D…D+3) belong to that Saturday, so a Monday repair counts and a
 * Wednesday rehearsal does not.
 * @param {string} title
 * @param {string} startedAt
 */
export function releaseSaturday(title, startedAt) {
  const text = String(title ?? '');
  if (text.includes('resolve-date') || text.startsWith('weekly rehearsal')) return null;
  const dated = /^weekly release (\d{4}-\d{2}-\d{2})$/.exec(text);
  if (dated) return dated[1];
  const time = Date.parse(startedAt);
  if (Number.isNaN(time)) return null;
  const day = new Date(time);
  const midnight = Date.UTC(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate());
  const dow = new Date(midnight).getUTCDay();
  const sinceSaturday = dow === 6 ? 0 : dow + 1;
  if (sinceSaturday > 3) return null;
  return new Date(midnight - sinceSaturday * DAY_MS).toISOString().slice(0, 10);
}

/** A green guard that skipped collection is not a capture. Unknown jobs are not success. */
export function snapshotSkipped(jobsBody) {
  const jobs = jobsBody?.jobs;
  if (!Array.isArray(jobs)) return true;
  const snapshot = jobs.find(job => job?.name === 'snapshot');
  if (!snapshot || snapshot.conclusion === 'skipped') return true;
  const collect = (snapshot.steps || []).find(step => step?.name?.startsWith('Collect snapshot'));
  return collect?.conclusion === 'skipped';
}

export function saturdaysThrough(nowIso) {
  const end = Date.parse(nowIso);
  if (Number.isNaN(end)) throw new Error('Invalid clock');
  const days = [];
  for (let time = Date.parse(`${FIRST_SATURDAY}T00:00:00Z`); time <= end; time += DAY_MS) {
    const day = new Date(time).toISOString().slice(0, 10);
    if (new Date(time).getUTCDay() === 6) days.push(day);
  }
  return days;
}

function stamp(value) {
  const time = Date.parse(value ?? '');
  return Number.isNaN(time) ? null : time;
}

function beforeNoon(iso, saturday) {
  const time = stamp(iso);
  return time !== null && time < Date.parse(`${saturday}T12:00:00Z`);
}

const DAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
let configuredTicks = null;

/** The external clock's cron ticks, parsed from its own config so the two cannot drift. */
export function clockTicks(toml) {
  const list = /crons\s*=\s*\[([^\]]*)\]/.exec(toml);
  return list ? [...list[1].matchAll(/"(\d+) (\d+) \* \* ([A-Z]{3})"/g)]
    .map(([, min, hour, day]) => ({ min: Number(min), hour: Number(hour), day })) : [];
}

function ticks() {
  if (configuredTicks === null) {
    try {
      configuredTicks = clockTicks(readFileSync(new URL('../infra/clock/wrangler.toml', import.meta.url), 'utf8'));
    } catch {
      configuredTicks = [];
    }
  }
  return configuredTicks;
}

/** The clock dispatches with the steward's key, so GitHub reports a User; its tick window tells them apart. */
export function clockDispatch(startedAt, list = ticks()) {
  const time = stamp(startedAt);
  if (time === null) return false;
  const day = new Date(time);
  return list.some(({ min, hour, day: weekday }) => {
    if (DAYS[day.getUTCDay()] !== weekday) return false;
    const tick = Date.UTC(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate(), hour, min);
    return time >= tick && time - tick <= 30 * 60 * 1000;
  });
}

/** Schedule stays the clock even when GitHub labels its actor User. A rerun click does not. */
function humanLaunch(attempt) {
  if (attempt.actor !== 'human') return false;
  if (attempt.event === 'workflow_dispatch') return !clockDispatch(attempt.started_at);
  return Number(attempt.run_attempt) > 1;
}

function captured(attempt) {
  return attempt.status === 'completed' && attempt.conclusion === 'success' && attempt.collected !== false;
}

function byStart(a, b) {
  return stamp(a.started_at) - stamp(b.started_at);
}

function publicAttempt(attempt) {
  const skipped = attempt.conclusion === 'success' && attempt.collected === false;
  return {
    started_at: attempt.started_at,
    completed_at: attempt.completed_at,
    conclusion: skipped ? 'skipped' : (attempt.conclusion ?? null),
    status: attempt.status,
    event: attempt.event,
    actor: attempt.actor,
  };
}

function receipt(statuses, stage) {
  return (statuses || []).find(status => status?.context === `evidaxis/release-${stage}`) || null;
}

function hfCell(statuses) {
  return receipt(statuses, 'hf')?.state || 'нет записи';
}

/**
 * @param {{
 *   now: string,
 *   weekly?: object[],
 *   deploys?: object[],
 *   statuses?: Record<string, object[]>,
 *   edits?: Record<string, { at: string, actor: string }[]>,
 * }} facts
 */
export function buildScorecard(facts) {
  const days = saturdaysThrough(facts.now);
  const weekly = (facts.weekly || []).map(normalizeWeekly).filter(run => run.saturday && run.branch === 'main' && run.event !== 'pull_request');
  const deploys = (facts.deploys || []).map(normalizeDeploy).filter(run => run.branch === 'main' && run.event !== 'pull_request');
  const rows = days.map(saturday => scoreSaturday(saturday, {
    weekly: weekly.filter(run => run.saturday === saturday).sort(byStart),
    deploys,
    statuses: facts.statuses?.[saturday] || [],
    edits: facts.edits?.[saturday] || [],
  }));
  return { score: scoreText(rows, facts.now), rows };
}

function normalizeWeekly(run) {
  const started_at = run.started_at || run.run_started_at || run.created_at;
  const title = run.title || run.display_title || run.name || '';
  return {
    // null means the loader already rejected a rehearsal or resolve-date run.
    saturday: run.saturday !== undefined ? run.saturday : releaseSaturday(title, started_at),
    started_at,
    completed_at: run.completed_at || run.updated_at,
    status: run.status,
    conclusion: run.conclusion ?? null,
    event: run.event,
    actor: actorKind(run.actor),
    branch: run.branch || run.head_branch,
    collected: run.collected !== false && run.conclusion !== 'skipped',
    run_attempt: run.run_attempt,
  };
}

function normalizeDeploy(run) {
  return {
    started_at: run.started_at || run.run_started_at || run.created_at,
    completed_at: run.completed_at || run.updated_at,
    status: run.status,
    conclusion: run.conclusion ?? null,
    event: run.event,
    actor: actorKind(run.actor),
    branch: run.branch || run.head_branch,
  };
}

function scoreSaturday(saturday, facts) {
  const attempts = facts.weekly.filter(run => stamp(run.started_at) !== null);
  const successIndex = attempts.findIndex(captured);
  const success = successIndex === -1 ? null : attempts[successIndex];
  const path = success ? attempts.slice(0, successIndex + 1) : attempts;
  const publication = success ? publicationDeploy(facts.deploys, success.completed_at, saturday) : { failure: null, success: null };
  const human = humanWeek(path, success, facts.edits, publication.success);
  const onTime = onTimeWeek(saturday, success, publication.success, facts.statuses);
  const decisive = success || attempts.at(-1) || null;
  return {
    saturday,
    capture_start: attempts[0]?.started_at ?? null,
    capture_end: decisive?.completed_at ?? null,
    deploy_end: publication.success?.completed_at ?? null,
    hf: hfCell(facts.statuses),
    human,
    on_time: onTime,
    ok: onTime && !human,
    attempts: attempts.map(publicAttempt),
    deploy_failure: publication.failure ? publicAttempt(publication.failure) : null,
    deploy: publication.success ? publicAttempt(publication.success) : null,
  };
}

function publicationDeploy(deploys, captureEnd, saturday) {
  const start = stamp(captureEnd);
  const next = Date.parse(`${saturday}T00:00:00Z`) + 7 * DAY_MS;
  const after = deploys
    .filter(run => run.conclusion !== 'skipped')
    .filter(run => {
      const time = stamp(run.started_at);
      return time !== null && time >= start - DEPLOY_SKEW_MS && time < next;
    })
    .sort(byStart);
  const chain = after.find(run => run.event === 'workflow_run' && run.conclusion === 'success');
  if (chain) return { failure: null, success: chain };
  return {
    failure: after.find(run => run.conclusion === 'failure') || null,
    success: after.find(run => run.conclusion === 'success') || null,
  };
}

function humanWeek(path, success, edits, deploy) {
  if (path.some(humanLaunch)) return true;
  if (success) {
    const fails = path.filter(attempt => attempt !== success && attempt.conclusion && attempt.conclusion !== 'success');
    const opened = fails.map(attempt => stamp(attempt.completed_at)).filter(time => time !== null);
    const closed = stamp(success.started_at);
    if (opened.length && closed !== null && (edits || []).some(edit => edit.actor === 'human'
      && stamp(edit.at) > Math.min(...opened) && stamp(edit.at) < closed)) return true;
  }
  // A push or hand dispatch that publishes after the chain failed is a person.
  return Boolean(deploy && deploy.event !== 'workflow_run' && deploy.actor === 'human');
}

function onTimeWeek(saturday, success, deploy, statuses) {
  const recorded = RELEASE_CONTEXTS.map(stage => receipt(statuses, stage)).filter(Boolean);
  if (recorded.length) {
    const site = receipt(statuses, 'deployed');
    const hf = receipt(statuses, 'hf');
    return Boolean(site?.state === 'success' && hf?.state === 'success'
      && beforeNoon(site.updated_at, saturday) && beforeNoon(hf.updated_at, saturday));
  }
  // Before 2026-10-18 there is no receipt. The HF upload is inside the weekly
  // run, so that run's end is the HF time and the deploy end is the site time.
  return Boolean(success && deploy && beforeNoon(success.completed_at, saturday) && beforeNoon(deploy.completed_at, saturday));
}

/** Current streak inside the four acceptance Saturdays. A miss resets it. */
export function scoreText(rows, nowIso) {
  const today = String(nowIso).slice(0, 10);
  const now = stamp(nowIso);
  let streak = 0;
  for (const saturday of SCORE_SATURDAYS) {
    if (saturday > today) break;
    const row = rows.find(item => item.saturday === saturday);
    if (row?.ok) {
      streak += 1;
      continue;
    }
    const noon = Date.parse(`${saturday}T12:00:00Z`);
    const running = row?.attempts?.some(attempt => attempt.status && attempt.status !== 'completed');
    const closedFailure = !running && row?.attempts?.some(attempt => ['failure', 'cancelled', 'timed_out', 'startup_failure'].includes(attempt.conclusion));
    // Before noon, a Saturday with no closed failure can still finish unattended.
    const stillOpen = saturday === today && now !== null && now < noon && !row?.human && !closedFailure;
    if (!stillOpen) streak = 0;
  }
  return `${streak} из 4`;
}

function hm(iso, saturday) {
  const time = stamp(iso);
  if (time === null) return '—';
  const day = new Date(time);
  const clock = `${String(day.getUTCHours()).padStart(2, '0')}:${String(day.getUTCMinutes()).padStart(2, '0')}`;
  const date = day.toISOString().slice(0, 10);
  return date === saturday ? clock : `${date.slice(5)} ${clock}`;
}

export function toMarkdown(card) {
  const head = '| суббота | старт сбора UTC | конец сбора | конец выкладки | HF | человек | к 12:00 | итог |';
  const rule = '| --- | --- | --- | --- | --- | --- | --- | --- |';
  const lines = card.rows.map(row => `| ${[
    row.saturday,
    row.attempts.length ? row.attempts.map(attempt => `${hm(attempt.started_at, row.saturday)} ${attempt.conclusion || attempt.event || '—'}`).join('; ') : '—',
    row.capture_end ? `${hm(row.capture_end, row.saturday)} ${row.attempts.find(attempt => attempt.completed_at === row.capture_end)?.conclusion || ''}`.trim() : '—',
    deployCell(row),
    row.hf,
    row.human ? 'да' : 'нет',
    row.on_time ? 'да' : 'нет',
    row.ok ? 'ok' : 'нет',
  ].join(' | ')} |`);
  return [`${card.score}`, '', head, rule, ...lines].join('\n');
}

function span(startIso, endIso, saturday) {
  const start = hm(startIso, saturday);
  const end = hm(endIso, saturday);
  if (start === end) return end;
  if ((startIso || '').slice(0, 10) === (endIso || '').slice(0, 10)) return `${start}→${end.slice(-5)}`;
  return `${start}→${end}`;
}

function deployCell(row) {
  const parts = [];
  if (row.deploy_failure) parts.push(`${hm(row.deploy_failure.completed_at, row.saturday)} failure`);
  if (row.deploy) parts.push(`${span(row.deploy.started_at, row.deploy.completed_at, row.saturday)} success`);
  return parts.length ? parts.join('; ') : '—';
}

function repoOf(env) {
  const repo = env.GITHUB_REPOSITORY || 'evidaxis/evidaxis';
  if (!/^[\w.-]+\/[\w.-]+$/.test(repo)) throw new Error('Invalid repository');
  return repo;
}

async function github(repo, path, token) {
  const response = await fetch(`https://api.github.com/repos/${repo}/${path}`, {
    headers: {
      accept: 'application/vnd.github+json',
      authorization: `Bearer ${token}`,
      'user-agent': 'release-scorecard/1',
      'x-github-api-version': '2022-11-28',
    },
    // Same 10s bound as the freshness GitHub reader, so a stuck call cannot hang the score.
    signal: AbortSignal.timeout(10_000),
  });
  if (!response.ok) throw new Error(`GitHub HTTP ${response.status}`);
  const body = await response.json();
  return { body, link: response.headers.get('link') || '' };
}

async function githubList(repo, path, token, key) {
  const out = [];
  let next = `https://api.github.com/repos/${repo}/${path}${path.includes('?') ? '&' : '?'}per_page=100`;
  // Twenty pages is 2,000 runs, past GitHub's filtered history cap. Stop closed
  // rather than score a truncated Saturday list.
  for (let page = 0; page < 20; page++) {
    const response = await fetch(next, {
      headers: {
        accept: 'application/vnd.github+json',
        authorization: `Bearer ${token}`,
        'user-agent': 'release-scorecard/1',
        'x-github-api-version': '2022-11-28',
      },
      signal: AbortSignal.timeout(10_000),
    });
    if (!response.ok) throw new Error(`GitHub HTTP ${response.status}`);
    const body = await response.json();
    const items = key ? body?.[key] : body;
    if (!Array.isArray(items)) throw new Error('Invalid GitHub list');
    out.push(...items);
    if (key && body.total_count === out.length) return out;
    const match = /<([^>]+)>;\s*rel="next"/.exec(response.headers.get('link') || '');
    if (!match) {
      if (key && body.total_count !== out.length) throw new Error('Incomplete GitHub page');
      return out;
    }
    next = match[1];
  }
  throw new Error('Incomplete GitHub page');
}

function editRecord(commit) {
  const at = commit?.commit?.author?.date || commit?.commit?.committer?.date;
  if (!at) return null;
  const actor = actorKind(commit?.author) === 'human' || actorKind(commit?.committer) === 'human'
    ? 'human'
    : (actorKind(commit?.author) === 'bot' || actorKind(commit?.committer) === 'bot' ? 'bot' : 'unknown');
  return { at, actor };
}

async function loadStatuses(repo, token, days) {
  const statuses = {};
  for (const day of days) {
    const listed = await github(repo, `commits?path=data/snapshots/${day}/snapshot.json&sha=main&per_page=1`, token);
    const commits = listed.body;
    if (!Array.isArray(commits) || commits.length > 1) throw new Error('Invalid snapshot commit response');
    const sha = commits[0]?.sha;
    if (!sha || !/^[a-f0-9]{40}$/.test(sha)) {
      statuses[day] = [];
      continue;
    }
    const { body } = await github(repo, `commits/${sha}/status?per_page=100`, token);
    if (!Array.isArray(body?.statuses) || body.total_count !== body.statuses.length) throw new Error('Incomplete commit statuses');
    statuses[day] = body.statuses
      .filter(status => RELEASE_CONTEXTS.some(stage => status?.context === `evidaxis/release-${stage}`))
      .map(status => ({ context: status.context, state: status.state, updated_at: status.updated_at }));
  }
  return statuses;
}

async function loadEdits(repo, token, weekly) {
  const edits = {};
  const byDay = new Map();
  for (const run of weekly) {
    if (!run.saturday) continue;
    const list = byDay.get(run.saturday) || [];
    list.push(run);
    byDay.set(run.saturday, list);
  }
  for (const [saturday, runs] of byDay) {
    const ordered = runs.filter(run => run.collected !== false).sort(byStart);
    const success = ordered.find(captured);
    const fails = ordered.filter(run => run.conclusion && run.conclusion !== 'success');
    if (!success || !fails.length) continue;
    const since = fails.map(run => run.completed_at).sort()[0];
    const until = success.started_at;
    if (!(stamp(until) > stamp(since))) continue;
    const commits = await githubList(repo, `commits?sha=main&since=${encodeURIComponent(since)}&until=${encodeURIComponent(until)}`, token);
    edits[saturday] = commits.map(editRecord).filter(Boolean);
  }
  return edits;
}

export async function loadScorecard(env = process.env, now = new Date()) {
  const token = env.GITHUB_TOKEN || env.GH_TOKEN;
  if (!token) throw new Error('GITHUB_TOKEN or GH_TOKEN missing');
  const repo = repoOf(env);
  const nowIso = now.toISOString();
  const created = `created=%3E%3D${FIRST_SATURDAY}`;
  const [weeklyRuns, deployRuns] = await Promise.all([
    githubList(repo, `actions/workflows/weekly-snapshot.yml/runs?${created}&branch=main`, token, 'workflow_runs'),
    githubList(repo, `actions/workflows/deploy-web.yml/runs?${created}&branch=main`, token, 'workflow_runs'),
  ]);
  const weekly = [];
  for (const run of weeklyRuns) {
    const title = run.display_title || run.name || '';
    let collected = run.conclusion !== 'skipped';
    if (/^weekly release \d{4}-\d{2}-\d{2}$/.test(title) && run.conclusion === 'success') {
      const { body } = await github(repo, `actions/runs/${run.id}/jobs?per_page=100`, token);
      if (!Array.isArray(body?.jobs) || body.total_count !== body.jobs.length) throw new Error('Incomplete jobs');
      collected = !snapshotSkipped(body);
    }
    weekly.push({
      saturday: releaseSaturday(title, run.run_started_at || run.created_at),
      started_at: run.run_started_at || run.created_at,
      completed_at: run.updated_at,
      status: run.status,
      conclusion: run.conclusion ?? null,
      event: run.event,
      actor: actorKind(run.actor),
      branch: run.head_branch,
      collected,
      run_attempt: run.run_attempt,
    });
  }
  const deploys = deployRuns.map(run => ({
    started_at: run.run_started_at || run.created_at,
    completed_at: run.updated_at,
    status: run.status,
    conclusion: run.conclusion ?? null,
    event: run.event,
    actor: actorKind(run.actor),
    branch: run.head_branch,
  }));
  const days = saturdaysThrough(nowIso);
  const [statuses, edits] = await Promise.all([
    loadStatuses(repo, token, days),
    loadEdits(repo, token, weekly),
  ]);
  return buildScorecard({ now: nowIso, weekly, deploys, statuses, edits });
}

async function main() {
  const card = await loadScorecard();
  console.log(process.argv.includes('--json') ? JSON.stringify(card, null, 2) : toMarkdown(card));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
