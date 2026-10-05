"""Person-free handle matching for the Hugging Face publication mirror.

Same rules as web/src/lib/personFree.mjs: a GitHub login counts when it appears
as a path or slug prefix (``handle/``), as an ``@mention``, or as a standalone
word when it is distinctive (4+ characters and not only digits). Short or
all-digit handles count only in an explicit GitHub context (``github.com/`` or
``repos/``).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

SLUG = re.compile(r"(?<![a-z0-9_.-])([a-z0-9][a-z0-9-]{0,38})(?=/)")
MENTION = re.compile(r"(?<![a-z0-9_.-])@([a-z0-9][a-z0-9-]{0,38})(?![a-z0-9-])")
WORD = re.compile(r"(?<![a-z0-9-])[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?![a-z0-9-])")
GITHUB_CONTEXT = re.compile(r"(?:github\.com/|repos/)$")
# Explicit GitHub contexts count ANY handle, whatever its length (review 2026-10-04):
# a profile URL without a trailing slash, a Pages host, a raw-content path.
GH_PROFILE = re.compile(r"github\.com/([a-z0-9][a-z0-9-]{0,38})(?![a-z0-9-])")
GH_PAGES = re.compile(r"(?<![a-z0-9-])([a-z0-9][a-z0-9-]{0,38})\.github\.io(?![a-z0-9-])")
GH_RAW = re.compile(r"githubusercontent\.com/([a-z0-9][a-z0-9-]{0,38})/")
_FULL_NAME = re.compile(r"^[^/]+/[^/]+$")
_BAD_PERCENT = re.compile(r"%(?![0-9A-Fa-f]{2})")
_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z+\-.]*:")

# Free-text fields the site does not publish once they reveal a handle.
# `note` is omitted from the public entity JSON; a revealing value is dropped.
FREE_TEXT_KEYS = frozenset({"note", "proxy", "description", "summary"})


@dataclass(frozen=True)
class HandleIndex:
    all: frozenset[str]
    words: frozenset[str]


def build_handle_index(handles) -> HandleIndex:
    all_handles: set[str] = set()
    words: set[str] = set()
    for handle in handles:
        key = str(handle or "").strip().lower()
        if not key:
            continue
        all_handles.add(key)
        if len(key) >= 4 and not key.isdigit():
            words.add(key)
    return HandleIndex(frozenset(all_handles), frozenset(words))


def handle_hits(text: str, index: HandleIndex) -> list[str]:
    lower = str(text).lower()
    hits: list[str] = []
    seen: set[str] = set()

    def add(handle: str) -> None:
        if handle not in seen:
            seen.add(handle)
            hits.append(handle)

    for match in SLUG.finditer(lower):
        handle = match.group(1)
        if handle not in index.all:
            continue
        context = lower[max(0, match.start() - 11):match.start()]
        if handle in index.words or GITHUB_CONTEXT.search(context):
            add(handle)
    for match in MENTION.finditer(lower):
        handle = match.group(1)
        if handle in index.all:
            add(handle)
    for match in WORD.finditer(lower):
        token = match.group(0)
        if token in index.words:
            add(token)
    for pattern in (GH_PROFILE, GH_PAGES, GH_RAW):
        for match in pattern.finditer(lower):
            if match.group(1) in index.all:
                add(match.group(1))
    return hits


def reveals_handle(text: str | None, index: HandleIndex) -> bool:
    if not text:
        return False
    # A whole value equal to a handle reveals it, short or all-digit ones included.
    if str(text).strip().lower() in index.all:
        return True
    return bool(handle_hits(text, index))


def lenient_decoded(text: str) -> str:
    """Percent-decode until stable (at most 3 rounds); malformed sequences stay as is.
    Used by the publication guard so github.com%2Fhandle%2Frepo cannot hide a handle."""
    out = text
    for _ in range(3):
        nxt = unquote(out)
        if nxt == out:
            break
        out = nxt
    return out


def neutral_name(entity_id: str) -> str:
    return f"System {entity_id}"


def public_package_label(system: str, package: str, index: HandleIndex) -> str:
    if reveals_handle(package, index):
        return "package not shown"
    return f"{system}/{package}"


def _decode_uri_component(value: str) -> str:
    if _BAD_PERCENT.search(value):
        raise ValueError("malformed percent-encoding")
    return unquote(value)


def fully_decoded(value: str) -> str:
    out = value
    for _ in range(3):
        try:
            nxt = _decode_uri_component(out)
        except ValueError:
            break
        if nxt == out:
            break
        out = nxt
    return out.lower()


def is_valid_url(value: str) -> bool:
    if not isinstance(value, str) or not _SCHEME.match(value):
        return False
    try:
        parts = urlsplit(value)
    except ValueError:
        return False
    return bool(parts.netloc)


def is_github_url(value: str) -> bool:
    if not is_valid_url(value):
        return False
    host = (urlsplit(value).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host == "github.com"


def safe_user_homepage(homepage: str | None, owner: "str | tuple[str, ...]") -> str | None:
    """web/src/lib/person_free.ts safeUserHomepage. Invalid URLs and any GitHub
    URL (including a percent-encoded one) are dropped, as is a URL whose decoded
    form contains that entity's owner handle."""
    if not homepage:
        return None
    if not is_valid_url(homepage):
        return None
    decoded = fully_decoded(homepage)
    owners = (owner,) if isinstance(owner, str) else tuple(owner)
    if is_github_url(homepage) or is_github_url(decoded) or any(o.lower() in decoded for o in owners if o):
        return None
    return homepage


