"""frontier_manifest - the discovery-frontier denominator, captured at scan time.

Why: "who did we see and NOT admit" is un-backfillable. The 19->103 expansion
ran without any candidate-pool record (SCALE-PLAN required freezing the
universe first; it never happened), so that denominator is lost forever. This
tool makes the loss unrepeatable: every universe scan writes a dated frontier
manifest, and CI refuses any etl/seeds.json change that is not paired with one
(.github/workflows/archive-integrity.yml).

Positive-only discipline (I1): the manifest lists candidate systems considered
(a positive statement) and aggregate counts. It never records per-system
negative judgments - exclusion reasons stay aggregate.

Usage:
  python collectors/frontier_manifest.py --input scan.json [--date YYYY-MM-DD]

Input JSON shape:
  {
    "method": "how the scan was performed",
    "sources": ["github-api", "hf-trending", ...],
    "examined_estimate": 400,          # aggregate pool size looked at
    "candidates": [ {"repo": "org/name", "cohort": "slug", "stars": 123,
                     "axes_observed": "github", "note": "..."}, ... ],
    "retro_note": "optional free-text for irrecoverable prior scans"
  }
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    args = sys.argv[1:]
    if "--input" not in args:
        print(__doc__)
        return 2
    src = Path(args[args.index("--input") + 1])
    date = (args[args.index("--date") + 1] if "--date" in args
            else datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    scan = json.loads(src.read_text())

    out_dir = REPO / "data" / "observations" / date
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "discovery-frontier.json"
    if out.exists():
        print(f"frontier_manifest: {out.relative_to(REPO)} already exists (append-only day; "
              "use a new date or extend the batch input)")
        return 1

    manifest = {
        "v": "frontier_1",
        "date": date,
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": scan["method"],
        "sources": scan.get("sources", []),
        "examined_estimate": scan.get("examined_estimate"),
        "candidates_returned": len(scan.get("candidates", [])),
        "candidates": scan.get("candidates", []),
        **({"retro_note": scan["retro_note"]} if scan.get("retro_note") else {}),
        "note": "Discovery-frontier denominator (un-backfillable). Candidates are systems "
                "CONSIDERED at scan time, not judgments; admission happens via a paired "
                "seeds.json change (CI enforces the pairing). Positive-only: no per-system "
                "negatives are recorded.",
    }
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"frontier_manifest: {manifest['candidates_returned']} candidates -> {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
