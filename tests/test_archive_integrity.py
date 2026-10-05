"""Committed-archive integrity (renewal CP-6) — the local mirror of
.github/workflows/archive-integrity.yml.

Unlike the pipeline tests (which validate freshly-generated tmp artifacts),
these assert the PUBLISHED tree: every committed snapshot verifies against its
own SHA256SUMS, the taxonomy-v2 remap is idempotent on the committed snapshot,
and the genesis snapshot stays byte-identical to the immutable deposit copy.
This is the check that would have caught the 2026-07-01 SHA256SUMS defect
(post-steps mutated the bundle after sums were written; see that folder's
ERRATA.md) before it shipped.
"""
import subprocess
import sys
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))

from refresh_sums import BUNDLE, _sums_text
from collectors.universe_integrity import check_range, departure_repos

GENESIS_DATE = "2026-06-27"
GENESIS_FILES = ("SHA256SUMS", "snapshot.json", "manifest.json",
                 "provenance.json", "archive-pointers.json")


def _snapshot_dirs():
    root = REPO / "data" / "snapshots"
    return sorted(p for p in root.iterdir() if p.is_dir())


def test_every_committed_snapshot_matches_its_sums():
    dirs = _snapshot_dirs()
    assert dirs, "no committed snapshots found"
    for snap_dir in dirs:
        sums = snap_dir / "SHA256SUMS"
        assert sums.exists(), f"{snap_dir.name}: SHA256SUMS missing"
        assert sums.read_text() == _sums_text(snap_dir), (
            f"{snap_dir.name}: SHA256SUMS does not match actual bytes "
            f"(a post-step mutated the bundle after sums were written?)"
        )


def test_refresh_sums_verify_cli_is_green():
    """The exact command CI runs must pass against the committed tree."""
    proc = subprocess.run(
        [sys.executable, "collectors/refresh_sums.py", "--verify"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_taxonomy_v2_idempotent_on_committed_snapshot():
    proc = subprocess.run(
        [sys.executable, "collectors/taxonomy_v2.py", "--verify"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_genesis_snapshot_byte_identical_to_deposit():
    for fn in GENESIS_FILES:
        live = REPO / "data" / "snapshots" / GENESIS_DATE / fn
        frozen = REPO / "genesis-deposit" / "data" / fn
        assert frozen.exists(), f"genesis-deposit/data/{fn} missing"
        assert live.exists(), f"live genesis {fn} missing"
        assert live.read_bytes() == frozen.read_bytes(), (
            f"{fn}: live genesis snapshot drifted from the immutable deposit "
            f"(I5 escalation trigger — historical bytes must never change)"
        )


def test_bundle_order_matches_frozen_collector():
    """refresh_sums keeps collect.py's exact trio order as a PREFIX; dropped.json
    was consciously appended 2026-07-10 (live-sweep: advertised but unpinned) and
    is optional (skipped when absent), so older sums stay byte-identical."""
    assert BUNDLE == ("snapshot.json", "manifest.json", "provenance.json")
    # dropped.json pins forward-only (cutover), never retro (append-only sums).
    from refresh_sums import FORWARD_EXTRAS
    assert FORWARD_EXTRAS == (("dropped.json", "2026-07-11"),)


@pytest.fixture
def universe_tree(tmp_path):
    """Real git trees exercise the CI diff without making any commits."""
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "-q")

    def tree(repos, files=None):
        seeds = tmp_path / "etl/seeds.json"
        seeds.parent.mkdir(exist_ok=True)
        seeds.write_text(json.dumps({"verticals": {"test": {"entities": [
            {"github_repo": repo} for repo in repos
        ]}}}))
        for name, payload in (files or {}).items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload))
        git("add", ".")
        return git("write-tree")

    return tmp_path, tree


def journal(repo="gone/tool", status=404, day="2026-10-05"):
    return {"schema_version": "departed_1", "date": day, "departed": [
        {"date": day, "github_repo": repo, "github_status": status}
    ]}


def test_removal_without_departed_is_red_even_with_frontier(universe_tree):
    repo, tree = universe_tree
    base = tree(["gone/tool", "live/tool"])
    head = tree(["live/tool"], {"data/observations/2026-10-05/discovery-frontier.json": {}})
    assert check_range(base, head, repo) == [
        "seed removal WITHOUT a paired departed.json record: gone/tool"
    ]


def test_removal_with_departed_needs_no_frontier(universe_tree):
    repo, tree = universe_tree
    base = tree(["gone/tool", "live/tool"])
    head = tree(["live/tool"], {"data/observations/2026-10-05/departed.json": journal()})
    assert check_range(base, head, repo) == []


@pytest.mark.parametrize("payload", [journal("unrelated/tool"), journal(status=200),
                                    journal(day="2026-10-04"), {}])
def test_wrong_departure_cannot_authorize_removal(universe_tree, payload):
    repo, tree = universe_tree
    base = tree(["gone/tool"])
    head = tree([], {"data/observations/2026-10-05/departed.json": payload})
    assert any("removal WITHOUT" in error for error in check_range(base, head, repo))


def test_mixed_change_requires_both_kinds_of_evidence(universe_tree):
    repo, tree = universe_tree
    base = tree(["gone/tool"])
    head = tree(["new/tool"], {"data/observations/2026-10-05/departed.json": journal()})
    assert any("additions WITHOUT" in error for error in check_range(base, head, repo))
    head = tree(["new/tool"], {"data/observations/2026-10-05/discovery-frontier.json": {}})
    assert check_range(base, head, repo) == []


def test_old_departure_cannot_be_reused_or_rewritten(universe_tree):
    repo, tree = universe_tree
    path = "data/observations/2026-10-05/departed.json"
    base = tree(["gone/tool"], {path: journal()})
    head = tree([])
    assert any("removal WITHOUT" in error for error in check_range(base, head, repo))
    head = tree([], {path: journal(status=410)})
    assert any("append-only" in error for error in check_range(base, head, repo))


def test_cosmetic_or_reordered_seeds_need_no_manifest(universe_tree):
    repo, tree = universe_tree
    base = tree(["live/tool", "org/other"])
    head = tree(["org/other", "Live/Tool"])
    assert check_range(base, head, repo) == []


def test_committed_departure_journals_are_valid():
    paths = list((REPO / "data/observations").glob("*/departed.json"))
    assert paths
    for path in paths:
        assert departure_repos(json.loads(path.read_text()), path.parent.name)
