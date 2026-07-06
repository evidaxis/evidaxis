// Pure uptime+integrity check for the external liveness sensor. Evidaxis is a
// static site deployed deliberately (vercel --prod CLI from the committed tree,
// not auto-on-push), so "prod == main HEAD" is NOT an invariant — the fact to
// watch is: is the live archive up and serving its real content? Dependency-free
// + side-effect-free: runs under plain `node` in CI, unit-tested (liveness.test.mjs).
// Seam-sensor principle from ai-checker (2026-07-06).

/** @typedef {'ok'|'down'|'degraded'} LivenessStatus */

/**
 * @param {{ url: string, reached: boolean, status: number, hasMarker: boolean, marker: string }} i
 * @returns {{ status: LivenessStatus, alert: boolean, message: string }}
 */
export function evaluateLiveness(i) {
  if (!i.reached) {
    return { status: 'down', alert: true, message: `${i.url} недоступен — нет ответа (сеть/DNS/таймаут).` };
  }
  if (i.status !== 200) {
    return { status: 'down', alert: true, message: `${i.url} отдаёт HTTP ${i.status} (ожидался 200).` };
  }
  if (!i.hasMarker) {
    return {
      status: 'degraded',
      alert: true,
      message: `${i.url} отвечает 200, но не содержит маркер «${i.marker}» — битый или чужой контент.`,
    };
  }
  return { status: 'ok', alert: false, message: `${i.url} жив (200 + контент-маркер).` };
}
