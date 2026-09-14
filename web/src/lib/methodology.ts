import registry from './methodology-registry.json';

export const DEVELOPMENT_AXIS = 'github_commit_velocity' as const;
export const CITATION_AXIS = 'openalex_citation_momentum' as const;
export const DEPENDENTS_AXIS = 'deps_direct_dependents_momentum' as const;
export type AxisKey = typeof DEVELOPMENT_AXIS | typeof CITATION_AXIS | typeof DEPENDENTS_AXIS;
export type VersionedAxes<T> = Record<typeof DEVELOPMENT_AXIS | typeof CITATION_AXIS, T>
  & Partial<Record<typeof DEPENDENTS_AXIS, T>>;

const axesByVersion: Record<string, AxisKey[]> = {
  m1: [DEVELOPMENT_AXIS, CITATION_AXIS],
  m2: [DEVELOPMENT_AXIS, CITATION_AXIS],
  m3: [DEVELOPMENT_AXIS, CITATION_AXIS, DEPENDENTS_AXIS],
};

export function methodologyEntry(version: string) {
  const entry = registry.versions.find((row) => row.version === version);
  if (!entry) throw new Error(`methodology ${version} not in registry`);
  return entry;
}

export function methodologyAxes(version: string): readonly AxisKey[] {
  methodologyEntry(version);
  const axes = axesByVersion[version];
  if (!axes) throw new Error(`axis definition missing for methodology ${version}`);
  return axes;
}

export const AXIS3_ESTIMAND = 'This axis measures the frozen-panel trajectory of the package set selected and linkage-verified as of 2026-07-21. Systems outside that panel are not measured on this axis. Residual survivorship beyond the frozen universe is disclosed, not denied.';
export const AXIS3_ATTRIBUTION = 'Source: deps.dev (Google), CC-BY 4.0. Modified: aggregated to system-level counts and momentum scores.';
