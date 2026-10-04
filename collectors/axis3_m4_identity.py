"""m4 axis-3 identity: which frozen-panel packages are the system's own.

Admission uses the 2026-10-04 linkage audit and private-manifest scan.
no_link stays admitted and is labelled unverified. History is derived exactly
from stored per-package rows; a withheld point restarts the series.
Standard library only.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

try:
    from . import evaluate_axis3_v2h1 as evaluator
    from . import t2_deps_v2h1_collect as deps
except ImportError:
    import evaluate_axis3_v2h1 as evaluator
    import t2_deps_v2h1_collect as deps

REPO = Path(__file__).resolve().parent.parent
M4_ACTIVATION = "2026-10-10"
UNVERIFIED = "unverified"
AUDIT_PATH = REPO / "data/quarantine/axis3-deps-v2/linkage-audit-2026-10-04.json"
PRIVATE_PATH = REPO / "data/quarantine/axis3-deps-v2/private-manifests-2026-10-04.json"


def _pkg_key(pkg: str) -> str:
    system, name = pkg.split("/", 1)
    return f"{system.upper()}/{name}"


@lru_cache(maxsize=1)
def _verdicts() -> dict[tuple[str, str], str]:
    doc = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    return {(row["entity_id"], _pkg_key(f"{row['system']}/{row['package']}")): row["verdict"]
            for row in doc["packages"]}


@lru_cache(maxsize=1)
def _private_flags() -> dict[tuple[str, str], bool]:
    doc = json.loads(PRIVATE_PATH.read_text(encoding="utf-8"))
    # The evidence file covers npm package.json manifests only.
    return {(row["entity_id"], f"NPM/{row['package']}"): row.get("private") is True for row in doc["packages"]}


@lru_cache(maxsize=1)
def _legacy_pins() -> frozenset[tuple[str, str]]:
    """Pre-freeze pins of the v2h.1 panel: name match AND source-repository linkage were
    verified when each was pinned (data/deps_id_map.json), so they count as verified."""
    pins = json.loads(deps.LEGACY_PINS.read_text(encoding="utf-8"))["pins"]
    id_map = json.loads((deps.REPO / "etl/id_map.json").read_text(encoding="utf-8"))
    out = set()
    for repo, pin in pins.items():
        if not pin.get("pinned_at") or pin["pinned_at"] > deps.FROZEN_PIN_CUTOFF:
            continue
        eid = id_map.get(repo)
        if eid:
            out.add((eid, _pkg_key(f"{pin['system']}/{pin['package']}")))
    return frozenset(out)


def _verdict(entity_id: str, key: str) -> str:
    verdict = _verdicts().get((entity_id, key))
    if verdict is not None:
        return verdict
    if (entity_id, key) in _legacy_pins():
        return "verified"
    raise ValueError(f"m4 identity: {entity_id} {key} has no audit verdict and is not a legacy pin")


def admitted(entity_id: str, pkg: str) -> bool:
    """True when the package counts for the entity under m4.

    False when the linkage audit says other_repo, or when the manifest is
    private and the audit verdict is not verified. no_link is True and is
    labelled unverified. A package the audit does not mention stays.
    """
    key = _pkg_key(pkg)
    verdict = _verdict(entity_id, key)
    if verdict == "other_repo":
        return False
    if _private_flags().get((entity_id, key), False) and verdict != "verified":
        return False
    return True


def admission_label(entity_id: str, pkg: str) -> str:
    """verified, other_repo, unverified (no_link or no audit row), or private."""
    key = _pkg_key(pkg)
    verdict = _verdict(entity_id, key)
    if verdict != "other_repo" and _private_flags().get((entity_id, key), False) and verdict != "verified":
        return "private"
    if verdict == "no_link":
        return UNVERIFIED
    return verdict


def _panels() -> tuple[dict, dict[str, set[str]], dict[str, set[str]], str]:
    full, sha = deps.load_panel()
    kept: dict[str, set[str]] = {}
    dropped: dict[str, set[str]] = {}
    for eid, pkgs in full.items():
        keep, drop = set(), set()
        for system, name in pkgs:
            key = f"{system}/{name}"
            (keep if admitted(eid, key) else drop).add(key)
        if keep:
            kept[eid] = keep
        if drop:
            dropped[eid] = drop
    return full, kept, dropped, sha


def m4_mapping_sha(manifest_sha: str) -> str:
    """Provenance of an m4 mapping: v2h.1 manifest + linkage audit + private-manifest evidence."""
    h = hashlib.sha256()
    for part in (manifest_sha.encode(), AUDIT_PATH.read_bytes(), PRIVATE_PATH.read_bytes()):
        h.update(hashlib.sha256(part).digest())
    return "m4:" + h.hexdigest()


def load_panel_m4() -> tuple[dict, str]:
    """(entity -> admitted packages, m4 mapping sha). Entities with none are absent."""
    full, kept, _dropped, manifest_sha = _panels()
    sha = m4_mapping_sha(manifest_sha)
    out = {}
    for eid, pkgs in full.items():
        keep = {(system, name) for system, name in pkgs if f"{system}/{name}" in kept.get(eid, ())}
        if keep:
            out[eid] = keep
    return out, sha


def self_names_v2h1() -> set[str]:
    """Every package name in the unchanged v2h.1 panel. Fixed exclusion list."""
    full, _sha = deps.load_panel()
    return {f"{system}/{name}" for pkgs in full.values() for system, name in pkgs}


def _sketch_complete(row: dict) -> bool:
    try:
        unique = int(row["unique_direct"])
    except (KeyError, TypeError, ValueError):
        return False
    sketch = row.get("sketch64") or []
    return unique <= 64 and len(sketch) == unique


def _union_count(rows: list[dict]) -> int:
    found = set()
    for row in rows:
        for item in row.get("sketch64") or []:
            found.add(int(item))
    return len(found)


def _classify(system_value: int, admitted_rows: list[dict], excluded_present: bool,
              known: bool, has_excluded: bool) -> tuple[str, int | None]:
    """One of the four record cases: a stored total, b one package, c sketch union, d withheld."""
    if not known:
        if has_excluded:
            return "d", None
        return "a", system_value
    if not excluded_present:
        return "a", system_value
    if len(admitted_rows) == 1:
        return "b", int(admitted_rows[0]["unique_direct"])
    if len(admitted_rows) >= 2 and all(_sketch_complete(row) for row in admitted_rows):
        return "c", _union_count(admitted_rows)
    return "d", None


def _package_index(path: Path, cache: dict) -> dict | None:
    if path in cache:
        return cache[path]
    if not path.is_file():
        cache[path] = None
        return None
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        pkg = row.get("pkg")
        if not pkg or "/" not in pkg:
            continue
        grouped[row.get("entity_key")][_pkg_key(pkg)] = row
    cache[path] = grouped
    return grouped


def partition_cases(as_of: str, observations: Path, captured_at: str | None = None) -> dict[str, list[tuple[str, str, int | None]]]:
    """entity_id -> [(date, case, value or None)] after the same custody filter as observation_rows.

    Last in-custody capture wins per date. Includes entities whose packages are all excluded.
    """
    _full, kept, dropped, _sha = _panels()
    latest: dict[tuple[str, str], tuple[str, int | None]] = {}
    cache: dict = {}
    for path, row in evaluator.observation_rows(as_of, observations=observations, captured_at=captured_at):
        eid = row.get("entity_id")
        if eid not in kept and eid not in dropped:
            continue
        day = (row.get("snapshot_at") or "")[:10]
        if not day:
            continue
        grouped = _package_index(path.with_name(path.stem + "-packages.jsonl"), cache)
        keep, drop = kept.get(eid, set()), dropped.get(eid, set())
        try:
            system_value = int(row["signals"]["deps_v2h1_unique_direct"]["value"])
        except (KeyError, TypeError, ValueError):
            latest[(eid, day)] = ("d", None)
            continue
        if grouped is None:
            case, value = _classify(system_value, [], False, False, bool(drop))
        else:
            rows = grouped.get(eid, {})
            if drop and not rows:
                # A system total with no per-package rows cannot be checked for excluded
                # packages: withhold rather than publish the v2h.1 total (review 2026-10-04).
                latest[(eid, day)] = ("d", None)
                continue
            admitted_rows = [rows[key] for key in sorted(rows) if key in keep]
            excluded_present = any(key in drop for key in rows)
            try:
                case, value = _classify(system_value, admitted_rows, excluded_present, True, bool(drop))
            except (KeyError, TypeError, ValueError):
                case, value = "d", None
        latest[(eid, day)] = (case, value)
    by_entity: dict[str, list[tuple[str, str, int | None]]] = defaultdict(list)
    for (eid, day), (case, value) in latest.items():
        by_entity[eid].append((day, case, value))
    for rows in by_entity.values():
        rows.sort()
    return dict(by_entity)


def _latest_run(points: list[tuple[str, str, int | None]], confirmed: set[str] | None,
                calendar: list[str] | None = None) -> list[tuple[str, int]]:
    """Latest unbroken usable run over the partition calendar.

    A withheld point clears the run, and so does a calendar date with no point once the
    series has started: the estimator fits ordinal positions, so a gap must restart the
    series rather than be compressed (review 2026-10-04). Dates outside confirmed are skipped.
    """
    by_day = {day: (case, value) for day, case, value in points}
    days = sorted(set(calendar or []) | set(by_day))
    run: list[tuple[str, int]] = []
    started = False
    for day in days:
        if confirmed is not None and day not in confirmed:
            continue
        if day not in by_day:
            if started:
                run = []
            continue
        case, value = by_day[day]
        started = True
        if case == "d" or value is None:
            run = []
        else:
            run.append((day, value))
    return run


def derive_m4_series(as_of: str, observations: Path, captured_at: str | None = None, *,
                     confirmed: set[str] | None = None) -> dict[str, list[tuple[str, int]]]:
    """entity_id -> [(date, value)] for the latest unbroken run of exact m4 points.

    Entities with no admitted package are absent. confirmed restricts the run to
    those partition dates (the scorer passes CLEAN dates); omitted, every
    in-custody capture is in the sequence.
    """
    _full, kept, _dropped, _sha = _panels()
    series = {}
    cases = partition_cases(as_of, observations, captured_at)
    calendar = sorted({day for points in cases.values() for day, _case, _value in points})
    for eid, points in cases.items():
        if eid not in kept:
            continue
        run = _latest_run(points, confirmed, calendar)
        if run:
            series[eid] = run
    return series
