// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import sentry from '@sentry/astro';
import { loadEnv } from 'vite';
import { readFileSync } from 'node:fs';

// Sentry DSN читаем на сборке (loadEnv видит .env файлы + реальный process.env).
// Сайт статический → Sentry ловит только клиентские (браузерные) ошибки; DSN публичный.
const { SENTRY_DSN, SENTRY_AUTH_TOKEN } = loadEnv(process.env.NODE_ENV ?? 'production', process.cwd(), '');

// Freshness: stamp sitemap lastmod from the real data-change date (snapshot_date)
// for data-driven pages; a frozen date for methodology/about. Only bumps when the
// snapshot actually changes — never on cosmetic edits (preserves the freshness signal).
const SNAP_DATE = JSON.parse(readFileSync(new URL('../data/latest.json', import.meta.url), 'utf8')).snapshot_date;
const METHODOLOGY_FROZEN = '2026-06-27';

export default defineConfig({
  site: 'https://evidaxis.org',
  output: 'static',
  trailingSlash: 'always',
  build: { format: 'directory' },
  integrations: [
    sitemap({
      filter: (page) => !page.includes('/charttest') && !page.includes('/methodology/current/'),
      serialize(item) {
        const u = item.url;
        item.lastmod = (u.includes('/methodology/') || u.includes('/about/')) ? METHODOLOGY_FROZEN : SNAP_DATE;
        if (u.includes('/snapshots/') || u.includes('/cohorts/') || u.includes('/e/')) item.changefreq = 'weekly';
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
