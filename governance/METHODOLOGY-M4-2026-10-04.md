# Methodology m4 — axis 3 counts only a system's own packages, effective 2026-10-10

> status: RECORD 2026-10-04, implementation pending (this file is FIXED by the commit that
> activates m4 in the weekly pipeline). Supersedes the axis-3 package admission of
> `AXIS3-DEPS-V2H1-SUPERSESSION-2026-07-21.md` component 5 for m4 scoring only. m1, m2 and
> m3 rows, pages and snapshots are unchanged; nothing published is recomputed
> (METHODOLOGY-VERSIONING.md rule 3). Class: MAJOR (the axis-3 measurand changes).
> Finding: `governance/DRAFT-2026-10-04-axis3-namesake-packages.md` (superseded by this
> record). Design reviewed by an independent engine (consult, verdict REVISE 0.98); every
> revision it required is adopted below (§8).

## 1. What changes

Axes 1 and 2, the gate, cohorts, momentum, percentile, confidence and status: unchanged
from m3. Axis 3 keeps its estimator, floors, fragility veto and canary hold; only the set of
packages whose dependents are counted changes.

**m3 rule (as implemented):** a package counts for a system when it is declared in the
system's own repository tree, outside excluded directories, and a package of that NAME
exists on deps.dev. The name match admitted unrelated packages: a private build folder
(`build/builtin/package.json`) matched the public npm package `builtin`; bundled extensions
and vendored third-party packages matched their upstream names.

**m4 rule:** as m3, and additionally a declared package is excluded when
1. its published metadata on deps.dev names a different source repository than the
   declaring one (`other_repo` in `data/quarantine/axis3-deps-v2/linkage-audit-2026-10-04.json`), or
2. its own manifest marks it `"private": true` (npm) and the published package of that
   name does not name the declaring repository — the declared package is never published,
   so the name belongs to somebody else. (Checked 2026-10-04 on 329 npm manifests at HEAD,
   `data/quarantine/axis3-deps-v2/private-manifests-2026-10-04.json`: 3 are private, all 3
   are published by the same repository from another manifest and stay; 5 manifests no
   longer exist at HEAD. The rule removes nothing today and guards future admissions.)

A package whose metadata names no repository (`no_link`) stays and is labelled
**unverified**: absence of metadata is not evidence of a namesake. The Sybil guard is
intact: the declaring side is still the system's own tree, so a third party cannot add a
package to a system's union.

**Self-dependent exclusion list:** unchanged and fixed — the v2h.1 panel's package names,
for history and for future captures. Changing it would return dependents that the stored
weekly aggregates already exclude and would move systems that have no removed package.

## 2. History for m4 — exact derivation only, no estimates

Every weekly capture since 2026-03-16 stores rows per system and per package
(`unique_direct`, `xor_fp_direct`, `sketch64`). For a system and partition:

- no removed package present → the stored system total is the m4 value;
- exactly one kept package present → that package's stored `unique_direct` is exact;
- several kept packages present and every kept package's sketch is complete
  (`unique_direct` ≤ 64 and all fingerprints stored) → the number of distinct fingerprints
  in their union is exact up to 64-bit hash collisions;
- otherwise the point is **withheld**. Subtracting removed packages from the stored total
  is not used: disjoint bottom-64 samples do not prove disjoint sets (a kept set of 100
  inside a removed set of 100,000 escapes detection in about 94% of draws).

A system with no kept package leaves axis 3 (`out_of_panel`). A series is scored only on
an unbroken run of usable points; after a withheld point the series restarts, so the
estimator never spans a gap with ordinal time. A vote needs ≥ 14 usable points of the m4
quantity, not merely 14 confirmed-clean partitions.

## 3. Effect, computed from committed files on 2026-10-04

`collectors/axis3_m4_activation_report.py --as-of 2026-10-03` (cutoff partition
2026-09-14): 26 systems hold at least one excluded package. Of the 15 of them with a scored
axis 3 in the m3 snapshot of 2026-10-03, under m4:

- 8 stay scored on an exactly derived 24-point run (Continue, UI-TARS Desktop, Kilo Code,
  Zed, Microsoft Agent Framework, Cline, Qwen Code, dora-rs);
- 3 restart and are unscored on axis 3 until 14 usable points accrue, about three months
  (LangGraph, Void, Mastra) — Void's published m3 value of 126,420 direct dependents came
  from packages of other repositories;
- 4 leave axis 3 because no admitted package remains (Letta, Open Interpreter, MetaGPT,
  Qwen3-VL).

The other 11 affected systems were not scored under m3 and are not scored under m4 (7 out of
panel, 4 below floor). Cohort canary agreement under m4 is equal or higher in every cohort
with votes (agent-frameworks 0.941 → 1.000, coding-agents 0.917 → 1.000); the
multimodal-foundation-models cohort has no axis-3 vote under m4 (n 1 → 0). All other panel
systems are unchanged. The report is re-run on the first m4 snapshot and published with it.

## 4. Forward captures

From the first capture after activation, the BigQuery query maps only m4-admitted packages
to systems; the self-name list stays as in §1. Cost is the existing weekly capture; no
replay is bought.

## 5. Gates rechecked at activation (thresholds not lowered)

Cohort canary agreement ≥ 0.80 (n ≥ 3), cohort size ≥ 5, latest-dependents floor 5,
fragility veto, axis independence monitor: recomputed on m4 data at activation and reported
in the activation note; a cohort that fails is held as under m3.

## 6. Known limits

- The identity audit is as of 2026-10-04 and is applied to all stored partitions; it does
  not prove ownership in March. Repository moves and aliases are resolved through the owner
  cache (`etl/owner_types.json`).
- `no_link` packages are unverified, not verified.
- 64-bit fingerprint collisions are negligible at these set sizes and are not corrected.

## 7. Surfaces

`methodology/m4.json` (parent m3), registry row and fingerprint, permalinked page
`/methodology/m4/`, the axis-3 description on cards, JSON-LD and API, the Hugging Face
dataset card. m3 keeps `score_m3.py --verify` over 2026-09-19 … 2026-10-03.

## 8. Review

Independent consult (2026-10-04) required: MAJOR class; no subtraction-based
reconstruction; fixed self-name list; exact derivation from kept packages only; ≥ 14 usable
points of the new quantity and no time compression across gaps; `private: true` and
`no_link` handling; gates rechecked without lowering; an erratum that lists affected m3
snapshots and numeric consequences. All adopted.
