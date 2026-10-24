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
  snapshot_id: 9a3f0a2522ac
  captured_at: 2026-10-24T03:35:10+00:00
  period: 2026-w43
  momentum: 39.4
  percentile: 6
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.043131621921029394, "cohort_z": -1.767, "recent_weekly_commits": 2.7, "stars_not_scored": 17958}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.032791, "theil_sen": 0.03143, "cohort_z": 0.071, "latest": 14, "points": 27, "points_reconstructable": 15, "as_of_partition": "2026-10-05", "unstable": false, "rising_vote": false}
note: "paper_ref: 2303.17760; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# CAMEL

Evidaxis measures **CAMEL** on methodology m5. Momentum 39.4/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
