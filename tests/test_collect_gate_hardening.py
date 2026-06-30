"""Hardening tests closing the two survivors found by the audit mutation sweep:
  1. robust_z lower winsorization bound (-3.0) was not pinned by any assertion.
  2. the ACTIVITY_FLOOR_WK dormancy guard ("a dormant repo is not rising") was not
     exercised — no entity sat in the (positive slope + positive z + recent_wk < floor)
     corner the guard exists to catch.

Both are brand-integrity invariants for an observatory whose badge means something,
so they get explicit coverage.
"""
from __future__ import annotations

import json
import re
from datetime import date

import pytest

import collect

CY = date.today().year


# ----------------------------------------------------------------- (1) winsor lower bound
def test_robust_z_lower_winsor_clamped_to_minus_three():
    # one value sits far below the median with a modest MAD -> raw z ~ -37, must clamp to -3.0
    out = collect.robust_z([-100, 8, 10, 12, 14])
    assert out[0] == pytest.approx(-3.0), "lower tail must winsorize to exactly -3.0"
    assert min(out) >= -3.0 and max(out) <= 3.0


def test_robust_z_upper_winsor_clamped_to_plus_three():
    out = collect.robust_z([8, 10, 12, 14, 1000])
    assert out[-1] == pytest.approx(3.0)


# ----------------------------------------------------------------- (2) ACTIVITY_FLOOR dormancy guard
# A 3-entity cohort with FLAT stars (axis-1 residualize is a no-op at n<4 anyway).
# E_dormant: the ONLY positive commit slope -> axis1 z > 0, AND a rising citation axis,
# so it WOULD be 2-axis rising — except its recent weekly commits are < ACTIVITY_FLOOR_WK,
# so the dormancy guard must demote it. Flip the floor to 0 (the mutation) and it becomes
# rising: that is exactly what this test forbids.
def _weekly(base, growth, n=30):
    return [max(0, round(base + growth * i)) for i in range(n)]


WEEKLY = {
    "z/dormant": _weekly(0, 0.18),    # 0..~5, steepest (only positive) slope, recent mean < 5
    "z/busy_a": _weekly(60, -0.6),    # high volume, declining -> slope < 0
    "z/busy_b": _weekly(50, -0.4),    # high volume, declining -> slope < 0
}
CITES = {
    "Wd": {CY - 5: 4, CY - 4: 9, CY - 3: 25, CY - 2: 55, CY - 1: 110, CY: 30},   # accelerating -> rising
    "Wa": {CY - 5: 80, CY - 4: 65, CY - 3: 50, CY - 2: 35, CY - 1: 20, CY: 5},   # declining
    "Wb": {CY - 5: 70, CY - 4: 60, CY - 3: 48, CY - 2: 33, CY - 1: 18, CY: 4},   # declining
}
ENT = {
    "z/dormant": ("Dormant Riser", ["Wd"]),
    "z/busy_a": ("Busy A", ["Wa"]),
    "z/busy_b": ("Busy B", ["Wb"]),
}


def _seeds():
    return {
        "domain": {"slug": "ai", "label": "Artificial Intelligence"},
        "verticals": {
            "floor-cohort": {
                "label": "Floor Cohort",
                "industry_slug": "floor-industry",
                "subniche_slug": "floor-subniche",
                "entities": [
                    {"github_repo": repo, "entity_type": "repo", "name": name,
                     "homepage": None, "openalex_work_ids": works}
                    for repo, (name, works) in ENT.items()
                ],
            }
        },
    }


def _fake_get_json(url, headers=None, tries=5):
    m = re.search(r"openalex\.org/works/([^?]+)", url)
    if m:
        counts = CITES[m.group(1)]
        return {"id": f"https://openalex.org/{m.group(1)}", "display_name": m.group(1),
                "cited_by_count": sum(counts.values()),
                "counts_by_year": [{"year": y, "cited_by_count": c} for y, c in counts.items()]}
    m = re.search(r"/repos/([^/]+/[^/]+)/stats/commit_activity", url)
    if m:
        return [{"total": t} for t in WEEKLY[m.group(1)]]
    m = re.search(r"/repos/([^/]+/[^/]+)$", url)
    if m:
        return {"stargazers_count": 1000, "created_at": "2020-01-01T00:00:00Z"}
    raise AssertionError(f"unexpected url {url}")


def _run(monkeypatch, isolated_repo):
    (collect.ROOT / "seeds.json").write_text(json.dumps(_seeds()))
    monkeypatch.setattr(collect, "_get_json", _fake_get_json)
    monkeypatch.setattr(collect.time, "sleep", lambda *a, **k: None)
    collect.main()
    snap = json.loads((collect.REPO / "data" / "snapshots" /
                       date.today().isoformat() / "snapshot.json").read_text())
    return {e["github_repo"]: e for e in snap["entities"]}


def test_dormant_repo_with_rising_signals_is_not_rising(monkeypatch, isolated_repo):
    ents = _run(monkeypatch, isolated_repo)
    d = ents["z/dormant"]
    a1 = d["axes"]["github_commit_velocity"]
    # preconditions: the guard's corner — positive slope, non-negative z, but dormant
    assert a1["slope"] is not None and a1["slope"] > 0, "dormant repo must have positive raw slope"
    assert a1["cohort_z"] is not None and a1["cohort_z"] >= 0, "dormant repo must be above-median on slope"
    assert a1["recent_weekly_commits"] < collect.ACTIVITY_FLOOR_WK, "scenario requires sub-floor activity"
    # the invariant: the dormancy floor must keep axis-1 OUT of the rising set, so the
    # entity cannot reach >=2-axis convergence even with a rising citation axis.
    assert "github_commit_velocity" not in d["convergent_axes"], "dormant axis must not count as rising"
    assert d["rising"] is False, "a dormant repo must never be badged rising (ACTIVITY_FLOOR guard)"
