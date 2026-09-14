"""Committed evidence for m3. Working-tree additions cannot confirm a partition."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from . import evaluate_axis3_v2h1 as evaluator
except ImportError:
    import evaluate_axis3_v2h1 as evaluator

REPO = Path(__file__).resolve().parent.parent
SANITY_DIR = "data/quarantine/axis3-deps-v2"
CALIBRATION = "3e51319d9817"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(f"git evidence unavailable: {result.stderr.strip()}")
    return result.stdout


def require_full_history(repo: Path) -> None:
    if git(repo, "rev-parse", "--is-shallow-repository").strip() == "true":
        raise ValueError("shallow clone: first-add commit times require full history (fetch-depth: 0 / git fetch --unshallow)")


def first_add(repo: Path, relative: str) -> tuple[str, datetime]:
    rows = git(repo, "log", "--diff-filter=A", "--format=%H %cI", "--reverse", "HEAD", "--", relative).splitlines()
    if not rows:
        raise ValueError(f"no first-add commit for {relative}")
    commit, timestamp = rows[0].split(" ", 1)
    return commit, datetime.fromisoformat(timestamp)


def committed_checks(repo: Path = REPO, captured_at: str | None = None) -> list[dict]:
    """Use byte-identical committed checks from the frozen v2h.1 calibration.

    Confirmation needs a successor capture. Its check must already be committed
    at the snapshot's capture time, or replay would see future source health.
    """
    require_full_history(repo)
    cutoff = datetime.fromisoformat(captured_at.replace("Z", "+00:00")) if captured_at else None
    if cutoff is not None and cutoff.tzinfo is None:
        raise ValueError("captured_at must include a timezone")
    checks = []
    for relative in git(repo, "ls-tree", "-r", "--name-only", "HEAD", "--", SANITY_DIR).splitlines():
        path = repo / relative
        if not path.match("*/sanity-check-*.json"):
            continue
        commit, added = first_add(repo, relative)
        if cutoff is not None and added > cutoff:
            continue
        blob = git(repo, "show", f"HEAD:{relative}").encode("utf-8")
        if not path.is_file() or path.read_bytes() != blob:
            raise ValueError(f"sanity artifact differs from committed bytes: {relative}")
        doc = json.loads(blob)
        if doc.get("calibration_sha256_prefix") != CALIBRATION:
            continue
        digest = hashlib.sha256(blob).hexdigest()
        if path.stem != f"sanity-check-{digest[:12]}":
            raise ValueError(f"sanity artifact hash mismatch: {relative}")
        checks.append({"path": path, "relative": relative, "sha256": digest,
                       "commit": commit, "committed_at": added.isoformat(),
                       "states": evaluator.partition_states(path)})
    return sorted(checks, key=lambda c: (max(c["states"], default=""), c["committed_at"], c["relative"]))


def sanity_as_of(captured_at: str, repo: Path = REPO) -> dict:
    checks = committed_checks(repo, captured_at)
    if not checks:
        raise ValueError("no committed v2h.1 sanity artifact at snapshot captured_at")
    return checks[-1]
