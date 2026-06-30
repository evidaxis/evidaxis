"""Math-core tests for etl/collect.py — the LOCKED scoring methodology.

Pure functions only (no network, no artifact writes): log_slope, robust_z,
residualize, citation_series, axis2_slope. Network is mocked by monkeypatching
collect._get_json to return canned dicts; nothing here hits OpenAlex/GitHub and
nothing writes the repo tree.

Exact math is asserted exactly where it is exact (log_slope on a geometric
series collapses to a clean ln-multiple; counts/totals are integers); floats
that carry MAD/least-squares rounding use math.isclose tolerance.
"""
from __future__ import annotations

import math

import pytest

import collect  # etl/ is on sys.path via tests/conftest.py


# ---------------------------------------------------------------- log_slope

def test_log_slope_too_short_returns_none():
    # n < 3 -> not enough points for a slope.
    assert collect.log_slope([]) is None
    assert collect.log_slope([5]) is None
    assert collect.log_slope([1, 2]) is None


def test_log_slope_geometric_series_is_exact_ln_multiple():
    # ys = [1,3,7,15] -> log1p = [ln2, ln4, ln8, ln16] = k*ln2 for k=1..4,
    # a perfectly linear series in x with slope exactly ln(2).
    got = collect.log_slope([1, 3, 7, 15])
    assert math.isclose(got, math.log(2.0), rel_tol=0, abs_tol=1e-12)


def test_log_slope_matches_hand_least_squares():
    ys = [2, 5, 9, 20, 33]
    n = len(ys)
    ly = [math.log1p(y) for y in ys]
    xs = list(range(n))
    mx, my = sum(xs) / n, sum(ly) / n
    den = sum((xs[i] - mx) ** 2 for i in range(n))
    num = sum((xs[i] - mx) * (ly[i] - my) for i in range(n))
    expected = num / den
    assert math.isclose(collect.log_slope(ys), expected, rel_tol=1e-12, abs_tol=1e-12)


def test_log_slope_strictly_increasing_is_positive():
    assert collect.log_slope([1, 2, 3, 4, 5, 6]) > 0


def test_log_slope_strictly_decreasing_is_negative():
    assert collect.log_slope([100, 50, 25, 10, 3]) < 0


def test_log_slope_flat_is_zero():
    # constant series -> log1p constant -> slope exactly 0.0.
    assert collect.log_slope([5, 5, 5, 5]) == 0.0
    assert collect.log_slope([0, 0, 0]) == 0.0


def test_log_slope_negative_values_clamped_not_crash():
    # max(0.0, float(y)) clamp: negatives floor at log1p(0)=0, no domain error.
    got = collect.log_slope([-5, -1, 0, 10])
    assert got is not None and math.isfinite(got)
    # the two leading negatives both map to log1p(0)=0, identical to a [0,0,0,10] series.
    assert math.isclose(got, collect.log_slope([0, 0, 0, 10]), rel_tol=0, abs_tol=1e-12)


# ---------------------------------------------------------------- robust_z

def test_robust_z_all_equal_maps_to_zeros():
    # mad==0 -> sd=1e-9, but v-med==0 for every element so the ratio is 0/sd = 0.0.
    assert collect.robust_z([7, 7, 7, 7]) == [0.0, 0.0, 0.0, 0.0]
    assert collect.robust_z([5, 5]) == [0.0, 0.0]    # even-n all-equal


def test_robust_z_mad_zero_oneoff_blows_up_then_clamps():
    # mostly-equal -> median-of-abs-devs is 0 (mad==0); the single off value
    # divides by 1e-9 -> enormous, winsorized to +3 (never unbounded).
    z = collect.robust_z([5, 5, 5, 5, 5, 9])
    assert z[:5] == [0.0, 0.0, 0.0, 0.0, 0.0]
    assert z[-1] == 3.0


def test_robust_z_single_giant_clamps_to_plus_three():
    z = collect.robust_z([1, 2, 3, 4, 5, 1000])
    assert max(z) == 3.0           # the giant is winsorized, not unbounded
    assert all(-3.0 <= v <= 3.0 for v in z)


def test_robust_z_odd_n_exact():
    # n=5 odd: med = sorted[2]=3. devs=|v-3|=[2,1,0,97,2], sorted=[0,1,2,2,97], mad=devs[2]=2.
    # sd=1.4826*2. Values in ORIGINAL order [1,2,3,100,5].
    vals = [1, 2, 3, 100, 5]
    sd = 1.4826 * 2.0
    expected = [max(-3.0, min(3.0, (v - 3) / sd)) for v in vals]
    got = collect.robust_z(vals)
    assert len(got) == len(expected)
    for g, e in zip(got, expected, strict=False):
        assert math.isclose(g, e, rel_tol=1e-12, abs_tol=1e-12)
    assert got[3] == 3.0           # the 100 winsorizes to +3


