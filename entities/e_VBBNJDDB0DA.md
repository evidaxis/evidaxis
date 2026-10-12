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
  methodology_version: m4
  snapshot_id: ad5e404d4f82
  captured_at: 2026-10-12T12:11:36+00:00
  period: 2026-w41
  momentum: 42.4
  percentile: 27
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.04621779633035659, "cohort_z": -1.776, "recent_weekly_commits": 3.1, "stars_not_scored": 17871}
    openalex_citation_momentum: {"status": "present", "slope": 0.877009570622604, "cohort_z": 0.0, "total_citations": 101, "by_year": {"2026": 14, "2025": 51, "2024": 28, "2023": 8}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.034171, "theil_sen": 0.032919, "cohort_z": -0.05, "latest": 15, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": false}
note: "paper_ref: 2303.17760; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# CAMEL

Evidaxis measures **CAMEL** on methodology m4. Momentum 42.4/100; 3 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
