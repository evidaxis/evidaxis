// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import sentry from '@sentry/astro';
import { loadEnv } from 'vite';
import { readFileSync, readdirSync } from 'node:fs';

// Sentry DSN читаем на сборке (loadEnv видит .env файлы + реальный process.env).
// Сайт статический → Sentry ловит только клиентские (браузерные) ошибки; DSN публичный.
const { SENTRY_DSN, SENTRY_AUTH_TOKEN } = loadEnv(process.env.NODE_ENV ?? 'production', process.cwd(), '');

// Freshness: stamp sitemap lastmod from the real data-change date (snapshot_date)
// for data-driven pages; a frozen date for methodology/about. Only bumps when the
// snapshot actually changes — never on cosmetic edits (preserves the freshness signal).
const SNAP_DATE = JSON.parse(readFileSync(new URL('../data/latest.json', import.meta.url), 'utf8')).snapshot_date;
const METHODOLOGY_FROZEN = '2026-06-27';
const snapshotDates = new Map();
const entityLastSeen = new Map();
for (const date of readdirSync(new URL('../data/snapshots/', import.meta.url)).filter((name) => /^\d{4}-\d{2}-\d{2}$/.test(name)).sort()) {
  const snap = JSON.parse(readFileSync(new URL(`../data/snapshots/${date}/snapshot.json`, import.meta.url), 'utf8'));
  if (snap.snapshot_date !== date) throw new Error(`snapshot date mismatch: directory ${date}, payload ${snap.snapshot_date}`);
  snapshotDates.set(`/snapshots/${date}/`, date);
  for (const entity of snap.entities) entityLastSeen.set(`/e/${entity.entity_id}/`, date);
}
if (![...snapshotDates.values()].includes(SNAP_DATE)) throw new Error(`data/latest.json points to missing snapshot ${SNAP_DATE}`);

export default defineConfig({
  site: 'https://evidaxis.org',
  output: 'static',
  trailingSlash: 'always',
  build: { format: 'directory' },
  integrations: [
    sitemap({
      filter: (page) => !page.includes('/charttest') && !page.includes('/methodology/current/'),
      serialize(item) {
        const path = new URL(item.url).pathname;
        item.lastmod = (path.includes('/methodology/') || path.includes('/about/'))
          ? METHODOLOGY_FROZEN
          : snapshotDates.get(path) ?? entityLastSeen.get(path) ?? SNAP_DATE;
        if (path === '/snapshots/') item.lastmod = SNAP_DATE;
        if (path.includes('/cohorts/') || (path.startsWith('/e/') && entityLastSeen.get(path) === SNAP_DATE)) item.changefreq = 'weekly';
        return item;
      },
    }),
    // Sentry — только браузерные ошибки (сайт статический). Без DSN не подключаем (no-op).
    ...(SENTRY_DSN
      ? [sentry({
          dsn: SENTRY_DSN,
          ...(SENTRY_AUTH_TOKEN
            ? { sourceMapsUploadOptions: { org: 'doctor-ads', project: 'evidaxis', authToken: SENTRY_AUTH_TOKEN } }
            : {}),
        })]
      : []),
  ],
});
