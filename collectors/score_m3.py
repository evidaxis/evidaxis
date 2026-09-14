"""Forward m3 post-step over the frozen collector's output. Standard library only.

Run after taxonomy/redirect restoration and before snapshot_identity/refresh_sums.
--dry-run --out-dir DIR copies data/ into DIR and cards into DIR/entities/, then
seals that isolated preview. EVIDAXIS_DATA_DIR=DIR builds the web against it.
--dry-run --out-dir DIR --verify checks that preview without copying or writing.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import re
import shutil
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

try:
    from . import evaluate_axis3_v2h1 as evaluator
    from .axis3_inputs import sanity_as_of
    from .counts_check import expected_counts
    from .refresh_sums import _sums_text
    from .snapshot_identity import content_snapshot_id
    from .t2_deps_v2h1_collect import load_panel
except ImportError:
    import evaluate_axis3_v2h1 as evaluator
    from axis3_inputs import sanity_as_of
    from counts_check import expected_counts
    from refresh_sums import _sums_text
    from snapshot_identity import content_snapshot_id
    from t2_deps_v2h1_collect import load_panel

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
ENTITIES = REPO / "entities"
ACTIVATION_DATE = "2026-09-19"
AXIS1 = "github_commit_velocity"
AXIS2 = "openalex_citation_momentum"
AXIS3 = "deps_direct_dependents_momentum"
AXES = (AXIS1, AXIS2, AXIS3)
SPEC = json.loads((REPO / "methodology/m3.json").read_text(encoding="utf-8"))
AXIS3_DESCRIPTION = (
    "Unique direct dependents over each frozen-panel system's linkage-verified package union "
    "(deps.dev BigQuery Dependents, weekly; intra-panel self-dependents excluded). "
    "OLS log1p slope residualized on log1p latest, then within-cohort robust z; "
    "14 CLEAN points and 5 latest dependents; one-way fragility veto; cohort canary floor 0.80. "
    + SPEC["estimand"] + " " + SPEC["attribution"]
)
GATE = (
    "Rising = not incumbent AND cohort_n >= 5 AND >=2 of 3 axes present AND >=2 axes rising. "
    "An axis rises when raw slope > 0 AND within-cohort z >= 1; development velocity also "
    "requires >=5 average weekly commits. Axis 3 must be scored, pass its cohort canary, "
    "and have no fragility veto. No threshold changed from m2."
)
ENTITY_FIELDS = ("momentum", "percentile", "confidence", "axes_present", "convergent_axes", "rising", "status")


def axis3_records(snapshot: dict, series: dict, states: dict, panel: set,
                  reconstructed: dict) -> tuple[dict, str | None]:
    series = {eid: pts for eid, pts in series.items() if eid in panel}
    clean = sorted({s for pts in series.values() for s, _ in pts
                    if s <= snapshot["snapshot_date"] and states.get(s) == "CLEAN"})
    cutoff = clean[-1] if clean else None
    # No confirmed-clean partition at all is the same condition as a too-old one: the
    # axis cannot be scored, which is stale, not a per-system shortfall (below_floor).
    stale = cutoff is None or (date.fromisoformat(snapshot["snapshot_date"]) - date.fromisoformat(cutoff)).days > 28
    cohorts = {e["entity_id"]: e["cohort"] for e in snapshot["entities"]}
    _eligible, _rising, per = evaluator.votes_at_cutoff(series, cohorts, clean)
    held = {c for c, row in evaluator.canary(per).items() if row["hold"]}
    records = {}
    for entity in snapshot["entities"]:
        eid = entity["entity_id"]
        points = [(s, v) for s, v in series.get(eid, []) if s in clean]
        status = ("out_of_panel" if eid not in panel else "stale" if stale else
                  "held" if entity["cohort"] in held else "scored" if eid in per else "below_floor")
        row = {"status": status, "slope": None, "theil_sen": None, "cohort_z": None,
               "latest": points[-1][1] if points else None,
               "points": len(points) if eid in panel else None,
               "points_reconstructable": None, "as_of_partition": None,
               "unstable": None, "rising_vote": False}
        if status == "scored":
            vote = per[eid]
            # The evaluator votes before rounding. A published zero slope must
            # not contradict the record's explicit positive-slope requirement.
            rising_vote = vote["rising"] and vote["slope"] > 0 and vote["z"] >= evaluator.Z_FLOOR and not vote["unstable"]
            row.update(slope=vote["slope"], theil_sen=vote["theil_sen"], cohort_z=vote["z"],
                       points_reconstructable=sum(bool(reconstructed.get((eid, s))) for s, _ in points),
                       as_of_partition=points[-1][0], unstable=vote["unstable"], rising_vote=rising_vote)
        records[eid] = row
    return records, cutoff


def aggregate_entities(entities: list[dict]) -> None:
    """Preserve collect.py's order, rounding, presence rules and tie behavior."""
    cohorts = defaultdict(list)
    for entity in entities:
        cohorts[entity["cohort"]].append(entity)
    for rows in cohorts.values():
        for entity in rows:
            a1, a2, a3 = (entity["axes"].get(axis, {}) for axis in AXES)
            present, rising = [], []
            if a1.get("slope") is not None:
                present.append(AXIS1)
                if a1["slope"] > 0 and a1.get("cohort_z") is not None and a1["cohort_z"] >= 1 and a1.get("recent_weekly_commits", 0) >= 5:
                    rising.append(AXIS1)
            if a2.get("status") == "present" and a2.get("cohort_z") is not None:
                present.append(AXIS2)
                if a2["slope"] > 0 and a2["cohort_z"] >= 1:
                    rising.append(AXIS2)
            if a3.get("status") == "scored":
                present.append(AXIS3)
                if a3["rising_vote"]:
                    rising.append(AXIS3)
            entity["axes_present"], entity["convergent_axes"] = present, rising
            entity["rising"] = not entity["incumbent"] and len(rows) >= 5 and len(present) >= 2 and len(rising) >= 2
            entity["status"] = ("calibration" if entity["incumbent"] else "rising" if entity["rising"] else
                                "watch" if len(rising) == 1 else "tracked" if len(present) >= 2 else "single-axis")
            zs = [a["cohort_z"] for a in (a1, a2) if a.get("cohort_z") is not None]
            if a3.get("status") == "scored" and a3.get("cohort_z") is not None:
                zs.append(a3["cohort_z"])
            entity["momentum"] = round(max(0.0, min(100.0, 50 + 12.5 * (sum(zs) / len(zs)))), 1) if zs else None
            entity["confidence"] = ("high" if entity["rising"] else "medium") if len(present) >= 2 else "low"
            entity["percentile"] = None
        scored = sorted((e for e in rows if e["momentum"] is not None), key=lambda e: e["momentum"])
        for i, entity in enumerate(scored):
            entity["percentile"] = round(100 * i / max(1, len(scored) - 1)) if len(scored) > 1 else 50


