---
schema_ver: 1.0
entity_id: e_EDX1R1KVT3X
entity_type: repo
name: "AutoGen"
slug: autogen
homepage: "https://microsoft.github.io/autogen/"
ids:
  github_repo: "microsoft/autogen"
  openalex_work_ids: []
classification:
  domain: ai
  industry: ai-agents
  sub_niche: agent-frameworks
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: d1eb0cec0f6a
  captured_at: 2026-10-31T03:43:22+00:00
  period: 2026-w44
  momentum: 45.6
  percentile: 38
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.010900776172908543, "cohort_z": 0.094, "recent_weekly_commits": 0.2, "stars_not_scored": 61642}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.010986, "theil_sen": 0.009858, "cohort_z": -0.794, "latest": 156, "points": 28, "points_reconstructable": 15, "as_of_partition": "2026-10-12", "unstable": false, "rising_vote": false}
note: "paper_ref: 2308.08155; incumbent (calibration); batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# AutoGen

Evidaxis measures **AutoGen** on methodology m5. Momentum 45.6/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
