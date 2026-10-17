// Run identity is shared with weekly-snapshot and the release observer.
export function tick(cron, scheduledTime) {
  const day = new Date(scheduledTime);
  if (!Number.isFinite(day.getTime())) throw new Error('invalid scheduled time');
  const rehearsal = cron === '17 2 * * WED';
  if (!rehearsal && !['17 2 * * SAT', '17 4 * * SAT', '47 6 * * SAT'].includes(cron)) {
    throw new Error('unknown cron');
  }
  if (day.getUTCDay() !== (rehearsal ? 3 : 6)) throw new Error('cron weekday mismatch');
  if (rehearsal) day.setUTCDate(day.getUTCDate() + 3);
  return { mode: rehearsal ? 'rehearsal' : 'release', release_date: day.toISOString().slice(0, 10) };
}

export function findRuns(runs, inputs, ref) {
  if (!Array.isArray(runs)) throw new Error('unknown GitHub run state');
  return runs.filter(run => run.display_title === `weekly ${inputs.mode} ${inputs.release_date}`
    && run.head_branch === ref);
}

export function needsDispatch(runs, inputs, ref) {
  return !findRuns(runs, inputs, ref).some(run =>
    run.status !== 'completed' || run.conclusion === 'success' || !run.conclusion);
}

export function validDispatchToken(token) {
  return typeof token === 'string' && token.length > 0 && !/[^A-Za-z0-9_]/.test(token);
}
