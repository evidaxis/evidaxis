# Evidaxis

> An independent data observatory that measures **rising** open-source and
> research-native AI systems by the *rate of change* of public signals, and
> publishes the results as open datasets under **CC0**.

Evidaxis scores **systems** (repos / models / organizations — never people) on a
transparent, versioned methodology. A positive "momentum" signal is only emitted
when **≥2 independent axes converge** (e.g. development velocity *and* citation
momentum both rising within a system's cohort). The institute publishes **only
positive** recognition — there is no "worst" list.

## Layout (day-1 build slice)

```
etl/        collect.py — the collector: pulls signals, computes axes, runs the
            convergence gate, emits the canonical data artifacts. (Apache-2.0)
data/       canonical truth (CC0): snapshots, per-entity history, manifests.
entities/   per-entity dossier records (CC0).
taxonomy/   the node registry (domain → industry → sub-niche). (CC0)
web/        the public static site (Astro, 0 JS, GEO-optimized).
```

## Principles (locked in design)

- **git = the only source of truth.** The database and site are derived and
  rebuildable. Every score is byte-reproducible from the manifest.
- **systems-not-people.** The measured unit is always a system; individuals are
  never named or scored. There is no `/persons` surface.
- **Axes measure the *slope* of a trend**, normalized within a cohort
  (sub-niche), so "rising" means rising *relative to peers* — not just big.
- **Positive-only + ≥2-axis convergence gate.** Restraint is the brand.
- **Identity is opaque and permanent.** An entity's id (`e_…`) is minted once,
  never reused or reassigned; citations and badges carry the id, so a rename or
  acquisition never breaks a link.

*Evidaxis = evidence × axis.*
