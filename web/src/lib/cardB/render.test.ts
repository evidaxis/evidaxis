import { describe, expect, it } from 'vitest';
import { experimental_AstroContainer as AstroContainer } from 'astro/container';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import CardB from '../../components/cardB/CardB.astro';
import EntityCard from '../../components/EntityCard.astro';
import { archiveEntityById, snapshots } from '../archive';
import { cardBFor, contextFor } from './context';
import { buildCardB } from './build';
import { scanEntityLexicon, scanEntityPageWide } from '../../../scripts/entity-lexicon.mjs';

const ids = ['e_S7DQ1QJCCMT', 'e_88YAM3PXK4S', 'e_X33782S1M13', 'e_97SYW64PA3G', 'e_03QFRGK7VQX', 'e_093XKS44M6Q', 'e_Y3HMWAG1BQZ', 'e_7ZJR0NT1B6H', 'e_9SWWW2SWASG', 'e_KR3M8ESKAEW', 'e_H6PPP8CA9RR', 'e_QTVWFV6FJ2V'];
describe('actual Astro Card B render', () => {
  it('renders and exports m5 own-package coverage without falling back to m3', async () => {
    // Pinned to the immutable 2026-10-17 snapshot: e_002Y62PR7VR is out of panel there and keeps a daily count,
    // so the dependents section renders. The first out-of-panel system in the latest snapshot can have neither.
    const snap = snapshots.find(s => s.snapshot_date === '2026-10-17')!;
    const entity = snap.entities.find(e => e.entity_id === 'e_002Y62PR7VR')!;
    expect(entity.axes.deps_direct_dependents_momentum?.status).toBe('out_of_panel');
    const record = { ...archiveEntityById.get('e_002Y62PR7VR')!, snapshot: snap, entity };
    const model = buildCardB(record, contextFor(record));
    expect(model.facets.dependents.answer).toBe('Dependents: no admitted own package.');
    expect(model.readings.find(r => r.key === 'dependents')?.definition).toContain("system's own packages");
    const container = await AstroContainer.create();
    const html = await container.renderToString(CardB, { props: {
      model, industry: record.entity.industry, industryLabel: record.entity.industry, subNiche: record.entity.sub_niche,
    }, slots: { measurement: '<p>Measurement fixture</p>' } });
    expect(html).toContain('/methodology/m5/#dependents');
    expect(html).toContain('m5 own packages');
    expect(html).not.toContain('/methodology/m3/#dependents');
  });

  it('renders all twelve fixtures twice, preserving raw numeric HTML and the old instruments', async () => {
    const container = await AstroContainer.create();
    // Test renders must not overwrite the tracked design review artifacts.
    const directory = pathToFileURL(mkdtempSync(join(tmpdir(), 'evx-card-render-')) + '/');
    try {
      for (const id of ids) {
        const record = archiveEntityById.get(id)!, model = cardBFor(record), e = record.entity;
        const measurement = await container.renderToString(EntityCard, { props: { entity: e } });
        const options = { props: { model, industry: e.industry, industryLabel: e.industry, subNiche: e.sub_niche }, slots: { measurement } };
        const first = await container.renderToString(CardB, options);
        const second = await container.renderToString(CardB, options);
        expect(first).toBe(second);
        expect(first.match(/<h1\b/g)).toHaveLength(1);
        expect(first).not.toMatch(/\u2014|\bn\/a\b/);
        expect(first).toContain('data-b-citation');
        expect(first.includes('Other indexes count differently')).toBe(model.workIds.length > 0);
        expect(first).toContain('convergence gate');
        expect(first).toContain('Gate ETA: never published');
        expect(first).not.toContain('needs snapshot history (1 snapshot exists)');
        if (model.nicheAssigned) expect(first).toContain('niche median');
        else {
          expect(first.match(/Niche: not yet assigned\./g)).toHaveLength(1);
          expect(first).not.toContain('niche median');
          expect(first).not.toContain('card-b-neighbours');
          expect(first).not.toContain('Peer signals');
        }
        if (id === 'e_S7DQ1QJCCMT') expect(/total citations<\/div>\s*<div[^>]*><data value="5">5<\/data>/.test(first)).toBe(true);
        expect(scanEntityPageWide(first)).toEqual([]);
        expect(scanEntityLexicon(first, e.name)).toEqual([]);
        const withoutNiche = first.replace(/<section[^>]*id="niche"[\s\S]*?<\/section>/, '');
        expect([...withoutNiche.matchAll(/<data value="[\d.]+" data-source="[^"]+" data-date="[^"]+" data-entity="[^"]+"/g)].length).toBeGreaterThanOrEqual(3);
        writeFileSync(new URL(`${id}.html`, directory), first.replace(/\sdata-astro-source-(?:file|loc)="[^"]*"/g, ''));
      }
    } finally { rmSync(directory, { recursive: true, force: true }); }
  });
});
