"""Promotion accounting must reproduce the capture-time boundary in verdict 2.1."""
from datetime import datetime

import pytest

from collectors import axis3_inputs
from collectors.axis3_forward_count import forward_count


def test_verdict_forward_partitions():
    repo = axis3_inputs.REPO
    if axis3_inputs.git(repo, "rev-parse", "--is-shallow-repository").strip() == "true":
        pytest.skip("forward accounting needs first-add history; CI checkout uses fetch-depth: 0")
    # New weekly captures must not change the evidence available at the verdict.
    _commit, verdict_time = axis3_inputs.first_add(repo, "governance/AXIS3-DEPS-V2H2-VERDICT-2026-09-14.md")
    record, rows = forward_count(repo / "governance/AXIS3-DEPS-V2H2-SUPERSESSION-2026-08-18.md", as_of=verdict_time.isoformat())
    assert [r["partition"] for r in rows if r["forward"]] == ["2026-08-17", "2026-08-24", "2026-08-31"]
    excluded = next(r for r in rows if r["partition"] == "2026-08-10")
    assert excluded["state"] == "CLEAN"
    assert not excluded["forward"]
    assert datetime.fromisoformat(excluded["capture_committed_at"]) < datetime.fromisoformat(record["committed_at"])
    assert excluded["capture_commit"].startswith("eb918a11")


def test_shallow_clone_has_actionable_error(monkeypatch):
    monkeypatch.setattr(axis3_inputs, "git", lambda *_args: "true\n")
    with pytest.raises(ValueError, match=r"shallow clone.*fetch-depth: 0"):
        axis3_inputs.require_full_history(axis3_inputs.REPO)
