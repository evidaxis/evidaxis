/**
 * Second-order ("derived") signals over the REAL published series.
 *
 * SPAR-CONVERGED rule (DESIGN-PORT-PLAN.md §1, revised by adversarial spar
 * MiniMax M3 + GLM 5.2, 2026-06-29): only signals statistically defensible at
 * the real N may ship; everything else RESERVES with an explicit, honest,
 * machine-readable reason. A reserved signal is a typed object, NEVER a
 * fabricated or "0"-sentinel number. The prototype's seeded-PRNG fakes are
 * deliberately NOT ported.
 *
 * Real N per entity: ~52 weekly commit points, ~5 yearly citation points,
 * only 9/19 entities have a citation axis at all.
 *
 * All functions are pure, deterministic, DOM-free, and person-free.
 */

import type { Entity } from './data';

/** Versioned method id stamped onto every SHIP value for later JSON-LD. */
export const METHOD_VERSION = 'EvidaxisMethodology v0.3.0';

/** Sufficiency gate for commit-axis fits: minimum non-zero commit weeks. */
export const MIN_COMMIT_WEEKS = 26;

/** Provenance for a shipped value, surfaced as schema.org PropertyValue later. */
export interface ShipMeta {
  measurementMethod: string;
  measurementTechnique: string;
}

/** A signal we deliberately do not compute, with an honest reason. */
export interface Reserved {
  reserved: true;
  reason: string;
}

export interface RecencySwing {
  /** ratio of trailing-13w slope to prior-window slope (descriptive, not predictive). */
  value: number;
  recentWindow: 13;
  /** Honest length of the prior window actually used (≤ 39; shorter on undersampled series). */
  priorWindow: number;
  /** human label for the regime the ratio implies. */
  label: string;
  meta: ShipMeta;
}

export interface CommitSharpe {
  /** log-linear slope / residual std of the ~52-week fit. */
  value: number;
  /** +/- confidence interval [lo, hi] (HAC / Newey-West style). */
  ci: [number, number];
  /** degrees of freedom of the fit. */
  dof: number;
  meta: ShipMeta;
}

export interface CommitChangepoint {
  /** index (week) of the single detected changepoint. */
  dateIndex: number;
  /** change in slope across the changepoint. */
  deltaSlope: number;
  meta: ShipMeta;
}
export interface NoChangepoint {
  none: true;
  label: string;
}

export interface SignalQuality {
  commit_weeks: number;
  citation_years: number;
  derived_shipped: string[];
  derived_reserved: string[];
}

const m = (anchor: string): ShipMeta => ({
  measurementMethod: METHOD_VERSION,
  measurementTechnique: `/methodology/current/#${anchor}`,
});

const isReserved = (x: unknown): x is Reserved =>
  typeof x === 'object' && x !== null && (x as Reserved).reserved === true;

// ---------------------------------------------------------------------------
//  small numeric helpers (pure)
// ---------------------------------------------------------------------------

/** OLS slope of y on x = index (0..n-1). Returns slope and residual std. */
function linFit(y: number[]): { slope: number; intercept: number; residStd: number; n: number } {
  const n = y.length;
  if (n < 2) return { slope: 0, intercept: n ? y[0] : 0, residStd: 0, n };
  const xbar = (n - 1) / 2;
  const ybar = y.reduce((a, b) => a + b, 0) / n;
  let sxy = 0;
  let sxx = 0;
  for (let i = 0; i < n; i++) {
    sxy += (i - xbar) * (y[i] - ybar);
    sxx += (i - xbar) * (i - xbar);
  }
  const slope = sxx === 0 ? 0 : sxy / sxx;
  const intercept = ybar - slope * xbar;
  let ss = 0;
  for (let i = 0; i < n; i++) {
    const fitted = intercept + slope * i;
    ss += (y[i] - fitted) ** 2;
  }
  // residual std with n-2 dof (regression), guard small n
  const dof = Math.max(1, n - 2);
  const residStd = Math.sqrt(ss / dof);
  return { slope, intercept, residStd, n };
}

/** log1p-transformed series, for log-linear commit fits (counts are >= 0). */
function logSeries(weekly: number[]): number[] {
  return weekly.map((v) => Math.log1p(Math.max(0, v)));
}

const countNonZero = (weekly: number[]): number => weekly.reduce((c, v) => (v > 0 ? c + 1 : c), 0);

// ---------------------------------------------------------------------------
//  SHIP  -  recency-weighted swing (commit axis)
// ---------------------------------------------------------------------------

