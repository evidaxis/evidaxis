import type { APIRoute } from 'astro';
import { snapshot } from '../../../lib/data';
import { entityUniverse } from '../../../lib/archive';

export function getStaticPaths() {
  // Universe, not latest-only: preserved (superseded) pages link their badges too
  // (re-audit fix 2026-07-10). Each badge renders at its record's own period.
  return entityUniverse.map((r) => ({
    params: { id: r.entity.entity_id, period: r.snapshot.period ?? snapshot.period },
    props: { e: r.entity },
  }));
}

const C = {
  rising: '#0c6e63', watch: '#b0641c', calibration: '#756d5f',
  tracked: '#756d5f', 'single-axis': '#756d5f',
} as const;

export const GET: APIRoute = ({ props }) => {
  const e = (props as any).e;
  const accent = (C as any)[e.status] ?? '#756d5f';
  const SHORT_STATUS: Record<string, string> = {
    rising: 'RISING', watch: 'WATCH', tracked: 'TRACKED', calibration: 'CALIB', 'single-axis': '1-AXIS',
  };
  const label = SHORT_STATUS[e.status] ?? e.status.toUpperCase().replace('-', ' ');
  const score = e.momentum != null ? e.momentum.toFixed(1) : '-';
  const W = 244, H = 56;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Evidaxis ${label}, ${e.name}">
  <style>text{font-family:'IBM Plex Mono',ui-monospace,monospace}</style>
  <rect x="0.5" y="0.5" width="${W - 1}" height="${H - 1}" rx="5" fill="#fcfbf7" stroke="#cdc2ab"/>
  <rect x="0.5" y="0.5" width="5" height="${H - 1}" rx="2.5" fill="${accent}"/>
  <g transform="translate(16,16)">
    <path d="M0 24 L12 12 L24 2" stroke="#b0641c" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    <path d="M0 24 L12 12 L24 22" stroke="#0c6e63" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    <circle cx="12" cy="12" r="2.4" fill="#1b1813"/>
  </g>
  <text x="52" y="22" font-size="11" letter-spacing="1.5" fill="#756d5f">EVIDAXIS</text>
  <text x="52" y="40" font-size="14" font-weight="500" fill="#1b1813">${escapeXml(e.name)}</text>
  <text x="${W - 14}" y="24" font-size="18" font-weight="500" text-anchor="end" fill="${accent}">${score}</text>
  <text x="${W - 14}" y="40" font-size="8" letter-spacing="0.4" text-anchor="end" fill="#756d5f">${label} · ${snapshot.period}</text>
</svg>`;
  return new Response(svg, {
    headers: { 'Content-Type': 'image/svg+xml; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
  });
};

function escapeXml(s: string) {
  return s.replace(/[<>&'"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[c]!));
}
