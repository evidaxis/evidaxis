import { describe, expect, it } from 'vitest';
import { experimental_AstroContainer as AstroContainer } from 'astro/container';
import SwingSignal from './SwingSignal.astro';

describe('SwingSignal', () => {
  it('renders the reserved state for a commit series shorter than the recency window', async () => {
    // 2026-10-03 snapshot: the first card with fewer than 14 commit weeks crashed the build.
    const container = await AstroContainer.create();
    const html = await container.renderToString(SwingSignal, { props: { series: [1, 0, 2] } });
    expect(html).toContain('reserved');
    expect(html).not.toMatch(/undefined|NaN/);
  });
  it('still renders the ratio for a full series', async () => {
    const container = await AstroContainer.create();
    const series = Array.from({ length: 52 }, (_, i) => i % 7);
    const html = await container.renderToString(SwingSignal, { props: { series } });
    expect(html).toMatch(/log-slope ratio [+-]\d+\.\d{2}/);
  });
});
