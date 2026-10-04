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
  m4: [DEVELOPMENT_AXIS, CITATION_AXIS, DEPENDENTS_AXIS],
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

const AXIS3_ESTIMAND_M3 = 'This axis measures the frozen-panel trajectory of the package set selected and linkage-verified as of 2026-07-21. Systems outside that panel are not measured on this axis. Residual survivorship beyond the frozen universe is disclosed, not denied.';
const AXIS3_ESTIMAND_M4 = 'This axis measures the trajectory of a system\'s own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays, unless its own manifest is private and the published package does not name the declaring repository. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.';
const AXIS3_HISTORY_M3 = 'The earliest weekly points of each series were read from deps.dev\'s BigQuery history on 2026-07-21; later points are weekly captures. Each record reports how many of its points are reconstructed history.';
const AXIS3_HISTORY_M4 = 'The earliest weekly points of each series were read from deps.dev\'s BigQuery history on 2026-07-21; later points are weekly captures. m4 does not replay those partitions: each point is the stored system total, one package\'s unique_direct, or a complete sketch union, and a point that is not exact is withheld. Each record reports how many of its points are reconstructed history.';

/** Frozen m3 permalink imports this string. Callers with a snapshot use axis3Estimand(version). */
export const AXIS3_ESTIMAND = AXIS3_ESTIMAND_M3;
export const AXIS3_ATTRIBUTION = 'Source: deps.dev (Google), CC-BY 4.0. Modified: aggregated to system-level counts and momentum scores.';

export function axis3Estimand(version: string): string {
  if (version === 'm3') return AXIS3_ESTIMAND_M3;
  if (version === 'm4') return AXIS3_ESTIMAND_M4;
  throw new Error(`axis-3 estimand missing for methodology ${version}`);
}

export function axis3History(version: string): string {
  if (version === 'm3') return AXIS3_HISTORY_M3;
  if (version === 'm4') return AXIS3_HISTORY_M4;
  throw new Error(`axis-3 history missing for methodology ${version}`);
}

/** Scored-axis permalink. Versions without axis 3 keep the existing m3 link. */
export function axis3Permalink(version: string): string {
  return version === 'm4' ? '/methodology/m4/#dependents' : '/methodology/m3/#dependents';
}

export function axis3Short(version: string): string {
  if (version === 'm4') return 'Weekly counts of a system\'s own packages: declared in its own tree, published under that name and not attributed by deps.dev to another repository. Packages without repository metadata are unverified.';
  return 'Confirmed-clean weekly package-union counts, measured as a size-adjusted log-slope within the frozen panel.';
}

export function axis3GapLabel(version: string): string {
  return version === 'm4' ? 'Own packages.' : 'Frozen package panel.';
}

export function axis3MethodLabel(version: string): string {
  return version === 'm4' ? 'm4 own packages' : 'm3 package union';
}

export function axis3ReadingDefinition(version: string): string {
  if (version === 'm4') return 'deps.dev weekly direct dependents of the system\'s own packages. A package counts when it is declared in the system\'s own tree, published under that name and not attributed by deps.dev to another repository. Partition dates can repeat across snapshots.';
  return 'deps.dev weekly package-union direct dependents, frozen m3 panel; partition dates can repeat across snapshots.';
}

export function axis3ChartSource(version: string): string {
  return version === 'm4' ? 'deps.dev weekly own-package counts' : 'deps.dev weekly package union';
}

export function dailyDependentsDescription(version: string): string {
  const named = version === 'm4' ? 'm4' : 'm3';
  return `Daily deps.dev REST count, captured point-in-time. The scored direct-dependents axis in ${named} uses weekly partitions.`;
}
