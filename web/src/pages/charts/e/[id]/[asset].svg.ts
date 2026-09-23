import type { APIRoute } from 'astro';
import { assetRecords, cardBFor } from '../../../../lib/cardB/context';
import { chartsFor } from '../../../../lib/cardB/charts';

export function getStaticPaths() {
  // Previously published release URLs remain addressable when cards switch to
  // inline figures; the rendering switch must not remove immutable artifacts.
  return assetRecords().flatMap(record => {
    const model = cardBFor(record);
    return Object.values(chartsFor(model)).map(chart => ({
      params: { id: record.entity.entity_id, asset: `${chart.block}-${model.release}` }, props: { svg: chart.svg },
    }));
  });
}
export const GET: APIRoute = ({ props }) => new Response(props.svg, { headers: { 'Content-Type': 'image/svg+xml; charset=utf-8' } });
