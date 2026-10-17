// Pure freshness check for the external publication sensor.
//
// The liveness sensor deliberately watches only "is the archive up and serving
// its real content", and its header says prod == main is NOT an invariant. That
// was true while deploys were manual. It stopped being true on 2026-07-11, when
// CI took over publication — and the gap it left is what let the 2026-08-08
// snapshot (and with it the first census activation tranche) sit in git for a
// week while evidaxis.org kept serving 2026-08-01 with every check green.
//
// So this module watches a different fact: does the live host serve the newest
// snapshot the repository holds? A snapshot that exists only in git is not
// published, and a sensor that cannot say so is what makes the failure silent.
//
// The Saturday release is a third fact. File age cannot tell "GitHub started
// the cron late" from "the capture did not happen". On 2026-10-17 that confusion
// paged the keeper while weekly-snapshot was still running. evaluateWeeklyRelease
// names the state of the release instead. It does no I/O.
//
// Deliberately NOT an alarm about being down: unreachable is the liveness
// sensor's fact, and two sensors shouting about one outage teach the keeper to
// mute both. Dependency-free aside from the pure daily gate in alert-gate.mjs.
import { shouldPush } from './alert-gate.mjs';

/** @typedef {'ok'|'publishing'|'stale'|'unknown'} FreshnessStatus */
/** @typedef {'ok'|'released'|'running'|'publishing'|'failed'|'not_started'|'unknown'} ReleaseStatus */

const HOUR_MS = 3600_000;
const DAY_MS = 24 * HOUR_MS;
// 06:17 UTC is the weekly-snapshot cron (`17 6 * * 6`); the delay sentence measures from that minute, not from a file-age budget.
const SCHEDULE_HOUR_UTC = 6;
const SCHEDULE_MINUTE_UTC = 17;
// 12:00 UTC Saturday is when a still-running or still-missing release is worth one message: the old 174 h file-age budget expired near this hour and paged while the run was alive.
const DEADLINE_HOUR_UTC = 12;
const WEEKLY_WORKFLOW_URL = 'https://github.com/evidaxis/evidaxis/actions/workflows/weekly-snapshot.yml';
// waiting/pending/requested count as running: weekly-snapshot sits on the data-commits lock, and that wait is not "the schedule did not start".
const IN_FLIGHT = new Set(['queued', 'in_progress', 'waiting', 'pending', 'requested']);
const BAD_CONCLUSION = new Set(['failure', 'cancelled', 'timed_out']);

/** @param {string} nowIso @returns {string|null} YYYY-MM-DD of the last Saturday at or before now (UTC). */
export function weeklyReleaseDay(nowIso) {
  const now = new Date(nowIso);
  if (Number.isNaN(now.getTime())) return null;
  const back = (now.getUTCDay() + 1) % 7;
  const midnight = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  return new Date(midnight - back * DAY_MS).toISOString().slice(0, 10);
}

/** @param {string} iso @returns {string|null} */
function clock(iso) {
  const parsed = Date.parse(iso ?? '');
  if (Number.isNaN(parsed)) return null;
  const date = new Date(parsed);
  const hour = String(date.getUTCHours()).padStart(2, '0');
  const minute = String(date.getUTCMinutes()).padStart(2, '0');
  return `${hour}:${minute}`;
}

/** @param {string} week */
function deadlineMs(week) {
  return Date.parse(`${week}T${String(DEADLINE_HOUR_UTC).padStart(2, '0')}:00:00Z`);
}

/** @param {string} week */
function scheduleMs(week) {
  const hour = String(SCHEDULE_HOUR_UTC).padStart(2, '0');
  const minute = String(SCHEDULE_MINUTE_UTC).padStart(2, '0');
  return Date.parse(`${week}T${hour}:${minute}:00Z`);
}

/** @param {object[]} runs @param {string} week @param {number} nowMs */
function runsForWeek(runs, week, nowMs) {
  const start = Date.parse(`${week}T00:00:00Z`);
  return (Array.isArray(runs) ? runs : [])
    .filter((run) => {
      const created = Date.parse(run?.created_at ?? '');
      return !Number.isNaN(created) && created >= start && created <= nowMs;
    })
    .sort((a, b) => {
      const delta = Date.parse(b.created_at) - Date.parse(a.created_at);
      if (delta) return delta;
      return Number(b.id) - Number(a.id);
    });
}

