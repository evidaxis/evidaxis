---
schema_ver: 1.0
entity_id: e_M5SCCQPBZ89
entity_type: repo
name: "Microsoft Agent Framework"
slug: microsoft-agent-framework
homepage: "https://github.com/microsoft/agent-framework"
ids:
  github_repo: "microsoft/agent-framework"
  openalex_work_ids: []
classification:
  domain: ai
  industry: ai-agents
  sub_niche: agent-frameworks
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 4d9867e6f218
  captured_at: 2026-10-17T12:13:42+00:00
  period: 2026-w42
  momentum: 70.3
  percentile: 94
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["deps_direct_dependents_momentum"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.03161601396010638, "cohort_z": 0.627, "recent_weekly_commits": 79.7, "stars_not_scored": 14178}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.078227, "theil_sen": 0.077027, "cohort_z": 2.614, "latest": 26, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": true}
note: "No canonical paper / paper has 0 citations indexed; axis-2 structurally absent."
---

# Microsoft Agent Framework

Evidaxis measures **Microsoft Agent Framework** on methodology m5. Momentum 70.3/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
