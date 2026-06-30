"""Shared pytest fixtures for the etl/ test suite (public, runs in CI).

Puts etl/ on sys.path so the collector scripts import by bare module name
(`import collect`), and provides an `isolated_repo` fixture that redirects the
collector's ROOT/REPO module globals at a temp directory so artifact-writing
tests never touch the real repo tree.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ETL = REPO_ROOT / "etl"
if str(ETL) not in sys.path:
    sys.path.insert(0, str(ETL))


@pytest.fixture
def isolated_repo(tmp_path, monkeypatch):
    """Redirect collect.ROOT/REPO to a throwaway tree.

    collect.write_artifacts writes into collect.REPO/{data,entities,taxonomy};
    without this redirect a pipeline test would mutate the real repo. Seeds a
    copy of seeds.json into the fake etl/ dir so load_seeds() still works.
    """
    import collect

    fake_root = tmp_path / "etl"
    fake_root.mkdir(parents=True, exist_ok=True)
    (fake_root / "seeds.json").write_text((ETL / "seeds.json").read_text())
    monkeypatch.setattr(collect, "ROOT", fake_root, raising=True)
    monkeypatch.setattr(collect, "REPO", tmp_path, raising=True)
    return tmp_path