def test_robust_z_even_n_uses_two_middle_averages():
    # n=4 even: med = (sorted[1]+sorted[2])/2 = (2+3)/2 = 2.5.
    # devs=|v-2.5|=[1.5,0.5,0.5,1.5], sorted=[0.5,0.5,1.5,1.5], mad=(0.5+1.5)/2=1.0.
    vals = [1, 2, 3, 4]
    sd = 1.4826 * 1.0
    expected = [max(-3.0, min(3.0, (v - 2.5) / sd)) for v in vals]
    got = collect.robust_z(vals)
    for g, e in zip(got, expected, strict=False):
        assert math.isclose(g, e, rel_tol=1e-12, abs_tol=1e-12)


def test_robust_z_preserves_input_order():
    # output order tracks INPUT order (median computed on a sorted copy, not in place).
    z = collect.robust_z([3, 1, 2])
    # med=2; this is just a sanity check that index 0 (value 3) is positive, index 1 (value 1) negative.
    assert z[0] > 0 and z[1] < 0


# ---------------------------------------------------------------- residualize

def test_residualize_too_small_returns_unchanged():
    # n < 4 -> the size-dampener is skipped; identical object returned.
    zs = [1.0, 2.0, 3.0]
    out = collect.residualize(zs, [10, 20, 30])
    assert out is zs            # returned unchanged (same list)


@pytest.mark.parametrize("sizes", [[5, 5, 5, 5], [0, 0, 0, 0, 0]])
def test_residualize_equal_sizes_var_guard_no_crash(sizes):
    # all-equal sizes -> robust_z(log size) is all zeros -> var==0 guard (->1e-9),
    # cov==0 -> beta=0 -> residual == zs unchanged, and no ZeroDivisionError.
    zs = [float(i) for i in range(len(sizes))]
    out = collect.residualize(zs, sizes)
    assert all(math.isclose(o, z, rel_tol=0, abs_tol=1e-12) for o, z in zip(out, zs, strict=False))


def test_residualize_collapses_spread_when_z_is_linear_in_logsize():
    # The incumbent dampener: if z is an EXACT linear function of robust_z(log size),
    # regressing it out leaves a constant residual -> the spread (which is what feeds
    # the gate's z-comparison) collapses to ~0.
    sizes = [1, 10, 100, 1000, 10000]
    lz = collect.robust_z([math.log1p(s) for s in sizes])
    a, b = 2.0, 3.0
    zs = [a + b * v for v in lz]              # perfectly explained by size
    res = collect.residualize(zs, sizes)
    spread = max(res) - min(res)
    assert math.isclose(spread, 0.0, rel_tol=0, abs_tol=1e-9)


def test_residualize_keeps_size_orthogonal_signal():
    # Signal that is NOT explained by size must survive (residual spread stays large).
    sizes = [1, 10, 100, 1000, 10000]
    zs = [1.0, -1.0, 1.0, -1.0, 1.0]          # zig-zag, uncorrelated with monotone size
    res = collect.residualize(zs, sizes)
    assert (max(res) - min(res)) > 1.0        # real signal not flattened away


# ---------------------------------------------------------------- citation_series

def _patch_get_json(monkeypatch, table):
    """Route collect._get_json to a dict keyed by OpenAlex work id parsed from the url."""
    import re

    def fake(url, headers=None, tries=5):
        wid = re.search(r"/works/([^?]+)", url).group(1)
        return table.get(wid)

    monkeypatch.setattr(collect, "_get_json", fake, raising=True)


def _work(title, pairs):
    return {"display_name": title, "cited_by_count": sum(c for _, c in pairs),
            "counts_by_year": [{"year": y, "cited_by_count": c} for y, c in pairs]}


def test_citation_series_sums_across_multiple_works(monkeypatch):
    table = {
        "W1": _work("A", [(2020, 1), (2021, 2)]),
        "W2": _work("B", [(2020, 3), (2022, 4)]),
    }
    _patch_get_json(monkeypatch, table)
    by_year, raw = collect.citation_series(["W1", "W2"])
    assert by_year == {2020: 4, 2021: 2, 2022: 4}   # 2020 overlaps -> summed
    assert set(raw) == {"W1", "W2"}
    assert raw["W1"]["title"] == "A"


@pytest.mark.parametrize("bad", [None, "RATELIMIT", {"display_name": "x", "cited_by_count": 0}])
def test_citation_series_skips_none_ratelimit_and_missing_counts(monkeypatch, bad):
    # A good work plus one bad sibling; the bad one contributes nothing and is absent from raw.
    table = {"GOOD": _work("G", [(2021, 5)]), "BAD": bad}
    _patch_get_json(monkeypatch, table)
    by_year, raw = collect.citation_series(["GOOD", "BAD"])
    assert by_year == {2021: 5}
    assert set(raw) == {"GOOD"}                      # BAD never enters raw


def test_citation_series_none_count_coerced_to_zero(monkeypatch):
    # cited_by_count: None on a row must not blow the sum (the `(c or 0)` guard).
    table = {"W": {"display_name": "N", "counts_by_year": [
        {"year": 2020, "cited_by_count": None}, {"year": 2021, "cited_by_count": 3}]}}
    _patch_get_json(monkeypatch, table)
    by_year, _ = collect.citation_series(["W"])
    assert by_year == {2020: 0, 2021: 3}