/** @param {object|undefined} run */
function isInFlight(run) {
  return Boolean(run) && IN_FLIGHT.has(run.status) && !run.conclusion;
}

/** @param {object|undefined} run */
function isSuccess(run) {
  return run?.conclusion === 'success';
}

/** @param {object|undefined} run */
function isBad(run) {
  return BAD_CONCLUSION.has(run?.conclusion);
}

// Rehearsal (`weekly rehearsal …`) and a dry-run do not publish the Saturday snapshot, so they are not release runs and must not clear an earlier failure.
function isReleaseRun(run) {
  const title = String(run?.display_title ?? '').trim();
  if (title.startsWith('weekly rehearsal')) return false;
  if (/\bdry[-_ ]run\b/i.test(title)) return false;
  if (run?.dry_run === true) return false;
  return true;
}

/** @param {object} a @param {object} b */
function isNewer(a, b) {
  const delta = Date.parse(a.created_at) - Date.parse(b.created_at);
  if (delta) return delta > 0;
  return Number(a.id) > Number(b.id);
}

/** Newest failed run for the week that no later run has replaced with success or work in progress. @param {object[]} runs */
function blockingFailure(runs) {
  for (const run of runs) {
    if (!isBad(run)) continue;
    const replaced = runs.some((other) => isNewer(other, run) && (isInFlight(other) || isSuccess(other)));
    if (!replaced) return run;
  }
  return null;
}

/**
 * First step whose conclusion is failure, in job order. The runner passes the
 * jobs payload from the GitHub API; the wording of the alert stays here.
 * @param {{ steps?: { name?: string, conclusion?: string }[] }[]|undefined} jobs
 * @returns {string|undefined}
 */
export function pickFailedStep(jobs) {
  for (const job of jobs ?? []) {
    for (const step of job?.steps ?? []) {
      if (step?.conclusion === 'failure' && step.name) return step.name;
    }
  }
  return undefined;
}

/** Last `RELEASE_KEY` line in a job log. `-` and a missing line mean "nothing sent yet". @param {string} logText */
export function parseReleaseKey(logText) {
  let found = null;
  for (const line of String(logText ?? '').split(/\r?\n/)) {
    const mark = line.match(/RELEASE_KEY (\S+)\s*$/);
    if (!mark) continue;
    found = mark[1] === '-' ? null : mark[1];
  }
  return found;
}

/**
 * @param {string} week
 * @param {ReleaseStatus} status
 * @param {boolean} alert
 * @param {string} message
 * @param {boolean} remind
 */
function verdict(week, status, alert, message, remind) {
  return {
    status,
    alert,
    message,
    key: `${week}:${status}`,
    remind: Boolean(alert && remind),
    week,
  };
}

/** @param {string} text @param {string|undefined} url */
function withRun(text, url) {
  return url ? `${text} ${url}` : text;
}

/** @param {object} run @param {string} week */
function scheduleDelay(run, week) {
  if (run.event !== 'schedule') return '';
  const started = Date.parse(run.run_started_at || run.created_at || '');
  const planned = scheduleMs(week);
  if (Number.isNaN(started) || Number.isNaN(planned)) return '';
  const minutes = Math.floor((started - planned) / 60_000);
  if (minutes < 1) return '';
  return ` (GitHub запустил расписание на ${Math.floor(minutes / 60)} ч ${minutes % 60} мин позже)`;
}

/** @param {string} week @param {object} run */
function runningMessage(week, run) {
  const started = clock(run.run_started_at || run.created_at) ?? 'неизвестное время';
  const sentence = `Срез ${week} опаздывает, но идёт: сбор начался в ${started} UTC${scheduleDelay(run, week)}.`;
  return `${withRun(sentence, run.html_url)} Нужен человек: нет. Следующее сообщение — когда выйдет или упадёт.`;
}

