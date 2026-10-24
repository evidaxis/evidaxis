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
  snapshot_id: 9a3f0a2522ac
  captured_at: 2026-10-24T03:35:10+00:00
  period: 2026-w43
  momentum: 67.8
  percentile: 88
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.065663762716958, "cohort_z": 1.959, "recent_weekly_commits": 28.9, "stars_not_scored": 33783}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 11, "by_year": {"2026": 3, "2025": 6, "2024": 2}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.045705, "theil_sen": 0.038936, "cohort_z": 0.883, "latest": 31, "points": 27, "points_reconstructable": 15, "as_of_partition": "2026-10-05", "unstable": false, "rising_vote": false}
note: "paper_ref: 2402.14034; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# AgentScope

Evidaxis measures **AgentScope** on methodology m5. Momentum 67.8/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