def test_citation_series_row_missing_year_skipped(monkeypatch):
    # a row with year=None is skipped, not crashed on.
    table = {"W": {"display_name": "Y", "counts_by_year": [
        {"year": None, "cited_by_count": 9}, {"year": 2022, "cited_by_count": 4}]}}
    _patch_get_json(monkeypatch, table)
    by_year, _ = collect.citation_series(["W"])
    assert by_year == {2022: 4}


# ---------------------------------------------------------------- axis2_slope

def test_axis2_empty_work_ids_is_absent():
    # no monkeypatch needed: short-circuits before any fetch.
    assert collect.axis2_slope([], 2026) == ("absent", None, 0, {})


def test_axis2_no_by_year_is_absent(monkeypatch):
    # every work skipped (404 -> None) -> empty by_year -> absent.
    _patch_get_json(monkeypatch, {"W": None})
    assert collect.axis2_slope(["W"], 2026) == ("absent", None, 0, {})


def test_axis2_insufficient_when_fewer_than_three_completed_years(monkeypatch):
    # 2024,2025 completed + 2026 partial-current -> only 2 completed < AXIS2_MIN_YEARS(3).
    table = {"WI": _work("I", [(2024, 5), (2025, 3), (2026, 1)])}
    _patch_get_json(monkeypatch, table)
    status, slope, total, detail = collect.axis2_slope(["WI"], 2026)
    assert status == "insufficient"
    assert slope is None
    assert total == 9                              # total spans ALL years incl. partial current
    assert detail["by_year"] == {2024: 5, 2025: 3, 2026: 1}


def test_axis2_present_three_completed_drops_current_keeps_in_total(monkeypatch):
    # completed=[2022,2023,2024] (==3 -> no earliest drop); 2025 is partial-current:
    # dropped from the FIT but its 100 stays in TOTAL.
    table = {"WP": _work("P", [(2022, 2), (2023, 4), (2024, 8), (2025, 100)])}
    _patch_get_json(monkeypatch, table)
    status, slope, total, detail = collect.axis2_slope(["WP"], 2025)
    assert status == "present"
    assert total == 114                            # 2+4+8+100 -> current year counted in total
    # fit is over the three completed years only, current year excluded.
    assert math.isclose(slope, collect.log_slope([2, 4, 8]), rel_tol=1e-12, abs_tol=1e-12)
    assert detail["by_year"] == {2022: 2, 2023: 4, 2024: 8, 2025: 100}


def test_axis2_present_four_completed_drops_earliest_birth_year(monkeypatch):
    # completed=[2020,2021,2022,2023] (4 -> fit_years = completed[1:] = [2021,2022,2023]);
    # 2024 is partial-current (dropped from fit, kept in total). 2020 birth-year dropped from fit.
    table = {"WQ": _work("Q", [(2020, 1), (2021, 10), (2022, 20), (2023, 30), (2024, 7)])}
    _patch_get_json(monkeypatch, table)
    status, slope, total, _ = collect.axis2_slope(["WQ"], 2024)
    assert status == "present"
    assert total == 68                             # 1+10+20+30+7 -> everything counted in total
    # earliest (2020) AND current (2024) excluded from the fit; slope over [10,20,30].
    assert math.isclose(slope, collect.log_slope([10, 20, 30]), rel_tol=1e-12, abs_tol=1e-12)
    # and explicitly NOT the all-years slope (proves the earliest-drop actually changed the fit).
    assert not math.isclose(slope, collect.log_slope([1, 10, 20, 30]), rel_tol=1e-9)


def test_axis2_present_exactly_three_does_not_drop_earliest(monkeypatch):
    # boundary: 3 completed years stays at completed_years (no [1:] slice), fits all three.
    table = {"WT": _work("T", [(2021, 3), (2022, 6), (2023, 12), (2024, 99)])}
    _patch_get_json(monkeypatch, table)
    status, slope, total, _ = collect.axis2_slope(["WT"], 2024)
    assert status == "present"
    assert math.isclose(slope, collect.log_slope([3, 6, 12]), rel_tol=1e-12, abs_tol=1e-12)
    assert total == 120                            # 3+6+12+99


def test_axis2_present_aggregates_two_works_then_fits(monkeypatch):
    # multi-work aggregation feeds a single by_year before the year logic runs.
    table = {
        "WA": _work("A", [(2021, 1), (2022, 2), (2023, 3)]),
        "WB": _work("B", [(2021, 4), (2022, 5), (2023, 6), (2024, 50)]),
    }
    _patch_get_json(monkeypatch, table)
    status, slope, total, detail = collect.axis2_slope(["WA", "WB"], 2024)
    assert status == "present"
    assert detail["by_year"] == {2021: 5, 2022: 7, 2023: 9, 2024: 50}
    assert total == 71                             # 5+7+9+50
    assert math.isclose(slope, collect.log_slope([5, 7, 9]), rel_tol=1e-12, abs_tol=1e-12)
