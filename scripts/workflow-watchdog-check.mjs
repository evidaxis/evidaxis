// Runner for the class-level workflow watchdog. GitHub Actions remains the
// source of run outcomes; Telegram is the independent delivery channel that
// repeats every six hours until each failed or overdue workflow is green.
import { readdirSync, readFileSync } from 'node:fs';
import { evaluateWorkflowHealth } from './workflow-watchdog.mjs';

const ACTIONS_URL = 'https://github.com/evidaxis/evidaxis/actions';
const WORKFLOW_DIR = '.github/workflows';
const ROSTER = [
  { name: 'liveness-check', kind: 'scheduled', budgetHours: 3 },
  { name: 't2-daily-snapshot', kind: 'scheduled', budgetHours: 36 },
  { name: 'archive-integrity', kind: 'scheduled', budgetHours: 36 },
  { name: 'axis-staleness-check', kind: 'scheduled', budgetHours: 36 },
  { name: 'registry-staleness-check', kind: 'scheduled', budgetHours: 36 },
  { name: 'weekly-snapshot', kind: 'scheduled', budgetHours: 204 },
  { name: 'shadow-observe', kind: 'scheduled', budgetHours: 204 },
  { name: 'shadow-discover', kind: 'scheduled', budgetHours: 840 },
  { name: 'workflow-watchdog', kind: 'scheduled', budgetHours: 13 },
  { name: 'deploy-web', kind: 'event' },
  { name: 'web-ci', kind: 'event' },
  { name: 'python-ci', kind: 'event' },
  { name: 'mirror-push', kind: 'event' },
];

/** @param {string} text */
async function sendTelegram(text) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chat = process.env.ALERT_CHAT_ID;
  if (!token || !chat) {
    console.error('[workflow-watchdog] TELEGRAM_BOT_TOKEN/ALERT_CHAT_ID not set; alert NOT sent');
    return false;
  }
  try {
    const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ chat_id: chat, text, disable_web_page_preview: true }),
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) console.error('[workflow-watchdog] telegram HTTP', res.status);
    return res.ok;
  } catch (e) {
    console.error('[workflow-watchdog] telegram send failed', e);
    return false;
  }
}

/** @param {string} url */
async function githubJson(url) {
  const token = process.env.GH_TOKEN;
  if (!token) throw new Error('GH_TOKEN not set');
  const res = await fetch(url, {
    headers: {
      accept: 'application/vnd.github+json',
      authorization: `Bearer ${token}`,
      'user-agent': 'evidaxis-workflow-watchdog/1',
      'x-github-api-version': '2022-11-28',
    },
    signal: AbortSignal.timeout(15_000),
  });
  if (!res.ok) throw new Error(`GitHub API HTTP ${res.status} for ${url}`);
  return res.json();
}

/** @param {string} path */
function workflowKey(path) {
  return path.split('/').at(-1)?.replace(/\.ya?ml$/, '') ?? '';
}

function unrosteredScheduledWorkflows() {
  const rosterNames = new Set(ROSTER.map((workflow) => workflow.name));
  return readdirSync(WORKFLOW_DIR)
    .filter((file) => file.endsWith('.yml'))
    .filter((file) => /^\s+schedule:\s*(?:#.*)?$/m.test(readFileSync(`${WORKFLOW_DIR}/${file}`, 'utf8')))
    .map((file) => workflowKey(file))
    .filter((name) => !rosterNames.has(name));
}

async function evaluate() {
  const repository = process.env.GITHUB_REPOSITORY;
  if (!repository) throw new Error('GITHUB_REPOSITORY not set');
  const api = `https://api.github.com/repos/${repository}`;
  const listing = await githubJson(`${api}/actions/workflows?per_page=100`);
  const byKey = new Map();
  for (const workflow of listing.workflows ?? []) {
    byKey.set(workflowKey(workflow.path), workflow);
    if (!byKey.has(workflow.name)) byKey.set(workflow.name, workflow);
  }

  const latestCompleted = {};
  const latestSuccess = {};
  for (const item of ROSTER) {
    const workflow = byKey.get(item.name);
    if (!workflow) continue;
    const branch = item.kind === 'event' ? '&branch=main' : '';
    const body = await githubJson(
      `${api}/actions/workflows/${workflow.id}/runs?per_page=15${branch}`,
    );
    const runs = (body.workflow_runs ?? []).filter((run) => run.event !== 'pull_request');
    latestCompleted[item.name] = runs.find((run) => run.status === 'completed');
    latestSuccess[item.name] = runs.find((run) => run.conclusion === 'success');
  }

  const results = evaluateWorkflowHealth({
    roster: ROSTER,
    latestCompleted,
    latestSuccess,
    nowIso: new Date().toISOString(),
  });
  for (const name of unrosteredScheduledWorkflows()) {
    results.push({
      name,
      status: 'missing',
      alert: true,
      message: `${name}: воркфлоу вне надзора, добавьте его в roster.\n${ACTIONS_URL}`,
    });
  }
  return results;
}

if (process.argv.includes('--selftest')) {
  await sendTelegram('🟢 evidaxis · сторож воркфлоу активен (тестовый сигнал)');
  process.exit(0);
}

try {
  const results = await evaluate();
  console.log(JSON.stringify(results));
  const alerts = results.filter((result) => result.alert);
  for (const result of alerts) {
    await sendTelegram(`🔴 evidaxis · сторож воркфлоу\n\n${result.message}`);
  }
  process.exit(alerts.length > 0 ? 1 : 0);
} catch (e) {
  console.error('[workflow-watchdog] evaluation failed', e);
  await sendTelegram(
    `🔴 evidaxis · сторож воркфлоу\n\nПроверка исходов не состоялась: ${e.message}.\n${ACTIONS_URL}`,
  );
  process.exit(1);
}
