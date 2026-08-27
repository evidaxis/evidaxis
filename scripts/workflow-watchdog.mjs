// Pure workflow-health evaluator for the class-level watchdog. The runner owns
// GitHub and Telegram I/O; this module only decides whether every rostered
// workflow is green and, for scheduled workflows, recently successful.
//
// Alert discipline (2026-08-27, after the watchdog spent a GitHub cron drought
// alarming about itself): a push is born only by a fact that needs a human.
// Three gates sit between "a workflow looks overdue" and "wake the keeper":
//   1. SELF      — the watchdog never judges itself by its own last outcome.
//                  It used to: an alert exits non-zero, which made the run red,
//                  which the next run read as "workflow-watchdog is failing" and
//                  alarmed again — a latch whose only exit (a green run) required
//                  the previous run to be green already. Deadlock, forever.
//   2. FACT      — overdue is not the fact; the fact is the site. A stale
//                  liveness-check with the archive up and serving its marker is a
//                  GitHub scheduling artefact, not an outage. Fails CLOSED: if the
//                  probe itself could not run, the alert stands.
//   3. DROUGHT   — when NOTHING in the repo has been dispatched for longer than
//                  the tightest exhausted budget, the subject is GitHub's cron, not
//                  Evidaxis: one line about the platform instead of one per workflow.
//                  Workflows whose staleness costs un-backfillable CAPTURE
//                  (`dataLoss`) stay loud through it — a lost observation hour is
//                  never recoverable, which is the asymmetry the whole sensor exists for.

/** @typedef {'ok'|'red'|'stale'|'missing'|'drought'} WorkflowStatus */

const ACTIONS_URL = 'https://github.com/evidaxis/evidaxis/actions';
const HOUR_MS = 3600_000;

/** @param {Map<string, object>|Record<string, object>|undefined} runs @param {string} name */
function runFor(runs, name) {
  if (!runs) return undefined;
  return runs instanceof Map ? runs.get(name) : runs?.[name];
}

/** @param {object} run */
function runTime(run) {
  return run.completed_at ?? run.updated_at ?? run.created_at ?? '';
}

/** When the scheduler DISPATCHED the run — the fact a drought is measured in. @param {object} run */
function startTime(run) {
  return run.created_at ?? run.updated_at ?? run.completed_at ?? '';
}

/** @param {number} hours */
function ageText(hours) {
  const safeHours = Math.max(0, Math.floor(hours));
  const days = (safeHours / 24).toFixed(1);
  return `${safeHours} ч (${days} дн.)`;
}

/** @param {{name: string, status: WorkflowStatus}} result */
function isOverdue(result) {
  return result.status === 'stale' || result.status === 'missing';
}

/**
 * @param {{name: string, kind: 'scheduled'|'event', budgetHours?: number, self?: boolean, factGate?: string, dataLoss?: boolean}} workflow
 * @param {{latestCompleted: any, latestSuccess: any}} i
 * @param {number} now
 */
function judge(workflow, i, now) {
  const completed = runFor(i.latestCompleted, workflow.name);
  if (!completed) {
    return {
      status: /** @type {WorkflowStatus} */ ('missing'),
      alert: true,
      message: `${workflow.name}: нет завершённых запусков; воркфлоу вне надзора.\n${ACTIONS_URL}`,
    };
  }

  if (completed.conclusion !== 'success') {
    const conclusion = completed.conclusion ?? 'без результата';
    return {
      status: /** @type {WorkflowStatus} */ ('red'),
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
        status: /** @type {WorkflowStatus} */ ('missing'),
        alert: true,
        message:
          `${workflow.name}: не найден корректно датированный успешный запуск; ` +
          `воркфлоу вне надзора.\n${ACTIONS_URL}`,
      };
    }
    if (ageHours > (workflow.budgetHours ?? Infinity)) {
      return {
        status: /** @type {WorkflowStatus} */ ('stale'),
        alert: true,
        message:
          `${workflow.name}: последний успешный запуск был ${ageText(ageHours)} назад, ` +
          `бюджет ${workflow.budgetHours} ч исчерпан.\n${ACTIONS_URL}`,
      };
    }
  }

  return {
    status: /** @type {WorkflowStatus} */ ('ok'),
    alert: false,
    message: `${workflow.name}: последний запуск зелёный.\n${ACTIONS_URL}`,
  };
}

/**
 * Gate 1. The watchdog is running right now, so its own gap is over by
 * construction and its own red run is the latch, not news.
 */
function silenceSelf(result) {
  if (result.status === 'ok') return result;
  const reason =
    result.status === 'red'
      ? 'прошлый собственный запуск был красным'
      : 'собственные запуски прерывались';
  return {
    ...result,
    alert: false,
    quiet: 'self',
    message:
      `${result.name}: ${reason}, но сторож работает прямо сейчас — разрыв закрыт, ` +
      `тревожить не о чем (тихо).`,
  };
}

