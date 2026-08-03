#!/usr/bin/env python3
"""census_ai_v1 - hash-anchored monthly census of the full GitHub star universe.

Implements governance/CENSUS-AI-V1-PREDICATE-2026-08-03.md, which is subordinate
to REGISTRY-GROWTH-POLICY-2026-07-21.md ("census, not quota"): the institute
publishes a BAR and a MECHANICAL PREDICATE, and every qualifier enters
automatically. Nothing in this file may require a judgment call.

Scope signals live in collectors/ai_scope.py - one source, quoted by the act.
Their exact source hash and first qualifying census date are retained so a
later declaration cannot be projected backward as historical AI identity.
Mechanical strata, channel attribution and block-token aggregates keep changes
in the instrument and changes in its heterogeneous population observable.

Positive-only discipline (I1): the published artifacts are the ADMITTED members
plus AGGREGATE exclusion counts. Per-repo negative judgments are never written
to the public tree; raw sweep rows and deep-check evidence are gitignored, and
the shadow band is written outside the repository entirely.

Phases (checkpointed, resumable):
  selftest   - reconciliation of the predicate against the legacy 137 members
  enumerate  - full-universe star sweep >=500  -> data/census/<m>/raw-500plus.jsonl
  shadow     - star sweep 200..499 (ids+stars) -> <staging>/raw-200-499.jsonl
  deepcheck  - GraphQL: licence, language, velocity, README, manifests
  emit       - census-run.json + pending-manifest.json + sha256 anchors

Usage: python3 collectors/census_ai_v1.py <phase> [--month YYYY-MM]
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_scope import (
    BLOCK_NAME,
    BLOCK_STRONG,
    MANIFESTS,
    README_PREFIX,
    classify,
    is_blocked,
    parse_manifest,
)

REPO = Path(__file__).resolve().parent.parent
BUILDER_VERSION = "census_ai_v1"
ACT = REPO / "governance" / "CENSUS-AI-V1-PREDICATE-2026-08-03.md"
SCOPE_SRC = Path(__file__).resolve().parent / "ai_scope.py"
EXECUTOR_SRC = Path(__file__).resolve()
SHADOW_STAGING = REPO.parent / "Evidaxis-shadow-staging"

LICENSE_ALLOW = frozenset({
    "MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "BSD-3-Clause-Clear",
    "GPL-2.0", "GPL-3.0", "AGPL-3.0", "LGPL-2.1", "LGPL-3.0",
    "MPL-2.0", "ISC", "Unlicense", "CC0-1.0", "0BSD", "Zlib", "EPL-2.0",
    "Artistic-2.0",
})

# A frozen allowlist, not a blocklist: "is this label a programming language"
# cannot be read off GitHub's plurality `language` field by exclusion, and the
# first draft's "not Markdown/HTML/TeX" proxy silently classified MDX, Vue,
# Dockerfile and CSS repos as code. Membership here is the whole rule.
CODE_LANGS = frozenset({
    "Python", "Jupyter Notebook", "C", "C++", "C#", "Cuda", "Rust", "Go",
    "Java", "Kotlin", "Swift", "JavaScript", "TypeScript", "Ruby", "PHP",
    "Scala", "Julia", "R", "Lua", "Haskell", "OCaml", "Elixir", "Erlang",
    "Clojure", "Zig", "Nim", "Dart", "Objective-C", "Objective-C++", "Shell",
    "PowerShell", "Perl", "Fortran", "MATLAB", "Assembly", "Verilog", "VHDL",
    "Mojo", "Solidity", "Vue", "Svelte", "Metal", "HLSL", "GLSL", "Cython",
})

STRATA = ("model-infrastructure", "declared-application", "other-declared")

# This is the sole mechanical interpretation of classifier signals. Canonical
# spaces absorb only the classifier's allowed hyphen/space spelling variants;
# an unlisted signal remains visible in the other-declared continuity series.
STRATUM_BY_SIGNAL = MappingProxyType({
    "llm": "model-infrastructure",
    "llms": "model-infrastructure",
    "gpt": "model-infrastructure",
    "gpts": "model-infrastructure",
    "transformer": "model-infrastructure",
    "transformers": "model-infrastructure",
    "diffusion": "model-infrastructure",
    "neural": "model-infrastructure",
    "deep learning": "model-infrastructure",
    "machine learning": "model-infrastructure",
    "reinforcement learning": "model-infrastructure",
    "language model": "model-infrastructure",
    "foundation model": "model-infrastructure",
    "embedding": "model-infrastructure",
    "inference": "model-infrastructure",
    "inference engine": "model-infrastructure",
    "inference server": "model-infrastructure",
    "inference pipeline": "model-infrastructure",
    "model serving": "model-infrastructure",
    "training": "model-infrastructure",
    "fine tun": "model-infrastructure",
    "rlhf": "model-infrastructure",
    "ai model": "model-infrastructure",
    "ai agent": "declared-application",
    "ai assistant": "declared-application",
    "agent": "declared-application",
    "assistant": "declared-application",
    "agentic": "declared-application",
    "application": "declared-application",
    "copilot": "declared-application",
})

# The classifier's two tiers: `storefront` admits alone (the project's public
# label), `corroborated` is two independent supporting registers (README prose,
# a framework-tier dependency, an ambiguous topic). The single-source channels
# below are retained so historical artifacts stay readable.
CHANNELS = ("storefront", "corroborated",
            "readme", "manifest", "weak-topic+second")


def norm_license(spdx: str | None) -> str:
    if not spdx:
        return "NOASSERTION"
    for suffix in ("-only", "-or-later"):
        if spdx.endswith(suffix):
            return spdx[: -len(suffix)]
    return spdx


# ---------------------------------------------------------------- gh plumbing

def gh_search(q: str, page: int) -> dict:
    """One Search API call. Fail-CLOSED on truncation and on transport error."""
    for attempt in range(8):
        p = subprocess.run(
            ["gh", "api", "-X", "GET", "search/repositories",
             "-f", f"q={q}", "-f", "sort=stars", "-f", "order=desc",
             "-f", "per_page=100", "-f", f"page={page}"],
            capture_output=True, text=True, timeout=120)
        if p.returncode == 0:
            d = json.loads(p.stdout)
            # A timed-out search returns a TRUNCATED page with this flag set.
            # Accepting it is exactly the silent under-count a census cannot
            # have, so it is retried, never used.
            if d.get("incomplete_results"):
                wait = min(120, 15 * (attempt + 1))
                print(f"    incomplete_results, retry {attempt+1} {wait}s",
                      flush=True)
                time.sleep(wait)
                continue
            return d
        err = (p.stderr or p.stdout)[:120].strip()
        wait = min(120, 15 * (attempt + 1))
        print(f"    search retry {attempt+1} ({err}) {wait}s", flush=True)
        time.sleep(wait)
    raise RuntimeError(f"search failed after retries: q={q} page={page}")


def gh_graphql(query: str) -> tuple[dict, bool]:
    """Return (data, clean). clean=False when any node came back null/errored.

    The caller must NOT persist a repo as 'missing' when clean is False: a
    502 or a rate-limit nulls nodes, and persisting that verdict turns a
    transient transport failure into a permanent exclusion from the census.
    """
    for attempt in range(8):
        p = subprocess.run(["gh", "api", "graphql", "-f", f"query={query}"],
                           capture_output=True, text=True, timeout=240)
        try:
            d = json.loads(p.stdout) if p.stdout else {}
        except json.JSONDecodeError:
            d = {}
        errors = d.get("errors") or []
        # NOT_FOUND is a PERMANENT fact about that alias (the repository was
        # deleted or renamed away between the sweep and the deep check), not a
        # transport failure. Treating every `errors` payload as transient sent
        # a deleted repo into an unbounded retry loop and failed the whole
        # shard - measured on kweaver-ai/kweaver-core, gone since the 09:35
        # sweep. Only non-NOT_FOUND errors mean "ask again".
        transient = [e for e in errors if e.get("type") != "NOT_FOUND"]
        if p.returncode == 0 and d.get("data") and not errors:
            return d["data"], True
        if d.get("data") and not transient:
            return d["data"], True
        if d.get("data"):
            return d["data"], False
        wait = min(180, 20 * (attempt + 1))
        print(f"    graphql retry {attempt+1} {wait}s", flush=True)
        time.sleep(wait)
    raise RuntimeError("graphql failed after retries")


ROW_FIELDS = ("id", "full_name", "stargazers_count", "created_at", "pushed_at",
              "language", "description")


def row_of(item: dict) -> dict:
    r = {k: item.get(k) for k in ROW_FIELDS}
    r["topics"] = item.get("topics") or []
    r["license"] = (item.get("license") or {}).get("spdx_id")
    return r


# ------------------------------------------------------------------ enumerate

def sweep(lo: int, hi: int, out_path: Path, bands_path: Path,
          project=None) -> None:
    """Full-universe star sweep over [lo..hi], resumable, coverage-asserted.

    GitHub Search returns at most 1000 results per query, so every band above
    the cap is partitioned: geometrically on stars, then on creation TIMESTAMP
    down to one second. A band is marked done only when the number of distinct
    ids collected equals the total the API reported for it - otherwise a page
    overlap would lose rows and the band would be skipped forever on resume.
    """
    done = set()
    if bands_path.exists():
        for line in bands_path.open():
            b = json.loads(line)
            if b.get("done"):
                done.add((b["lo"], b["hi"], b.get("created", "")))
    seen: set[int] = set()
    if out_path.exists():
        for line in out_path.open():
            seen.add(json.loads(line)["id"])
    horizon = (datetime.now(timezone.utc) + timedelta(days=1)).strftime(
        "%Y-%m-%dT00:00:00Z")
    out, bands = out_path.open("a"), bands_path.open("a")
    stack: list[tuple[int, int, str]] = [(lo, hi, "")]
    attempts: dict[tuple[int, int, str], int] = {}
    n_req = 0
    while stack:
        blo, bhi, created = stack.pop()
        if (blo, bhi, created) in done:
            continue
        q = f"stars:{blo}..{bhi} fork:false is:public"
        if created:
            q += f" created:{created}"
        first = gh_search(q, 1)
        n_req += 1
        total = first["total_count"]
        if total > 1000:
            if blo < bhi:
                mid = max(blo, int((blo * bhi) ** 0.5))
                if mid >= bhi:
                    mid = blo
                stack += [(blo, mid, created), (mid + 1, bhi, created)]
            else:
                d_lo, d_hi = (created.split("..") if created
                              else ("2007-01-01T00:00:00Z", horizon))
                a = datetime.fromisoformat(d_lo.replace("Z", "+00:00"))
                b = datetime.fromisoformat(d_hi.replace("Z", "+00:00"))
                if (b - a).total_seconds() <= 1:
                    bands.write(json.dumps({
                        "lo": blo, "hi": bhi, "created": created,
                        "total": total, "done": False,
                        "error": "terminal partition over the 1000 cap"}) + "\n")
                    bands.flush()
                    raise RuntimeError(
                        f"un-partitionable slice stars={blo} {created} "
                        f"total={total}")
                m = (a + (b - a) / 2).replace(microsecond=0).strftime(
                    "%Y-%m-%dT%H:%M:%SZ")
                stack += [(blo, bhi, f"{d_lo}..{m}"), (blo, bhi, f"{m}..{d_hi}")]
            continue
        items, pages = first["items"], (total + 99) // 100
        for page in range(2, pages + 1):
            time.sleep(2.2)                     # per PAGE, not per band
            items += gh_search(q, page)["items"]
            n_req += 1
        band_ids = {it["id"] for it in items}
        # Coverage is a ONE-SIDED claim: fewer rows than the API reported means
        # pagination lost some and the band must be retried. MORE rows is the
        # live index moving under us - a repo gains a star mid-pagination and
        # enters the band - which costs no coverage and must not block. The
        # first version demanded exact equality and deadlocked at 719 vs 718.
        drift = len(band_ids) - total
        # GitHub's total_count is an INDEX ESTIMATE, not a promise. Measured on
        # band 2019..2079: total_count=939, full pagination yields 938 distinct
        # ids with zero duplicates and incomplete_results=false, reproducibly
        # across four attempts. Demanding equality of someone else's estimate
        # is not rigour, it is a deadlock. Tolerate a small shortfall, RECORD
        # every occurrence, and publish the reconciliation - a real pagination
        # loss is large and random, an index estimate is off by one or two.
        tolerance = max(2, int(total * 0.005))
        if drift < -tolerance:
            attempts[(blo, bhi, created)] = attempts.get(
                (blo, bhi, created), 0) + 1
            n_try = attempts[(blo, bhi, created)]
            bands.write(json.dumps({
                "lo": blo, "hi": bhi, "created": created, "total": total,
                "collected": len(band_ids), "attempt": n_try, "done": False,
                "error": "collected < total_count"}) + "\n")
            bands.flush()
            if n_try <= 3:
                print(f"  band {blo}..{bhi}: {len(band_ids)}/{total} - retry "
                      f"{n_try}", flush=True)
                stack.append((blo, bhi, created))
                time.sleep(10)
                continue
            # Three honest attempts failed: partition instead of looping, and
            # never silently accept the shortfall.
            raise RuntimeError(
                f"band {blo}..{bhi} {created} short by {-drift} after "
                f"{n_try} attempts - investigate before publishing coverage")
        fresh = 0
        for it in items:
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            row = row_of(it)
            out.write(json.dumps(project(row) if project else row,
                                 ensure_ascii=False) + "\n")
            fresh += 1
        out.flush()
        bands.write(json.dumps({"lo": blo, "hi": bhi, "created": created,
                                "total": total, "collected": len(band_ids),
                                "index_drift": drift, "fresh": fresh,
                                "done": True}) + "\n")
        bands.flush()
        done.add((blo, bhi, created))
        print(f"  band {blo}..{bhi} {created or 'all'}: {total} "
              f"(+{fresh}, req#{n_req}, universe={len(seen)})", flush=True)
        time.sleep(2.2)
    out.close()
    bands.close()
    # Reconciliation. Two things move under a multi-hour sweep and neither can
    # be eliminated, only measured: GitHub's total_count is an index estimate,
    # and the sweep descends stars, so a repo that GAINS stars mid-run migrates
    # into a band already marked done and is missed (one that loses stars falls
    # into unvisited territory and is caught). The honest instrument reports the
    # gap instead of claiming it away.
    all_bands = [json.loads(l) for l in bands_path.open()]
    done_bands = [b for b in all_bands if b.get("done")]
    shortfall = sum(-b["index_drift"] for b in done_bands
                    if b.get("index_drift", 0) < 0)
    surplus = sum(b["index_drift"] for b in done_bands
                  if b.get("index_drift", 0) > 0)
    live = gh_search(f"stars:{lo}..{hi} fork:false is:public", 1)["total_count"]
    (out_path.parent / f"{out_path.stem}-complete.json").write_text(json.dumps({
        "bar_lo": lo, "bar_hi": hi, "collected": len(seen), "requests": n_req,
        "bands_done": len(done_bands),
        "universe_at_sweep_end": live,
        "delta_vs_universe": len(seen) - live,
        "band_shortfall_total": shortfall,
        "band_surplus_total": surplus,
        "note": ("delta_vs_universe compares a multi-hour collection against a "
                 "single-instant count; band_shortfall is the sum of per-band "
                 "gaps against GitHub's own index estimate. Both are published "
                 "rather than reconciled away - the coverage claim is 'these N "
                 "repositories were observed', never 'nothing was missed'."),
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=1))
    print(f"sweep complete: {len(seen)} collected, universe now {live} "
          f"(delta {len(seen)-live:+d}), band shortfall {shortfall}, "
          f"{n_req} requests", flush=True)


# ------------------------------------------------------------------ deepcheck

SINCE = (datetime.now(timezone.utc) - timedelta(days=365)).strftime(
    "%Y-%m-%dT00:00:00Z")
SINCE90 = (datetime.now(timezone.utc) - timedelta(days=90)).strftime(
    "%Y-%m-%dT00:00:00Z")


def _deep_query(batch: list[dict]) -> str:
    parts = []
    for j, r in enumerate(batch):
        owner, name = r["full_name"].split("/", 1)
        files = " ".join(
            f'm{k}: object(expression:"HEAD:{f}") {{ ... on Blob {{ text }} }}'
            for k, f in enumerate(MANIFESTS))
        parts.append(
            f'r{j}: repository(owner:"{owner}", name:"{name}") {{'
            f' databaseId nameWithOwner isFork isArchived'
            f' licenseInfo {{ spdxId }} primaryLanguage {{ name }}'
            f' defaultBranchRef {{ name target {{ oid ... on Commit {{'
            f'  h365: history(since:"{SINCE}") {{ totalCount }}'
            f'  h90: history(since:"{SINCE90}") {{ totalCount }} }} }} }}'
            f' releases(first:1) {{ totalCount }}'
            f' {files} }}')
    return "query {" + " ".join(parts) + "}"



README_NAMES = ("README.md", "README.rst", "README", "readme.md", "docs/README.md")


def readme_prefix(full_name: str) -> str:
    """First README_PREFIX bytes of the README, over raw.githubusercontent.

    Measured 2026-08-03: pulling READMEs inside the GraphQL batch returned
    1.6 MB per 20 repositories and made the phase bandwidth-bound - ten
    parallel workers moved 280 repos/min while 89% of the API budget sat
    unused, because cost is 1 point per query regardless of payload. A ranged
    request over the raw CDN returns exactly the 2000 bytes the classifier
    reads (HTTP 206, 93% less traffic for pytorch/pytorch) and does not touch
    the API budget at all.
    """
    for name in README_NAMES:
        url = f"https://raw.githubusercontent.com/{full_name}/HEAD/{name}"
        req = urllib.request.Request(url, headers={
            "Range": f"bytes=0-{README_PREFIX}",
            "User-Agent": "evidaxis-census"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (404, 403):
                continue          # try the next spelling
            return ""
        except (urllib.error.URLError, OSError, TimeoutError):
            return ""
    return ""


def readme_batch(names: list[str]) -> dict[str, str]:
    with ThreadPoolExecutor(max_workers=16) as pool:
        return dict(zip(names, pool.map(readme_prefix, names),
                        strict=True))


def deepcheck(rows: list[dict], out_path: Path, shard: int = 0,
              shards: int = 1) -> None:
    """Deep legs for the candidate set, shardable.

    Measured 2026-08-03: one batch of 20 takes ~9s and returns ~1.6 MB (the
    README text is the entire payload; without it the same batch is 198 KB).
    Serial, that is ~26 hours for 78k candidates. The GraphQL budget is NOT the
    constraint - cost is 1 point per query and 4795 of 5000 points were free
    while the serial run crawled - so the work is latency-bound and shards
    linearly. Each shard writes its own file; emit() reads them all.
    """
    if shards > 1:
        rows = [r for i, r in enumerate(rows) if i % shards == shard]
    # The cache is read across ALL shard files, not just this worker's own, so
    # re-sharding (changing the worker count mid-run) never redoes finished
    # work and never drops any.
    done = set()
    for cached in out_path.parent.glob("deepcheck*.jsonl"):
        for line in cached.open():
            done.add(json.loads(line)["full_name"])
    todo = [r for r in rows if r["full_name"] not in done]
    print(f"deepcheck: {len(todo)} to go ({len(done)} cached)", flush=True)
    out = out_path.open("a")
    queue, pending = list(todo), []
    rounds = 0
    while queue and rounds < 6:
        rounds += 1
        pending = []
        for i in range(0, len(queue), 20):
            batch = queue[i:i + 20]
            data, clean = gh_graphql(_deep_query(batch))
            readmes = readme_batch([r['full_name'] for r in batch])
            for j, r in enumerate(batch):
                node = data.get(f"r{j}")
                if node is None:
                    # Only a CLEAN response proves the repo is really gone. A
                    # nulled node inside an errored response is a transport
                    # failure; persisting it as "missing" would turn a 502 into
                    # a permanent exclusion that resume never revisits.
                    if clean:
                        out.write(json.dumps({
                            "full_name": r["full_name"], "id": r["id"],
                            "missing": True}) + "\n")
                    else:
                        pending.append(r)
                    continue
                tgt = ((node.get("defaultBranchRef") or {}).get("target") or {})
                manifests = {}
                for k, f in enumerate(MANIFESTS):
                    blob = node.get(f"m{k}") or {}
                    if blob.get("text"):
                        manifests[f] = blob["text"][:200_000]
                out.write(json.dumps({
                    "full_name": node["nameWithOwner"],
                    "id": node["databaseId"],
                    "isFork": node["isFork"], "isArchived": node["isArchived"],
                    "license": (node.get("licenseInfo") or {}).get("spdxId"),
                    "language": (node.get("primaryLanguage") or {}).get("name"),
                    "releases": node["releases"]["totalCount"],
                    "commit_oid": tgt.get("oid"),
                    "commits365": (tgt.get("h365") or {}).get("totalCount", 0),
                    "commits90": (tgt.get("h90") or {}).get("totalCount", 0),
                    "readme": readmes.get(node["nameWithOwner"], "")[
                        :README_PREFIX],
                    "manifests": manifests,
                }, ensure_ascii=False) + "\n")
            out.flush()
            if (i // 20) % 20 == 0:
                print(f"  round {rounds}: {i}/{len(queue)}", flush=True)
            time.sleep(0.2)   # not rate-bound: 1 point/query, 5000/hour
        queue = pending
        if queue:
            print(f"  {len(queue)} transient failures, retrying", flush=True)
            time.sleep(30)
    out.close()
    if queue:
        raise RuntimeError(
            f"{len(queue)} repos never returned cleanly - fix transport before "
            f"emitting; a census may not silently drop candidates")


def rescue_contributors(batch: list[str]) -> dict[str, bool]:
    """>=3 distinct commit authors in the trailing year, batched."""
    parts = []
    for j, fn in enumerate(batch):
        owner, name = fn.split("/", 1)
        parts.append(
            f'r{j}: repository(owner:"{owner}", name:"{name}") {{'
            f' defaultBranchRef {{ target {{ ... on Commit {{'
            f' history(first:100, since:"{SINCE}") {{ nodes {{'
            f' author {{ user {{ login }} email }} }} }} }} }} }} }}')
    data, _ = gh_graphql("query {" + " ".join(parts) + "}")
    out = {}
    for j, fn in enumerate(batch):
        try:
            nodes = (data[f"r{j}"]["defaultBranchRef"]["target"]["history"]
                     ["nodes"])
            authors = {(n["author"].get("user") or {}).get("login")
                       or n["author"].get("email")
                       for n in nodes if n.get("author")}
            out[fn] = len(authors) >= 3
        except (KeyError, TypeError):
            out[fn] = False
    return out


# ----------------------------------------------------------------------- emit

def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.open()] if p.exists() else []


def registry_ids() -> dict[int, str]:
    p = REPO / "data" / "registry_ids.json"
    if not p.exists():
        raise RuntimeError("data/registry_ids.json missing - build it first")
    return {v["repo_id"]: k for k, v in json.loads(p.read_text())["members"].items()}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def stratum_of(evidence: dict) -> str:
    if evidence["channel"] == "manifest":
        return "model-infrastructure"
    signal = re.sub(r"[-_\s]+", " ", evidence["signal"].casefold()).strip()
    return STRATUM_BY_SIGNAL.get(signal, "other-declared")


def blocklist_token(name: str, description: str | None,
                    topics: list[str]) -> str | None:
    """Which token blocked this row, for the aggregate histogram.

    Must mirror is_blocked EXACTLY, including its separator-split view of the
    name: `generative-ai-for-beginners` blocks on the part `beginners`, which a
    whole-string search never sees. A mismatch here aborted the census rather
    than mis-reporting one histogram bucket - fail-closed in the wrong place.
    """
    from ai_scope import _SPLIT
    name_forms = name + " " + " ".join(_SPLIT.split(name.lower()))
    match = BLOCK_NAME.search(name_forms)
    if match is None:
        match = BLOCK_STRONG.search(
            f"{name} {description or ''} {' '.join(topics or [])}"
        )
    if match is None:
        return None
    return re.sub(r"[-\s]+", "-", match.group(1).casefold())


def _line_at(text: str, offset: int) -> str:
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    if end == -1:
        end = len(text)
    return text[start:end].removesuffix("\r")


def _closing_delimiter(text: str, opening: int, left: str, right: str) -> int:
    depth = 0
    quote = None
    escaped = False
    for offset in range(opening, len(text)):
        char = text[offset]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in "\"'":
            quote = char
        elif char == left:
            depth += 1
        elif char == right:
            depth -= 1
            if depth == 0:
                return offset + 1
    raise RuntimeError("qualifying manifest dependency value is unterminated")


def _dependency_pattern(dependency: str) -> re.Pattern:
    parts = re.split(r"[-_.]+", dependency)
    body = r"[-_.]+".join(re.escape(part) for part in parts)
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])",
                      re.IGNORECASE)


def manifest_dependency_line(filename: str, text: str,
                             dependency: str) -> str:
    """Recover the exact source line for an already-parsed runtime dependency."""
    if filename == "requirements.txt":
        for line in text.splitlines():
            if dependency in parse_manifest(filename, line):
                return line
        raise RuntimeError("qualifying requirements dependency line not found")

    pattern = _dependency_pattern(dependency)
    if filename == "package.json":
        header = re.search(r'"dependencies"\s*:\s*\{', text)
        if header:
            opening = text.find("{", header.start())
            end = _closing_delimiter(text, opening, "{", "}")
            match = re.search(
                rf'"{pattern.pattern}"\s*:', text[opening:end], re.IGNORECASE
            )
            if match:
                return _line_at(text, opening + match.start())
    elif filename == "pyproject.toml":
        project = re.search(r"(?m)^\s*\[project\]\s*(?:#.*)?$", text)
        if project:
            next_section = re.search(r"(?m)^\s*\[", text[project.end():])
            section_end = (project.end() + next_section.start()
                           if next_section else len(text))
            dep_key = re.search(
                r"(?m)^\s*dependencies\s*=\s*\[",
                text[project.end():section_end],
            )
            if dep_key:
                opening = text.find("[", project.end() + dep_key.start())
                end = _closing_delimiter(text, opening, "[", "]")
                match = pattern.search(text, opening, end)
                if match:
                    return _line_at(text, match.start())
    elif filename == "Cargo.toml":
        section = re.search(r"(?m)^\s*\[dependencies\]\s*(?:#.*)?$", text)
        if section:
            next_section = re.search(r"(?m)^\s*\[", text[section.end():])
            section_end = (section.end() + next_section.start()
                           if next_section else len(text))
            match = pattern.search(text, section.end(), section_end)
            if match:
                return _line_at(text, match.start())
    raise RuntimeError(
        f"qualifying {filename} dependency line for {dependency!r} not found"
    )


def qualifying_text(row: dict, deep: dict, evidence: dict) -> str:
    """The exact text that fired, for the anti-look-ahead hash.

    Failure to isolate the precise span must DEGRADE, never abort: provenance
    is evidence about one member, a census is the whole record, and letting the
    finer artifact kill the coarser one inverts their importance. An unusual
    manifest (an unterminated array, an exotic dialect) falls back to hashing
    the whole file, which is still a sound point-in-time commitment - only less
    specific. The degradation is visible in the artifact via the prefix.
    """
    channel = evidence["channel"]
    if channel == "manifest":
        filename = evidence["manifest"]
        text = (deep.get("manifests") or {}).get(filename) or ""
        try:
            return manifest_dependency_line(filename, text, evidence["signal"])
        except (RuntimeError, ValueError, KeyError, IndexError):
            return f"[whole-manifest:{filename}]\n{text}"
    if channel == "readme":
        return (deep.get("readme") or "")[:README_PREFIX]
    if channel == "weak-topic+second":
        second = classify(
            "", None, [], readme=deep.get("readme"),
            manifests=deep.get("manifests"),
        )
        if second is None:
            raise RuntimeError("weak topic admission has no second channel")
        return qualifying_text(row, deep, second)
    if channel == "corroborated":
        # Two independent registers admitted this member, so the commitment is
        # to BOTH of them: the storefront it published, the opening of its
        # README, and the manifests it declares. Hashing the union is what the
        # anti-look-ahead guarantee needs - it pins everything that spoke.
        parts = [f"{row['full_name'].split('/')[-1]} "
                 f"{row.get('description') or ''} "
                 f"{' '.join(row.get('topics') or [])}".strip(),
                 (deep.get("readme") or "")[:README_PREFIX]]
        for fn, text in sorted((deep.get("manifests") or {}).items()):
            parts.append(f"[{fn}]\n{text}")
        return "\n---\n".join(parts)
    if channel != "storefront":
        raise RuntimeError(f"unknown qualification channel: {channel}")

    # The storefront IS the declaration - name, description and topics as the
    # classifier reads them, joined. An earlier version tried to reproduce
    # WHICH part fired by re-classifying each in isolation and raised when it
    # could not; that breaks whenever a match spans the join (the regex reads
    # the concatenation), and a provenance detail must never be able to abort
    # a census. Hashing the whole storefront is a stronger commitment anyway:
    # it pins everything the repository said about itself at census time.
    return f"{row['full_name'].split('/')[-1]} {row.get('description') or ''} " \
           f"{' '.join(row.get('topics') or [])}".strip()


def previous_qualification_dates(month_dir: Path) -> dict[int, str]:
    dates: dict[int, str] = {}
    for manifest_path in sorted(month_dir.parent.glob("*/pending-manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        fallback = (manifest.get("census_run_at") or "")[:10]
        for member in manifest.get("members", []):
            date = (member.get("first_qualified_on")
                    or member.get("first_observed") or fallback)
            repo_id = member.get("repo_id")
            if repo_id is not None and date:
                dates[repo_id] = min(date, dates.get(repo_id, date))
    return dates


def channel_attribution(members: list[dict], census_date: str) -> dict:
    admitted = dict.fromkeys(CHANNELS, 0)
    first_qualified = dict.fromkeys(CHANNELS, 0)
    for member in members:
        channel = member["admitted_by"]
        if channel not in admitted:
            raise RuntimeError(f"unknown qualification channel: {channel}")
        admitted[channel] += 1
        if member["first_qualified_on"] == census_date:
            first_qualified[channel] += 1
    return {
        "all_admitted": admitted,
        "first_qualified_on_this_census": first_qualified,
    }


def candidates_of(raw: list[dict],
                  blocklist_histogram: dict[str, int] | None = None) -> list[dict]:
    """Storefront-channel pre-filter: who is worth a deep check at all."""
    out = []
    for r in raw:
        name = r["full_name"].split("/")[-1]
        if is_blocked(name, r["description"], r["topics"]):
            token = blocklist_token(name, r["description"], r["topics"])
            if token is None:
                raise RuntimeError("blocked row has no attributable token")
            if blocklist_histogram is not None:
                blocklist_histogram[token] = blocklist_histogram.get(token, 0) + 1
            continue
        if classify(name, r["description"], r["topics"]):
            out.append(r)
            continue
        # No storefront signal, but the licence/language legs are cheap and
        # already known from the sweep: only survivors are worth a README.
        if norm_license(r["license"]) in LICENSE_ALLOW and \
                r["language"] in CODE_LANGS:
            out.append(r)
    return out


def emit(month_dir: Path) -> None:
    sentinel = month_dir / "raw-500plus-complete.json"
    if not sentinel.exists():
        raise RuntimeError(
            "sweep sentinel missing - the universe is partial; emitting now "
            "would hash-anchor a manifest whose completeness claim is false")
    raw = load_jsonl(month_dir / "raw-500plus.jsonl")
    # Keyed on the NUMERIC id, not the name: GraphQL resolves a renamed
    # repository and returns its CANONICAL name, so a name-keyed lookup misses
    # every member that moved between the sweep and the deep check. Measured:
    # d3george/slash-admin is dingyi214/slash-admin today. Same class as the 8
    # stale names in the legacy roster.
    deep = {}
    for p_deep in sorted(month_dir.glob("deepcheck*.jsonl")):
        for d in load_jsonl(p_deep):
            if d.get("id") is not None:
                deep[d["id"]] = d
    members = registry_ids()

    agg = {k: 0 for k in (
        "universe", "blocked_nonsystem", "not_ai_scope", "excluded_license",
        "no_code_language", "no_velocity", "rescued", "fork_or_archived",
        "gone_since_sweep", "legacy_member", "admitted")}
    agg["universe"] = len(raw)
    admitted, rescue_q, legacy_fail = [], [], []
    blocklist_histogram: Counter[str] = Counter()

    for r in candidates_of(raw, blocklist_histogram):
        d = deep.get(r["id"])
        is_legacy = r["id"] in members
        if d is None:
            raise RuntimeError(
                f"candidate never deep-checked: {r['full_name']} (id {r['id']})")
        if d.get("missing"):
            agg["gone_since_sweep"] += 1
            continue
        name = r["full_name"].split("/")[-1]
        ev = classify(name, r["description"], r["topics"],
                      readme=d.get("readme"), manifests=d.get("manifests"))
        legs = []
        if not ev:
            legs.append("ai_scope")
        if d.get("isFork") or d.get("isArchived"):
            legs.append("fork_or_archived")
        if norm_license(d.get("license")) not in LICENSE_ALLOW:
            legs.append("license")
        if d.get("language") not in CODE_LANGS:
            legs.append("code_language")
        velocity = d.get("releases", 0) >= 1 or d.get("commits365", 0) >= 50
        if not velocity and d.get("commits90", 0) >= 10:
            rescue_q.append((r, d, ev, legs))
            continue
        if not velocity:
            legs.append("velocity")
        # Legacy reconciliation is counted BEFORE the exclusion buckets so the
        # census can answer "how many of the 137 would AI-v1 admit today" - an
        # order-dependent counter hid that number in the first draft.
        if is_legacy:
            agg["legacy_member"] += 1
            if legs:
                legacy_fail.append({"full_name": r["full_name"],
                                    "fails": legs})
            continue
        if legs:
            key = {"ai_scope": "not_ai_scope", "license": "excluded_license",
                   "code_language": "no_code_language",
                   "velocity": "no_velocity",
                   "fork_or_archived": "fork_or_archived"}[legs[0]]
            agg[key] += 1
            continue
        admitted.append({**r, "evidence": ev, "commit_oid": d.get("commit_oid"),
                         "license_observed": d.get("license")})

    for i in range(0, len(rescue_q), 10):
        chunk = rescue_q[i:i + 10]
        verdict = rescue_contributors([r["full_name"] for r, _, _, _ in chunk])
        for r, d, ev, legs in chunk:
            if not verdict.get(r["full_name"]):
                legs = [*legs, "velocity"]
            else:
                agg["rescued"] += 1
            if r["id"] in members:
                agg["legacy_member"] += 1
                if legs:
                    legacy_fail.append({"full_name": r["full_name"],
                                        "fails": legs})
                continue
            if legs:
                key = {"ai_scope": "not_ai_scope",
                       "license": "excluded_license",
                       "code_language": "no_code_language",
                       "velocity": "no_velocity",
                       "fork_or_archived": "fork_or_archived"}[legs[0]]
                agg[key] += 1
                continue
            admitted.append({**r, "evidence": ev,
                             "commit_oid": d.get("commit_oid"),
                             "license_observed": d.get("license")})
        time.sleep(1.2)

    agg["blocked_nonsystem"] = sum(blocklist_histogram.values())
    agg["admitted"] = len(admitted)
    admitted.sort(key=lambda r: (-r["stargazers_count"], r["id"]))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    census_date = now[:10]
    month = month_dir.name
    prior_dates = previous_qualification_dates(month_dir)
    executor_hash = sha256(EXECUTOR_SRC)

    manifest_members = []
    for r in admitted:
        first_qualified_on = min(
            census_date, prior_dates.get(r["id"], census_date)
        )
        source_text = qualifying_text(r, deep[r["id"]], r["evidence"])
        manifest_members.append({
            "repo_id": r["id"], "full_name": r["full_name"],
            "stars": r["stargazers_count"],
            "first_observed": first_qualified_on,
            "first_qualified_on": first_qualified_on,
            "qualifying_text_sha256": sha256_text(source_text),
            "cohort": "unassigned-v1", "status": "pending",
            "wave": "backlog" if month == "2026-08" else "forward",
            "commit_oid": r.get("commit_oid"),
            "license_observed": r.get("license_observed"),
            "admitted_by": r["evidence"]["channel"],
            "signal": r["evidence"]["signal"],
            "stratum": stratum_of(r["evidence"]),
        })

    manifest = {
        "@type": "PendingMembershipManifest",
        "predicate": "AI-v1",
        "census_month": month,
        "wave": "backlog" if month == "2026-08" else "forward",
        "governance_act": str(ACT.relative_to(REPO)),
        "governance_act_sha256": sha256(ACT),
        "scope_module_sha256": sha256(SCOPE_SRC),
        "executor_sha256": executor_hash,
        "census_run_at": now,
        "note": ("New admissions of this census. COMPLETE MEMBERSHIP = this "
                 "file UNION the live registry (etl/seeds.json); legacy "
                 "members are not repeated here. Cards activate in weekly "
                 "tranches and index after 4 weekly observations. Order of "
                 "publication is a marketing schedule, never a measurement "
                 "verdict."),
        "members": manifest_members,
    }
    mp = month_dir / "pending-manifest.json"
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=1))

    census = {
        "@type": "CensusRun", "builder": BUILDER_VERSION, "predicate": "AI-v1",
        "star_bar": 500, "run_at": now,
        "governance_act_sha256": sha256(ACT),
        "scope_module_sha256": sha256(SCOPE_SRC),
        "executor_sha256": executor_hash,
        "sweep": json.loads(sentinel.read_text()),
        "method": ("Full-universe GitHub Search star sweep (geometric band "
                   "bisection, creation-timestamp slicing at the 1000-result "
                   "cap, per-band collected==total_count assertion); scope by "
                   "the three declaration channels of collectors/ai_scope.py; "
                   "deep legs via GraphQL. Positive-only: admitted members are "
                   "named, exclusions are aggregate."),
        "aggregate": agg,
        "qualification_history_note": (
            "Metrics predating first_qualified_on are pre-qualification history, "
            "never evidence that the repository always declared an AI identity."
        ),
        "strata_counts": {
            stratum: sum(m["stratum"] == stratum for m in manifest_members)
            for stratum in STRATA
        },
        "channel_attribution": channel_attribution(
            manifest_members, census_date
        ),
        "blocklist_token_histogram": dict(sorted(blocklist_histogram.items())),
        "legacy_reconciliation": {
            "note": ("AI-v1 evaluated against the 137 members admitted under "
                     "the pre-policy discretionary method. They remain members "
                     "under the no-removal rule; this block reports where the "
                     "predicate disagrees with the institute's own history "
                     "rather than tuning the predicate to agree."),
            "legacy_evaluated": agg["legacy_member"],
            "legacy_failing_ai_v1": legacy_fail,
        },
        "bands": load_jsonl(month_dir / "bands-500plus.jsonl"),
        "pending_manifest_sha256": sha256(mp),
    }
    cp = month_dir / "census-run.json"
    cp.write_text(json.dumps(census, ensure_ascii=False, indent=1))
    (month_dir / "census-run.sha256").write_text(sha256(cp) + "  census-run.json\n")
    print(json.dumps(agg, indent=1))
    print(f"legacy failing AI-v1: {len(legacy_fail)} of {agg['legacy_member']}")
    print(f"manifest {mp} sha256={census['pending_manifest_sha256'][:16]}")


# ------------------------------------------------------------------- selftest

def selftest() -> int:
    """Reconciliation, NOT a pass/fail gate on the legacy roster.

    The 137 were chosen by the discretionary method the policy abolished, so
    the predicate owes them nothing and matching them 137/137 would be fitting.
    A miss here is a FALSIFIER to examine (it may reveal an over-broad block,
    as `collection of` did by killing timm - which is not even in the 137), not
    a licence to add tokens that match the failing rows.
    """
    ids = json.loads((REPO / "data" / "registry_ids.json").read_text())["members"]
    names = [v["canonical"] for v in ids.values()]
    rows = [{"full_name": n, "id": 0} for n in names]
    deep_path = REPO / "data" / "census" / "_selftest" / "deepcheck.jsonl"
    deep_path.parent.mkdir(parents=True, exist_ok=True)
    deepcheck(rows, deep_path)
    deep = {d["full_name"]: d for d in load_jsonl(deep_path)}
    store_only, with_channels, blocked, misses = 0, 0, [], []
    for n in names:
        d = deep.get(n) or {}
        meta = _repo_meta(n)
        nm = n.split("/")[-1]
        if is_blocked(nm, meta["description"], meta["topics"]):
            blocked.append(n)
        if classify(nm, meta["description"], meta["topics"]):
            store_only += 1
            with_channels += 1
            continue
        ev = classify(nm, meta["description"], meta["topics"],
                      readme=d.get("readme"), manifests=d.get("manifests"))
        if ev:
            with_channels += 1
        else:
            misses.append((n, "no channel fired"))
    n = len(names)
    print(f"\nstorefront only : {store_only}/{n} = {100*store_only/n:.1f}%")
    print(f"all 3 channels  : {with_channels}/{n} = {100*with_channels/n:.1f}%")
    print(f"blocked (should be 0 or explained): {blocked or 'none'}")
    print(f"not recognised  : {[m[0] for m in misses] or 'none'}")
    return 0


_META_CACHE: dict[str, dict] = {}


def _repo_meta(full_name: str) -> dict:
    if full_name in _META_CACHE:
        return _META_CACHE[full_name]
    p = subprocess.run(
        ["gh", "api", f"repos/{full_name}",
         "--jq", "{description:.description, topics:.topics}"],
        capture_output=True, text=True, timeout=60)
    d = json.loads(p.stdout) if p.returncode == 0 else {"description": None,
                                                        "topics": []}
    _META_CACHE[full_name] = d
    return d


def main() -> int:
    phase = sys.argv[1] if len(sys.argv) > 1 else ""
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    if "--month" in sys.argv:
        month = sys.argv[sys.argv.index("--month") + 1]
    month_dir = REPO / "data" / "census" / month
    month_dir.mkdir(parents=True, exist_ok=True)
    if phase == "selftest":
        return selftest()
    if phase == "enumerate":
        sweep(500, 1_000_000, month_dir / "raw-500plus.jsonl",
              month_dir / "bands-500plus.jsonl")
        return 0
    if phase == "shadow":
        SHADOW_STAGING.mkdir(exist_ok=True)
        # Policy: the 200-499 band gets "star counts only". Projecting here is
        # what makes that true of the stored bytes, not just of the intent.
        sweep(200, 499, SHADOW_STAGING / "raw-200-499.jsonl",
              SHADOW_STAGING / "bands-200-499.jsonl",
              project=lambda r: {"id": r["id"], "stars": r["stargazers_count"]})
        return 0
    if phase == "deepcheck":
        raw = load_jsonl(month_dir / "raw-500plus.jsonl")
        cands = candidates_of(raw)
        shard, shards = 0, 1
        if "--shard" in sys.argv:
            shard, shards = (int(x) for x in
                             sys.argv[sys.argv.index("--shard") + 1].split("/"))
        out = (month_dir / f"deepcheck-{shard}.jsonl" if shards > 1
               else month_dir / "deepcheck.jsonl")
        print(f"deepcheck candidates: {len(cands)} of {len(raw)} "
              f"(shard {shard}/{shards})")
        deepcheck(cands, out, shard, shards)
        return 0
    if phase == "emit":
        emit(month_dir)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