/**
 * Descriptive ratio of the trailing-13-week slope vs the prior-window slope
 * (up to 39 weeks when the series allows). Reproducible and falsifiable, not
 * predictive. Windows are declared honestly in the return value: `priorWindow`
 * is the actual length used, never a hardcoded 39 when fewer points exist.
 * Reserves when the series is too short to form both windows.
 */
export function recencySwing(weekly: number[]): RecencySwing | Reserved {
  const recentWindow = 13 as const;
  const priorWindowMax = 39;
  if (weekly.length < recentWindow + 1) {
    return { reserved: true, reason: `<${recentWindow + 1} commit weeks for a recency window` };
  }
  const recent = weekly.slice(-recentWindow);
  const prior = weekly.slice(-(recentWindow + priorWindowMax), -recentWindow);
  if (prior.length < 2) {
    return { reserved: true, reason: 'prior window too short for a baseline slope' };
  }
  const priorWindow = prior.length; // honest actual window (C1)
  const recentSlope = linFit(logSeries(recent)).slope;
  const priorSlope = linFit(logSeries(prior)).slope;
  // ratio of slopes; when prior slope ~ 0 the ratio is undefined -> describe via sign
  const denom = Math.abs(priorSlope) < 1e-6 ? 1e-6 * Math.sign(priorSlope || 1) : priorSlope;
  const value = recentSlope / denom;
  let label: string;
  if (Math.abs(priorSlope) < 1e-6) {
    label = recentSlope > 1e-6 ? 'accelerating from a flat base' : recentSlope < -1e-6 ? 'declining from a flat base' : 'flat';
  } else if (value > 1.15) {
    label = 'accelerating';
  } else if (value < 0) {
    label = 'reversing';
  } else if (value < 0.85) {
    label = 'decelerating';
  } else {
    label = 'steady';
  }
  return { value, recentWindow, priorWindow, label, meta: m('recency-swing') };
}

// ---------------------------------------------------------------------------
//  SHIP-WITH-CAVEAT  -  commit-axis Sharpe
// ---------------------------------------------------------------------------

/**
 * Commit-axis "Sharpe": log-linear slope divided by residual std of the
 * ~52-week fit, with a +/- CI band (HAC/Newey-West-style: slope SE inflated for
 * residual autocorrelation). Sufficiency gate: requires >= 26 non-zero commit
 * weeks, else RESERVE.
 */
export function commitSharpe(weekly: number[]): CommitSharpe | Reserved {
  const nz = countNonZero(weekly);
  if (nz < MIN_COMMIT_WEEKS) {
    return { reserved: true, reason: `<${MIN_COMMIT_WEEKS} non-zero commit weeks` };
  }
  const y = logSeries(weekly);
  const { slope, residStd, n, intercept } = linFit(y);
  if (residStd === 0) {
    return { reserved: true, reason: 'zero residual variance (degenerate fit)' };
  }
  const value = slope / residStd;
  // slope standard error, then HAC inflation for lag-1 residual autocorrelation
  const xbar = (n - 1) / 2;
  let sxx = 0;
  for (let i = 0; i < n; i++) sxx += (i - xbar) ** 2;
  const slopeSe = residStd / Math.sqrt(sxx);
  // lag-1 autocorrelation of residuals (Newey-West, 1 lag)
  const resid = y.map((v, i) => v - (intercept + slope * i));
  let num = 0;
  let den = 0;
  for (let i = 1; i < n; i++) num += resid[i] * resid[i - 1];
  for (let i = 0; i < n; i++) den += resid[i] * resid[i];
  const rho = den === 0 ? 0 : num / den;
  const hac = Math.sqrt(Math.max(1, (1 + rho) / (1 - rho || 1e-6)));
  // CI on the Sharpe = (slope +/- z*se_hac) / residStd at ~95%
  const seSharpe = (1.96 * slopeSe * hac) / residStd;
  const dof = Math.max(1, n - 2);
  return {
    value,
    ci: [value - seSharpe, value + seSharpe],
    dof,
    meta: m('commit-sharpe'),
  };
}

// ---------------------------------------------------------------------------
//  SHIP-WITH-CAVEAT  -  commit-axis changepoint (k_max = 1)
// ---------------------------------------------------------------------------

