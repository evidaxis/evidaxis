#!/usr/bin/env python3
"""Value-blind catchup of the m4 dependents panel, effective partition 2026-10-19.

A registry system outside the current m4 panel contributes a package only when
the root manifest declares it, deps.dev publishes that name, and the published
metadata does not name some other source repository. Dependent counts are never
read: a URL containing "dependents" is refused.

  python3 collectors/axis3_panel_catchup.py --partition 2026-10-19 \\
      --out data/quarantine/axis3-deps-v2/ --write-record

Writes expansion-manifest-<partition>.json, its sha256 sidecar, and
linkage-audit-<partition>.json. --resume rereads the response cache
(EVX_GH_CACHE_DIR, or the system temp dir). Standard library only.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import tempfile
import threading
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

try:
    from collectors import axis3_m4_identity as ident
except ImportError:
    import axis3_m4_identity as ident

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "data/quarantine/axis3-deps-v2"
MANIFEST_NAME = "expansion-manifest-2026-10-19.json"
AUDIT_NAME = "linkage-audit-2026-10-19.json"
ROOT_FILES = ("package.json", "pyproject.toml", "setup.py", "Cargo.toml", "go.mod")
# 0.75s keeps GitHub contents under the authenticated 5000/hour REST cap.
GITHUB_INTERVAL_S = 0.75
# The catchup order caps deps.dev at about 5 requests a second.
DEPSDEV_INTERVAL_S = 0.2
RAW_INTERVAL_S = 0.2
RETRY_CAP_S = 30  # a single retry wait; a read that still fails is not_admitted
_DEPS_LOCK = threading.Lock()
ADMITTED_VERDICTS = ("verified", "no_link")
EXCLUDED_VERDICTS = ("other_repo", "not_admitted")

_SETUP_NAME = re.compile(r"""(?m)^[ \t]*name[ \t]*=[ \t]*["']([^"']+)["']""")
_CHANGED = "[catchup] изменённые данные → новая датированная запись"
_GH_REPO = re.compile(r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.I)
_FRONT_ID = re.compile(r"(?m)^entity_id:\s*(\S+)\s*$")
_FRONT_REPO = re.compile(r'(?m)^  github_repo:\s*"?([^"\n]+?)"?\s*$')


class _Pace:
    def __init__(self, interval: float):
        self.interval = interval
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self._next - now
            self._next = max(now, self._next) + self.interval
        if delay > 0:
            time.sleep(delay)


def pypi_normalize(name: str) -> str:
    """PEP 503. deps.dev indexes the normalized name; the raw spelling 404s."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _toml_header(line: str) -> str | None:
    """Table name from a header, including one with a trailing comment."""
    stripped = line.strip()
    if not stripped.startswith("["):
        return None
    quote = None
    for index, char in enumerate(stripped):
        if quote is not None:
            if char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
            continue
        if char == "#":
            return None
        if char == "]":
            rest = stripped[index + 1:].strip()
            if rest == "" or rest.startswith("#"):
                return stripped[1:index].strip()
            return None
    return None


def _assigned_name(line: str) -> str | None:
    found = re.match(r"""name\s*=\s*["']([^"']+)["']""", line.strip())
    return found.group(1) if found else None


def _pyproject_name_lines(text: str) -> str | None:
    section = None
    project_name = poetry_name = None
    for line in text.splitlines():
        header = _toml_header(line)
        if header is not None:
            section = header
            continue
        found = _assigned_name(line)
        if found is None:
            continue
        if section == "project" and project_name is None:
            project_name = found
        elif section == "tool.poetry" and poetry_name is None:
            poetry_name = found
    return project_name or poetry_name


def _string_field(table: object, key: str) -> str | None:
    if not isinstance(table, dict):
        return None
    value = table.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _pyproject_name(text: str) -> str | None:
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return _pyproject_name_lines(text)
    if not isinstance(doc, dict):
        return None
    project = _string_field(doc.get("project"), "name")
    tool = doc.get("tool")
    poetry = _string_field(tool.get("poetry"), "name") if isinstance(tool, dict) else None
    return project or poetry


def _cargo_name_lines(text: str) -> str | None:
    in_pkg = False
    for line in text.splitlines():
        header = _toml_header(line)
        if header is not None:
            in_pkg = header == "package"
            continue
        if not in_pkg:
            continue
        found = _assigned_name(line)
        if found:
            return found
    return None


def _cargo_name(text: str) -> str | None:
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return _cargo_name_lines(text)
    if not isinstance(doc, dict):
        return None
    return _string_field(doc.get("package"), "name")


