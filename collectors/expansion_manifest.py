#!/usr/bin/env python3
"""m3-v2h.1 VALUE-BLIND pin-expansion manifest builder.

Council decision (consilium 2026-07-21, 8 voices): the expanded panel must be
selected by METADATA-ONLY eligibility rules, frozen (content-hashed) BEFORE any
value-bearing query. This script never reads dependents values.

ELIGIBILITY RULE (mechanical, pre-registered in the manifest itself):
A package belongs to a tracked system iff ALL of:
  1. Its manifest is DECLARED IN THE SYSTEM'S OWN REPOSITORY TREE at the HEAD
     commit read at build time (pyproject.toml [project].name / package.json
     non-private "name" / Cargo.toml [package].name / go.mod module path).
     Rationale: deps.dev's project->package linkage includes third-party forks
     and republishes (observed live: hive-vllm, tilearn-infer, fast-langgraph)
     — trusting it would admit Sybil pollution (PREREG §5 gaming vector).
     The repo tree is authored by the system itself; a manifest in the tree is
     the system's own declaration.
  2. The manifest path is outside excluded directories
     (examples|tests?|docs?|benchmarks?|vendor|third_party|scripts|tools|demos?|samples?).
  3. The (system, name) exists on deps.dev (HTTP 200 on the package endpoint)
     — otherwise it cannot appear in the BigQuery Dependents table at all.
  4. Systems limited to what deps.dev's Dependents covers: PYPI, NPM, GO,
     CARGO, MAVEN, NUGET, RUBYGEMS.
Existing 41 pins are carried over verbatim (their linkage evidence stands);
this script only ADDS newly-eligible pins.

Provenance per repo: HEAD commit sha + manifest paths. Output:
data/quarantine/axis3-deps-v2/expansion-manifest-DRAFT.json (+ sha256 printed).
The manifest becomes binding only inside the superseding record.

Uses `gh api` (authenticated reads; read-only) + deps.dev REST (no key).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BUILDER_VERSION = "expansion_manifest_1"
EXCLUDE_RE = re.compile(
    r"(^|/)(examples?|tests?|docs?|benchmarks?|vendor|third_party|scripts|tools|demos?|samples?|\.github)(/|$)",
    re.IGNORECASE)
MANIFEST_FILES = ("pyproject.toml", "package.json", "Cargo.toml", "go.mod")


def gh_json(path: str):
    p = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return None


def raw_file(repo: str, sha: str, path: str) -> str | None:
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return None


def parse_name(fname: str, text: str) -> tuple | None:
    """-> (system, package) or None."""
    if fname == "pyproject.toml":
        in_project = False
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("["):
                in_project = s == "[project]"
            elif in_project:
                m = re.match(r'name\s*=\s*["\']([^"\']+)["\']', s)
                if m:
                    return ("pypi", m.group(1).lower())
        return None
    if fname == "package.json":
        try:
            d = json.loads(text)
        except json.JSONDecodeError:
            return None
        if d.get("private") is True or not d.get("name"):
            return None
        return ("npm", d["name"])
    if fname == "Cargo.toml":
        in_pkg = False
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("["):
                in_pkg = s == "[package]"
            elif in_pkg:
                m = re.match(r'name\s*=\s*["\']([^"\']+)["\']', s)
                if m:
                    return ("cargo", m.group(1))
        return None
    if fname == "go.mod":
        m = re.match(r"module\s+(\S+)", text)
        if m and "/" in m.group(1):
            return ("go", m.group(1))
        return None
    return None


def depsdev_exists(system: str, name: str) -> bool:
    url = f"https://api.deps.dev/v3/systems/{system.upper()}/packages/{urllib.parse.quote(name, safe='')}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def main() -> int:
    id_map = json.loads((REPO / "etl/id_map.json").read_text())
    existing = json.loads((REPO / "data/deps_id_map.json").read_text())["pins"]
    out_repos, all_new = {}, []
    for n, (repo, entity_id) in enumerate(sorted(id_map.items()), 1):
        head = gh_json(f"repos/{repo}/commits/HEAD")
        sha = (head or {}).get("sha")
        if not sha:
            out_repos[repo] = {"entity_id": entity_id, "error": "no HEAD via gh api"}
            continue
        tree = gh_json(f"repos/{repo}/git/trees/{sha}?recursive=1")
        if not tree or "tree" not in tree:
            out_repos[repo] = {"entity_id": entity_id, "head": sha, "error": "no tree"}
            continue
        found = []
        for node in tree["tree"]:
            path = node.get("path", "")
            fname = path.rsplit("/", 1)[-1]
            if fname not in MANIFEST_FILES or EXCLUDE_RE.search(path):
                continue
            text = raw_file(repo, sha, path)
            if text is None:
                continue
            parsed = parse_name(fname, text)
            if parsed:
                found.append({"system": parsed[0], "package": parsed[1],
                              "manifest_path": path})
        # dedup within repo
        seen = set()
        pkgs = []
        for f in found:
            k = (f["system"], f["package"])
            if k not in seen:
                seen.add(k)
                pkgs.append(f)
        out_repos[repo] = {"entity_id": entity_id, "head": sha,
                           "truncated_tree": bool(tree.get("truncated")),
                           "declared_packages": pkgs}
        all_new.extend((repo, p) for p in pkgs)
        print(f"[{n}/{len(id_map)}] {repo}: {len(pkgs)} declared "
              f"({'tree TRUNCATED! ' if tree.get('truncated') else ''}@{sha[:8]})",
              flush=True)
        time.sleep(0.3)

    # deps.dev existence check (metadata-only)
    print("deps.dev existence pass…", flush=True)
    verified = 0
    for _repo, p in all_new:
        p["depsdev_exists"] = depsdev_exists(p["system"], p["package"])
        verified += p["depsdev_exists"]
        time.sleep(0.15)
    print(f"deps.dev existence: {verified}/{len(all_new)} declared packages exist")

    manifest = {
        "v": BUILDER_VERSION,
        "rule": "declared-in-own-repo-tree AND outside excluded dirs AND exists on deps.dev; "
                "third-party project-linkage rejected (Sybil guard); existing 41 pins carried verbatim",
        "excluded_dirs_regex": EXCLUDE_RE.pattern,
        "manifest_files": list(MANIFEST_FILES),
        "value_blind": "no dependents value was read during selection",
        "existing_pins_carried": len(existing),
        "repos": out_repos,
    }
    blob = json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    digest = hashlib.sha256(blob.encode()).hexdigest()
    out = REPO / "data/quarantine/axis3-deps-v2/expansion-manifest-DRAFT.json"
    out.write_text(blob)
    eligible = sum(1 for _, p in all_new if p["depsdev_exists"])
    print(f"[{BUILDER_VERSION}] DRAFT manifest: {len(out_repos)} repos, "
          f"{len(all_new)} declared, {eligible} deps.dev-eligible NEW candidates "
          f"(+{len(existing)} existing pins)")
    print(f"  sha256 {digest}")
    print(f"  -> {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
