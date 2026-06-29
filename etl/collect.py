#!/usr/bin/env python3
"""
Evidaxis collector v2 — the day-1 build slice of the locked architecture.

Implements the LOCKED methodology faithfully on live data:
  * Axis 1  — GitHub commit-velocity: log-slope of the weekly commit trend (speed, not size).
  * Axis 2  — OpenAlex citation momentum: log-slope of citations-per-year (completed years only).
  * Within-cohort robust-z (median/MAD) per axis, with a light residualize on a size proxy
    (log stars / log total-citations) so "rising" means rising RELATIVE to peers, not just big.
  * Convergence GATE: an entity is "Rising" (badge-eligible) only if >=2 axes are PRESENT and
    >=2 of them are rising (raw slope > 0 AND cohort-z >= 0). Positive-only; no "worst" list.

Then it emits the canonical CC0 artifacts (P5): opaque entity ids, per-entity dossier cards,
append-only history JSONL, a frozen snapshot bundle + manifest + SHA256SUMS + provenance,
the taxonomy node registry, a reserved (empty) relationships table, and redirects.yaml.

git = the only source of truth. The site and any DB are derived and rebuildable from these files.
Stdlib only (json, math, hashlib, urllib). GitHub token optional (env GITHUB_TOKEN, or a gitignored etl/.env).
"""
import json, math, os, re, time, hashlib, urllib.request, urllib.error
from pathlib import Path
from datetime import date, datetime, timezone

ROOT = Path(__file__).resolve().parent          # etl/
REPO = ROOT.parent                              # repo root
METHODOLOGY_VERSION = "m1"
SCHEMA_VER = "1.0"
FETCHER_VERSION = "collect/2.0"
CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"   # no I L O U
ACTIVITY_FLOOR_WK = 5.0     # axis-1 sanity floor: a dormant repo (< this avg weekly commits) is not "rising"
AXIS2_MIN_YEARS = 3         # axis-2 needs >=3 completed citation years to vote

# ---------------------------------------------------------------- tokens / http

