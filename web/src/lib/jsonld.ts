/** JSON-LD builders. v1 frozen external contract — property names are load-bearing
 *  (Google indexes them, LLMs train on them). Do not rename. */
import type { DepsSignal, Entity, Snapshot } from './data';
import registry from './methodology-registry.json';

const SITE = 'https://evidaxis.org';
const CC0 = 'https://creativecommons.org/publicdomain/zero/1.0/';
const ORG_ID = `${SITE}/#org`;
const CATALOG_ID = `${SITE}/#catalog`;
const FOUNDED = '2026-06';
// Genesis dataset DOI (Zenodo). The DOI belongs to the genesis SNAPSHOT dataset, not the org,
// so it is emitted on that snapshot's Dataset node (identifier + sameAs), not in org sameAs.
// Future weekly snapshots mint their own version DOIs under the concept DOI.
const GENESIS_SNAPSHOT = '2026-06-27';
const GENESIS_DOI = '10.5281/zenodo.21076012';
// sameAs grows as off-site profiles land. Wikidata QID / Zenodo DOI / X / LinkedIn appended here.
const SAME_AS = [
  'https://github.com/evidaxis',
  // huggingface.co/evidaxis dropped from sameAs 2026-06-30: the HF org publicly lists a named
  // person (a person-free leak via structured data) and has no public datasets/models yet.
  // Re-add once the HF org is both person-free and populated.
];

// Durable, VERSIONED methodology permalink for a given methodology_version. Records
// cite the version they were computed under, never the moving /methodology/current/
// alias, so a frozen citation never drifts when "current" advances (METHODOLOGY-VERSIONING.md).
const methodologyPath = (version: string) => `${SITE}/methodology/${version === 'm1' ? 'v1' : version}/`;

const typeForEntity = (t: string) =>
  t === 'org' || t === 'company' || t === 'lab' ? 'Organization'
  : t === 'model' || t === 'product' || t === 'app' ? 'SoftwareApplication'
  : 'SoftwareSourceCode';

// Self-consistent Organization stub spread into every @graph so deep pages resolve
// their creator/publisher @id locally; the full node on home/about accretes by @id.
const orgRef = () => ({ '@type': 'Organization', '@id': ORG_ID, name: 'Evidaxis', url: SITE + '/' });

export function orgGraph() {
  return {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        '@id': ORG_ID,
        name: 'Evidaxis',
        alternateName: 'Evidaxis Observatory',
        url: SITE + '/',
        slogan: 'An observatory of momentum in open AI systems',
        description:
          'Evidaxis is an independent data observatory that measures open-source and research-native AI systems by the rate of change of their public signals, and publishes the results as open datasets under CC0.',
        disambiguatingDescription:
          'Independent open-data observatory measuring open-source AI momentum; not a company, product, or person.',
        foundingDate: FOUNDED,
        logo: { '@type': 'ImageObject', url: SITE + '/logo.png', width: 600, height: 600 },
        image: SITE + '/logo.png',
        knowsAbout: ['momentum measurement', 'open-source AI', 'software ecosystems', 'open data', 'scientometrics'],
        sameAs: SAME_AS,
      },
      {
        '@type': 'WebSite',
        '@id': `${SITE}/#website`,
        url: SITE + '/',
        name: 'Evidaxis',
        description: 'Open observatory scoring AI systems by measured momentum, published as CC0 datasets.',
        inLanguage: 'en',
        publisher: { '@id': ORG_ID },
      },
      {
        '@type': 'DataCatalog',
        '@id': CATALOG_ID,
        name: 'Evidaxis Open Measurements',
        description: 'The open corpus of Evidaxis measurements: weekly snapshots and per-cohort momentum measurements of open-source AI systems, released under CC0.',
        url: SITE + '/',
        license: CC0,
        isAccessibleForFree: true,
        publisher: { '@id': ORG_ID },
        creator: { '@id': ORG_ID },
      },
    ],
  };
}