def _setup_keyword_name(text: str, start: int) -> str | None:
    """Literal name= argument inside one setup() call, or None."""
    depth = 1
    index = start
    length = len(text)
    while index < length and depth:
        char = text[index]
        if char in {"'", '"'}:
            quote = char
            index += 1
            while index < length and text[index] != quote:
                index += 2 if text[index] == "\\" else 1
            index += 1
            continue
        if char == "(":
            depth += 1
            index += 1
            continue
        if char == ")":
            depth -= 1
            if depth == 0:
                return None
            index += 1
            continue
        if depth == 1 and (index == start or not (text[index - 1].isalnum() or text[index - 1] == "_")):
            found = re.match(r"""name\s*=\s*(['"])([^'"]*)\1""", text[index:])
            if found:
                previous = text[:index].rstrip()
                if previous.endswith((",", "(")):
                    return found.group(2)
        index += 1
    return None


def _setup_call_name(text: str) -> str | None:
    for match in re.finditer(r"\bsetup\s*\(", text):
        name = _setup_keyword_name(text, match.end())
        if name:
            return name
    return None


def _literal_setup_name(text: str) -> str | None:
    """name= of a real setup(...) call, read from Python syntax without running it.

    Only a plain string literal counts. Comments, other assignments and computed
    names (concatenation, variables) yield no package, so no foreign name can
    enter the panel. Unparseable files fall back to nothing, not to text search.
    """
    import ast
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
        if called != "setup":
            continue
        for keyword in node.keywords:
            if keyword.arg == "name" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                return keyword.value.value
    return None


def parse_root_manifest(filename: str, text: str) -> tuple[str, str] | None:
    """(deps.dev system, package name) declared by one root manifest, or None.

    A private package.json is not a publication. Poetry-only projects keep the
    name under tool.poetry when [project] is absent.
    """
    if filename == "pyproject.toml":
        chosen = _pyproject_name(text)
        return ("pypi", pypi_normalize(chosen)) if chosen else None
    if filename == "setup.py":
        found = _literal_setup_name(text)
        return ("pypi", pypi_normalize(found)) if found else None
    if filename == "package.json":
        try:
            doc = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(doc, dict) or doc.get("private") is True or not isinstance(doc.get("name"), str):
            return None
        if not doc["name"]:
            return None
        return ("npm", doc["name"])
    if filename == "Cargo.toml":
        chosen = _cargo_name(text)
        return ("cargo", chosen) if chosen else None
    if filename == "go.mod":
        found = re.search(r'(?m)^module\s+"?([^"\s]+)"?', text)
        # A module path without a slash is not a public Go module.
        if found and "/" in found.group(1):
            return ("go", found.group(1))
    return None


def github_repo_from_text(value: str) -> str | None:
    match = _GH_REPO.search(value or "")
    if not match:
        return None
    owner, name = match.group(1), match.group(2).removesuffix(".git")
    if owner.casefold() in {"orgs", "sponsors", "settings", "features"}:
        return None
    return f"{owner}/{name}"


def _alias_key(repo: str) -> str:
    return repo.casefold()


def linkage_verdict(aliases: set[str], version: dict | None, *, error: str | None = None) -> tuple[str, str | None]:
    """(verdict, reason).

    verified / other_repo / no_link match the 2026-10-04 audit. not_admitted is
    the explicit refusal when the two directions disagree or the read failed.
    """
    if error:
        return "not_admitted", error
    if not isinstance(version, dict):
        return "not_admitted", "version metadata unreadable"
    known = {_alias_key(name) for name in aliases if name}
    source_ids = []
    for project in version.get("relatedProjects") or []:
        if project.get("relationType") != "SOURCE_REPO":
            continue
        project_id = str((project.get("projectKey") or {}).get("id") or "")
        if project_id:
            source_ids.append(project_id)
    link_ids = []
    for link in version.get("links") or []:
        repo = github_repo_from_text(link.get("url") or "")
        if repo:
            link_ids.append(repo)
    named = source_ids or link_ids
    if not named:
        return "no_link", None
    matched = 0
    foreign = 0
    for raw in named:
        repo = github_repo_from_text(raw if "://" in raw or raw.startswith("github.com/") else raw)
        key = _alias_key(repo) if repo else ""
        bare = raw.casefold().removeprefix("https://").removeprefix("http://").removeprefix("github.com/")
        bare = bare.removesuffix(".git").strip("/")
        if key in known or bare in known:
            matched += 1
        else:
            foreign += 1
    if matched and not foreign:
        return "verified", None
    if matched and foreign:
        return "not_admitted", "metadata names this repository and another"
    return "other_repo", None


