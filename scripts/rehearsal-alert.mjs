// Text and send path for one failed Saturday rehearsal. Drills do not use this.
import { pathToFileURL } from 'node:url';
import { sendTelegram } from './telegram.mjs';

/**
 * @param {{ date: string, step: string, runUrl: string }} input
 * @returns {string}
 */
export function rehearsalFailureText(input) {
  return (
    `Репетиция субботы ${input.date} упала на шаге «${input.step}». ` +
    `Выпуск не задет; до субботы есть время починить. ${input.runUrl}`
  );
}

/** First failed step name from a GitHub Actions jobs payload, or ''. */
export function failedStepName(payload) {
  const jobs = Array.isArray(payload) ? payload : (payload && payload.jobs) || [];
  for (const job of jobs) {
    for (const step of (job && job.steps) || []) {
      if (step && step.conclusion === 'failure' && step.name) return step.name;
    }
  }
  return '';
}

/**
 * @param {{ date: string, jobs: unknown, runUrl: string }} input
 * @returns {string}
 */
export function rehearsalAlertText(input) {
  return rehearsalFailureText({
    date: input.date,
    step: failedStepName(input.jobs) || 'неизвестен',
    runUrl: input.runUrl,
  });
}

async function loadJobs() {
  const token = process.env.GH_TOKEN;
  const repo = process.env.GITHUB_REPOSITORY;
  const runId = process.env.GITHUB_RUN_ID;
  const attempt = process.env.GITHUB_RUN_ATTEMPT || '1';
  if (!token || !repo || !runId) return null;
  const url = `https://api.github.com/repos/${repo}/actions/runs/${runId}/attempts/${attempt}/jobs?per_page=100`;
  const res = await fetch(url, {
    headers: {
      accept: 'application/vnd.github+json',
      authorization: `Bearer ${token}`,
      'user-agent': 'evidaxis-rehearsal-alert/1',
      'x-github-api-version': '2022-11-28',
    },
    signal: AbortSignal.timeout(10_000),
  });
  if (!res.ok) return null;
  return res.json();
}

async function main() {
  const date = process.env.SNAPSHOT_DATE || '';
  const server = process.env.GITHUB_SERVER_URL || 'https://github.com';
  const repo = process.env.GITHUB_REPOSITORY || '';
  const runId = process.env.GITHUB_RUN_ID || '';
  const runUrl = `${server}/${repo}/actions/runs/${runId}`;
  let jobs = null;
  try {
    jobs = await loadJobs();
  } catch {
    jobs = null;
  }
  const text = rehearsalAlertText({ date, jobs, runUrl });
  console.log(text);
  const sent = await sendTelegram(text, 'rehearsal');
  if (!sent && process.env.TELEGRAM_BOT_TOKEN && process.env.ALERT_CHAT_ID) process.exit(1);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
