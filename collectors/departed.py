#!/usr/bin/env python3
"""Record reviewed preflight departures without changing seeds or old journals."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from universe_integrity import REPO, departure_repos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="preflight.json report")
    args = parser.parse_args()
    report = json.loads(args.input.read_text())
    payload = {"schema_version": "departed_1", "date": report["date"],
               "recorded_at": datetime.now(timezone.utc).isoformat(), "departed": report["departed"]}
    departure_repos(payload, report["date"])
    path = REPO / "data/observations" / report["date"] / "departed.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents an unrelated removal from rewriting prior evidence.
    with path.open("x") as out:
        out.write(json.dumps(payload, indent=2) + "\n")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