export function entityGraph(e: Entity, snap: Snapshot, urn?: string, depsSig?: DepsSignal | null) {
  const a1 = e.axes.github_commit_velocity;
  const a2 = e.axes.openalex_citation_momentum;
  const vars: any[] = [];
  if (e.momentum != null)
    vars.push({ '@type': 'PropertyValue', name: 'Evidaxis Momentum Score', value: e.momentum, minValue: 0, maxValue: 100, unitText: 'points', measurementTechnique: methodologyPath(snap.methodology_version) });
  if (a1.cohort_z != null)
    vars.push({ '@type': 'PropertyValue', name: 'Development-velocity z-score (within cohort)', value: a1.cohort_z });
  if (a2.cohort_z != null)
    vars.push({ '@type': 'PropertyValue', name: 'Citation-momentum z-score (within cohort)', value: a2.cohort_z });
  // deps.dev dependents: an adoption (R0) signal, DISPLAYED and declared, never
  // folded into the momentum score (scoring methodology is frozen). Point-in-time.
  if (depsSig)
    vars.push({ '@type': 'PropertyValue', name: 'deps.dev dependents (adoption, R0)', value: depsSig.value, description: 'Count of downstream packages depending on this system (deps.dev), point-in-time. Adoption signal, not part of the momentum score.' });

  const desc =
    `Independent Evidaxis measurement of ${e.name}, an open ${e.entity_type} in the ${e.sub_niche} cohort. ` +
    (e.momentum != null ? `Momentum score ${e.momentum.toFixed(1)}/100. ` : '') +
    `Status: ${e.status}. ${e.convergent_axes.length} of 2 independent axes rising. ` +
    `Computed on Evidaxis methodology ${snap.methodology_version} from public signals (snapshot ${snap.snapshot_date}).`;

  const paperId = e.openalex_work_ids?.[0];
  const entityNode: any = {
    '@type': typeForEntity(e.entity_type),
    '@id': `${SITE}/e/${e.entity_id}/#entity`,
    name: e.name,
    description: `${e.name}, an open AI system in the ${e.sub_niche} cohort, measured by Evidaxis.`,
    codeRepository: `https://github.com/${e.github_repo}`,
    url: e.homepage ?? `https://github.com/${e.github_repo}`,
    sameAs: [`https://github.com/${e.github_repo}`, ...(e.homepage ? [e.homepage] : [])],
    subjectOf: { '@id': `${SITE}/e/${e.entity_id}/#dataset` },
  };
  if (paperId) entityNode.citation = { '@type': 'ScholarlyArticle', '@id': `https://openalex.org/${paperId}`, sameAs: `https://openalex.org/${paperId}` };
  // Durable canonical reference (CLAIM-URN.md). Goes in `identifier`, never in `@id`:
  // schema.org @id must remain an HTTP-resolvable IRI for graph linking; the URN is
  // the format-independent citation target that survives changes in how LLMs cite.
  if (urn) entityNode.identifier = urn;

  const graph: any[] = [
    orgRef(),
    {
      '@type': 'Dataset',
      '@id': `${SITE}/e/${e.entity_id}/#dataset`,
      name: `Evidaxis measurement: ${e.name}`,
      description: desc,
      url: `${SITE}/e/${e.entity_id}/`,
      identifier: urn
        ? [e.entity_id, { '@type': 'PropertyValue', propertyID: 'claim-urn', value: urn }]
        : e.entity_id,
      license: CC0,
      isAccessibleForFree: true,
      creator: { '@id': ORG_ID },
      publisher: { '@id': ORG_ID },
      includedInDataCatalog: { '@id': CATALOG_ID },
      datePublished: snap.snapshot_date,
      dateModified: snap.snapshot_date,
      temporalCoverage: snap.snapshot_date,
      isBasedOn: `${SITE}/snapshots/${snap.snapshot_date}/`,
      citation: `Evidaxis Methodology ${snap.methodology_version}, ${methodologyPath(snap.methodology_version)}`,
      measurementTechnique: methodologyPath(snap.methodology_version),
      keywords: ['AI', e.industry, e.sub_niche, 'momentum', 'open source'],
      sameAs: `https://github.com/${e.github_repo}`,
      mainEntity: { '@id': `${SITE}/e/${e.entity_id}/#entity` },
      variableMeasured: vars,
      distribution: {
        '@type': 'DataDownload',
        contentUrl: `${SITE}/e/${e.entity_id}.json`,
        encodingFormat: 'application/json',
      },
    },
    entityNode,
  ];

  return { '@context': 'https://schema.org', '@graph': graph };
}

