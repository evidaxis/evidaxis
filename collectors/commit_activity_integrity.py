"""Refuse a false-zero GitHub stats/commit_activity body.

The methodology records weekly totals from that endpoint. GitHub can answer
HTTP 200 with every week at 0 for a repository that has commits. When the
last 12 weeks are all zero, one commits-list probe checks that window, with
the caller's own fetch (the same auth as the stats call). A commit in the
window means the body is not trustworthy for this run: the caller treats it
as an unresolved stats response. The probe is not a source of weekly counts.
A confirmed empty window keeps the zeros. A failed probe keeps the zeros and
increments the run counter.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

WINDOW_WEEKS = 12

# One run's audit trail. Callers copy it into their provenance and reset it
# at the start of the run. Entries are repo + run date only: the commits
# response carries author fields and is never stored.
RUN_LOG: dict = {"refused": [], "probe_failed": 0}


def reset_run_log() -> None:
    RUN_LOG["refused"] = []
    RUN_LOG["probe_failed"] = 0


def run_log_snapshot() -> dict:
    return {
        "refused": [dict(row) for row in RUN_LOG["refused"]],
        "probe_failed": RUN_LOG["probe_failed"],
    }


def commits_probe_url(repo: str, since: str) -> str:
    return f"https://api.github.com/repos/{repo}/commits?since={since}&per_page=1"


def _week_total(week: object) -> float | None:
    if not isinstance(week, dict) or "total" not in week:
        return None
    total = week["total"]
    if isinstance(total, bool) or not isinstance(total, (int, float)):
        return None
    return float(total)


def last_twelve_all_zero(payload: object) -> bool:
    if not isinstance(payload, list) or len(payload) < WINDOW_WEEKS:
        return False
    totals = [_week_total(week) for week in payload[-WINDOW_WEEKS:]]
    return all(total == 0.0 for total in totals)


def window_start_iso(payload: object) -> str | None:
    """ISO UTC start of the oldest of the last 12 week buckets, or None."""
    if not isinstance(payload, list) or len(payload) < WINDOW_WEEKS:
        return None
    oldest = payload[-WINDOW_WEEKS]
    if not isinstance(oldest, dict):
        return None
    start = oldest.get("week")
    if isinstance(start, bool) or not isinstance(start, (int, float)):
        return None
    # GitHub's week field is unix seconds. A millisecond value is not that clock.
    if not 0 <= start <= 10**11:
        return None
    try:
        moment = datetime.fromtimestamp(int(start), tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _note_probe_failure(repo: str) -> None:
    RUN_LOG["probe_failed"] += 1
    print(f"  commit_activity probe failed for {repo}; keeping the stats zeros", flush=True)


def screen_commit_activity(
    repo: str,
    payload: object,
    fetch: Callable[[str], object],
    *,
    run_date: str,
) -> object:
    """Return `payload` to record, or None when the caller must drop it.

    None is the unresolved-stats outcome (the same outcome as a 202 that never
    resolved). `fetch` is one GET and returns the parsed JSON body. None, a
    non-list, or an exception is a failed probe: the payload is kept.
    """
    if not last_twelve_all_zero(payload):
        return payload
    since = window_start_iso(payload)
    if since is None:
        _note_probe_failure(repo)
        return payload
    try:
        body = fetch(commits_probe_url(repo, since))
    except Exception:
        _note_probe_failure(repo)
        return payload
    if not isinstance(body, list):
        _note_probe_failure(repo)
        return payload
    if len(body) >= 1:
        RUN_LOG["refused"].append({"repo": repo, "run_date": run_date})
        return None
    return payload
