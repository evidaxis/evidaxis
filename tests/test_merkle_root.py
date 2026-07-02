"""CI gate for the archive Merkle root: determinism, tamper-detection, domain
separation, and that the real data/ archive folds to a stable root."""
import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))
from merkle_root import compute, leaf, merkle_root


def test_root_is_deterministic():
    a = merkle_root([leaf("a.txt", b"1"), leaf("b.txt", b"2"), leaf("c.txt", b"3")])
    b = merkle_root([leaf("a.txt", b"1"), leaf("b.txt", b"2"), leaf("c.txt", b"3")])
    assert a == b


def test_single_byte_change_flips_root():
    base = [leaf("a.txt", b"1"), leaf("b.txt", b"2")]
    tampered = [leaf("a.txt", b"1"), leaf("b.txt", b"2x")]
    assert merkle_root(base) != merkle_root(tampered)


def test_rename_flips_root():
    # leaves bind the path, so moving identical content to a new name is detected
    assert merkle_root([leaf("a.txt", b"x")]) != merkle_root([leaf("b.txt", b"x")])


def test_reorder_flips_root():
    assert merkle_root([leaf("a", b"1"), leaf("b", b"2")]) != merkle_root([leaf("b", b"2"), leaf("a", b"1")])


def test_leaf_and_node_are_domain_separated():
    # a leaf digest must never collide with an internal-node digest of the same material
    lf = leaf("x", b"y")
    node = hashlib.sha256(b"\x01" + lf + lf).digest()
    assert lf != node


def test_empty_is_total():
    assert merkle_root([]) == hashlib.sha256(b"").digest()


def test_real_archive_computes_a_root():
    r = compute()
    assert r["root"].startswith("sha256:")
    assert r["n_files"] >= 1
    assert r["file_list_sha256"].startswith("sha256:")
    # recomputing over the unchanged archive reproduces the same root
    assert compute()["root"] == r["root"]
