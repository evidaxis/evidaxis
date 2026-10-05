"""Publish a staged quarterly package as a new version of the Evidaxis Zenodo record.

Stage first: python3 scripts/zenodo_quarterly_stage.py --date <D> --out <DIR>
Then:        ZENODO_EVIDAXIS_TOKEN=... python3 scripts/zenodo_publish_version.py --out <DIR> [--publish]

Without --publish the script creates (or reuses) the new-version draft, replaces its files,
writes the metadata and stops: the draft can be previewed on Zenodo. With --publish it also
publishes, which mints a DOI that cannot be withdrawn. The token must belong to the Evidaxis
account that owns the record; the script refuses another owner (CONSTITUTION.md, invariant 1).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.zenodo_quarterly_stage import check_metadata  # noqa: E402

API = "https://zenodo.org/api"
LATEST_RECORD = 21307528        # version 2026-07-11 under concept 21076011
EVIDAXIS_OWNER = 1707593        # owner id of every Evidaxis record


def call(method: str, url: str, token: str, body: bytes | None = None, ctype: str = "application/json") -> dict:
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Zenodo {method} {url}: HTTP {exc.code} {exc.read()[:300]!r}") from None
    return json.loads(raw) if raw else {}


def owner_of(record: dict) -> int | None:
    owners = record.get("owners") or []
    first = owners[0] if owners else None
    return int(first["id"]) if isinstance(first, dict) else (int(first) if first is not None else None)


def run(out: Path, token: str, publish: bool) -> int:
    archive = next(out.glob("evidaxis-snapshot-*-deposit.zip"), None)
    meta_path = out / "zenodo-metadata.json"
    if archive is None or not meta_path.is_file():
        raise SystemExit(f"no staged package in {out} (run zenodo_quarterly_stage.py first)")
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))["metadata"]
    if check_metadata(metadata):
        raise SystemExit(f"staged metadata names a person: {check_metadata(metadata)}")

    latest = call("GET", f"{API}/deposit/depositions/{LATEST_RECORD}", token)
    if owner_of(latest) != EVIDAXIS_OWNER:
        raise SystemExit(f"token owner {owner_of(latest)} is not the Evidaxis account {EVIDAXIS_OWNER}; refusing")
    draft_url = latest.get("links", {}).get("latest_draft")
    if not draft_url or draft_url.rstrip("/").endswith(str(LATEST_RECORD)):
        draft_url = call("POST", f"{API}/deposit/depositions/{LATEST_RECORD}/actions/newversion", token)["links"]["latest_draft"]
    draft = call("GET", draft_url, token)
    inherited = check_metadata(draft.get("metadata", {}))
    if inherited:
        print(f"inherited draft metadata names a person, replaced below: {inherited}")
    for item in draft.get("files", []):
        call("DELETE", f"{draft_url}/files/{item['id']}", token)
    call("PUT", f"{draft['links']['bucket']}/{archive.name}", token, archive.read_bytes(), "application/octet-stream")
    draft = call("PUT", draft_url, token, json.dumps({"metadata": metadata}).encode("utf-8"))
    if check_metadata(draft.get("metadata", {})):
        raise SystemExit(f"draft metadata still names a person after update: {check_metadata(draft['metadata'])}")
    files = [item.get("filename") for item in call("GET", draft_url, token).get("files", [])]
    if files != [archive.name]:
        raise SystemExit(f"draft files are {files}, expected only {archive.name}")
    print(f"draft ready: {draft['links'].get('html')} files={files}")
    if not publish:
        print("not published (pass --publish after previewing the draft)")
        return 0
    done = call("POST", f"{draft_url}/actions/publish", token)
    print(f"published: doi={done.get('doi')} record={done.get('links', {}).get('record_html') or done.get('links', {}).get('html')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True, help="folder written by zenodo_quarterly_stage.py")
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args(argv)
    token = os.environ.get("ZENODO_EVIDAXIS_TOKEN", "")
    if not token:
        raise SystemExit("ZENODO_EVIDAXIS_TOKEN is not set (a token of the Evidaxis Zenodo account)")
    return run(args.out, token, args.publish)


if __name__ == "__main__":
    sys.exit(main())