export function itemListDataset(opts: {
  path: string; name: string; description: string; period?: string; snap: Snapshot; entities: Entity[];
}) {
  const { path, name, description, period, snap, entities } = opts;
  return {
    '@context': 'https://schema.org',
    '@graph': [
      orgRef(),
      {
        '@type': 'Dataset',
        '@id': `${SITE}${path}#dataset`,
        name, description,
        url: SITE + path,
        license: CC0,
        isAccessibleForFree: true,
        creator: { '@id': ORG_ID },
        publisher: { '@id': ORG_ID },
        includedInDataCatalog: { '@id': CATALOG_ID },
        datePublished: snap.snapshot_date,
        dateModified: snap.snapshot_date,
        ...(period ? { temporalCoverage: period } : {}),
        isBasedOn: `${SITE}/snapshots/${snap.snapshot_date}/`,
        citation: `Evidaxis Methodology ${snap.methodology_version}, ${methodologyPath(snap.methodology_version)}`,
        mainEntity: { '@id': `${SITE}${path}#list` },
      },
      {
        '@type': 'ItemList',
        '@id': `${SITE}${path}#list`,
        itemListOrder: 'https://schema.org/ItemListUnordered',
        numberOfItems: entities.length,
        itemListElement: entities.map((e) => ({
          '@type': 'ListItem', url: `${SITE}/e/${e.entity_id}/`, name: e.name,
        })),
      },
    ],
  };
}

export function snapshotDataset(snap: Snapshot) {
  const isGenesis = snap.snapshot_date === GENESIS_SNAPSHOT;
  const doiUrl = `https://doi.org/${GENESIS_DOI}`;
  return {
    '@context': 'https://schema.org',
    '@graph': [
      orgRef(),
      {
        '@type': 'Dataset',
        '@id': `${SITE}/snapshots/${snap.snapshot_date}/#dataset`,
        name: `Evidaxis snapshot ${snap.snapshot_date}`,
        description:
          `Complete Evidaxis measurement snapshot for ${snap.snapshot_date}: momentum scores and per-axis signals for ${snap.counts.entities} tracked AI systems across ${Object.keys(snap.cohorts).length} cohorts, computed on methodology ${snap.methodology_version}. Released to the public domain under CC0.`,
        url: `${SITE}/snapshots/${snap.snapshot_date}/`,
        identifier: isGenesis
          ? { '@type': 'PropertyValue', propertyID: 'DOI', value: GENESIS_DOI, url: doiUrl }
          : `evidaxis-snapshot-${snap.snapshot_date}`,
        ...(isGenesis ? { sameAs: doiUrl } : {}),
        license: CC0,
        isAccessibleForFree: true,
        creator: { '@id': ORG_ID },
        publisher: { '@id': ORG_ID },
        includedInDataCatalog: { '@id': CATALOG_ID },
        datePublished: snap.snapshot_date,
        dateModified: snap.snapshot_date,
        temporalCoverage: snap.snapshot_date,
        measurementTechnique: methodologyPath(snap.methodology_version),
        citation: `Evidaxis Methodology ${snap.methodology_version}, ${methodologyPath(snap.methodology_version)}`,
        keywords: ['AI systems', 'momentum', 'open data', 'software ecosystems'],
        // Canonical machine surface: the variables this dataset measures. Only the
        // primary, universally-present quantities are declared here; per-entity
        // derived signals are emitted on each entity page and only when shipped
        // (reserved signals are never published as a number).
        variableMeasured: [
          {
            '@type': 'PropertyValue',
            name: 'Evidaxis Momentum Score',
            description: 'Within-pilot percentile of the combined two-axis signal.',
            minValue: 0, maxValue: 100, unitText: 'points',
            measurementTechnique: methodologyPath(snap.methodology_version),
          },
          {
            '@type': 'PropertyValue',
            name: 'Development-velocity z-score (within cohort)',
            description: 'Log-slope of weekly commit activity, robust-z normalized within the cohort.',
            measurementTechnique: `${methodologyPath(snap.methodology_version)}#velocity`,
          },
          {
            '@type': 'PropertyValue',
            name: 'Citation-momentum z-score (within cohort)',
            description: 'Log-slope of yearly citations to the system paper, robust-z normalized within the cohort. Absent for systems with no measurable citation axis.',
            measurementTechnique: `${methodologyPath(snap.methodology_version)}#citation`,
          },
        ],
        distribution: [
          { '@type': 'DataDownload', name: 'Full snapshot (JSON)', contentUrl: `${SITE}/snapshots/${snap.snapshot_date}/snapshot.json`, encodingFormat: 'application/json' },
        ],
      },
    ],
  };
}

