// Pure workflow-health evaluator for the class-level watchdog. The runner owns
// GitHub and Telegram I/O; this module only decides whether every rostered
// workflow is green and, for scheduled workflows, recently successful.

/** @typedef {'ok'|'red'|'stale'|'missing'} WorkflowStatus */

const ACTIONS_URL = 'https://github.com/evidaxis/evidaxis/actions';
const HOUR_MS = 3600_000;

/** @param {Map<string, object>|Record<string, object>} runs @param {string} name */
function runFor(runs, name) {
  return runs instanceof Map ? runs.get(name) : runs?.[name];
}

/** @param {object} run */
function runTime(run) {
  return run.completed_at ?? run.updated_at ?? run.created_at ?? '';
}

/** @param {number} hours */
function ageText(hours) {
  const safeHours = Math.max(0, Math.floor(hours));
  const days = (safeHours / 24).toFixed(1);
  return `${safeHours} ч (${days} дн.)`;
}

/**
 * @param {{
 *   roster: Array<{name: string, kind: 'scheduled'|'event', budgetHours?: number}>,
 *   latestCompleted: Map<string, object>|Record<string, object>,
 *   latestSuccess: Map<string, object>|Record<string, object>,
 *   nowIso: string,
 * }} i
 * @returns {Array<{name: string, status: WorkflowStatus, alert: boolean, message: string}>}
 */
export function evaluateWorkflowHealth(i) {
  const now = Date.parse(i.nowIso);

  return i.roster.map((workflow) => {
    const completed = runFor(i.latestCompleted, workflow.name);
    if (!completed) {
      return {
        name: workflow.name,
        status: 'missing',
        alert: true,
        message:
          `${workflow.name}: нет завершённых запусков; воркфлоу вне надзора.\n` +
          ACTIONS_URL,
      };
    }

    if (completed.conclusion !== 'success') {
      const conclusion = completed.conclusion ?? 'без результата';
      return {
        name: workflow.name,
        status: 'red',
        alert: true,
        message:
          `${workflow.name}: последний запуск завершился с результатом «${conclusion}». ` +
          `Сигнал повторится, пока воркфлоу не станет зелёным.\n${ACTIONS_URL}`,
      };
    }

    if (workflow.kind === 'scheduled') {
      const success = runFor(i.latestSuccess, workflow.name);
      const succeededAt = success ? Date.parse(runTime(success)) : Number.NaN;
      const ageHours = (now - succeededAt) / HOUR_MS;
      if (!success || Number.isNaN(now) || Number.isNaN(succeededAt)) {
        return {
          name: workflow.name,
          status: 'missing',
          alert: true,
          message:
            `${workflow.name}: не найден корректно датированный успешный запуск; ` +
            `воркфлоу вне надзора.\n${ACTIONS_URL}`,
        };
      }
      if (ageHours > workflow.budgetHours) {
        return {
          name: workflow.name,
          status: 'stale',
          alert: true,
          message:
            `${workflow.name}: последний успешный запуск был ${ageText(ageHours)} назад, ` +
            `бюджет ${workflow.budgetHours} ч исчерпан.\n${ACTIONS_URL}`,
        };
      }
    }

    return {
      name: workflow.name,
      status: 'ok',
      alert: false,
      message: `${workflow.name}: последний запуск зелёный.\n${ACTIONS_URL}`,
    };
  });
}
