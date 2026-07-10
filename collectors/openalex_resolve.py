"""openalex_resolve - candidate finder + allowlist applier for missing OpenAlex work IDs.

Why: axis 2 (OpenAlex citation momentum) cannot fire for 105/135 entities because
`openalex_work_ids` is empty in the seeds, including systems with famous papers
(vLLM, AlphaFold3). This tool (1) queries the OpenAlex API for candidate works per
entity with a transparent score+reason, (2) after human/live-web verification of
candidates, applies the curated allowlist to `etl/seeds.json` ON DISK — an explicit,
git-auditable config change (deliberately NOT runtime injection into the frozen
collector: the archive's provenance must show WHEN and WHY the inputs changed).

Pipeline: --limit/--entity candidates run -> etl/openalex_candidates.json ->
verification (live-web cross-check) -> etl/openalex_allowlist.json (curated) ->
--apply-allowlist merges status="linked" work_ids into etl/seeds.json.

New code, lives OUTSIDE the frozen etl/. Pure standard library; injectable network
layer so tests run offline.

Usage:
  python collectors/openalex_resolve.py                    # all entities missing ids
  python collectors/openalex_resolve.py --limit 5          # smoke run
  python collectors/openalex_resolve.py --entity e_XXXX
  python collectors/openalex_resolve.py --apply-allowlist  # merge into seeds.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parent.parent
SNAPSHOTS = REPO / "data" / "snapshots"
CANDIDATES = REPO / "etl" / "openalex_candidates.json"
ALLOWLIST = REPO / "etl" / "openalex_allowlist.json"
SEEDS = REPO / "etl" / "seeds.json"
ID_MAP = REPO / "etl" / "id_map.json"


def _load_credentials() -> tuple[str, str]:
    """API key + mailto from env or gitignored etl/.env. Key never reaches logs."""
    api_key = os.environ.get("OPENALEX_API_KEY", "").strip()
    mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    env_path = REPO / "etl" / ".env"
    if env_path.is_file() and (not api_key or not mailto):
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if not api_key:
                m = re.match(r"\s*OPENALEX_API_KEY\s*=\s*(\S+)", line)
                if m:
                    api_key = m.group(1).strip().strip('"').strip("'")
            if not mailto:
                m = re.match(r"\s*OPENALEX_MAILTO\s*=\s*(\S+)", line)
                if m:
                    mailto = m.group(1).strip().strip('"').strip("'")
    return api_key, mailto


def fetch_json(url: str) -> dict[str, Any]:
    """Default network fetcher: polite 1s spacing, 3 retries with backoff."""
    time.sleep(1.0)
    req = urllib.request.Request(url, headers={"User-Agent": "evidaxis-resolve/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            return {}
        except Exception:  # network layer: degrade to "no results"
            time.sleep(2 ** attempt)
            continue
    return {}


def score_candidate(work: dict[str, Any], entity_name: str, github_repo: str) -> tuple[float, str]:
    """Transparent 0-1 score for a candidate work. Pure function."""
    score = 0.0
    reasons = []
    title = (work.get("title") or "").lower()
    name_lower = entity_name.lower()
    year = work.get("publication_year") or 0
    if year and year < 2015:
        return 0.0, "year < 2015"
    if title == name_lower:
        score += 0.5
        reasons.append("exact title match")
    elif f"{name_lower}:" in title:
        score += 0.4
        reasons.append("title prefix match")
    elif name_lower in title:
        score += 0.2
        reasons.append("title contains name")
    if github_repo:
        repo_parts = github_repo.lower().replace("/", " ").replace("-", " ").split()
        overlap = sum(1 for p in repo_parts if p in title and len(p) > 2)
        if overlap:
            boost = min(0.3, overlap * 0.1)
            score += boost
            reasons.append(f"repo token overlap (+{boost:.1f})")
    if (work.get("cited_by_count") or 0) >= 50:
        score += 0.2
        reasons.append("high citations (>=50)")
    return min(1.0, score), ", ".join(reasons)


def get_candidates(entity: dict[str, Any], fetch_fn: Callable[[str], dict[str, Any]],
                   api_key: str, mailto: str) -> list[dict[str, Any]]:
    """Find + score candidate works for one entity (injected fetch => offline tests)."""
    name = entity.get("name", "")
    if not name:
        return []
    encoded = urllib.parse.quote(name)
    base = "https://api.openalex.org/works?per-page=5"
    params = []
    if api_key:
        params.append(f"api_key={api_key}")
    if mailto:
        params.append(f"mailto={mailto}")
    auth = "&" + "&".join(params) if params else ""
    urls = [
        f"{base}&search={encoded}{auth}",
        f"{base}&filter=title.search:{encoded}{auth}",
    ]
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for url in urls:
        for work in (fetch_fn(url).get("results") or []):
            work_id = (work.get("id") or "").split("/")[-1]
            if not work_id or work_id in seen:
                continue
            seen.add(work_id)
            score, reason = score_candidate(work, name, entity.get("github_repo", ""))
            out.append({
                "work_id": work_id,
                "title": work.get("title", ""),
                "year": work.get("publication_year"),
                "cited_by_count": work.get("cited_by_count", 0),
                "score": round(score, 2),
                "reason": reason,
            })
    out.sort(key=lambda c: c["score"], reverse=True)
    return out


def merge_allowlist_into_seeds(seeds: dict[str, Any], allowlist: dict[str, Any],
                               id_map: dict[str, str]) -> tuple[int, list[str]]:
    """Merge status=linked work_ids into seeds entities (matched repo->entity_id).
    Pure function: mutates `seeds` in place, returns (n_changed, notes)."""
    changed = 0
    notes: list[str] = []
    for vertical in seeds.get("verticals", {}).values():
        for ent in vertical.get("entities", []):
            repo = ent.get("github_repo")
            eid = id_map.get(repo)
            entry = allowlist.get(eid) if eid else None
            if not entry or entry.get("status") != "linked":
                continue
            work_ids = list(entry.get("work_ids") or [])
            if not work_ids or ent.get("openalex_work_ids") == work_ids:
                continue
            if ent.get("openalex_work_ids"):
                notes.append(f"  {eid} ({repo}): OVERWRITE {ent['openalex_work_ids']} -> {work_ids}")
            ent["openalex_work_ids"] = work_ids
            changed += 1
            notes.append(f"  {eid} ({repo}): linked {work_ids}")
    return changed, notes


def apply_allowlist() -> int:
    """--apply-allowlist: explicit on-disk seeds.json update (git-auditable)."""
    if not ALLOWLIST.is_file():
        print(f"openalex_resolve: no allowlist at {ALLOWLIST.relative_to(REPO)}")
        return 1
    allowlist = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    seeds = json.loads(SEEDS.read_text(encoding="utf-8"))
    id_map = json.loads(ID_MAP.read_text(encoding="utf-8"))
    changed, notes = merge_allowlist_into_seeds(seeds, allowlist, id_map)
    for n in notes:
        print(n)
    if not changed:
        print("openalex_resolve: seeds already up to date (no-op)")
        return 0
    SEEDS.write_text(json.dumps(seeds, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"openalex_resolve: updated {changed} seed entit{'y' if changed == 1 else 'ies'} in {SEEDS.relative_to(REPO)}")
    return 0


def _latest_snapshot() -> dict[str, Any]:
    snaps = sorted(SNAPSHOTS.glob("*/snapshot.json"), key=lambda p: p.parent.name)
    if not snaps:
        return {}
    return json.loads(snaps[-1].read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve missing OpenAlex work IDs.")
    ap.add_argument("--limit", type=int, help="max entities to process")
    ap.add_argument("--entity", type=str, help="one entity_id")
    ap.add_argument("--apply-allowlist", action="store_true",
                    help="merge curated allowlist into etl/seeds.json (on disk)")
    args = ap.parse_args()

    if args.apply_allowlist:
        return apply_allowlist()

    snapshot = _latest_snapshot()
    if not snapshot:
        print("openalex_resolve: no snapshot found")
        return 1
    targets = [e for e in snapshot.get("entities", [])
               if not e.get("openalex_work_ids") and e.get("entity_id")]
    if args.entity:
        targets = [e for e in targets if e["entity_id"] == args.entity]
    if args.limit:
        targets = targets[: args.limit]

    api_key, mailto = _load_credentials()
    results: dict[str, Any] = {}
    if CANDIDATES.is_file():
        results = json.loads(CANDIDATES.read_text(encoding="utf-8"))

    print(f"openalex_resolve: {len(targets)} entities missing openalex_work_ids")
    for i, entity in enumerate(targets, 1):
        eid = entity["entity_id"]
        print(f"[{i}/{len(targets)}] {entity.get('name')} ({eid})")
        results[eid] = {
            "entity_id": eid,
            "github_repo": entity.get("github_repo"),
            "display_name": entity.get("name"),
            "candidates": get_candidates(entity, fetch_json, api_key, mailto),
        }
        # Incremental save: an interrupted run keeps everything fetched so far.
        CANDIDATES.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    print(f"openalex_resolve: wrote {CANDIDATES.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
