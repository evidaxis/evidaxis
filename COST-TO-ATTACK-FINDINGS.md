# Evidaxis — cost-to-attack probe findings (2026-06-30)

> Source: 14-agent ultracode probe (12 signal/cross-cutting probes + adversarial undercut + verdict), grounded
> in live platform mechanics + the actual collect.py. Verdict: NO-GO as-is, CONDITIONAL GO with 3 cheap fixes.

## The discovery (reconciles consilium-44)
The CITATION axis — which consilium-44 (Kimi/Opus) called "architecturally flawed / too slow, fires late" — is
EXACTLY what makes a public "Rising" badge UNFORGEABLE. Its ~3-year incubation (OpenAlex AXIS2_MIN_YEARS=3) +
the post-Jan-2026 arXiv endorsement gate is a TIME + CREDENTIAL wall money cannot buy, AND it draws from a
DISJOINT credential pool from the commit axis (free GitHub accounts vs arXiv-endorsed academics) → the 2-axis
AND is near-PRODUCT, not near-min: no single fabricated identity lights both legs.

**The fundamental tradeoff this surfaces: TIMELINESS vs FORGERY-RESISTANCE.** The citation axis's slowness is a
bug for early-warning (consilium-44) but the FEATURE for security (this probe). A signal that is BOTH fast AND
forgery-resistant as a PUBLIC read essentially does not exist: every fast signal (derivatives, dependents,
downloads, distinct-contributors) is forgeable for ~$0-100 once public.

## The numbers
- **"Rising" badge** (needs BOTH live axes): ~$2-4k + an irreducible ~3-year wall + one complicit credentialed
  academic → currently > the prize → PASSES.
- **"Watch" badge** (single live axis): commit-drip via free GitHub Actions cron ≈ **$0-25**, fully automated,
  1 identity → FAILS badly.
- **Prize** = a credibility halo (fundraising deck line / hiring / sales / laundering a scam model), low-five-
  figures EV at most. Bounded LOW because Evidaxis is POSITIVE-ONLY, no public rank, no ScoreVector, no "worst"
  list → a one-directional halo, nothing to poison or capture. (The person-free + positive-only invariants are
  SECURITY features here.)

## The critical hole = D10a (the z>=0 thin-cohort gate)
An attacker targets a THIN/COLD cohort (n=3-4) and beats a DEAD/negative median with a modest forged slope —
collapsing the citation-leg cost from ~$25-60k to ~$2-4k. This is the SAME D10a gap flagged in the audit
(spar-21); now revealed as THE security hole. Fix = ONE LINE in collect.py: require z>=1 (or cohort_size>=5 to
score a cohort at all). Pushes attack cost back to $25-60k. Highest-leverage defender move.

## VERDICT: NO-GO as-is; CONDITIONAL GO with 3 fixes
1. **SHIP THE D10a FIX before any public predictive layer** (z>=1 / cohort_size>=5). One line. Highest leverage.
2. **NEVER let "Watch" carry "Rising"-grade public credibility** ($0-25 attack) — mark it visibly provisional/
   un-converged, or drop the Watch tier from the public surface.
3. **FREEZE the DISJOINT-CREDENTIAL-POOL invariant:** admit a new public axis ONLY if it adds a NEW disjoint
   credential pool; REJECT any axis that shares the free-GitHub/HF pool (downloads, dependents, distinct-
   contributors, stars) — else one free farm lights multiple legs and the AND is near-free.
   (+ move the Sybil/age/cluster guard onto the SCORING path before any reserved consumption/identity axis goes
   live; keep velocity corroborating-only, never a sole gating leg.)

## Excluded signals (forgeable below prize → never a public gate)
hf-downloads (~$0 anonymous HEADs, no dedup) · hf-derivative-tree (self-declared base_model YAML, ~$0) ·
stars-velocity (SCORER-INVERTED — buying stars LOWERS the score) · distinct-contributor-velocity (the live axis
counts aggregate commits, not distinct → one bot satisfies it) · deps.dev-dependents (self-attested manifests,
mass-forged in the wild, ~$0-100) · distinct-org-descendants (reserved; ~$1-5k even guarded) · unique-puller
consumption (NOT externally observable by a third party; only hard if Evidaxis becomes the metering host, which
changes the product).

## Strategic crux (founder call)
A FAST, forgery-resistant, PUBLIC real-time predictor does not exist. Evidaxis can be EITHER:
- (A) a SLOW but DEFENSIBLE public "Rising" badge = 2-axis convergence (commit + citation) + the D10a fix —
  forgery-resistant but late/confirmation-grade (the security comes from the citation lag); OR
- (B) archive-only public surface + prediction as a private/forward research layer.
The original 2-axis convergence design was right for SECURITY (disjoint pools) even though weak for
timeliness/prediction. Pick the axis: fast OR forgery-resistant, not both in public.
