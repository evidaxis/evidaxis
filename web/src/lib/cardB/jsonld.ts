import type { CardBModel } from './build';
import { chartsFor } from './charts';

export function cardBGraphs(graphs: object[], m: CardBModel) {
  // Clone only in the B branch: shared JSON-LD and A serialization stay intact.
  const result = JSON.parse(JSON.stringify(graphs).replace(/\u2014/g, '-').replace(/\bn\/a\b/g, 'no reading'));
  const entityGraph = result.find((graph: any) => Array.isArray(graph['@graph']));
  const nodes = entityGraph['@graph'];
  for (const node of nodes) if (node['@type'] === 'Dataset') {
    node.distribution = [...(Array.isArray(node.distribution) ? node.distribution : [node.distribution]).filter(Boolean),
      { '@type': 'DataDownload', contentUrl: `https://evidaxis.org${m.valuesUrl}`, encodingFormat: 'text/csv' }];
  }
  const charts = chartsFor(m), primary = charts.commits ?? charts.citations ?? charts.dependents ?? charts.changes;
  if (primary) nodes.push({ '@type': 'WebPage', '@id': `${m.url}#webpage`, url: m.url, name: `${m.entity.name}, Evidaxis measurement`,
    primaryImageOfPage: { '@type': 'ImageObject', url: `https://evidaxis.org${primary.url}`, contentUrl: `https://evidaxis.org${primary.url}`, caption: primary.title } });
  return result;
}
