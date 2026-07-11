# DRAFT — Provenance quarantine (generalized admission funnel for new sources/axes)

> status: ADOPTED 2026-07-11 with amendments (licence/db-rights gate, 28-day floor, promo re-verify, one-at-a-time) — see ADJUDICATION-2026-07-11.md §6
> Grounds: QUARANTINE-m3-deps-axis.md (the working instance) · deps.dev identity
> erratum 2026-07-02 (the incident that proved the need) · RENEWAL delegation ·
> DRAFT-m3-quarantine-adjudication.md (which proposes making this funnel the §4 rule).

## Purpose

Every new DATA SOURCE or SIGNAL AXIS is a supply-chain risk to an append-only archive:
a mis-identified package (deps.dev pypi→npm flip), a gameable endpoint, or a silently
drifting upstream schema writes PERMANENT wrong rows. The m3 quarantine showed the
shape of the answer; this draft generalizes it into the standing admission rule.

## The funnel (five gates, all mandatory, in order)

1. **Invariant filter (paper gate).** Written check against the constitution:
   person-free feasible? positive-only compatible? reproducible from public inputs?
   gameability sketch with cost-to-attack estimate. Fails here → rejected, one page,
   filed in governance/.
2. **Identity audit (the deps.dev lesson).** Before ANY capture: how is the measured
   object's identity verified against the source (linkage proof, not name match)?
   Pinned identity map committed BEFORE capture starts.
3. **Shadow capture (append-only, unscored).** Minimum one full methodology period.
   Shadow rows are namespaced (never mix with scored axes), carry full provenance
   (endpoint, response hash), and are publishable as observations (I5: capture now,
   score later — capture is unrecoverable, scoring is cheap).
4. **Pre-registered A/B.** Promotion criteria written and committed BEFORE looking at
   shadow results (anti-HARKing). Includes: stability across the window, identity-flip
   rate, coverage floor, discrimination value added to the gate.
5. **Human gate.** The keeper signs promotion as a dated decision; the axis enters as
   a NEW methodology version. Demotion goes back through the same door (new version,
   never mutation).

## Sensors (fail-closed at the seams — the external-seam rule)

- A quarantined source whose collector exits green on a total outage is a defect of
  the QUARANTINE (this happened: outage rows written as "no_package_match"). Every
  quarantine collector must carry an outage sensor (total-failure => nonzero exit)
  BEFORE stage-3 shadow begins.
- Upstream schema drift → the identity map's `--verify` breaks loudly, not silently.

## Keeper action
- [ ] Adjudicate; if adopted, this becomes the standing rule the m3 adjudication
      (§4 amendment) points to.
