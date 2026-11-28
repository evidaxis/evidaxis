---
schema_ver: 1.0
entity_id: e_9VRK70WNP96
entity_type: repo
name: "Diffusers"
slug: diffusers
homepage: "https://huggingface.co/docs/diffusers"
ids:
  github_repo: "huggingface/diffusers"
  openalex_work_ids: []
classification:
  domain: ai
  industry: generative-media
  sub_niche: diffusion-media-gen
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 7bf8281671a3
  captured_at: 2026-11-28T03:40:51+00:00
  period: 2026-w48
  momentum: 29.3
  percentile: 0
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": -0.016136625909578577, "cohort_z": -3.311, "recent_weekly_commits": 16.9, "stars_not_scored": 34985}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.007243, "theil_sen": 0.007008, "cohort_z": 0.0, "latest": 389, "points": 32, "points_reconstructable": 15, "as_of_partition": "2026-11-09", "unstable": false, "rising_vote": false}
note: "incumbent (calibration); batch#02 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# Diffusers

Evidaxis measures **Diffusers** on methodology m5. Momentum 29.3/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
