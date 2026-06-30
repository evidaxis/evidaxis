"""Identity / slug helper tests for etl/collect.py (investor-grade audit baseline).

Locks the three pure, deterministic helpers that mint opaque entity ids and
human slugs and stamp ISO-week periods. These are the load-bearing identity
primitives: a drift in mint_entity_id silently re-keys every dossier card,
history file and redirect, so the algorithm is pinned both structurally AND
against the real etl/id_map.json the live snapshots already committed.

No network, no writes. conftest.py puts etl/ on sys.path -> `import collect`.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

import collect

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"   # no I L O U (mirror of collect.CROCKFORD)
ID_MAP = json.loads((Path(collect.__file__).resolve().parent / "id_map.json").read_text())


# ---------------------------------------------------------------- mint_entity_id

def _independent_mint(natural_key: str) -> str:
    """Re-implementation from the docstring spec, used as an oracle that the
    test's own understanding of the algorithm matches the code (and id_map)."""
    import hashlib
    h = hashlib.sha256(natural_key.lower().encode()).digest()
    n = int.from_bytes(h[:8], "big")
    chars = []
    for _ in range(10):
        chars.append(CROCKFORD[n & 31]); n >>= 5
    data = "".join(chars)
    chk = CROCKFORD[sum(CROCKFORD.index(c) for c in data) % 32]
    return f"e_{data}{chk}"


def test_constant_matches_crockford_alphabet():
    # the alphabet the body+checksum draw from — no I,L,O,U (Crockford base32)
    assert collect.CROCKFORD == CROCKFORD
    for bad in "ILOU":
        assert bad not in collect.CROCKFORD
    assert len(collect.CROCKFORD) == 32


@pytest.mark.parametrize("key", [
    "huggingface/lerobot", "a/b", "Foo/Bar", "x", "", "  ", "tab\tkey",
    "UPPER/CASE", "openvla/openvla",
])
def test_mint_format_and_alphabet(key):
    eid = collect.mint_entity_id(key)
    # e_ + 10 body + 1 checksum == 13 chars total
    assert eid.startswith("e_")
    assert len(eid) == 13
    body_chk = eid[2:]
    assert len(body_chk) == 11
    # every body+checksum char is in the Crockford alphabet (no I,L,O,U)
    assert all(c in CROCKFORD for c in body_chk)


@pytest.mark.parametrize("key", [
    "huggingface/lerobot", "a/b", "Foo/Bar", "x", "", "weird key/with spaces",
])
def test_mint_deterministic_across_calls(key):
    # pure function: same key -> same id every time
    assert collect.mint_entity_id(key) == collect.mint_entity_id(key)


@pytest.mark.parametrize("key", [
    "huggingface/lerobot", "a/b", "Foo/Bar", "x", "openvla/openvla", "dora-rs/dora",
])
def test_mint_checksum_independently_recomputed(key):
    eid = collect.mint_entity_id(key)
    body = eid[2:12]            # the 10 data chars
    chk = eid[12]               # the 1 checksum char
    # INDEPENDENT recompute: sum of Crockford indices mod 32
    expected_chk = CROCKFORD[sum(CROCKFORD.index(c) for c in body) % 32]
    assert chk == expected_chk


@pytest.mark.parametrize("key", [
    "huggingface/lerobot", "a/b", "Foo/Bar", "x", "", "openvla/openvla",
])
def test_mint_matches_independent_oracle(key):
    assert collect.mint_entity_id(key) == _independent_mint(key)


def test_mint_case_insensitive_lower_collides():
    # key.lower() => differing-case keys mint the SAME id
    assert collect.mint_entity_id("A/B") == collect.mint_entity_id("a/b")
    assert collect.mint_entity_id("Foo/Bar") == collect.mint_entity_id("foo/bar")
    assert collect.mint_entity_id("HuggingFace/LeRobot") == collect.mint_entity_id("huggingface/lerobot")


def test_mint_does_not_strip_whitespace():
    # only lowercases — does NOT strip; a trailing space is a DIFFERENT key
    assert collect.mint_entity_id("a/b") != collect.mint_entity_id("a/b ")
    assert collect.mint_entity_id("a/b") != collect.mint_entity_id(" a/b")
    assert collect.mint_entity_id(" a/b") != collect.mint_entity_id("a/b ")


