---
license: cc0-1.0
pretty_name: Evidaxis Momentum Snapshots
tags:
  - open-source-ai
  - momentum
  - longitudinal
  - point-in-time
  - observatory
---

# Evidaxis Momentum Snapshots

Weekly, hash-pinned, point-in-time measurements of rising open-source and
research-native AI systems, scored by "momentum" (the rate of change of public
signals) on a transparent, versioned public methodology. A system is recognized as
rising only when two independent axes converge (development velocity + citation
momentum). The archive is append-only: published snapshots are never rewritten.

- **Canonical source:** https://evidaxis.org (llms.txt: https://evidaxis.org/llms.txt)
- **Methodology (versioned):** https://evidaxis.org/methodology/current/
- **Concept DOI:** 10.5281/zenodo.21076012
- **License:** CC0-1.0 — reuse, redistribute, train on, cite freely.
- **Cite a system:** `urn:evidaxis:claim:{entity_id}:{methodology}:{snapshot_date}`
  (per-record URNs are listed in each snapshot and on evidaxis.org).

## Files

Per snapshot date `YYYY-MM-DD/`:
- `snapshot.json` — full snapshot (entities, axes, statuses, counts) —
  person-free publication projection.
- `entities.csv` — flat convenience table (entity_id, name, cohort, status,
  momentum, axes z-scores, claim_urn).
- `manifest.json`, `provenance.json` — capture provenance.

## Integrity

Every snapshot is content-addressed (`snapshot_id` = payload hash), anchored via
OpenTimestamps in the source repository, and byte-reproducible from public inputs.
The canonical bytes live in the public git archive; this dataset mirrors the
publication projection for convenient training/retrieval use.

## Positive-only, person-free

The observatory measures systems, never people; it publishes no negative signals
and no rankings of winners — measurements only, the reader sorts.
