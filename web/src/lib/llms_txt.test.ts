/**
 * Structural contract for /llms.txt (WP-E): status-first, non-ranked catalog.
 * Shape test  -  not a full text snapshot (counts move with the live snapshot).
 */
import { describe, it, expect } from 'vitest';
import { GET } from '../pages/llms.txt';

async function body(): Promise<string> {
  const res = GET({} as any);
  const out = res instanceof Response ? res : await res;
  return out.text();
}

describe('llms.txt structure (WP-E status-first, no-rank)', () => {
  it('leads with header then Status counts before Rising / Watch / Catalog', async () => {
    const txt = await body();
    expect(txt.startsWith('# Evidaxis\n')).toBe(true);

    const iStatus = txt.indexOf('## Status (snapshot ');
    const iRising = txt.indexOf('## Rising this period');
    const iWatch = txt.indexOf('## Watch list');
    const iCatalog = txt.indexOf('## Catalog (by cohort, alphabetical within cohort)');
    const iKey = txt.indexOf('## Key resources');

    expect(iStatus).toBeGreaterThan(0);
    expect(iRising).toBeGreaterThan(iStatus);
    expect(iWatch).toBeGreaterThan(iRising);
    expect(iCatalog).toBeGreaterThan(iWatch);
    expect(iKey).toBeGreaterThan(iCatalog);
  });

  it('exposes status count lines including provisional and spine_complete', async () => {
    const txt = await body();
    const statusBlock = txt.slice(
      txt.indexOf('## Status (snapshot '),
      txt.indexOf('## Rising this period'),
    );
    for (const key of ['rising:', 'watch:', 'axis2_present:', 'provisional:', 'spine_complete:']) {
      expect(statusBlock).toContain(key);
    }
  });

  it('explains empty Rising state when none converge', async () => {
    const txt = await body();
    // Either lists rising entities or the locked empty-state sentence.
    const risingBlock = txt.slice(
      txt.indexOf('## Rising this period'),
      txt.indexOf('## Watch list'),
    );
    if (!/^-\s/m.test(risingBlock)) {
      expect(risingBlock).toMatch(/two independent axes must converge/i);
    }
  });

  it('does not advertise momentum ranking of the machine surface', async () => {
    const txt = await body();
    expect(txt.toLowerCase()).not.toContain('ranked by momentum');
    expect(txt).not.toMatch(/## Tracked systems.*ranked/i);
  });

  it('includes methodology-registry.json in Key resources', async () => {
    const txt = await body();
    const keyBlock = txt.slice(txt.indexOf('## Key resources'));
    expect(keyBlock).toContain('https://evidaxis.org/methodology-registry.json');
  });

  it('includes How to verify with the verification bundle URLs', async () => {
    const txt = await body();
    expect(txt).toContain('## How to verify');
    expect(txt).toContain('/manifest.json');
    expect(txt).toContain('/provenance.json');
    expect(txt).toContain('/SHA256SUMS');
    expect(txt).toMatch(/sha256sum -c SHA256SUMS/);
  });

  it('emits per-entity claim-URN and JSON twin in the catalog', async () => {
    const txt = await body();
    const catalog = txt.slice(
      txt.indexOf('## Catalog (by cohort, alphabetical within cohort)'),
      txt.indexOf('## Key resources'),
    );
    expect(catalog).toMatch(/urn:evidaxis:claim:e_[0-9A-HJKMNP-TV-Z]+:m\d+:\d{4}-\d{2}-\d{2}/);
    expect(catalog).toMatch(/https:\/\/evidaxis\.org\/e\/e_[0-9A-HJKMNP-TV-Z]+\.json/);
    // Cohort subheadings
    expect(catalog).toMatch(/^### /m);
  });
});
