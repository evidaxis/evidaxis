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
  snapshot_id: 7bf8281671a3
  captured_at: 2026-11-28T03:40:51+00:00
  period: 2026-w48
  momentum: 54.0
  percentile: 67
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.04696846934002223, "cohort_z": 1.248, "recent_weekly_commits": 15.8, "stars_not_scored": 39266}
    openalex_citation_momentum: {"status": "present", "slope": 1.8870186312271213, "cohort_z": 0.487, "total_citations": 1516, "by_year": {"2026": 980, "2025": 391, "2024": 137, "2023": 8}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.011238, "theil_sen": 0.010607, "cohort_z": -0.776, "latest": 174, "points": 32, "points_reconstructable": 15, "as_of_partition": "2026-11-09", "unstable": false, "rising_vote": false}
note: "paper_ref: 2310.03714; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# DSPy

Evidaxis measures **DSPy** on methodology m5. Momentum 54.0/100; 3 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
