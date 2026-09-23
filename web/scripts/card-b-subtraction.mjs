#!/usr/bin/env node
import { readFileSync, readdirSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, join, dirname } from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseHTML, plainText, cardArticle, hasClass } from './card-b-html.mjs';

export function subtraction(html) {
  const article = cardArticle(parseHTML(html));
  if (!article) return null;
  const inert = node => ['script', 'style', 'svg'].includes(node.tag);
  const removed = node => inert(node) || node.tag === 'data'
    || (node.tag === 'p' && (hasClass(node, 'answer') || 'data-claim' in node.attrs));
  const count = text => text.trim().split(/\s+/).filter(Boolean).length;
  const all_words = count(plainText(article, inert)), residual_words = count(plainText(article, removed));
  return { id: article.attrs['data-entity'], all_words, residual_words, residual_share: all_words ? +(residual_words / all_words).toFixed(4) : 0 };
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const dist = resolve(process.env.EVIDAXIS_DIST ?? 'dist');
  const rows = readdirSync(join(dist, 'e'), { withFileTypes: true }).filter(e => e.isDirectory() && e.name.startsWith('e_'))
    .map(e => subtraction(readFileSync(join(dist, 'e', e.name, 'index.html'), 'utf8'))).filter(Boolean).sort((a, b) => a.id.localeCompare(b.id));
  const output = resolve(process.argv[2] ?? '.foundation-check/subtraction.json');
  mkdirSync(dirname(output), { recursive: true });
  writeFileSync(output, JSON.stringify(rows, null, 2) + '\n');
  const sorted = rows.map(r => r.residual_share).sort((a, b) => a - b), mid = Math.floor(sorted.length / 2);
  const median = sorted.length ? sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2 : 0;
  console.log(`${rows.length} B cards; median residual ${100 * median}%`);
}
