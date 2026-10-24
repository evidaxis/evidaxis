---
schema_ver: 1.0
entity_id: e_VMQ8QRRDWVS
entity_type: repo
name: "FlashInfer"
slug: flashinfer
homepage: "https://github.com/flashinfer-ai/flashinfer"
ids:
  github_repo: "flashinfer-ai/flashinfer"
  openalex_work_ids: ["W4406032994"]
classification:
  domain: ai
  industry: ml-infrastructure
  sub_niche: llm-inference-serving
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 9a3f0a2522ac
  captured_at: 2026-10-24T03:35:10+00:00
  period: 2026-w43
  momentum: 57.1
  percentile: 85
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.09396742477671435, "cohort_z": 2.041, "recent_weekly_commits": 124.2, "stars_not_scored": 6763}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 4, "by_year": {"2026": 3, "2025": 1}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.022527, "theil_sen": 0.022129, "cohort_z": -0.905, "latest": 15, "points": 27, "points_reconstructable": 15, "as_of_partition": "2026-10-05", "unstable": false, "rising_vote": false}
---

# FlashInfer

Evidaxis measures **FlashInfer** on methodology m5. Momentum 57.1/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
