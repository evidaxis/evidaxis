# Evidaxis

[Evidaxis](https://evidaxis.org) is an independent observatory of open AI systems.
It publishes a weekly CC0 archive of measured facts, with a source and observation
date for each value. The **2026-10-17** snapshot contains **6,289 systems** and uses
methodology **m5**.

The three axes follow weekly GitHub commit counts, OpenAlex citations, and
verified direct dependent packages from deps.dev. Package evidence distinguishes
verified repository links from unverified links. Momentum describes change within
a system's niche; medals recognize measured activity within that niche. Recognition
follows the declared methodology and its convergence rules. Each record carries
its coverage and methodology version so readers can interpret the evidence.

## Get the data

- **Snapshot JSON:** `data/snapshots/<date>/snapshot.json` in this repository.
  The [2026-10-17 snapshot](data/snapshots/2026-10-17/) includes its manifest,
  provenance, and checksums.
- **System records:** the site's system cards link to CSV downloads and JSON
  records at `https://evidaxis.org/e/<id>.json`.
- **Hugging Face:** [evidaxis/momentum-snapshots](https://huggingface.co/datasets/evidaxis/momentum-snapshots)
  provides dated `snapshot.json` and `entities.csv` publication projections.
- **Zenodo:** the archive's concept DOI is
  [10.5281/zenodo.21076011](https://doi.org/10.5281/zenodo.21076011).
  Individual deposits have version DOIs for citing a specific release.

**git = the only source of truth.** The site and distribution mirrors derive from
the repository. Dated snapshots preserve their captured bytes; manifests and
provenance make the recorded inputs checkable. Publication projections apply the
person-free rules before distribution.

## Cite the evidence

For a measurement about one system, copy its `claim_urn` from the JSON record or
the card's citation block:

```text
urn:evidaxis:claim:{entity_id}:{methodology_version}:{snapshot_date}
```

The identifier binds a permanent system ID, an immutable methodology version,
and a snapshot date. The [claim-URN specification](CLAIM-URN.md) also documents
historical week epochs and the accepted accession formats.

For the archive, cite the concept DOI
[10.5281/zenodo.21076011](https://doi.org/10.5281/zenodo.21076011), together with
the snapshot date and methodology version used. The FAIRsharing registry record
is [10.25504/FAIRsharing.70181b](https://doi.org/10.25504/FAIRsharing.70181b).

## Methodology versions

Definitions live in [`methodology/`](methodology/). The public
[methodology registry](https://evidaxis.org/methodology-registry.json) records
versions and their effective dates; the site provides a
[current methodology page](https://evidaxis.org/methodology/current/).
The current version is **m5**, used by the 2026-10-17 snapshot. Each historical
snapshot retains the version under which it was measured.

## Repository layout

| Path | Purpose |
| --- | --- |
| `collectors/` | Signal collection, identity, provenance, and archive tooling. |
| `etl/` | Frozen genesis collector and supporting legacy artifacts. |
| `data/` | Dated observations, snapshots, manifests, and histories. |
| `entities/`, `taxonomy/` | Permanent system records and niche definitions. |
| `methodology/` | Versioned measurement definitions. |
| `web/` | Astro site, public records, downloads, and presentation checks. |
| `governance/` | Dated decisions, errata, and stewardship records. |
| `scripts/` | Publication, integrity, privacy, and operational checks. |

## Person-free and positive-only

The unit of observation is a system. Public projections omit personal account
identifiers and apply person-free checks before publication. The observatory
offers measured facts, momentum, and positive recognition within niches. Removal requests:
hello@evidaxis.org ([procedure](governance/ERASURE-REQUESTS-2026-10-19.md)).

The [Constitution](CONSTITUTION.md) defines these commitments. Facts, computed
measurements, and dataset metadata are CC0; code is Apache-2.0 and authored prose
is CC-BY-4.0. See [LICENSING.md](LICENSING.md) and [RIGHTS-BASIS.md](RIGHTS-BASIS.md)
for the component licenses and source attribution rules.
