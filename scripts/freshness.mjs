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
// Deliberately NOT an alarm about being down: unreachable is the liveness
// sensor's fact, and two sensors shouting about one outage teach the keeper to
// mute both. Dependency-free and side-effect-free; unit-tested in
// freshness.test.mjs.

/** @typedef {'ok'|'publishing'|'stale'|'unknown'} FreshnessStatus */

const HOUR_MS = 3600_000;
const DAY_MS = 24 * HOUR_MS;
const ACTIONS_URL = 'https://github.com/evidaxis/evidaxis/actions';

/** @param {string} snapshotDate */
function captureTime(snapshotDate) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(snapshotDate)) return Number.NaN;
  // snapshot_date has day precision, so anchor it to the scheduled 06:17 UTC
  // capture. The 174-hour budget then expires at 12:17 the next Saturday.
  const timestamp = Date.parse(`${snapshotDate}T06:17:00Z`);
  if (Number.isNaN(timestamp)) return Number.NaN;
  return new Date(timestamp).toISOString().slice(0, 10) === snapshotDate
    ? timestamp
    : Number.NaN;
}

/** @param {number} ageHours */
function archiveAge(ageHours) {
  const hours = Math.max(0, Math.floor(ageHours));
  return `${hours} ч (${(hours / 24).toFixed(1)} дн.)`;
}

/**
 * @param {{ snapshotDate: string, nowIso: string, budgetHours?: number }} i
 * @returns {{ status: FreshnessStatus, alert: boolean, message: string }}
 */
export function evaluateArchiveFreshness(i) {
  const budgetHours = i.budgetHours ?? 174;
  const capturedAt = captureTime(i.snapshotDate);
  const now = Date.parse(i.nowIso);
  if (Number.isNaN(capturedAt) || Number.isNaN(now)) {
    return {
      status: 'stale',
      alert: true,
      message:
        `Дата архивного снапшота «${i.snapshotDate}» некорректна: нельзя подтвердить, ` +
        `что сам CAPTURE состоялся.\n${ACTIONS_URL}`,
    };
  }

  const ageHours = (now - capturedAt) / HOUR_MS;
  if (ageHours <= budgetHours) {
    return {
      status: 'ok',
      alert: false,
      message:
        `Архивный снапшот ${i.snapshotDate} имеет возраст ${archiveAge(ageHours)}, ` +
        `бюджет ${budgetHours} ч не исчерпан.\n${ACTIONS_URL}`,
    };
  }
  return {
    status: 'stale',
    alert: true,
    message:
      `Сам CAPTURE не состоялся: новейшему архивному снапшоту ${i.snapshotDate} уже ` +
      `${archiveAge(ageHours)}, бюджет ${budgetHours} ч исчерпан.\n${ACTIONS_URL}`,
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
      message: `${url} не ответил — свежесть фида не проверялась.`,
    };
  }
  if (i.status !== 200) {
    return {
      status: 'stale',
      alert: true,
      message: `${url} отдаёт HTTP ${i.status}; последняя запись фида не проверена.`,
    };
  }
  const published = Date.parse(i.latestEntryAt ?? '');
  if (Number.isNaN(published)) {
    return {
      status: 'stale',
      alert: true,
      message: `${url} не содержит корректную дату последней записи.`,
    };
  }
  const ageDays = (i.now.getTime() - published) / DAY_MS;
  if (ageDays <= maxAgeDays) {
    return {
      status: 'ok',
      alert: false,
      message: `Последняя запись ${url} имеет возраст ${Math.max(0, Math.floor(ageDays))} дн.`,
    };
  }
  return {
    status: 'stale',
    alert: true,
    message: `Последняя запись ${url} старше ${maxAgeDays} дн. (${Math.floor(ageDays)} дн.).`,
  };
}
