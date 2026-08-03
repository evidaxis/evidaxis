#!/usr/bin/env python3
"""Build the private shadow series without repeating its expensive Search sweep.

Discovery changes slowly, while weekly star observations are the time series.
Keeping those phases separate lets monthly Search shards publish independently
and lets weekly GraphQL shards finish within one Actions run. Both phases write
only their policy projections before any repository record reaches disk.

Usage:
  python3 collectors/shadow_snapshot.py --mode discover --shard 0/8
  python3 collectors/shadow_snapshot.py --mode discover --merge --shards 8
  python3 collectors/shadow_snapshot.py --mode observe --shard 0/4
  python3 collectors/shadow_snapshot.py --mode observe --merge --shards 4
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence, TypeVar

from census_ai_v1 import gh_graphql as census_graphql
from census_ai_v1 import gh_search as census_search
from census_ai_v1 import sweep as census_sweep

PUBLIC_REPO = Path(__file__).resolve().parent.parent
SHADOW_LO = 200
SHADOW_HI = 499
DISCOVERY_FIELDS = frozenset({"id", "full_name"})
OBSERVATION_FIELDS = frozenset({"id", "stars", "observed_at"})
GRAPHQL_BATCH_SIZE = 50
DISCOVERY_WORKFLOW = "shadow-discover"

T = TypeVar("T")


@dataclass(frozen=True)
class Shard:
    index: int
    total: int

    def __post_init__(self) -> None:
        if self.total <= 0 or self.index < 0 or self.index >= self.total:
            raise ValueError(
                f"invalid shard {self.index}/{self.total}; expected 0 <= i < N"
            )

    def __str__(self) -> str:
        return f"{self.index}/{self.total}"


class Progress:
    """Emit liveness independently of a blocked GitHub request."""

    def __init__(
        self, label: str, total: int | None, *, interval: float = 60.0
    ) -> None:
        self.label = label
        self.total = total
        self.interval = interval
        self.done = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._heartbeat, daemon=True)

    def __enter__(self) -> Progress:
        self.report()
        self._thread.start()
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self._stop.set()
        self._thread.join()
        self.report()

    def advance(self, count: int = 1) -> None:
        with self._lock:
            self.done += count

    def set_total(self, total: int) -> None:
        with self._lock:
            self.total = total

    def report(self) -> None:
        with self._lock:
            done = self.done
            total = self.total
        total_text = str(total) if total is not None else "?"
        print(f"{self.label} progress: {done}/{total_text} repos", flush=True)

    def _heartbeat(self) -> None:
        while not self._stop.wait(self.interval):
            self.report()


def parse_shard(value: str) -> Shard:
    try:
        index_text, total_text = value.split("/", 1)
        return Shard(int(index_text), int(total_text))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid shard {value!r}; expected i/N") from exc


def partition_for_shard(items: Sequence[T], shard: Shard) -> Sequence[T]:
    """Return one contiguous, balanced partition of an ordered input."""
    base, remainder = divmod(len(items), shard.total)
    start = shard.index * base + min(shard.index, remainder)
    stop = start + base + (shard.index < remainder)
    return items[start:stop]


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


def _parse_month(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValueError(f"invalid discovery month {value!r}; expected YYYY-MM") from exc
    if parsed.strftime("%Y-%m") != value:
        raise ValueError(f"invalid discovery month {value!r}; expected YYYY-MM")
    return value


def _validate_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"invalid GitHub repository id: {value!r}")
    return value


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


def discovery_record(row: dict) -> dict:
    """Project Search output to the only identity fields discovery retains."""
    repo_id = _validate_id(row.get("id"))
    full_name = row.get("full_name")
    if (
        not isinstance(full_name, str)
        or full_name.count("/") != 1
        or not all(full_name.split("/"))
    ):
        raise ValueError(f"invalid GitHub full_name for id {repo_id}")
    return {"id": repo_id, "full_name": full_name}


def observation_record(repo_id: object, stars: object, observed_at: str) -> dict:
    """Project GraphQL output to the complete weekly storage schema."""
    repo_id = _validate_id(repo_id)
    if isinstance(stars, bool) or not isinstance(stars, int) or stars < 0:
        raise ValueError(f"invalid GitHub star count for id {repo_id}: {stars!r}")
    return {
        "id": repo_id,
        "stars": stars,
        "observed_at": _validate_timestamp(observed_at),
    }


def _validate_discovery_record(record: object) -> dict:
    if not isinstance(record, dict) or set(record) != DISCOVERY_FIELDS:
        keys = sorted(record) if isinstance(record, dict) else type(record).__name__
        raise ValueError(
            "discovery record schema violation; expected only "
            f"{sorted(DISCOVERY_FIELDS)}, got {keys}"
        )
    return discovery_record(record)


def _validate_observation_record(record: object, snapshot_date: str) -> dict:
    if not isinstance(record, dict) or set(record) != OBSERVATION_FIELDS:
        keys = sorted(record) if isinstance(record, dict) else type(record).__name__
        raise ValueError(
            "observation record schema violation; expected only "
            f"{sorted(OBSERVATION_FIELDS)}, got {keys}"
        )
    observed_at = _validate_timestamp(record["observed_at"])
    if observed_at[:10] != snapshot_date:
        raise ValueError(
            f"observation timestamp {observed_at} does not match {snapshot_date}"
        )
    return observation_record(record["id"], record["stars"], observed_at)


def _load_records(path: Path, validator) -> list[dict]:
    records: list[dict] = []
    seen: set[int] = set()
    try:
        source = path.open()
    except OSError as exc:
        raise RuntimeError(f"cannot read required shadow artifact {path}") from exc
    with source:
        for line_number, line in enumerate(source, 1):
            try:
                record = validator(json.loads(line))
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"invalid shadow row {path}:{line_number}: {exc}") from exc
            if record["id"] in seen:
                raise ValueError(f"duplicate repository id {record['id']} in {path}")
            seen.add(record["id"])
            records.append(record)
    return sorted(records, key=lambda record: record["id"])


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content)
    temporary.replace(path)


def _jsonl(records: Sequence[dict]) -> str:
    return "".join(
        json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n"
        for record in records
    )


def _write_or_verify_records(path: Path, records: Sequence[dict]) -> None:
    expected = _jsonl(records)
    if path.exists():
        if path.read_text() != expected:
            raise RuntimeError(f"existing append-only shadow artifact differs: {path}")
        return
    _atomic_write(path, expected)


def _write_or_verify_hash(path: Path, hash_path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"cannot hash missing shadow artifact {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = f"{digest}  {path.name}\n"
    if hash_path.exists():
        if hash_path.read_text() != expected:
            raise RuntimeError(f"sha256 mismatch for existing shadow artifact {path}")
        return
    _atomic_write(hash_path, expected)


def _verify_hash(path: Path, hash_path: Path) -> None:
    if not hash_path.exists():
        raise RuntimeError(f"sha256 is missing for discovery set {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = f"{digest}  {path.name}\n"
    if hash_path.read_text() != expected:
        raise RuntimeError(f"sha256 mismatch for existing shadow artifact {path}")


def _required_shards(directory: Path, shards: int) -> list[Path]:
    if shards <= 0:
        raise ValueError("--shards must be positive")
    paths = [directory / f"shard-{index}.jsonl" for index in range(shards)]
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        raise RuntimeError(
            f"missing {len(missing)} required shard file(s) in {directory}: "
            + ", ".join(missing)
        )
    return paths


def _validate_sweep(checkpoint: Path, lo: int, hi: int) -> dict:
    bands_path = checkpoint / "bands.jsonl"
    complete_path = checkpoint / "repos-complete.json"
    if not bands_path.exists() or not complete_path.exists():
        raise RuntimeError("discovery sweep lacks its coverage ledger or sentinel")
    bands = [json.loads(line) for line in bands_path.open()]
    done = [band for band in bands if band.get("done")]
    if not done:
        raise RuntimeError("discovery sweep contains no completed Search partition")
    if any("index_drift" not in band for band in done):
        raise RuntimeError("completed discovery partition lacks index_drift")
    done_keys = {
        (band.get("lo"), band.get("hi"), band.get("created", "")) for band in done
    }
    unresolved = [
        band
        for band in bands
        if not band.get("done")
        and (band.get("lo"), band.get("hi"), band.get("created", ""))
        not in done_keys
    ]
    if unresolved:
        raise RuntimeError("discovery sweep contains an unresolved Search partition")
    complete = json.loads(complete_path.read_text())
    if complete.get("bar_lo") != lo or complete.get("bar_hi") != hi:
        raise RuntimeError("discovery sweep sentinel has the wrong star range")
    return complete


def collect_discovery(shadow_repo: Path, month: str, shard: Shard) -> Path:
    """Enumerate and publish one monthly Search shard."""
    month = _parse_month(month)
    output = shadow_repo / "discovery" / month / f"shard-{shard.index}.jsonl"
    if output.exists():
        records = _load_records(output, _validate_discovery_record)
        if not records:
            raise RuntimeError(f"existing discovery shard is empty: {output}")
        print(f"discover shard {shard}: {len(records)}/{len(records)} repos", flush=True)
        return output

    star_values = list(range(SHADOW_LO, SHADOW_HI + 1))
    assigned = partition_for_shard(star_values, shard)
    if not assigned:
        raise RuntimeError(f"shard {shard} has no star values to enumerate")
    lo, hi = assigned[0], assigned[-1]
    checkpoint = shadow_repo / ".checkpoints" / "discovery" / month / f"shard-{shard.index}"
    raw_path = checkpoint / "repos.jsonl"
    bands_path = checkpoint / "bands.jsonl"
    checkpoint.mkdir(parents=True, exist_ok=True)

    existing = sum(1 for _line in raw_path.open()) if raw_path.exists() else 0
    query = f"stars:{lo}..{hi} fork:false is:public"
    with Progress(f"discover shard {shard}", None) as progress:
        progress.advance(existing)
        progress.set_total(census_search(query, 1)["total_count"])
        census_sweep(
            lo,
            hi,
            raw_path,
            bands_path,
            project=lambda row: _discovery_progress_record(row, progress),
        )
    complete = _validate_sweep(checkpoint, lo, hi)
    records = _load_records(raw_path, _validate_discovery_record)
    if not records:
        raise RuntimeError(f"discovery shard {shard} produced zero repositories")
    if complete.get("collected") != len(records):
        raise RuntimeError(
            f"discovery shard coverage mismatch: {len(records)} stored, "
            f"{complete.get('collected')!r} asserted"
        )
    _write_or_verify_records(output, records)
    shutil.rmtree(checkpoint)
    print(f"discover shard {shard} complete: {len(records)} repos", flush=True)
    return output


def _discovery_progress_record(row: dict, progress: Progress) -> dict:
    record = discovery_record(row)
    progress.advance()
    return record


def merge_discovery(shadow_repo: Path, month: str, shards: int) -> Path:
    """Merge a complete monthly identity set and refuse partial discovery."""
    month = _parse_month(month)
    directory = shadow_repo / "discovery" / month
    records_by_id: dict[int, dict] = {}
    for path in _required_shards(directory, shards):
        records = _load_records(path, _validate_discovery_record)
        if not records:
            raise RuntimeError(f"discovery shard is empty: {path}")
        for record in records:
            previous = records_by_id.get(record["id"])
            if previous is not None and previous != record:
                raise RuntimeError(
                    f"repository id {record['id']} has conflicting discovery names"
                )
            records_by_id[record["id"]] = record
    if not records_by_id:
        raise RuntimeError("discovery merge produced zero repositories")
    output = directory / "ids.jsonl"
    records = sorted(records_by_id.values(), key=lambda record: record["id"])
    _write_or_verify_records(output, records)
    _write_or_verify_hash(output, directory / "ids.sha256")
    print(f"discovery merge complete: {len(records)} repos", flush=True)
    return output


def newest_discovery(shadow_repo: Path) -> tuple[str, Path, list[dict]]:
    candidates: list[tuple[str, Path]] = []
    discovery_root = shadow_repo / "discovery"
    if discovery_root.exists():
        for path in discovery_root.glob("*/ids.jsonl"):
            try:
                month = _parse_month(path.parent.name)
            except ValueError:
                continue
            candidates.append((month, path))
    if not candidates:
        raise RuntimeError(
            "no merged discovery set exists; run the shadow-discover workflow "
            "before shadow-observe"
        )
    month, path = max(candidates)
    records = _load_records(path, _validate_discovery_record)
    if not records:
        raise RuntimeError(
            f"newest discovery set is empty; rerun the {DISCOVERY_WORKFLOW} workflow"
        )
    _verify_hash(path, path.with_name("ids.sha256"))
    return month, path, records


def _graphql_query(batch: Sequence[dict]) -> str:
    parts = []
    for index, record in enumerate(batch):
        owner, name = record["full_name"].split("/", 1)
        parts.append(
            f"r{index}: repository(owner:{json.dumps(owner)}, name:{json.dumps(name)}) "
            "{ databaseId stargazerCount }"
        )
    return "query {" + " ".join(parts) + "}"


# Repositories present at discovery that no longer resolve at observation time.
# Module-level because the shard reports the total once, not per batch.
_ABSENT: list[int] = []
ABSENT_LIMIT = 0.01          # 1% of a shard: churn below, systemic fault above


def _observe_batch(batch: Sequence[dict], observed_at: str) -> list[dict]:
    """Star counts for one batch. A vanished repository is DATA, not an error.

    Measured on the first live observation: id 7061513 was present at discovery
    and unresolvable four hours later - deleted, made private, or taken down.
    At 146,589 repositories over a multi-hour gap that is ordinary churn, and
    the first version aborted the whole shard on it, exactly the defect already
    fixed in the census collector (a clean NOT_FOUND is a permanent fact about
    that repository, never a transport failure).

    Refusing to publish a weekly snapshot because one repository of 146,589
    disappeared is the wrong trade. But silently dropping many WOULD hide a
    systemic fault - a bad token, a wrong id set - so the caller counts the
    absences and fails if their share crosses ABSENT_LIMIT. Churn is recorded;
    breakage still stops the run.
    """
    for attempt in range(1, 7):
        data, clean = census_graphql(_graphql_query(batch))
        missing = [index for index in range(len(batch)) if data.get(f"r{index}") is None]
        if clean and missing:
            records = []
            for index, expected in enumerate(batch):
                node = data.get(f"r{index}")
                if node is None:
                    _ABSENT.append(expected["id"])
                    continue
                records.append(observation_record(
                    node["databaseId"], node["stargazerCount"], observed_at))
            return records
        if clean and not missing:
            records = []
            for index, expected in enumerate(batch):
                node = data[f"r{index}"]
                if node.get("databaseId") != expected["id"]:
                    raise RuntimeError(
                        f"GraphQL identity changed for repository id {expected['id']}"
                    )
                records.append(
                    observation_record(
                        node["databaseId"], node["stargazerCount"], observed_at
                    )
                )
            return records
        print(f"observation GraphQL batch retry {attempt}/6", flush=True)
        if attempt < 6:
            time.sleep(min(60, 10 * attempt))
    raise RuntimeError("GraphQL observation batch remained incomplete after 6 attempts")


def _validate_observation_shard(
    path: Path, snapshot_date: str, expected: Sequence[dict]
) -> list[dict]:
    records = _load_records(
        path, lambda record: _validate_observation_record(record, snapshot_date)
    )
    expected_ids = {record["id"] for record in expected}
    actual_ids = {record["id"] for record in records}
    extra = actual_ids - expected_ids
    if extra:
        # An id nobody discovered means the shard observed something outside
        # its own assignment: always a fault, never churn.
        raise RuntimeError(
            f"observation shard {path} carries {len(extra)} ids that were "
            f"never discovered")
    absent = expected_ids - actual_ids
    share = len(absent) / max(len(expected_ids), 1)
    if share > ABSENT_LIMIT:
        raise RuntimeError(
            f"observation shard {path}: {len(absent)} of {len(expected_ids)} "
            f"discovered repositories ({share:.1%}) did not resolve, above the "
            f"{ABSENT_LIMIT:.0%} churn allowance - investigate the token or the "
            f"id set before publishing this snapshot")
    if absent:
        print(f"  {len(absent)} of {len(expected_ids)} discovered repositories "
              f"({share:.2%}) no longer resolve - recorded as churn", flush=True)
    return records


def collect_observation(shadow_repo: Path, snapshot_date: str, shard: Shard) -> Path:
    """Refresh one balanced shard from the newest complete discovery set."""
    snapshot_date = _parse_date(snapshot_date)
    month, _path, discovery = newest_discovery(shadow_repo)
    assigned = partition_for_shard(discovery, shard)
    output = (
        shadow_repo
        / "observations"
        / snapshot_date
        / f"shard-{shard.index}.jsonl"
    )
    if output.exists():
        records = _validate_observation_shard(output, snapshot_date, assigned)
        print(f"observe shard {shard}: {len(records)}/{len(assigned)} repos", flush=True)
        return output

    observed_at = _utc_timestamp()
    if observed_at[:10] != snapshot_date:
        raise RuntimeError(
            f"refusing to start a {snapshot_date} observation at {observed_at}"
        )
    records: list[dict] = []
    with Progress(f"observe shard {shard} ({month})", len(assigned)) as progress:
        for start in range(0, len(assigned), GRAPHQL_BATCH_SIZE):
            batch = assigned[start : start + GRAPHQL_BATCH_SIZE]
            records.extend(_observe_batch(batch, observed_at))
            progress.advance(len(batch))
    records.sort(key=lambda record: record["id"])
    _write_or_verify_records(output, records)
    _validate_observation_shard(output, snapshot_date, assigned)
    print(f"observe shard {shard} complete: {len(records)} repos", flush=True)
    return output


def merge_observation(shadow_repo: Path, snapshot_date: str, shards: int) -> Path:
    """Merge a dated observation only when every discovered id is present."""
    snapshot_date = _parse_date(snapshot_date)
    _month, _path, discovery = newest_discovery(shadow_repo)
    directory = shadow_repo / "observations" / snapshot_date
    paths = _required_shards(directory, shards)
    records: list[dict] = []
    for index, path in enumerate(paths):
        expected = partition_for_shard(discovery, Shard(index, shards))
        records.extend(_validate_observation_shard(path, snapshot_date, expected))
    if len(records) != len(discovery):
        raise RuntimeError(
            f"observation merge coverage mismatch: {len(records)}/{len(discovery)} repos"
        )
    records.sort(key=lambda record: record["id"])
    output = directory / "snapshot.jsonl"
    _write_or_verify_records(output, records)
    _write_or_verify_hash(output, directory / "snapshot.sha256")
    print(f"observation merge complete: {len(records)} repos", flush=True)
    return output


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


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _current_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _run(args: argparse.Namespace) -> Path:
    shadow_repo = _shadow_repo_from_env()
    if args.merge:
        if args.shard is not None:
            raise ValueError("--merge and --shard are mutually exclusive")
        if args.shards is None:
            raise ValueError("--merge requires --shards N")
        if args.mode == "discover":
            return merge_discovery(shadow_repo, args.month or _current_month(), args.shards)
        return merge_observation(shadow_repo, args.date or _current_date(), args.shards)
    if args.shard is None:
        raise ValueError("shard collection requires --shard i/N")
    shard = parse_shard(args.shard)
    if args.shards is not None and args.shards != shard.total:
        raise ValueError("--shards does not match --shard i/N")
    if args.mode == "discover":
        return collect_discovery(shadow_repo, args.month or _current_month(), shard)
    return collect_observation(shadow_repo, args.date or _current_date(), shard)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("discover", "observe"), required=True)
    parser.add_argument("--shard", help="zero-based shard as i/N")
    parser.add_argument("--shards", type=int, help="required shard count for a merge")
    parser.add_argument("--merge", action="store_true", help="merge completed shards")
    parser.add_argument("--month", help="discovery month, YYYY-MM")
    parser.add_argument("--date", help="observation date, YYYY-MM-DD")
    args = parser.parse_args(argv)
    try:
        _run(args)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"shadow {args.mode} failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
