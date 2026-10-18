// Runner for the external liveness sensor. Probes the live site (SITE_URL) for
// HTTP 200 + a required content marker and pings Telegram on failure. Runs under
// plain `node` — no npm install (see liveness.mjs).
import { previousConclusion, shouldPush } from './alert-gate.mjs';
import { evaluateLiveness } from './liveness.mjs';
import { sendTelegram as deliverTelegram } from './telegram.mjs';

/** @param {string} url @param {string} marker */
async function probe(url, marker) {
  try {
    const res = await fetch(url, {
      redirect: 'follow',
      headers: { 'user-agent': 'liveness-sensor/1', 'cache-control': 'no-cache' },
      signal: AbortSignal.timeout(12_000),
    });
    const body = await res.text().catch(() => '');
    return { reached: true, status: res.status, hasMarker: marker ? body.includes(marker) : true };
  } catch {
    return { reached: false, status: 0, hasMarker: false };
  }
}

/** @param {string} text */
function sendTelegram(text) {
  return deliverTelegram(text, 'liveness');
}

const url = process.env.SITE_URL;
const marker = process.env.MARKER || '';
const label = process.env.SITE_LABEL || url;
if (!url) {
  console.error('[liveness] SITE_URL not set');
  process.exit(2);
}

const p = await probe(url, marker);
const result = evaluateLiveness({ url, marker, ...p });
console.log(JSON.stringify({ url, status: p.status, hasMarker: p.hasMarker, ...result }));

if (result.alert) {
  // One outage = one push, then at most one morning reminder a day (alert-gate.mjs).
  // The run stays red either way: the next run reads it as "already pushed".
  if (shouldPush({ previousConclusion: await previousConclusion(), nowIso: new Date().toISOString() })) {
    await sendTelegram(
      `🔴 Сайт ${url.replace(/^https?:\/\//, '')} не открывается.\n` +
        `Что сделать: открой чат по Evidaxis и скажи «сайт не открывается, почини».`,
    );
  } else {
    console.log('[liveness] (тихо · повтор) уже отправлено, напоминание — утром');
  }
  process.exit(1);
}
process.exit(0);
