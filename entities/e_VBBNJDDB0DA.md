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
  snapshot_id: 04724603bccf
  captured_at: 2026-11-14T03:45:26+00:00
  period: 2026-w46
  momentum: 34.3
  percentile: 0
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.061159866027226485, "cohort_z": -2.528, "recent_weekly_commits": 2.2, "stars_not_scored": 18031}
    openalex_citation_momentum: {"status": "present", "slope": 0.8503036497861969, "cohort_z": -1.414, "total_citations": 1001, "by_year": {"2026": 563, "2025": 240, "2024": 155, "2023": 43}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.02969, "theil_sen": 0.027893, "cohort_z": 0.182, "latest": 15, "points": 30, "points_reconstructable": 15, "as_of_partition": "2026-10-26", "unstable": false, "rising_vote": false}
note: "paper_ref: 2303.17760; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# CAMEL

Evidaxis measures **CAMEL** on methodology m5. Momentum 34.3/100; 3 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
