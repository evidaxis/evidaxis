---
schema_ver: 1.0
entity_id: e_5WYRYN5H1XY
entity_type: repo
name: "Continue"
slug: continue
homepage: "https://continue.dev/"
ids:
  github_repo: "continuedev/continue"
  openalex_work_ids: []
classification:
  domain: ai
  industry: developer-tools
  sub_niche: coding-agents
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 63819f13c9c7
  captured_at: 2026-11-21T03:40:14+00:00
  period: 2026-w47
  momentum: 38.6
  percentile: 5
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.050505174706053965, "cohort_z": -1.098, "recent_weekly_commits": 0.0, "stars_not_scored": 36532}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.00319, "theil_sen": 0.0, "cohort_z": -0.73, "latest": 7, "points": 31, "points_reconstructable": 15, "as_of_partition": "2026-11-02", "unstable": true, "rising_vote": false}
note: "No academic paper; axis-2 absent."
---

# Continue

Evidaxis measures **Continue** on methodology m5. Momentum 38.6/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
