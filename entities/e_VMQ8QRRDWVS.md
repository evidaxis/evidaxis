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
  snapshot_id: d1eb0cec0f6a
  captured_at: 2026-10-31T03:43:22+00:00
  period: 2026-w44
  momentum: 57.8
  percentile: 85
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.10417803210447439, "cohort_z": 2.03, "recent_weekly_commits": 180.2, "stars_not_scored": 6823}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 4, "by_year": {"2026": 3, "2025": 1}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.02252, "theil_sen": 0.022129, "cohort_z": -0.779, "latest": 15, "points": 28, "points_reconstructable": 15, "as_of_partition": "2026-10-12", "unstable": false, "rising_vote": false}
---

# FlashInfer

Evidaxis measures **FlashInfer** on methodology m5. Momentum 57.8/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
