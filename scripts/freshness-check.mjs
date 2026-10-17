// Runner for the publication-freshness sensor. Reads the newest snapshot the
// committed tree holds (data/latest.json), asks the live host for that exact
// snapshot, asks GitHub whether this Saturday's release is running, late,
// failed, or out, and pings Telegram only for a new state of that release.
// Runs under plain `node` — no npm install (see freshness.mjs).
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { attachReleaseJobs, releaseRunDate } from './weekly-release.mjs';
import { previousConclusion, shouldPush } from './alert-gate.mjs';
import {
  decideFeedPush,
  decideWeeklyPush,
  evaluateFeedFreshness,
  evaluateFreshness,
  evaluateWeeklyRelease,
  gateFreshnessAlerts,
  parseFeedKey,
  parseReleaseKey,
  pickFailedStep,
  releaseKeyToPrint,
  weeklyReleaseDay,
} from './freshness.mjs';

const API = 'https://api.github.com';
// 100 is the GitHub page cap, so Saturday's run is still listed after a week of deploys.
const GH_PAGE = 100;

/** @param {string} url */
async function probe(url) {
  try {
    const res = await fetch(url, {
      redirect: 'follow',
      headers: { 'user-agent': 'freshness-sensor/1', 'cache-control': 'no-cache' },
      signal: AbortSignal.timeout(12_000),
    });
    return { reached: true, status: res.status };
  } catch {
    return { reached: false, status: 0 };
  }
}

/** @param {string} url */
async function probeFeed(url) {
  try {
    const res = await fetch(url, {
      redirect: 'follow',
      headers: { 'user-agent': 'freshness-sensor/1', 'cache-control': 'no-cache' },
      signal: AbortSignal.timeout(12_000),
    });
    let latestEntryAt = null;
    if (res.ok) {
      const body = await res.json().catch(() => null);
      latestEntryAt = body?.items?.[0]?.date_published ?? null;
    }
    return { reached: true, status: res.status, latestEntryAt };
  } catch {
    return { reached: false, status: 0, latestEntryAt: null };
  }
}

/** @param {string} text */
async function sendTelegram(text) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chat = process.env.ALERT_CHAT_ID;
  if (!token || !chat) {
    console.error('[freshness] TELEGRAM_BOT_TOKEN/ALERT_CHAT_ID not set — alert NOT sent');
    return false;
  }
  try {
    const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ chat_id: chat, text, disable_web_page_preview: true }),
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) console.error('[freshness] telegram HTTP', res.status);
    return res.ok;
  } catch (e) {
    console.error('[freshness] telegram send failed', e);
    return false;
  }
}

/** @returns {Record<string, string>|null} */
function ghHeaders() {
  const token = process.env.GH_TOKEN;
  if (!token) return null;
  return {
    accept: 'application/vnd.github+json',
    authorization: `Bearer ${token}`,
    'user-agent': 'freshness-sensor/1',
    'x-github-api-version': '2022-11-28',
  };
}

/** @param {unknown} error */
function githubError(error) {
  const name = error && typeof error === 'object' && 'name' in error ? String(error.name) : '';
  if (name === 'TimeoutError' || name === 'AbortError') return 'таймаут';
  return 'сбой сети';
}

/** @param {string} workflowFile @returns {Promise<{ runs?: object[], error?: string }>} */
async function workflowRuns(workflowFile, week) {
  const repo = process.env.GITHUB_REPOSITORY;
  const headers = ghHeaders();
  if (!headers || !repo) return { error: 'нет GH_TOKEN или GITHUB_REPOSITORY' };
  const url = `${API}/repos/${repo}/actions/workflows/${workflowFile}/runs?per_page=${GH_PAGE}&branch=main`;
  try {
    const res = await fetch(url, { headers, signal: AbortSignal.timeout(10_000) });
    if (!res.ok) return { error: `HTTP ${res.status}` };
    const body = await res.json();
    if (!Array.isArray(body.workflow_runs) || !Number.isInteger(body.total_count)) return { error: 'неполный список запусков' };
    if (body.workflow_runs.some(run => !run || !Number.isFinite(Date.parse(run.created_at)) ||
        typeof run.display_title !== 'string' || typeof run.head_branch !== 'string' || typeof run.status !== 'string')) {
      return { error: 'некорректные сведения о запуске' };
    }
    const oldest = body.workflow_runs.at(-1)?.created_at;
    if (body.total_count > body.workflow_runs.length && (!oldest || oldest.slice(0, 10) >= week)) {
      return { error: 'неполный список запусков субботы' };
    }
    const runs = body.workflow_runs.map((run) => ({
      id: run.id,
      status: run.status,
      conclusion: run.conclusion,
      created_at: run.created_at,
      run_started_at: run.run_started_at,
      updated_at: run.updated_at,
      html_url: run.html_url,
      event: run.event,
      display_title: run.display_title,
      head_branch: run.head_branch,
    }));
    return { runs };
  } catch (error) {
    return { error: githubError(error) };
  }
}

