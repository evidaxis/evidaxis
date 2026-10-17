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
  snapshot_id: 4d9867e6f218
  captured_at: 2026-10-17T12:13:42+00:00
  period: 2026-w42
  momentum: 69.3
  percentile: 64
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.0010431749022917474, "cohort_z": 3.081, "recent_weekly_commits": 22.3, "stars_not_scored": 34744}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.008212, "theil_sen": 0.008103, "cohort_z": 0.0, "latest": 383, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": false}
note: "incumbent (calibration); batch#02 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# Diffusers

Evidaxis measures **Diffusers** on methodology m5. Momentum 69.3/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
