"""gh_auth - one source of GitHub credentials for the collection path.

Why: the built-in Actions GITHUB_TOKEN allows ~1,000 REST requests/hour/repo,
and the 5,939-system weekly snapshot needs an order of magnitude more (the
2026-09-26 run died on the first 403). A GitHub App installation token carries
its own, larger budget.

Behaviour:
  * env COLLECT_APP_ID + COLLECT_APP_KEY (PEM text) set -> "app" mode: mint an
    RS256 JWT with the `openssl` CLI (the key is written to a 0600 temp file and
    deleted right after signing), find the installation for org
    COLLECT_APP_ORG (default "evidaxis") via GET /app/installations, create an
    installation token (POST /app/installations/{id}/access_tokens), cache it and
    refresh it when fewer than 10 minutes remain (tokens live one hour);
  * otherwise fall back to env GITHUB_TOKEN ("token" mode), or nothing.

`auth_header()` is what every GitHub request uses. Token and key material are
never logged, printed or written anywhere except the short-lived key file.

Pure standard library + the `openssl` CLI (present on GitHub-hosted runners).
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

API = "https://api.github.com"
USER_AGENT = "evidaxis-collect/2.0"
REFRESH_MARGIN_S = 600          # refresh the installation token when < 10 min remain
JWT_LIFETIME_S = 540            # GitHub caps App JWTs at 10 minutes
JWT_BACKDATE_S = 60             # tolerate clock drift between runner and GitHub


class AuthError(RuntimeError):
    """App authentication failed. Messages never carry token or key material."""


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _normalize_pem(pem: str) -> str:
    pem = pem.strip()
    # A PEM pasted into a secret as one line with literal "\n" escapes.
    if "\\n" in pem and "\n" not in pem:
        pem = pem.replace("\\n", "\n")
    return pem + "\n"


def make_jwt(app_id: str, pem: str, now: float | None = None,
             run: Callable[..., Any] = subprocess.run) -> str:
    """RS256 App JWT, signed by `openssl dgst -sha256 -sign <0600 temp key>`."""
    issued = int(time.time() if now is None else now)
    app_id = str(app_id).strip()
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "iat": issued - JWT_BACKDATE_S,
        "exp": issued + JWT_LIFETIME_S,
        "iss": int(app_id) if app_id.isdigit() else app_id,   # numeric App ID or a Client ID
    }
    signing_input = (_b64url(json.dumps(header, separators=(",", ":")).encode())
                     + "." + _b64url(json.dumps(claims, separators=(",", ":")).encode()))
    fd, key_path = tempfile.mkstemp(prefix="evx-app-", suffix=".pem")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(_normalize_pem(pem))
        proc = run(["openssl", "dgst", "-sha256", "-sign", key_path],
                   input=signing_input.encode("ascii"), capture_output=True, check=False)
    finally:
        try:
            os.unlink(key_path)
        except FileNotFoundError:
            pass
    if proc.returncode != 0 or not proc.stdout:
        raise AuthError(f"openssl could not sign the App JWT (exit {proc.returncode}); "
                        "check that COLLECT_APP_KEY holds the App's PEM private key")
    return signing_input + "." + _b64url(proc.stdout)


def _http(method: str, url: str, headers: dict[str, str], data: bytes | None = None,
          tries: int = 4, sleep: Callable[[float], None] = time.sleep) -> tuple[int, bytes]:
    """Small request helper for the App endpoints (JWT-authenticated, own limits)."""
    last = 0
    for attempt in range(tries):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.getcode(), resp.read()
        except urllib.error.HTTPError as exc:
            last = exc.code
            if exc.code >= 500 and attempt < tries - 1:
                sleep(2 ** attempt)
                continue
            return exc.code, b""
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt < tries - 1:
                sleep(2 ** attempt)
                continue
            raise AuthError(f"GitHub App endpoint unreachable: {method} {url}") from None
    return last, b""


def _parse_expiry(value: Any, fallback: float) -> float:
    try:
        return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return fallback


class TokenProvider:
    def __init__(self, env: dict[str, str] | None = None,
                 now: Callable[[], float] = time.time,
                 http: Callable[..., tuple[int, bytes]] = _http,
                 signer: Callable[..., str] = make_jwt) -> None:
        env = dict(os.environ) if env is None else env
        self.app_id = (env.get("COLLECT_APP_ID") or "").strip()
        self._app_key = env.get("COLLECT_APP_KEY") or ""
        self.org = (env.get("COLLECT_APP_ORG") or "evidaxis").strip().lower()
        self._fallback = (env.get("GITHUB_TOKEN") or "").strip()
        self._now = now
        self._http = http
        self._signer = signer
        self._token: str | None = None
        self._expires_at = 0.0
        self.installation_id: int | None = None
        self.mints = 0

    @property
    def mode(self) -> str:
        if self.app_id and self._app_key.strip():
            return "app"
        return "token" if self._fallback else "anonymous"

    def token(self) -> str | None:
        if self.mode != "app":
            return self._fallback or None
        if self._token is None or self._expires_at - self._now() < REFRESH_MARGIN_S:
            self._mint()
        return self._token

    def auth_header(self) -> dict[str, str]:
        tok = self.token()
        return {"Authorization": f"Bearer {tok}"} if tok else {}

    def invalidate(self) -> bool:
        """Drop the cached App token (after a 401). True if a fresh one can be minted."""
        if self.mode != "app":
            return False
        self._token = None
        self._expires_at = 0.0
        return True

    def seconds_left(self) -> float | None:
        return None if self._token is None else self._expires_at - self._now()

    def _jwt_headers(self) -> dict[str, str]:
        jwt = self._signer(self.app_id, self._app_key, now=self._now())
        return {"Authorization": f"Bearer {jwt}", "Accept": "application/vnd.github+json",
                "User-Agent": USER_AGENT, "X-GitHub-Api-Version": "2022-11-28"}

    def _find_installation(self, headers: dict[str, str]) -> int:
        status, body = self._http("GET", f"{API}/app/installations?per_page=100", headers)
        if status != 200:
            raise AuthError(f"GET /app/installations answered HTTP {status} (App ID or key wrong?)")
        installs = json.loads(body.decode() or "[]")
        for inst in installs:
            login = str((inst.get("account") or {}).get("login") or "").lower()
            if login == self.org:
                return int(inst["id"])
        raise AuthError(f"the GitHub App has no installation on org '{self.org}' "
                        f"({len(installs)} installation(s) visible)")

    def _mint(self) -> None:
        headers = self._jwt_headers()
        if self.installation_id is None:
            self.installation_id = self._find_installation(headers)
        status, body = self._http("POST", f"{API}/app/installations/{self.installation_id}/access_tokens",
                                  headers, data=b"")
        if status != 201 and status != 200:
            raise AuthError(f"creating the installation token answered HTTP {status}")
        payload = json.loads(body.decode())
        token = payload.get("token")
        if not token:
            raise AuthError("installation token response carried no token")
        now = self._now()
        self._token = token
        self._expires_at = _parse_expiry(payload.get("expires_at"), now + 3600)
        self.mints += 1
        print(f"[gh_auth] GitHub App installation token minted (#{self.mints}, "
              f"valid {int((self._expires_at - now) / 60)} min)", flush=True)


_PROVIDER: TokenProvider | None = None


def provider() -> TokenProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = TokenProvider()
    return _PROVIDER


def reset(new: TokenProvider | None = None) -> None:
    """Replace the process-wide provider (tests; re-reading the environment)."""
    global _PROVIDER
    _PROVIDER = new


def mode() -> str:
    return provider().mode


def token() -> str | None:
    return provider().token()


def auth_header() -> dict[str, str]:
    return provider().auth_header()


def invalidate() -> bool:
    return provider().invalidate()
