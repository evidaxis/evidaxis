import type { APIRoute } from 'astro';
import { entityUniverse, publicEntity, publicHomepage, publicRepoUrl } from '../../lib/data';
import type { ArchivedEntity } from '../../lib/archive';
import { claimUrnForEntity } from '../../lib/claim_urn';
import { measurementStateFor, serializeMeasurementState } from '../../lib/measurement';
import { isTemplateB } from '../../lib/cardB/policy.mjs';
import { cardBFor } from '../../lib/cardB/context';

export function getStaticPaths() {
  return entityUniverse.map((record) => ({ params: { id: record.entity.entity_id }, props: { record } }));
}

export const GET: APIRoute = ({ props }) => {
  const record = (props as any).record as ArchivedEntity;
  const e = record.entity;
  const snapshot = record.snapshot;
  const repoUrl = publicRepoUrl(e);
  const homepage = publicHomepage(e);
  const projected = publicEntity(e);
  const {
    status: _legacyStatus,
    rising: _legacyRising,
    axes_present: _legacyAxesPresent,
    convergent_axes: _legacyConvergentAxes,
    note: _legacyNote,
    ...typedEntity
  } = projected;
  const measurementState = measurementStateFor(e, snapshot);
  const body = {
    entity: typedEntity,
    measurement_state: serializeMeasurementState(measurementState),
    record_status: record.recordStatus,
    last_seen_snapshot: record.lastSeenSnapshot,
    // Format-independent canonical reference (CLAIM-URN.md); cite this, not the URL.
    claim_urn: claimUrnForEntity(e, snapshot),
    score_receipt: {
      methodology_version: snapshot.methodology_version,
      snapshot_id: snapshot.snapshot_id,
      snapshot_date: snapshot.snapshot_date,
      period: snapshot.period,
      source: `https://evidaxis.org/snapshots/${snapshot.snapshot_date}/`,
    },
    license: 'CC0-1.0',
    canonical: `https://evidaxis.org/e/${e.entity_id}/`,
    sameAs: [
      ...new Set([repoUrl, homepage].filter((url): url is string => !!url)),
      ...(e.openalex_work_ids?.length ? [`https://openalex.org/${e.openalex_work_ids[0]}`] : []),
    ],
  };
  const card = isTemplateB(e.entity_id) ? cardBFor(record) : null;
  const result = card ? { ...body, display: card.display, facets: card.facets, readings: card.readings, changes: card.changes } : body;
  return new Response(JSON.stringify(result, null, 2), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
