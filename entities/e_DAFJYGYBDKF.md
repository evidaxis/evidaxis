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
  snapshot_id: 63819f13c9c7
  captured_at: 2026-11-21T03:40:14+00:00
  period: 2026-w47
  momentum: 45.8
  percentile: 26
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.06969033838123673, "cohort_z": -1.265, "recent_weekly_commits": 0.1, "stars_not_scored": 9903}
    openalex_citation_momentum: {"status": "present", "slope": 2.816501146297577, "cohort_z": -0.355, "total_citations": 3612, "by_year": {"2026": 2947, "2025": 558, "2024": 106, "2023": 1}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.034296, "theil_sen": 0.033572, "cohort_z": 0.616, "latest": 11, "points": 31, "points_reconstructable": 15, "as_of_partition": "2026-11-02", "unstable": false, "rising_vote": false}
note: "No canonical paper / paper has 0 citations indexed; axis-2 structurally absent."
---

# mini-swe-agent

Evidaxis measures **mini-swe-agent** on methodology m5. Momentum 45.8/100; 3 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
