// Runner for the publication-freshness sensor. Reads the newest snapshot the
// committed tree holds (data/latest.json), asks the live host for that exact
// snapshot, and pings Telegram when prod has fallen behind the archive. Runs
// under plain `node` — no npm install (see freshness.mjs for the fact it
// watches and why it is separate from the liveness sensor).
import { readFileSync } from 'node:fs';
import {
  evaluateArchiveFreshness,
  evaluateFeedFreshness,
  evaluateFreshness,
} from './freshness.mjs';

/** @param {string} url */
async function probe(url) {
  try {
    const res = await fetch(url, {
      redirect: 'follow',
      headers: { 'user-agent': 'freshness-sensor/1', 'cache-control': 'no-cache' },
      signal: AbortSignal.timeout(12_000),
    });
    return { reached: true, status: res.status };
  } catch {
    return { reached: false, status: 0 };
  }
}

/** @param {string} url */
async function probeFeed(url) {
  try {
    const res = await fetch(url, {
      redirect: 'follow',
      headers: { 'user-agent': 'freshness-sensor/1', 'cache-control': 'no-cache' },
      signal: AbortSignal.timeout(12_000),
    });
    let latestEntryAt = null;
    if (res.ok) {
      const body = await res.json().catch(() => null);
      latestEntryAt = body?.items?.[0]?.date_published ?? null;
    }
    return { reached: true, status: res.status, latestEntryAt };
  } catch {
    return { reached: false, status: 0, latestEntryAt: null };
  }
}

/** @param {string} text */
async function sendTelegram(text) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chat = process.env.ALERT_CHAT_ID;
  if (!token || !chat) {
    console.error('[freshness] TELEGRAM_BOT_TOKEN/ALERT_CHAT_ID not set — alert NOT sent');
    return false;
  }
  try {
    const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ chat_id: chat, text, disable_web_page_preview: true }),
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) console.error('[freshness] telegram HTTP', res.status);
    return res.ok;
  } catch (e) {
    console.error('[freshness] telegram send failed', e);
    return false;
  }
}

const site = (process.env.SITE_URL || '').replace(/\/+$/, '');
const label = process.env.SITE_LABEL || site;
const latestPath = process.env.LATEST_JSON || 'data/latest.json';
if (!site) {
  console.error('[freshness] SITE_URL not set');
  process.exit(2);
}

let snapshotDate;
try {
  snapshotDate = JSON.parse(readFileSync(latestPath, 'utf8')).snapshot_date;
} catch (e) {
  // A missing or broken pointer file is itself a publication defect: nothing
  // downstream can know what prod is supposed to be serving.
  console.error(`[freshness] cannot read ${latestPath}`, e);
  process.exit(2);
}

const url = `${site}/snapshots/${snapshotDate}/snapshot.json`;
const p = await probe(url);
const now = new Date();
const result = evaluateFreshness({ site, snapshotDate, now, ...p });
const feedUrl = `${site}/feed.json`;
const feedProbe = await probeFeed(feedUrl);
const feedResult = evaluateFeedFreshness({ site, now, ...feedProbe });
const archiveResult = evaluateArchiveFreshness({ snapshotDate, nowIso: now.toISOString() });
console.log(JSON.stringify({
  snapshot: { url, snapshotDate, httpStatus: p.status, ...result },
  feed: { url: feedUrl, httpStatus: feedProbe.status, latestEntryAt: feedProbe.latestEntryAt, ...feedResult },
  archive: { snapshotDate, ...archiveResult },
}));

if (result.alert || feedResult.alert || archiveResult.alert) {
  await sendTelegram(
    `🟠 ${label} · свежесть данных\n\n` +
    `${result.message}\n${feedResult.message}\n${archiveResult.message}`,
  );
  process.exit(1);
}
process.exit(0);
