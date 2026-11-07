---
schema_ver: 1.0
entity_id: e_VBBNJDDB0DA
entity_type: repo
name: "CAMEL"
slug: camel
homepage: "https://camel-ai.org"
ids:
  github_repo: "camel-ai/camel"
  openalex_work_ids: ["W4362508448"]
classification:
  domain: ai
  industry: ai-agents
  sub_niche: agent-frameworks
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 868e3c39d9c7
  captured_at: 2026-11-07T03:43:55+00:00
  period: 2026-w45
  momentum: 35.1
  percentile: 6
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.06974874766362144, "cohort_z": -3.047, "recent_weekly_commits": 2.5, "stars_not_scored": 18015}
    openalex_citation_momentum: {"status": "present", "slope": 1.3013448427221919, "cohort_z": -0.674, "total_citations": 497, "by_year": {"2026": 285, "2025": 134, "2024": 69, "2023": 9}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.030585, "theil_sen": 0.028852, "cohort_z": 0.151, "latest": 15, "points": 29, "points_reconstructable": 15, "as_of_partition": "2026-10-19", "unstable": false, "rising_vote": false}
note: "paper_ref: 2303.17760; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# CAMEL

Evidaxis measures **CAMEL** on methodology m5. Momentum 35.1/100; 3 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
