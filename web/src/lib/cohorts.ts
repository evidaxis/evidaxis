/**
 * Deterministic cohort -> CSS-var color mapping. Three cohorts in the live
 * snapshot map to the three signal accents (--c1 teal, --c2 amber, --c3 slate).
 * Inside the dark `.band` section these vars are re-mapped, so charts recolour
 * automatically. Returns a `var(--cN)` reference, never a hardcoded hex.
 */
import { snapshot } from './data';

const ORDER: string[] = Object.keys(snapshot.cohorts);

/** 1-based css-var index for a cohort key (cycles if ever > 3). */
export function cohortVarIndex(cohortKey: string): number {
  const i = ORDER.indexOf(cohortKey);
  return (i < 0 ? 0 : i % 3) + 1;
}

/** `var(--cN)` color token for a cohort (recolours in the dark band). */
export function cohortColor(cohortKey: string): string {
  return `var(--c${cohortVarIndex(cohortKey)})`;
}

/** Human label for a cohort key. Em-dash (U+2014, brand-banned) -> comma. */
export function cohortLabel(cohortKey: string): string {
  const raw = snapshot.cohorts[cohortKey]?.label ?? cohortKey;
  return raw.replace(/\s*—\s*/g, ', ');
}

export const COHORT_ORDER = ORDER;

/**
 * Null-safe z formatter for chart TEXT surfaces. data.ts `fmtZ` returns the
 * em-dash U+2014 for null (brand-banned in built HTML); here null -> "no axis".
 */
export function fmtZsafe(z: number | null | undefined): string {
  if (z == null || !Number.isFinite(z)) return 'no axis';
  return (z >= 0 ? '+' : '') + z.toFixed(2);
}
