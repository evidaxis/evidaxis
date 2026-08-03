#!/usr/bin/env python3
"""Collect the non-public 200..499-star shadow layer into a private checkout.

The shadow exists to preserve otherwise unrecoverable point-in-time star counts
before a repository reaches the public census bar. It is intentionally a narrow
projection: repository identity, stars, and the observation timestamp are the
only per-repository bytes retained.

Enumeration imports ``census_ai_v1.sweep`` so the public census and private
shadow share one fail-closed implementation of partitioning and coverage
assertions. This module only supplies the stricter projection and packages the
result as an idempotent, hash-anchored dated snapshot.

Usage: EVIDAXIS_SHADOW_REPO=/path/to/private/checkout \
       python3 collectors/shadow_snapshot.py [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from census_ai_v1 import sweep as census_sweep

PUBLIC_REPO = Path(__file__).resolve().parent.parent
SHADOW_LO = 200
SHADOW_HI = 499
SHADOW_FIELDS = frozenset({"id", "stars", "observed_at"})


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid snapshot date {value!r}; expected YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"invalid snapshot date {value!r}; expected YYYY-MM-DD")
    return value


def shadow_record(row: dict, observed_at: str) -> dict:
    """Return the complete and exclusive per-repository storage projection."""
    repo_id = row["id"]
    stars = row["stargazers_count"]
    if isinstance(repo_id, bool) or not isinstance(repo_id, int) or repo_id <= 0:
        raise ValueError(f"invalid GitHub repository id: {repo_id!r}")
    if isinstance(stars, bool) or not isinstance(stars, int):
        raise ValueError(f"invalid GitHub star count for id {repo_id}: {stars!r}")
    if not SHADOW_LO <= stars <= SHADOW_HI:
        raise ValueError(
            f"repository id {repo_id} moved outside the shadow band: {stars} stars"
        )
    _validate_timestamp(observed_at)
    return {"id": repo_id, "stars": stars, "observed_at": observed_at}


def _validate_timestamp(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError(f"observed_at must be a UTC timestamp, got {value!r}")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise ValueError(f"invalid observed_at timestamp: {value!r}") from exc
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_record(record: object, snapshot_date: str) -> dict:
    if not isinstance(record, dict) or set(record) != SHADOW_FIELDS:
        keys = sorted(record) if isinstance(record, dict) else type(record).__name__
        raise ValueError(
            "shadow record schema violation; expected only "
            f"{sorted(SHADOW_FIELDS)}, got {keys}"
        )
    observed_at = _validate_timestamp(record["observed_at"])
    if observed_at[:10] != snapshot_date:
        raise ValueError(
            f"shadow record timestamp {observed_at} does not match {snapshot_date}"
        )
    return shadow_record(
        {"id": record["id"], "stargazers_count": record["stars"]}, observed_at
    )


def _load_records(path: Path, snapshot_date: str) -> list[dict]:
    records: list[dict] = []
    seen: set[int] = set()
    with path.open() as source:
        for line_number, line in enumerate(source, 1):
            try:
                record = _validate_record(json.loads(line), snapshot_date)
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"invalid shadow row {path}:{line_number}: {exc}") from exc
            if record["id"] in seen:
                raise ValueError(f"duplicate repository id in shadow snapshot: {record['id']}")
            seen.add(record["id"])
            records.append(record)
    return sorted(records, key=lambda record: record["id"])


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content)
    temporary.replace(path)


def _snapshot_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_snapshot(path: Path, records: list[dict]) -> None:
    content = "".join(
        json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n"
        for record in records
    )
    _atomic_write(path, content)


def _write_or_verify_hash(snapshot_path: Path, hash_path: Path) -> None:
    expected = f"{_snapshot_digest(snapshot_path)}  {snapshot_path.name}\n"
    if hash_path.exists():
        if hash_path.read_text() != expected:
            raise RuntimeError(f"sha256 mismatch for existing snapshot {snapshot_path}")
        return
    _atomic_write(hash_path, expected)


def _validate_ledger(ledger_path: Path, complete_path: Path) -> None:
    if not ledger_path.exists() or not complete_path.exists():
        raise RuntimeError("shadow partition ledger or completion sentinel is missing")
    done_bands = 0
    with ledger_path.open() as ledger:
        for line_number, line in enumerate(ledger, 1):
            try:
                band = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"invalid shadow ledger row {ledger_path}:{line_number}"
                ) from exc
            if band.get("done"):
                done_bands += 1
                if "index_drift" not in band:
                    raise RuntimeError(
                        f"completed shadow band lacks index_drift at line {line_number}"
                    )
    complete = json.loads(complete_path.read_text())
    if complete.get("bar_lo") != SHADOW_LO or complete.get("bar_hi") != SHADOW_HI:
        raise RuntimeError("shadow completion sentinel has the wrong star band")
    if done_bands == 0:
        raise RuntimeError("shadow partition ledger contains no completed bands")


def _copy_if_missing(source: Path, destination: Path) -> None:
    if destination.exists():
        return
    if not source.exists():
        raise RuntimeError(f"cannot publish missing checkpoint artifact {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    shutil.copyfile(source, temporary)
    temporary.replace(destination)


def _observed_at(checkpoint: Path, snapshot_date: str) -> str:
    run_path = checkpoint / "run.json"
    if run_path.exists():
        run = json.loads(run_path.read_text())
        if run.get("snapshot_date") != snapshot_date:
            raise RuntimeError(f"checkpoint date does not match {snapshot_date}: {run_path}")
        observed_at = _validate_timestamp(run.get("observed_at"))
        if observed_at[:10] != snapshot_date:
            raise RuntimeError(
                f"checkpoint observation {observed_at} does not match {snapshot_date}"
            )
        return observed_at
    observed_at = _utc_timestamp()
    if observed_at[:10] != snapshot_date:
        raise RuntimeError(
            f"refusing to start a new {snapshot_date} snapshot at {observed_at}"
        )
    checkpoint.mkdir(parents=True, exist_ok=True)
    _atomic_write(
        run_path,
        json.dumps(
            {
                "snapshot_date": snapshot_date,
                "observed_at": observed_at,
                "star_band": {"lo": SHADOW_LO, "hi": SHADOW_HI},
                "repository_fields": sorted(SHADOW_FIELDS),
            },
            indent=1,
        )
        + "\n",
    )
    return observed_at


def collect_snapshot(shadow_repo: Path, snapshot_date: str) -> Path:
    """Collect or verify one UTC-date snapshot inside a private checkout."""
    snapshot_date = _parse_date(snapshot_date)
    snapshots = shadow_repo / "snapshots"
    ledgers = shadow_repo / "ledgers"
    checkpoint = shadow_repo / "checkpoints" / snapshot_date
    snapshot_path = snapshots / f"{snapshot_date}.jsonl"
    hash_path = snapshots / f"{snapshot_date}.sha256"
    ledger_path = ledgers / f"{snapshot_date}.jsonl"
    complete_path = ledgers / f"{snapshot_date}-complete.json"
    raw_path = checkpoint / "repos.jsonl"
    bands_path = checkpoint / "bands.jsonl"
    checkpoint_complete = checkpoint / "repos-complete.json"

    if hash_path.exists() and not snapshot_path.exists():
        raise RuntimeError(f"sha256 exists without its snapshot: {hash_path}")
    if snapshot_path.exists():
        _load_records(snapshot_path, snapshot_date)
        _write_or_verify_hash(snapshot_path, hash_path)
        if ledger_path.exists() and complete_path.exists():
            _validate_ledger(ledger_path, complete_path)
            if checkpoint.exists():
                shutil.rmtree(checkpoint)
            print(f"shadow snapshot already complete and verified: {snapshot_path}")
            return snapshot_path
        if not checkpoint.exists():
            raise RuntimeError("snapshot exists without its dated partition audit")

    observed_at = _observed_at(checkpoint, snapshot_date)
    if not checkpoint_complete.exists():
        census_sweep(
            SHADOW_LO,
            SHADOW_HI,
            raw_path,
            bands_path,
            project=lambda row: shadow_record(row, observed_at),
        )
    if not checkpoint_complete.exists():
        raise RuntimeError("shadow sweep returned without a completion sentinel")

    records = _load_records(raw_path, snapshot_date)
    if not records:
        raise RuntimeError("shadow sweep produced zero repositories; refusing silent no-op")
    if not snapshot_path.exists():
        _write_snapshot(snapshot_path, records)
    else:
        existing = _load_records(snapshot_path, snapshot_date)
        if existing != records:
            raise RuntimeError("existing snapshot differs from its completed checkpoint")
    _write_or_verify_hash(snapshot_path, hash_path)
    _copy_if_missing(bands_path, ledger_path)
    _copy_if_missing(checkpoint_complete, complete_path)
    _validate_ledger(ledger_path, complete_path)
    shutil.rmtree(checkpoint)
    print(
        f"shadow snapshot complete: {len(records)} repos, "
        f"sha256={_snapshot_digest(snapshot_path)}"
    )
    return snapshot_path


def _shadow_repo_from_env() -> Path:
    configured = os.environ.get("EVIDAXIS_SHADOW_REPO", "").strip()
    if not configured:
        raise RuntimeError(
            "EVIDAXIS_SHADOW_REPO must name the local private-repository checkout"
        )
    shadow_repo = Path(configured).expanduser().resolve()
    if not shadow_repo.is_dir() or not (shadow_repo / ".git").exists():
        raise RuntimeError(f"shadow repository is not a Git checkout: {shadow_repo}")
    if shadow_repo == PUBLIC_REPO or PUBLIC_REPO in shadow_repo.parents:
        raise RuntimeError("EVIDAXIS_SHADOW_REPO must be outside the public repository")
    return shadow_repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="UTC snapshot date (default: today)",
    )
    args = parser.parse_args(argv)
    try:
        collect_snapshot(_shadow_repo_from_env(), args.date)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"shadow snapshot failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
