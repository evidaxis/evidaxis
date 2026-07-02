# ERRATUM — deps.dev package-identity audit (2026-07-02)

**What was wrong.** The first two daily deps.dev captures (2026-07-01,
2026-07-02) resolved each system's package by NAME MATCH ONLY across
pypi/npm/cargo. An identity audit against the packages' own declared source
links found that 21 of 81 name matches pointed at a DIFFERENT project —
name-squats or unrelated same-name packages (e.g. an npm `goose` from 2012 for
block/goose; `codex` from a 2012 project for openai/codex; a `pypi alphafold3`
squat) — and a further set could not be verified at all.

**What changed.**
1. The collector (`collectors/t2_deps_collect.py`, `t2_deps_m2`) now requires
   BOTH a name match AND a source-repo linkage on the package's own deps.dev
   version record before treating a package as a system's identity; verified
   identities are pinned in `data/deps_id_map.json` and never silently
   switched.
2. Every historical row whose identity is not linkage-verified received an
   appended RETRACTION record (status-flip, the standard correction mechanism
   of this archive) in `data/observations/history/*.deps.jsonl` — 140 rows on
   2026-07-02. Original rows remain in place, as always: corrections add a
   layer, never rewrite.
3. The site surfaces a dependents value ONLY when the captured identity
   matches the verified pin; unverified values no longer render.

**Effect on coverage.** Verified coverage is currently 31/108 systems —
honestly smaller than the 81/108 name-matched figure previously displayed.
Coverage will grow as additional identities are verified (richer linkage
sources are a known follow-up), but a smaller true number beats a larger
false one.

The daily capture files (`deps.jsonl` per date) are immutable point-in-time
records and keep their original bytes; their `coverage: matched` field
reflects the collector's belief AT CAPTURE TIME under the then-current
methodology (`t2_deps_m1`, name-only).
