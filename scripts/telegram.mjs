// One Telegram send for every keeper alert. Callers pass their log label.
// No new dependencies: global fetch, same body as the liveness sensor.

/**
 * @param {string} text
 * @param {string} label log prefix without brackets
 * @returns {Promise<boolean>}
 */
export async function sendTelegram(text, label) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chat = process.env.ALERT_CHAT_ID;
  if (!token || !chat) {
    const joiner = label === 'workflow-watchdog' ? '; ' : ' — ';
    console.error(`[${label}] TELEGRAM_BOT_TOKEN/ALERT_CHAT_ID not set${joiner}alert NOT sent`);
    return false;
  }
  try {
    const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ chat_id: chat, text, disable_web_page_preview: true }),
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) console.error(`[${label}] telegram HTTP`, res.status);
    return res.ok;
  } catch (e) {
    console.error(`[${label}] telegram send failed`, e);
    return false;
  }
}