def registry_repos(entities: Path | None = None) -> list[tuple[str, str]]:
    """(entity_id, owner/repo) from card frontmatter, sorted by entity id."""
    root = entities or (REPO / "entities")
    found = []
    for path in root.glob("e_*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        front = parts[1]
        eid = _FRONT_ID.search(front)
        repo = _FRONT_REPO.search(front)
        if not eid or not repo:
            continue
        found.append((eid.group(1), repo.group(1).strip()))
    return sorted(found)


def alias_map(registry_ids: dict) -> dict[str, set[str]]:
    """casefold(owner/repo) -> every stored and canonical name sharing that repo id."""
    groups: dict[int, set[str]] = defaultdict(set)
    lone: dict[str, set[str]] = {}
    for name, info in (registry_ids.get("members") or {}).items():
        names = {name}
        canonical = info.get("canonical")
        if canonical:
            names.add(str(canonical))
        repo_id = info.get("repo_id")
        if isinstance(repo_id, int):
            groups[repo_id].update(names)
        else:
            lone[_alias_key(name)] = names
    out: dict[str, set[str]] = {}
    for names in groups.values():
        for name in names:
            out.setdefault(_alias_key(name), set()).update(names)
    for key, names in lone.items():
        out.setdefault(key, set()).update(names)
    return out


def aliases_for(repo: str, redirected: str | None, table: dict[str, set[str]]) -> set[str]:
    names = {repo}
    if redirected:
        names.add(redirected)
    for name in list(names):
        names.update(table.get(_alias_key(name), ()))
    return names


def decide_rows(rows: list[dict], taken: set[tuple[str, str]]) -> list[dict]:
    """Apply panel-collision and same-name rules. Does not read dependent counts.

    `taken` is the current m4 panel as (SYSTEM, name). A name already mapped
    there stays on its old system. Two new systems declaring one unpublished
    link are both refused: either name would be a silent pick.
    """
    decided = []
    for row in rows:
        if row.get("verdict") in ADMITTED_VERDICTS and (row["system"].upper(), row["package"]) in taken:
            row = dict(row)
            row["verdict"] = "not_admitted"
            row["reason"] = "already in the m4 panel"
        decided.append(row)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in decided:
        if row.get("verdict") in ADMITTED_VERDICTS:
            groups[(row["system"].upper(), row["package"])].append(row)
    for group in groups.values():
        if len(group) < 2:
            continue
        verified = [row for row in group if row["verdict"] == "verified"]
        if len(verified) == 1:
            keep = verified[0]
            for row in group:
                if row is keep:
                    continue
                row["verdict"] = "not_admitted"
                row["reason"] = "same published name declared by more than one system"
            continue
        for row in group:
            row["verdict"] = "not_admitted"
            row["reason"] = "same published name declared by more than one system"
    return decided


def _refuse_value_url(url: str) -> None:
    if "dependents" in url.casefold():
        raise RuntimeError("value-blind catchup refuses dependent-count reads")


def _http_get(url: str, headers: dict[str, str], pacer: _Pace) -> tuple[int, str, bytes]:
    _refuse_value_url(url)
    last_status, last_url, last_body = 0, url, b""
    for attempt in range(4):
        pacer.wait()
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                return resp.status, resp.geturl(), resp.read()
        except urllib.error.HTTPError as exc:
            last_body = exc.read()
            last_status = exc.code
            last_url = url
            if exc.code not in (403, 429, 500, 502, 503, 504) or attempt == 3:
                return exc.code, url, last_body
            wait = min(RETRY_CAP_S, 2 ** attempt)
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            if retry_after:
                try:
                    wait = min(RETRY_CAP_S, max(wait, float(retry_after)))
                except ValueError:
                    pass
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError, OSError):
            last_status, last_body = 0, b""
            if attempt == 3:
                return 0, url, b""
            time.sleep(min(RETRY_CAP_S, 2 ** attempt))
    return last_status, last_url, last_body


