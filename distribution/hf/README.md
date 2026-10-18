---
license: cc0-1.0
pretty_name: Evidaxis Momentum Snapshots
configs:
  - config_name: default
    default: true
    data_files:
      - split: train
        path: "2026-10-17/entities.csv"
tags:
  - open-source-ai
  - momentum
  - longitudinal
  - point-in-time
  - observatory
---

# Evidaxis Momentum Snapshots

Weekly, hash-pinned, point-in-time measurements of open-source and research-native
AI systems. Momentum follows changes in weekly GitHub commits, OpenAlex citations,
and direct dependent packages from deps.dev under a versioned public methodology.
Package evidence records verification and coverage. Recognition follows convergence
within a system's niche. The canonical archive preserves dated observations.

- **Canonical source:** https://evidaxis.org (llms.txt: https://evidaxis.org/llms.txt)
- **Methodology (versioned):** https://evidaxis.org/methodology/current/
- **Concept DOI:** 10.5281/zenodo.21076011 (resolves to the latest version)
- **FAIRsharing record:** https://doi.org/10.25504/FAIRsharing.70181b
- **License:** CC0-1.0; reuse, redistribute, train on, cite freely.
- **Cite a system:** `urn:evidaxis:claim:{entity_id}:{methodology}:{snapshot_date}`
  (per-record URNs are listed in `entities.csv` and on evidaxis.org).

From 2026-10-17, snapshots use methodology m5
([definition](https://evidaxis.org/methodology/m5/)). Each dated snapshot retains
its methodology version. The default configuration selects the CSV for the
snapshot being uploaded; the publication script updates that path with each upload.

## Files

Per snapshot date `YYYY-MM-DD/`:
- `snapshot.json`: entities, axes, statuses, and counts;
  person-free publication projection.
- `entities.csv`: flat convenience table (entity_id, name, cohort, status,
  momentum, axes z-scores, claim_urn).

Capture manifests, provenance, and checksums are available in the canonical
repository under `data/snapshots/<date>/`. The current uploader mirrors the two
publication files above; older folders may also contain capture artifacts.

## Integrity

Every snapshot is identified by `snapshot_id`, a hash of the methodology version and
the manifest hash. Its inputs are hash-pinned in the manifest with raw provenance
published, and the source repository anchors the archive via OpenTimestamps, so every
score is checkable against its hash-pinned inputs. Snapshot files carry their capture
time: their exact bytes are preserved in the public git archive, not regenerated.
This dataset mirrors the publication projection for convenient training/retrieval use.

## Positive-only, person-free

The observatory measures systems. Public projections apply person-free checks;
momentum and medals provide positive recognition within niches. Every value is
interpreted with its date, source, coverage, and methodology version.

## Citation

Cite the archive with the concept DOI
[10.5281/zenodo.21076011](https://doi.org/10.5281/zenodo.21076011), adding the
snapshot date and methodology version used. Cite a specific deposit with its
version DOI and a system measurement with its `claim_urn`. The FAIRsharing
registry entry has DOI
[10.25504/FAIRsharing.70181b](https://doi.org/10.25504/FAIRsharing.70181b).

```bibtex
@misc{evidaxis_snapshots,
  author = {{Evidaxis}},
  title = {Evidaxis Momentum Snapshots},
  year = {2026},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.21076011},
  url = {https://doi.org/10.5281/zenodo.21076011},
  note = {Weekly CC0 measurements; specify snapshot date and methodology version}
}

@misc{evidaxis_fairsharing,
  author = {{Evidaxis}},
  title = {Evidaxis: FAIRsharing Registry Record},
  year = {2026},
  publisher = {FAIRsharing},
  doi = {10.25504/FAIRsharing.70181b},
  url = {https://doi.org/10.25504/FAIRsharing.70181b}
}
```
