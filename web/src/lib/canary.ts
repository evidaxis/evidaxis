import assignment from '../data/canary-assignment.json';
import type { MeasurementState } from './measurement';
import { CITATION_AXIS, measurementPhrases } from './measurement';

export type CanaryGroup = 'treatment' | 'control' | null;

export type CanaryPair = {
  pair: number;
  treatment: string;
  control: string;
};

function entityIdFromUrl(url: string): string {
  const match = new URL(url).pathname.match(/^\/e\/(e_[A-Z0-9]+)\/$/);
  if (!match) throw new Error(`invalid canary entity URL: ${url}`);
  return match[1];
}

export const CANARY_PAIRS = assignment.pairs.map((pair) => ({
  pair: pair.pair,
  treatment: entityIdFromUrl(pair.treatment),
  control: entityIdFromUrl(pair.control),
})) satisfies CanaryPair[];

const groupByEntity = new Map<string, Exclude<CanaryGroup, null>>();
for (const pair of CANARY_PAIRS) {
  if (groupByEntity.has(pair.treatment) || groupByEntity.has(pair.control) || pair.treatment === pair.control) {
    throw new Error(`duplicate canary assignment in pair ${pair.pair}`);
  }
  groupByEntity.set(pair.treatment, 'treatment');
  groupByEntity.set(pair.control, 'control');
}

export function canaryGroup(entityId: string): CanaryGroup {
  return groupByEntity.get(entityId) ?? null;
}

export function treatmentTitle(name: string, state: MeasurementState): string {
  const citationMeasured = state.axis_coverage.axes[CITATION_AXIS] === 'measurable';
  return citationMeasured
    ? `${name} momentum: development velocity & citation signals — weekly open data`
    : `${name} momentum: development velocity signals — weekly open data`;
}

export function treatmentAnswerFirst(name: string, cohort: string, state: MeasurementState): string {
  const phrases = measurementPhrases(state);
  return `As of ${state.snapshot_date}: ${name} (${cohort}) is under weekly measurement. ${phrases.axis_coverage} ${phrases.gate}`;
}

export function citationText(name: string, entityId: string, snapshotDate: string): { plain: string; bibtex: string } {
  const record = `https://evidaxis.org/e/${entityId}/`;
  const plain = `Evidaxis. ${name} measurement record. Snapshot ${snapshotDate}. ${record} Concept DOI: 10.5281/zenodo.21076011.`;
  const bibtex = `@dataset{evidaxis_${entityId}_${snapshotDate.replaceAll('-', '')},\n  title = {${name} measurement record},\n  publisher = {Evidaxis},\n  year = {${snapshotDate.slice(0, 4)}},\n  url = {${record}},\n  doi = {10.5281/zenodo.21076011}\n}`;
  return { plain, bibtex };
}
