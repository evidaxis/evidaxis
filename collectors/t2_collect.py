#!/usr/bin/env python3
"""Evidaxis Type-2 observation collector (t2_m0).

Captures genuinely NON-RECONSTRUCTABLE point-in-time signals that the existing
frozen etl/collect.py does NOT capture. The two scored axes (github_commit_velocity,
openalex_citation_momentum) are RECONSTRUCTABLE (Type-1): GitHub serves commit_activity
history and OpenAlex serves citation history. This collector captures Type-2 signals
whose point-in-time value is NOT served historically and cannot be back-filled:
  - watchers (subscribers_count)  -> reconstructable: false  (headline Type-2)
  - open_issues_count             -> reconstructable: partial

Design invariants (spar-27, 2026-07-01):
  * ADDITIVE: lives outside etl/; never touches the byte-frozen genesis code.
  * NOT SCORED: raw observation store only (capture-first; scoring is a later step).
  * APPEND-ONLY + RETRACTABLE: an error is corrected by appending a status-flip
    record (retract), never by deleting/rewriting history (integrity archive).
  * FULL PROVENANCE: every record carries source, endpoint, http_status, fetched_at,
    response_sha256, collector_version; the raw response is stored alongside.
  * person-free: only counts/metadata; no maintainer/author identities captured.

Usage:
  python3 collectors/t2_collect.py                                  # capture a snapshot
  python3 collectors/t2_collect.py --retract <obs_id> --reason "…"  # append a retraction
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gh_http  # shared GitHub path: App token (gh_auth), rate-limit waits, 401 refresh
from field_policy import filter_provenance

REPO = Path(__file__).resolve().parent.parent
COLLECTOR_VERSION = "t2_m0"
GITHUB_API = "https://api.github.com/repos/{repo}"
MAX_ERROR_RATE = 0.20  # above this the capture is DEGRADED and the run fails loudly

# (record_name, github_field, reconstructable, method) — the [K] adversarial verdict,
# baked into the data so the archive self-documents what is genuinely Type-2.
SIGNAL_SPEC = [
    ("watchers", "subscribers_count", "false", "GitHub serves no historical watcher time-series"),
    ("open_issues", "open_issues_count", "partial", "issues API with state filter; drifts on reopen"),
    ("forks", "forks_count", "partial", "fork events recoverable via GH Archive"),
    ("network", "network_count", "partial", "recoverable via GH Archive"),
    ("stars_reference_not_scored", "stargazers_count", "partial", "GH Archive; NOT scored per methodology"),
    ("size_kb", "size", "true", "current repo metadata"),
    ("pushed_at", "pushed_at", "true", "current repo metadata"),
]


def _fetch(url: str, token: str | None, tries: int = 5, timeout: int = 40) -> tuple[int, bytes]:
    """GET through gh_http: the GitHub App token when configured (else `token`),
    rate limits waited out (sleep until X-RateLimit-Reset / Retry-After, same
    request retried, no try consumed), a 401 on an App token refreshed once."""
    headers = {"User-Agent": "evidaxis-t2-collector", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last: Exception | None = None
    for attempt in range(tries):
        try:
            status, _resp_headers, body = gh_http.request(url, headers=headers, timeout=timeout)
        except gh_http.RateLimited as exc:
            # A limit that cannot be waited out (> 65 min, or 3 hits): this repo is an error.
            raise RuntimeError(f"GitHub rate limit not recoverable: {exc}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
            if attempt < tries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
        if status == 401:
            # Dead/revoked token: every subsequent call would fail identically.
            # Fail the whole run loudly instead of capturing a blind snapshot.
            raise RuntimeError("GitHub API 401 (token dead/revoked) - aborting capture")
        if status >= 500 and attempt < tries - 1:
            time.sleep(2 ** attempt)
            continue
        return status, body
    raise RuntimeError(f"unreachable retry exhaustion: {last}")


def _load_entities() -> list[dict]:
    seeds = json.loads((REPO / "etl/seeds.json").read_text())
    entities: list[dict] = []
    for vertical in seeds["verticals"].values():
        entities.extend(vertical["entities"])
    return entities


def capture() -> int:
    id_map = json.loads((REPO / "etl/id_map.json").read_text())
    entities = _load_entities()
    token = os.environ.get("GITHUB_TOKEN")

    now = datetime.now(timezone.utc)
    captured_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date = now.strftime("%Y-%m-%d")
    iso = now.isocalendar()
    period = f"{iso.year}-w{iso.week:02d}"

    out_dir = REPO / "data/observations" / date
    prov_dir = out_dir / "provenance"
    hist_dir = REPO / "data/observations/history"
    for directory in (prov_dir, hist_dir):
        directory.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    errors: list[dict] = []
    for entity in entities:
        repo = entity["github_repo"]
        entity_id = id_map.get(repo)
        url = GITHUB_API.format(repo=repo)
        try:
            status, body = _fetch(url, token)
        except Exception as exc:  # capture-first: one bad repo must not abort the snapshot
            errors.append({"repo": repo, "error": str(exc)})
            continue
        if status != 200:
            errors.append({"repo": repo, "http_status": status})
            continue

        data = json.loads(body)
        signals = {
            name: {"value": data.get(field), "reconstructable": recon, "method": method}
            for (name, field, recon, method) in SIGNAL_SPEC
        }
        obs_id = hashlib.sha256(f"{entity_id}|github_repo_pit|{captured_at}".encode()).hexdigest()[:16]
        record = {
            "v": "t2_obs_1",
            "observation_id": obs_id,
            "entity_id": entity_id,
            "github_repo": repo,
            "captured_at": captured_at,
            "period": period,
            "collector_version": COLLECTOR_VERSION,
            "source": "github_rest_v3",
            "endpoint": url,
            "http_status": status,
            "response_sha256": hashlib.sha256(body).hexdigest(),
            "signals": signals,
            "status": "active",
            "retraction": None,
        }
        records.append(record)
        # person-free: store the allowlisted system-level view, NEVER the raw owner/user object.
        # Integrity is preserved by response_sha256 (of the full upstream body) in the record.
        (prov_dir / f"{entity_id}.json").write_text(
            json.dumps(filter_provenance(data), indent=2, ensure_ascii=False)
        )
        with (hist_dir / f"{entity_id}.t2.jsonl").open("a") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    obs_text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    obs_path = out_dir / "observations.jsonl"
    obs_path.write_text(obs_text)
    obs_sha = hashlib.sha256(obs_text.encode()).hexdigest()

    error_rate = len(errors) / len(entities) if entities else 1.0
    degraded = len(records) == 0 or error_rate > MAX_ERROR_RATE
    manifest = {
        "collector_version": COLLECTOR_VERSION,
        "captured_at": captured_at,
        "date": date,
        "period": period,
        "entity_count": len(records),
        "error_count": len(errors),
        "error_rate": round(error_rate, 4),
        "max_error_rate": MAX_ERROR_RATE,
        "degraded": degraded,
        "errors": errors,
        "observations_sha256": obs_sha,
        "signal_spec": [
            {"name": n, "github_field": f, "reconstructable": r} for (n, f, r, _m) in SIGNAL_SPEC
        ],
        "note": "Type-2 (non-reconstructable) point-in-time capture; NOT scored; additive to frozen etl/.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    print(f"[t2_m0] captured {len(records)}/{len(entities)} entities @ {captured_at} ({period})")
    if errors:
        print(f"[t2_m0] errors ({len(errors)}): {json.dumps(errors, ensure_ascii=False)}")
    print(f"[t2_m0] observations.jsonl sha256={obs_sha[:12]} -> {obs_path}")
    if degraded:
        # A total/near-total failure must NOT be committed as a green heartbeat:
        # an empty day would read as "the world had no signals", which is false.
        print(f"[t2_m0] DEGRADED capture (records={len(records)}, error_rate={error_rate:.0%} "
              f"> {MAX_ERROR_RATE:.0%}) - failing the run")
        return 1
    return 0


def retract(obs_id: str, reason: str) -> int:
    """Append a status-flip record (never delete). Retractability = integrity."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    hist_dir = REPO / "data/observations/history"
    flipped = 0
    for hist_file in sorted(hist_dir.glob("*.t2.jsonl")):
        for line in hist_file.read_text().splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("observation_id") == obs_id and rec.get("status") == "active":
                flip = dict(rec)
                flip["status"] = "retracted"
                flip["retraction"] = {"retracted_at": now, "reason": reason, "supersedes": obs_id}
                flip["observation_id"] = hashlib.sha256(f"{obs_id}|retract|{now}".encode()).hexdigest()[:16]
                with hist_file.open("a") as fh:
                    fh.write(json.dumps(flip, ensure_ascii=False) + "\n")
                flipped += 1
    print(f"[t2_m0] retraction appended for {obs_id}: {flipped} record(s), reason={reason!r}")
    return 0 if flipped else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evidaxis Type-2 observation collector (t2_m0)")
    parser.add_argument("--retract", metavar="OBS_ID", help="append a retraction (status flip)")
    parser.add_argument("--reason", help="retraction reason (>=5 chars, required with --retract)")
    args = parser.parse_args(argv)
    if args.retract:
        if not args.reason or len(args.reason) < 5:
            parser.error("--retract requires --reason (>=5 chars)")
        return retract(args.retract, args.reason)
    return capture()


if __name__ == "__main__":
    sys.exit(main())
