"""gh_http - the one GitHub request path: auth header, rate-limit waiting, 401 refresh.

Rules (weekly snapshot at 5,939 systems, 2026-09-26):
  * every request carries gh_auth's header (App installation token when configured;
    otherwise the caller's own Authorization header or GITHUB_TOKEN is kept);
  * 403/429 that is a RATE LIMIT -> read Retry-After / X-RateLimit-Remaining /
    X-RateLimit-Reset, sleep (until reset + 5 s, or Retry-After) and retry the SAME
    request; the wait does not consume a caller's try. Raise RateLimited only when
    a single wait would exceed 65 minutes or the same request hit the limit 3 times;
  * a 403 without any rate-limit signal (blocked/forbidden repository) is returned
    as-is: it is a per-repository fact, not a reason to stop the whole collection;
  * 401 -> refresh the App token once and retry.

Counters in STATS feed the progress lines and the run summary (no secrets).
Pure standard library.
"""
from __future__ import annotations

import time
import urllib.error
import urllib.request
from typing import Any

import gh_auth

USER_AGENT = "evidaxis-collect/2.0"
MAX_SINGLE_WAIT_S = 65 * 60
MAX_LIMIT_HITS = 3
RESET_PAD_S = 5
NO_HEADER_WAIT_S = 60           # GitHub: "wait at least one minute" when no header says how long

STATS: dict[str, Any] = {}


def reset_stats() -> None:
    STATS.clear()
    STATS.update({"rest": 0, "graphql": 0, "rate_waits": 0, "rate_wait_s": 0.0,
                  "auth_refreshes": 0, "remaining": None, "limit": None, "reset": None,
                  "started": time.time()})


reset_stats()


class RateLimited(RuntimeError):
    """The rate limit could not be waited out within the allowed bounds."""


def _header(headers: Any, name: str) -> str | None:
    if headers is None:
        return None
    try:
        value = headers.get(name)
    except AttributeError:
        return None
    if value is None and isinstance(headers, dict):
        lowered = name.lower()
        for key, val in headers.items():
            if str(key).lower() == lowered:
                return val
    return value


def _note_budget(headers: Any) -> None:
    for key, name in (("remaining", "X-RateLimit-Remaining"), ("limit", "X-RateLimit-Limit"),
                      ("reset", "X-RateLimit-Reset")):
        value = _header(headers, name)
        if value is not None:
            try:
                STATS[key] = int(value)
            except ValueError:
                pass


def rate_limit_wait(code: int, headers: Any, body_text: str, hit: int, now: float) -> float | None:
    """Seconds to wait before retrying, or None when this 403/429 is not a rate limit."""
    retry_after = _header(headers, "Retry-After")
    if retry_after:
        try:
            return max(1.0, float(retry_after))
        except ValueError:
            pass
    remaining = _header(headers, "X-RateLimit-Remaining")
    reset_at = _header(headers, "X-RateLimit-Reset")
    if remaining is not None and str(remaining).strip() == "0" and reset_at:
        try:
            return max(0.0, float(reset_at) - now) + RESET_PAD_S
        except ValueError:
            pass
    text = (body_text or "").lower()
    if code == 429 or "rate limit" in text or "abuse" in text:
        return float(NO_HEADER_WAIT_S * (2 ** max(0, hit - 1)))
    return None


def _read_error(exc: urllib.error.HTTPError) -> bytes:
    try:
        return exc.read() or b""
    except Exception:
        return b""


def budget_line() -> str:
    reset_at = STATS.get("reset")
    reset_in = f"{max(0, int(reset_at - time.time()))}s" if isinstance(reset_at, int) else "?"
    return (f"rest={STATS['rest']} graphql={STATS['graphql']} rate_remaining={STATS.get('remaining')}"
            f"/{STATS.get('limit')} reset_in={reset_in} rate_waits={STATS['rate_waits']}"
            f" ({int(STATS['rate_wait_s'])}s)")


def request(url: str, *, method: str = "GET", data: bytes | None = None,
            headers: dict[str, str] | None = None, timeout: float = 40,
            kind: str = "rest") -> tuple[int, Any, bytes]:
    """One logical GitHub request -> (status, response headers, body bytes).

    Network exceptions propagate (callers own their try budget). HTTP errors are
    returned as a status, except rate limits (waited out here) and a 401 on an App
    token (refreshed once here).
    """
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    hdrs.update(headers or {})
    hits = 0
    refreshed = False
    while True:
        if gh_auth.mode() == "app" or "Authorization" not in hdrs:
            hdrs.update(gh_auth.auth_header())
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        STATS[kind] = STATS.get(kind, 0) + 1
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", None) or resp.getcode()
                body = resp.read()
                resp_headers = getattr(resp, "headers", None)
            _note_budget(resp_headers)
            return status, resp_headers, body
        except urllib.error.HTTPError as exc:
            resp_headers = exc.headers
            _note_budget(resp_headers)
            body = _read_error(exc)
            if exc.code == 401 and not refreshed and gh_auth.invalidate():
                refreshed = True
                STATS["auth_refreshes"] += 1
                print("  github 401: refreshing the App installation token once", flush=True)
                continue
            if exc.code in (403, 429):
                wait = rate_limit_wait(exc.code, resp_headers, body.decode("utf-8", "replace"),
                                       hits + 1, time.time())
                if wait is not None:
                    hits += 1
                    if wait > MAX_SINGLE_WAIT_S:
                        raise RateLimited(f"rate limit wait of {int(wait)}s exceeds {MAX_SINGLE_WAIT_S}s "
                                          f"({exc.code} on {url[:90]})") from None
                    if hits >= MAX_LIMIT_HITS:
                        raise RateLimited(f"rate limit hit {hits} times on the same request "
                                          f"({exc.code} on {url[:90]})") from None
                    print(f"  rate-limit {exc.code} (hit {hits}): sleeping {int(wait)}s, then retrying "
                          f"{url[:90]} | {budget_line()}", flush=True)
                    STATS["rate_waits"] += 1
                    STATS["rate_wait_s"] += wait
                    time.sleep(wait)
                    continue
            return exc.code, resp_headers, body
