---
schema_ver: 1.0
entity_id: e_MB6DQ5PDDKH
entity_type: model
name: "Kokoro-82M"
slug: kokoro-82m
homepage: "https://huggingface.co/hexgrad/Kokoro-82M"
ids:
  github_repo: "hexgrad/kokoro"
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
  momentum: 49.8
  percentile: 43
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.0, "cohort_z": -0.033, "recent_weekly_commits": 0.0, "stars_not_scored": 9396}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.034458, "theil_sen": 0.030375, "cohort_z": 0.0, "latest": 125, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": false}
note: "batch#02 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# Kokoro-82M

Evidaxis measures **Kokoro-82M** on methodology m5. Momentum 49.8/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
