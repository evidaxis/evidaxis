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
  methodology_version: m4
  snapshot_id: ad5e404d4f82
  captured_at: 2026-10-12T12:11:36+00:00
  period: 2026-w41
  momentum: 44.0
  percentile: 33
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.008281472761522376, "cohort_z": -0.285, "recent_weekly_commits": 13.2, "stars_not_scored": 38598}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 59, "by_year": {"2026": 15, "2025": 29, "2024": 15}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.014099, "theil_sen": 0.01369, "cohort_z": -0.674, "latest": 167, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": false}
note: "paper_ref: 2310.03714; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# DSPy

Evidaxis measures **DSPy** on methodology m4. Momentum 44.0/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
