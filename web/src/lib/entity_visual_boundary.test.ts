import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const component = (name: string) => readFileSync(new URL(`../components/${name}`, import.meta.url), 'utf8');
const chart = (name: string) => readFileSync(new URL(`../components/charts/${name}`, import.meta.url), 'utf8');

describe('entity visual boundary', () => {
  it('keeps peer-plane and momentum-ring charts out of EntityCard while retaining self series', () => {
    const source = component('EntityCard.astro');
    expect(source).not.toMatch(/MomentumRing|Quadrant|Beeswarm/);
    expect(source).toContain('<CommitHeatmap');
    expect(source).toContain('<CitBars');
  });

  it('does not expose foreign point names in aggregate chart hover labels', () => {
    expect(chart('Beeswarm.astro')).not.toContain('b.item.name');
    expect(chart('Scatter.astro')).not.toContain('<title>{e.name}');
    expect(chart('Quadrant.astro')).not.toContain('<title>{p.name}');
  });
});
