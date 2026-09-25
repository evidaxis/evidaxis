import { describe, expect, it } from 'vitest';
import { experimental_AstroContainer as AstroContainer } from 'astro/container';
import { mkdirSync, writeFileSync } from 'node:fs';
import CardB from '../../components/cardB/CardB.astro';
import EntityCard from '../../components/EntityCard.astro';
import { archiveEntityById } from '../archive';
import { cardBFor } from './context';
import { scanEntityLexicon, scanEntityPageWide } from '../../../scripts/entity-lexicon.mjs';

const ids = ['e_S7DQ1QJCCMT', 'e_88YAM3PXK4S', 'e_X33782S1M13', 'e_97SYW64PA3G', 'e_03QFRGK7VQX', 'e_093XKS44M6Q', 'e_Y3HMWAG1BQZ', 'e_7ZJR0NT1B6H', 'e_9SWWW2SWASG', 'e_KR3M8ESKAEW', 'e_H6PPP8CA9RR', 'e_QTVWFV6FJ2V'];
describe('actual Astro Card B render', () => {
  it('renders all twelve fixtures twice, preserving raw numeric HTML and the old instruments', async () => {
    const container = await AstroContainer.create();
    const directory = new URL('../../../.foundation-check/fixtures/', import.meta.url);
    mkdirSync(directory, { recursive: true });
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
  });
});
