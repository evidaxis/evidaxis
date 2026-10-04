import json
import subprocess
import sys

from collectors.methodology_fingerprint import M4_SPEC, SPEC, fingerprint
from collectors import evaluate_axis3_v2h1 as evaluator, score_m3

M4_FINGERPRINT = "sha256:5de15c3a55c026487205c67d09c71efa18ec006103e9653a7f59ee9424d0cad4"


def test_registry_pins_canonical_spec():
    repo = SPEC.parent.parent
    registry = json.loads((repo / "web/src/lib/methodology-registry.json").read_text())
    entry = next(row for row in registry["versions"] if row["version"] == "m3")
    output = subprocess.check_output([sys.executable, str(repo / "collectors/methodology_fingerprint.py")], text=True).strip()
    assert entry["formula_fingerprint"] == fingerprint() == output
    assert entry["effective_at"] == json.loads(SPEC.read_text())["activation_date"]


def test_m4_fingerprint_is_pinned():
    repo = M4_SPEC.parent.parent
    output = subprocess.check_output(
        [sys.executable, str(repo / "collectors/methodology_fingerprint.py"), "m4"], text=True).strip()
    assert fingerprint("m4") == fingerprint(M4_SPEC) == output == M4_FINGERPRINT
    spec = json.loads(M4_SPEC.read_text(encoding="utf-8"))
    assert spec["methodology_version"] == "m4"
    assert spec["parent_version"] == "m3"
    assert spec["activation_date"] == "2026-10-10"
    assert spec["changelog"][0]["class"] == "MAJOR"
    assert spec["changelog"][0]["record"] == "governance/METHODOLOGY-M4-2026-10-04.md"
    assert spec["axes"][2]["floors"]["confirmed_clean_points"] == evaluator.MIN_POINTS


def test_spec_matches_scoring_constants():
    spec = json.loads(SPEC.read_text())
    assert [a["id"] for a in spec["axes"]] == list(score_m3.AXES)
    assert spec["activation_date"] == score_m3.ACTIVATION_DATE
    third = spec["axes"][2]
    assert third["floors"] == {"confirmed_clean_points": evaluator.MIN_POINTS,
                               "latest_dependents": evaluator.DEPS_FLOOR, "rising_z": evaluator.Z_FLOOR}
    assert third["canary"]["agreement_floor"] == evaluator.CANARY_AGREEMENT_FLOOR
