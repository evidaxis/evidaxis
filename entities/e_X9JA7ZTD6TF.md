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
  snapshot_id: 04724603bccf
  captured_at: 2026-11-14T03:45:26+00:00
  period: 2026-w46
  momentum: 59.4
  percentile: 75
  confidence: high
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity", "openalex_citation_momentum"]
  rising: true
  status: rising
  axes:
    github_commit_velocity: {"slope": 0.061866263703089355, "cohort_z": 1.202, "recent_weekly_commits": 17.7, "stars_not_scored": 39036}
    openalex_citation_momentum: {"status": "present", "slope": 2.253594888813944, "cohort_z": 1.761, "total_citations": 949, "by_year": {"2026": 555, "2025": 271, "2024": 121, "2023": 2}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.011977, "theil_sen": 0.011561, "cohort_z": -0.712, "latest": 173, "points": 30, "points_reconstructable": 15, "as_of_partition": "2026-10-26", "unstable": false, "rising_vote": false}
note: "paper_ref: 2310.03714; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# DSPy

Evidaxis measures **DSPy** on methodology m5. Momentum 59.4/100; 3 axes present, 2 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
