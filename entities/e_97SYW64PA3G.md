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
  snapshot_id: 868e3c39d9c7
  captured_at: 2026-11-07T03:43:55+00:00
  period: 2026-w45
  momentum: 64.5
  percentile: 81
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.05371992346897168, "cohort_z": 1.462, "recent_weekly_commits": 34.0, "stars_not_scored": 35521}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 42, "by_year": {"2026": 21, "2025": 18, "2024": 3}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.041272, "theil_sen": 0.03428, "cohort_z": 0.864, "latest": 30, "points": 29, "points_reconstructable": 15, "as_of_partition": "2026-10-19", "unstable": false, "rising_vote": false}
note: "paper_ref: 2402.14034; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# AgentScope

Evidaxis measures **AgentScope** on methodology m5. Momentum 64.5/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
