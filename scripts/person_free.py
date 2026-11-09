"""Person-free handle matching for the Hugging Face publication mirror.

Same rules as web/src/lib/personFree.mjs: a GitHub login counts when it appears
as a path or slug prefix (``handle/``), as an ``@mention``, or as a standalone
word when it is distinctive (4+ characters and not only digits). Short or
all-digit handles count only in an explicit GitHub context (``github.com/`` or
``repos/``).
"""
from __future__ import annotations

import json
import hashlib
import math
import secrets
from functools import lru_cache
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

SLUG = re.compile(r"(?<![a-z0-9_.-])([a-z0-9][a-z0-9-]{0,38})(?=/)")
MENTION = re.compile(r"(?<![a-z0-9_.-])@([a-z0-9][a-z0-9-]{0,38})(?![a-z0-9-])")
WORD = re.compile(r"[a-z0-9]+(?:-+[a-z0-9]+)*")
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
    context_only: frozenset[str] = frozenset()
    max_word_length: int = 0


@lru_cache(maxsize=1)
def template_words() -> frozenset[str]:
    # Source vocabulary, never registry data: template words need GitHub context.
    root = Path(__file__).resolve().parents[1] / "web" / "src"
    return frozenset(token for path in root.rglob("*")
                     if path.suffix in {".astro", ".ts"} and ".test." not in path.name
                     for token in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", path.read_text().lower()))


def build_handle_index(handles, template_vocabulary=None) -> HandleIndex:
    vocabulary = template_words() if template_vocabulary is None else set(template_vocabulary)
    all_handles: set[str] = set()
    words: set[str] = set()
    context_only: set[str] = set()
    for handle in handles:
        key = str(handle or "").strip().lower()
        if not key:
            continue
        all_handles.add(key)
        # Rule f exempts distinctive template words, not exact short field values.
        if len(key) >= 4 and not key.isdigit():
            (context_only if key in vocabulary else words).add(key)
    return HandleIndex(frozenset(all_handles), frozenset(words), frozenset(context_only),
                       max(map(len, words), default=0))


def handle_hits(text: str, index: HandleIndex) -> list[str]:
    lower = str(text).lower()
    hits: list[str] = []
    seen: set[str] = set()
    max_length = index.max_word_length

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
        # Rule g: hyphens delimit tokens but may also belong to a login.
        parts = match.group(0).split('-')
        for start in range(len(parts)):
            token = ''
            for end in range(start, len(parts)):
                token += ('-' if end > start else '') + parts[end]
                if len(token) > max_length:
                    break
                if token in index.words:
                    add(token)
    for pattern in (GH_PROFILE, GH_PAGES, GH_RAW):
        for match in pattern.finditer(lower):
            if match.group(1) in index.all:
                add(match.group(1))
    return hits


def reveals_handle(text: str | None, index: HandleIndex, classified=None) -> bool:
    if not text:
        return False
    # A whole value equal to a handle reveals it, short or all-digit ones included.
    decoded = lenient_decoded(str(text))
    if decoded.strip().lower() in index.all - index.context_only:
        return True
    return bool(handle_hits(text, index) or handle_hits(decoded, index)
                or (classified and stale_slug_hits(decoded.lower(), classified.stale_paths,
                                                  classified.canonical_paths)))


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


def decimal_entities_decoded(text: str) -> str:
    # Match check-dist's Number/FromCharCode coercion even outside Unicode's range.
    def decode(match):
        value = float(match[1])
        return chr(int(value) & 0xFFFF) if math.isfinite(value) else "\0"
    return re.sub(r"&#([0-9]+);", decode, text)


def neutral_name(entity_id: str) -> str:
    return f"System {entity_id}"


def public_package_label(system: str, package: str, index: HandleIndex) -> str:
    if reveals_handle(system, index) or reveals_handle(package, index):
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


@dataclass(frozen=True)
class RegistryClassification:
    handles: frozenset[str]
    organizations: frozenset[str]
    stale_paths: frozenset[str]
    personal_paths: frozenset[str]
    canonical_paths: frozenset[str]
    public_repos: frozenset[str]


def classify_registry(registry: dict, accounts=(), floor=()) -> RegistryClassification:
    """Rules a-e. Inputs and outputs stay in memory; no identifier store is written."""
    projects = {str(owner).lower() for owner in accounts}
    entries = [(stored, entry) for stored, entry in registry.items()
               if isinstance(entry, dict) and isinstance(entry.get("full_name"), str)]
    organizations = {entry["full_name"].split("/")[0].lower() for _, entry in entries
                     if entry.get("owner_type") == "Organization"} | projects
    handles = {str(owner).strip().lower() for owner in floor if owner}
    for stored, entry in entries:
        current = entry["full_name"].split("/")[0].lower()
        former = stored.split("/")[0].lower()
        if entry.get("owner_type") == "User":
            handles.add(current)
        if former != current:
            handles.add(former)
    handles -= organizations
    stale, personal, canonical, public = set(), set(), set(), set()
    for stored, entry in entries:
        path = entry["full_name"].lower()
        current, former = path.split("/")[0], stored.split("/")[0].lower()
        if current in organizations:
            public.add(stored)
            canonical.add(path)
        if current in handles:
            personal.add(path)
            personal.add(stored.lower())
        if former != current and (former in handles or current in handles):
            stale.add(stored.lower())
            personal.add(stored.lower())
    return RegistryClassification(*(frozenset(s) for s in
        (handles, organizations, stale, personal, canonical, public)))


def load_classification(repo: Path, *, project_accounts: bool = True) -> RegistryClassification:
    floor = json.loads((repo / "web/src/data/person-free-handles.json").read_text(encoding="utf-8"))
    accounts = load_project_accounts(repo) if project_accounts else {}
    # A project account stays public even after its last tracked repository moves.
    return classify_registry(load_owner_types(repo, project_accounts=False), accounts, floor)


def load_handle_index(repo: Path, *, project_accounts: bool = True) -> tuple[HandleIndex, tuple[str, ...]]:
    classified = load_classification(repo, project_accounts=project_accounts)
    return build_handle_index(classified.handles), tuple(sorted(classified.stale_paths))


def stale_slug_hits(text, stale_paths, canonical_paths):
    hits = []
    for slug in stale_paths:
        start = text.find(slug)
        if start < 0:
            continue
        exemptions = [(path, offset) for path in canonical_paths
                      for offset in range(len(path)) if path.startswith(slug, offset)]
        while start >= 0:
            if not any(start >= offset and text.startswith(path, start - offset)
                       for path, offset in exemptions):
                hits.append(slug)
                break
            start = text.find(slug, start + 1)
    return hits


_DIAGNOSTIC_SALT = secrets.token_bytes(32)


def diagnostic(path: str, rule: str, value: str, index=None, classified=None) -> str:
    digest = lambda text: hashlib.sha256(_DIAGNOSTIC_SALT + b"\0" + text.lower().encode()).hexdigest()[:8]
    if (index and reveals_handle(path, index, classified)) or (rule == 'd' and value.lower() in lenient_decoded(path).lower()):
        path = f"[path:{digest(path)}]"
    return f"{path}: rule={rule} hash={digest(value)}"


def safe_homepage(homepage, stored, entry, classified, index):
    if not homepage:
        return None
    if stored in classified.public_repos and is_github_url(homepage):
        return None if reveals_handle(entry['full_name'], index, classified) else f"https://github.com/{entry['full_name']}"
    if not is_valid_url(homepage) or reveals_handle(homepage, index):
        return None
    decoded = lenient_decoded(homepage).lower()
    owners = {stored.split('/')[0].lower(), entry['full_name'].split('/')[0].lower()}
    # Rule f's prose exemption does not apply to the known owner's own homepage.
    if any(owner in decoded for owner in owners & index.all):
        return None
    if stored not in classified.public_repos and (is_github_url(homepage) or is_github_url(decoded)):
        return None
    if stale_slug_hits(decoded, classified.stale_paths, classified.canonical_paths):
        return None
    return homepage


def classification_for(github_repo: str, registry: dict) -> dict:
    entry = registry.get(github_repo)
    if not _valid_entry(entry):
        raise ValueError(diagnostic("registry", "classification", github_repo))
    return entry
