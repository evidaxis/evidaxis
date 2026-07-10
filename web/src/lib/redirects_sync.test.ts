/** The machine-auditable redirect map (redirects.yaml, CC0) must mirror the
 * actually-executing config (web/vercel.json) 1:1  -  a divergence means the
 * published map lies about what the site does (2026-07-02 finding: yaml had
 * 2 of 5 rules and a live 301->404). Also: every static destination must
 * resolve to a real page directory in src/pages. */
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = dirname(fileURLToPath(import.meta.url));
const vercel = JSON.parse(readFileSync(resolve(here, '../../vercel.json'), 'utf8'));

function parseYamlRules(text: string): { from: string; to: string }[] {
  const rules: { from: string; to: string }[] = [];
  let cur: { from?: string; to?: string } = {};
  for (const line of text.split('\n')) {
    const from = line.match(/^\s*-\s*from:\s*'([^']+)'/);
    const to = line.match(/^\s*to:\s*'([^']+)'/);
    if (from) {
      if (cur.from && cur.to) rules.push(cur as { from: string; to: string });
      cur = { from: from[1] };
    }
    if (to) cur.to = to[1];
  }
  if (cur.from && cur.to) rules.push(cur as { from: string; to: string });
  return rules;
}

const yaml = parseYamlRules(readFileSync(resolve(here, '../../../redirects.yaml'), 'utf8'));

describe('redirects.yaml <-> vercel.json equivalence', () => {
  it('has the same number of rules', () => {
    expect(yaml.length).toBe(vercel.redirects.length);
  });

  it('every vercel redirect appears in the yaml map (same source and destination)', () => {
    const norm = (s: string) => (s.endsWith('/') ? s : `${s}/`);
    for (const r of vercel.redirects) {
      const match = yaml.find((y) => y.from === r.source);
      expect(match, `yaml missing rule for ${r.source}`).toBeTruthy();
      expect(norm(match!.to), `destination drift for ${r.source}`).toBe(norm(r.destination));
    }
  });

  it('destination prefixes resolve to real page routes (literal or dynamic segments)', () => {
    const routeExists = (prefix: string): boolean => {
      let dir = resolve(here, '../pages');
      for (const seg of prefix.split('/').filter(Boolean)) {
        const literal = resolve(dir, seg);
        if (existsSync(literal)) {
          dir = literal;
          continue;
        }
        const dynamic = readdirSync(dir).find((d) => d.startsWith('['));
        if (dynamic) {
          dir = resolve(dir, dynamic);
          continue;
        }
        return false;
      }
      return true;
    };
    for (const r of vercel.redirects) {
      const prefix = r.destination.split(':')[0];
      expect(routeExists(prefix), `destination prefix ${prefix} resolves to no route`).toBe(true);
    }
  });
});