def pearson(rows: list[tuple[float, float]]) -> float | None:
    if len(rows) < 5:
        return None
    mx, my = (sum(row[i] for row in rows) / len(rows) for i in (0, 1))
    cov = sum((x - mx) * (y - my) for x, y in rows)
    vx = sum((x - mx) ** 2 for x, _ in rows)
    vy = sum((y - my) ** 2 for _, y in rows)
    return round(cov / math.sqrt(vx * vy), 4) if vx > 0 and vy > 0 else None


def axis_correlations(entities: list[dict]) -> dict:
    result = {}
    for left, right in ((AXIS3, AXIS1), (AXIS3, AXIS2), (AXIS1, AXIS2)):
        cohorts = defaultdict(list)
        for entity in entities:
            a, b = (entity["axes"][axis] for axis in (left, right))
            if AXIS3 in (left, right) and entity["axes"][AXIS3]["status"] != "scored":
                continue
            if a.get("cohort_z") is not None and b.get("cohort_z") is not None:
                cohorts[entity["cohort"]].append((a["cohort_z"], b["cohort_z"]))
        pooled, per_cohort = [], {}
        for cohort, pairs in sorted(cohorts.items()):
            per_cohort[cohort] = {"r": pearson(pairs), "pairs": len(pairs)}
            if len(pairs) >= 5:
                ma, mb = (sum(pair[i] for pair in pairs) / len(pairs) for i in (0, 1))
                pooled.extend((a - ma, b - mb) for a, b in pairs)
        result[f"{left}__{right}"] = {"axes": [left, right], "r": pearson(pooled),
                                     "pairs": len(pooled), "per_cohort": per_cohort}
    return result


def score_snapshot(snapshot: dict, *, observations: Path, evidence: dict, panel: set) -> dict:
    scored = copy.deepcopy(snapshot)
    series = evaluator.load_series(snapshot["snapshot_date"], observations=observations, captured_at=snapshot["captured_at"])
    reconstructed = {}
    for path, row in evaluator.observation_rows(snapshot["snapshot_date"], observations=observations, captured_at=snapshot["captured_at"]):
        reconstructed[(row["entity_id"], row["snapshot_at"][:10])] = (
            "backfill" in path.relative_to(observations).parts or row.get("series", "").startswith("baseline"))
    records, cutoff = axis3_records(snapshot, series, evidence["states"], panel, reconstructed)
    for entity in scored["entities"]:
        entity["axes"][AXIS3] = records[entity["entity_id"]]
    aggregate_entities(scored["entities"])
    scored.update(methodology_version="m3", gate=GATE, axis3_cutoff=cutoff)
    scored["axes"][AXIS3] = AXIS3_DESCRIPTION
    scored["counts"] = expected_counts(scored["entities"])
    diagnostics = scored.setdefault("diagnostics", {})
    diagnostics["axis_correlations"] = axis_correlations(scored["entities"])
    diagnostics["axis3_sanity_check"] = {key: evidence[key] for key in ("relative", "sha256", "commit", "committed_at")}
    return scored


