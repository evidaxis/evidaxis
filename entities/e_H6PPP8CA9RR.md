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
  snapshot_id: 04724603bccf
  captured_at: 2026-11-14T03:45:26+00:00
  period: 2026-w46
  momentum: 52.1
  percentile: 33
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.03143959620722167, "cohort_z": 0.446, "recent_weekly_commits": 20.1, "stars_not_scored": 28868}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 66, "by_year": {"2026": 66}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.016378, "theil_sen": 0.016532, "cohort_z": -0.108, "latest": 87, "points": 30, "points_reconstructable": 15, "as_of_partition": "2026-10-26", "unstable": false, "rising_vote": false}
note: "Paper exists but 0 citations indexed; axis-2 not yet usable."
---

# LeRobot

Evidaxis measures **LeRobot** on methodology m5. Momentum 52.1/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
