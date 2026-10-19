"""No workflow keeps a person index, or the addresses resolved from it, between runs.

actions/cache and actions/upload-artifact persist a path after the runner is
gone. EVX_PERSON_INDEX_DIR set to a workspace path does the same. A planted
workflow must make this check fail. A path under runner.temp is one run only.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
_ASSIGN = re.compile(r"EVX_PERSON_INDEX_DIR\s*=\s*(['\"]?)([^\s;'\"]+)\1")
_REDIRECT = re.compile(r">\s*['\"]?[^\s'\"]*index\.json")


def _action(uses: object) -> str:
    if not isinstance(uses, str):
        return ""
    return uses.split("@", 1)[0].strip()


def _persisting_action(uses: object) -> bool:
    name = _action(uses)
    return name in {"actions/cache", "actions/upload-artifact"} or name.startswith("actions/cache/") or name.startswith("actions/upload-artifact/")


def _path_is_index(path: str) -> bool:
    parts = [part for part in path.replace("\\", "/").lower().split("/") if part not in {"", ".", ".."}]
    for part in parts:
        bare = part.split("?", 1)[0]
        if bare == "index.json" or "person_index" in bare or "person-index" in bare or "evx_person_index" in bare:
            return True
    return False


def _workspace_value(value: str) -> bool:
    text = value.strip().strip("\"'")
    lower = text.lower()
    if "github.workspace" in lower or "github_workspace" in lower:
        return True
    if "runner.temp" in lower or "runner_temp" in lower:
        return False
    if text.startswith("/") or text.startswith("~") or text.startswith("$") or text.startswith("${{"):
        return False
    return bool(text)


def _env_values(env: object) -> list[str]:
    if not isinstance(env, dict) or "EVX_PERSON_INDEX_DIR" not in env:
        return []
    return [str(env["EVX_PERSON_INDEX_DIR"])]


def findings(directory: Path) -> list[str]:
    """Paths that would keep the index after the run. Empty means the tree is clean."""
    found: list[str] = []
    for path in sorted(directory.glob("*.yml")):
        workflow = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        workflow_env = _env_values(workflow.get("env"))
        for job_name, job in (workflow.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            job_env = workflow_env + _env_values(job.get("env"))
            for index, step in enumerate(job.get("steps") or []):
                if not isinstance(step, dict):
                    continue
                label = f"{path.name}:{job_name}:{index}"
                values = job_env + _env_values(step.get("env"))
                run = step.get("run") or ""
                if isinstance(run, str):
                    values.extend(match.group(2) for match in _ASSIGN.finditer(run))
                    if _REDIRECT.search(run):
                        found.append(label)
                if any(_workspace_value(value) for value in values):
                    found.append(label)
                if _persisting_action(step.get("uses")):
                    raw = (step.get("with") or {}).get("path", "")
                    lines = raw if isinstance(raw, list) else str(raw).splitlines()
                    if any(_path_is_index(line) for line in lines):
                        found.append(label)
    return found


def _plant(tmp_path: Path, body: str) -> Path:
    folder = tmp_path / "workflows"
    folder.mkdir()
    path = folder / "planted.yml"
    path.write_text(body, encoding="utf-8")
    return folder


def test_checked_in_workflows_do_not_keep_a_person_index() -> None:
    assert findings(REPO / ".github" / "workflows") == []


def test_cache_of_index_json_is_rejected(tmp_path: Path) -> None:
    folder = _plant(tmp_path, """
name: planted
on: push
jobs:
  keep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/cache@v4
        with:
          path: person-index/index.json
          key: planted
""")
    assert findings(folder)


def test_uploaded_index_json_is_rejected(tmp_path: Path) -> None:
    folder = _plant(tmp_path, """
name: planted
on: push
jobs:
  keep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/upload-artifact@v4
        with:
          name: index
          path: index.json
""")
    assert findings(folder)


def test_workspace_index_variable_is_rejected(tmp_path: Path) -> None:
    folder = _plant(tmp_path, """
name: planted
on: push
jobs:
  keep:
    runs-on: ubuntu-latest
    steps:
      - name: write the index into the workspace
        run: mkdir -p "$EVX_PERSON_INDEX_DIR"
        env:
          EVX_PERSON_INDEX_DIR: ${{ github.workspace }}/person-index
""")
    assert findings(folder)


def test_shell_assignment_into_the_workspace_is_rejected(tmp_path: Path) -> None:
    folder = _plant(tmp_path, """
name: planted
on: push
jobs:
  keep:
    runs-on: ubuntu-latest
    steps:
      - run: export EVX_PERSON_INDEX_DIR="$GITHUB_WORKSPACE/person-index"
""")
    assert findings(folder)


def test_runner_temp_index_is_not_a_workspace_write(tmp_path: Path) -> None:
    folder = _plant(tmp_path, """
name: planted
on: push
jobs:
  keep:
    runs-on: ubuntu-latest
    steps:
      - run: mkdir -p "$EVX_PERSON_INDEX_DIR"
        env:
          EVX_PERSON_INDEX_DIR: ${{ runner.temp }}/person-index
""")
    assert findings(folder) == []
