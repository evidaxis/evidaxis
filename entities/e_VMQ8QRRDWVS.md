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
  snapshot_id: 04724603bccf
  captured_at: 2026-11-14T03:45:26+00:00
  period: 2026-w46
  momentum: 64.8
  percentile: 100
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.1257545965132412, "cohort_z": 3.05, "recent_weekly_commits": 264.2, "stars_not_scored": 6917}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 230, "by_year": {"2026": 140, "2025": 86, "2024": 4}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.022476, "theil_sen": 0.022129, "cohort_z": -0.674, "latest": 16, "points": 30, "points_reconstructable": 15, "as_of_partition": "2026-10-26", "unstable": false, "rising_vote": false}
---

# FlashInfer

Evidaxis measures **FlashInfer** on methodology m5. Momentum 64.8/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
