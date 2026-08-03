#!/usr/bin/env python3
"""census_ai_v1 - hash-anchored monthly census of the full GitHub star universe.

Implements governance/CENSUS-AI-V1-PREDICATE-2026-08-03.md, which is subordinate
to REGISTRY-GROWTH-POLICY-2026-07-21.md ("census, not quota"): the institute
publishes a BAR and a MECHANICAL PREDICATE, and every qualifier enters
automatically. Nothing in this file may require a judgment call.

Scope signals live in collectors/ai_scope.py - one source, quoted by the act.

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
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_scope import (FRAMEWORK_DEPS, MANIFESTS, README_PREFIX,  # noqa: E402
                      classify, is_blocked)

REPO = Path(__file__).resolve().parent.parent
BUILDER_VERSION = "census_ai_v1"
ACT = REPO / "governance" / "CENSUS-AI-V1-PREDICATE-2026-08-03.md"
SCOPE_SRC = Path(__file__).resolve().parent / "ai_scope.py"
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
        if p.returncode == 0 and d.get("data") and not d.get("errors"):
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
        if drift < 0:
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
    # The sentinel is what lets emit() know the universe is whole. Without it,
    # emit() would happily hash a manifest built from a partial sweep and label
    # it complete.
    (out_path.parent / f"{out_path.stem}-complete.json").write_text(json.dumps({
        "bar_lo": lo, "bar_hi": hi, "universe": len(seen), "requests": n_req,
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=1))
    print(f"sweep complete: {len(seen)} repos, {n_req} requests", flush=True)


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
            f' readme: object(expression:"HEAD:README.md")'
            f' {{ ... on Blob {{ text }} }}'
            f' {files} }}')
    return "query {" + " ".join(parts) + "}"


def deepcheck(rows: list[dict], out_path: Path) -> None:
    done = {json.loads(l)["full_name"] for l in out_path.open()} \
        if out_path.exists() else set()
    todo = [r for r in rows if r["full_name"] not in done]
    print(f"deepcheck: {len(todo)} to go ({len(done)} cached)", flush=True)
    out = out_path.open("a")
    queue, pending = list(todo), []
    rounds = 0
    while queue and rounds < 6:
        rounds += 1
        pending = []
        for i in range(0, len(queue), 10):
            batch = queue[i:i + 10]
            data, clean = gh_graphql(_deep_query(batch))
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
                    "readme": ((node.get("readme") or {}).get("text") or ""
                               )[:README_PREFIX],
                    "manifests": manifests,
                }, ensure_ascii=False) + "\n")
            out.flush()
            if (i // 10) % 20 == 0:
                print(f"  round {rounds}: {i}/{len(queue)}", flush=True)
            time.sleep(1.2)
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


def candidates_of(raw: list[dict]) -> list[dict]:
    """Storefront-channel pre-filter: who is worth a deep check at all."""
    out = []
    for r in raw:
        name = r["full_name"].split("/")[-1]
        if is_blocked(name, r["description"], r["topics"]):
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
    deep = {d["full_name"]: d for d in load_jsonl(month_dir / "deepcheck.jsonl")}
    members = registry_ids()

    agg = {k: 0 for k in (
        "universe", "blocked_nonsystem", "not_ai_scope", "excluded_license",
        "no_code_language", "no_velocity", "rescued", "fork_or_archived",
        "gone_since_sweep", "legacy_member", "admitted")}
    agg["universe"] = len(raw)
    admitted, rescue_q, legacy_fail = [], [], []

    for r in candidates_of(raw):
        d = deep.get(r["full_name"])
        is_legacy = r["id"] in members
        if d is None:
            raise RuntimeError(f"candidate never deep-checked: {r['full_name']}")
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
                legs = legs + ["velocity"]
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

    agg["admitted"] = len(admitted)
    admitted.sort(key=lambda r: (-r["stargazers_count"], r["id"]))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    month = month_dir.name

    manifest = {
        "@type": "PendingMembershipManifest",
        "predicate": "AI-v1",
        "census_month": month,
        "wave": "backlog" if month == "2026-08" else "forward",
        "governance_act": str(ACT.relative_to(REPO)),
        "governance_act_sha256": sha256(ACT),
        "scope_module_sha256": sha256(SCOPE_SRC),
        "census_run_at": now,
        "note": ("New admissions of this census. COMPLETE MEMBERSHIP = this "
                 "file UNION the live registry (etl/seeds.json); legacy "
                 "members are not repeated here. Cards activate in weekly "
                 "tranches and index after 4 weekly observations. Order of "
                 "publication is a marketing schedule, never a measurement "
                 "verdict."),
        "members": [{
            "repo_id": r["id"], "full_name": r["full_name"],
            "stars": r["stargazers_count"], "first_observed": now[:10],
            "cohort": "unassigned-v1", "status": "pending",
            "wave": "backlog" if month == "2026-08" else "forward",
            "commit_oid": r.get("commit_oid"),
            "license_observed": r.get("license_observed"),
            "admitted_by": r["evidence"]["channel"],
            "signal": r["evidence"]["signal"],
        } for r in admitted],
    }
    mp = month_dir / "pending-manifest.json"
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=1))

    census = {
        "@type": "CensusRun", "builder": BUILDER_VERSION, "predicate": "AI-v1",
        "star_bar": 500, "run_at": now,
        "sweep": json.loads(sentinel.read_text()),
        "method": ("Full-universe GitHub Search star sweep (geometric band "
                   "bisection, creation-timestamp slicing at the 1000-result "
                   "cap, per-band collected==total_count assertion); scope by "
                   "the three declaration channels of collectors/ai_scope.py; "
                   "deep legs via GraphQL. Positive-only: admitted members are "
                   "named, exclusions are aggregate."),
        "aggregate": agg,
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
        print(f"deepcheck candidates: {len(cands)} of {len(raw)}")
        deepcheck(cands, month_dir / "deepcheck.jsonl")
        return 0
    if phase == "emit":
        emit(month_dir)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
