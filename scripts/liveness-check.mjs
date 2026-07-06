// Runner for the external liveness sensor. Probes the live site (SITE_URL) for
// HTTP 200 + a required content marker and pings Telegram on failure. Runs under
// plain `node` — no npm install (see liveness.mjs).
import { evaluateLiveness } from './liveness.mjs';

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
async function sendTelegram(text) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chat = process.env.ALERT_CHAT_ID;
  if (!token || !chat) {
    console.error('[liveness] TELEGRAM_BOT_TOKEN/ALERT_CHAT_ID not set — alert NOT sent');
    return false;
  }
  try {
    const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ chat_id: chat, text, disable_web_page_preview: true }),
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) console.error('[liveness] telegram HTTP', res.status);
    return res.ok;
  } catch (e) {
    console.error('[liveness] telegram send failed', e);
    return false;
  }
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
  const actionsLink =
    process.env.GITHUB_SERVER_URL && process.env.GITHUB_REPOSITORY
      ? `\n${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions`
      : '';
  await sendTelegram(`🔴 ${label} · прод-доступность\n\n${result.message}${actionsLink}`);
  process.exit(1);
}
process.exit(0);
