---
schema_ver: 1.0
entity_id: e_97SYW64PA3G
entity_type: repo
name: "AgentScope"
slug: agentscope
homepage: "https://docs.agentscope.io"
ids:
  github_repo: "agentscope-ai/agentscope"
  openalex_work_ids: ["W4392126161"]
classification:
  domain: ai
  industry: ai-agents
  sub_niche: agent-frameworks
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 04724603bccf
  captured_at: 2026-11-14T03:45:26+00:00
  period: 2026-w46
  momentum: 61.1
  percentile: 88
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.052650249920900574, "cohort_z": 0.923, "recent_weekly_commits": 37.6, "stars_not_scored": 35956}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 157, "by_year": {"2026": 88, "2025": 58, "2024": 11}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.039261, "theil_sen": 0.032401, "cohort_z": 0.86, "latest": 30, "points": 30, "points_reconstructable": 15, "as_of_partition": "2026-10-26", "unstable": false, "rising_vote": false}
note: "paper_ref: 2402.14034; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# AgentScope

Evidaxis measures **AgentScope** on methodology m5. Momentum 61.1/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
