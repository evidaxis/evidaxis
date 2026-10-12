---
schema_ver: 1.0
entity_id: e_BTT9Q5KW4YN
entity_type: product
name: "OpenCode"
slug: opencode
homepage: "https://opencode.ai"
ids:
  github_repo: "anomalyco/opencode"
  openalex_work_ids: []
classification:
  domain: ai
  industry: developer-tools
  sub_niche: coding-agents
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m4
  snapshot_id: ad5e404d4f82
  captured_at: 2026-10-12T12:11:36+00:00
  period: 2026-w41
  momentum: 57.2
  percentile: 68
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.04245848863191119, "cohort_z": 0.644, "recent_weekly_commits": 165.0, "stars_not_scored": 212830}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.050813, "theil_sen": 0.049577, "cohort_z": 0.516, "latest": 2345, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": false}
note: "batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# OpenCode

Evidaxis measures **OpenCode** on methodology m4. Momentum 57.2/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
