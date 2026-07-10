"""CI gate: person-free enforcement for the public Type-2 archive (cons-03 artifact #1).

Fails the build if any person-identifying field (login, avatar_url, owner/user object,
email, ...) has leaked into the public provenance, observations, or history.
"""
import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))
from field_policy import scan_person_fields


def _load_jsonl(path: str):
    for line in Path(path).read_text().splitlines():
        if line.strip():
            yield json.loads(line)


def test_no_person_fields_in_provenance():
    violations = {}
    for f in glob.glob(str(REPO / "data/observations/**/provenance/*.json"), recursive=True):
        hits = scan_person_fields(json.loads(Path(f).read_text()))
        if hits:
            violations[f] = hits
    assert not violations, f"person data leaked into public provenance: {violations}"


def test_no_person_fields_in_observations_and_history():
    violations = {}
    # every JSONL under observations/: observations.jsonl, per-date deps.jsonl,
    # history/*.jsonl, and the reconstructed backfill/*.backfill.jsonl namespace.
    paths = glob.glob(str(REPO / "data/observations/**/*.jsonl"), recursive=True)
    for f in paths:
        for rec in _load_jsonl(f):
            hits = scan_person_fields(rec)
            if hits:
                violations.setdefault(f, []).extend(hits)
    assert not violations, f"person data in observations/history: {violations}"


def test_owner_classification_is_complete_and_minimal():
    id_map = json.loads((REPO / "etl/id_map.json").read_text())
    cache = json.loads((REPO / "etl/owner_types.json").read_text())
    assert cache.get("schema_version") == "owner_types_1"
    assert set(cache.get("repos", {})) == set(id_map)
    for entry in cache["repos"].values():
        assert set(entry) == {"owner_type", "repo_id", "full_name"}
        assert entry["owner_type"] in {"Organization", "User"}
        assert isinstance(entry["repo_id"], int) and not isinstance(entry["repo_id"], bool) and entry["repo_id"] > 0
        assert isinstance(entry["full_name"], str) and len(entry["full_name"].split("/")) == 2
