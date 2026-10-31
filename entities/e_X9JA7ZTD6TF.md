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
  snapshot_id: d1eb0cec0f6a
  captured_at: 2026-10-31T03:43:22+00:00
  period: 2026-w44
  momentum: 55.6
  percentile: 69
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.04002867786829912, "cohort_z": 1.569, "recent_weekly_commits": 16.2, "stars_not_scored": 38860}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 71, "by_year": {"2026": 16, "2025": 37, "2024": 18}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.012918, "theil_sen": 0.012211, "cohort_z": -0.674, "latest": 169, "points": 28, "points_reconstructable": 15, "as_of_partition": "2026-10-12", "unstable": false, "rising_vote": false}
note: "paper_ref: 2310.03714; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# DSPy

Evidaxis measures **DSPy** on methodology m5. Momentum 55.6/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
