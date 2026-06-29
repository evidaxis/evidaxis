# Evidaxis Genesis Deposit — README, Re-Fetch Recipe & Verification

This bundle is the **genesis deposit** of Evidaxis: an independent, CC0, machine-readable **seed coverage map** of public AI systems (organizations, repositories, models — never people). It ships **facts + content-hashes + a re-fetch recipe + archive pointers**, NOT raw upstream expressive bytes. It is a hand-curated 19-system seed across 3 cohorts, a single t=0 observation point.

> See `GENESIS-ARTIFACT-LOCKED` (title/abstract/JSON-LD), `RIGHTS-BASIS.md` (legal posture), `TRUST-ROOT-AND-CONTINUITY.md` (signing/continuity), `MINT-STEPS.md` (how this was minted).

## Bundle manifest (per-file license)
| File | What | License |
|---|---|---|
| `data/snapshot.json` | the person-free computed facts/metrics + tiers (the seed coverage map) | **CC0-1.0** |
| `data/manifest.json` | snapshot id + `manifest_hash` (the genesis identity digest of the source set) | **CC0-1.0** |
| `data/provenance.json` | the re-fetch source_manifest + the retained raw GitHub weekly-commit-counts + OpenAlex citation facts (numbers only) | **CC0-1.0** |
| `data/SHA256SUMS` | content-hashes of snapshot/manifest/provenance (byte-reproducibility grip) | **CC0-1.0** |
| `data/archive-pointers.json` | Wayback + Software Heritage pre-image pointers for each source repo | **CC0-1.0** |
| `genesis.jsonld` | the canonical machine-readable surface (@type SeedCoverageSnapshot; absence-semantics; layered ladder) | **CC0-1.0** |
| `RIGHTS-BASIS.md` · `TRUST-ROOT-AND-CONTINUITY.md` | authored notices | **CC-BY-4.0** |
| `code/collect.py` · `code/archive_pin.py` | the transform + archiver | **Apache-2.0** |
| `methodology.md` | the scoring methodology | **CC-BY-4.0** |

**CC0 covers ONLY Evidaxis-owned rights** (facts, computed scores, schema, the compilation, with an explicit waiver of any sui-generis database right Evidaxis holds). It does not license third-party trademarks, upstream expressive content, or source-platform rights. **Names of natural persons are excluded** (systems-not-people; the deposit is person-free).

## What is NOT in this deposit (by design)
Raw READMEs / model-card prose / source code / paper abstracts / free-text descriptions / natural-person names or handles. The deposit references where to re-fetch them under their own licenses; it does not republish them.

## Re-fetch recipe (how a third party re-derives the facts)
1. Read `data/provenance.json` → `source_manifest` (the exact list of GitHub repos + OpenAlex work IDs) + `captured_at`.
2. Re-fetch each source:
   - GitHub: the repo's weekly commit-activity (`/stats/commit_activity`) via the public API.
   - OpenAlex: each work's citations-by-year (`api.openalex.org/works/<id>`) — OpenAlex is CC0.
   If a live source has mutated/404'd, use the pre-image pointer in `data/archive-pointers.json` (Wayback / Software Heritage hold it under their own legal basis).
3. Re-run the transform: `code/collect.py` (deterministic given the same inputs; computes the same robust-z slopes, the 2-axis convergence gate, the tiers).
4. The re-derived snapshot must match `data/snapshot.json`; the content-hashes must match `data/SHA256SUMS`. `manifest_hash` in `data/manifest.json` is the digest of the source set (`source_manifest`) and is the stable genesis identity (independent of any per-row presentation field).

## Verification
- `manifest_hash` = `sha256(json.dumps(source_manifest, sort_keys=True))` — pins WHICH repos/works the genesis covers.
- `SHA256SUMS` = byte-hashes of the shipped files — pins their exact bytes.
- (Post-mint) each sealed snapshot is externally anchored (OpenTimestamps + RFC-3161 TSA) per `TRUST-ROOT-AND-CONTINUITY.md`, so the record stays verifiable even if the signing key is later lost.

## Framing (do not misread)
A system **not listed is undefined, never judged not-rising**. The numbers describe the **seed, not AI** — there is no population denominator. An empty Rising tier at t=0 is the **expected output of a strict gate** (convergence needs a sustained window genesis cannot yet have), the output a gate not tuned to flatter would produce, not a finding about the field. Coverage is biased toward open / public-API systems; closed/commercial/non-English/individual-maintained systems are under-covered (see `RIGHTS-BASIS.md`).
