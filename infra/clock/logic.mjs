// Run identity is shared with weekly-snapshot and the release observer.
const RELEASE_CRONS = ['17 2 * * SAT', '17 4 * * SAT', '47 6 * * SAT'];

export function tick(cron, scheduledTime) {
  const day = scheduledDay(scheduledTime);
  const offset = cron === '17 2 * * WED' ? 3 : cron === '17 2 * * FRI' ? 1 : 0;
  if (!offset && !RELEASE_CRONS.includes(cron)) throw new Error('unknown cron');
  const weekday = cron === '17 2 * * FRI' ? 5 : cron === '17 2 * * WED' ? 3 : 6;
  if (day.getUTCDay() !== weekday) throw new Error('cron weekday mismatch');
  if (offset) day.setUTCDate(day.getUTCDate() + offset);
  return { mode: offset ? 'rehearsal' : 'release', release_date: day.toISOString().slice(0, 10) };
}

// Friday shares Wednesday's `weekly rehearsal <Saturday>` title.
// Only runs created on this tick's UTC day count. Other ticks keep full history.
export function createdOnOrAfter(cron, scheduledTime) {
  if (cron !== '17 2 * * FRI') return undefined;
  const day = scheduledDay(scheduledTime);
  return Date.UTC(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate());
}

function scheduledDay(scheduledTime) {
  const day = new Date(scheduledTime);
  if (!Number.isFinite(day.getTime())) throw new Error('invalid scheduled time');
  return day;
}

export function findRuns(runs, inputs, ref, since) {
  if (!Array.isArray(runs)) throw new Error('unknown GitHub run state');
  return runs.filter(run => {
    if (run.display_title !== `weekly ${inputs.mode} ${inputs.release_date}` || run.head_branch !== ref) return false;
    if (since == null) return true;
    const created = Date.parse(run.created_at);
    // A missing timestamp cannot tell Friday from Wednesday. Skipping it would dispatch blind.
    if (!Number.isFinite(created)) throw new Error('incomplete data');
    return created >= since;
  });
}

export function needsDispatch(runs, inputs, ref, since) {
  return !findRuns(runs, inputs, ref, since).some(run =>
    run.status !== 'completed' || run.conclusion === 'success' || !run.conclusion);
}

export function validDispatchToken(token) {
  return typeof token === 'string' && token.length > 0 && !/[^A-Za-z0-9_]/.test(token);
}
