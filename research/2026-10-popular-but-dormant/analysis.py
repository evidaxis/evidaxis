#!/usr/bin/env python3
"""Popular but dormant: default-branch commit activity of open-source AI repositories by
GitHub star band, from one Evidaxis weekly snapshot. Standard library only.

    python3 analysis.py [--snapshot PATH] [--verify-live]

--snapshot     a snapshot.json (repo archive `data/snapshots/<date>/snapshot.json`, or the
               person-free projection published on Hugging Face `<date>/snapshot.json`).
               Default: the 2026-10-03 archive file of this repository.
--verify-live  re-check every zero-activity repository with 10,000+ stars against the GitHub
               commits API (needs GITHUB_TOKEN; organisation-owned repos only are written by
               name, the rest by entity id) and write verification.csv.

Outputs (next to this script): bands.csv, chart.svg, and with --verify-live verification.csv.
Data and outputs: CC0-1.0.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import urllib.request
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DEFAULT = REPO / "data/snapshots/2026-10-03/snapshot.json"
BANDS = [("<1k", 0, 1_000), ("1k-10k", 1_000, 10_000), ("10k-50k", 10_000, 50_000), ("50k+", 50_000, 10**12)]
BAND_OF: dict[str, str] = {}
WINDOW_WEEKS = 12  # `recent_weekly_commits` = mean of the last 12 weeks of GitHub commit_activity


def velocity(e: dict) -> dict:
    return (e.get("axes") or {}).get("github_commit_velocity") or {}


def band_of(stars: int) -> str:
    return next(name for name, lo, hi in BANDS if lo <= stars < hi)


def live_commits(repo: str, since: str, token: str) -> int | None:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/commits?since={since}T00:00:00Z&per_page=5",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "User-Agent": "evidaxis-research"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return len(json.load(r))
    except Exception:
        return None


def svg_chart(rows: list[dict], snapshot_date: str) -> str:
    # One series, one hue; values in text ink, not the series colour.
    w, h, left, top, bar_h, gap = 720, 300, 120, 74, 34, 18
    plot_w = w - left - 150
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
           f'font-family="Inter, Helvetica, Arial, sans-serif">',
           f'<rect width="{w}" height="{h}" fill="#fcfcfb"/>',
           '<text x="24" y="34" font-size="17" font-weight="600" fill="#0b0b0b">'
           'Share of open-source AI repos with no default-branch commits in 12 weeks</text>',
           f'<text x="24" y="56" font-size="13" fill="#52514e">By GitHub stars · Evidaxis registry, '
           f'{snapshot_date} · n = {sum(r["repos"] for r in rows):,}</text>']
    for i, r in enumerate(rows):
        y = top + i * (bar_h + gap)
        bw = max(2, plot_w * r["share"])
        out.append(f'<text x="{left - 12}" y="{y + bar_h / 2 + 5}" font-size="14" text-anchor="end" '
                   f'fill="#0b0b0b">{html.escape(r["band"])} stars</text>')
        out.append(f'<rect x="{left}" y="{y}" width="{plot_w}" height="{bar_h}" fill="#ecebe8"/>')
        out.append(f'<rect x="{left}" y="{y}" width="{bw:.1f}" height="{bar_h}" rx="4" fill="#2a78d6"/>')
        out.append(f'<text x="{left + plot_w + 12}" y="{y + bar_h / 2 + 5}" font-size="14" fill="#0b0b0b">'
                   f'{r["share"]:.0%}  <tspan fill="#52514e">({r["zero"]:,} of {r["repos"]:,})</tspan></text>')
    out.append('</svg>')
    return "\n".join(out)


def verify(ents: list[dict], snapshot_date: str) -> set[str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    since = (date.fromisoformat(snapshot_date) - timedelta(weeks=WINDOW_WEEKS)).isoformat()
    owners = json.loads((REPO / "etl/owner_types.json").read_text(encoding="utf-8"))["repos"]
    checks = []
    for e in ents:
        v = velocity(e)
        if (v.get("stars_not_scored") or 0) >= 10_000 and (v.get("recent_weekly_commits") or 0) == 0:
            repo = e.get("github_repo")
            n = live_commits(repo, since, token) if repo else None
            owner = owners.get(repo or "", {})
            # Person-free: only organisation-owned repositories are written by name.
            public = owner.get("full_name", repo) if owner.get("owner_type") == "Organization" else ""
            checks.append({"entity_id": e["entity_id"],
                           "name_or_repo": public,
                           "stars": v.get("stars_not_scored"),
                           "band": band_of(v.get("stars_not_scored") or 0),
                           "live_commits_since": since,
                           "live_commits_found": n,
                           "confirmed_zero": n == 0})
    with (HERE / "verification.csv").open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(checks[0].keys()))
        wr.writeheader()
        wr.writerows(checks)
    return {c["entity_id"] for c in checks if not c["confirmed_zero"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, default=DEFAULT)
    ap.add_argument("--verify-live", action="store_true")
    args = ap.parse_args()
    snap = json.loads(args.snapshot.read_text(encoding="utf-8"))
    snapshot_date = snap["snapshot_date"]
    ents = [e for e in snap["entities"] if velocity(e).get("slope") is not None]
    global BAND_OF
    BAND_OF = {e["entity_id"]: band_of(velocity(e).get("stars_not_scored") or 0) for e in ents}

    false_ids: set[str] = set()
    if args.verify_live:
        false_ids = verify(ents, snapshot_date)
    ents = [e for e in ents if e["entity_id"] not in false_ids]  # a stats-endpoint false zero is not dormancy

    rows = []
    for name, _lo, _hi in BANDS:
        members = [e for e in ents if band_of(velocity(e).get("stars_not_scored") or 0) == name]
        zero = [e for e in members if (velocity(e).get("recent_weekly_commits") or 0) == 0]
        falling = [e for e in members if velocity(e)["slope"] < 0]
        excluded = sum(1 for i in false_ids if i in BAND_OF and BAND_OF[i] == name)
        rows.append({"band": name, "repos": len(members), "zero": len(zero), "excluded_false_zero": excluded,
                     "share": len(zero) / len(members) if members else 0.0,
                     "declining_26w_share": round(len(falling) / len(members), 4) if members else 0.0})

    for r in rows:
        r["share"] = round(r["share"], 4)
    with (HERE / "bands.csv").open("w", newline="", encoding="utf-8") as fh:
        keys = ["band", "repos", "zero", "share", "declining_26w_share", "excluded_false_zero"]
        wr = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(rows)
    (HERE / "chart.svg").write_text(svg_chart(rows, snapshot_date), encoding="utf-8")
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