def cache_dir() -> Path:
    """Response cache outside the repository. EVX_GH_CACHE_DIR, else the system temp dir."""
    raw = os.environ.get("EVX_GH_CACHE_DIR")
    path = Path(raw).expanduser().resolve() if raw else Path(tempfile.gettempdir()) / "evidaxis-axis3-catchup-2026-10-19"
    repo = REPO.resolve()
    if path == repo or repo in path.parents:
        raise RuntimeError("catchup cache must stay outside the repository")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_json(path: Path, payload: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(path)
    return payload


def _load_cache(path: Path, resume: bool) -> dict | None:
    if not resume or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _github_token() -> str:
    # No `gh auth token`: that opens the keychain and would hide a no-key run.
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def _transport_incomplete(status: int, body: bytes) -> bool:
    """A rate limit or a dropped connection is not a fact about the repository."""
    if status in (0, 429, 500, 502, 503, 504):
        return True
    return status == 403 and b"rate limit" in body.lower()


def _redirected_repo(final_url: str) -> str | None:
    match = re.search(r"repos/([^/]+)/([^/]+)/contents", final_url or "")
    if not match:
        return None
    return f"{match.group(1)}/{match.group(2)}"


def _manifest_text(filename: str, repo: str, token: str, gh_pace: _Pace, raw_pace: _Pace,
                  cache: Path, resume: bool) -> tuple[str | None, str | None, bool]:
    """Return (text, error, incomplete). The contents listing already proved the file is in the tree.

    The body is read from raw.githubusercontent so the REST budget stays on listings.
    The contents API is the fallback when raw does not return the file.
    """
    key = hashlib.sha256(f"{repo}/{filename}".encode()).hexdigest()
    path = cache / "manifests" / key[:2] / f"{key}.json"
    cached = _load_cache(path, resume)
    if cached and "text" in cached:
        return cached.get("text"), cached.get("error"), False
    raw_status, _u, raw = _http_get(
        f"https://raw.githubusercontent.com/{repo}/HEAD/{urllib.parse.quote(filename)}",
        {"User-Agent": "evidaxis-catchup"}, raw_pace)
    if raw_status == 200:
        text = raw.decode("utf-8", "replace")
        _cache_json(path, {"text": text, "error": None})
        return text, None, False
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "evidaxis-catchup",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, _final, body = _http_get(
        f"https://api.github.com/repos/{repo}/contents/{urllib.parse.quote(filename)}", headers, gh_pace)
    if status != 200:
        # A failed raw read plus a failed API read is retried. A stable 404 is a refusal.
        incomplete = _transport_incomplete(status, body) or _transport_incomplete(raw_status, raw)
        return None, "manifest unreadable", incomplete
    try:
        doc = json.loads(body.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        doc = None
    if isinstance(doc, dict) and doc.get("encoding") == "base64" and doc.get("content"):
        text = base64.b64decode(doc["content"]).decode("utf-8", "replace")
        _cache_json(path, {"text": text, "error": None})
        return text, None, False
    return None, "manifest unreadable", False


def _depsdev_version(system: str, name: str, pacer: _Pace, cache: Path, resume: bool) -> dict:
    key = hashlib.sha256(f"{system}/{name}".encode()).hexdigest()
    path = cache / "deps" / key[:2] / f"{key}.json"
    with _DEPS_LOCK:
        cached = _load_cache(path, resume)
        if cached:
            return cached
        return _depsdev_version_uncached(system, name, pacer, path)


def _depsdev_version_uncached(system: str, name: str, pacer: _Pace, path: Path) -> dict:
    quoted = urllib.parse.quote(name, safe="")
    base = f"https://api.deps.dev/v3/systems/{system.upper()}/packages/{quoted}"
    headers = {"User-Agent": "evidaxis-catchup", "Accept": "application/json"}
    status, _url, body = _http_get(base, headers, pacer)
    if _transport_incomplete(status, body):
        return {"published": None, "version": None, "error": "deps.dev package request failed", "incomplete": True}
    if status == 404:
        payload = {"published": False, "version": None, "error": None}
        return _cache_json(path, payload)
    if status != 200:
        return {"published": None, "version": None, "error": "deps.dev package request failed", "incomplete": True}
    try:
        doc = json.loads(body.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        return {"published": None, "version": None, "error": "deps.dev package request failed", "incomplete": True}
    canonical = str((doc.get("packageKey") or {}).get("name") or name)
    versions = doc.get("versions") or []
    if not versions:
        return _cache_json(path, {"published": False, "version": None, "error": None, "canonical": canonical})
    default = next((row for row in versions if row.get("isDefault")), None)
    chosen = default or versions[-1]
    version = str((chosen.get("versionKey") or {}).get("version") or "")
    if not version:
        return {"published": True, "version": None, "error": "version metadata unreadable", "canonical": canonical,
                "incomplete": True}
    vurl = f"{base}/versions/{urllib.parse.quote(version, safe='')}"
    vstatus, _u, vbody = _http_get(vurl, headers, pacer)
    if vstatus != 200 or _transport_incomplete(vstatus, vbody):
        return {"published": True, "version": None, "error": "version metadata unreadable", "canonical": canonical,
                "incomplete": True}
    try:
        version_doc = json.loads(vbody.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        return {"published": True, "version": None, "error": "version metadata unreadable", "canonical": canonical,
                "incomplete": True}
    canonical = str((version_doc or {}).get("versionKey", {}).get("name") or canonical)
    return _cache_json(path, {"published": True, "version": version_doc, "error": None, "canonical": canonical})


def _package_row(entity_id: str, repo: str, system: str, package: str, filename: str,
                 published, verdict: str, reason: str | None, incomplete: bool = False) -> dict:
    return {
        "entity_id": entity_id, "repo": repo, "system": system, "package": package,
        "manifest_path": filename, "published": published, "verdict": verdict, "reason": reason,
        "incomplete": incomplete,
    }


def _scan_repo(entity_id: str, repo: str, token: str, table: dict[str, set[str]],
               gh_pace: _Pace, raw_pace: _Pace, deps_pace: _Pace, cache: Path, resume: bool) -> dict:
    done = cache / "repos" / f"{entity_id}.json"
    cached = _load_cache(done, resume)
    if cached:
        return cached
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "evidaxis-catchup",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, final, body = _http_get(f"https://api.github.com/repos/{repo}/contents/", headers, gh_pace)
    record: dict = {"entity_id": entity_id, "repo": repo, "http_status": status, "packages": [],
                    "private_root": False}
    if status != 200:
        record["error"] = "repository root unreadable"
        if _transport_incomplete(status, body):
            record["incomplete"] = True
            return record
        return _cache_json(done, record)
    try:
        listing = json.loads(body.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        record["error"] = "repository root unreadable"
        record["incomplete"] = True
        return record
    if not isinstance(listing, list):
        record["error"] = "repository root unreadable"
        return _cache_json(done, record)
    present = {entry.get("name") for entry in listing if isinstance(entry, dict)}
    record["head_name"] = _redirected_repo(final) or repo
    names = aliases_for(repo, record["head_name"], table)
    seen: set[tuple[str, str]] = set()
    for filename in ROOT_FILES:
        if filename not in present:
            continue
        text, error, incomplete = _manifest_text(filename, repo, token, gh_pace, raw_pace, cache, resume)
        if filename == "package.json" and text:
            try:
                doc = json.loads(text)
            except json.JSONDecodeError:
                doc = None
            if isinstance(doc, dict) and doc.get("private") is True:
                record["private_root"] = True
        if incomplete:
            record["incomplete"] = True
            record["packages"].append(_package_row(
                entity_id, repo, "", "", filename, None, "not_admitted", error or "manifest unreadable", True))
            return record
        if error or text is None:
            record["packages"].append(_package_row(
                entity_id, repo, "", "", filename, None, "not_admitted", error or "manifest unreadable"))
            continue
        parsed = parse_root_manifest(filename, text)
        if not parsed:
            continue
        system, package = parsed
        if (system, package) in seen:
            continue
        seen.add((system, package))
        looked = _depsdev_version(system, package, deps_pace, cache, resume)
        canonical = looked.get("canonical") or package
        if looked.get("incomplete"):
            record["incomplete"] = True
            record["packages"].append(_package_row(
                entity_id, repo, system, canonical, filename, looked.get("published"),
                "not_admitted", looked.get("error") or "deps.dev package request failed", True))
            return record
        if looked.get("published") is False:
            record["packages"].append(_package_row(
                entity_id, repo, system, canonical, filename, False, "not_admitted", "not published"))
            continue
        if looked.get("error") and looked.get("version") is None:
            record["packages"].append(_package_row(
                entity_id, repo, system, canonical, filename, looked.get("published"),
                "not_admitted", looked["error"]))
            continue
        verdict, reason = linkage_verdict(names, looked.get("version"))
        if not verdict:
            raise ValueError(f"catchup: {entity_id} {system}/{canonical} has no audit verdict")
        record["packages"].append(_package_row(
            entity_id, repo, system, canonical, filename, True, verdict, reason))
    return _cache_json(done, record)


def _taken_names() -> set[tuple[str, str]]:
    panel, _sha = ident.load_panel_m4()
    return {(system, name) for pkgs in panel.values() for system, name in pkgs}


def assemble(records: list[dict], taken: set[tuple[str, str]]) -> tuple[dict, dict, dict]:
    """Manifest, audit, and count summary. Admitted rows are verified or no_link."""
    flat = []
    unreadable = []
    private_roots = 0
    for record in records:
        if record.get("error"):
            unreadable.append({"entity_id": record["entity_id"], "http_status": record.get("http_status")})
            continue
        private_roots += int(bool(record.get("private_root")))
        for row in record.get("packages") or []:
            if row.get("verdict") is None and row.get("reason") == "not published":
                flat.append(row)
                continue
            if row.get("package"):
                flat.append(row)
    judged = [row for row in flat if row.get("verdict")]
    judged = decide_rows(judged, taken)
    by_id = {(row["entity_id"], row["system"], row["package"], row["manifest_path"]): row for row in judged}
    merged = []
    for row in flat:
        key = (row["entity_id"], row["system"], row["package"], row["manifest_path"])
        merged.append(by_id.get(key, row))
    repos: dict[str, dict] = {}
    for record in records:
        declared = []
        for row in merged:
            if row["entity_id"] != record["entity_id"] or not row.get("package"):
                continue
            if row.get("reason") == "not published":
                declared.append({"system": row["system"], "package": row["package"],
                                 "manifest_path": row["manifest_path"], "depsdev_exists": False})
            elif row.get("published") is True:
                declared.append({"system": row["system"], "package": row["package"],
                                 "manifest_path": row["manifest_path"], "depsdev_exists": True})
        if not declared and not record.get("error"):
            continue
        if record.get("error"):
            continue
        # Keyed by entity ID: the loader needs only the system and its packages,
        # and a repository name may be a natural person's account (invariant 1).
        repos[record["entity_id"]] = {
            "entity_id": record["entity_id"],
            "declared_packages": declared,
        }
    audit_rows = []
    for row in merged:
        if not row.get("verdict") or not row.get("package"):
            continue
        item = {
            "entity_id": row["entity_id"],
            "system": row["system"],
            "package": row["package"],
            "manifest_path": row["manifest_path"],
            "verdict": row["verdict"],
        }
        if row.get("reason") and row["verdict"] == "not_admitted":
            item["reason"] = row["reason"]
        audit_rows.append(item)
    audit_rows.sort(key=lambda item: (item["entity_id"], item["system"], item["package"], item["manifest_path"]))
    counts: dict[str, int] = defaultdict(int)
    counts["systems_outside_panel"] = len(records)
    counts["roots_unreadable"] = len(unreadable)
    counts["private_root_package_json"] = private_roots
    for row in merged:
        if not row.get("package") and row.get("verdict") == "not_admitted":
            counts["manifest_unreadable"] += 1
            continue
        if not row.get("verdict"):
            raise ValueError(
                f"catchup: {row.get('entity_id')} {row.get('system')}/{row.get('package')} has no audit verdict")
        if row.get("reason") == "not published":
            counts["not_published"] += 1
        counts[f"verdict_{row.get('verdict')}"] += 1
        if row.get("verdict") == "not_admitted" and row.get("reason"):
            counts[f"reason_{row['reason']}"] += 1
    manifest = {
        "v": "axis3_panel_catchup_1",
        "effective_partition": ident.CATCHUP_ACTIVATION,
        "rule": "registry system outside the current m4 panel; package name declared in a root "
                "package.json, pyproject.toml, setup.py, Cargo.toml, or go.mod; name published on "
                "deps.dev; published metadata does not name another source repository. "
                "verified and no_link are admitted. other_repo and not_admitted are refused. "
                "Selection read no dependent counts.",
        "value_blind": "no dependents value was read; deps.dev package and version metadata only",
        "manifest_files": list(ROOT_FILES),
        "root_only": True,
        "counts": dict(sorted(counts.items())),
        "unreadable_roots": sorted(unreadable, key=lambda item: item["entity_id"]),
        "repos": repos,
    }
    audit = {
        "v": "linkage_audit_1",
        "audited_at": "2026-10-19",
        "source": "deps.dev v3: package -> default version -> relatedProjects (SOURCE_REPO) and links",
        "rule": "verified = the published package names the declaring repository (stored, redirected, "
                "or registry canonical full name); other_repo = it names a different repository; "
                "no_link = it names none; not_admitted = the two directions disagree or the read failed, "
                "with a reason, and the package is refused",
        "packages": audit_rows,
    }
    summary = {"counts": dict(sorted(counts.items())), "unreadable": len(unreadable)}
    return manifest, audit, summary


def _json_bytes(doc: dict) -> bytes:
    return (json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def _record_path(partition: str, record_file: Path | None) -> Path:
    return record_file or (REPO / "governance" / f"AXIS3-PANEL-CATCHUP-{partition}.md")


def _bytes_differ(path: Path, blob: bytes) -> bool:
    if not path.exists():
        return False
    try:
        current = path.read_bytes()
    except OSError:
        return True
    return current != blob


def _create_exclusive(path: Path, blob: bytes, *, text: bool) -> bool:
    """Create path. An existing file is left unchanged. False when its bytes differ."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if text:
            with open(path, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(blob.decode("utf-8"))
        else:
            with open(path, "xb") as handle:
                handle.write(blob)
    except FileExistsError:
        try:
            current = path.read_bytes()
        except OSError:
            return False
        return current == blob
    return True


def write_outputs(manifest: dict, audit: dict, out_dir: Path | None = None, partition: str | None = None,
                  preview: bool = False, *, write_record: bool = False,
                  record_file: Path | None = None) -> str | None:
    """Write the manifest and the audit. Return the manifest sha256.

    Returns None, and writes nothing, when a published manifest, checksum, audit,
    or governance record of this partition already exists with different bytes.
    Identical bytes are left untouched. preview=True uses the .preview.json names
    and does not consult the governance record. The panel loader reads only the
    full names, and only a manifest with complete true.
    """
    out = out_dir or OUT_DIR
    part = partition or ident.CATCHUP_ACTIVATION
    suffix = ".preview.json" if preview else ".json"
    manifest_name = f"expansion-manifest-{part}{suffix}"
    audit_name = f"linkage-audit-{part}{suffix}"
    manifest_blob = _json_bytes(manifest)
    digest = hashlib.sha256(manifest_blob).hexdigest()
    planned: list[tuple[Path, bytes, bool]] = [
        (out / manifest_name, manifest_blob, False),
        (out / f"{manifest_name}.sha256", f"{digest}  {manifest_name}\n".encode("utf-8"), False),
        (out / audit_name, _json_bytes(audit), False),
    ]
    governance = None
    if not preview:
        governance = _record_path(part, record_file)
        planned.append((governance, render_record(manifest, digest).encode("utf-8"), True))
    for path, blob, _text in planned:
        if _bytes_differ(path, blob):
            print(_CHANGED, flush=True)
            return None
    # The governance record is created first so a clash does not leave a new manifest.
    order = sorted(planned, key=lambda item: item[0] != governance)
    for path, blob, text in order:
        if path.exists():
            # Created after the preflight check: identical bytes are fine, anything else is a clash.
            if _bytes_differ(path, blob):
                print(_CHANGED, flush=True)
                return None
            continue
        if path == governance and not write_record:
            continue
        if not _create_exclusive(path, blob, text=text):
            print(_CHANGED, flush=True)
            return None
    return digest


def render_record(manifest: dict, digest: str) -> str:
    """Governance note from manifest counts. No repository names and no personal logins."""
    counts = manifest.get("counts") or {}
    verified = int(counts.get("verdict_verified") or 0)
    no_link = int(counts.get("verdict_no_link") or 0)
    other = int(counts.get("verdict_other_repo") or 0)
    refused = int(counts.get("verdict_not_admitted") or 0)
    admitted = verified + no_link
    reasons = sorted((key.removeprefix("reason_"), value) for key, value in counts.items() if key.startswith("reason_"))
    reason_lines = "\n".join(f"- {name}: {value}" for name, value in reasons) or "- none"
    partition = manifest.get("effective_partition") or ident.CATCHUP_ACTIVATION
    return "\n".join([
        f"# Axis 3 panel catchup, effective partition {partition}",
        "",
        "Status: generated from the expansion manifest. Selection read no dependent counts.",
        "",
        "## Rule",
        "",
        "A registry system outside the current m4 panel contributes a package only when",
        "the root manifest declares the name, deps.dev publishes that name, and the published",
        "metadata does not name another source repository. The root files are package.json,",
        "pyproject.toml, setup.py, Cargo.toml, and go.mod.",
        "",
        "verified and no_link are admitted. other_repo and not_admitted are refused.",
        "A published package with no verdict stops the weekly capture.",
        "",
        "## Counts",
        "",
        f"- Systems outside the previous panel: {counts.get('systems_outside_panel', 0)}",
        f"- Admitted: {admitted} (verified {verified}, no_link {no_link})",
        f"- Refused: {other + refused} (other_repo {other}, not_admitted {refused})",
        f"- Roots unreadable: {counts.get('roots_unreadable', 0)}",
        f"- Private root package.json: {counts.get('private_root_package_json', 0)}",
        "",
        "Refused by reason:",
        "",
        reason_lines,
        "",
        "## What changes, and what does not",
        "",
        f"The manifest applies to deps.dev partitions dated {partition} and later.",
        f"Partitions before {partition} keep the previous m4 panel and the previous mapping hash.",
        "Methodology m5 is unchanged. Stored slices are not recomputed.",
        "The fixed self-name exclusion list is unchanged.",
        "",
        "## Where the audit is",
        "",
        f"Linkage audit: data/quarantine/axis3-deps-v2/linkage-audit-{partition}.json",
        f"Manifest: data/quarantine/axis3-deps-v2/expansion-manifest-{partition}.json",
        f"Manifest sha256: {digest}",
        "",
    ])


def candidates() -> list[tuple[str, str]]:
    panel, _sha = ident.load_panel_m4()
    inside = set(panel)
    return [(eid, repo) for eid, repo in registry_repos() if eid not in inside]


def _incomplete(records: list[dict]) -> list[dict]:
    return [record for record in records
            if record.get("incomplete") or any(row.get("incomplete") for row in record.get("packages") or [])]


def execute(partition: str, out_dir: Path, *, limit: int | None = None, resume: bool = False,
            write_record: bool = False, repos: list[tuple[str, str]] | None = None,
            cache: Path | None = None, token: str | None = None,
            record_file: Path | None = None, taken: set[tuple[str, str]] | None = None) -> int:
    """Scan, write the manifest and the audit, and optionally the governance record.

    A transport failure or a rate limit writes nothing and returns 3. --resume
    continues from the response cache. Returns 2 when the arguments disagree, or
    when a published manifest, checksum, audit, or governance record of this
    partition already has different bytes. Identical bytes are left in place.
    That check also runs without --write-record. --limit writes preview files
    and does not touch the panel paths.
    """
    if partition != ident.CATCHUP_ACTIVATION:
        print(f"[catchup] partition must be {ident.CATCHUP_ACTIVATION}", flush=True)
        return 2
    if write_record and limit:
        print("[catchup] --write-record refuses --limit", flush=True)
        return 2
    if limit is not None and limit < 1:
        print("[catchup] --limit must be at least 1", flush=True)
        return 2
    store = cache or cache_dir()
    if token is None:
        token = _github_token()
    table = alias_map(json.loads((REPO / "data/registry_ids.json").read_text(encoding="utf-8")))
    chosen = list(repos) if repos is not None else candidates()
    if limit is not None:
        chosen = chosen[:limit]
    print(f"[catchup] cache {store} token {'yes' if token else 'no'} resume {resume} "
          f"systems {len(chosen)}", flush=True)
    gh_pace, raw_pace, deps_pace = _Pace(GITHUB_INTERVAL_S), _Pace(RAW_INTERVAL_S), _Pace(DEPSDEV_INTERVAL_S)
    records = []
    # Four workers hide latency. The pacers, not the pool, set the request rate.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_scan_repo, eid, repo, token, table, gh_pace, raw_pace, deps_pace, store, resume)
                   for eid, repo in chosen]
        for done_n, future in enumerate(as_completed(futures), 1):
            records.append(future.result())
            if done_n % 200 == 0:
                print(f"[catchup] scanned {done_n}/{len(chosen)}", flush=True)
    pending = _incomplete(records)
    if pending:
        print(f"[catchup] {len(pending)} systems unread; manifest not written; re-run with --resume", flush=True)
        return 3
    manifest, audit, summary = assemble(records, _taken_names() if taken is None else taken)
    for row in audit["packages"]:
        if row.get("verdict") not in (*ADMITTED_VERDICTS, *EXCLUDED_VERDICTS):
            raise ValueError(f"catchup: {row.get('entity_id')} {row.get('package')} has no audit verdict")
    manifest["systems_viewed"] = len(records)
    manifest["complete"] = limit is None
    digest = write_outputs(
        manifest, audit, Path(out_dir), partition, preview=limit is not None,
        write_record=write_record, record_file=record_file)
    if digest is None:
        return 2
    admitted = summary["counts"].get("verdict_verified", 0) + summary["counts"].get("verdict_no_link", 0)
    print(f"[catchup] admitted {admitted} sha256 {digest}", flush=True)
    print(json.dumps(summary["counts"], sort_keys=True), flush=True)
    if write_record:
        path = _record_path(partition, record_file)
        print(f"[catchup] record {path}", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Value-blind m4 dependents-panel catchup")
    parser.add_argument("--partition", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--write-record", action="store_true")
    args = parser.parse_args(argv)
    if args.partition != ident.CATCHUP_ACTIVATION:
        print(f"[catchup] partition must be {ident.CATCHUP_ACTIVATION}", flush=True)
        return 2
    if args.write_record and args.limit:
        print("[catchup] --write-record refuses --limit", flush=True)
        return 2
    if args.limit is not None and args.limit < 1:
        print("[catchup] --limit must be at least 1", flush=True)
        return 2
    return execute(args.partition, Path(args.out), limit=args.limit, resume=args.resume,
                   write_record=args.write_record)


if __name__ == "__main__":
    raise SystemExit(main())
