import { describe, it, expect } from 'vitest';
import {
  polar,
  arcPath,
  scaleLinear,
  linePath,
  areaPath,
  beeswarmLayout,
  donutDash,
  gaugeNeedle,
  heatmapCells,
  niceTicks,
} from './charts';

describe('polar', () => {
  it('places 0deg at 12 o\'clock (straight up)', () => {
    const p = polar(0, 0, 10, 0);
    expect(p.x).toBeCloseTo(0, 6);
    expect(p.y).toBeCloseTo(-10, 6);
  });
  it('places 90deg at 3 o\'clock', () => {
    const p = polar(0, 0, 10, 90);
    expect(p.x).toBeCloseTo(10, 6);
    expect(p.y).toBeCloseTo(0, 6);
  });
});

describe('arcPath', () => {
  it('emits a valid SVG arc command with sweep flag 1', () => {
    const d = arcPath(60, 60, 43, -135, 135);
    expect(d).toMatch(/^M[-\d. ]+A43 43 0 [01] 1 [-\d. ]+$/);
  });
  it('sets large-arc flag when sweep exceeds 180deg', () => {
    const big = arcPath(0, 0, 10, -135, 135); // 270deg sweep
    const small = arcPath(0, 0, 10, -45, 45); // 90deg sweep
    expect(big).toContain('0 1 1'); // large-arc=1
    expect(small).toContain('0 0 1'); // large-arc=0
  });
});

describe('scaleLinear', () => {
  it('maps domain endpoints to range endpoints', () => {
    const s = scaleLinear([-2, 2], [0, 100]);
    expect(s(-2)).toBe(0);
    expect(s(2)).toBe(100);
    expect(s(0)).toBe(50);
  });
  it('handles inverted range (SVG y-down)', () => {
    const s = scaleLinear([0, 100], [200, 0]);
    expect(s(0)).toBe(200);
    expect(s(100)).toBe(0);
    expect(s(50)).toBe(100);
  });
  it('maps a zero-width domain to the range start deterministically', () => {
    const s = scaleLinear([5, 5], [0, 100]);
    expect(s(5)).toBe(0);
    expect(s(999)).toBe(0);
  });
});

describe('linePath / areaPath', () => {
  const pts = [
    { x: 0, y: 10 },
    { x: 10, y: 5 },
    { x: 20, y: 8 },
  ];
  it('linePath starts with M and uses L for the rest', () => {
    const d = linePath(pts);
    expect(d.startsWith('M0 10')).toBe(true);
    expect((d.match(/L/g) ?? []).length).toBe(2);
  });
  it('linePath of empty is empty', () => {
    expect(linePath([])).toBe('');
  });
  it('areaPath closes down to the baseline with Z', () => {
    const d = areaPath(pts, 32);
    expect(d.endsWith('Z')).toBe(true);
    expect(d).toContain('L20 32'); // last point dropped to baseline
    expect(d).toContain('L0 32'); // first point dropped to baseline
  });
});

describe('beeswarmLayout', () => {
  it('is deterministic and alternates sign by index', () => {
    const a = beeswarmLayout([10, 20, 30, 40]);
    const b = beeswarmLayout([10, 20, 30, 40]);
    expect(a.map((x) => x.dx)).toEqual(b.map((x) => x.dx));
    expect(a[0].dx).toBeLessThan(0); // index 0 -> negative
    expect(a[1].dx).toBeGreaterThan(0); // index 1 -> positive
  });
  it('preserves items and indices', () => {
    const out = beeswarmLayout(['a', 'b', 'c']);
    expect(out.map((x) => x.item)).toEqual(['a', 'b', 'c']);
    expect(out.map((x) => x.index)).toEqual([0, 1, 2]);
  });
});

describe('donutDash', () => {
  it('0% hides the whole ring, 100% reveals it', () => {
    const r = 52;
    const circ = 2 * Math.PI * r;
    const zero = donutDash(0, r);
    const full = donutDash(100, r);
    expect(zero.dashOffset).toBeCloseTo(circ, 6);
    expect(full.dashOffset).toBeCloseTo(0, 6);
    expect(zero.circumference).toBeCloseTo(circ, 6);
  });
  it('50% reveals half', () => {
    const r = 52;
    const circ = 2 * Math.PI * r;
    expect(donutDash(50, r).dashOffset).toBeCloseTo(circ / 2, 6);
  });
  it('clamps out-of-range pct', () => {
    const r = 10;
    expect(donutDash(-50, r).dashOffset).toBeCloseTo(2 * Math.PI * r, 6); // -> 0%
    expect(donutDash(150, r).dashOffset).toBeCloseTo(0, 6); // -> 100%
  });
});

describe('gaugeNeedle', () => {
  it('z=0 points to the top of a -135..135 dial', () => {
    const g = gaugeNeedle(0, 60, 60, 43);
    expect(g.deg).toBeCloseTo(0, 6); // middle of arc
    expect(g.arcFraction).toBeCloseTo(0.5, 6);
    expect(g.tip.y).toBeLessThan(60); // tip above hub
  });
  it('z at domain max hits arc end and fraction 1', () => {
    const g = gaugeNeedle(2, 60, 60, 43);
    expect(g.deg).toBeCloseTo(135, 6);
    expect(g.arcFraction).toBeCloseTo(1, 6);
  });
  it('clamps z beyond the domain', () => {
    const g = gaugeNeedle(99, 60, 60, 43);
    expect(g.arcFraction).toBe(1);
  });
});

describe('heatmapCells', () => {
  it('normalises intensity by the series max', () => {
    const cells = heatmapCells([0, 5, 10]);
    expect(cells.map((c) => c.intensity)).toEqual([0, 0.5, 1]);
    expect(cells.map((c) => c.index)).toEqual([0, 1, 2]);
  });
  it('all-zero series -> all-zero intensity (no divide-by-zero)', () => {
    const cells = heatmapCells([0, 0, 0]);
    expect(cells.every((c) => c.intensity === 0)).toBe(true);
  });
  it('empty series -> empty', () => {
    expect(heatmapCells([])).toEqual([]);
  });
});

describe('niceTicks', () => {
  it('produces rounded ticks spanning the range', () => {
    const t = niceTicks(0, 100, 5);
    expect(t[0]).toBeLessThanOrEqual(0);
    expect(t[t.length - 1]).toBeGreaterThanOrEqual(100);
    // 1/2/5 nice rule at count=5 over [0,100] -> step 20
    expect(t).toEqual([0, 20, 40, 60, 80, 100]);
  });
  it('uses rounded steps for an awkward range', () => {
    const t = niceTicks(0, 1, 5);
    // step 0.2 -> ticks every 0.2
    expect(t).toContain(0.2);
    expect(t[0]).toBeLessThanOrEqual(0);
    expect(t[t.length - 1]).toBeGreaterThanOrEqual(1);
  });
  it('single value when min === max', () => {
    expect(niceTicks(7, 7)).toEqual([7]);
  });
});
