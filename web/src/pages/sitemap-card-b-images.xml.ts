import type { APIRoute } from 'astro';
import { bRecords, cardBFor } from '../lib/cardB/context';
import { chartsFor } from '../lib/cardB/charts';
import { isIndexable } from '../lib/cardB/policy.mjs';
import { CHARTS_INLINE } from '../lib/cardB/config';
import { xml } from '../lib/cardB/exports';
export const GET: APIRoute = () => {
  const urls = CHARTS_INLINE ? [] : bRecords.flatMap(record => {
    const m = cardBFor(record);
    if (!isIndexable({ entity: record.entity, display: m.display, readings: m.readings })) return [];
    return [`<url><loc>${xml(m.url)}</loc>${Object.values(chartsFor(m)).map(c => `<image:image><image:loc>https://evidaxis.org${xml(c.url)}</image:loc></image:image>`).join('')}</url>`];
  });
  return new Response(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">${urls.join('')}</urlset>`, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
};