export function breadcrumb(items: { name: string; path: string }[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((it, i) => ({
      '@type': 'ListItem', position: i + 1, name: it.name, item: SITE + it.path,
    })),
  };
}

// Resolve a methodology version to its immutable publish date. Each version is frozen
// the day it went effective; the registry is the single source of truth
// (METHODOLOGY-VERSIONING.md). Unknown version -> throw (fail the build LOUDLY), never
// silently stamp a wrong date: a reader MUST be able to resolve every published version.
const methodologyDate = (version: string): string => {
  const entry = registry.versions.find((v) => v.version === version) as any;
  if (!entry) throw new Error(`methodology ${version} not in registry; add it before publishing its page`);
  return entry.effective_at;
};

export function methodologyGraph(version: string, canonicalVersionPath: string) {
  const frozen = methodologyDate(version);
  return {
    '@context': 'https://schema.org',
    '@graph': [
      orgRef(),
      {
        '@type': ['TechArticle', 'CreativeWork'],
        '@id': `${SITE}${canonicalVersionPath}#doc`,
        name: `Evidaxis Methodology ${version}`,
        headline: 'How Evidaxis measures momentum',
        description: 'The complete, versioned definition of how Evidaxis collects signals, normalizes them within cohorts, and decides which systems are rising.',
        url: SITE + canonicalVersionPath,
        version: version.replace(/^m/, ''),
        datePublished: frozen,
        dateModified: frozen,
        license: 'https://creativecommons.org/licenses/by/4.0/',
        creator: { '@id': ORG_ID },
        publisher: { '@id': ORG_ID },
        inLanguage: 'en',
        hasDefinedTerm: { '@id': `${SITE}${canonicalVersionPath}#terms` },
      },
      {
        '@type': 'DefinedTermSet',
        '@id': `${SITE}${canonicalVersionPath}#terms`,
        name: 'Evidaxis scoring terms',
        hasDefinedTerm: [
          { '@type': 'DefinedTerm', name: 'Momentum Score', description: 'A 0–100 composite of an entity’s within-cohort axis z-scores, measuring rate-of-change relative to peers.', inDefinedTermSet: `${SITE}${canonicalVersionPath}#terms` },
          { '@type': 'DefinedTerm', name: 'Convergence Gate', description: 'A system is "Rising" only when at least two independent axes are simultaneously rising. Positive-only.', inDefinedTermSet: `${SITE}${canonicalVersionPath}#terms` },
        ],
      },
    ],
  };
}
