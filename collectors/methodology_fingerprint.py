"""Print the SHA256 of a methodology's canonical UTF-8 JSON specification."""
import argparse
import hashlib
import json
from pathlib import Path

SPEC = Path(__file__).resolve().parent.parent / "methodology/m3.json"


def fingerprint(path: Path = SPEC) -> str:
    canonical = json.dumps(json.loads(path.read_text(encoding="utf-8")), sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=SPEC)
    print(fingerprint(parser.parse_args().path))


if __name__ == "__main__":
    main()
