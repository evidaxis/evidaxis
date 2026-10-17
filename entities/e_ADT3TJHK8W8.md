---
schema_ver: 1.0
entity_id: e_ADT3TJHK8W8
entity_type: repo
name: "Google ADK"
slug: google-adk
homepage: "https://google.github.io/adk-docs/"
ids:
  github_repo: "google/adk-python"
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
  momentum: 60.8
  percentile: 75
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.05570670073805985, "cohort_z": 1.67, "recent_weekly_commits": 120.6, "stars_not_scored": 21891}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.026085, "theil_sen": 0.025632, "cohort_z": 0.064, "latest": 221, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": false}
note: "batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# Google ADK

Evidaxis measures **Google ADK** on methodology m5. Momentum 60.8/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
