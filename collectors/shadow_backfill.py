"""shadow_backfill - reconstruct pre-capture history for RECONSTRUCTABLE signals only.

A new or renamed cohort would otherwise start as a blank slate. We can honestly fill
in the part of a system's past that is RECONSTRUCTABLE after the fact:
  - development velocity: weekly commit counts from git history (GitHub commit_activity),
  - (citation history is already reconstructable-by-definition from OpenAlex counts_by_year
    and is displayed directly; not duplicated here).

We can NOT reconstruct the Type-2 point-in-time signals (watchers, open issues, deps)
that Evidaxis captures weekly. Those are the moat, and their history is only what was
captured. So this tool writes to a SEPARATE namespace (data/observations/backfill/) and
stamps every record `reconstructable: true` with the method and source. The site renders
this series ONLY under an explicit "reconstructed history (not point-in-time capture)"
label. Presenting reconstructed data as captured would destroy the honesty that is the
whole moat; the namespace + flag + label make that structurally impossible.

New code, outside frozen etl/. Pure standard library (+ `gh auth token` for the API).

Usage:
  python collectors/shadow_backfill.py [--limit N] [--repos owner/name ...]
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEEDS = REPO / "etl/seeds.json"
ID_MAP = REPO / "etl/id_map.json"
OUT_DIR = REPO / "data/observations/backfill"
UA = "evidaxis-shadow-backfill/1.0 (+https://evidaxis.org)"


def _token() -> str | None:
    import os
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    try:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or None
    except Exception:
        return None


def week_period(unix_ts: int) -> str:
    """Convert a week-start unix timestamp to an ISO-week period string (YYYY-wWW)."""
    iso = datetime.fromtimestamp(unix_ts, tz=timezone.utc).isocalendar()
    return f"{iso[0]}-w{iso[1]:02d}"


def backfill_record(entity_id: str, period: str, value: int, computed_at: str) -> dict:
    """One reconstructed weekly commit-velocity datum. reconstructable:true is MANDATORY."""
    return {
        "v": "backfill_1",
        "entity_id": entity_id,
        "period": period,
        "signal": "github_commit_velocity_weekly",
        "value": value,
        "reconstructable": True,
        "method": "GitHub commit_activity (weekly commits); reconstructed from git history, NOT a point-in-time capture",
        "source": "github.com/repos/{repo}/stats/commit_activity",
        "computed_at": computed_at,
    }


def fetch_commit_activity(repo: str, token: str | None, retries: int = 3) -> list | None:
    """Return [{'week': unix, 'total': n}, ...] (up to 52 weeks) or None.

    GitHub returns 202 (no body) while it computes stats for a cold repo; the first
    request triggers the computation, a warm one returns 200. We retry BRIEFLY on 202
    only, then give up (a cold repo is logged as skipped, not silently dropped, and a
    later warm run picks it up). A 200 with [] means the repo genuinely has no activity
    -> not retryable. This keeps the pass fast: warm repos return instantly.
    """
    url = f"https://api.github.com/repos/{repo}/stats/commit_activity"
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for _ in range(retries):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.status == 202:  # stats being generated; brief back off and retry
                    time.sleep(2)
                    continue
                data = json.loads(r.read().decode() or "[]")
                return data if isinstance(data, list) and data else None
        except urllib.error.HTTPError as e:
            if e.code == 202:
                time.sleep(2)
                continue
            return None
        except Exception:
            return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Reconstruct pre-capture commit-velocity history (labeled reconstructed).")
    ap.add_argument("--limit", type=int, default=None, help="cap number of repos (rest logged as skipped, not silent)")
    ap.add_argument("--repos", nargs="*", default=None, help="explicit owner/name list (default: all seeds)")
    args = ap.parse_args()

    id_map = json.loads(ID_MAP.read_text())
    seeds = json.loads(SEEDS.read_text())
    all_repos = args.repos or [e["github_repo"] for v in seeds["verticals"].values() for e in v["entities"]]
    repos = all_repos[: args.limit] if args.limit else all_repos
    dropped = len(all_repos) - len(repos)

    token = _token()
    if not token:
        print("shadow_backfill: no GitHub token (env or `gh auth token`); commit reconstruction will be rate-limited", file=sys.stderr)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    reconstructed, skipped = [], []

    for repo in repos:
        time.sleep(0.3)  # courtesy pacing; avoids GitHub secondary rate limits over ~100 repos
        entity_id = id_map.get(repo)
        if not entity_id:
            skipped.append({"repo": repo, "reason": "no entity_id"})
            continue
        activity = fetch_commit_activity(repo, token)
        if not activity:
            skipped.append({"repo": repo, "reason": "no commit_activity (202/rate/absent)"})
            continue
        records = [backfill_record(entity_id, week_period(w["week"]), int(w["total"]), now)
                   for w in activity if w.get("total", 0) > 0]
        if not records:
            skipped.append({"repo": repo, "reason": "no nonzero weeks"})
            continue
        (OUT_DIR / f"{entity_id}.backfill.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
        reconstructed.append({"repo": repo, "entity_id": entity_id, "weeks": len(records)})

    manifest = {
        "v": "backfill_manifest_1",
        "computed_at": now,
        "signal": "github_commit_velocity_weekly",
        "reconstructable": True,
        "note": "Reconstructed history, NOT point-in-time capture. Type-2 signals (watchers/issues/deps) are never backfilled.",
        "n_reconstructed": len(reconstructed),
        "n_skipped": len(skipped),
        "n_dropped_by_limit": dropped,
        "reconstructed": reconstructed,
        "skipped": skipped,
    }
    (OUT_DIR / "backfill_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"shadow_backfill: reconstructed {len(reconstructed)}, skipped {len(skipped)}, dropped-by-limit {dropped}")
    if dropped:
        print(f"  NOTE: --limit dropped {dropped} repos (NOT silent; rerun without --limit to complete)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
