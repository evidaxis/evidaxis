#!/usr/bin/env python3
"""Field policy — person-free enforcement for the Type-2 archive (artifact #1).

cons-03 (2026-07-01) hard rule: person-free must be CI-ENFORCED, not merely claimed.
Raw upstream responses (e.g. GitHub /repos) embed an `owner` user object with login,
avatar_url, html_url etc. — personal data under UK GDPR for individually-owned repos.
It must never land in the public CC0 archive.

Two guards:
  1. WHITELIST (default-deny): only known system-level repo fields are persisted to
     public provenance. `filter_provenance` builds the person-free view.
  2. BLOCKLIST scan: `scan_person_fields` recursively flags any residual person key;
     the CI gate (tests/test_field_policy.py) fails the build if it finds any.

The full upstream body is NEVER stored publicly; its sha256 (in observations.jsonl)
preserves integrity/priority without retaining the personal data.
"""
from __future__ import annotations

# Only these top-level repo fields are persisted to public provenance (default-deny).
PROVENANCE_ALLOWLIST = frozenset({
    "id", "node_id", "name", "full_name", "private", "fork",
    "created_at", "updated_at", "pushed_at", "size",
    "stargazers_count", "watchers_count", "forks_count", "network_count",
    "subscribers_count", "open_issues_count",
    "language", "default_branch", "topics", "homepage", "description",
    "archived", "disabled", "visibility",
})

# Keys that indicate PERSON data — must never appear in stored provenance.
PERSON_KEY_BLOCKLIST = frozenset({
    "login", "avatar_url", "gravatar_id", "email", "user_view_type",
    "followers_url", "following_url", "gists_url", "starred_url",
    "subscriptions_url", "organizations_url", "received_events_url",
    "owner", "organization", "author", "committer", "maintainer",
})


def filter_provenance(raw: dict) -> dict:
    """Return the person-free system-level view of a raw GitHub /repos response."""
    out = {k: raw[k] for k in PROVENANCE_ALLOWLIST if k in raw}
    # keep the owner CLASSIFICATION (Organization/User) but not the identity
    owner = raw.get("owner") or {}
    if owner.get("type"):
        out["owner_type"] = owner["type"]
    # keep license spdx id only (an object, but non-personal)
    lic = raw.get("license") or {}
    if lic.get("spdx_id"):
        out["license_spdx_id"] = lic["spdx_id"]
    out["_note"] = "person-free filtered; response_sha256 (in observations.jsonl) is of the full upstream body"
    return out


def scan_person_fields(obj, path: str = "") -> list[str]:
    """Recursively flag any key in PERSON_KEY_BLOCKLIST. Returns list of json-paths."""
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = f"{path}.{k}" if path else k
            if k in PERSON_KEY_BLOCKLIST:
                hits.append(here)
            hits.extend(scan_person_fields(v, here))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(scan_person_fields(v, f"{path}[{i}]"))
    return hits
