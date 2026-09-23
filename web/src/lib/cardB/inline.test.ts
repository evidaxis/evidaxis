import { expect, it, vi } from 'vitest';
import { experimental_AstroContainer as AstroContainer } from 'astro/container';
vi.mock('./config', () => ({ CHARTS_INLINE: true, TEMPLATE_VERSION: 'b1' }));
import Chart from '../../components/cardB/Chart.astro';
import { chartsFor } from './charts';
import { cardBFor } from './context';
import { archiveEntityById } from '../archive';
it('uses the same accessible SVG and numeric data in the inline fallback', async () => {
  const m = cardBFor(archiveEntityById.get('e_S7DQ1QJCCMT')!);
  const chart = chartsFor(m).commits;
  const container = await AstroContainer.create();
  const html = await container.renderToString(Chart, { props: { chart } });
  expect(html).toContain(chart.svg);
  expect(html).not.toContain('<img');
  expect(html).toContain('role="img"');
  expect(html).toContain('<title'); expect(html).toContain('<desc');
});