/**
 * Single changepoint on the ~52 weekly commit points (CUSUM/PELT-lite, k_max=1):
 * scan every interior split, fit a slope each side, pick the split with the
 * largest |Δslope|, and only return it when |Δslope| exceeds ~2× the standard
 * error of the slope difference (the within-segment noise floor); otherwise
 * report "no significant changepoint". Using the per-segment slope SE rather
 * than the whole-series residual std avoids the trap where a genuine kink
 * inflates the single-line residual and masks itself.
 *
 * Undersampled series (< 8 points) RESERVE  -  insufficient, never "no changepoint".
 */
export function commitChangepoint(weekly: number[]): CommitChangepoint | NoChangepoint | Reserved {
  // Runs on the raw weekly cadence (commits/week), not log-space: a regime
  // change in commit cadence is a shift in the raw-count slope.
  const y = weekly;
  const n = y.length;
  if (n < 8) {
    return { reserved: true, reason: `<8 commit weeks for changepoint detection (got ${n})` };
  }
  // sum of (i - mean)^2 over m consecutive indices (denominator of slope SE)
  const sxxOf = (len: number): number => {
    const xbar = (len - 1) / 2;
    let s = 0;
    for (let i = 0; i < len; i++) s += (i - xbar) ** 2;
    return s;
  };
  let best:
    | { idx: number; delta: number; seDelta: number }
    | null = null;
  // keep a min segment of 3 points each side
  for (let k = 3; k <= n - 3; k++) {
    const left = linFit(y.slice(0, k));
    const right = linFit(y.slice(k));
    const delta = right.slope - left.slope;
    // SE of the slope difference from each side's residual std
    const seL = left.residStd / Math.sqrt(sxxOf(k) || 1);
    const seR = right.residStd / Math.sqrt(sxxOf(n - k) || 1);
    const seDelta = Math.sqrt(seL * seL + seR * seR);
    if (best === null || Math.abs(delta) > Math.abs(best.delta)) {
      best = { idx: k, delta, seDelta };
    }
  }
  // significance gate: |Δslope| > 2 * SE(Δslope). When both segments fit a clean
  // line (seDelta ~ 0) any real kink passes; on a noisy flat series it does not.
  if (best === null || Math.abs(best.delta) <= 2 * best.seDelta) {
    return { none: true, label: 'no significant changepoint detected' };
  }
  return { dateIndex: best.idx, deltaSlope: best.delta, meta: m('commit-changepoint') };
}

// ---------------------------------------------------------------------------
//  RESERVED signals (honest objects, never numbers)
// ---------------------------------------------------------------------------

/** code-leads-citation lag: ~5 yearly citation points are too short; undefined without a citation axis. */
export function lag(): Reserved {
  return {
    reserved: true,
    reason: 'citation series too short / axis absent for cross-correlation',
  };
}

/** axis alpha vs cohort: cohorts of <=12 (only 9 dual-axis) give power ~ 0. */
export function alpha(): Reserved {
  return {
    reserved: true,
    reason: 'cohort N too small for regression (power ~0)',
  };
}

/** gate-ETA: needs snapshot history; only one snapshot exists. */
export function gateEta(): Reserved {
  return {
    reserved: true,
    reason: 'needs snapshot history (1 snapshot exists)',
  };
}

// ---------------------------------------------------------------------------
//  per-entity signal quality / methodology gate
// ---------------------------------------------------------------------------

/**
 * Disclosure object for the visible "methodology gate" footnote: how much data
 * backed this entity and which derived signals shipped vs reserved.
 * `weekly` is the real commit series for the entity (caller passes
 * commitSeries(id)); `e` provides the citation axis.
 */
export function signalQuality(e: Entity, weekly: number[]): SignalQuality {
  const a2 = e.axes.openalex_citation_momentum;
  const citation_years = a2.by_year ? Object.keys(a2.by_year).length : 0;
  const commit_weeks = weekly.length;

  const shipped: string[] = [];
  const reserved: string[] = [];

  const tag = (name: string, result: unknown) =>
    (isReserved(result) ? reserved : shipped).push(name);

  tag('recency-swing', recencySwing(weekly));
  tag('commit-sharpe', commitSharpe(weekly));
  // changepoint: undersampled → reserved (insufficient); significant hit or
  // "none detected" on a sufficient series → shipped (honest computed result)
  const cp = commitChangepoint(weekly);
  if (isReserved(cp)) {
    reserved.push('commit-changepoint');
  } else {
    shipped.push('commit-changepoint');
  }
  reserved.push('code-leads-citation-lag');
  reserved.push('axis-alpha');
  reserved.push('gate-eta');

  return {
    commit_weeks,
    citation_years,
    derived_shipped: shipped,
    derived_reserved: reserved,
  };
}
