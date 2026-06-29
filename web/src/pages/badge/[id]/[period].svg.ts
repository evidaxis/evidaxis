import type { APIRoute } from 'astro';
import { entities, snapshot } from '../../../lib/data';

export function getStaticPaths() {
  return entities.map((e) => ({ params: { id: e.entity_id, period: snapshot.period }, props: { e } }));
}

const C = {
  rising: '#0c6e63', watch: '#b0641c', calibration: '#756d5f',
  tracked: '#756d5f', 'single-axis': '#756d5f',
} as const;

export const GET: APIRoute = ({ props }) => {
  const e = (props as any).e;
  const accent = (C as any)[e.status] ?? '#756d5f';
  const label = e.status.toUpperCase().replace('-', ' ');
  const score = e.momentum != null ? e.momentum.toFixed(1) : '—';
  const W = 232, H = 56;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Evidaxis ${label} — ${e.name}">
  <style>text{font-family:'IBM Plex Mono',ui-monospace,monospace}</style>
  <rect x="0.5" y="0.5" width="${W - 1}" height="${H - 1}" rx="5" fill="#fcfbf7" stroke="#cdc2ab"/>
  <rect x="0.5" y="0.5" width="5" height="${H - 1}" rx="2.5" fill="${accent}"/>
  <g transform="translate(16,16)">
    <path d="M0 24 L12 12 L24 2" stroke="#b0641c" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    <path d="M0 24 L12 12 L24 22" stroke="#0c6e63" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    <circle cx="12" cy="12" r="2.4" fill="#1b1813"/>
  </g>
  <text x="52" y="22" font-size="11" letter-spacing="1.5" fill="#756d5f">EVIDAXIS · ${label}</text>
  <text x="52" y="40" font-size="14" font-weight="500" fill="#1b1813">${escapeXml(e.name)}</text>
  <text x="${W - 14}" y="25" font-size="18" font-weight="500" text-anchor="end" fill="${accent}">${score}</text>
  <text x="${W - 14}" y="40" font-size="8.5" text-anchor="end" fill="#756d5f">${snapshot.period}</text>
</svg>`;
  return new Response(svg, {
    headers: { 'Content-Type': 'image/svg+xml; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
  });
};

function escapeXml(s: string) {
  return s.replace(/[<>&'"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[c]!));
}
