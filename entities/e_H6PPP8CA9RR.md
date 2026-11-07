---
schema_ver: 1.0
entity_id: e_H6PPP8CA9RR
entity_type: repo
name: "LeRobot"
slug: lerobot
homepage: "https://github.com/huggingface/lerobot"
ids:
  github_repo: "huggingface/lerobot"
  openalex_work_ids: ["W7131910578"]
classification:
  domain: ai
  industry: robotics
  sub_niche: embodied-ai
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 868e3c39d9c7
  captured_at: 2026-11-07T03:43:55+00:00
  period: 2026-w45
  momentum: 52.1
  percentile: 53
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.0289879926267077, "cohort_z": 0.487, "recent_weekly_commits": 19.1, "stars_not_scored": 28723}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 3, "by_year": {"2026": 3}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.016658, "theil_sen": 0.016905, "cohort_z": -0.15, "latest": 86, "points": 29, "points_reconstructable": 15, "as_of_partition": "2026-10-19", "unstable": false, "rising_vote": false}
note: "Paper exists but 0 citations indexed; axis-2 not yet usable."
---

# LeRobot

Evidaxis measures **LeRobot** on methodology m5. Momentum 52.1/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
