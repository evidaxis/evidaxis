# Erratum — immature cards were indexable, against the published growth policy (2026-08-23)

**Class:** correctness defect (freeze-exempt per METHODOLOGY-FREEZE-2026-08-20:
the fix IMPLEMENTS a frozen rule, it does not alter any predicate).

**The rule.** REGISTRY-GROWTH-POLICY-2026-07-21: "Cards index after 4 weekly
observations; before that, admitted systems are visible in a machine-readable
pending manifest (membership is complete and auditable from day one;
thin-content GEO risk avoided)." Every activation-tranche record repeats it.

**What was actually built.** The build never wired that rule to robots or the
sitemap. Every entity page shipped `robots: index, follow` and a sitemap entry
from its first appearance. As of the 2026-08-22 snapshot, 29 of 166 built
cards carry `history_sufficiency: insufficient` in their own typed measurement
state (the page KNOWS its history is short) while inviting indexing. The
second-tranche card e_01E6T51Z5NE, live with `weekly_observations: 2,
required: 4`, is the dated witness.

**Fix.** The page's own `measurementStateFor` verdict now drives
`noindex` on entity pages with insufficient history; the sitemap excludes the
same pages by reading each built JSON twin (single source of truth, no second
counter); the dist gate enforces the invariant both ways and additionally
requires every canary page (both arms) to be history-sufficient, so the
running display experiment can never be confounded by a robots flip.

**No membership change.** Which systems are admitted, activated, or measured
is untouched; this record is about robots metadata and sitemap membership
only. Archived snapshots are retained unchanged.
