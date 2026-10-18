import { publicPackageLabel, type DepsSignal, type Entity, type Snapshot } from './data';
import { axis3OwnPackages, axis3ReadingDefinition } from './methodology';

/** Describe the two captured quantities without substituting or recomputing either. */
export function dependentReadings(entity: Entity, snapshot: Snapshot, daily: DepsSignal | null) {
  const axis = entity.axes.deps_direct_dependents_momentum;
  const ownPackages = axis3OwnPackages(snapshot.methodology_version);
  const verification = ownPackages
    ? 'Package linkage is not uniformly verified: packages with no repository metadata (no_link) are unverified and remain admitted.'
    : '';
  const packageLabel = daily ? publicPackageLabel(daily.system, daily.package) : null;
  return {
    weekly: {
      label: 'Weekly direct dependents', value: axis?.status === 'out_of_panel' ? null : axis?.latest ?? null,
      date: axis?.as_of_partition ?? null, source: `https://evidaxis.org/snapshots/${snapshot.snapshot_date}/snapshot.json`,
      role: 'weekly_axis_input', scoring_status: axis?.status ?? 'not_measured',
      package_scope: ownPackages ? 'admitted_own_package_union' : 'frozen_m3_package_union',
      verification: ownPackages ? 'may_include_unverified' : 'verified_at_selection',
      definition: axis3ReadingDefinition(snapshot.methodology_version) + (verification ? ` ${verification}` : ''),
    },
    daily: {
      label: 'Daily package dependents (unscored)', value: daily?.value ?? null,
      date: daily?.captured_at?.slice(0, 10) ?? null, period: daily?.period ?? null,
      captured_at: daily?.captured_at ?? null,
      source: daily && packageLabel !== 'package not shown'
        ? `https://api.deps.dev/v3alpha/systems/${encodeURIComponent(daily.system)}/packages/${encodeURIComponent(daily.package)}` : '',
      role: 'unscored_context', package_scope: packageLabel, verification: daily ? 'identity_verified_pin' : 'not_measured',
      definition: 'deps.dev REST count for one identity-verified pinned package, captured daily and never scored. Its package scope differs from the weekly package union; neither value replaces the other.',
    },
  };
}
