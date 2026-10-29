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
import { inReminderWindow, shouldPush } from './alert-gate.mjs';
export { evaluateWeeklyRelease, weeklyReleaseDay } from './weekly-release.mjs';

/** @typedef {'ok'|'publishing'|'stale'|'unknown'} FreshnessStatus */

const HOUR_MS = 3600_000;
const DAY_MS = 24 * HOUR_MS;

/** Last marked key in a job log. `-` and a missing line mean "nothing sent yet". @param {string} logText @param {string} marker */
function lastMarkedKey(logText, marker) {
  let found = null;
  const markLine = new RegExp(`${marker} (\\S+)\\s*$`);
  for (const line of String(logText ?? '').split(/\r?\n/)) {
    const mark = line.match(markLine);
    if (!mark) continue;
    found = mark[1] === '-' ? null : mark[1];
  }
  return found;
}

/** @param {string} logText */
export function parseReleaseKey(logText) {
  return lastMarkedKey(logText, 'RELEASE_KEY');
}

/** @param {string} logText */
export function parseFeedKey(logText) {
  return lastMarkedKey(logText, 'FEED_KEY');
}

export function parseReceiptWeek(logText) {
  return lastMarkedKey(logText, 'RELEASE_RECEIPT');
}

export function parseActiveWeek(logText) {
  return lastMarkedKey(logText, 'RELEASE_ACTIVE');
}

/**
 * One push per feed state. The previous workflow conclusion is not an input:
 * a new feed key is sent even when the last run failed while reading GitHub.
 * The same key is repeated only inside the morning window.
 * A healthy feed clears the key, so the next failure is new.
 *
 * @param {{
 *   alert: boolean,
 *   key: string,
 *   previousKey?: string|null,
 *   nowIso: string,
 * }} i
 * @returns {{ push: boolean, exitCode: 0|1, notifiedKey: string }}
 */
export function decideFeedPush(i) {
  const previousKey = typeof i.previousKey === 'string' && i.previousKey && i.previousKey !== '-'
    ? i.previousKey
    : null;
  if (!i.alert) return { push: false, exitCode: 0, notifiedKey: '' };
  const same = previousKey === i.key;
  return {
    push: same ? inReminderWindow(i.nowIso) : true,
    exitCode: 1,
    notifiedKey: i.key,
  };
}

/**
 * Telegram carries only states that need the keeper (`remind`): failed, not started, unreadable.
 * The receipt and "late but moving" stay in the job log, even when the previous keys are lost:
 * the keeper asked for no "nobody is needed" messages (26.09.2026, again 29.10.2026).
 * `alert` still lets those states own duplicate snapshot and feed alarms.
 * One push per (week, state); the same state repeats only through alert-gate's daily reminder.
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
  if (!release.remind) return { push: false, exitCode: 0, notifiedKey: release.key };
  const same = previousKey === release.key;
  // A missing key means we do not know whether this state was sent. A red previous run may be liveness, not this release, so send.
  const push = same ? shouldPush({ previousConclusion: i.previousConclusion, nowIso: i.nowIso }) : true;
  return { push, exitCode: 1, notifiedKey: release.key };
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
