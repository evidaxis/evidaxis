"""Owner patterns remain private even when a tracked file fails the gate."""
import os
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/owner_trace_check.py"


@pytest.fixture
def tracked_repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "notes.txt").write_text("ordinary text\nFictional-Steward42\n", encoding="utf-8")
    for name in ("data/a.txt", "etl/a.txt", "entities/a.txt", "web/.foundation-check/fixtures/a.html"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Fictional-Steward42\n", encoding="utf-8")
    (tmp_path / "binary.bin").write_bytes(b"\0Fictional-Steward42\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    (tmp_path / "untracked.txt").write_text("Fictional-Steward42\n", encoding="utf-8")
    return tmp_path


def run_check(repo, **patterns):
    env = {k: v for k, v in os.environ.items()
           if k not in {"EVX_OWNER_PATTERNS", "EVX_OWNER_PATTERNS_FILE"}}
    return subprocess.run([sys.executable, str(SCRIPT)], cwd=repo,
                          env={**env, **patterns}, capture_output=True, text=True)


@pytest.mark.parametrize("from_file", [False, True])
def test_ere_finding_is_private_and_scoped(tracked_repo, tmp_path, from_file):
    patterns = "absent-synthetic-value\nfictional[- ]steward[[:digit:]]+"
    if from_file:
        path = tmp_path / "private-patterns.txt"
        path.write_text(patterns, encoding="utf-8")
        result = run_check(tracked_repo, EVX_OWNER_PATTERNS_FILE=str(path))
    else:
        result = run_check(tracked_repo, EVX_OWNER_PATTERNS=patterns)
    assert result.returncode == 1
    assert result.stdout.splitlines() == [
        "notes.txt:2: owner trace (pattern 2)", "owner-trace check: 1 findings"]
    assert "Fictional" not in result.stdout
    assert not result.stderr
    (tracked_repo / "notes.txt").write_text("ordinary text\n", encoding="utf-8")
    clean = run_check(tracked_repo, EVX_OWNER_PATTERNS=patterns)
    assert clean.returncode == 0
    assert clean.stdout == "owner-trace check: 0 findings\n"


def test_identifier_in_a_path_is_never_printed(tracked_repo):
    named = tracked_repo / "docs" / "Fictional-Steward42-notes.txt"
    named.parent.mkdir()
    named.write_text("Fictional-Steward42 again\n", encoding="utf-8")
    subprocess.run(["git", "add", "docs"], cwd=tracked_repo, check=True)
    result = run_check(tracked_repo, EVX_OWNER_PATTERNS="fictional[- ]steward[[:digit:]]+")
    assert result.returncode == 1
    assert "Fictional" not in result.stdout and "Steward" not in result.stdout
    assert "owner trace in its path (pattern 1)" in result.stdout
    assert "owner-trace check: 3 findings" in result.stdout


def test_newline_in_a_file_name_keeps_masking_aligned(tracked_repo):
    for name, text in (("0\nextra.txt", "plain\n"), ("Fictional-Steward42.txt", "Fictional-Steward42\n"),
                       ("z.txt", "plain\n")):
        (tracked_repo / name).write_text(text, encoding="utf-8")
        subprocess.run(["git", "add", "--", name], cwd=tracked_repo, check=True)
    result = run_check(tracked_repo, EVX_OWNER_PATTERNS="fictional[- ]steward[[:digit:]]+")
    assert result.returncode == 1
    assert "Fictional" not in result.stdout and "Steward" not in result.stdout


def test_dash_file_and_symlink_target_are_checked(tracked_repo):
    (tracked_repo / "-").write_text("Fictional-Steward42\n", encoding="utf-8")
    os.symlink("/home/Fictional-Steward42/private-notes.txt", tracked_repo / "link")
    subprocess.run(["git", "add", "--", "-", "link"], cwd=tracked_repo, check=True)
    result = run_check(tracked_repo, EVX_OWNER_PATTERNS="fictional[- ]steward[[:digit:]]+")
    assert result.returncode == 1
    assert "-:1: owner trace (pattern 1)" in result.stdout
    assert "owner trace in its link target (pattern 1)" in result.stdout
    assert "Fictional" not in result.stdout and "Steward" not in result.stdout


def test_missing_patterns_skip_without_git(tmp_path):
    result = run_check(tmp_path)
    assert result.returncode == 0
    assert result.stdout == "owner-trace check skipped: no patterns\n"


def test_invalid_pattern_fails_without_disclosing_it(tracked_repo):
    result = run_check(tracked_repo, EVX_OWNER_PATTERNS="[private-synthetic-value")
    assert result.returncode == 2
    assert "private-synthetic-value" not in result.stdout + result.stderr