/** @param {string} week @param {object} run */
function publishingMessage(week, run) {
  const started = clock(run.run_started_at || run.created_at) ?? 'неизвестное время';
  const sentence = `Срез ${week}: сбор готов, идёт выкладка с ${started} UTC.`;
  return `${withRun(sentence, run.html_url)} Нужен человек: нет.`;
}

/** @param {string} week @param {'weekly'|'deploy'} kind @param {object} run */
function failedMessage(week, kind, run) {
  const step = run.failedStep ? `на шаге «${run.failedStep}»` : 'на неизвестном шаге';
  const when = clock(run.updated_at || run.run_started_at) ?? 'неизвестное время';
  const what = kind === 'deploy' ? `выкладка упала ${step}` : `weekly-snapshot упал ${step}`;
  const sentence = `Срез ${week} не вышел: ${what} в ${when} UTC.`;
  return `${withRun(sentence, run.html_url)} Нужен человек: да.`;
}

/** @param {string} week @param {object[]} weeklies @param {object[]} deploys */
function releasedMessage(week, weeklies, deploys) {
  const weekly = weeklies.find(isSuccess);
  const deploy = deploys.find(isSuccess);
  const start = clock(weekly?.run_started_at || weekly?.created_at);
  const end = clock(weekly?.updated_at);
  const published = clock(deploy?.updated_at);
  let sentence = `✅ Срез ${week} на сайте.`;
  if (start && end && published) {
    sentence = `✅ Срез ${week} на сайте. Сбор шёл ${start}–${end} UTC, выкладка закончилась в ${published} UTC.`;
  } else if (start && end) {
    sentence = `✅ Срез ${week} на сайте. Сбор шёл ${start}–${end} UTC.`;
  }
  return `${withRun(sentence, weekly?.html_url || deploy?.html_url)} Нужен человек: нет.`;
}

/**
 * State of the Saturday release. `D` is the last Saturday at or before `nowIso`.
 * A run is "for D" when GitHub created it at or after D 00:00 UTC.
 * File age is not an input: a live run must not read as a missed capture.
 *
 * @param {{
 *   nowIso: string,
 *   archiveDate: string,
 *   prodDate: string|null,
 *   weeklyRuns?: object[],
 *   deployRuns?: object[],
 *   apiError?: string|null,
 * }} i
 * @returns {{ status: ReleaseStatus, alert: boolean, message: string, key: string, remind: boolean, week: string }}
 */
export function evaluateWeeklyRelease(i) {
  const week = weeklyReleaseDay(i.nowIso);
  const apiError = typeof i.apiError === 'string' ? i.apiError.replace(/\s+/g, ' ').trim() : '';
  if (!week) {
    return verdict('unknown', 'unknown', true,
      'Не могу проверить выпуск: время проверки некорректно. Нужен человек: нет, проверю в следующий раз.',
      true);
  }
  if (apiError) {
    return verdict(week, 'unknown', true,
      `Не могу проверить выпуск ${week}: GitHub API ответил ${apiError}. Нужен человек: нет, проверю в следующий раз.`,
      true);
  }

  const nowMs = Date.parse(i.nowIso);
  const past = nowMs >= deadlineMs(week);
  const weeklies = runsForWeek(i.weeklyRuns, week, nowMs).filter(isReleaseRun);
  const deploys = runsForWeek(i.deployRuns, week, nowMs);

  if (i.archiveDate === week && i.prodDate === week) {
    return verdict(week, 'released', true, releasedMessage(week, weeklies, deploys), false);
  }

  const live = weeklies.find(isInFlight);
  if (live) {
    if (!past) return verdict(week, 'running', false, '', false);
    return verdict(week, 'running', true, runningMessage(week, live), false);
  }

  const weeklyFail = blockingFailure(weeklies);
  if (weeklyFail) return verdict(week, 'failed', true, failedMessage(week, 'weekly', weeklyFail), true);

  const deployLive = deploys.find(isInFlight);
  if (i.archiveDate === week && i.prodDate !== week && deployLive) {
    if (!past) return verdict(week, 'publishing', false, '', false);
    return verdict(week, 'publishing', true, publishingMessage(week, deployLive), false);
  }

  const deployFail = blockingFailure(deploys);
  if (i.archiveDate === week && i.prodDate !== week && deployFail) {
    return verdict(week, 'failed', true, failedMessage(week, 'deploy', deployFail), true);
  }

  if (weeklies.length === 0) {
    if (!past) return verdict(week, 'not_started', false, '', false);
    const deadline = `${String(DEADLINE_HOUR_UTC).padStart(2, '0')}:00`;
    return verdict(week, 'not_started', true,
      `Срез ${week} не стартовал к ${deadline} UTC: GitHub не запустил расписание. ` +
        `Нужен человек: да — запустить weekly-snapshot вручную: ${WEEKLY_WORKFLOW_URL}`,
      true);
  }

  const latest = weeklies[0];
  if (past && i.archiveDate !== week && isSuccess(latest)) {
    const when = clock(latest.updated_at || latest.run_started_at) ?? 'неизвестное время';
    const sentence = `Срез ${week} не вышел: сбор завершился в ${when} UTC, но среза ${week} в архиве нет.`;
    return verdict(week, 'failed', true, `${withRun(sentence, latest.html_url)} Нужен человек: да.`, true);
  }

  return verdict(week, 'ok', false, '', false);
}

