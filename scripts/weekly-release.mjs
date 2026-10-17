// Shared release identity for both sensors. A successful no-op is not recovery.
export const COLLECT_STEP = 'Collect snapshot (keyed OpenAlex; capture pass + completeness gate)';

export function weeklyReleaseDay(nowIso) {
  const now = new Date(nowIso);
  if (Number.isNaN(now.getTime())) return null;
  now.setUTCDate(now.getUTCDate() - (now.getUTCDay() + 1) % 7);
  return now.toISOString().slice(0, 10);
}

export function releaseRunDate(run) {
  if (run?.head_branch !== 'main' || run.event === 'pull_request') return null;
  const title = run.display_title;
  const dated = /^weekly release (\d{4}-\d{2}-\d{2})$/.exec(title ?? '');
  if (dated) return dated[1];
  // Only old workflows lack run-name. Current manual and scheduled entries always
  // say `weekly release resolve-date`; routers and rehearsals never count here.
  return title === 'weekly-snapshot' ? weeklyReleaseDay(run.created_at) : null;
}

export function releaseRunKind(run) {
  if (!releaseRunDate(run)) return 'ignore';
  if (run.display_title === 'weekly-snapshot' || run.conclusion !== 'success') return 'release';
  // Job outputs are not exposed by REST. On a successful dated run, guard.skip
  // makes the snapshot job (first guard) or its collection step (second guard)
  // skipped. Jobs API exposes both conclusions, including for the backup cron.
  // Failed preflight/guard runs remain failures; missing job evidence is unknown.
  const job = run.jobs?.find(job => job.name === 'snapshot');
  if (job?.conclusion === 'skipped') return 'ignore';
  const collect = job?.steps?.find(step => step.name === COLLECT_STEP);
  if (collect?.conclusion === 'skipped') return 'ignore';
  return collect?.conclusion === 'success' ? 'release' : 'unknown';
}

export async function attachReleaseJobs(runs, getJobs) {
  await Promise.all(runs.map(async run => {
    if (releaseRunKind(run) !== 'unknown') return;
    try {
      const body = await getJobs(run.id);
      if (Array.isArray(body.jobs) && Number.isInteger(body.total_count) && body.jobs.length === body.total_count) {
        run.jobs = body.jobs;
      }
    } catch {
      // An unreadable or incomplete Jobs response cannot turn a no-op into success.
    }
  }));
}
