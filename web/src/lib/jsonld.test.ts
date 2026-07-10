import { describe, it, expect } from 'vitest';
import { snapshot, entities } from './data';
import {
  orgGraph, entityGraph, itemListDataset, snapshotDataset, breadcrumb, methodologyGraph,
} from './jsonld';

const GENESIS_DATE = '2026-06-27';
const GENESIS_DOI = '10.5281/zenodo.21076012';

describe('orgGraph', () => {
  it('emits a schema.org @graph with the Organization @id and sameAs', () => {
    const g = orgGraph();
    expect(g['@context']).toBe('https://schema.org');
    const org = g['@graph'].find((n: any) => n['@type'] === 'Organization');
    expect(org['@id']).toBe('https://evidaxis.org/#org');
    expect(Array.isArray(org.sameAs)).toBe(true);
    // org sameAs must NOT carry the dataset DOI (DOI lives on the snapshot Dataset node)
    expect(JSON.stringify(org.sameAs)).not.toContain('doi.org');
  });
});

describe('entityGraph', () => {
  it('wires Dataset -> entity by @id and surfaces momentum as a PropertyValue', () => {
    const e = entities.find((x) => x.momentum != null)!;
    const g = entityGraph(e, snapshot);
    const ds = g['@graph'].find((n: any) => n['@type'] === 'Dataset');
    expect(ds['@id']).toBe(`https://evidaxis.org/e/${e.entity_id}/#dataset`);
    expect(ds.mainEntity['@id']).toBe(`https://evidaxis.org/e/${e.entity_id}/#entity`);
    expect(ds.license).toBe('https://creativecommons.org/publicdomain/zero/1.0/');
    const mv = ds.variableMeasured.find((v: any) => v.name === 'Evidaxis Momentum Score');
    expect(mv.value).toBe(e.momentum);
  });

  it('keeps the canonical GitHub repository for Organization ownership', () => {
    const e = entities.find((x) => x.github_repo === 'paul-gauthier/aider')!;
    const g = entityGraph(e, snapshot);
    const node = g['@graph'].find((n: any) => n['@id']?.endsWith('#entity'));
    expect(node.codeRepository).toBe('https://github.com/Aider-AI/aider');
    expect(JSON.stringify(g)).not.toContain('paul-gauthier');
  });

  it('publishes only an eligible external homepage for User ownership', () => {
    const e = entities.find((x) => x.github_repo === 'jwohlwend/boltz')!;
    const g = entityGraph(e, snapshot);
    const node = g['@graph'].find((n: any) => n['@id']?.endsWith('#entity'));
    const ds = g['@graph'].find((n: any) => n['@type'] === 'Dataset');
    expect(node.codeRepository).toBeUndefined();
    expect(node.url).toBeUndefined();
    expect(node.sameAs).toBeUndefined();
    expect(ds.sameAs).toBeUndefined();
    expect(JSON.stringify(g)).not.toContain('jwohlwend');
  });
});

describe('snapshotDataset — the genesis DOI branch', () => {
  it('attaches the Zenodo DOI (identifier + sameAs) only on the genesis snapshot', () => {
    // Genesis-dated fixture (robust to `latest` advancing past genesis once weekly snapshots
    // accrue), matching the sibling non-genesis test below.
    const genesis = { ...snapshot, snapshot_date: GENESIS_DATE };
    const g = snapshotDataset(genesis as any);
    const ds = g['@graph'].find((n: any) => n['@type'] === 'Dataset');
    expect(ds.identifier).toEqual({ '@type': 'PropertyValue', propertyID: 'DOI', value: GENESIS_DOI, url: `https://doi.org/${GENESIS_DOI}` });
    expect(ds.sameAs).toBe(`https://doi.org/${GENESIS_DOI}`);
  });
  it('a non-genesis snapshot gets a plain string identifier and no DOI sameAs', () => {
    const future = { ...snapshot, snapshot_date: '2026-07-04' };
    const ds = snapshotDataset(future as any)['@graph'].find((n: any) => n['@type'] === 'Dataset');
    expect(ds.identifier).toBe('evidaxis-snapshot-2026-07-04');
    expect(ds.sameAs).toBeUndefined();
  });
});

describe('itemListDataset', () => {
  it('numbers the list and lists each entity url', () => {
    const g = itemListDataset({ path: '/coverage/', name: 'n', description: 'd', snap: snapshot, entities: entities.slice(0, 3) });
    const list = g['@graph'].find((n: any) => n['@type'] === 'ItemList');
    expect(list.numberOfItems).toBe(3);
    expect(list.itemListElement).toHaveLength(3);
    expect(list.itemListElement[0].url).toContain('/e/');
  });
});

describe('breadcrumb', () => {
  it('positions are 1-indexed and absolute', () => {
    const b = breadcrumb([{ name: 'Home', path: '/' }, { name: 'X', path: '/x/' }]);
    expect(b.itemListElement[0].position).toBe(1);
    expect(b.itemListElement[1].position).toBe(2);
    expect(b.itemListElement[1].item).toBe('https://evidaxis.org/x/');
  });
});

describe('methodologyGraph', () => {
  it('strips the m-prefix from the version number', () => {
    const g = methodologyGraph('m1', '/methodology/v1/');
    const doc = g['@graph'].find((n: any) => Array.isArray(n['@type']));
    expect(doc.version).toBe('1');
  });
});
