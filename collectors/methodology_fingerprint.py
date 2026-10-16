"""Print the SHA256 of a methodology's canonical UTF-8 JSON specification."""
import argparse
import hashlib
import json
from pathlib import Path

SPEC = Path(__file__).resolve().parent.parent / "methodology/m3.json"
M4_SPEC = SPEC.with_name("m4.json")
M5_SPEC = SPEC.with_name("m5.json")
SPECS = {"m3": SPEC, "m4": M4_SPEC, "m5": M5_SPEC}


def fingerprint(path: Path | str = SPEC) -> str:
    if isinstance(path, str):
        path = SPECS.get(path, Path(path))
    canonical = json.dumps(json.loads(path.read_text(encoding="utf-8")), sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=None,
                        help="m3 (default), m4, m5, or a path to a methodology JSON file")
    arg = parser.parse_args().path
    print(fingerprint(arg or "m3"))


if __name__ == "__main__":
    main()
