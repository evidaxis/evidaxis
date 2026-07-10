import { describe, it, expect } from 'vitest';
import { snapshot, entities, snapshots } from './data';
import { claimUrnForEntity } from './claim_urn';
import {
  orgGraph, entityGraph, itemListDataset, snapshotDataset, breadcrumb, methodologyGraph,
} from './jsonld';

const GENESIS_DATE = '2026-06-27';
const GENESIS_DOI = '10.5281/zenodo.21076012';

describe('orgGraph', () => {
  it('emits a schema.org @graph with the Organization @id and expanded sameAs', () => {
    const g = orgGraph();
    expect(g['@context']).toBe('https://schema.org');
    const org = g['@graph'].find((n: any) => n['@type'] === 'Organization');
    expect(org['@id']).toBe('https://evidaxis.org/#org');
    expect(Array.isArray(org.sameAs)).toBe(true);
    expect(org.sameAs).toEqual(expect.arrayContaining([
      'https://github.com/evidaxis',
      'https://x.com/evidaxis',
      'https://huggingface.co/evidaxis',
      'https://zenodo.org/records/21076012',
    ]));
    // DOI lives on identifier (PropertyValue), not as a bare doi.org sameAs entry
    expect(org.sameAs.some((s: string) => s.includes('doi.org'))).toBe(false);
    expect(org.identifier).toEqual({
      '@type': 'PropertyValue',
      propertyID: 'DOI',
      value: GENESIS_DOI,
      url: `https://doi.org/${GENESIS_DOI}`,
    });
    // No people links in institutional sameAs
    expect(JSON.stringify(org.sameAs)).not.toMatch(/github\.com\/[^/]+\/[^/"']+/);
  });

  it('DataCatalog lists every archived snapshot Dataset and carries the DOI identifier', () => {
    const g = orgGraph();
    const catalog = g['@graph'].find((n: any) => n['@type'] === 'DataCatalog');
    expect(catalog.identifier.value).toBe(GENESIS_DOI);
    expect(Array.isArray(catalog.dataset)).toBe(true);
    expect(catalog.dataset).toHaveLength(snapshots.length);
    for (const snap of snapshots) {
      const entry = catalog.dataset.find((d: any) => d.url === `https://evidaxis.org/snapshots/${snap.snapshot_date}/`);
      expect(entry).toBeTruthy();
      expect(entry['@id']).toBe(`https://evidaxis.org/snapshots/${snap.snapshot_date}/#dataset`);
    }
  });
});

describe('entityGraph', () => {
  it('wires Dataset -> entity by @id and surfaces momentum as a PropertyValue', () => {
    const e = entities.find((x) => x.momentum != null)!;
    const g = entityGraph(e, snapshot);
    const ds = g['@graph'].find((n: any) => n['@type'] === 'Dataset');
    // Without a claim-URN, Dataset falls back to the HTTPS fragment @id
    expect(ds['@id']).toBe(`https://evidaxis.org/e/${e.entity_id}/#dataset`);
    expect(ds.mainEntity['@id']).toBe(`https://evidaxis.org/e/${e.entity_id}/#entity`);
    expect(ds.license).toBe('https://creativecommons.org/publicdomain/zero/1.0/');
    const mv = ds.variableMeasured.find((v: any) => v.name === 'Evidaxis Momentum Score');
    expect(mv.value).toBe(e.momentum);
  });

  it('keeps Dataset @id an HTTP IRI (CLAIM-URN.md lock) with the URN in identifier', () => {
    // CLAIM-URN.md: the URN lives in identifier + rel=cite-as; @id must stay an
    // HTTP-resolvable IRI so in-graph cross-references dereference (night fix 2026-07-10).
    const e = entities.find((x) => x.momentum != null)!;
    const urn = claimUrnForEntity(e, snapshot);
    const g = entityGraph(e, snapshot, urn);
    const ds = g['@graph'].find((n: any) => n['@type'] === 'Dataset');
    const entity = g['@graph'].find((n: any) => n['@id']?.endsWith('#entity'));
    expect(ds['@id']).toBe(`https://evidaxis.org/e/${e.entity_id}/#dataset`);
    expect(ds.url).toBe(`https://evidaxis.org/e/${e.entity_id}/`);
    expect(ds.mainEntityOfPage).toBe(`https://evidaxis.org/e/${e.entity_id}/`);
    expect(JSON.stringify(ds.identifier)).toContain(urn);
    expect(entity['@id']).toBe(`https://evidaxis.org/e/${e.entity_id}/#entity`);
    expect(entity.subjectOf['@id']).toBe(`https://evidaxis.org/e/${e.entity_id}/#dataset`);
    expect(ds.mainEntity['@id']).toBe(entity['@id']);
  });

  it('models the measured repo as a SoftwareSourceCode node for Organization ownership', () => {
    const e = entities.find((x) => x.github_repo === 'paul-gauthier/aider')!;
    const g = entityGraph(e, snapshot);
    const node = g['@graph'].find((n: any) => n['@id']?.endsWith('#entity'));
    // Entity type may also be SoftwareSourceCode; select the repo node by #source id.
    const source = g['@graph'].find((n: any) => n['@id']?.endsWith('#source'));
    // codeRepository belongs on the #source SoftwareSourceCode node, not on the entity
    expect(node.codeRepository).toBeUndefined();
    expect(source).toBeTruthy();
    expect(source['@type']).toBe('SoftwareSourceCode');
    expect(source.codeRepository).toBe('https://github.com/Aider-AI/aider');
    expect(source['@id']).toBe(`https://evidaxis.org/e/${e.entity_id}/#source`);
    expect(node.isBasedOn['@id']).toBe(source['@id']);
    expect(JSON.stringify(g)).not.toContain('paul-gauthier');
  });

  it('publishes only an eligible external homepage for User ownership', () => {
    const e = entities.find((x) => x.github_repo === 'jwohlwend/boltz')!;
    const g = entityGraph(e, snapshot);
    const node = g['@graph'].find((n: any) => n['@id']?.endsWith('#entity'));
    const ds = g['@graph'].find((n: any) => n['@type'] === 'Dataset');
    const source = g['@graph'].find((n: any) => n['@id']?.endsWith('#source'));
    expect(node.codeRepository).toBeUndefined();
    expect(source).toBeUndefined();
    expect(node.isBasedOn).toBeUndefined();
    expect(node.url).toBeUndefined();
    expect(node.sameAs).toBeUndefined();
    expect(ds.sameAs).toBeUndefined();
    expect(JSON.stringify(g)).not.toContain('jwohlwend');
  });
});

describe('snapshotDataset  -  the genesis DOI branch', () => {
  it('attaches the Zenodo DOI (identifier + sameAs) only on the genesis snapshot', () => {
    // Genesis-dated fixture (robust to `latest` advancing past genesis once weekly snapshots
    // accrue), matching the sibling non-genesis test below.
    const genesis = { ...snapshot, snapshot_date: GENESIS_DATE };
    const g = snapshotDataset(genesis as any);
    const ds = g['@graph'].find((n: any) => n['@type'] === 'Dataset');
    expect(ds.identifier).toEqual({ '@type': 'PropertyValue', propertyID: 'DOI', value: GENESIS_DOI, url: `https://doi.org/${GENESIS_DOI}` });
    expect(ds.sameAs).toBe(`https://doi.org/${GENESIS_DOI}`);
  });
  it('a non-genesis snapshot gets snapshot_id identity and no DOI sameAs', () => {
    const future = { ...snapshot, snapshot_date: '2026-07-04', snapshot_id: 'deadbeefcafe' };
    const ds = snapshotDataset(future as any)['@graph'].find((n: any) => n['@type'] === 'Dataset');
    expect(ds.identifier).toBe('deadbeefcafe');
    expect(ds.sameAs).toBeUndefined();
  });

  it('lists verification-bundle DataDownloads (manifest, provenance, SHA256SUMS)', () => {
    const ds = snapshotDataset(snapshot)['@graph'].find((n: any) => n['@type'] === 'Dataset');
    expect(Array.isArray(ds.distribution)).toBe(true);
    const names = ds.distribution.map((d: any) => d.name);
    expect(names).toEqual(expect.arrayContaining([
      'Full snapshot (JSON)',
      'Input manifest (JSON)',
      'Provenance (JSON)',
      'SHA256 checksums',
    ]));
    const sums = ds.distribution.find((d: any) => d.name === 'SHA256 checksums');
    expect(sums.encodingFormat).toBe('text/plain');
    expect(sums.contentUrl).toContain(`/snapshots/${snapshot.snapshot_date}/SHA256SUMS`);
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

  it('links DefinedTermSet via about/mentions, not hasDefinedTerm on TechArticle', () => {
    const g = methodologyGraph('m1', '/methodology/v1/');
    const doc = g['@graph'].find((n: any) => Array.isArray(n['@type']));
    const terms = g['@graph'].find((n: any) => n['@type'] === 'DefinedTermSet');
    expect(doc.hasDefinedTerm).toBeUndefined();
    expect(doc.about['@id']).toBe(terms['@id']);
    expect(doc.mentions['@id']).toBe(terms['@id']);
    expect(terms.hasDefinedTerm.length).toBeGreaterThan(0);
  });
});
