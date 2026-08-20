# Display-semantics correction — 2026-08-20 (display layer, not measurement methodology)

Until this date, discovery surfaces rendered evaluative strings next to system names
(`decelerating`, `gate shut`, `not rising`, a "Verdict" section, momentum badges, a
peer plane with named z-scores). **Those strings were inconsistent with the
institute's own invariant; this record corrects them. Archived snapshots are retained
unchanged, as the record of that inconsistency.**

The invariant, stated precisely: **the institute does not predicate deficit on a
name.** What is published: raw weekly series (including declining slopes — data is
data), measurement metadata for every card in the instrument's voice with its
coverage reason (`axes measurable: 1 of 2`, `history: 2 of 4 weekly observations`,
`gate: not computable this week`), unnamed aggregates, and positive gate-passing
events. Forbidden: any string next to a system name that reads as a verdict about
the system. A page-wide lexicon guard now enforces this on every built entity
surface (HTML and JSON) and fails the build on violation.

Reasoning: short-window slopes are noisy; attaching the institute's name to an
adverse judgment about a named system is a reputational act disproportionate to
that noise. **Absence of a published signal is not an adverse finding.**

Machine-code map (old → new): `gate_shut` → gate state with coverage reason ·
`decelerating` / `not_rising` → removed from display; slope sign remains in CC0
microdata, not rendered as a named evaluative badge. Archived snapshots render in
the lexicon in effect at capture; cross-lexicon re-rendering is not provided.

This correction changes public meaning and is therefore recorded here, dated;
measurement methodology, thresholds, axes and admission are unchanged.
