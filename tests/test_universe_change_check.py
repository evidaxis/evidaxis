"""archive-integrity pairing rule for tracked-system changes (collectors/universe_change_check.py).

Runs against a throwaway git repository in tmp_path; no network.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))

import universe_change_check as ucc


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def _seeds(repo, names, indent=1):
    path = repo / "etl" / "seeds.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"verticals": {"v": {"entities": [{"github_repo": n} for n in names]}}}, indent=indent))


def _commit(repo, msg):
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", msg)
    return _git(repo, "rev-parse", "HEAD")


def _repo(tmp_path, names):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.org")
    _git(tmp_path, "config", "user.name", "t")
    _seeds(tmp_path, names)
    return _commit(tmp_path, "base")


def _departures(repo, date, names):
    path = repo / "data" / "observations" / date / "seed-departures.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"departures": [{"github_repo": n, "reason": "gone"} for n in names]}))
    return path


def test_removal_declared_in_departures_passes(tmp_path):
    before = _repo(tmp_path, ["a/one", "b/two", "c/three"])
    _seeds(tmp_path, ["a/one"])
    _departures(tmp_path, "2026-10-10", ["b/two", "c/three"])
    ok, msg = ucc.check(tmp_path, before, _commit(tmp_path, "retire"))
    assert ok, msg


def test_removal_without_any_record_fails(tmp_path):
    before = _repo(tmp_path, ["a/one", "b/two"])
    _seeds(tmp_path, ["a/one"])
    ok, msg = ucc.check(tmp_path, before, _commit(tmp_path, "hand removal"))
    assert not ok and "b/two" in msg


def test_removal_not_named_in_the_record_fails(tmp_path):
    before = _repo(tmp_path, ["a/one", "b/two", "c/three"])
    _seeds(tmp_path, ["a/one"])
    _departures(tmp_path, "2026-10-10", ["b/two"])
    ok, msg = ucc.check(tmp_path, before, _commit(tmp_path, "partial"))
    assert not ok and "c/three" in msg


def test_addition_hidden_in_a_reformatted_file_needs_a_frontier_manifest(tmp_path):
    # Codex review 2026-10-12: removed+added lines in a reformatted file looked removal-only.
    before = _repo(tmp_path, ["a/one", "b/two"])
    _seeds(tmp_path, ["a/one", "new/three"], indent=None)
    _departures(tmp_path, "2026-10-10", ["b/two"])
    ok, msg = ucc.check(tmp_path, before, _commit(tmp_path, "swap"))
    assert not ok and "new/three" in msg


def test_deleted_departures_record_does_not_pair(tmp_path):
    # Codex review 2026-10-12: a deleted record still shows up in `git diff --name-only`.
    _repo(tmp_path, ["a/one", "b/two"])
    _departures(tmp_path, "2026-10-03", ["b/two"])
    before = _commit(tmp_path, "old record")
    _seeds(tmp_path, ["a/one"])
    (tmp_path / "data" / "observations" / "2026-10-03" / "seed-departures.json").unlink()
    ok, msg = ucc.check(tmp_path, before, _commit(tmp_path, "remove and delete record"))
    assert not ok and "b/two" in msg


def test_record_moved_to_another_date_still_pairs(tmp_path):
    # Codex review 2026-10-12: a moved and edited record showed up as R and was dropped.
    _repo(tmp_path, ["a/one", "b/two", "c/three"])
    _departures(tmp_path, "2026-10-09", ["b/two"])
    before = _commit(tmp_path, "record under the wrong date")
    _seeds(tmp_path, ["a/one", "c/three"])
    (tmp_path / "data" / "observations" / "2026-10-09" / "seed-departures.json").unlink()
    _departures(tmp_path, "2026-10-10", ["b/two"])
    ok, msg = ucc.check(tmp_path, before, _commit(tmp_path, "move record, retire b/two"))
    assert ok, msg


def test_frontier_manifest_still_pairs_additions(tmp_path):
    before = _repo(tmp_path, ["a/one"])
    _seeds(tmp_path, ["a/one", "new/two"])
    frontier = tmp_path / "data" / "observations" / "2026-10-05" / "discovery-frontier.json"
    frontier.parent.mkdir(parents=True)
    frontier.write_text("{}")
    ok, msg = ucc.check(tmp_path, before, _commit(tmp_path, "tranche"))
    assert ok, msg


def test_cosmetic_edit_needs_nothing(tmp_path):
    before = _repo(tmp_path, ["a/one"])
    _seeds(tmp_path, ["a/one"], indent=4)
    ok, msg = ucc.check(tmp_path, before, _commit(tmp_path, "reformat"))
    assert ok and "no tracked-system change" in msg
