/**
 * Pure, deterministic, DOM-free SVG geometry helpers.
 *
 * Ported from the approved prototype:
 *   projects/bonsai/evidaxis/proto/charts.js
 *   projects/bonsai/evidaxis/proto/cards/final-card.html  (inline SVG math)
 *
 * These functions compute coordinates and path strings ONLY. They never touch
 * `window`, `document`, or any runtime DOM. Astro chart components call them at
 * build time and emit the resulting <path>/<rect>/<circle>/<text> server-side,
 * so every chart's geometry exists in the static HTML (the GEO lever in §1 of
 * DESIGN-PORT-PLAN.md). They are unit-tested in charts.test.ts.
 */

export interface Point {
  x: number;
  y: number;
}

/** SVG-format a number with bounded precision and no trailing-zero noise. */
function n2(v: number, dp = 2): string {
  return Number.isFinite(v) ? Number(v.toFixed(dp)).toString() : '0';
}

/**
 * Polar -> cartesian, with 0deg at 12 o'clock (the prototype convention:
 * `(deg - 90) * pi/180`). Returns the point on a circle of radius `r`.
 */
export function polar(cx: number, cy: number, r: number, deg: number): Point {
  const a = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}

/**
 * Arc path between two angles (degrees) on a circle, swept clockwise.
 * Matches the prototype `arcPath`: large-arc flag set when the swept angle
 * exceeds 180deg, sweep flag = 1 (clockwise).
 */
export function arcPath(cx: number, cy: number, r: number, a0: number, a1: number): string {
  const p0 = polar(cx, cy, r, a0);
  const p1 = polar(cx, cy, r, a1);
  const large = a1 - a0 <= 180 ? 0 : 1;
  return `M${n2(p0.x)} ${n2(p0.y)} A${r} ${r} 0 ${large} 1 ${n2(p1.x)} ${n2(p1.y)}`;
}

/**
 * Linear scale from a numeric domain [d0,d1] to a range [r0,r1].
 * Returns a pure mapping function. A zero-width domain maps everything to r0
 * (avoids divide-by-zero; deterministic).
 */
export function scaleLinear(
  domain: [number, number],
  range: [number, number],
): (v: number) => number {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0;
  if (span === 0) return () => r0;
  const k = (r1 - r0) / span;
  return (v: number) => r0 + (v - d0) * k;
}

/** Polyline path "M.. L.. L.." through points. Empty input -> "". */
export function linePath(points: Point[]): string {
  if (points.length === 0) return '';
  return points
    .map((p, i) => `${i ? 'L' : 'M'}${n2(p.x, 1)} ${n2(p.y, 1)}`)
    .join(' ');
}

/**
 * Closed area path under a polyline down to `baseline` (a y coordinate),
 * for soft fills below sparklines / citation areas.
 */
export function areaPath(points: Point[], baseline: number): string {
  if (points.length === 0) return '';
  const top = linePath(points);
  const last = points[points.length - 1];
  const first = points[0];
  return `${top} L${n2(last.x, 1)} ${n2(baseline, 1)} L${n2(first.x, 1)} ${n2(baseline, 1)} Z`;
}

export interface BeeswarmOpts {
  /** half-width of the jitter band, in px (default 26, matching prototype span). */
  spread?: number;
  /** base offset before the index ramp (default 8). */
  base?: number;
}
export interface BeeForced<T> {
  item: T;
  /** signed horizontal offset from the column centre (deterministic). */
  dx: number;
  /** index within the (already-sorted) column. */
  index: number;
}

/**
 * Deterministic index-based jitter for a beeswarm column (ports the prototype:
 *   jitter = (i%2 ? +1 : -1) * (base + (i*13 % spread)) ).
 * No PRNG, no DOM: same input order -> same layout, every build.
 * Caller is responsible for sorting `items` first (the prototype sorts by
 * momentum ascending before laying out).
 */
export function beeswarmLayout<T>(
  items: T[],
  opts: BeeswarmOpts = {},
): BeeForced<T>[] {
  const spread = opts.spread ?? 26;
  const base = opts.base ?? 8;
  return items.map((item, i) => {
    const sign = i % 2 ? 1 : -1;
    const dx = sign * (base + ((i * 13) % spread));
    return { item, dx, index: i };
  });
}

export interface DonutDash {
  /** full circumference 2*pi*r. */
  circumference: number;
  /** dash array value (= circumference). */
  dashArray: number;
  /** dash offset that reveals `pct`% of the ring (0 -> full hidden). */
  dashOffset: number;
}