/** @param {object[]} runs @param {number} weekStart */
async function attachFailedSteps(runs, weekStart) {
  const headers = ghHeaders();
  const repo = process.env.GITHUB_REPOSITORY;
  if (!headers || !repo) return;
  await Promise.all(runs.map(async (run) => {
    if (!['failure', 'cancelled', 'timed_out'].includes(run.conclusion)) return;
    const created = Date.parse(run.created_at ?? '');
    if (Number.isNaN(created) || created < weekStart) return;
    try {
      const url = `${API}/repos/${repo}/actions/runs/${run.id}/jobs?per_page=${GH_PAGE}`;
      const res = await fetch(url, { headers, signal: AbortSignal.timeout(10_000) });
      if (!res.ok) return;
      const body = await res.json();
      const step = pickFailedStep(body.jobs);
      if (step) run.failedStep = step;
    } catch {
      // The failure is still reportable without the step name.
    }
  }));
}

/** @param {string} jobId @param {Record<string, string>} headers */
async function jobLog(jobId, headers) {
  const repo = process.env.GITHUB_REPOSITORY;
  const res = await fetch(`${API}/repos/${repo}/actions/jobs/${jobId}/logs`, {
    headers,
    redirect: 'manual',
    signal: AbortSignal.timeout(10_000),
  });
  if (res.status >= 300 && res.status < 400) {
    const location = res.headers.get('location');
    if (!location) return '';
    // The log host rejects the GitHub bearer token, so the second fetch is unsigned.
    const file = await fetch(new URL(location, res.url), { signal: AbortSignal.timeout(10_000) });
    if (!file.ok) return '';
    return file.text();
  }
  if (!res.ok) return '';
  return res.text();
}

/** Keys of the last release and feed messages this workflow actually sent. Nulls if a log cannot be read. */
async function previousSensorKeys() {
  const headers = ghHeaders();
  const repo = process.env.GITHUB_REPOSITORY;
  const runId = process.env.GITHUB_RUN_ID;
  const empty = { release: null, feed: null };
  if (!headers || !repo || !runId) return empty;
  try {
    const api = `${API}/repos/${repo}/actions`;
    const runRes = await fetch(`${api}/runs/${runId}`, { headers, signal: AbortSignal.timeout(10_000) });
    if (!runRes.ok) return empty;
    const { workflow_id: workflowId } = await runRes.json();
    const listRes = await fetch(`${api}/workflows/${workflowId}/runs?status=completed&per_page=5`, {
      headers,
      signal: AbortSignal.timeout(10_000),
    });
    if (!listRes.ok) return empty;
    const body = await listRes.json();
    const previous = (body.workflow_runs ?? []).find((run) => String(run.id) !== String(runId));
    if (!previous) return empty;
    const jobsRes = await fetch(`${api}/runs/${previous.id}/jobs?per_page=${GH_PAGE}`, {
      headers,
      signal: AbortSignal.timeout(10_000),
    });
    if (!jobsRes.ok) return empty;
    const jobsBody = await jobsRes.json();
    let release = null;
    let feed = null;
    for (const job of jobsBody.jobs ?? []) {
      const text = await jobLog(job.id, headers);
      if (!release) release = parseReleaseKey(text);
      if (!feed) feed = parseFeedKey(text);
      if (release && feed) break;
    }
    return { release, feed };
  } catch {
    return empty;
  }
}

/** Whether data/snapshots/D/snapshot.json is on main right now. @param {string|null} date @returns {Promise<'present'|'absent'|'unknown'>} */
async function snapshotOnMain(date) {
  const repo = process.env.GITHUB_REPOSITORY;
  const headers = ghHeaders();
  if (!headers || !repo || !date) return 'unknown';
  const url = `${API}/repos/${repo}/contents/data/snapshots/${date}/snapshot.json?ref=main`;
  try {
    const res = await fetch(url, { headers, signal: AbortSignal.timeout(10_000) });
    const status = res.status;
    await res.body?.cancel().catch(() => {});
    if (status === 200) return 'present';
    if (status === 404) return 'absent';
    return 'unknown';
  } catch {
    return 'unknown';
  }
}

async function snapshotOnSite(site, date) {
  try {
    const res = await fetch(`${site}/snapshots/${date}/snapshot.json`, {
      redirect: 'follow',
      headers: { 'user-agent': 'freshness-sensor/1', 'cache-control': 'no-cache' },
      signal: AbortSignal.timeout(12_000),
    });
    if (res.status === 404) return 'absent';
    if (res.status !== 200) return 'unknown';
    const body = await res.json();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(body?.snapshot_date ?? '')) return 'unknown';
    return body.snapshot_date === date ? 'present' : 'absent';
  } catch {
    return 'unknown';
  }
}