/**
 * One Telegram push per (week, state). The same state uses alert-gate's daily
 * reminder only when a human is needed or the API could not be read (`remind`).
 * A quiet observation must not overwrite the key of the message already sent,
 * or the late alarm would think it had already fired.
 *
 * @param {{
 *   release: { alert: boolean, key: string, remind: boolean },
 *   previousKey?: string|null,
 *   previousConclusion?: string|null,
 *   nowIso: string,
 * }} i
 * @returns {{ push: boolean, exitCode: 0|1, notifiedKey: string }}
 */
export function decideWeeklyPush(i) {
  const previousKey = typeof i.previousKey === 'string' && i.previousKey && i.previousKey !== '-'
    ? i.previousKey
    : null;
  const release = i.release;
  if (!release?.alert) {
    return { push: false, exitCode: 0, notifiedKey: previousKey ?? '' };
  }
  const same = previousKey === release.key;
  const gateOpen = shouldPush({ previousConclusion: i.previousConclusion, nowIso: i.nowIso });
  // A missing key means we do not know whether this state was sent. A red previous run may be liveness, not this release, so send.
  const push = same ? Boolean(release.remind) && gateOpen : true;
  return { push, exitCode: release.remind ? 1 : 0, notifiedKey: release.key };
}

/**
 * Line value for `RELEASE_KEY`. A push that Telegram did not accept must not
 * look delivered: until `sent`, keep the previous key (empty when it was unreadable).
 * @param {{ push: boolean, notifiedKey: string, previousKey?: string|null, sent: boolean }} i
 * @returns {string}
 */
export function releaseKeyToPrint(i) {
  const pending = typeof i.previousKey === 'string' && i.previousKey && i.previousKey !== '-'
    ? i.previousKey
    : '';
  if (!i.push) return i.notifiedKey || pending;
  return i.sent ? i.notifiedKey : pending;
}

/**
 * Snapshot and feed alarms that only repeat the weekly-release message stay in
 * the log. The release verdict is the one the keeper sees for that Saturday.
 * Only an ageing feed is explained by a release that is not out yet. HTTP errors,
 * a dead feed, and a broken feed still go out. A released week does not swallow
 * a later feed fault. An API miss does not swallow a prod fault the probe already measured.
 *
 * @param {{
 *   archiveDate: string,
 *   release: { alert?: boolean, status?: string, week?: string },
 *   snapshot: { alert?: boolean },
 *   feed: { alert?: boolean, reason?: string },
 * }} i
 * @returns {{ snapshot: boolean, feed: boolean }}
 */
