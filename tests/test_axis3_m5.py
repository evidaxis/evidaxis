"""The m5 correction follows the snapshot date, including delayed captures."""
from datetime import date, timedelta

import pytest

from collectors import score_m3 as scorer


@pytest.mark.parametrize("day,version,exact", [
    ("2026-10-09", "m3", False),
    ("2026-10-10", "m4", False),
    ("2026-10-16", "m4", False),
    ("2026-10-17", "m5", True),
    ("2026-10-24", "m5", True),
])
def test_snapshot_date_controls_exact_pair(tmp_path, monkeypatch, day, version, exact):
    parts = [(date(2026, 7, 6) + timedelta(weeks=i)).isoformat() for i in range(14)]
    series = {eid: list(zip(parts, [base + i * step for i in range(14)], strict=True))
              for eid, base, step in [("e_a", 100, 2), ("e_b", 200, 3)]}
    snap = {"snapshot_date": day, "captured_at": "2026-10-25T12:00:00Z",
            "snapshot_id": "fixture", "period": "2026-w42", "methodology_version": "m2", "axes": {},
            "entities": [{"entity_id": eid, "name": eid, "cohort": "c", "incumbent": False,
                          "axes": {scorer.AXIS1: {"slope": 0.2, "cohort_z": 1.1, "recent_weekly_commits": 6},
                                   scorer.AXIS2: {"status": "absent", "slope": None, "cohort_z": None}}}
                         for eid in series]}
    evidence = {"relative": "fixture.json", "sha256": "fixture", "commit": "fixture",
                "committed_at": "2026-10-05T12:00:00Z", "states": dict.fromkeys(parts, "CLEAN")}
    monkeypatch.setattr(scorer.identity, "derive_m4_series", lambda *_args, **_kwargs: series)
    monkeypatch.setattr(scorer.identity, "load_panel_m4", lambda *_args, **_kwargs: (series, "fixture"))
    monkeypatch.setattr(scorer.evaluator, "load_series", lambda *_args, **_kwargs: series)
    robust_z = scorer.evaluator._robust_z
    calls = []

    def observe(values, *, exact_pair=False):
        calls.append(exact_pair)
        # Fixed binary inputs reproduce the one-ulp residue on every test platform.
        return robust_z({"e_a": (4.77912349311153, 0.03605302477819056),
                         "e_b": (5.942799375126701, 0.00864513421882937)}, exact_pair=exact_pair)

    monkeypatch.setattr(scorer.evaluator, "_robust_z", observe)
    scored = scorer.score_snapshot(snap, observations=tmp_path, evidence=evidence, panel=set(series))
    assert scored["methodology_version"] == version
    assert calls == [exact]
    assert [e["axes"][scorer.AXIS3]["cohort_z"] for e in scored["entities"]] == (
        [0.0, 0.0] if exact else [-0.674, 0.0])
    assert all(not e["axes"][scorer.AXIS3]["rising_vote"] for e in scored["entities"])
    card = scorer.card_text("---\nscore:\n  snapshot_id: fixture\n---\n", scored["entities"][0], scored)
    assert scorer.SPECS[version]["estimand"] in card
    if exact:
        assert "exact residual z = 0" in scored["axes"][scorer.AXIS3]