def _load_github_token():
    t = os.environ.get("GITHUB_TOKEN", "").strip()
    if t:
        return t
    for cand in (ROOT / ".env", Path(os.environ["EVIDAXIS_GITHUB_ENV"]) if os.environ.get("EVIDAXIS_GITHUB_ENV") else ROOT / ".env"):
        try:
            if cand.exists():
                for line in cand.read_text().splitlines():
                    line = line.strip()
                    if line.startswith("GITHUB_TOKEN="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""

GH_TOKEN = _load_github_token()
GH_HDR = {"User-Agent": "evidaxis-collect/2.0", "Accept": "application/vnd.github+json"}
if GH_TOKEN:
    GH_HDR["Authorization"] = f"Bearer {GH_TOKEN}"
OA_MAILTO = "research@evidaxis.org"


def _get_json(url, headers=None, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers or {"User-Agent": "evidaxis-collect/2.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                if r.status == 202:           # GitHub computing stats
                    time.sleep(2.0); continue
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 202:
                time.sleep(2.0); continue
            if e.code in (403, 429):
                print(f"  rate-limit {e.code} on {url[:70]}"); return "RATELIMIT"
            if e.code == 404:
                return None
            time.sleep(1.0); continue
        except Exception as ex:
            print(f"  err {type(ex).__name__} {url[:70]}"); time.sleep(1.0); continue
    return None

# ---------------------------------------------------------------- identity (P5)

def mint_entity_id(natural_key: str) -> str:
    """Deterministic opaque id from a stable natural key (github_repo).
    e_ + 10 Crockford chars + 1 checksum. A pure function of the key => minted once,
    never reassigned, stable across re-runs without a registry."""
    h = hashlib.sha256(natural_key.lower().encode()).digest()
    n = int.from_bytes(h[:8], "big")            # 64 bits
    chars = []
    for _ in range(10):
        chars.append(CROCKFORD[n & 31]); n >>= 5
    data = "".join(chars)
    chk = CROCKFORD[sum(CROCKFORD.index(c) for c in data) % 32]
    return f"e_{data}{chk}"


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return re.sub(r"-+", "-", s) or "x"

# ---------------------------------------------------------------- math

def log_slope(ys):
    """Least-squares slope of log1p(y) over evenly spaced points. Speed of a trend."""
    n = len(ys)
    if n < 3:
        return None
    xs = list(range(n)); ly = [math.log1p(max(0.0, float(y))) for y in ys]
    mx, my = sum(xs) / n, sum(ly) / n
    den = sum((xs[i] - mx) ** 2 for i in range(n)) or 1.0
    num = sum((xs[i] - mx) * (ly[i] - my) for i in range(n))
    return num / den


def robust_z(vals):
    """median/MAD z, winsorized +-3 (robust to a single giant)."""
    s = sorted(vals); n = len(s)
    med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    devs = sorted(abs(v - med) for v in vals)
    mad = devs[n // 2] if n % 2 else (devs[n // 2 - 1] + devs[n // 2]) / 2
    sd = 1.4826 * mad or 1e-9
    return [max(-3.0, min(3.0, (v - med) / sd)) for v in vals]


def residualize(zs, sizes):
    """Remove the size-correlation: regress z on z(log size), return residual.
    This is the 'rising != big' incumbent dampener. Guarded for tiny cohorts."""
    n = len(zs)
    if n < 4:
        return zs
    lz = robust_z([math.log1p(max(0.0, s)) for s in sizes])
    mz, ml = sum(zs) / n, sum(lz) / n
    var = sum((lz[i] - ml) ** 2 for i in range(n)) or 1e-9
    cov = sum((zs[i] - mz) * (lz[i] - ml) for i in range(n))
    beta = cov / var
    return [zs[i] - beta * (lz[i] - ml) for i in range(n)]

# ---------------------------------------------------------------- axis 2 (OpenAlex)

def citation_series(work_ids):
    """Sum counts_by_year across one or more OpenAlex works (preprint+published split)."""
    by_year = {}
    raw = {}
    for wid in work_ids:
        url = (f"https://api.openalex.org/works/{wid}"
               f"?select=id,display_name,cited_by_count,counts_by_year&mailto={OA_MAILTO}")
        d = _get_json(url)
        if not d or d == "RATELIMIT" or "counts_by_year" not in d:
            continue
        raw[wid] = {"title": d.get("display_name"), "counts_by_year": d.get("counts_by_year", [])}
        for row in d.get("counts_by_year", []):
            y = row.get("year"); c = row.get("cited_by_count", 0)
            if y is not None:
                by_year[y] = by_year.get(y, 0) + (c or 0)
        time.sleep(0.15)
    return by_year, raw


def axis2_slope(work_ids, current_year):
    """Returns (status, slope, total, series). status in absent|insufficient|present.
    Citation MOMENTUM (recent rate of change), not all-time growth:
      * drop the partial current year (incomplete -> biases slope down),
      * drop the earliest completed year when >=4 exist (a paper's birth year is anomalously
        low and inflates the all-time slope; a cooling paper then correctly reads as declining),
      * need >=3 completed years to vote."""
    if not work_ids:
        return "absent", None, 0, {}
    by_year, raw = citation_series(work_ids)
    if not by_year:
        return "absent", None, 0, {}
    completed_years = sorted(y for y in by_year if y < current_year)
    total = sum(by_year.values())
    detail = {"by_year": by_year, "raw": raw}
    if len(completed_years) < AXIS2_MIN_YEARS:
        return "insufficient", None, total, detail
    fit_years = completed_years[1:] if len(completed_years) >= 4 else completed_years
    ys = [by_year[y] for y in fit_years]
    return "present", log_slope(ys), total, detail

# ---------------------------------------------------------------- collection

def load_seeds():
    return json.loads((ROOT / "seeds.json").read_text())


def iso_period(d):
    iso = d.isocalendar()
    return f"{iso[0]}-w{iso[1]:02d}"


def main():
    seeds = load_seeds()
    today = date.today()
    captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    period = iso_period(today)
    current_year = today.year
    domain = seeds["domain"]
    print(f"Evidaxis collect v2 — period {period}, token={'yes' if GH_TOKEN else 'no(60/h)'}\n")

    cohorts = {}           # vert_key -> list of entity dicts (with raw axis data)
    id_map = {}
    provenance = {"github_weekly": {}, "openalex": {}}

    for vkey, vert in seeds["verticals"].items():
        print(f"-- {vkey} --")
        rows = []
        for ent in vert["entities"]:
            repo = ent["github_repo"]
            eid = mint_entity_id(repo)
            id_map[repo] = eid
            meta = _get_json(f"https://api.github.com/repos/{repo}", GH_HDR)
            act = _get_json(f"https://api.github.com/repos/{repo}/stats/commit_activity", GH_HDR)
            if meta == "RATELIMIT" or act == "RATELIMIT":
                print("  ABORT: GitHub rate limit. Set GITHUB_TOKEN."); return
            if not meta or not act:
                print(f"  x {repo}: no data"); continue
            weekly = [w["total"] for w in act]
            a1 = log_slope(weekly[-26:])
            stars = meta.get("stargazers_count") or 0
            created = (meta.get("created_at") or "")[:10]
            recent = round(sum(weekly[-12:]) / 12, 1)
            a2_status, a2_slope, a2_total, a2_detail = axis2_slope(ent.get("openalex_work_ids", []), current_year)
            provenance["github_weekly"][eid] = weekly
            if a2_detail:
                provenance["openalex"][eid] = a2_detail
            rows.append({
                "entity_id": eid, "repo": repo, "name": ent["name"],
                "slug": slugify(ent["name"]), "entity_type": ent.get("entity_type", "repo"),
                "homepage": ent.get("homepage"),
                "incumbent": ent.get("incumbent", False),
                "openalex_work_ids": ent.get("openalex_work_ids", []),
                "axis1_slope": a1, "stars": stars, "created": created, "recent_wk": recent,
                "axis2_status": a2_status, "axis2_slope": a2_slope, "axis2_total": a2_total,
                "axis2_series": a2_detail.get("by_year") if a2_detail else None,
                "note": ent.get("note"), "axis2_proxy": ent.get("axis2_proxy"),
            })
            a2s = "n/a" if a2_slope is None else f"{a2_slope:+.3f}"
            print(f"  ok {repo:<34} a1={('  n/a' if a1 is None else f'{a1:+.3f}')} "
                  f"a2={a2s:<7}({a2_status}) ★{stars}")
            time.sleep(0.2)
        cohorts[vkey] = rows
        print()

    # ---- within-cohort robust-z + residualize + convergence gate
    for vkey, rows in cohorts.items():
        a1_rows = [r for r in rows if r["axis1_slope"] is not None]
        if len(a1_rows) >= 3:
            z = robust_z([r["axis1_slope"] for r in a1_rows])
            z = residualize(z, [r["stars"] for r in a1_rows])
            for r, zz in zip(a1_rows, z):
                r["axis1_z"] = round(zz, 3)
        a2_rows = [r for r in rows if r["axis2_status"] == "present" and r["axis2_slope"] is not None]
        if len(a2_rows) >= 3:
            z = robust_z([r["axis2_slope"] for r in a2_rows])
            z = residualize(z, [r["axis2_total"] for r in a2_rows])
            for r, zz in zip(a2_rows, z):
                r["axis2_z"] = round(zz, 3)
        elif len(a2_rows) >= 2:                 # too few to z-score; mark present but not voting
            for r in a2_rows:
                r["axis2_z"] = None

        for r in rows:
            axes_present, axes_rising = [], []
            if r.get("axis1_slope") is not None:
                rising1 = ((r["axis1_slope"] > 0) and (r.get("axis1_z") is not None and r["axis1_z"] >= 0)
                           and (r.get("recent_wk", 0) >= ACTIVITY_FLOOR_WK))   # dormant repo is not "rising"
                axes_present.append("github_commit_velocity")
                if rising1:
                    axes_rising.append("github_commit_velocity")
            if r["axis2_status"] == "present" and r.get("axis2_z") is not None:
                rising2 = (r["axis2_slope"] > 0) and (r["axis2_z"] >= 0)
                axes_present.append("openalex_citation_momentum")
                if rising2:
                    axes_rising.append("openalex_citation_momentum")
            r["axes_present"] = axes_present
            r["convergent_axes"] = axes_rising
            r["rising"] = (not r["incumbent"]) and len(axes_present) >= 2 and len(axes_rising) >= 2
            # honest display taxonomy
            if r["incumbent"]:
                r["status"] = "calibration"      # measured to anchor the cohort; not badge-eligible
            elif r["rising"]:
                r["status"] = "rising"           # >=2 independent axes converge (the badge)
            elif len(axes_rising) == 1:
                r["status"] = "watch"            # one axis rising; awaiting convergence on a second
            elif len(axes_present) >= 2:
                r["status"] = "tracked"          # measured on >=2 axes, none currently rising
            else:
                r["status"] = "single-axis"      # only one axis available; cannot converge yet
            # composite momentum (FLEX per P3): mean of present-axis z mapped to 0-100, gate-aware
            zs = [r[k] for k in ("axis1_z", "axis2_z") if r.get(k) is not None]
            r["momentum"] = round(max(0.0, min(100.0, 50 + 12.5 * (sum(zs) / len(zs)))), 1) if zs else None
            # confidence: data richness
            conf = "low"
            if len(axes_present) >= 2:
                conf = "high" if r["rising"] else "medium"
            r["confidence"] = conf

        # within-cohort percentile by momentum (only among scored)
        scored = sorted([r for r in rows if r["momentum"] is not None], key=lambda r: r["momentum"])
        m = len(scored)
        for i, r in enumerate(scored):
            r["percentile"] = round(100 * (i) / max(1, m - 1)) if m > 1 else 50

    write_artifacts(seeds, cohorts, id_map, provenance, today, period, captured_at)


# ---------------------------------------------------------------- emit (P5 artifacts)

def _yaml_escape(s):
    if s is None:
        return '""'
    s = str(s).replace('"', '\\"')
    return f'"{s}"'


def write_artifacts(seeds, cohorts, id_map, provenance, today, period, captured_at):
    dstr = today.isoformat()
    domain = seeds["domain"]
    snap_dir = REPO / "data" / "snapshots" / dstr
    snap_dir.mkdir(parents=True, exist_ok=True)
    (REPO / "entities").mkdir(exist_ok=True)
    (REPO / "data" / "history").mkdir(parents=True, exist_ok=True)
    (REPO / "taxonomy").mkdir(exist_ok=True)

    # snapshot.json (the full computed record, public-facing fields)
    all_entities = []
    for vkey, vert in seeds["verticals"].items():
        for r in cohorts[vkey]:
            all_entities.append({
                "entity_id": r["entity_id"], "name": r["name"], "slug": r["slug"],
                "entity_type": r["entity_type"], "homepage": r["homepage"],
                "github_repo": r["repo"], "openalex_work_ids": r["openalex_work_ids"],
                "industry": vert["industry_slug"], "sub_niche": vert["subniche_slug"],
                "cohort": vkey,
                "axes": {
                    "github_commit_velocity": {
                        "slope": r.get("axis1_slope"), "cohort_z": r.get("axis1_z"),
                        "recent_weekly_commits": r.get("recent_wk"), "stars_not_scored": r.get("stars"),
                    },
                    "openalex_citation_momentum": {
                        "status": r["axis2_status"], "slope": r.get("axis2_slope"),
                        "cohort_z": r.get("axis2_z"), "total_citations": r.get("axis2_total"),
                        "by_year": r.get("axis2_series"), "proxy": r.get("axis2_proxy"),
                    },
                },
                "momentum": r.get("momentum"), "percentile": r.get("percentile"),
                "confidence": r.get("confidence"), "axes_present": r.get("axes_present"),
                "convergent_axes": r.get("convergent_axes"), "rising": r.get("rising"),
                "status": r.get("status"), "incumbent": r.get("incumbent", False),
                "note": r.get("note"),
            })

    source_manifest = {
        "github_repos": sorted(id_map.keys()),
        "openalex_works": sorted({w for v in seeds["verticals"].values()
                                  for e in v["entities"] for w in e.get("openalex_work_ids", [])}),
    }
    manifest_hash = hashlib.sha256(
        json.dumps(source_manifest, sort_keys=True).encode()).hexdigest()
    snapshot_id = hashlib.sha1(f"{METHODOLOGY_VERSION}{manifest_hash}".encode()).hexdigest()[:12]

    snapshot = {
        "schema_version": SCHEMA_VER,
        "snapshot_date": dstr, "period": period, "captured_at": captured_at,
        "methodology_version": METHODOLOGY_VERSION, "snapshot_id": snapshot_id,
        "fetcher_version": FETCHER_VERSION, "license": "CC0-1.0",
        "domain": domain,
        "axes": {
            "github_commit_velocity": "log-slope of weekly commit counts (last 26 weeks); within-cohort robust-z (median/MAD), residualized on log stars. Stars are never scored.",
            "openalex_citation_momentum": "log-slope of citations-per-year measuring recent momentum: partial current year dropped, earliest (birth) year dropped when >=4 exist, >=3 completed years required; within-cohort robust-z, residualized on log total citations.",
        },
        "gate": ("Rising = >=2 axes present AND >=2 axes rising. An axis is rising if raw slope > 0 AND "
                 "within-cohort z >= 0; commit-velocity additionally requires >= %g avg weekly commits "
                 "(a dormant repo is not rising). Positive-only; no 'worst' list." % ACTIVITY_FLOOR_WK),
        "cohorts": {vk: {"label": v["label"], "industry": v["industry_slug"],
                         "sub_niche": v["subniche_slug"]} for vk, v in seeds["verticals"].items()},
        # Person-free by construction (I2 systems-not-people + UK-GDPR + immutable-DOI × Art.17):
        # no natural-person field is collected, emitted, or carried anywhere — neither the live
        # site nor the CC0 deposit names individuals. manifest_hash is over source_manifest only.
        "entities": all_entities,
        "counts": {"entities": len(all_entities),
                   "rising": sum(1 for e in all_entities if e["rising"]),
                   "watch": sum(1 for e in all_entities if e["status"] == "watch"),
                   "tracked": sum(1 for e in all_entities if e["status"] in ("tracked", "single-axis")),
                   "calibration": sum(1 for e in all_entities if e["status"] == "calibration"),
                   "axis2_present": sum(1 for e in all_entities
                                        if e["axes"]["openalex_citation_momentum"]["status"] == "present")},
    }
    _write_json(snap_dir / "snapshot.json", snapshot)
    _write_json(snap_dir / "provenance.json", {
        "snapshot_id": snapshot_id, "methodology_version": METHODOLOGY_VERSION,
        "fetcher_version": FETCHER_VERSION, "captured_at": captured_at,
        "source_manifest": source_manifest, "manifest_hash": manifest_hash,
        "github_weekly_raw": provenance["github_weekly"], "openalex_raw": provenance["openalex"],
    })
    _write_json(snap_dir / "manifest.json", {
        "snapshot_id": snapshot_id, "snapshot_date": dstr, "period": period,
        "schema_version": SCHEMA_VER, "methodology_version": METHODOLOGY_VERSION,
        "fetcher_version": FETCHER_VERSION, "manifest_hash": manifest_hash,
        "license": "CC0-1.0", "generator": FETCHER_VERSION,
    })

    # SHA256SUMS over the snapshot files (byte-reproducibility grip)
    sums = []
    for fn in ("snapshot.json", "manifest.json", "provenance.json"):
        h = hashlib.sha256((snap_dir / fn).read_bytes()).hexdigest()
        sums.append(f"{h}  {fn}")
    (snap_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n")

    # per-entity dossier cards + history JSONL
    for e in all_entities:
        _write_entity_card(e, snapshot_id, dstr, period, captured_at)
        hist = REPO / "data" / "history" / f"{e['entity_id']}.jsonl"
        row = {"v": "ts_1", "entity_id": e["entity_id"], "period": period,
               "captured_at": captured_at, "methodology_version": METHODOLOGY_VERSION,
               "snapshot_id": snapshot_id, "momentum": e["momentum"],
               "axis1_z": e["axes"]["github_commit_velocity"]["cohort_z"],
               "axis2_z": e["axes"]["openalex_citation_momentum"]["cohort_z"],
               "rising": e["rising"], "convergent_axes": e["convergent_axes"]}
        with hist.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # taxonomy node registry
    nodes = [{"taxon_id": "t_" + hashlib.sha256(domain["slug"].encode()).hexdigest()[:8],
              "level": "domain", "slug": domain["slug"], "name": domain["label"], "parent": None}]
    for vk, v in seeds["verticals"].items():
        nodes.append({"taxon_id": "t_" + hashlib.sha256(v["industry_slug"].encode()).hexdigest()[:8],
                      "level": "industry", "slug": v["industry_slug"], "name": v["label"].split("—")[0].strip(),
                      "parent": domain["slug"]})
        nodes.append({"taxon_id": "t_" + hashlib.sha256(v["subniche_slug"].encode()).hexdigest()[:8],
                      "level": "sub_niche", "slug": v["subniche_slug"], "name": v["label"],
                      "parent": v["industry_slug"]})
    _write_json(REPO / "taxonomy" / "nodes.json", {"taxonomy_version": "tax_1", "nodes": nodes})

    # reserved relationships table (people/graph layer arrives with zero migration)
    rel = REPO / "relationships.tsv"
    if not rel.exists():
        rel.write_text("rel_id\tsrc_id\tsrc_type\tdst_id\tdst_type\trel_type\tsince\tuntil\tsource\tconfidence\n")

    # redirects artifact (P5 lock) — human slug form -> canonical id-only
    (REPO / "redirects.yaml").write_text(
        "# machine-auditable redirects (P5). /e/{id}/{slug} -> /e/{id} is also enforced in vercel.json.\n"
        "rules:\n  - from: '/e/:entity_id/:slug'\n    to: '/e/:entity_id'\n    status: 301\n"
        "  - from: '/methodology'\n    to: '/methodology/current'\n    status: 301\n")

    _write_json(REPO / "etl" / "id_map.json", id_map)

    # latest pointer for the site build
    _write_json(REPO / "data" / "latest.json",
                {"snapshot_date": dstr, "period": period, "snapshot_id": snapshot_id})

    c = snapshot["counts"]
    print(f"\nSNAPSHOT {snapshot_id}  ({dstr}, {period})")
    print(f"  entities={c['entities']}  rising={c['rising']}  watch={c['watch']}"
          f"  tracked={c['tracked']}  calibration={c['calibration']}  axis2_present={c['axis2_present']}")
    for label, st in (("RISING (>=2-axis convergence)", "rising"), ("WATCH (1 axis rising)", "watch")):
        es = sorted([e for e in all_entities if e["status"] == st], key=lambda x: -(x["momentum"] or 0))
        if es:
            print(f"  {label}:")
            for e in es:
                print(f"    {e['name']:<16} momentum={e['momentum']}  axes_rising={e['convergent_axes']}")
    print(f"  artifacts -> data/snapshots/{dstr}/  + entities/  + data/history/")


def _write_entity_card(e, snapshot_id, dstr, period, captured_at):
    a1 = e["axes"]["github_commit_velocity"]; a2 = e["axes"]["openalex_citation_momentum"]
    fm = []
    fm.append("---")
    fm.append(f"schema_ver: {SCHEMA_VER}")
    fm.append(f"entity_id: {e['entity_id']}")
    fm.append(f"entity_type: {e['entity_type']}")
    fm.append(f"name: {_yaml_escape(e['name'])}")
    fm.append(f"slug: {e['slug']}")
    fm.append(f"homepage: {_yaml_escape(e['homepage'])}")
    fm.append("ids:")
    fm.append(f"  github_repo: {_yaml_escape(e['github_repo'])}")
    fm.append(f"  openalex_work_ids: {json.dumps(e['openalex_work_ids'])}")
    fm.append("classification:")
    fm.append(f"  domain: ai")
    fm.append(f"  industry: {e['industry']}")
    fm.append(f"  sub_niche: {e['sub_niche']}")
    fm.append("score:  # DERIVED — never edited by hand; rebuilt from data each snapshot")
    fm.append(f"  methodology_version: {METHODOLOGY_VERSION}")
    fm.append(f"  snapshot_id: {snapshot_id}")
    fm.append(f"  captured_at: {captured_at}")
    fm.append(f"  period: {period}")
    fm.append(f"  momentum: {e['momentum']}")
    fm.append(f"  percentile: {e['percentile']}")
    fm.append(f"  confidence: {e['confidence']}")
    fm.append(f"  rising: {str(e['rising']).lower()}")
    fm.append(f"  status: {e['status']}")
    fm.append(f"  axes_present: {json.dumps(e['axes_present'])}")
    fm.append(f"  convergent_axes: {json.dumps(e['convergent_axes'])}")
    fm.append("  axes:")
    fm.append(f"    github_commit_velocity: {json.dumps(a1)}")
    fm.append(f"    openalex_citation_momentum: {json.dumps(a2)}")
    if e.get("note"):
        fm.append(f"note: {_yaml_escape(e['note'])}")
    fm.append("---")
    fm.append("")
    fm.append(f"# {e['name']}")
    fm.append("")
    one = _one_liner(e)
    fm.append(one)
    (REPO / "entities" / f"{e['entity_id']}.md").write_text("\n".join(fm) + "\n")


def _one_liner(e):
    a2 = e["axes"]["openalex_citation_momentum"]
    if e["rising"]:
        return (f"Evidaxis measures **{e['name']}** as **rising** in the {e['sub_niche']} cohort: "
                f"momentum {e['momentum']}/100, with {len(e['convergent_axes'])} independent axes converging.")
    if a2["status"] == "absent":
        return (f"Evidaxis tracks **{e['name']}** on development-velocity only — no academic citation axis "
                f"exists for it, so it cannot satisfy the >=2-axis convergence gate (measured, not badged).")
    if a2["status"] == "insufficient":
        return (f"Evidaxis tracks **{e['name']}**; its citation history is too young (<2 completed years) "
                f"to compute a citation-momentum axis yet — measured on one axis.")
    return f"Evidaxis measures **{e['name']}** in the {e['sub_niche']} cohort."


def _write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