def json_bytes(doc: dict) -> bytes:
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def historical_card(entity: dict, snapshot: dict) -> str:
    """A historical preview cannot reuse the latest capture's card frontmatter."""
    fields = {"schema_ver": snapshot.get("schema_version", "1.0"),
              **{key: entity.get(key) for key in ("entity_id", "entity_type", "name", "slug", "homepage")},
              "ids": {key: entity.get(key) for key in ("github_repo", "openalex_work_ids")},
              "classification": {"domain": snapshot.get("domain", {}).get("slug", "ai"),
                                 "industry": entity.get("industry"), "sub_niche": entity.get("sub_niche")}}
    lines = ["---", *(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items()),
             "score:", f"  snapshot_id: {snapshot['snapshot_id']}", f"  captured_at: {snapshot['captured_at']}",
             "---", ""]
    return "\n".join(lines)


def card_text(text: str, entity: dict, snapshot: dict) -> str:
    score = {"methodology_version": "m3", "snapshot_id": snapshot["snapshot_id"],
             "captured_at": snapshot["captured_at"], "period": snapshot["period"],
             **{key: entity[key] for key in ENTITY_FIELDS}}
    lines = []
    for key, value in score.items():
        encoded = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        lines.append(f"  {key}: {encoded}")
    lines.append("  axes:")
    lines.extend(f"    {axis}: {json.dumps(entity['axes'][axis], ensure_ascii=False)}" for axis in AXES)
    front, sep, body = text.partition("\n---\n")
    front, replacements = re.subn(r"(?m)^(score:[^\n]*\n)(?:[ \t]+[^\n]*\n)*", lambda m: m[1] + "\n".join(lines) + "\n", front + "\n")
    if not sep or replacements != 1:
        raise ValueError(f"missing score frontmatter: {entity['entity_id']}")
    # The frozen collector's prose can claim no convergence is possible without
    # citations. Regenerate its derived body when a third axis becomes available.
    body = f"\n# {entity['name']}\n\nEvidaxis measures **{entity['name']}** on methodology m3. Momentum {'n/a' if entity['momentum'] is None else entity['momentum']}{'' if entity['momentum'] is None else '/100'}; {len(entity['axes_present'])} axes present, {len(entity['convergent_axes'])} axes converging.\n"
    if entity["axes"][AXIS3]["status"] == "scored":
        body += "\n" + SPEC["estimand"] + "\n"
    return front.rstrip("\n") + sep + body


def planned_files(snapshot: dict, old: dict, data: Path, cards: Path) -> dict[Path, bytes]:
    bundle = data / "snapshots" / snapshot["snapshot_date"]
    plan = {bundle / "snapshot.json": json_bytes(snapshot)}
    for name in ("manifest.json", "provenance.json"):
        path = bundle / name
        if path.is_file():
            doc = json.loads(path.read_text())
            if "methodology_version" in doc:
                doc["methodology_version"] = "m3"
            doc["snapshot_id"] = snapshot["snapshot_id"]
            plan[path] = json_bytes(doc)
    latest_path = data / "latest.json"
    latest = json.loads(latest_path.read_text())
    if latest["snapshot_date"] != snapshot["snapshot_date"]:
        raise ValueError("only the latest snapshot may be scored in place")
    latest.update({key: snapshot[key] for key in ("methodology_version", "snapshot_id", "period")})
    plan[latest_path] = json_bytes(latest)
    for entity in snapshot["entities"]:
        eid = entity["entity_id"]
        card = cards / f"{eid}.md"
        text = card.read_text(encoding="utf-8")
        if f"  snapshot_id: {old['snapshot_id']}\n" not in text or f"  captured_at: {old['captured_at']}\n" not in text:
            raise ValueError(f"entity card belongs to another capture: {card}")
        plan[card] = card_text(text, entity, snapshot).encode("utf-8")
        history = data / "history" / f"{eid}.jsonl"
        lines, matches = [], 0
        for line in history.read_bytes().decode("utf-8").splitlines(keepends=True):
            row = json.loads(line) if line.strip() else {}
            if (row.get("v") == "ts_1" and row.get("entity_id") == eid and row.get("snapshot_id") == old["snapshot_id"]
                    and row.get("period") == old["period"] and row.get("captured_at") == old["captured_at"]):
                row.update({key: snapshot[key] for key in ("methodology_version", "snapshot_id")})
                row.update({key: entity[key] for key in ("momentum", "rising", "convergent_axes")})
                row.update(axis3_z=entity["axes"][AXIS3]["cohort_z"], axis3_as_of=entity["axes"][AXIS3]["as_of_partition"])
                line = json.dumps(row, ensure_ascii=False) + ("\n" if line.endswith("\n") else "")
                matches += 1
            lines.append(line)
        if not matches:
            raise ValueError(f"no matching current-capture history row: {history}")
        plan[history] = "".join(lines).encode("utf-8")
    return plan


