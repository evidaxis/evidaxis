"""CI gate for the claim-URN scheme (CLAIM-URN.md). Locks build/parse round-trip and rejections."""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))
from claim_urn import ClaimURNError, build, parse

ACC = "EVX:SYS:Y92940K5ESN7"
LEGACY = "e_H6PPP8CA9RR"  # the form live snapshots actually carry


def test_legacy_entity_id_roundtrip():
    # live entity ids are colon-free `e_...`; the URN must build and parse for them
    urn = build(LEGACY, "m2", "2026-w27")
    assert urn == "urn:evidaxis:claim:e_H6PPP8CA9RR:m2:2026-w27"
    assert parse(urn) == {"accession_id": LEGACY, "methodology_version": "m2", "epoch": "2026-w27"}


def test_legacy_rejects_bad_body_alphabet():
    # I/L/O/U are not in Crockford base32 -> reject (guards against garbage accessions)
    with pytest.raises(ClaimURNError):
        build("e_ILLEGALOCHAR", "m2", "2026-w27")


def test_build_roundtrip_week_epoch():
    urn = build(ACC, "m2", "2026-w26")
    assert urn == "urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m2:2026-w26"
    assert parse(urn) == {"accession_id": ACC, "methodology_version": "m2", "epoch": "2026-w26"}


def test_build_roundtrip_iso_date_epoch():
    urn = build(ACC, "m1", "2026-06-27")
    assert parse(urn) == {"accession_id": ACC, "methodology_version": "m1", "epoch": "2026-06-27"}


def test_accession_with_colons_parses_unambiguously():
    # the accession itself carries two colons; parser must still recover all three fields
    got = parse("urn:evidaxis:claim:EVX:ACC:0123456789AB:m10:2027-w01")
    assert got["accession_id"] == "EVX:ACC:0123456789AB"
    assert got["methodology_version"] == "m10"
    assert got["epoch"] == "2027-w01"


def test_rejects_non_urn():
    with pytest.raises(ClaimURNError):
        parse("https://evidaxis.org/e/EVX:SYS:Y92940K5ESN7/")


def test_rejects_bad_methodology():
    with pytest.raises(ClaimURNError):
        build(ACC, "v2", "2026-w26")


def test_rejects_colon_in_epoch():
    # a time-of-day epoch would break unambiguous parsing; grammar forbids it
    with pytest.raises(ClaimURNError):
        build(ACC, "m1", "2026-06-27T10:00:00")


def test_rejects_person_looking_accession():
    with pytest.raises(ClaimURNError):
        build("github:torvalds", "m1", "2026-w26")
