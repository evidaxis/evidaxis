---
schema_ver: 1.0
entity_id: e_P4YGBAFMV94
entity_type: repo
name: "Cline"
slug: cline
homepage: "https://cline.bot/"
ids:
  github_repo: "cline/cline"
  openalex_work_ids: []
classification:
  domain: ai
  industry: developer-tools
  sub_niche: coding-agents
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: d1eb0cec0f6a
  captured_at: 2026-10-31T03:43:22+00:00
  period: 2026-w44
  momentum: 46.5
  percentile: 42
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.014390860307005532, "cohort_z": 0.089, "recent_weekly_commits": 65.6, "stars_not_scored": 71082}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.011163, "theil_sen": 0.012835, "cohort_z": -0.641, "latest": 21, "points": 28, "points_reconstructable": 15, "as_of_partition": "2026-10-12", "unstable": false, "rising_vote": false}
note: "No academic paper; axis-2 absent."
---

# Cline

Evidaxis measures **Cline** on methodology m5. Momentum 46.5/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
