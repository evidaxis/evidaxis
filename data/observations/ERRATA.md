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

---

# ERRATUM — snapshot_id collision f1f2495d518d (2026-07-10)

**What was wrong.** Two published measurement snapshots —
`data/snapshots/2026-07-03` (133 entities) and `data/snapshots/2026-07-04`
(135 entities) — share the identical `snapshot_id` `f1f2495d518d` and the same
ISO-week period `2026-w27` under methodology `m2`, while holding different
payloads (entity set and scores). Root cause: the frozen mint in
`etl/collect.py` computes
`snapshot_id = sha1(METHODOLOGY_VERSION + manifest_hash)[:12]`, where
`manifest_hash` covers only the seed lists (`github_repos`, `openalex_works`),
not entity payloads. When seeds are unchanged across days, distinct
measurements collide on identity. Claim-URNs minted with epoch `2026-w27`
under `m2` are therefore ambiguous across those two snapshots: the same URN
names two different assertions.

**Payload hashes** (content-address of `snapshot.json` with the `snapshot_id`
field removed; canonical JSON, sort_keys, tight separators, UTF-8):

| date       | entities | stored snapshot_id | payload sha256 (full)                                      | content-id [:12] |
|------------|----------|--------------------|------------------------------------------------------------|------------------|
| 2026-07-03 | 133      | `f1f2495d518d`     | `38287b561ff9ab07b5ed850b7280472a63eb59014e3b65dae15ef4cd4a1bb4a7` | `38287b561ff9`   |
| 2026-07-04 | 135      | `f1f2495d518d`     | `900232c1b32c8c9029d934ca3ffffc377d1a9954116b5bc9718ea86146b61188` | `900232c1b32c`   |

**What changed (forward only).**
1. New post-step `collectors/snapshot_identity.py` rewrites `snapshot_id` on the
   *current* (not-yet-published) snapshot to
   `sha256(canonical_json(snapshot without snapshot_id))[:12]` before
   `refresh_sums.py` seals the bundle. Frozen `etl/collect.py` is untouched.
2. Claim-URN minting switches epoch from ISO-week `period` to `snapshot_date`
   (`YYYY-MM-DD`) in `web/src/lib/claim_urn.ts` (`claimUrnForEntity`). Grammar
   still accepts `YYYY-Www` so historically minted URNs remain parseable.
3. CI: `python3 collectors/snapshot_identity.py --check` fails on any new
   unallowlisted collision; the known pair is listed in
   `data/observations/errata_snapshot_id.json`.

**What was NOT rewritten.** Published snapshots `2026-06-27`, `2026-07-01`,
`2026-07-03`, and `2026-07-04` keep their original bytes (append-only archive).
The collision is documented here and allowlisted for integrity checks; it is
not fixed retroactively. From this change forward, every new snapshot has a
unique content-derived `snapshot_id` and an unambiguous claim-URN epoch.