/**
 * Donut / ring stroke-dash math. `pct` in [0,100]. Out-of-range pct is clamped.
 * dashOffset = circumference * (1 - pct/100): 0% -> fully hidden, 100% -> full ring.
 */
export function donutDash(pct: number, r: number): DonutDash {
  const p = Math.max(0, Math.min(100, pct)) / 100;
  const circumference = 2 * Math.PI * r;
  return {
    circumference,
    dashArray: circumference,
    dashOffset: circumference * (1 - p),
  };
}

export interface GaugeNeedle {
  /** needle endpoint on the dial (radius r-1 in the prototype). */
  tip: Point;
  /** needle base near the hub (radius `hubR`). */
  base: Point;
  /** angle (deg) of the needle. */
  deg: number;
  /** fraction of the arc [0,1] the value occupies (clamped). */
  arcFraction: number;
  /** angle of the active-arc start (always the 0 mark for signed z gauges). */
  zeroDeg: number;
}

/**
 * Gauge needle geometry for a signed value `z` over `domain` (default [-2,2])
 * across an angular arc (default [-135,135] deg), matching the prototype gauge.
 * Returns the needle endpoints, the value angle, and the arc fraction so the
 * component can draw both the needle and the active arc from the zero mark.
 */
export function gaugeNeedle(
  z: number,
  cx: number,
  cy: number,
  r: number,
  opts: { domain?: [number, number]; arc?: [number, number]; hubR?: number } = {},
): GaugeNeedle {
  const [d0, d1] = opts.domain ?? [-2, 2];
  const [a0, a1] = opts.arc ?? [-135, 135];
  const hubR = opts.hubR ?? 6;
  const span = d1 - d0;
  const frac = span === 0 ? 0.5 : Math.max(0, Math.min(1, (z - d0) / span));
  const deg = a0 + (a1 - a0) * frac;
  const zeroFrac = span === 0 ? 0.5 : Math.max(0, Math.min(1, (0 - d0) / span));
  const zeroDeg = a0 + (a1 - a0) * zeroFrac;
  return {
    tip: polar(cx, cy, r - 1, deg),
    base: polar(cx, cy, hubR, deg),
    deg,
    arcFraction: frac,
    zeroDeg,
  };
}

export interface HeatCell {
  /** original value. */
  value: number;
  /** intensity in [0,1] = value / max (0 when max is 0). */
  intensity: number;
  /** zero-based index in the series. */
  index: number;
}

/**
 * Heatmap intensity per cell from a REAL series (replaces the prototype's
 * seeded-PRNG fake path: §1 / GAP). Intensity is value normalised by the series
 * max, in [0,1]; an all-zero or empty series yields all-zero intensities.
 */
export function heatmapCells(series: number[]): HeatCell[] {
  const max = series.reduce((m, v) => (v > m ? v : m), 0);
  return series.map((value, index) => ({
    value,
    index,
    intensity: max > 0 ? value / max : 0,
  }));
}

/**
 * "Nice" axis ticks. Returns evenly spaced, rounded tick values spanning
 * [min,max] with approximately `count` steps (default 5), using the standard
 * 1/2/5 * 10^k nice-number rule. Deterministic; useful for axis labels.
 */
export function niceTicks(min: number, max: number, count = 5): number[] {
  if (!Number.isFinite(min) || !Number.isFinite(max) || count < 1) return [];
  if (min === max) return [min];
  const range = niceNum(max - min, false);
  const step = niceNum(range / (count - 1), true);
  const niceMin = Math.floor(min / step) * step;
  const niceMax = Math.ceil(max / step) * step;
  const ticks: number[] = [];
  // guard against fp drift; round to step's decimal precision
  const dp = Math.max(0, -Math.floor(Math.log10(step)));
  for (let v = niceMin; v <= niceMax + step / 2; v += step) {
    ticks.push(Number(v.toFixed(dp)));
  }
  return ticks;
}

function niceNum(range: number, round: boolean): number {
  const exp = Math.floor(Math.log10(range));
  const frac = range / Math.pow(10, exp);
  let niceFrac: number;
  if (round) {
    if (frac < 1.5) niceFrac = 1;
    else if (frac < 3) niceFrac = 2;
    else if (frac < 7) niceFrac = 5;
    else niceFrac = 10;
  } else {
    if (frac <= 1) niceFrac = 1;
    else if (frac <= 2) niceFrac = 2;
    else if (frac <= 5) niceFrac = 5;
    else niceFrac = 10;
  }
  return niceFrac * Math.pow(10, exp);
}
