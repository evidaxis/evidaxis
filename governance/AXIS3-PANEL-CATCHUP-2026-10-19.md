# Axis 3 panel catchup, effective partition 2026-10-19

Status: generated from the expansion manifest. Selection read no dependent counts.

## Rule

A registry system outside the current m4 panel contributes a package only when
the root manifest declares the name, deps.dev publishes that name, and the published
metadata does not name another source repository. The root files are package.json,
pyproject.toml, setup.py, Cargo.toml, and go.mod.

verified and no_link are admitted. other_repo and not_admitted are refused.
A published package with no verdict stops the weekly capture.

## Counts

- Systems outside the previous panel: 6252
- Admitted: 2375 (verified 2042, no_link 333)
- Refused: 1079 (other_repo 293, not_admitted 786)
- Roots unreadable: 14
- Private root package.json: 633

Refused by reason:

- metadata names this repository and another: 16
- not published: 764
- same published name declared by more than one system: 6

## What changes, and what does not

The manifest applies to deps.dev partitions dated 2026-10-19 and later.
Partitions before 2026-10-19 keep the previous m4 panel and the previous mapping hash.
Methodology m5 is unchanged. Stored slices are not recomputed.
The fixed self-name exclusion list is unchanged.

## Where the audit is

Linkage audit: data/quarantine/axis3-deps-v2/linkage-audit-2026-10-19.json
Manifest: data/quarantine/axis3-deps-v2/expansion-manifest-2026-10-19.json
Manifest sha256: 15bb0abf7b5ee82f40e47d98c8c679732b2e9af1c6fb8f09f85453b1e56a7f2b
