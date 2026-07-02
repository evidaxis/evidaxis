"""openalex_keyed_fetch - STAGED forward fetch-layer hardening for axis-2.

Why: OpenAlex retired the polite pool / mailto parameter on 2026-02-13 and now
requires an API key (free tier: 100,000 credits/day; keyless: ~100 credits,
then HTTP 409). The frozen collector (etl/collect.py) still appends the dead
mailto param and, on failure, silently degrades axis-2 to 'absent' - a
silent-series-rot class defect: today's 14 calls/run squeeze under the demo
allowance, but any coverage expansion crosses the cliff without an alarm.

What this wrapper does (fetch layer ONLY; scoring semantics untouched):
  * rewrites api.openalex.org URLs: strips the dead `mailto=` param, appends
    `api_key=` from env OPENALEX_API_KEY (or a gitignored etl/.env);
  * HARD-FAILS (exit 3) on HTTP 409 credit exhaustion for OpenAlex calls -
    a loud [THREAT] instead of a silent axis-2 'absent';
  * without a key, request URLs stay byte-identical (keyless demo allowance)
    plus a loud warning; the 409 hard-fail above still applies keyless too;
  * delegates every non-OpenAlex URL to the frozen collector's own fetcher.

STATUS: WIRED (2026-07-02). The weekly workflow's collect step runs this
wrapper; OPENALEX_API_KEY lives in repo secrets and the keeper's gitignored
etl/.env. The m-version is NOT bumped: transport is not methodology - the
frozen collector, the formula fingerprint, and every published number are
untouched (recorded in METHODOLOGY-VERSIONING.md operational notes).

Pure standard library. etl/collect.py is never edited (byte-frozen).
"""
import os
import re
import sys
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "etl"))

import collect  # the frozen collector, imported, never edited

_ORIG_GET_JSON = collect._get_json
_WARNED = False


def _mask(url: str) -> str:
    """Never let the api_key reach logs."""
    return re.sub(r"api_key=[^&]+", "api_key=***", url)


def _load_key() -> str:
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if key:
        return key
    env = REPO / "etl" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            m = re.match(r"\s*OPENALEX_API_KEY\s*=\s*(\S+)", line)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    return ""


def _rewrite(url: str, key: str) -> str:
    base, _, query = url.partition("?")
    params = [p for p in query.split("&") if p and not p.startswith("mailto=")]
    params.append(f"api_key={key}")
    return base + "?" + "&".join(params)


def _get_json_keyed(url, headers=None, tries=5):
    global _WARNED
    if "api.openalex.org" not in url:
        return _ORIG_GET_JSON(url, headers=headers, tries=tries)

    key = _load_key()
    if key:
        url = _rewrite(url, key)
    elif not _WARNED:
        _WARNED = True
        print("WARNING: OPENALEX_API_KEY not set - running on the keyless demo "
              "allowance (~100 credits, then HTTP 409). Get a free key at "
              "https://openalex.org/settings/api-key and put it in etl/.env")

    # Own request path for OpenAlex so a 409 can NEVER be swallowed into a
    # silent axis-2 'absent' (the frozen fetcher's generic retry would).
    import json as _json
    import time as _time
    import urllib.request as _rq
    for _ in range(tries):
        try:
            req = _rq.Request(url, headers=headers or {"User-Agent": "evidaxis-collect/2.0"})
            with _rq.urlopen(req, timeout=40) as r:
                return _json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 409:
                print("[THREAT] OpenAlex HTTP 409: API credits exhausted. "
                      "Axis-2 input is UNAVAILABLE - refusing to publish a "
                      "silently degraded snapshot. Provide/upgrade "
                      "OPENALEX_API_KEY and re-run.")
                raise SystemExit(3) from None
            if e.code in (403, 429):
                print(f"  rate-limit {e.code} on {_mask(url)[:70]}")
                return "RATELIMIT"
            if e.code == 404:
                return None
            _time.sleep(1.0)
        except Exception as ex:  # mirror the frozen fetcher's resilience
            print(f"  err {type(ex).__name__} {_mask(url)[:70]}")
            _time.sleep(1.0)
    return None


def main() -> int:
    collect._get_json = _get_json_keyed
    return collect.main() or 0


if __name__ == "__main__":
    sys.exit(main())