/**
 * @param {{
 *   roster: Array<{name: string, kind: 'scheduled'|'event', budgetHours?: number, self?: boolean, factGate?: string, dataLoss?: boolean}>,
 *   latestCompleted: Map<string, object>|Record<string, object>,
 *   latestSuccess: Map<string, object>|Record<string, object>,
 *   nowIso: string,
 * }} i
 */
export function evaluateWorkflowHealth(i) {
  const now = Date.parse(i.nowIso);

  return i.roster.map((workflow) => {
    const verdict = judge(workflow, i, now);
    const result = {
      name: workflow.name,
      kind: workflow.kind,
      ...verdict,
      ...(workflow.self ? { self: true } : {}),
      ...(workflow.factGate ? { factGate: workflow.factGate } : {}),
      ...(workflow.dataLoss ? { dataLoss: true } : {}),
      ...(workflow.budgetHours ? { budgetHours: workflow.budgetHours } : {}),
    };
    return workflow.self ? silenceSelf(result) : result;
  });
}

/**
 * Gate 2. `facts` maps a workflow name to the directly observed truth behind it.
 * A missing fact for a gated alert keeps the alert LOUD (fail closed).
 * @param {Array<any>} results
 * @param {Record<string, {ok: boolean, detail: string}>} facts
 */
export function applyFactGates(results, facts) {
  return results.map((result) => {
    if (!result.factGate || !result.alert || !isOverdue(result)) return result;
    const fact = facts?.[result.name];
    if (!fact) {
      return {
        ...result,
        factVerdict: 'unknown',
        message: `${result.message}\nПроверить факт напрямую не удалось — сигнал оставлен громким.`,
      };
    }
    if (!fact.ok) {
      return {
        ...result,
        factVerdict: 'bad',
        message: `${result.message}\nПроверено напрямую: ${fact.detail}`,
      };
    }
    return {
      ...result,
      alert: false,
      quiet: 'fact-ok',
      factVerdict: 'ok',
      message:
        `${result.name}: датчик просрочен, но факт проверен напрямую — ${fact.detail} ` +
        `Молчание датчика вызвано расписанием GitHub, а не архивом (тихо).`,
    };
  });
}

/**
 * Gate 3. Collapses a repo-wide scheduling drought into one platform line.
 * @param {Array<any>} results
 * @param {{
 *   roster: Array<{name: string, self?: boolean}>,
 *   latestAnyRun?: Map<string, object>|Record<string, object>,
 *   latestCompleted?: Map<string, object>|Record<string, object>,
 *   nowIso: string,
 * }} i
 */
export function applyDroughtGate(results, i) {
  const now = Date.parse(i.nowIso);
  const overdue = results.filter(
    (result) => result.alert && isOverdue(result) && !result.self && result.kind === 'scheduled',
  );
  if (!overdue.length || Number.isNaN(now)) return results;

  const tightest = Math.min(...overdue.map((result) => result.budgetHours ?? Infinity));
  if (!Number.isFinite(tightest)) return results;

  // Newest dispatch anywhere in the repo, self excluded: this run proves nothing
  // about the scheduler that is being judged.
  let newest = Number.NaN;
  for (const workflow of i.roster) {
    if (workflow.self) continue;
    const run = runFor(i.latestAnyRun, workflow.name) ?? runFor(i.latestCompleted, workflow.name);
    const started = run ? Date.parse(startTime(run)) : Number.NaN;
    if (!Number.isNaN(started) && (Number.isNaN(newest) || started > newest)) newest = started;
  }
  if (Number.isNaN(newest)) return results;

  const idleHours = (now - newest) / HOUR_MS;
  if (idleHours <= tightest) return results;

  const sinceIso = new Date(newest).toISOString();
  const gated = results.map((result) => {
    if (!result.alert || !isOverdue(result) || result.kind !== 'scheduled') return result;
    if (result.dataLoss || result.factVerdict === 'bad') return result;
    return { ...result, alert: false, quiet: 'drought' };
  });

  const loudLeft = gated.some((result) => result.alert);
  gated.push({
    name: 'github-scheduler',
    kind: 'platform',
    status: 'drought',
    alert: loudLeft,
    ...(loudLeft ? {} : { quiet: 'drought' }),
    droughtSince: sinceIso,
    message:
      `GitHub не запускает плановые задачи с ${sinceIso} — ${ageText(idleHours)} тишины, ` +
      `за это окно не стартовала ни одна задача архива. Дело в расписании GitHub, не в Evidaxis.\n${ACTIONS_URL}`,
  });
  return gated;
}
