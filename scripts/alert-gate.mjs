// Shared repeat gate for every Telegram push to the keeper (2026-09-26).
//
// The keeper's rule, verbatim: "only the critical should arrive, and written so I
// understand what to do with it". Six identical "python-ci failure" pushes a day and
// a 30-minute liveness cron that would repeat one outage 48 times a day both broke it.
// So: a NEW problem is pushed at once; the SAME problem is repeated at most once a
// day, in the morning reminder window. Everything else stays in the run log (pull).
//
// Stateless by design: "new" is read from GitHub itself (the previous completed run
// of the same workflow), not from a cache that could silently drift. Fails CLOSED:
// if the previous outcome cannot be read, the push goes out.

/** UTC hour whose first half-hour carries the once-a-day reminder (07:00–07:30 London). */
export const REMINDER_HOUR_UTC = 6;

/** @param {string} nowIso */
export function inReminderWindow(nowIso) {
  const now = new Date(nowIso);
  if (Number.isNaN(now.getTime())) return true;
  return now.getUTCHours() === REMINDER_HOUR_UTC && now.getUTCMinutes() < 30;
}

/**
 * @param {{ previousConclusion: string|null|undefined, nowIso: string }} i
 * `previousConclusion` — conclusion of the previous completed run of this workflow,
 * null when unknown. A red previous run means this problem was already pushed.
 */
export function shouldPush(i) {
  const repeat = Boolean(i.previousConclusion) && i.previousConclusion !== 'success';
  return !repeat || inReminderWindow(i.nowIso);
}

/**
 * Conclusion of the previous completed run of the workflow this job belongs to.
 * Needs GH_TOKEN with `actions: read`. Returns null on any failure (fail closed).
 */
export async function previousConclusion() {
  const token = process.env.GH_TOKEN;
  const repo = process.env.GITHUB_REPOSITORY;
  const runId = process.env.GITHUB_RUN_ID;
  if (!token || !repo || !runId) return null;
  const headers = {
    accept: 'application/vnd.github+json',
    authorization: `Bearer ${token}`,
    'user-agent': 'evidaxis-alert-gate/1',
    'x-github-api-version': '2022-11-28',
  };
  try {
    const api = `https://api.github.com/repos/${repo}/actions`;
    const run = await fetch(`${api}/runs/${runId}`, { headers, signal: AbortSignal.timeout(10_000) });
    if (!run.ok) return null;
    const { workflow_id: workflowId } = await run.json();
    const list = await fetch(`${api}/workflows/${workflowId}/runs?status=completed&per_page=5`, {
      headers,
      signal: AbortSignal.timeout(10_000),
    });
    if (!list.ok) return null;
    const body = await list.json();
    const previous = (body.workflow_runs ?? []).find((r) => String(r.id) !== String(runId));
    return previous?.conclusion ?? null;
  } catch {
    return null;
  }
}
