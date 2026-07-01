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
    paths = glob.glob(str(REPO / "data/observations/**/observations.jsonl"), recursive=True)
    paths += glob.glob(str(REPO / "data/observations/history/*.jsonl"))
    for f in paths:
        for rec in _load_jsonl(f):
            hits = scan_person_fields(rec)
            if hits:
                violations.setdefault(f, []).extend(hits)
    assert not violations, f"person data in observations/history: {violations}"
