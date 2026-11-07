---
schema_ver: 1.0
entity_id: e_DAFJYGYBDKF
entity_type: repo
name: "mini-swe-agent"
slug: mini-swe-agent
homepage: "https://github.com/SWE-agent/mini-swe-agent"
ids:
  github_repo: "SWE-agent/mini-swe-agent"
  openalex_work_ids: ["W7103754783"]
classification:
  domain: ai
  industry: developer-tools
  sub_niche: coding-agents
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 868e3c39d9c7
  captured_at: 2026-11-07T03:43:55+00:00
  period: 2026-w45
  momentum: 42.5
  percentile: 21
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.06905330397817169, "cohort_z": -1.882, "recent_weekly_commits": 0.2, "stars_not_scored": 9236}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 438, "by_year": {"2026": 329, "2025": 92, "2024": 17}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.031634, "theil_sen": 0.03119, "cohort_z": 0.674, "latest": 9, "points": 29, "points_reconstructable": 15, "as_of_partition": "2026-10-19", "unstable": false, "rising_vote": false}
note: "No canonical paper / paper has 0 citations indexed; axis-2 structurally absent."
---

# mini-swe-agent

Evidaxis measures **mini-swe-agent** on methodology m5. Momentum 42.5/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
