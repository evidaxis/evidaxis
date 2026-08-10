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
