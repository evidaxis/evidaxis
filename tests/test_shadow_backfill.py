"""Shadow-backfill pure logic: ISO-week conversion and the mandatory reconstructed flag."""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))
from shadow_backfill import backfill_record, week_period


def test_week_period_format():
    p = week_period(1782604800)
    assert re.fullmatch(r"\d{4}-w\d{2}", p), p


def test_backfill_record_is_always_flagged_reconstructed():
    r = backfill_record("e_ABC", "2026-w20", 42, "2026-07-02T00:00:00Z")
    assert r["reconstructable"] is True
    assert "NOT a point-in-time capture" in r["method"]
    assert r["signal"] == "github_commit_velocity_weekly"
    assert r["value"] == 42
