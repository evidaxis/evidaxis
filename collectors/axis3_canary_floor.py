"""Rule-first confirmation of the unchanged 0.80 cohort canary floor."""
from __future__ import annotations

import json
import math
from pathlib import Path

BASELINE = Path(__file__).resolve().parent.parent / "data/quarantine/axis3-deps-v2/eval/v2h1-baseline-2026-07-21-0c0af7876879.json"
FLOOR = 0.80


def confirmation(path: Path = BASELINE) -> dict:
    stats = json.loads(path.read_text())["canary"]
    cohort, row = min(((c, r) for c, r in stats.items() if r["n"] >= 3),
                      key=lambda item: (item[1]["agreement"], item[0]))
    p, n = row["agreement"], row["n"]
    error = math.sqrt(p * (1 - p) / n)
    return {"cohort": cohort, "p": p, "n": n, "standard_error": error,
            "lower": p - error, "floor": FLOOR, "confirmed": p - error >= FLOOR}


def main() -> int:
    result = confirmation()
    print(f"{result['cohort']}: p = {result['p']}, n = {result['n']}")
    print(f"{result['p']} - sqrt({result['p']} * (1 - {result['p']}) / {result['n']})"
          f" = {result['p']} - {result['standard_error']:.9f} = {result['lower']:.9f}")
    print(f"{'CONFIRM' if result['confirmed'] else 'NOT CONFIRMED'} floor 0.80 (lower >= 0.80)")
    return 0 if result["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
