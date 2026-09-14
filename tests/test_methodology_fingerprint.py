import json
import subprocess
import sys

from collectors.methodology_fingerprint import SPEC, fingerprint
from collectors import evaluate_axis3_v2h1 as evaluator, score_m3


def test_registry_pins_canonical_spec():
    repo = SPEC.parent.parent
    registry = json.loads((repo / "web/src/lib/methodology-registry.json").read_text())
    entry = next(row for row in registry["versions"] if row["version"] == "m3")
    output = subprocess.check_output([sys.executable, str(repo / "collectors/methodology_fingerprint.py")], text=True).strip()
    assert entry["formula_fingerprint"] == fingerprint() == output
    assert entry["effective_at"] == json.loads(SPEC.read_text())["activation_date"]


def test_spec_matches_scoring_constants():
    spec = json.loads(SPEC.read_text())
    assert [a["id"] for a in spec["axes"]] == list(score_m3.AXES)
    assert spec["activation_date"] == score_m3.ACTIVATION_DATE
    third = spec["axes"][2]
    assert third["floors"] == {"confirmed_clean_points": evaluator.MIN_POINTS,
                               "latest_dependents": evaluator.DEPS_FLOOR, "rising_z": evaluator.Z_FLOOR}
    assert third["canary"]["agreement_floor"] == evaluator.CANARY_AGREEMENT_FLOOR
