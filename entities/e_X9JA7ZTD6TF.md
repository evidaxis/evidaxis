---
schema_ver: 1.0
entity_id: e_X9JA7ZTD6TF
entity_type: repo
name: "DSPy"
slug: dspy
homepage: "https://dspy.ai"
ids:
  github_repo: "stanfordnlp/dspy"
  openalex_work_ids: ["W4387430850"]
classification:
  domain: ai
  industry: ai-agents
  sub_niche: agent-frameworks
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 63819f13c9c7
  captured_at: 2026-11-21T03:40:14+00:00
  period: 2026-w47
  momentum: 53.0
  percentile: 60
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.049000109346481996, "cohort_z": 1.243, "recent_weekly_commits": 15.8, "stars_not_scored": 39159}
    openalex_citation_momentum: {"status": "present", "slope": 1.9700969411974212, "cohort_z": 0.264, "total_citations": 1275, "by_year": {"2026": 766, "2025": 359, "2024": 144, "2023": 6}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.011626, "theil_sen": 0.01114, "cohort_z": -0.782, "latest": 175, "points": 31, "points_reconstructable": 15, "as_of_partition": "2026-11-02", "unstable": false, "rising_vote": false}
note: "paper_ref: 2310.03714; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# DSPy

Evidaxis measures **DSPy** on methodology m5. Momentum 53.0/100; 3 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
