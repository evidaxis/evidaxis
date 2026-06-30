# Evidaxis — Entity-Resolution feasibility findings (sprint job #2, 2026-06-30)

> Source: ultracode workflow `evidaxis-er-test` (build agent pulled 330 real records, built 2 matchers,
> labeled 42 pairs; adversarial verify agent RE-RAN the code and corrected inflated numbers).
> Artifacts in scratchpad (er_records.json, matcher.py, matcher_v2.py, ground_truth.json, evaluate.py).
> Empirically + adversarially CONFIRMS the spar-23/24 prospect-id + human-review architecture.

## The result (corrected numbers, per the verify agent)
- Plain fuzzy name matching: precision **0.265** untuned, ceiling **~0.63 even at exact-string**, because it
  cannot separate "same artifact" from "family sibling" (bert-base-uncased vs bert-base-cased ~98% similar,
  different mintable artifacts).
- Discriminator-gated v2: the build agent claimed precision 0.90-1.0; the verify agent's full-catalog re-run
  shows **true auto-merge precision 0.846** with **2 live false-MERGES**, and the "precision-1.0 language patch"
  is **absent from the code** (the LANG presence-asymmetry landmine is still armed). High measured precision on
  a 21%-prevalence eyeballed sample is an UPPER BOUND that degrades on the real distribution.

## Verdict: auto-ER on names is NOT safe for permanent IDs
**False-merge is the worst poison** (irreversible: references minted against a merged ID contaminate both
artifacts and cannot be re-attributed; a false-SPLIT is recoverable). Both the matchers AND union-find
clustering are structurally biased toward the catastrophic merge direction (monotone-merging, FPs chain into a
9-model false cluster).

## The hardened spine ER guard (BUILD THIS into v3 — supersedes the looser version)
1. **Default-deny permanent minting.** Every catalog row mints a `prospect-id` first. A PERMANENT opaque-ID is
   granted ONLY by (a) human confirm, or (b) a hard cryptographic identity signal (identical weight hash /
   safetensors digest / arXiv-DOI in metadata). **Never by name score.**
2. **prospect-id TTL (~30d) + promotion gate.** Promote to permanent only on human confirm or external hard-ID
   corroboration arriving in the window; expiry without it = stays prospect (cheap, splittable).
3. **Dedup only on HARD equivalence.** Auto-merge allowed only for the cryptographic-equivalence class (same
   weights hash, or whitelisted quant/format suffix WITH identical core AND zero discriminator presence-asymmetry
   on ANY axis incl. LANG and ROLE). **Absent-attribute = NON-match → review** (fixes the live landmine).
4. **Human-review band sized by HARM, asymmetric.** Route any high-name-sim + no-hard-equivalence pair (~⅓ of
   candidates) to review; bias so MERGE needs MORE evidence than SPLIT (when uncertain, split into two
   prospect-ids, never merge).
5. **Cluster-level chaining guard.** Cap auto-merge cluster size (block any auto-cluster >2-3 records or spanning
   >1 owner from auto-promoting). Prevents the 9-model wav2vec2 collapse that no pairwise threshold catches.

## Hard-case taxonomy (the ER failure classes)
Family siblings (size/version/language/modality/resolution/cased — the DOMINANT failure) · cross-org mirrors of
identical weights (must MERGE; owner-diff is a false split signal) · name collisions across owners · org/library
vs artifact (transformers-lib vs a model) · cross-catalog model↔paper (rarest+weakest; needs external arXiv/DOI,
never title fuzz) · provenance≠identity (fine-tunes are linked-but-distinct) · preprint↔published (easy SAME).

## Net for the spine
The ER architecture is settled and grounded: build the 5-point guard above. The matcher is discriminator-gated,
not name-fuzzy. This is the prospect-id mechanism spar-23/24 demanded, now with empirical numbers + the exact
code-level landmines to avoid.
