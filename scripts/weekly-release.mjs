// Release outcomes belong to the snapshot commit. Actions only describes work
// still in flight; a completed run cannot establish or repair publication.
export const RELEASE_CONTEXTS = ['captured', 'deployed', 'hf'];
export const ACTIVE_RUN_STATES = ['queued', 'in_progress', 'pending', 'waiting', 'requested'];

export function weeklyReleaseDay(nowIso) {
  if (typeof nowIso !== 'string') return null;
  const now = new Date(nowIso);
  if (Number.isNaN(now.getTime())) return null;
  now.setUTCDate(now.getUTCDate() - (now.getUTCDay() + 1) % 7);
  return now.toISOString().slice(0, 10);
}

export function isInFlight(run) {
  return ACTIVE_RUN_STATES.includes(run?.status);
}

export function isWeeklyRelease(run, date) {
  return isInFlight(run) && run.head_branch === 'main' && run.event !== 'pull_request' &&
    run.display_title === `weekly release ${date}`;
}

// The combined-status endpoint supplies the latest value of each context.
export function releaseStatuses(body, date) {
  if (!Array.isArray(body?.statuses) || !Number.isInteger(body.total_count) ||
      body.total_count !== body.statuses.length) throw new Error('Incomplete commit statuses');
  const statuses = {};
  for (const status of body.statuses) {
    if (typeof status?.context !== 'string') throw new Error('Invalid commit status');
    const stage = RELEASE_CONTEXTS.find(name => status.context === `evidaxis/release-${name}`);
    if (!stage) continue;
    if (statuses[stage] || !['success', 'failure', 'error', 'pending'].includes(status.state) ||
        typeof status.description !== 'string' || !status.description.trim()) {
      throw new Error('Invalid release status');
    }
    if (stage === 'captured' && status.state === 'success' && status.description !== date) {
      throw new Error('Captured date mismatch');
    }
    statuses[stage] = status;
  }
  return statuses;
}

/** Pure truth table; errors precede all results, including apparent success. */
export function evaluateWeeklyRelease(i) {
  const week = weeklyReleaseDay(i.nowIso);
  const verdict = (status, alert, message = '', remind = false, since) => ({
    status, alert, message, remind, week, key: `${week ?? 'unknown'}:${['running', 'publishing'].includes(status) ? 'active' : status}`, ...(since ? { since } : {}),
  });
  const unknown = detail => verdict('unknown', true,
    `Не могу проверить выпуск ${week ?? ''}: ${detail}. Нужен человек: нет, проверю в следующий раз.`, true);
  if (!week || i.apiError) return unknown(i.apiError || 'некорректное время проверки');
  if (!i.record || i.record.date !== week || !(i.record.sha === null || /^[a-f0-9]{40}$/.test(i.record.sha))) return unknown('нет записи выпуска');
  let statuses;
  try { statuses = releaseStatuses(i.record, week); } catch (error) { return unknown(error.message); }
  if (!i.record.sha && Object.keys(statuses).length) return unknown('статусы без коммита среза');
  const failed = RELEASE_CONTEXTS.find(stage => ['failure', 'error'].includes(statuses[stage]?.state));
  if (failed) {
    const status = statuses[failed];
    return verdict('failed', true,
      `Срез ${week} не вышел: этап ${failed}, шаг «${status.description}». Нужен человек: да.`,
      true, status.updated_at);
  }
  const missing = RELEASE_CONTEXTS.filter(stage => statuses[stage]?.state !== 'success');
  if (!missing.length) return verdict('released', true,
    `✅ Срез ${week} на сайте и HF: обе квитанции подтверждены. Нужен человек: нет.`);
  if (typeof i.active !== 'boolean') return unknown('не удалось проверить активный запуск');
  // Preserve the existing Saturday 12:00 UTC notification deadline.
  const deadline = `${week}T12:00:00Z`;
  const late = Date.parse(i.nowIso) >= Date.parse(deadline);
  if (i.active) {
    const state = missing.includes('captured') ? 'running' : 'publishing';
    return verdict(state, late, late
      ? `Срез ${week} опаздывает, но идёт: ${state === 'running' ? 'сбор' : 'публикация'}. Нужен человек: нет.` : '');
  }
  if (!i.record.sha) return verdict('not_started', late, late
    ? `Срез ${week} не стартовал к 12:00 UTC: коммита среза нет. Нужен человек: да. https://github.com/evidaxis/evidaxis/actions/workflows/weekly-snapshot.yml`
    : '', late, deadline);
  if (!late) return verdict(missing.includes('captured') ? 'running' : 'publishing', false);
  return verdict('failed', true,
    `Срез ${week} не вышел: не дошло до этапа ${missing.join(', ')}. Нужен человек: да.`, true, deadline);
}