def test_mint_distinct_keys_distinct_ids():
    keys = ["huggingface/lerobot", "openvla/openvla", "dora-rs/dora",
            "a/b", "a/c", "b/a", "x", "y"]
    ids = [collect.mint_entity_id(k) for k in keys]
    assert len(set(ids)) == len(ids)            # no collisions among distinct keys


@pytest.mark.parametrize("repo,eid", list(ID_MAP.items()))
def test_mint_locked_against_real_id_map(repo, eid):
    """LOCK THE ALGORITHM AGAINST REALITY: every repo->id pair the live
    pipeline already committed to etl/id_map.json must reproduce exactly.
    A drift here means re-keyed dossiers/history/redirects on the deposited
    CC0 record."""
    assert collect.mint_entity_id(repo) == eid


def test_id_map_nonempty_and_well_formed():
    # guard the lock above isn't vacuously testing an empty/garbage map
    assert len(ID_MAP) >= 10
    for eid in ID_MAP.values():
        assert eid.startswith("e_") and len(eid) == 13


# ---------------------------------------------------------------- slugify

@pytest.mark.parametrize("name,expected", [
    ("Foo Bar", "foo-bar"),
    ("UPPER", "upper"),                         # lowercases
    ("Genesis-Embodied AI", "genesis-embodied-ai"),
    ("Hello!!World", "hello-world"),            # non-alnum run -> single '-'
    ("a   b", "a-b"),                           # whitespace run -> single '-'
    ("a___b", "a-b"),                           # underscores are non-alnum
    ("a---b", "a-b"),                           # collapse repeats
    ("a-b-c", "a-b-c"),
    ("openvla/openvla", "openvla-openvla"),     # slash -> '-'
    ("v2.0", "v2-0"),
    ("café", "caf"),                            # non-ascii dropped (only a-z0-9 kept)
    ("123", "123"),                             # digits kept
])
def test_slugify_basic(name, expected):
    assert collect.slugify(name) == expected


@pytest.mark.parametrize("name", [
    "  leading", "trailing  ", "  both  ", "-dash-", "!bang!", "...dots...",
])
def test_slugify_strips_leading_trailing_separators(name):
    s = collect.slugify(name)
    assert not s.startswith("-")
    assert not s.endswith("-")
    assert s != ""


@pytest.mark.parametrize("name", ["", "   ", "@@@", "!!!", "---", "...", "***", "/", " / "])
def test_slugify_empty_or_all_symbol_yields_x(name):
    # empty / all-symbol input falls back to 'x' (never an empty slug)
    assert collect.slugify(name) == "x"


@pytest.mark.parametrize("name", ["Foo Bar", "A-B-C", "x y z", "openvla/openvla", "  Spaced  "])
def test_slugify_never_double_dash_or_edge_dash(name):
    s = collect.slugify(name)
    assert "--" not in s
    assert not s.startswith("-") and not s.endswith("-")
    # output only ever contains a-z0-9 and '-'
    assert all(c.islower() or c.isdigit() or c == "-" for c in s)


# ---------------------------------------------------------------- iso_period

@pytest.mark.parametrize("d,expected", [
    (date(2021, 1, 4), "2021-w01"),     # ISO week 1 -> ZERO-PADDED single digit
    (date(2026, 1, 5), "2026-w02"),     # week 2
    (date(2026, 6, 30), "2026-w27"),
    (date(2024, 12, 30), "2025-w01"),   # ISO year rolls forward across calendar year
    (date(2021, 1, 1), "2020-w53"),     # ISO year rolls BACK; two-digit week unpadded
])
def test_iso_period_known_dates(d, expected):
    assert collect.iso_period(d) == expected


def test_iso_period_zero_pads_single_digit_week():
    # explicit: a single-digit week must render with a leading zero (sortable)
    s = collect.iso_period(date(2021, 1, 4))
    assert s == "2021-w01"
    wk = s.split("-w")[1]
    assert len(wk) == 2 and wk == "01"


@pytest.mark.parametrize("d", [
    date(2020, 3, 15), date(2022, 7, 1), date(2025, 11, 23), date(2026, 1, 5),
])
def test_iso_period_shape(d):
    # always YYYY-wWW : 4-digit ISO year, literal '-w', 2-digit week matching isocalendar
    s = collect.iso_period(d)
    yr, _, wk = s.partition("-w")
    iso = d.isocalendar()
    assert yr == str(iso[0]) and len(yr) == 4
    assert wk == f"{iso[1]:02d}" and len(wk) == 2
    assert 1 <= int(wk) <= 53