def _valid_entry(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("owner_type") not in {"Organization", "User"}:
        return False
    repo_id = entry.get("repo_id")
    if isinstance(repo_id, bool) or not isinstance(repo_id, int) or repo_id <= 0:
        return False
    full_name = entry.get("full_name")
    return isinstance(full_name, str) and _FULL_NAME.match(full_name) is not None


def apply_project_accounts(registry: dict, accounts: dict) -> dict:
    """Publish a listed User owner like an Organization. The file on disk stays User.

    Canonical owner is ``full_name`` before ``/``, lower-cased. A missing or empty
    accounts map leaves the registry unchanged. Already-Organization entries stay
    as they are, even when the handle is listed.
    """
    if not isinstance(registry, dict) or not isinstance(accounts, dict):
        return registry
    for key, entry in list(registry.items()):
        if not isinstance(entry, dict) or entry.get("owner_type") != "User":
            continue
        full_name = entry.get("full_name")
        if not isinstance(full_name, str) or "/" not in full_name:
            continue
        owner = full_name.split("/", 1)[0].lower()
        if not owner or owner not in accounts:
            continue
        registry[key] = {
            **entry,
            "owner_type": "Organization",
            "github_owner_type": "User",
            "publication_basis": "project_account",
        }
    return registry


def load_project_accounts(repo: Path) -> dict:
    path = repo / "etl" / "project_accounts.json"
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    accounts = document.get("accounts") if isinstance(document, dict) else None
    return accounts if isinstance(accounts, dict) else {}


def load_owner_types(repo: Path, *, project_accounts: bool = True) -> dict:
    """project_accounts=False is the strict projection (every User owner masked), used for a
    deposit that cannot be withdrawn until the project-account decision is re-checked."""
    registry = json.loads((repo / "etl" / "owner_types.json").read_text(encoding="utf-8"))["repos"]
    return apply_project_accounts(registry, load_project_accounts(repo)) if project_accounts else registry


def load_handle_index(repo: Path, *, project_accounts: bool = True) -> tuple[HandleIndex, tuple[str, ...]]:
    """Floor list plus every User owner: stored slug and canonical full_name owner.

    A stored slug whose login is an Organization today is not a personal handle
    (the site matches that case only as the exact stale ``owner/repo`` path).
    Canonical User owners stay in the handle index either way.
    """
    floor = json.loads((repo / "web" / "src" / "data" / "person-free-handles.json").read_text(encoding="utf-8"))
    registry = load_owner_types(repo, project_accounts=project_accounts)
    org_owners: set[str] = set()
    for stored, entry in registry.items():
        if isinstance(entry, dict) and entry.get("owner_type") == "Organization":
            full_name = entry.get("full_name") or stored
            org_owners.add(str(full_name).split("/")[0].lower())
    handles = list(floor)
    stale: list[str] = []
    for stored, entry in registry.items():
        if not isinstance(entry, dict):
            continue
        full_name = str(entry.get("full_name") or stored)
        # Same rule as web/scripts/check-dist.mjs: only an owner change leaves a
        # stale owner/repo path. A rename under the same owner must not match as
        # a prefix of the canonical path.
        if stored.split("/")[0].lower() != full_name.split("/")[0].lower():
            stale.append(stored.lower())
        if entry.get("owner_type") != "User":
            continue
        handles.append(full_name.split("/")[0])
        stored_owner = stored.split("/")[0]
        if stored_owner.lower() not in org_owners:
            handles.append(stored_owner)
    return build_handle_index(handles), tuple(stale)


def classification_for(github_repo: str, registry: dict) -> dict:
    entry = registry.get(github_repo)
    if not _valid_entry(entry):
        raise ValueError(f"repository publication classification is unavailable for {github_repo}")
    return entry