export function gateFreshnessAlerts(i) {
  const release = i.release ?? {};
  const owns = Boolean(release.alert) && release.status !== 'unknown' && release.status !== 'released';
  const sameArchive = owns && i.archiveDate === release.week;
  const feedAgeExplained = owns && i.feed?.reason === 'age';
  return {
    snapshot: Boolean(i.snapshot?.alert) && !sameArchive,
    feed: Boolean(i.feed?.alert) && !feedAgeExplained,
  };
}

/**
 * @param {{
 *   site: string,
 *   snapshotDate: string,   // newest snapshot in the committed tree, YYYY-MM-DD
 *   reached: boolean,       // did the probe get any HTTP response at all
 *   status: number,         // HTTP status for that snapshot's JSON on prod
 *   now: Date,
 *   graceHours?: number,    // publication window before a gap counts as stale
 * }} i
 * @returns {{ status: FreshnessStatus, alert: boolean, message: string }}
 */
export function evaluateFreshness(i) {
  const grace = i.graceHours ?? 24;
  const url = `${i.site}/snapshots/${i.snapshotDate}/snapshot.json`;

  if (!i.reached) {
    // The site being unreachable is the liveness sensor's fact, not this one's.
    return {
      status: 'unknown',
      alert: false,
      message: `${i.site} не ответил — свежесть не проверялась (это факт сенсора доступности).`,
    };
  }
  if (i.status === 200) {
    return {
      status: 'ok',
      alert: false,
      message: `${i.site} отдаёт снапшот ${i.snapshotDate} — прод совпадает с репозиторием.`,
    };
  }

  // Snapshot dates carry no time of day; measuring the gap from midnight UTC of
  // the snapshot date makes the window conservative (it can only over-wait),
  // which is the right direction for an alarm that pages a human.
  const committed = Date.parse(`${i.snapshotDate}T00:00:00Z`);
  const ageHours = Number.isNaN(committed)
    ? Number.POSITIVE_INFINITY
    : (i.now.getTime() - committed) / HOUR_MS;

  if (ageHours < grace) {
    return {
      status: 'publishing',
      alert: false,
      message: `Снапшот ${i.snapshotDate} ещё не на проде, но окно публикации (${grace} ч) не вышло.`,
    };
  }
  return {
    status: 'stale',
    alert: true,
    message:
      `Прод отстал: в репозитории снапшот ${i.snapshotDate}, ` +
      `${url} отдаёт HTTP ${i.status} спустя ${Math.floor(ageHours)} ч. ` +
      `Публикация не доехала — карточки живут в git, но не на сайте.`,
  };
}

/**
 * @param {{
 *   site: string,
 *   reached: boolean,
 *   status: number,
 *   latestEntryAt: string | null,
 *   now: Date,
 *   maxAgeDays?: number,
 * }} i
 * @returns {{ status: FreshnessStatus, alert: boolean, message: string }}
 */
export function evaluateFeedFreshness(i) {
  const maxAgeDays = i.maxAgeDays ?? 8;
  const url = `${i.site}/feed.json`;
  if (!i.reached) {
    return {
      status: 'unknown',
      alert: false,
      reason: 'down',
      message: `${url} не ответил — свежесть фида не проверялась.`,
    };
  }
  if (i.status !== 200) {
    return {
      status: 'stale',
      alert: true,
      reason: 'http',
      message: `${url} отдаёт HTTP ${i.status}; последняя запись фида не проверена.`,
    };
  }
  const published = Date.parse(i.latestEntryAt ?? '');
  if (Number.isNaN(published)) {
    return {
      status: 'stale',
      alert: true,
      reason: 'invalid',
      message: `${url} не содержит корректную дату последней записи.`,
    };
  }
  const ageDays = (i.now.getTime() - published) / DAY_MS;
  if (ageDays <= maxAgeDays) {
    return {
      status: 'ok',
      alert: false,
      reason: 'fresh',
      message: `Последняя запись ${url} имеет возраст ${Math.max(0, Math.floor(ageDays))} дн.`,
    };
  }
  return {
    status: 'stale',
    alert: true,
    reason: 'age',
    message: `Последняя запись ${url} старше ${maxAgeDays} дн. (${Math.floor(ageDays)} дн.).`,
  };
}
