"""EVX_DO_NOT_OBSERVE is a list of numeric repository ids. Collectors do not call it."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "do_not_observe.py"


def _load():
    spec = importlib.util.spec_from_file_location("evx_do_not_observe", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


do_not_observe = _load()


def test_is_blocked_matches_listed_ids(monkeypatch) -> None:
    monkeypatch.setenv("EVX_DO_NOT_OBSERVE", "900001, 900002")
    assert do_not_observe.is_blocked(900001) is True
    assert do_not_observe.is_blocked(900002) is True
    assert do_not_observe.is_blocked(900003) is False


def test_empty_list_blocks_nothing(monkeypatch) -> None:
    monkeypatch.delenv("EVX_DO_NOT_OBSERVE", raising=False)
    assert do_not_observe.is_blocked(900001) is False


def test_cli_reports_blocked_and_clear(monkeypatch) -> None:
    monkeypatch.setenv("EVX_DO_NOT_OBSERVE", "900001,900002")
    env = dict(os.environ)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "900001", "900003"],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 1
    assert result.stdout == "900001 blocked\n900003 clear\n"
    assert "900002" not in result.stdout


def test_malformed_list_is_an_error(monkeypatch) -> None:
    monkeypatch.setenv("EVX_DO_NOT_OBSERVE", "900001,nope")
    try:
        do_not_observe.is_blocked(900001)
        raised = False
    except do_not_observe.ListError:
        raised = True
    assert raised is True
    env = dict(os.environ)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "900001"],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 2
    assert result.stdout == "do-not-observe: malformed list\n"


def test_collectors_do_not_reference_do_not_observe() -> None:
    for path in sorted((REPO / "collectors").glob("*.py")):
        assert "do_not_observe" not in path.read_text(encoding="utf-8")
