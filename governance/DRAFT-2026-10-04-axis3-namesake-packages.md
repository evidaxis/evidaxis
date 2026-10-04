# DRAFT 2026-10-04: the axis-3 panel admits namesake packages of other repositories

> status: SUPERSEDED 2026-10-04 by `governance/METHODOLOGY-M4-2026-10-04.md` (its option 3 — a paid replay or subtraction — is NOT adopted; history is derived exactly from stored per-package rows or restarts). Original status: DRAFT — finding with a proposed correction; the correction changes the frozen
> panel, so it needs a superseding record, not an erratum · class: identity defect in the
> frozen panel plus a description that overstates it · evidence:
> `data/quarantine/axis3-deps-v2/linkage-audit-2026-10-04.json`. No committed verdict,
> evaluation or published value is rewritten by this draft.

## What the record says

`AXIS3-DEPS-V2H1-SUPERSESSION-2026-07-21.md`, component 5, and the expansion manifest rule:
a package enters the panel when it is "declared-in-own-repo-tree AND outside excluded dirs
AND exists on deps.dev; third-party project-linkage rejected (Sybil guard)".

`methodology/m3.json` and the axis-3 description shown on cards say something stronger:
"unique direct dependents over the union of **linkage-verified** packages".

## What the audit found

"Exists on deps.dev" was checked by name. A name declared in a repository's tree can belong
to an unrelated published package: a private build folder (`build/builtin/package.json`
declares `builtin`), a bundled extension (`extensions/bat`), or a vendored third-party
package. For each of the 614 packages the panel admits, the published package's default
version on deps.dev v3 was read (`relatedProjects` SOURCE_REPO and `links`):

| Verdict | Packages | Meaning |
|---|---:|---|
| verified | 341 | the published package names the declaring repository |
| other_repo | 158 | it names a different repository |
| no_link | 115 | it names no repository |

Systems affected: 26 of the 80 panel systems hold at least one `other_repo` package; in
the 2026-10-03 snapshot that is 15 of the 48 systems with a scored axis 3. Six scored
systems hold no `verified` package at all. The largest case is Void (`e_MX90J81EYDE`):
published latest value 126,420 direct dependents, none of its admitted packages names its
repository (`builtin`, `bat`, `coffeescript` and others name different repositories).

## Proposed correction (superseding record, m3.1)

1. Admission: a declared package stays in the panel unless the published package names a
   different source repository (`other_repo` out), or its manifest marks it
   `"private": true`. `no_link` stays (absence of metadata is not evidence of a namesake).
   This keeps the Sybil guard: a third party cannot add a package to a system's union,
   because the declaring side is still the system's own tree.
2. Description: replace "linkage-verified" with the rule as implemented, on cards,
   `methodology/m3.json` and the methodology page.
3. History: the corrected union changes every point of the affected series. Either
   (a) replay the 14 most recent confirmed-clean partitions read-only on BigQuery,
   about $48 (551 GB a partition at on-demand pricing, $3.44 each, the same circuit
   breaker), or (b) no spend: axis 3 for the 26 affected systems goes to `rebaseline`
   and is unscored until 14 clean points accrue under the new union.
4. Effective from the next capture after the record is committed; earlier snapshots stay
   as published, with a dated note on the affected cards.

## Owner decision needed

Option 3(a) or 3(b). Recommendation: (a) — $48 restores a correct axis within a week;
(b) leaves 26 systems without axis 3 for about three months.
