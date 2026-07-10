"""CI gate for the claim-URN scheme (CLAIM-URN.md). Locks build/parse round-trip and rejections."""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))
from claim_urn import ClaimURNError, build, parse

ACC = "EVX:SYS:Y92940K5ESN7"
LEGACY = "e_H6PPP8CA9RR"  # the form live snapshots actually carry

# 20 shared vectors mirrored in web/src/lib/claim_urn.test.ts — both implementations must agree.
SHARED_VECTORS = [
    (LEGACY, "m2", "2026-w27", "urn:evidaxis:claim:e_H6PPP8CA9RR:m2:2026-w27"),
    (LEGACY, "m2", "2026-07-03", "urn:evidaxis:claim:e_H6PPP8CA9RR:m2:2026-07-03"),
    (LEGACY, "m2", "2026-07-04", "urn:evidaxis:claim:e_H6PPP8CA9RR:m2:2026-07-04"),
    (ACC, "m1", "2026-06-27", "urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m1:2026-06-27"),
    (ACC, "m2", "2026-w26", "urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m2:2026-w26"),
    (ACC, "m2", "2026-07-01", "urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m2:2026-07-01"),
    (ACC, "m10", "2027-w01", "urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m10:2027-w01"),
    (ACC, "m0", "2025-01-01", "urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m0:2025-01-01"),
    ("e_0123456789AB", "m1", "2026-w01", "urn:evidaxis:claim:e_0123456789AB:m1:2026-w01"),
    ("e_ZZZZZZZZZZZ", "m2", "2026-12-31", "urn:evidaxis:claim:e_ZZZZZZZZZZZ:m2:2026-12-31"),
    ("EVX:ACC:0123456789AB", "m1", "2026-06-27", "urn:evidaxis:claim:EVX:ACC:0123456789AB:m1:2026-06-27"),
    ("EVX:SYS:ABCDEFGHJKMN", "m3", "2026-w52", "urn:evidaxis:claim:EVX:SYS:ABCDEFGHJKMN:m3:2026-w52"),
    ("EVX:TOOL:PQRSTVWXYZ01", "m2", "2026-07-10", "urn:evidaxis:claim:EVX:TOOL:PQRSTVWXYZ01:m2:2026-07-10"),
    (LEGACY, "m1", "2026-w26", "urn:evidaxis:claim:e_H6PPP8CA9RR:m1:2026-w26"),
    (LEGACY, "m1", "2026-06-27", "urn:evidaxis:claim:e_H6PPP8CA9RR:m1:2026-06-27"),
    (ACC, "m2", "2026-w27", "urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m2:2026-w27"),
    (ACC, "m2", "2026-07-03", "urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m2:2026-07-03"),
    (ACC, "m2", "2026-07-04", "urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m2:2026-07-04"),
    ("e_H6PPP8CA9RR0", "m2", "2030-w01", "urn:evidaxis:claim:e_H6PPP8CA9RR0:m2:2030-w01"),
    ("EVX:LIB:0A1B2C3D4E5F", "m99", "2099-12-31", "urn:evidaxis:claim:EVX:LIB:0A1B2C3D4E5F:m99:2099-12-31"),
]


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


def test_shared_vectors_mirror_ts():
    """20 vectors shared with web/src/lib/claim_urn.test.ts — byte-identical agreement."""
    assert len(SHARED_VECTORS) == 20
    for accession, method, epoch, want in SHARED_VECTORS:
        got = build(accession, method, epoch)
        assert got == want
        assert parse(got) == {
            "accession_id": accession,
            "methodology_version": method,
            "epoch": epoch,
        }