export async function readWeeklyFacts(site, nowIso) {
  const week = weeklyReleaseDay(nowIso);
  const [weekly, deploy, main, publicSnapshot] = await Promise.all([
    workflowRuns('weekly-snapshot.yml', week),
    workflowRuns('deploy-web.yml', week),
    snapshotOnMain(week),
    // latest.json may already point at Sunday; Saturday publication is a separate fact.
    snapshotOnSite(site, week),
  ]);
  const weeklyRuns = weekly.runs ?? [];
  const deployRuns = deploy.runs ?? [];
  await attachReleaseJobs(weeklyRuns.filter(run => releaseRunDate(run) === week), async id => {
    const res = await fetch(`${API}/repos/${process.env.GITHUB_REPOSITORY}/actions/runs/${id}/jobs?per_page=${GH_PAGE}`,
      { headers: ghHeaders(), signal: AbortSignal.timeout(10_000) });
    if (!res.ok) throw new Error('Jobs API unavailable');
    return res.json();
  });
  const weekStart = Date.parse(`${week}T00:00:00Z`);
  await Promise.all([attachFailedSteps(weeklyRuns, weekStart), attachFailedSteps(deployRuns, weekStart)]);
  return { nowIso, weeklyRuns, deployRuns, snapshotOnMain: main, snapshotOnSite: publicSnapshot,
    apiError: [weekly.error, deploy.error].filter(Boolean).join('; ') };
}

async function main() {
  const site = (process.env.SITE_URL || '').replace(/\/+$/, '');
  const label = process.env.SITE_LABEL || site;
  const latestPath = process.env.LATEST_JSON || 'data/latest.json';
  if (!site) {
    console.error('[freshness] SITE_URL not set');
    process.exit(2);
  }

  let snapshotDate;
  try {
    snapshotDate = JSON.parse(readFileSync(latestPath, 'utf8')).snapshot_date;
  } catch (e) {
    // A missing or broken pointer file is itself a publication defect: nothing
    // downstream can know what prod is supposed to be serving.
    console.error(`[freshness] cannot read ${latestPath}`, e);
    process.exit(2);
  }

  const url = `${site}/snapshots/${snapshotDate}/snapshot.json`;
  const p = await probe(url);
  const now = new Date();
  const nowIso = now.toISOString();
  const result = evaluateFreshness({ site, snapshotDate, now, ...p });
  const feedUrl = `${site}/feed.json`;
  const feedProbe = await probeFeed(feedUrl);
  const feedResult = evaluateFeedFreshness({ site, now, ...feedProbe });

  const [weeklyFacts, previousKeys] = await Promise.all([
    readWeeklyFacts(site, nowIso),
    previousSensorKeys(),
  ]);
  const release = evaluateWeeklyRelease(weeklyFacts);
  const gated = gateFreshnessAlerts({
    archiveDate: snapshotDate,
    release,
    snapshot: result,
    feed: feedResult,
  });
  const prevConclusion = (release.alert || gated.snapshot)
    ? await previousConclusion()
    : null;
  const previousKey = previousKeys.release;
  const decision = decideWeeklyPush({
    release,
    previousKey,
    previousConclusion: prevConclusion,
    nowIso,
  });
  const feedDecision = decideFeedPush({
    alert: gated.feed,
    key: `feed:${feedResult.reason || 'stale'}`,
    previousKey: previousKeys.feed,
    nowIso,
  });

  console.log(JSON.stringify({
    snapshot: { url, snapshotDate, httpStatus: p.status, ...result },
    feed: { url: feedUrl, httpStatus: feedProbe.status, latestEntryAt: feedProbe.latestEntryAt, ...feedResult },
    release,
    label,
  }));

  const parts = [];
  if (decision.push && release.message) parts.push(release.message);
  if (feedDecision.push && feedResult.message) parts.push(feedResult.message);
  const legacy = gated.snapshot && shouldPush({ previousConclusion: prevConclusion, nowIso });
  if (legacy) {
    parts.push(
      `🟠 На сайте Evidaxis не обновились данные: посетители видят устаревший снимок.\n` +
        `Что сделать: открой чат по Evidaxis и скажи «данные на сайте не обновились, почини».`,
    );
  }

  // A failed send must not consume the key, or the next run would treat a message the keeper never got as delivered.
  let sent = false;
  if (parts.length) {
    sent = await sendTelegram(parts.join('\n\n'));
  } else if ((release.alert && release.remind) || gated.snapshot || gated.feed) {
    console.log('[freshness] (тихо · повтор) уже отправлено, напоминание — утром');
  } else if (release.alert) {
    console.log(`[freshness] состояние ${release.key} уже сообщено`);
  }
  const notifiedKey = releaseKeyToPrint({
    push: decision.push,
    notifiedKey: decision.notifiedKey,
    previousKey,
    sent,
  });
  const feedKey = gated.feed
    ? releaseKeyToPrint({
      push: feedDecision.push,
      notifiedKey: feedDecision.notifiedKey,
      previousKey: previousKeys.feed,
      sent,
    })
    : '';
  console.log(`RELEASE_KEY ${notifiedKey || '-'}`);
  console.log(`FEED_KEY ${feedKey || '-'}`);

  // Human-needed states keep the run red so alert-gate repeats them at most once a day.
  // Late-but-moving and the receipt stay green: the keeper was told nobody is needed.
  const fail = decision.exitCode === 1 || feedDecision.exitCode === 1 || gated.snapshot;
  process.exit(fail ? 1 : 0);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main();
