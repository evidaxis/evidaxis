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
  snapshot_id: 7bf8281671a3
  captured_at: 2026-11-28T03:40:51+00:00
  period: 2026-w48
  momentum: 62.4
  percentile: 100
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.11208468989706967, "cohort_z": 2.661, "recent_weekly_commits": 277.2, "stars_not_scored": 7020}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 505, "by_year": {"2026": 396, "2025": 107, "2024": 2}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.022577, "theil_sen": 0.022129, "cohort_z": -0.674, "latest": 16, "points": 32, "points_reconstructable": 15, "as_of_partition": "2026-11-09", "unstable": false, "rising_vote": false}
---

# FlashInfer

Evidaxis measures **FlashInfer** on methodology m5. Momentum 62.4/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