def run(snapshot_date: str | None = None, *, dry_run: bool = False, out_dir: Path | None = None,
        verify: bool = False) -> int:
    if dry_run != (out_dir is not None):
        raise ValueError("--dry-run and --out-dir must be used together")
    data, cards = DATA, ENTITIES
    if dry_run:
        data = out_dir.resolve()
        if data == DATA.resolve() or DATA.resolve() in data.parents or data in DATA.resolve().parents:
            raise ValueError("--out-dir must be outside data/ and must not contain data/")
        cards = data / "entities"
    existing_preview = dry_run and (data / "latest.json").is_file()
    source = data if dry_run and (verify or existing_preview) else DATA
    latest_date = json.loads((source / "latest.json").read_text())["snapshot_date"]
    selected = snapshot_date or latest_date
    date.fromisoformat(selected)
    old = json.loads((source / "snapshots" / selected / "snapshot.json").read_text())
    if selected != old["snapshot_date"]:
        raise ValueError("snapshot directory date differs from payload")
    if selected != latest_date and not dry_run:
        raise ValueError("only the latest snapshot may be scored; earlier snapshots are immutable")
    if existing_preview and selected != latest_date:
        raise ValueError("use an empty --out-dir for another historical preview date")
    if selected < ACTIVATION_DATE and not dry_run:
        # A weekly run (manual dispatch or replay) before activation must stay an m2
        # publication, not a failed workflow: report and leave every file untouched.
        mode = "--verify" if verify else "run"
        print(f"score_m3 {mode}: latest snapshot {selected} predates activation {ACTIVATION_DATE}; "
              "no m3 work (use --dry-run --out-dir to preview)")
        return 0
    evidence = sanity_as_of(old["captured_at"], REPO)
    panel, _manifest_hash = load_panel()
    scored = score_snapshot(old, observations=source / "observations", evidence=evidence, panel=set(panel))
    if dry_run:
        scored["snapshot_id"] = content_snapshot_id(scored)
        if not verify and not existing_preview:
            if data.exists() and any(data.iterdir()):
                raise ValueError("--out-dir must be empty for a new dry run")
            def ignore_future_snapshots(folder, names):
                return [name for name in names if name > selected] if Path(folder) == DATA / "snapshots" else []

            shutil.copytree(DATA, data, dirs_exist_ok=True, ignore=ignore_future_snapshots)
            if selected == latest_date:
                shutil.copytree(ENTITIES, cards)
            else:
                cards.mkdir()
                for entity in old["entities"]:
                    (cards / f"{entity['entity_id']}.md").write_text(historical_card(entity, old), encoding="utf-8")
            if selected != latest_date:
                # A historical preview is isolated; its pointer must select the
                # requested date without changing the real publication pointer.
                (data / "latest.json").write_bytes(json_bytes({key: old[key] for key in ("snapshot_date", "snapshot_id", "period")}))
    plan = planned_files(scored, old, data, cards)
    drift = [path for path, blob in plan.items() if not path.is_file() or path.read_bytes() != blob]
    if verify:
        if drift:
            print("score_m3 --verify: DRIFT\n" + "\n".join(str(path) for path in drift))
            return 1
        print("score_m3 --verify: files match recomputation")
        return 0
    for path in drift:
        path.write_bytes(plan[path])
    if dry_run:
        bundle = data / "snapshots" / selected
        (bundle / "SHA256SUMS").write_text(_sums_text(bundle))
    statuses = defaultdict(int)
    for entity in scored["entities"]:
        statuses[entity["axes"][AXIS3]["status"]] += 1
    print(f"score_m3: {selected}, cutoff {scored['axis3_cutoff']}, {len(drift)} files changed")
    print(f"axis 3 states: {dict(sorted(statuses.items()))}; Rising: {[e['entity_id'] for e in scored['entities'] if e['rising']]}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        return run(args.date, dry_run=args.dry_run, out_dir=args.out_dir, verify=args.verify)
    except (ValueError, OSError) as exc:
        print(f"score_m3: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
