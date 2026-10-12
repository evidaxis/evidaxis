---
schema_ver: 1.0
entity_id: e_HTQD84GES1K
entity_type: repo
name: "Qwen-Agent"
slug: qwen-agent
homepage: "https://github.com/QwenLM/Qwen-Agent"
ids:
  github_repo: "QwenLM/Qwen-Agent"
  openalex_work_ids: []
classification:
  domain: ai
  industry: ai-agents
  sub_niche: agent-frameworks
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m4
  snapshot_id: ad5e404d4f82
  captured_at: 2026-10-12T12:11:36+00:00
  period: 2026-w41
  momentum: 40.7
  percentile: 20
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.0, "cohort_z": -0.042, "recent_weekly_commits": 0.0, "stars_not_scored": 17165}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.009827, "theil_sen": 0.0, "cohort_z": -1.442, "latest": 7, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": true, "rising_vote": false}
note: "No canonical paper / paper has 0 citations indexed; axis-2 structurally absent."
---

# Qwen-Agent

Evidaxis measures **Qwen-Agent** on methodology m4. Momentum 40.7/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
