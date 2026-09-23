// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import sentry from '@sentry/astro';
import { loadEnv } from 'vite';
import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { isIndexable } from './src/lib/cardB/policy.mjs';

// Sentry DSN читаем на сборке (loadEnv видит .env файлы + реальный process.env).
// Сайт статический → Sentry ловит только клиентские (браузерные) ошибки; DSN публичный.
const { SENTRY_DSN, SENTRY_AUTH_TOKEN } = loadEnv(process.env.NODE_ENV ?? 'production', process.cwd(), '');

// Freshness: stamp sitemap lastmod from the real data-change date (snapshot_date)
// for data-driven pages; a frozen date for methodology/about. Only bumps when the
// snapshot actually changes — never on cosmetic edits (preserves the freshness signal).
const DATA_DIR = process.env.EVIDAXIS_DATA_DIR ? resolve(process.env.EVIDAXIS_DATA_DIR) : new URL('../data/', import.meta.url).pathname;
const DIST = process.env.EVIDAXIS_DIST ? resolve(process.env.EVIDAXIS_DIST) : new URL('./dist/', import.meta.url).pathname;
const SNAP_DATE = JSON.parse(readFileSync(join(DATA_DIR, 'latest.json'), 'utf8')).snapshot_date;
const METHODOLOGY_FROZEN = '2026-06-27';
/** @type {{ versions: { page: string, effective_at: string }[] }} */
const methodologyRegistry = JSON.parse(readFileSync(new URL('./src/lib/methodology-registry.json', import.meta.url), 'utf8'));
const methodologyDates = new Map(methodologyRegistry.versions.map((entry) => [entry.page, entry.effective_at]));
const snapshotDates = new Map();
const entityLastSeen = new Map();
const entityIndexability = new Map();
for (const date of readdirSync(join(DATA_DIR, 'snapshots')).filter((name) => /^\d{4}-\d{2}-\d{2}$/.test(name)).sort()) {
  const snap = JSON.parse(readFileSync(join(DATA_DIR, 'snapshots', date, 'snapshot.json'), 'utf8'));
  if (snap.snapshot_date !== date) throw new Error(`snapshot date mismatch: directory ${date}, payload ${snap.snapshot_date}`);
  snapshotDates.set(`/snapshots/${date}/`, date);
  for (const entity of snap.entities) entityLastSeen.set(`/e/${entity.entity_id}/`, date);
}
if (![...snapshotDates.values()].includes(SNAP_DATE)) throw new Error(`data/latest.json points to missing snapshot ${SNAP_DATE}`);

const entityPageIsIndexable = (page) => {
  const match = new URL(page).pathname.match(/^\/e\/(e_[^/]+)\/$/);
  if (!match) return true;
  const id = match[1];
  if (entityIndexability.has(id)) return entityIndexability.get(id);

  let indexable = false;
  try {
    const twin = JSON.parse(readFileSync(join(DIST, 'e', `${id}.json`), 'utf8'));
    indexable = isIndexable(twin);
  } catch {}
  entityIndexability.set(id, indexable);
  return indexable;
};

export default defineConfig({
  site: 'https://evidaxis.org',
  output: 'static',
  outDir: DIST,
  trailingSlash: 'always',
  build: { format: 'directory' },
  integrations: [
    sitemap({
      customSitemaps: ['https://evidaxis.org/sitemap-card-b-images.xml'],
      // _charttest is an underscore private route (not built); filter is belt-and-suspenders.
      filter: (page) =>
        !page.includes('/charttest')
        && !page.includes('/_charttest')
        && !page.includes('/methodology/current/')
        && !new URL(page).pathname.startsWith('/signals/')
        && !new URL(page).pathname.startsWith('/badge/')
        && entityPageIsIndexable(page),
      serialize(item) {
        const path = new URL(item.url).pathname;
        item.lastmod = (path.includes('/methodology/') || path.includes('/about/'))
          ? methodologyDates.get(path) ?? METHODOLOGY_FROZEN
          : snapshotDates.get(path) ?? entityLastSeen.get(path) ?? SNAP_DATE;
        if (path === '/snapshots/') item.lastmod = SNAP_DATE;
        if (path.includes('/cohorts/') || (path.startsWith('/e/') && entityLastSeen.get(path) === SNAP_DATE)) item.changefreq = 'weekly';
        return item;
      },
    }),
    // Sentry — browser error-capture ONLY (WP-J / V1). Tracing + session replay off:
    // biggest client-bundle win; observability stack otherwise stays intact.
    ...(SENTRY_DSN
      ? [sentry({
          dsn: SENTRY_DSN,
          tracesSampleRate: 0,
          replaysSessionSampleRate: 0,
          replaysOnErrorSampleRate: 0,
          // Drop browserTracingIntegration from the generated client snippet.
          bundleSizeOptimizations: { excludeTracing: true },
          ...(SENTRY_AUTH_TOKEN
            ? { sourceMapsUploadOptions: { org: 'doctor-ads', project: 'evidaxis', authToken: SENTRY_AUTH_TOKEN } }
            : {}),
        })]
      : []),
  ],
});
