// Shared release identity for both sensors. A successful no-op is not recovery.
export const COLLECT_STEP = 'Collect snapshot (keyed OpenAlex; capture pass + completeness gate)';
const BAD = new Set(['failure', 'cancelled', 'timed_out']);
const IN_FLIGHT = new Set(['queued', 'in_progress', 'waiting', 'pending', 'requested']);

export function isInFlight(run) {
  return Boolean(run) && IN_FLIGHT.has(run.status) && !run.conclusion;
}

export function attemptTime(run) {
  if ((run.run_attempt ?? 1) > 1 && !run.run_started_at) return Number.NaN;
  return Date.parse(run.run_started_at || run.created_at || '');
}

export function allAttemptsBefore(run, startMs) {
  // The latest attempt bounds all earlier ones. Unknown start times cannot
  // exclude a rerun: its unchanged created_at may belong to a previous week.
  return attemptTime(run) < startMs;
}

// GitHub keeps created_at and ID on rerun; use the attempt's start in both sensors.
export function compareAttempts(a, b) {
  return attemptTime(b) - attemptTime(a) ||
    (b.run_attempt ?? 1) - (a.run_attempt ?? 1) || Number(b.id) - Number(a.id);
}

export function supersedesFailure(candidate, failure) {
  if (compareAttempts(candidate, failure) >= 0) return false;
  if (!failure.retainedFailure) return isInFlight(candidate) || candidate.conclusion === 'success';
  // Starting another run or collecting again does not repair the failed delivery.
  return candidate.conclusion === 'success' && releaseRunDate(candidate) === releaseRunDate(failure) &&
    failure.unrecoveredSteps.every(({ job, step }) => candidate.jobs?.some(value => value.name === job &&
      value.steps?.some(value => value.name === step && value.conclusion === 'success')));
}

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
  if (run.attemptEvidenceUnknown) return 'unknown';
  if (run.recoveryVerified) return 'release';
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

// Keep unresolved failed steps across attempts, including several green skips.
// A job's green conclusion alone proves nothing: its previously failed step must
// be success in a later attempt-specific Jobs response. No latest/all job mixing.
export function effectiveRun(run) {
  const count = run.run_attempt ?? 1;
  if (count < 2) return run;
  const unknown = () => ({ ...run, attemptEvidenceUnknown: true });
  if (!Array.isArray(run.attempts) || run.attempts.length !== count) return unknown();
  const pending = new Map();
  let meaningful;
  for (const attempt of run.attempts) {
    if (!Array.isArray(attempt.jobs)) return unknown();
    let recovered = false;
    let failed = false;
    for (const job of attempt.jobs) {
      const steps = job.steps ?? [];
      if (BAD.has(job.conclusion) && !steps.some(step => BAD.has(step.conclusion))) return unknown();
      for (const step of steps) {
        const key = JSON.stringify([job.name, step.name]);
        if (step.conclusion === 'success') recovered = pending.delete(key) || recovered;
        if (BAD.has(step.conclusion)) {
          pending.set(key, { attempt, job: job.name, step: step.name });
          failed = true;
        }
      }
    }
    if (BAD.has(attempt.conclusion) && !failed) return unknown();
    const observed = { ...attempt, recoveryVerified: recovered && pending.size === 0 && attempt.conclusion === 'success' };
    // A later no-op also must not refresh the age of an earlier real success.
    const ignored = releaseRunDate(observed)
      ? releaseRunKind(observed) === 'ignore'
      : observed.conclusion === 'skipped';
    if (!ignored) meaningful = observed;
  }
  if (pending.size) {
    const unresolved = [...pending.values()];
    const { attempt, step } = unresolved.sort((a, b) => compareAttempts(a.attempt, b.attempt))[0];
    return { ...attempt, failedStep: step, retainedFailure: true,
      unrecoveredSteps: unresolved.map(({ job, step }) => ({ job, step })) };
  }
  return meaningful ?? run.attempts.at(-1);
}

export async function attachReleaseJobs(runs, getJobs, getAttempt) {
  async function jobs(id, number) {
    const body = await getJobs(id, number);
    if (!Array.isArray(body.jobs) || !Number.isInteger(body.total_count) || body.jobs.length !== body.total_count ||
        body.jobs.some(job => job.run_attempt != null && job.run_attempt !== number)) {
      throw new Error('Incomplete or mismatched attempt jobs');
    }
    return body.jobs;
  }
  await Promise.all(runs.map(async run => {
    const count = run.run_attempt ?? 1;
    // A new successful deploy can repair another run's retained failure; both
    // sensors need its step evidence even though it has no weekly release title.
    if (count === 1 && run.conclusion !== 'success' && releaseRunKind(run) !== 'unknown') return;
    try {
      if (count === 1) {
        run.jobs = await jobs(run.id, 1);
        return;
      }
      const attempts = [];
      for (let number = 1; number <= count; number++) {
        const attempt = number === count ? { ...run } : await getAttempt(run.id, number);
        if (attempt.id !== run.id || attempt.run_attempt !== number || !Number.isFinite(attemptTime(attempt)) ||
            typeof attempt.status !== 'string' || (attempt.status === 'completed' && typeof attempt.conclusion !== 'string') ||
            (number < count && attempt.status !== 'completed')) {
          throw new Error('Mismatched workflow attempt');
        }
        attempts.push({ ...attempt, jobs: await jobs(run.id, number) });
      }
      run.attempts = attempts;
    } catch {
      // Missing attempt history is unknown; it cannot erase a previous HF/deploy failure.
      if (count > 1) delete run.attempts;
    }
  }));
}
